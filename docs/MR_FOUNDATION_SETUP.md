# Meta Quest + Unity MR 開発基盤構築ガイド

## 1. 目的

この文書は、macOS 上に Meta Quest 3 / 3S 向け Unity MR アプリの開発基盤を構築し、
USB 接続した Quest 実機でビルド、起動、デバッグできる状態までの工程を再現可能な形で
まとめたものである。

本プロジェクトでは、パススルー空間の壁・床・天井へ Mock 計器を配置し、
Spatial Anchor で保存・復元する最小垂直スライスまでを基盤の検証対象とする。
計器、レバー、スイッチと3種類のビジュアルテーマは、この基盤の上に追加する。

## 2. 検証済み構成

2026-07-17 時点の固定構成は次のとおり。

| 項目 | バージョン・設定 |
| --- | --- |
| 開発機 | macOS |
| Unity | `6000.3.19f1`（Unity 6.3 LTS） |
| 対象実機 | Meta Quest 3、将来 Quest 3S |
| Meta XR Core SDK | `203.0.0` |
| Meta XR MRUK | `203.0.0` |
| Meta XR Interaction SDK Essentials | `203.0.0` |
| OpenXR Plugin | `1.16.1` |
| Unity OpenXR Meta | `2.5.1` |
| XR Interaction Toolkit | `3.3.2` |
| Input System | `1.19.0` |
| URP | `17.3.0` |
| XR Plug-in Management | `4.5.4` |
| Android Minimum API | 32 |
| Android Target API | 34 |
| Android CPU / backend | ARM64 / IL2CPP |
| Graphics API | Vulkan のみ |
| Color Space | Linear |
| 目標リフレッシュレート | 72 Hz |

AR Foundation `6.5.0` と XR Hands `1.7.2` も依存パッケージとして解決されているが、
現在のパススルー、部屋認識、配置 raycast、Spatial Anchor の実装経路には使用していない。

## 3. 基盤の役割分担

本構成では「OpenXR を有効にしたこと」と「Unity OpenXR Meta の AR Foundation 機能を
使用すること」を区別する。

| 層 | 現在の役割 |
| --- | --- |
| Unity / URP | シーン、ライフサイクル、Android APK、Quest向け描画 |
| OpenXR | Quest向けXR loader、controller interaction profile、foveation |
| Meta XR Core | `OVRManager`、`OVRPassthroughLayer`、`OVRInput` |
| MRUK / Meta Scene API | 部屋データ、壁・床・天井分類、面への raycast |
| Meta Spatial Anchor | `OVRSpatialAnchor` によるローカル保存・復元 |
| ADB | USB端末確認、APK install、起動、停止、logcat |

現在有効な Android OpenXR feature は次のとおり。

- Meta Quest Support
- Meta XR Feature
- Meta XR Foveation
- Meta XR Subsampled Layout
- Meta Quest Touch Plus Controller Profile
- Meta Quest Touch Pro Controller Profile
- Oculus Touch Controller Profile
- Composition Layers

Unity OpenXR Meta の Camera (Passthrough)、Session、Planes、Raycasts、Anchors、
Occlusion、Meshing feature は現在無効である。MR 機能は Meta XR SDK / MRUK 経路で
成立しているため、両方の実装を無計画に同時有効化しない。

## 4. Mac と Unity の準備

### 4.1 Unity Hub

Unity Hub から Unity `6000.3.19f1` と次のモジュールを導入する。

- Android Build Support
- Android SDK & NDK Tools
- OpenJDK

Android モジュールは Unity プロジェクト作成後に Package Manager から入れるものではなく、
Unity Editor 本体へ Unity Hub の `Add modules` で追加する。

Unity 6.3 LTS でプロジェクトを開く際にバージョン不一致警告が出た場合は、
リポジトリで固定した `ProjectSettings/ProjectVersion.txt` と同じ
`6000.3.19f1` を選択する。別バージョンへの意図しない変換は行わない。

### 4.2 プロジェクト

