# Development setup

初回構築の全工程、役割分担、問題解決履歴は
[`MR_FOUNDATION_SETUP.md`](MR_FOUNDATION_SETUP.md) を参照する。

## Pinned baseline

- Unity `6000.3.19f1` (Unity 6.3 LTS)
- Android Build Support: SDK、NDK、OpenJDK を Unity Hub から追加
- OpenXR `1.16.1` + Unity OpenXR Meta `2.5.1`
- URP `17.3.0` + XR Interaction Toolkit `3.3.2`
- Meta XR Core SDK、MRUK、Interaction SDK Essentials `203.0.0`
- Meta Quest 3 / 3S を最初の実機ターゲットとする

`ProjectSettings/ProjectVersion.txt` と `Packages/manifest.json` を変更する SDK 更新は、実機 smoke test とセットで行う。

## Workstation setup (macOS)

1. Unity Hub をインストールする。
2. Unity `6000.3.19f1` と Android Build Support、Android SDK & NDK Tools、OpenJDK をインストールする。
3. Git LFS をインストールし、`git lfs install` を実行する。
4. Unity Hub からこのディレクトリを開き、Package Manager の解決完了を待つ。
5. `File > Build Profiles > Add Build Profile` から `Meta Quest` を追加する。
6. Platform Browser の Partner Packages で `Meta XR Core SDK`、`Meta XR Mixed Reality Utility Kit`、`Meta XR Interaction SDK Essentials` を選ぶ。初期版では All-in-one SDK は使用しない。
7. Meta Quest build profile へ切り替える。Vulkanのみ、Minimum API 32、Target API 34、IL2CPP、ARM64、Linear Color Space が設定されることを確認する。
8. `Project Settings > XR Plug-in Management` で Meta Quest/Android 用の OpenXR loader を有効化する。
9. OpenXR の `Meta Quest Support`、`Meta XR Feature`、Foveation、Subsampled Layout、Composition Layers、Touch Plus / Touch Pro / Oculus Touch controller profiles を有効化する。現在のPassthrough、部屋認識、面raycast、Spatial AnchorはUnity OpenXR MetaのAR Foundation featureではなく、Meta XR SDK / MRUK経路を使用する。
10. `Project Validation` のエラーをすべて解消し、適切な package id を設定する。

確認コマンド:

```sh
./scripts/check-development-environment.sh
```

## Quest USB debugging

1. Meta developer organization を作成し、スマートフォンの Meta Horizon アプリで対象 Quest の Developer Mode を有効にする。
2. Quest と Mac をデータ通信対応 USB-C ケーブルで接続する。
3. ヘッドセット内の `Allow USB debugging` を許可する。常用端末なら RSA キーの常時許可を選ぶ。
4. `adb devices -l` で端末が `device` と表示されることを確認する。`unauthorized` の場合はヘッドセット内の許可を再確認する。
5. Unity の `Build And Run` で Android 実機へ配置する。

### Safe exit control

Editモードで左スティックを2秒間押し込み続けると、保存処理完了後にAndroid
Activityを終了する。HUDに長押し進捗を表示し、Anchorや配置データの保存中は
終了を保留する。ADBから停止する場合は`./scripts/stop-quest-app.sh`を使用する。

## Current readiness

2026-07-30 時点:

- [x] Unity 6.3 LTS、Android Build Support、SDK、NDK、OpenJDK
- [x] ADB、Git LFS
- [x] URP Asset / Universal Renderer、Input System、XR Interaction Toolkit
- [x] OpenXR、Unity OpenXR Meta、AR Foundation
- [x] Package 解決と C# compilation
- [x] Meta Quest build profile の作成と切り替え
- [x] Meta XR Core SDK、MRUK、Interaction SDK Essentials `203.0.0`
- [x] Meta XR base feature、Touch controller profiles、foveation feature
- [x] Passthrough capability、OVRManager、透明 camera background
- [x] 最小 MR シーン `Assets/MatsuMotoMeterAR/Scenes/MinimalMR.unity` と Build Settings 登録
- [x] MRUK Room、Scene permission、1 個のローカル Spatial Anchor 保存・復元
- [x] Project Validation error 0
- [x] Quest 3 の Developer Mode、USB debugging、`adb devices`
- [x] Passthrough APK の Build And Run smoke test（Quest 3へインストール・起動、OpenXR/Meta XR/Passthrough API初期化ログを確認）
- [x] Meta controller の B / Trigger 入力、controller beam、アプリ内安全終了の実機確認

