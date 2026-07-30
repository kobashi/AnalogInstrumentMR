# 3Dモデル差し替えワークフロー

## 目的

リファインした3Dモデルを、配置データ、Spatial Anchor、操作状態、可動軸、
Grip位置、Connect機能を壊さずに段階導入する。候補モデルは検査が完了するまで
既存FBXとPrefabへ上書きしない。

## 現在の導入範囲

以下の13種類すべてについて、3テーマのFBXとVisual Prefabを本番導入済み:

- `meter.round`
- `meter.round.medium`
- `meter.round.large`
- `control.lever`
- `control.toggle`
- `control.rotary`
- `control.button`
- `indicator.lamp`
- `control.throttle`
- `control.power_slider`
- `indicator.status`
- `meter.window`
- `panel.window`

`indicator.status`、`meter.window`、`panel.window`もRuntime Greyboxから
専用Visual Prefabへ切り替え済み。

## 変更してはいけないRuntime契約

- `MockInstrumentKind`の値と順序
- `MockInstrumentCatalog`のtype ID
- `InstrumentRoot`とSpatial Anchorの対応
- `MountOrigin`、`Logic`、`Interaction`、`VisualSocket`等の共通socket
- `InteractionCollider`の位置と寸法
- 保存済みnormalized valueとdetent数
- 1 Unity unit = 1 m
- mount面はlocal `Z = 0`、local `+Z`は面から外向き
- root scale `(1, 1, 1)`

Visual Prefab内へCollider、Animator、Camera、Lightを追加しない。操作判定は
Runtime側の`InteractionCollider`を使い、theme間で操作感を変えない。

## 必須可動ノード

| 種類 | Pivot / motion target | 可動メッシュ |
| --- | --- | --- |
| Round Meter | `needle_pivot` | `needle` |
| Lever | `handle_pivot` | `handle` |
| Toggle | `switch_pivot` | `switch` |
| Rotary | `knob_pivot` | `knob` |
| Button | `button_travel` | `button` |
| Lamp | `indicator` | `indicator` |
| Throttle | `throttle_pivot` | `throttle_handle` |
| Power Slider | `slider_travel` | `slider_handle` |
| Status Indicator | `indicator` | `status_safe` / `status_warn` / `status_danger` |
| Window Meter | `needle_pivot` | `needle` |
| Window Panel | `vane_pivot` | `vane` |

Pivotは可動部と同じ場所へ移動させるのではなく、実際の回転軸・直動原点へ置く。
Lever、Toggle、ThrottleのPivotはbaseから浮かせず、可動端でもメッシュが
mount面やhousingへ貫通しない形状とする。

## Quest向け受け入れ上限

- 小型モデル: 5,000 triangles以下
- 中・大型メーター、窓枠メーター／パネル: 25,000 triangles以下
- Renderer: `InstrumentGreyboxSpecification`の種類別上限以下
- 共有Material: 2以下（opaque + emissive）
- realtime Light: 0
- Animator: 0
- Collider: 0
- 通常は1Kのtheme atlasを共有
- 大型モデルはLODを必須とし、個別予算は導入時に確定する

多段階LEDはhousingとSAFE／WARN／DANGERの最大4 Rendererを許可する。
3つの状態Rendererは同じMaterialを共有し、`ThemeVisualManifest`の
`stateRenderers`へSAFE、WARN、DANGERの順で登録する。OFFでは全消灯する。
大型Meter／Panelの暫定上限は25,000 trianglesとする。

モデルのvisual boundsは
[`GREYBOX_INSTRUMENT_SPEC.md`](GREYBOX_INSTRUMENT_SPEC.md)のEnvelope内へ収める。
mount面より後ろ（local `-Z`）へは1 mmを超えて出さない。

## 候補モデルの受け渡し

候補FBXは、既存ファイル名と区別できる名前で任意の`Assets`配下へ一時Importする。

```text
SM_<Key>_<Theme>_Refined.fbx
```

例:

```text
SM_Throttle_OrbitalAnalog_Refined.fbx
```

Blender側はZ-upで制作し、FBXは`-Z Forward / Y Up`でExportする。Unityでは
Scale Factor 1、Convert Units ON、Generate Colliders OFF、Import Animation OFF、
Import Cameras OFF、Import Lights OFF、Material Import Noneを使う。

## 段階導入手順

1. 候補FBXをUnityへ一時Importする。
2. Projectウィンドウで候補FBXを選択する。
3. `Tools > MatsuMotoMeterAR > Model Replacement > Validate Selected FBX`
   を実行する。
4. BlenderとUnityのプレビューでneutral pose、最大・最小可動端、mount面を確認する。
5. 合格した候補だけを対応する本番FBX名へ置き換える。
6. `Tools > MatsuMotoMeterAR > Rebuild Instrument Theme Assets`を実行する。
7. `Tools > MatsuMotoMeterAR > Model Replacement > Validate Active Prefabs`
   と`Audit Control Motion`を実行する。
8. まず1テーマ・代表3種類（Meter、LeverまたはToggle、Throttle）をQuestで確認する。
9. 問題がなければ同一契約で残りへ展開する。

本番FBX:

```text
Assets/MatsuMotoMeterAR/Content/Themes/<Theme>/Models/SM_<Key>_<Theme>.fbx
```

本番Prefab:

```text
Assets/MatsuMotoMeterAR/Resources/<Theme>/Prefabs/PF_Visual_<Key>_<Theme>.prefab
```

`StatusIndicator`、`WindowMeter`、`WindowPanel`も本番名のFBXが存在し、
再生成ツールがPrefab化する。FBXを一時的に取り下げた場合だけRuntime
Greyboxへフォールバックする。

## 実機確認項目

- 任意面でneutral poseの向きが正しい
- 配置previewと配置後でマテリアル・色が一致する
- Lever、Toggle、Throttleが可動端でbaseへめり込まない
- ThrottleのPalm Gripとコントローラー位置が一致する
- Power Sliderがlocal Y軸へ0.18 m直動する
- Buttonの接触範囲と見た目が一致する
- Meter、Lamp、StatusのEmissiveが暗所でも読める
- Connect線・選択マーカーがモデル外形に追従する
- 24個時に72 Hz性能基準を維持する

## ロールバック

差し替え前の本番FBX、Prefab、Materialを同じ変更単位としてGitへ記録する。
問題が出た場合は候補だけを取り下げ、type ID、保存schema、Runtimeロジックは
変更しない。これにより既存配置データを維持したまま旧Visualへ戻せる。