このリポジトリ自体が Unity プロジェクトのルートである。
Unity Hub の `New Project` で下位へ別プロジェクトを作らず、
Unity Hub の `Add` または `Open` から次を直接開く。

```text
<repository-root>
```

Unity Hub のテンプレートから新規作成する場合の基準は URP Core だが、
本リポジトリではすでに必要なプロジェクト構造と URP asset が作成済みである。

### 4.3 基本ツール

Git LFS を導入して初期化する。

```sh
git lfs install
./scripts/check-development-environment.sh
```

## 5. Unity Package の導入

### 5.1 Unity 側パッケージ

Package Manager で次を解決する。

- Input System
- XR Plug-in Management
- OpenXR Plugin
- Unity OpenXR Meta
- XR Interaction Toolkit
- Universal Render Pipeline

旧 Input Manager の廃止予定警告に対しては、
`Project Settings > Player > Active Input Handling` を `Input System Package (New)`
にする。本プロジェクトでは Input System のみを使用する。

### 5.2 Meta XR SDK

Unity 6 の Platform Browser にある `Partner Packages` から次を導入する。

- Meta XR Core SDK
- Meta XR Mixed Reality Utility Kit
- Meta XR Interaction SDK Essentials

これらは Asset Store から探す必要はない。初期構成では Meta XR All-in-One SDK を使わず、
必要なパッケージだけを明示的に選択している。

Meta XR Simulator は Editor 上の一部確認を補助する任意パッケージであり、
実機検証の必須要件ではない。自動 Fix で導入してもよいが、Quest のパススルー、
Space Setup、実コントローラー、端末性能、Spatial Anchor の実機試験を代替しない。

Package を更新した場合は、C# compilation、Project Validation、APK build、
Quest smoke test を一組で再実施する。

### 5.3 built-in module のエラー

Meta XR SDK 導入時に次のコンパイルエラーが発生した。

| エラー | 原因と対処 |
| --- | --- |
| `AssetBundle` が `UnityEngine` に見つからない | Package Manager の Built-in Packages で `Asset Bundle` を有効化 |
| `Physics2D` が存在しない | Package Manager の Built-in Packages で `Physics 2D` を有効化 |

現在の `Packages/manifest.json` では両 built-in module を有効化済みである。

## 6. Meta Quest Build Profile

`File > Build Profiles` で `Meta Quest` profile を追加し、アクティブにする。

現在の主要設定:

- Build scene: `Assets/MatsuMotoMeterAR/Scenes/MinimalMR.unity`
- Android Minimum API Level: 32
- Android Target API Level: 34
- Scripting Backend: IL2CPP
- Target Architecture: ARM64
- Color Space: Linear
- Graphics API: Vulkan のみ
- Auto Graphics API: Off
- Graphics Jobs: On
- Active Input Handling: Input System Package
- Development Build: Off
- Compression: LZ4HC
- IL2CPP optimization: LTO
- 開発用 Scripting Define Symbol: `MATSU_DEV_EXIT`

`MATSU_DEV_EXIT` は実機テスト用の安全終了UIを含める define である。
製品用 profile では外す。

正式なアプリ識別子は未確定で、現状は次を使用している。

```text
com.DefaultCompany.MatsuMotoMeterAR
```

ストア提出、署名、永続データ互換を固定する前に正式な package ID へ変更する。

## 7. XR と Meta Project 設定

### 7.1 XR Plug-in Management

Android タブで OpenXR loader を有効化し、前述の Quest Support、Meta XR、
controller profiles、foveation、composition layers を有効にする。

`Project Validation` は Error 0 にする。Fix ボタンで変更された設定や追加された
パッケージは、Fix 後に必ず差分と実機動作を確認する。

### 7.2 Meta XR 設定

Meta XR Project Setup Tool / Oculus Project Config では少なくとも次を有効にする。

- Passthrough capability: Required
- Scene support
- Anchor support
- Scene permission request

現在の最小 Horizon OS は 60、target は 203。Hand Tracking、Eye Tracking、
Body / Face Tracking、Shared Anchor は現在の垂直スライスでは無効である。

## 8. URP の Quest 向け設定

