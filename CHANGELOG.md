# Changelog

このプロジェクトの重要な変更を記録する。
バージョン番号は [Semantic Versioning](https://semver.org/) に従い、
コンセプト確認期間は prerelease identifier を付ける。

## [Unreleased]

## [0.1.0-concept.5-perfgate] - 2026-07-23

このsource releaseにはconcept.3からconcept.5までの操作、複数配置、
Spatial Anchor復元、性能gateの変更をまとめて収録する。公式APKは配布しない。

### Added

- 円形メーター、レバー、トグル、ロータリーノブ、押しボタン、状態灯のPrimitive Mock
- 右スティック左右によるMock選択と種類別の配置面制約
- 選択したtype IDの保存とSpatial Anchor再起動時の種類別復元
- Mockカタログのtype ID、循環選択、配置面に対するEditModeテスト
- Unity Editor内から全EditModeテストを実行する開発メニュー
- 3テーマ×6種類のBlender原本、FBX、1K PBR texture、Unity prefab
- 右コントローラーray/direct操作、haptics、種類別の論理状態保存
- schema v1 JSONによる最大24件の配置保存、legacy移行、個別削除
- Meta Spatial Anchor adapterと複数Anchorのlocalize / restore
- 12 / 24 / 40個のsynthetic性能scenarioとQuest自動計測script

### Changed

- 新規アンカーの保存成功後に旧アンカーを削除し、保存失敗時に既存配置を維持する
- 配置済みroot poseとAnchorを維持したまま`VisualSocket`以下のthemeを交換する
- 性能計測中のHUD／heartbeat allocationを停止し、72 Hzを要求・検証する

### Validated

- Unity EditMode 62 / 62
- Quest 3でlegacy移行、複数配置、個別削除、3 Anchor再起動復元
- Quest 3 synthetic 24個・10分72 Hz性能gate
- Quest 3 synthetic 40個・10分stress
- 3テーマ性能smoke、app GPU p95 2.302–2.317 ms
- 通常runtime・3 Anchor復元と目視screen-tear確認
- Quest 3通常runtimeの最終ユーザー受入（`問題なし`、PASS）

### Deferred

- Quest 3S実機検証（プロジェクト判断）
- 実Spatial Anchor 24個の厳密なmatrix試験（任意の拡張検証、release blockerではない）

## [0.1.0-concept.2] - 2026-07-20

### Added

- Forge Brass、Orbital Analog、Kinetic Safetyの3テーマ×6種類のBlender/FBX、
  1K PBR maps、Unity prefab
- 右スティック上下によるglobal theme切り替え
- global theme IDのPlayerPrefs保存、未知IDのOrbital Analog fallback
- 配置済みSpatial Anchor rootを維持した`VisualSocket`のみのtheme差し替え
- Blender/FBX round-trip validatorと全3テーマのUnity contract test

### Validated

- Blender source／FBX: 残り2テーマ12 / 12 PASS
- Unity EditMode: 32 / 32 PASS
- Orbital Analog: Quest 3で6種類の配置・復元、10分安定性PASS
- `concept.2` APK: ARM64、IL2CPP、Vulkan、API 32 / 34、v2署名、
  non-debuggable manifest
- Quest 3で3テーマpreview切り替え、配置済みvisual交換、global theme保存、
  Activity再起動後のForge Brass／Spatial Anchor同時復元
- 復元後72 Hz、Unity／Android／Spatial Anchor fatal error 0
- `concept.2`のQuest 3 10分連続試験：process生存、CPU 26.9–38.4%、
  PSS +1,609 KB、swap変化なし、72 Hz、fatal error 0

### Deferred

- Quest 3S実機検証（プロジェクト判断）

## [0.1.0-concept.1] - 2026-07-17

### Added

- Unity `6000.3.19f1` とAndroid Build SupportによるQuest開発基盤
- Meta XR Core SDK、MRUK、Interaction SDK Essentials `203.0.0`
- OpenXR、Touch controller profiles、foveation構成
- Quest 3のパススルー表示
- 壁・床・天井への円形Mockメーター配置
- ローカルSpatial Anchorの保存と再起動後復元
- controller beam、B長押し、照準+Trigger長押しによる開発用終了操作
- Quest向けURP `17.3.0` assetとruntime material bridge
- EditMode testとbuild前material validator
- USB/ADB、MRUK、URP移行を含む開発ドキュメント

### Validated

- Built-in版でcontroller入力、面配置、Spatial Anchor保存・復元
- URP版でQuest 3へのinstall/start、両眼パススルー、HUD、MRUK `ROOM READY`
- URP版でピンクmaterial、黒画面、片眼欠落がないこと
- URP版でcontroller入力、照準、面配置、削除、アプリ内終了
- URP版でSpatial Anchor保存後、Activity終了・再起動による同位置復元
- URP版の短時間計測で72/72 FPS、stale frame 0

### Known limitations

- 10分連続性能ゲートは未実施
- Quest 3Sは未検証
- 正式package ID、署名、ストア配布設定は未確定
- 配置できる計器は1個のMockのみ
