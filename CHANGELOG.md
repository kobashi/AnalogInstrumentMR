# Changelog

このプロジェクトの重要な変更を記録する。
バージョン番号は [Semantic Versioning](https://semver.org/) に従い、
コンセプト確認期間は prerelease identifier を付ける。

## [Unreleased]

### Added

- 接続単位のRange入力min / max・出力min / max、およびThreshold値・ABOVE / BELOWを
  Quest内で編集、preview、取消、保存・復元できるparameter editor。保存schemaをv5へ更新し、
  v1〜v4接続は従来と同じ既定値へ移行
- 第4テーマ`Machined Ergonomics`。受入済み14機種のproduction model、1K atlas、
  opaque／emissive／Trend Monitor暗色表示面material、独立prefabを追加し、
  theme ID `machined-ergonomics`として通常runtimeへ登録
- 候補領域からproductionへmesh／material参照を付け替え、candidate依存0を検査する
  idempotentなTheme 4 production promoterと専用Quest Gate APK builder
- 独立配置できる`monitor.trend`計器。最大4接続を色分けした現在値と32 sampleの
  短時間trendで同時表示し、通常の操作入力に加えて読取専用meterの出力も観測できる。
  信号評価とは分離した5 Hz更新、共有material、固定長bufferにより
  steady-stateのper-frame allocationを避ける
- manifest駆動のcandidate隔離staging、構造・motion・固定画像・Quest証跡を束ねる
  Gate C readiness検証
- Quest 48配置gate／64配置stressを同じ設定から実行するperformance matrix
- 承認済みM2n8 Kinetic Safety MeterRound／Medium／LargeのBlender原本、FBX、
  比較画像、検証report

### Changed

- Trend Monitorを先に選んでから入力元を選ぶtarget-first接続を追加。meter出力は
  Trend Monitorでの観測専用とし、既存計器への一般的な信号sourceには拡張しない
- Orbital Analog／Forge BrassのMeterMedium／MeterLargeから、前面カバー上に重複していた
  `secondary_scale_*`を除去。文字盤側の主目盛、針、可動範囲を維持したまま、
  二重目盛と奥行き競合を解消
- Gate Cを通過したmanifest内の選択モデルだけをproductionへ昇格し、元FBX GUID、
  prefab参照、production materialを維持してcandidate依存0を検証するpromoterを追加
- Blender authoring pipelineを`5.2.x`へ移行。プロジェクト専用launcher、V6生成前の
  Python API／EEVEE／Legacy FBX preflight、非破壊smoke test、生成reportの
  Blender／Python／FBX exporter provenanceを追加。Blender 5.2のEEVEE engine ID
  `BLENDER_EEVEE`へpreview生成を更新
- Kinetic Safetyの3サイズmeterをM2n8形状へ更新し、針の表示範囲を±115°へ拡大。
  active FBX／prefab GUIDを維持し、candidate依存をproductionから分離

### Validated

- 接続parameter編集はUnity EditMode 162 / 162とQuest 3でRange／Threshold編集、
  preview、保存をPASS
- Unity EditMode 154 / 154、Machined Ergonomics production prefab 14 / 14、
  installed active visual prefab 53 / 53
- 4テーマmotion 16 / 16、signal visual 8 / 8、candidate dependency 0
- M2n8 Gate C readiness 16 / 16
- Quest 3の48配置gate／64配置stress（各10分、baseline-relative）と
  M2n8 production smoke
- Machined Ergonomics productionの48配置30分stability Gateと、ユーザー判断で
  短縮した64配置10分stress。48はGC 0／delayed 0.017%、64はGC 15 `OBSERVE`／
  delayed 0.047%、両runともfatal・thermal stop・frame allocation 0
- MeterGlassScale G1はGate C readiness 18 / 18、対象4モデルのmotion 4 / 4
  （各230°）、Unity EditMode 154 / 154、Quest 3での4モデル視覚確認、48配置gate、
  64配置stress、production APK smokeをPASS

## [0.2.0-concept.1] - 2026-07-30

### Added

- Operation / Edit / Connectの3モードと、接続タイプ別に色分けした
  Direct / Invert / Range / Threshold接続
- schema v4によるRoomごと最大48配置・全Room合計192配置・192接続の保存、
  Room UUID所属、旧schemaからの移行
- アプリ実行中のMRUK Current Room変更検出。1秒間の安定確認後に旧Roomの表示と
  Colliderをアンロードし、移動先RoomのPlane／VolumeとSpatial Anchorを復元
- 丸形メーター中・大を含む13種類、3テーマ、計39個のV6 visual prefab
- PlaneとVolumeの任意面への配置、面wireframe、ray hit安定化
- 機能カテゴリ順の追加オブジェクト選択と右スティック上下のカテゴリジャンプ
- 操作モードの左右コントローラービーム／Trigger。左右別の状態管理により、
  2つの計器を両手で同時操作可能
- レバー／スライダーの接触Grip＋上下motion、スロットルの接触Grip＋
  アークmotion操作とdetent haptics、Grip解放時の状態保存
- 押しボタンの左右コントローラー接触押下と、読取専用メーター／大型パネルの
  操作モード限定の非同期微動アニメーション
- 第1選択の位置を起点に、整列前の空間的な並び順を維持する横・縦整列と、
  右スティック方向へ選択集合を回転する配置操作
- `X`でOperation → Edit → Connectを循環し、各モードの入力を排他的にする
- Operationモードの左スティック押し込み2秒長押しによる、`X`モード切替の
  ロック／解除
- 重なりを避ける自動配置、同一面の横一列整列、相対配置を保つグループ移動
- Spatial Anchor専用rootと永続化済み`localOffset`による編集レイアウトの再起動復元
- 壁・床・天井へ置ける窓枠サイズの`meter.window`と`panel.window`。
  3テーマの形状指針を踏襲した宇宙船向けruntime greybox
- 3テーマ対応のスロットルとパワースライダーのBlender原本、FBX、Unity Prefab。
  それぞれ`throttle_pivot`と`slider_travel`へ多段階motionを接続
- 編集移動中に新規配置previewを置き換える移動先target marker。壁・床・天井を
  またぐ移動後の外形と向きを表示し、面適合・重複を緑／赤とHUD理由で事前表示。
  Aで確定、Xで取消
- 3テーマ×4可動機種の全段階についてRenderer移動量、軸、取付面クリアランスを
  検査し、コンタクトシートを生成するUnity Editor監査
- Editモードの左スティック押し込み2秒長押しによる安全終了。
  保存中はActivity終了を保留

### Fixed

- スロットルのGrip開始判定を計器全体のColliderから、可動pivotへ追従する
  palm grip専用boxへ変更し、見た目のグリップとコントローラー反応位置のずれを修正
- 押しボタンを接触操作に加えて左右ビーム＋Triggerでも押下可能に修正
- 大型パネル、大型メーター、多段階警告LEDの配置previewが一律緑色になる
  material上書きを廃止し、テーマ固有配色を保持
- controller grip pose由来だったビームをOpenXR aim poseへ分離し、
  Quest HOME相当の照準角度・原点へ修正。Grip接触判定は物理poseを維持
- スロットルを左右fork、幅広palm grip、quadrant gate、6段階目盛を持つ
  航空機／船舶型エンジン出力レバーへ再設計し、Grip操作を直線移動から
  pivot中心の実アーク角入力へ変更
- トグルのpivotをbase上のauthoring位置に維持し、レバー・トグル・スロットルへ
  初期角offsetを適用。local X軸の片側sweepで可動面を取付面に垂直にし、
  初期状態と端位置でbaseへめり込む問題を修正
- HUD文字サイズを従来の50%へ縮小
- 配置済みオブジェクト照準中は新規previewと追加を停止し、複数選択中は
  追加・削除・種類変更を無効化。第1選択を太いシアン枠で表示
- 配置・整列の重複marginを外形に沿う2 mmへ縮小し、整列gapを12 mmに分離。
  第1選択の位置を固定した選択順整列へ変更し、外形は離れているのに
  margin判定で整列が失敗する問題を修正
- FBX可動ノードへ実行時motion proxyを挿入し、レバーの値だけ変化して
  3Dハンドルが追従しない問題を修正
- トグルの初期位置でbaseへめり込む問題を修正
- Metaメニューから復帰した際にOpenXR controller pose actionを再同期し、
  描画直前にも姿勢を更新してビームと実コントローラーのずれを修正
- FBX可動プロキシの座標をvisual root基準へ統一し、レバー、トグル、
  スロットル、パワースライダーの回転軸・移動軸を修正
- schema v4 placement store、旧schema自動移行、Roomごと最大48配置、
  全Room合計最大192配置、最大192接続、
  16 Anchor単位のbatch load、約2.75 m圏内の配置によるSpatial Anchor共有
- 右Triggerによる複数選択と選択枠、横・縦の等間隔整列、選択集合の移動。
  選択中の`B`は選択解除、`Y`は将来用の予約入力
- Anchor共有範囲外へのグループ移動で、近傍Anchor再利用または新規Anchor作成を
  行うtransactionalな自動再アンカーと保存失敗時rollback
- `control.lever`の操作を二値切替から5ノッチへ拡張。隣接ノッチ移動、端での
  方向反転、detent HUD、保存値の最寄りノッチ正規化
- レバーの可動域を片側48°へ調整し、端位置を含むInteractionColliderを
  幅0.24 mへ拡張
- ON/OFF専用`indicator.lamp`を維持しながら、`OFF / SAFE / WARN / DANGER`を
  消灯・緑・橙・赤で循環表示する`indicator.status`を9番目の配置種別として追加
- `control.throttle`へ6ノッチ状態、保存・復元、`throttle_pivot` motion contractと
  3テーマの完成モデルを実装
- `control.power_slider`へOFFからMAXまでの11ノッチ、0.18 mの
  `slider_travel` contract、保存・復元、3テーマの完成モデルを実装

### Validated

- Unity EditMode 99 / 99
- active V6 visual prefab 39 / 39
- Quest 3への非Development APK build / install

### Known limitations

- 48配置gateと64配置stressはQuest実機で長時間性能未再検証
- Quest 3Sは未検証
- ConnectのRangeは0.2–0.8、Thresholdは0.5固定、複数入力は平均合成
- モニターの数値／グラフ／図形表示は今後の実装対象

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