アクティブな pipeline asset:

```text
Assets/MatsuMotoMeterAR/Settings/Rendering/QuestUniversalRenderPipeline.asset
Assets/MatsuMotoMeterAR/Settings/Rendering/QuestUniversalRenderer.asset
```

Quest向け初期値:

| 設定 | 値 |
| --- | --- |
| Rendering Path | Forward |
| MSAA | 4x |
| Render Scale | 1.0 |
| HDR | Off |
| Depth Texture | Off |
| Opaque Texture | Off |
| Main Light Shadows | Off |
| Additional Lights | Disabled |
| Depth Priming | Disabled |
| Intermediate Texture | Auto |
| SRP Batcher | On |
| Dynamic Batching | Off |
| SRP Foveation API | On |

Android が使用する Quality Level は Medium で、個別 pipeline override は置かず、
Graphics Settings の global URP asset を継承している。

初期実装は Built-in Render Pipeline で Quest 実機動作を確立し、その基準を保持したまま
URP へ移行した。ランタイム生成物には実 asset として保存した Built-in / URP 用 material を
pipeline に応じて選ぶブリッジを設けている。詳細は
[`URP_MIGRATION.md`](URP_MIGRATION.md) を参照する。

## 9. USB デバッグと ADB

### 9.1 Quest 側の準備

1. Meta developer organization を作成する。
2. スマートフォンの Meta Horizon アプリで対象 Quest の Developer Mode を有効にする。
3. Quest の電源を入れ、ロックを解除する。
4. データ通信対応 USB-C ケーブルで Mac と接続する。
5. ヘッドセット内の `Allow USB debugging` と RSA key を許可する。

Developer Mode は通常、Quest の電源を切っても保持される。再起動のたびに有効化し直す
必要はない。USB debugging 通知が出ない場合は、端末のロック解除、ケーブルのデータ対応、
ポート、既存のRSA許可状態を確認する。

### 9.2 Unity 同梱 ADB

ターミナルから `adb` が見つからない場合は、Unity 同梱 SDK の adb を使う。

```sh
ADB="/Applications/Unity/Hub/Editor/6000.3.19f1/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb"
"$ADB" devices -l
```

恒常的に PATH を通す場合:

```sh
export PATH="/Applications/Unity/Hub/Editor/6000.3.19f1/PlaybackEngines/AndroidPlayer/SDK/platform-tools:$PATH"
```

必要なら同じ `export` を `~/.zshrc` へ追加し、新しいターミナルを開く。

期待する状態:

```text
<serial>    device ...
```

`unauthorized` の場合:

1. Quest を装着し、USB debugging 許可を確認する。
2. Quest の開発者設定で USB debugging authorization を取り消す。
3. USB を抜き差しして RSA 許可をやり直す。
4. 別のデータケーブルまたはUSBポートを試す。
5. `adb kill-server`、`adb start-server`、`adb devices -l` を順に実行する。

## 10. 最小 MR シーン

最小シーン:

```text
Assets/MatsuMotoMeterAR/Scenes/MinimalMR.unity
```

このシーンには次の基盤要素がある。

- `OVRManager`
- `OVRPassthroughLayer`
- 背景 alpha 0 の XR camera
- MRUK
- Scene permission request
- 稼働状態HUD
- controller beam と開発用終了パネル
- 壁・床・天井への Mock meter placement

パススルーは Unity OpenXR Meta の Camera feature ではなく、
`OVRManager` と `OVRPassthroughLayer` で有効化している。

## 11. 入力と開発用終了操作

右コントローラーは `OVRInput` で取得する。コントローラーを置くと `NOT FOUND`、
持つと ready 表示になるため、トラッキング状態の確認にも使用できる。

開発用終了操作:

- 右コントローラーの B を 1.5 秒長押し
- 終了パネルを照準し、Trigger を 0.75 秒長押し
- Mac から `./scripts/stop-quest-app.sh`
- Quest の Meta メニューからアプリを終了

照準状態を判別できるよう、controller beam と終了パネルは状態に応じて表示を変える。