### Rendering pipeline status

`QuestUniversalRenderPipeline.asset` と `QuestUniversalRenderer.asset` を使用し、
現在の実行パイプラインは URP である。Quest向け初期値は Forward、4x MSAA、
Render Scale 1.0、HDR / Depth Texture / Opaque Texture / Shadow / Additional Lightsを無効、
SRP Batcherを有効としている。

ランタイム生成オブジェクトはPipelineを検出してURP Materialを選択する。
切り戻し検証用にBuilt-in Materialと分岐も移行期間中は保持する。
移行手順と合否基準は [`URP_MIGRATION.md`](URP_MIGRATION.md) を参照する。

### Mock instrument placement controls

- 起動時は`OPERATION MODE`。左コントローラーの`X`で
  `OPERATION → EDIT → CONNECT → OPERATION`を循環する。モード切替時には
  短いhapticsが入る。
- `EDIT MODE`だけでpreview、種類・テーマ選択、配置、削除が有効になる。
- `OPERATION MODE`だけで配置済み計器へのray/direct Trigger操作が有効になる。
- `OPERATION MODE`で左スティックを2秒間押し込み続けると、`X`による
  モード切替をロックする。同じ操作をもう一度行うとロックを解除する。
- `OPERATION MODE`では左右コントローラーのOpenXR `aim pose`
  (`pointerPosition` / `pointerRotation`)からビームを描画し、Triggerを独立して
  使える。Quest HOMEと同じ照準姿勢を使い、左右の手で別々の操作対象を同時に扱える。
- レバー、スロットル、パワースライダーは、操作部へ接触してGripを握って
  多段階値を変更する。レバーはlocal Y方向0.24 m、スライダーはlocal Y方向
  0.18 mを全可動域として換算する。スロットルはpivot中心の70°アークに沿って
  操作する。detent通過時に操作側コントローラーへhapticsを返し、
  Grip解放時に保存する。
- 押しボタンは左右いずれかのコントローラー先端がColliderへ接触すると押下し、
  両方が離れたときに復帰する。ビーム＋Triggerでも同じ押下／復帰を行える。
- 円形メーター、窓枠メーター、窓枠パネルは操作不能とし、操作モード中は
  保存値を中心に小さな非同期needle/vane微動を続ける。編集モードでは停止する。
- `EDIT MODE`で配置位置が既存計器と重なる場合は、同じ認識面上の近傍を探索して
  previewを空き位置へ自動的にずらす。近傍に空きがない場合は配置を確定しない。
- 配置済み計器を照準して右Triggerを押すと個別に選択・選択解除する。選択中は
  第1選択を太いシアン枠、以降をオレンジ枠で表示し、異なる種類の計器も
  複数選択できる。選択中は新規追加・削除・配置種別変更を無効にする。
- 配置済み計器を照準している間は、新規配置previewと`A`による追加を停止する。
  未選択の照準対象は`B`で削除できる。右スティック押込みは照準対象を削除し、
  その種類へ追加対象を切り替える再配置操作とする。
- 選択中は移動先targetを表示し、`A`で移動を確定する。2個以上の選択中は
  右スティックを倒した方向へ、第1選択を起点に選択集合を回転する。
  選択中の`B`は選択集合全体を解除する。`Y`は将来の編集機能用に予約し、
  現在は何も実行しない。
- 2個以上の選択中は左スティック左で横整列、上で縦整列、右で横均等配置、
  下で縦均等配置をpreviewする。整列前の空間的な並び順を維持し、
  均等配置は軸上で最も離れた2個を両端とする。`A`で確定するまで元配置を保持し、
  別方向を入力すればpreviewだけを更新する。外形間隔は12 mm、重複判定の
  追加marginは2 mmとする。
- 整列・グループ移動が現在の共有Anchorから2.75 mを超える場合は、移動先近傍の
  Anchorを再利用するか新規Anchorを作成して自動的に付け替える。JSON保存に失敗した
  場合は親子関係、Anchor ID、surface、poseを編集前へ戻して新規Anchorをeraseする。
- Anchor範囲内の編集は`localOffset`として保存し、再起動後に復元する。
- EditモードではMRUKが認識したPlaneとVolumeをwireframe表示する。
  右コントローラーのrayから最も近い有効面を安定化して選択し、任意面へ
  previewを表示する。Mesh raycastは配置対象にしない。
