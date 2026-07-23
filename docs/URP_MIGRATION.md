# URP migration

## Objective

Built-in Render Pipelineで成立したQuest 3実機基準を維持しながら、
URP `17.3.0`へ段階的に移行する。移行中もピンクMaterial、黒画面、
片眼描画、Passthrough停止をBuild前と実機smoke testで検出する。

## Current baseline

- Unity `6000.3.19f1`
- URP `17.3.0` / Universal Renderer
- Vulkan、OpenXR Single Pass Instanced
- Meta XR Core / MRUK / Interaction SDK `203.0.0`
- Quest 3でPassthrough、MRUK room load、Spatial Anchor、
  Touch Plus入力、アプリ内終了を確認済み
- Built-in比較基準APK: `Builds/Quest/MatsuMotoMeterAR-placement-v5.apk`
- URP初回APK: `Builds/Quest/MatsuMotoMeterAR-urp-v1.apk`

`QuestUniversalRenderPipeline.asset` と `QuestUniversalRenderer.asset` を作成し、
Graphics Settingsへ割り当て済み。Android Meta Quest Supportは
SRP Foveation APIを使用する。

## Migration result (2026-07-17)

- [x] URP Asset / Universal Renderer Data作成・割り当て
- [x] Forward、4x MSAA、HDR / Depth / Opaque / Shadow無効
- [x] SRP Batcher有効、Dynamic Batching無効
- [x] Android SRP Foveation有効
- [x] Build前Validator成功、Unity Console error 0
- [x] Quest 3でURP APKをインストール・起動
- [x] Passthrough、両眼描画、HUD、赤パネル、シアン表示、MRUK `ROOM READY`
- [x] ピンクMaterial、黒画面、片眼欠落なし
- [x] 短時間計測で72/72 FPS、stale frame 0
- [x] コントローラー照準、A/B/Trigger、アプリ内終了、面配置の手動回帰
- [x] Spatial AnchorのActivity終了・再起動後復元
- [ ] 10分連続性能ゲート

## Preparation already in place

- `RuntimeMaterialUtility`が現在のPipelineを判定し、Built-in/URP用の実Materialを選択する。
- Built-in用: `MAT_RuntimeBuiltInUnlit.mat`
- URP用: `MAT_RuntimeUrpUnlit.mat`
- Build前Validatorが両Materialの存在、Shader名、色PropertyとPipeline種別を検証する。
- EditMode testが両Materialの契約を検証する。

このブリッジは移行期間専用とする。URP安定後はBuilt-in Materialと分岐を削除する。

## Migration phases

### Phase 1: create URP assets

次の2アセットを専用ディレクトリに作成する。

- Universal Renderer Data
- Universal Render Pipeline Asset

Quest向け初期値:

| Setting | Initial value |
| --- | --- |
| Rendering Path | Forward |
| HDR | Off |
| MSAA | 4xから開始し、GPU計測で2xも比較 |
| Render Scale | 1.0 |
| Depth Texture | Off |
| Opaque Texture | Off |
| Depth Priming | Disabled |
| SSAO / Post-processing | Off |
| Main Light Shadows | Offから開始 |
| Additional Lights | DisabledまたはPer Vertex |
| SRP Batcher | On |
| Dynamic Batching | Offを初期値 |

Environment Depthや遮蔽など、Depth Textureを必要とする機能を追加するときだけ
該当設定を有効化し、GPU負荷を再測定する。

### Phase 2: activate on a migration branch

1. Built-in基準APKとQuest画面録画、起動ログを保存する。
2. `Graphics Settings > Scriptable Render Pipeline Settings`へURP Assetを割り当てる。
3. Androidで使用するQuality Level（現在はMedium）のoverrideは、
   未設定でGlobal設定を継承するか、同じURP Assetを明示する。
4. Console error 0とBuild前Validator成功を確認する。
5. Editor表示だけで合格とせず、専用名のQuest APKをBuildする。

切り戻しはGraphics SettingsのRender Pipeline Assetを`None`へ戻し、
Quality overrideも`None`にする。MaterialブリッジによりBuilt-in描画へ戻る。

### Phase 3: Quest smoke test

以下を冷起動とActivity復帰後の両方で確認する。

- Passthrough背景が両眼で継続表示される。
- HUD、終了パネル、ビーム、配置preview、計器全パーツにピンク表示がない。
- 照準成功が緑、Trigger holdが黄色になる。
- MRUKが20秒以内に`Success`になり、壁・床・天井へ配置できる。
- Spatial Anchorを保存し、Activity終了・再起動後に復元できる。
- B長押しとTrigger長押しで終了できる。
- VulkanとSingle Pass Instancedで起動し、片眼欠落がない。

期待ログ:

```text
Runtime rendering pipeline: URP; material: Materials/MAT_RuntimeUrpUnlit.
[Placement] MRUK V1 room load started.
[Placement] MRUK room load completed: Success.
```

### Phase 4: performance gate

Quest 3を72 Hzに固定し、通常の非Development APKを10分実行する。

| Metric | Pass criterion |
| --- | --- |
| CPU frame time p95 | 13.9 ms未満 |
| GPU frame time p95 | 13.9 ms未満 |
| Internal headroom target | 各p95 11.1 ms以下 |
| Dropped/stale frames | 1%未満 |
| Built-in比のp95悪化 | CPU/GPU各+1.0 ms以内 |
| Memory増加 | 10%以内 |
| 起動からROOM READYまでの悪化 | 2秒以内 |

性能合否はOVR Metrics ToolまたはMQDH Performance Analyzerで測る。
Unity ProfilerのDevelopment Buildは原因分析にのみ使用し、最終合否には使わない。

## Material audit scope

現在、アプリ固有のPrimitive、配置preview、計器、終了パネル、Running marker、
LineRendererは`RuntimeMaterialUtility`を経由するため、一括して移行できる。

TextMeshはUnity既定Font Materialを使用するため、URP実機で別途確認する。
テーマ用PrefabとMaterialが増えた段階では、全Materialをカタログ化し、
Shaderとtexture budgetをテーマごとに検証する。

## Completion criteria

- URP AssetとRenderer Dataがリポジトリに保存されている。
- Graphics/Quality設定が意図したURP Assetを参照する。
- Build前ValidatorとEditMode testが成功する。
- Quest実機smoke testが全項目成功する。
- 72 Hz性能ゲートを通過する。
- Built-inへの切り戻し手順を1回実証する。
