# Architecture

## Goal

Meta Quest のパススルー MR 上で、壁・床・天井に複数種類の計器を配置し、空間アンカーによって次回起動時にも復元する。

## Layers

- `Instruments`: 計器の見た目、状態、アニメーション。初期段階は回転・点滅・針振れなどの Mock。
- `Themes`: 計器、レバー、スイッチの機能から外観を分離し、テーマ単位で prefab、material、audio、animation profile を差し替える。
- `Placement`: レイキャスト結果、面法線、配置可能面のルール、プレビュー、確定操作。
- `InteractionModes`: 編集モードと操作モードの排他的な権限ポリシー。編集時だけ
  配置・削除、操作時だけ計器interactionを許可する。
- `Anchors`: 保存・読込・削除の抽象 API。Editor では `MockAnchorService`、Quest では Meta Spatial Anchor adapter を使う。
- `Platform/Meta`: Meta XR SDK、Scene API、Passthrough、Spatial Anchors への依存を閉じ込める（次マイルストーンで追加）。
- `App`: 起動シーケンス、権限、計器カタログ、永続 ID とアンカー ID の対応付け。

Unity Editor での Mock 動作が Meta SDK に依存しないことを設計上の境界とする。実機固有コードは asmdef を分離し、Android/Quest のみで有効化する。

## Meta dependency boundary

「Meta SDK 非依存」は、アプリ全体を汎用 XR API だけで実装するという意味ではない。計器、配置ルール、永続データモデルを Meta SDK の型から分離し、Quest 固有機能は `Platform/Meta` の adapter から積極的に利用する。

この境界により、Editor Mock とドメインテストは Meta SDK なしで動作しつつ、Quest ビルドでは次の機能を有効化できる。

| Capability | Quest implementation | App-facing boundary |
| --- | --- | --- |
| カラーパススルー | Unity OpenXR Meta | Passthrough bootstrap |
| 壁・床・天井の理解 | Meta Scene API / MRUK | `IRoomSceneProvider` |
| 配置位置の永続化 | Meta Spatial Anchors | `IAnchorService` |
| 現実物による遮蔽 | Environment Depth / OpenXR occlusion | Occlusion capability |
| 手・コントローラー操作 | OpenXR Input / Meta Interaction SDK | Input/interaction service |
| Quest カメラ画像 | Passthrough Camera API | Camera capability |
| 描画性能 | Vulkan、Multiview、Foveated Rendering、Dynamic Resolution | Render configuration |

Meta SDK の更新は adapter と専用 asmdef 内に閉じ込める。Meta 固有 API が必要な機能を汎用インターフェースへ無理に抽象化せず、capability check と feature flag によって Quest 3 / 3S の差や OS バージョン差を扱う。

## Quest performance policy

- Quest 3 / 3S のスタンドアロン APK を性能評価の基準とし、Mac 上の Editor 再生を性能判定には使わない。
- 初期基準は 72 Hz（13.9 ms/frame）。安定後に 90 Hz（11.1 ms/frame）を評価する。
- URP、ARM64、IL2CPP、Vulkan、Multiview を基本構成とする。
- Foveated Rendering と Dynamic Resolution は OpenXR feature と実機互換性を確認して有効化する。
- 計器の材質共有、描画バッチ、LOD、距離別更新頻度、アニメーション更新の集約を行う。
- Environment Depth、透明表現、動的ライト、パーティクルは GPU 計測結果に基づいて段階的に有効化する。
- Quest 3 / 3S と Horizon OS の capability を実行時に確認し、未対応機能では安全な fallback を提供する。

## Initial data model

計器定義は ScriptableObject とし、`instrumentTypeId`、対応面、Prefab、配置オフセット、アニメーション設定を保持する。配置インスタンスは独自 ID、計器種別、アンカー UUID、ローカル補正、バージョンを JSON に保存する。アンカーの pose とアプリデータを別管理し、片方が欠落した場合に安全に再配置できるようにする。

配置データにはテーマ固有 prefab の参照を保存せず、安定した `instrumentTypeId` と `themeId` を保存する。テーマ変更時はアンカー、操作状態、計器値を維持し、表示用 prefab と演出だけを再構築する。テーマアセットが欠落した場合は default theme へフォールバックする。

`concept.3`までは1個のUUID、type ID、論理値を3つの`PlayerPrefs`キーへ保存した。
`concept.4`では`IPlacementStore`配下のschema v1 JSON blobへ移行し、app固有の
`placementId`とMeta Spatial Anchor UUIDを分離する。旧UUIDは再アンカーやeraseをせず
そのまま移行し、互換キーはconcept.4実機確認まで保持する。Quest実装は
`MetaQuestAnchorService`を介してUUID一括load、個別localize、root bind、eraseを行う。

schema v2は`schemaVersion`、`revision`と最大48件のrecordを持つ。各recordは
`placementId`、`anchorId`、stable `instrumentTypeId`、surface、local offset、
normalized value、lifecycleを保存する。global themeは引き続き独立設定とする。
schema v1は読込時にv2へ移行して即時保存し、v2を理解しない旧buildによる
25件目以降の切り捨てを防ぐ。近接する配置は約2.75 m以内でAnchorを共有し、
複数recordが同じ`anchorId`を参照できる。
計器rootはSpatial Anchor専用rootの子に置き、整列・グループ移動の結果を
`localOffset`へ保存する。Anchorの約2.75 m範囲内は既存rootを維持し、範囲外へ
移動する場合は移動先の既存Anchorを再利用するか、新規Anchorへtransactionalに
付け替える。複数オブジェクトのレイアウト変更は1回のplacement document更新として
扱い、保存失敗時は元のAnchor参照とposeへrollbackする。
未知の新schemaは上書きせず、破損JSONは有効な旧データからのみ回復する。
旧データ移行成功後は完了マーカーを保存し、以後のJSON破損時に古い1件へ自動で
巻き戻さない。削除中断は`PendingDelete`として次回起動時にeraseを再開し、
一時的にlocalizeできないrecordは`Unavailable`として48個のactive枠から外して再試行する。

初期リリースでは theme は部屋単位の global 設定、配置数は 1 部屋最大 24 個、操作は controller 優先とする。theme 変更は短い transition を伴い、操作中のオブジェクトは操作終了後に visual を交換する。

## Milestones

1. Editor Mock: 3 面の仮想ルーム、3 種類の仮計器、配置プレビュー、削除、再起動相当の復元、テーマの runtime 切り替え。
2. Quest vertical slice: Passthrough、コントローラー/ハンド入力、実空間面への 1 種類配置、ローカル空間アンカー保存・復元。
3. Scene understanding: Scene API による壁・床・天井分類、複数計器、権限/未スキャン/アンカー欠落 UX。
4. Rich interaction: Environment Depth、ハンド操作、音響、状態連携、パーティクル、性能調整。
5. Productization: セーブ移行、テレメトリ、長時間・複数部屋テスト、配布ビルド。

## Risks

- SDK と Quest OS の互換性: Unity/Meta XR/端末 OS をチームで固定し、更新は専用ブランチで検証する。
- 空間スキャン未実施・権限拒否: オンボーディングと再試行導線を用意する。
- アンカーの位置ずれ・消失: 信頼状態を表示し、再配置と孤立データ回収を可能にする。
- モバイル GPU 負荷: 72/90 Hz のフレーム予算を早期に実機計測し、透明・動的ライト・パーティクルを制限する。
- テーマごとの性能差: collider と操作ロジックを共通化し、material slot、LOD、texture budget、animation cost の上限をテーマ間で揃える。
