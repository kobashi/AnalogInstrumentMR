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

### Development exit controls

実機テスト中は視界内の `APP RUNNING` マーカーでアプリ稼働中と判別できる。終了方法は次のいずれかを使う。

- `META INPUT READY` を確認し、右コントローラーの B ボタンを 1.5 秒間長押しする。
- 赤い `POINT + TRIGGER EXIT` ボタンを右コントローラーで指し、トリガーを 0.75 秒間長押しする。
- Mac から `./scripts/stop-quest-app.sh` を実行する。

安全UIは Meta Quest Build Profile の `MATSU_DEV_EXIT` define でのみ有効になる。製品用Build Profileにはこのdefineを設定しない。

## Current readiness

2026-07-17 時点:

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

- 右コントローラーを壁・床・天井へ向ける。MRUKが認識した面では選択中オブジェクトの緑色previewと面種別が表示される。
- 右スティックを左右へ倒すと、円形メーター、レバー、トグル、ロータリーノブ、押しボタン、状態灯を順に切り替える。
- 右スティックを上下へ倒すと、Forge Brass、Orbital Analog、Kinetic Safetyを
  順に切り替える。選択テーマはglobal設定として直ちに保存され、previewと
  配置済みMockへ反映される。
- `A`を押すと選択中のMockを配置し、種類、操作状態、ローカルSpatial Anchorを
  schema v1 placement storeへ保存する。最大24個まで個別に保持する。
- レバーとロータリーノブは壁・床専用。天井を照準した場合は配置不可メッセージを表示する。
- 右スティックを押し込むと配置済みMockと保存アンカーを削除する。global theme
  設定は削除しない。
- アプリを終了して再起動すると、保存済みMockを同じ種類・同じテーマ・同じ
  実空間位置へ復元する。古い配置データにtheme IDがない場合も、global設定または
  Orbital Analog fallbackを使用する。
- 各Mockは右Triggerのray/direct interactionに対応し、種類別の論理状態と
  hapticsを持つ。
- `ROOM ERROR: NoRoomsFound` の場合は Quest の Space Setup で部屋をスキャンして再起動する。
- `ROOM TRACKING LOST / RUN SPACE SETUP` の場合は、保存済みの部屋は見つかっているが現在の実空間へ位置合わせできていない。Metaボタンでアプリを閉じ、Questの「設定 → 物理空間 → スペース設定」で現在の部屋を再スキャンしてからアプリを再起動する。

ログと基本操作:

```sh
adb logcat -s Unity ActivityManager AndroidRuntime
adb shell am force-stop com.DefaultCompany.MatsuMotoMeterAR
adb shell monkey -p com.DefaultCompany.MatsuMotoMeterAR 1
```

## Definition of done for the first vertical slice

- パススルー背景で起動する。
- 壁・床・天井を区別し、不適合面では配置を確定できない。
- 6種類からMockを選択して1個配置し、アニメーションが72 Hz目標を妨げない。
- アプリを終了・再起動して同じ種類を同じ実空間位置に復元する。
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