- Cyan: 通常
- Green: 照準成功
- Yellow: Trigger hold 中

終了パネルの判定は collider raycast に加えて4度の cone fallback と
0.15秒の照準猶予を持つ。

## 12. Space Setup、MRUK、配置

Quest の `設定 > 物理空間 > スペース設定` で使用する部屋をスキャンする。
壁、床、天井が認識されるまで Space Setup を完了させる。

現在の MRUK 読み込み設定:

- Data source: Device
- Scene API: V1
- High fidelity: Off
- 自動 Scene Capture request: Off
- XR 起動安定待ち: 1.5 秒
- Room load timeout: 20 秒

実行時は MRUK をいったん inactive で構成してから有効化し、
room load 完了を待つ。`ROOM READY` が表示されれば配置試験へ進める。

Mock meter 操作:

- 右コントローラーを壁・床・天井へ向ける。
- 配置可能面では緑色の円形 preview と面種別を表示する。
- A で `meter.round` を1個配置する。
- 新規配置は既存の1個を置き換える。
- 右スティック押し込みで配置物と保存 anchor を削除する。

raycast の最大距離は 10 m、面からの offset は 0.015 m である。

## 13. Spatial Anchor

配置確定時に `OVRSpatialAnchor` を作成し、`SaveAnchorAsync` でローカル保存する。
保存した UUID は現段階では `PlayerPrefs` に保持する。

確認手順:

1. 壁、床、天井のいずれかへ計器を配置する。
2. anchor 保存成功ログを確認する。
3. Activity を終了する。
4. アプリを再起動する。
5. 同じ実空間位置に計器が復元されることを確認する。

`ROOM ERROR: NoRoomsFound` の場合は Space Setup を実行する。
`ROOM TRACKING LOST / RUN SPACE SETUP` の場合は、保存済み部屋は存在するが
現在の実空間との位置合わせに失敗している。アプリを閉じ、現在の部屋を再スキャンする。

## 14. APK の build、install、起動

### 14.1 Unity から

`File > Build Profiles` で Meta Quest profile が active であることを確認し、
`Build And Run` を実行する。すでに build 済みなら、profile の `Run` または
ADB install を使う。

### 14.2 ターミナルから

```sh
ADB="/Applications/Unity/Hub/Editor/6000.3.19f1/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb"
"$ADB" install -r Builds/Quest/MatsuMotoMeterAR-urp-v1.apk
"$ADB" shell monkey -p com.DefaultCompany.MatsuMotoMeterAR 1
"$ADB" logcat -s Unity ActivityManager AndroidRuntime
```

停止:

```sh
"$ADB" shell am force-stop com.DefaultCompany.MatsuMotoMeterAR
```

または:

```sh
./scripts/stop-quest-app.sh
```

比較用 APK:

| APK | 用途 |
| --- | --- |
| `Builds/Quest/MatsuMotoMeterAR-placement-v5.apk` | Built-in 基準 |
| `Builds/Quest/MatsuMotoMeterAR-urp-v1.apk` | URP 初回実機検証 |

## 15. 発生した問題と解決

| 症状 | 原因・解決 |
| --- | --- |
| Input Manager 廃止予定警告 | Input System package を導入し、Active Input Handling を Input System のみに変更 |
| Meta SDK の `AssetBundle` compile error | Built-in `Asset Bundle` package を有効化 |
| `Physics2D` が見つからない | Built-in `Physics 2D` package を有効化 |
| USB接続しても反応しない | データケーブル、ロック解除、RSA許可、Developer Mode、`adb devices -l` を確認 |
| アプリを終了できない | B長押し、照準+Trigger長押し、ADB force-stop の安全経路を実装 |
| Trigger 自体は検出するがパネルを押せない | beam、照準色、cone fallback、照準猶予を追加 |
| Scene Loading が完了しない | XR settle wait、MRUK構成順、Device/V1、20秒 timeout、Space Setupを見直し |
| `NoRoomsFound` / tracking lost | Quest の Space Setup で現在の部屋を再スキャン |
| 計器やパネルがピンク | render pipeline と shader/material の不一致を修正 |
| build 後だけ material が失われる | `Shader.Find` だけに依存せず、Resources 内の実 material asset を参照 |
| Built-in では描画できるがURPでピンク | Built-in/URP別 material と pipeline検出ブリッジを作成 |