- 追加オブジェクトは機能別に `METERS → INDICATORS → SWITCHES → MOTION`
  の順へ整理する。右スティック左右でカテゴリ内外をこの順に移動し、右スティック
  上下で前後カテゴリの先頭へジャンプする。丸形メーター小・中・大を含む全13種類を
  配置でき、HUD先頭に現在カテゴリを表示する。
- 左スティック左右でForge Brass、Orbital Analog、Kinetic Safetyを順に切り替える。
  選択テーマはglobal設定として直ちに保存され、previewと配置済みMockへ反映される。
- `A`を押すと選択中のMockを配置し、種類、操作状態、ローカルSpatial Anchorを
  schema v4 placement storeへRoom UUIDとともに保存する。最大48個まで個別に
  Roomごとに保持し、全Room合計は192個を安全上限とする。既存schema v1/v2/v3は
  起動時にv4へ移行する。約2.75 m以内の配置はSpatial Anchorを共有し、
  個別位置を`localOffset`で保持する。
- 実行中はMRUKの`GetCurrentRoom()`を0.5秒間隔で監視する。別Roomの判定が1秒
  継続したら、旧Roomの表示とinteraction colliderをアンロードし、移動先Roomの
  Plane／Volume wireframeと、そのRoom UUIDに属するSpatial Anchorを復元する。
  Room UUIDを持たない旧recordは、最初にAnchorを復元できたRoomへ自動所属させる。
- `X`はOperation → Edit → Connect → Operationの順に切り替える。Connectでは
  入力装置をビーム＋TriggerでSource選択し、表示装置を同様にTarget選択する。
  左スティック左右でDirect / Invert / Range / Thresholdを切り替え、`A`で確定、
  `B`で取り消す。接続を編集する場合は、入力または出力オブジェクトを1個だけ
  Triggerで選択し、`A`を押すたびにそのオブジェクトへ出入りする接続を順に選ぶ。
  接続線はDirect=シアン、Invert=マゼンタ、Range=緑、Threshold=オレンジで表示し、
  選択中はタイプ色を維持して太く明るくする。左スティック左右でその接続の
  Direct / Invert / Range / Thresholdを仮選択し、左スティック押し込みで
  変更を保存する。保存後は接続線だけを非選択にし、オブジェクト選択は維持する。
  `B`で選択中の接続だけを削除する。第1オブジェクトだけを選択した段階では
  `B`で選択をキャンセルする。Connectモードでは右スティックを使用しない。
  接続線はConnect時のみ表示し、一つのSourceから複数Targetへ分岐できる。
  複数Sourceから同じTargetへの入力はコンセプト確認版では平均合成する。
- 編集モードでTrigger選択すると移動状態へ入り、通常の配置previewと新規追加を
  停止する。照準中のPlane／Volume面へ移動後の外形をtarget markerで表示し、
  面適合と既存オブジェクトとの重複を事前判定する。配置可能なら緑、不可なら赤と
  HUD理由を表示し、`A`で確定、`B`で選択解除する。複数選択済みの場合は相対配置を
  保ったまま別の面へ回転・移動する。
- 全オブジェクトは上下を区別せず、Plane／Volumeのどの面にも配置できる。
- アプリを終了して再起動すると、保存済みMockを同じ種類・同じテーマ・同じ
  実空間位置へ復元する。古い配置データにtheme IDがない場合も、global設定または
  Orbital Analog fallbackを使用する。
- 各Mockは右Triggerのray/direct interactionに対応し、種類別の論理状態と
  hapticsを持つ。
- レバーは5ノッチ`-2 / -1 / 0 / +1 / +2`を持つ。右Triggerを押すたびに隣の
  ノッチへ移動し、端では進行方向を反転する。HUDにはdetent番号とpositionを表示し、
  保存済みの0〜1値は復元時に最寄りノッチへ正規化する。可動軸はmount面内の
  local X、可動面はmount面に対して垂直とする。初期角offsetを持つ片側sweepにより
  handleが基部へめり込まないようにする。
- `indicator.lamp`は従来どおりON/OFFを維持する。`indicator.status`は右Triggerで
  `OFF → SAFE → WARN → DANGER → OFF`と循環し、それぞれ消灯・緑・橙・赤で表示する。
  HUDと保存値には状態名と`0 / 0.333 / 0.667 / 1`を使用する。
