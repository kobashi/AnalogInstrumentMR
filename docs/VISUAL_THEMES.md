# Visual themes

## Requirement

配置する計器、操作レバー、スイッチ類には 3 種類のビジュアルテーマを用意し、配置済みオブジェクトを失わずに切り替え可能にする。

開発時の方向性ラベルは次のとおり。

| Working label | Original design direction |
| --- | --- |
| Steampunk | 真鍮、銅、鋳鉄、リベット、配管、アナログ圧力計、蒸気や機械振動 |
| Retro Space Opera | 黒い計器盤、円形メーター、密集した目盛り、原色ランプ、手描き感のある宇宙船操作卓 |
| Kinetic Mecha Lab | 大胆な警告色、工業的パネル分割、過剰なスケール感、鋭いシルエット、勢いのある作動演出 |

`Retro Space Opera` と `Kinetic Mecha Lab` は、一般的なレトロ宇宙オペラと
工業的メカ表現を、固有作品に依存しない独自のアートディレクションへ整理した
内部テーマ名とする。特定作品の固有形状、ロゴ、キャラクター、配色配置、
特徴的な意匠を複製しない。

## Architecture

操作機能と表示を分離する。

- `InstrumentController`: 値、状態、イベント、保存対象データを管理する。
- `ControlInteraction`: レバー角度、スイッチ状態、押下、掴み判定を管理する。
- `ThemeDefinition`: テーマ ID、共通 material、audio、VFX、animation profile を保持する ScriptableObject。
- `InstrumentVisualSet`: `instrumentTypeId` ごとのテーマ別 prefab を解決する。
- `ThemeService`: 現在テーマの選択、保存、runtime 切り替え、fallback を管理する。

物理 collider、interaction anchor、可動範囲、イベント名はテーマ間で共通の contract を使う。テーマ prefab は同じ attachment point 名と可動部 ID を実装する。

## Switching behavior

- 初期版は承認済み方針として、部屋全体の global theme を切り替える。
- 計器単位の override は初期リリースに含めないが、将来追加できるデータ構造にする。
- 切り替え時も Spatial Anchor、計器値、レバー位置、スイッチ状態を保持する。
- 短い transition を使用し、操作中のオブジェクトは即時交換せず操作終了後に切り替える。
- テーマアセットのロード失敗時は default theme を表示し、操作機能は維持する。

## Mock scope

初期 Mock では各テーマにつき、次の最小セットを灰色モデルと簡易 material で用意する。

1. 円形メーター
2. 縦型レバー
3. トグルスイッチ
4. ロータリーノブ
5. 押しボタン
6. 状態ランプ

本制作前に、同一のcontrollerとcollider contractで6種類×3テーマを生成できることを検証する。実寸とテーマ別の造形案は [Instrument greybox specification](GREYBOX_INSTRUMENT_SPEC.md) を参照する。

オブジェクトの全カタログ、prefab contract、制作ゲートは [Object catalog and preparation plan](OBJECT_CATALOG.md) に定義する。

### 2026-07-20 production status

- 3テーマ×6種類のBlender原本、FBX、preview、1K PBR maps、Unity prefabを制作済み。
- Forge Brass / Kinetic Safetyを含む全18 prefabで共通root/socket、pivot、
  envelope、collider分離をUnity EditMode testで確認済み（29 / 29 PASS）。
- Orbital AnalogはQuest 3で6種類の配置・復元と10分安定性を確認済み。
- Quest 3S実機検証はプロジェクト判断で見送る。
- global theme切り替えを左スティック左右へ実装済み。theme IDは独立した
  PlayerPrefs設定へ保存し、既存のanchor UUID／type ID schemaは変更しない。
- 配置済みオブジェクトはSpatial Anchor rootを維持したまま`VisualSocket`だけを
  交換する。Unity EditModeでroot pose、socket、Collider、kind不変性を確認済み。
- `concept.2`はQuest 3で3テーマ切り替え、配置済みvisual交換、Activity再起動後の
  Forge Brass／Spatial Anchor同時復元を確認済み。詳細は
  [Quest 3 theme switch and restore test](QUEST_THEME_SWITCH_TEST.md)を参照する。

### 2026-07-30 V6 production status

- 丸形メーター小・中・大を含む13種類×3テーマ、計39個のV6 Visual Prefabを導入済み。
- 全39 prefabで共通root/socket、可動target、0 Collider、0 realtime Light、
  種類別triangle上限、取付面クリアランスを検証済み。
- テーマ切り替えは左スティック左右へ割り当て、Spatial Anchor、配置姿勢、
  normalized value、接続を維持したまま`VisualSocket`だけを交換する。
- 最終Blender原本は
  `ArtSource/Blender/ThemeHardSurfaceV6/*/*_ProductionReady.blend`を正とする。

## Quest asset budget

- 1 テーマあたりの texture atlas と material 数に上限を設ける。
- material instance の乱立を避け、色や発光は property block または共通 parameter で制御する。
- 可動アニメーションは可能な限り軽量な transform animation とし、常時計算する Animator を増やしすぎない。
- LOD、mesh complexity、透明・発光・パーティクルの上限をテーマ間で揃える。
- 3 テーマを常駐させず、必要に応じて Addressables 等による遅延ロードを検討する。

## Acceptance criteria

- 13種類の部品が3テーマすべてで表示できる。
- runtime 切り替え後も配置位置と操作状態が変わらない。
- theme prefab が欠落しても default theme へ復帰し、操作不能にならない。
- テーマごとの collider と操作感が同等である。
- Quest 3 / 3S 上でテーマ切り替えによる長いフリーズや継続的な GC spike が発生しない。