## 16. Material と URP 移行の保護策

ランタイム生成オブジェクトは `RuntimeMaterialUtility` を通し、pipeline に応じて
次の実 material asset を選ぶ。

- `MAT_RuntimeBuiltInUnlit.mat`
- `MAT_RuntimeUrpUnlit.mat`

Build前 validator は material の存在、shader、色 property、pipeline 種別を検証する。
EditMode test も同じ契約を検証する。ピンク表示は単なるデザイン不良ではなく、
shader欠落またはpipeline不一致として build を止めて扱う。

## 17. 実機 smoke test

### 17.1 基盤合否

- [x] Quest を `adb devices -l` が `device` として認識する
- [x] APK を install / start できる
- [x] OpenXR / Meta XR が初期化する
- [x] パススルーが両眼で表示される
- [x] controller の B / Trigger 入力を検出する
- [x] controller beam が表示される
- [x] B長押しと照準+Trigger長押しで終了できる
- [x] MRUK が部屋を読み込み `ROOM READY` になる
- [x] 壁・床・天井に Mock meter を配置できる（Built-in基準）
- [x] Spatial Anchor を保存・再起動復元できる（Built-in基準）

### 17.2 URP 移行確認

- [x] URP APK を Quest 3 に install / start
- [x] パススルー、両眼描画、HUD、終了パネル、MRUK `ROOM READY`
- [x] ピンク material、黒画面、片眼欠落なし
- [x] 短時間 72/72 FPS、stale frame 0
- [x] URPで controller照準、A/B/Trigger、終了操作を手動回帰
- [x] URPで認識面への配置と削除を手動回帰
- [x] URPで Spatial Anchor のActivity終了・再起動復元
- [ ] Quest 3で10分連続性能試験
- [ ] Built-inへの切り戻しを1回実証
- [ ] Quest 3S実機試験

短時間 telemetry では App 約 2.7 ms、CPU/GPU 約 5.5 ms を確認している。
最終性能合否は非 Development APK を72 Hzで10分実行して判定する。

## 18. 現在の基盤完成度

Unity、Android toolchain、Meta XR SDK、OpenXR、URP、USB/ADB、パススルー、
controller input、MRUK room、面配置、ローカル Spatial Anchor までの
開発基盤は揃っている。

ただし「URP移行完了」とするには、前節の未完了項目が残る。また製品化前には次も必要。

- 正式 package ID と署名方針
- 配置データを `IAnchorService` と JSON store へ統合
- 複数計器、レバー、スイッチの追加
- 3テーマ切り替え
- 権限拒否、room未設定、anchor消失時の製品UI
- Quest 3Sの性能・描画確認
- 現在の作業ツリーを version control の基準点として記録

## 19. 関連ファイル

- [`DEVELOPMENT.md`](DEVELOPMENT.md): 日常の開発・実機操作
- [`URP_MIGRATION.md`](URP_MIGRATION.md): URP移行と性能ゲート
- [`ARCHITECTURE.md`](ARCHITECTURE.md): SDK非依存domainとMeta adapterの設計
- [`OBJECT_CATALOG.md`](OBJECT_CATALOG.md): 計器、レバー、スイッチの準備計画
- [`VISUAL_THEMES.md`](VISUAL_THEMES.md): 3テーマの表現方針
- `Assets/MatsuMotoMeterAR/Scenes/MinimalMR.unity`: 最小MRシーン
- `Assets/MatsuMotoMeterAR/Settings/Rendering/`: Quest向けURP設定
- `Packages/manifest.json`: Unity / Meta package固定
- `ProjectSettings/`: Player、Graphics、XR、Build Profile設定
- `scripts/check-development-environment.sh`: Mac側ツール確認
- `scripts/stop-quest-app.sh`: USB接続したQuest上のアプリ停止