- `control.throttle`は6ノッチ`CUTOFF / IDLE / LOW / CRUISE / HIGH / FULL`を持ち、
  保存値`0 / 0.2 / 0.4 / 0.6 / 0.8 / 1`へ対応する。Triggerで隣接ノッチへ移動し、
  両端で方向反転する。3テーマのPrefabは`throttle_pivot`をmotion targetとして使い、
  local X軸回転と初期角offsetでmount面に垂直な片側sweepを行う。接触Grip時は
  controller位置をpivot中心の回転面へ投影し、開始方向からの実アーク角を70°の
  全可動域へ換算する。Grip開始判定は計器全体のColliderではなく、
  pivotからlocal `(0, 0.225, 0.002)`にある幅160 × 高さ75 × 奥行85 mmの
  palm grip専用boxへ限定し、可動中もpivot回転へ追従する。
- 大型パネル、大型メーター、多段階警告LEDの配置previewは一律緑色へ
  material propertyを上書きせず、選択中テーマのhousing、face、warning色を保持する。
- `control.power_slider`は11ノッチ`OFF / 10% / ... / 90% / MAX`を持ち、
  保存値`0 / 0.1 / ... / 0.9 / 1`へ対応する。Triggerで10%ずつ移動し、両端で
  方向反転する。3テーマの可動ノードは`slider_travel`、travelはY方向0.18 mとする。
- `ROOM ERROR: NoRoomsFound` の場合は Quest の Space Setup で部屋をスキャンして再起動する。
- `ROOM TRACKING LOST / RUN SPACE SETUP` の場合は、保存済みの部屋は見つかっているが現在の実空間へ位置合わせできていない。Metaボタンでアプリを閉じ、Questの「設定 → 物理空間 → スペース設定」で現在の部屋を再スキャンしてからアプリを再起動する。
- performance gateの`matsu_perf_count`は既存の12 / 24 / 40に加えて、
  schema v4検証用の48 / 64を受け付ける。48は新しい合格点、64はstress用とする。

ログと基本操作:

```sh
adb logcat -s Unity ActivityManager AndroidRuntime
adb shell am force-stop com.DefaultCompany.MatsuMotoMeterAR
adb shell monkey -p com.DefaultCompany.MatsuMotoMeterAR 1
```

可動モデルのEditor監査:

- Unityメニュー:
  `Tools/MatsuMotoMeterAR/Audit Control Motion`
- Batch:
  `-executeMethod MatsuMotoMeterAR.Editor.InstrumentMotionAudit.Run`
- 出力:
  `Builds/Reports/instrument-motion-audit.md`とテーマ別コンタクトシート
- レバー、トグル、スロットル、パワースライダーについて全段階のRenderer実移動、
  軸一致、取付面後方への侵入を3テーマ分確認する。

## Definition of done for v0.2.0-concept.1

- パススルー背景で起動する。
- Plane／Volumeの任意面へ配置でき、Meshを配置対象にしない。
- 配置可能な13種類からMockを選択して配置し、アニメーションが72 Hz目標を
  妨げない。
- アプリを終了・再起動して同じ種類を同じ実空間位置に復元する。
- 接続と接続タイプを保存し、再起動後に復元する。
- アンカー/権限/空間データがない場合にクラッシュせず、ユーザーへ次の操作を示す。

## Primary references

- [Unity OpenXR Meta package](https://docs.unity3d.com/jp/current/Manual/com.unity.xr.meta-openxr.html)
- [Unity 6.3 OpenXR Meta package versions](https://docs.unity3d.com/6000.3/Documentation/Manual/com.unity.xr.meta-openxr.html)
- [Unity 6.3 Meta Quest workflow](https://docs.unity3d.com/6000.3/Documentation/Manual/xr-meta-quest-develop.html)
- [Unity 6.3 Meta Quest build profile](https://docs.unity3d.com/6000.3/Documentation/Manual/xr-meta-quest-build-profile.html)
- [Unity 6.3 Meta Quest packages](https://docs.unity3d.com/6000.3/Documentation/Manual/xr-meta-quest-packages.html)
- [Unity Android dependencies](https://docs.unity3d.com/ja/current/Manual/android-install-dependencies.html)
- [Meta OpenXR device setup and Space Setup](https://docs.unity.cn/Packages/com.unity.xr.meta-openxr%402.1/manual/get-started/device-setup.html)
- [Android Debug Bridge](https://developer.android.com/tools/adb)
- [Meta Shared Spatial Anchors sample](https://github.com/oculus-samples/Unity-SharedSpatialAnchors)
