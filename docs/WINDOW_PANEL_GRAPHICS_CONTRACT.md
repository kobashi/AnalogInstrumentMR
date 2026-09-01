# Window Panel Parametric Graphics Contract

Status: **WP1 / WP2 PASS; WP3 model candidates next**
Date: 2026-08-30

## Purpose

4テーマの`panel.window`を、針・vane・アナログ目盛を持つmeterから、最大4入力で
2D幾何学図形を変形・アニメーション表示するread-only instrumentへ置き換える。
テーマは筐体、display材、paletteだけを変え、信号処理、図形座標、更新budgetは共通化する。

この工程は既存の一般targetが行う平均合成を変更しない。Window PanelはTrend Monitorと同じ
display-only multi-input経路を使い、各入力を平均せず独立slotとして描画へ渡す。

## Runtime contract

- 入力数は0〜4。sourceは`InstrumentSignalPolicy.CanObserve`を満たす操作計器またはread-only meter。
- 各接続のDirect / Invert / Range / Thresholdを先に適用し、その結果を0〜1へclampしてslotへ渡す。
- slotは接続順ではなく、保存された`targetInputSlot` 0〜3で決定する。
- 同一panelのslot重複は保存時に拒否する。旧schema移行時だけ、接続の保存順に空きslotへ割り当てる。
- Window Panelは入力を平均した`NormalizedValue`で動かさない。既存の
  `SignalGraphEvaluator`によるAverageはmeter、lampなど従来targetに維持する。
- Window Panel自身の観測用出力はEnergy（slot 0）の変換後値とする。これにより既存どおり
  Trend Monitorから観測できるが、`CanSource`には追加せず一般targetや別Window Panelは駆動しない。
- connectionが一時的に解決できない場合は、そのslotだけneutralへ戻す。他slotは継続する。
- NaN / Infinityはinvalidとしてneutralへ戻し、displayの警告accentを点灯する。
- 0入力時は図形を消さず、低輝度のneutral previewを表示して故障と未接続を区別する。

## Fixed input semantics

全presetでslotの意味を固定し、themeや図形によって接続の意味を入れ替えない。

| Slot | Name | Input 0 | Input 1 | Effect |
| ---: | --- | ---: | ---: | --- |
| 0 | Energy | 0.45 | 0.95 | 図形全体の大きさ |
| 1 | Balance | 0.60 | 1.40 | X/Y aspect ratio |
| 2 | Phase | -180° | +180° | 位相と回転offset |
| 3 | Detail | 0.00 | 1.00 | 第2輪郭の分離量と発光強度 |

未接続slotのneutral値は順に`0.50 / 0.50 / 0.50 / 0.00`とする。

## Initial graphic presets

最初の実装は次の3種類に限定する。いずれも閉じた2D lineで、透明面、particle、3D mesh animationを
使用しない。

1. `Orbit`: 楕円軌道と第2軌道。Energyが半径、Balanceが長短軸比、Phaseが回転、Detailが軌道間隔。
2. `Rose`: 3葉rose curveと外周。Energyが半径、BalanceがX/Y比、Phaseが花弁位相、Detailが振幅。
3. `Lissajous`: 2:3固定比のLissajous curve。Energyが範囲、BalanceがX/Y比、Phaseが位相差、
   Detailが副輪郭とのoffset。

周波数や葉数を入力で連続変更するとtopologyの跳躍が起きるため、初期版ではpreset内の整数係数を固定する。
preset変更はEdit modeで明示操作し、接続値から自動切替しない。

## Display and model interface

- 各themeのproduction prefabは、現在の`vane_pivot`を廃止して`display_surface`を1つ持つ。
- `display_surface`の前面はinstrument local `+Z`、上はlocal `+Y`。前面は2 triangleの平面とする。
- usable rectangleはdisplay mesh boundsの90%以内とし、frame内側に最低5% marginを残す。
- graphic rootは実測したdisplay前面から`0.2 mm`だけ外側に置き、depth testを有効にする。
- 裏面からの透過表示を禁止する。render queueやsorting orderでframeを貫通させない。
- 4テーマで同じnormalized display coordinates `[-1, 1] × [-0.55, 0.55]`を使う。
- theme差はframe形状、texture、shared palette materialだけとし、formulaを分岐させない。

## Rendering budget

- project内実装だけを使い、新しいlibrary / package / Blender add-onは導入しない。
- 1 panelあたりgraphic用`MeshRenderer` 1、shared material 1、submesh 1。
- 最大2輪郭、各64 sample、合計256 vertex / 768 index以内。
- managed allocationはsteady stateで0 B/frame。固定配列、固定index buffer、再利用Meshを使う。
- source評価は既存signal tick、parameter反映は10 Hz上限。連続回転はTransform更新で行い、
  入力が変わらないframeにvertex bufferを再構築しない。
- shadow cast / receive、dynamic light、transparent blending、per-instance Material生成を禁止する。
- 色と警告状態は`MaterialPropertyBlock`で渡す。

## Persistence proposal

実装時にplacement documentをschema v6へ上げる。

- `SignalConnectionRecord.targetInputSlot`: `-1`をlegacy/auto、Window Panelでは0〜3。
- `PlacementRecord.windowPanelPreset`: `0=Orbit`、`1=Rose`、`2=Lissajous`。
- v1〜v5読込時は既存値と接続parameterを維持し、Window Panel着信接続だけ保存順で空きslotへ割り当てる。
- 未知presetは`Orbit`へfallbackする。未知の将来schemaは従来どおり上書きしない。
- theme切替、Room切替、anchor再bindではslotとpresetを維持する。

schema v6はこの文書の承認だけでは有効化しない。runtime prototype、migration test、UI操作を同じ変更単位で
実装してから`CurrentSchemaVersion`を更新する。

## Edit / Connect UX

- Trend Monitorと同じtarget-first接続をWindow Panelにも許可する。
- 接続確定時は最小番号の空きslotを割り当て、4入力時は追加を拒否する。
- connection editには現在のtransform parameterとは別に`SLOT A/B/C/D`を表示する。
- preset editとslot editのcontroller bindingは、既存A/B/X/Y操作との衝突audit後に確定する。
- statusにはpreset、接続数、選択connectionのslotを表示する。図形上へ常時数値textは描画しない。

## Implementation sequence

1. **WP0 — contract:** 本文書、schema migration方針、model interface、budgetを確定する。
2. **WP1 — isolated runtime prototype（technical / Quest visual PASS）:** greybox display plane上で
   3 preset、4 slot、invalid/missing表示、allocation testを実装した。production modelと保存schemaは
   変更していない。
3. **WP2 — persistence and UX（desktop / Quest PASS）:** schema v6 migration、slot assignment、
   preset/slot edit、保存復元、独立runtime評価を実装した。
4. **WP3 — 4-theme model candidates:** Opus 5へ`display_surface`契約を渡し、各theme固有frameを隔離生成する。
5. **WP4 — Gate B/C:** 固定画像、Unity構造検証、EditMode、candidate dependency 0、rollbackを確認して昇格する。
6. **WP5 — Quest:** 近接視認、裏面遮蔽、48 objectsをrelease Gate、64 objectsをstressとして測定する。

WP1とWP3はinterface確定後に並行可能だが、WP3成果物をproductionへ入れるのはWP2完了後とする。

## Acceptance gates

- Formula unit tests: 3 preset × min / neutral / max、有限値、bounds内、閉curve。
- Slot tests: 最大4、重複拒否、削除後再利用、保存順に依存しないruntime mapping。
- Migration tests: schema v1〜v5からv6へ既存placement、connection transform parameterを損失なく移行。
- Visual tests: 4 themes × 3 presets × neutral / min / max固定画像、frame clipping、裏面非表示。
- Runtime tests: theme/Room再構築後もpresetとslotを維持し、missing/invalidが他slotへ波及しない。
- Performance tests: Editor profilerは回帰検出に使い、合否はQuest 3の48 / 64 matrixで判断する。

## Explicitly out of scope for the first implementation

- Average / Sum / Min / Max / Priorityを選ぶ一般target合成UI
- user-authored formula、任意node graph、画像／動画入力、3D particle、透明glass
- safety limiter、latched trip、manual reset
- 外部graphics libraryまたは新しいUnity package

一般targetの合成戦略はPriority 4として別契約に残す。Window Panelの4 slotをその先行実装として使うが、
これを全targetのcomposition仕様へ暗黙に拡張しない。

## WP1 evidence

- Runtime: `WindowPanelGraphicGeometry`、`WindowPanelGraphicsPrototypeView`
- Fixed review: `Builds/Reports/window-panel-WP1-prototype-contact-sheet.png`
- Rows: Orbit / Rose / Lissajous
- Columns: all minimum / all neutral / all maximum / invalid Balance
- Geometry: 2 contours、64 samples、256 vertices、768 indices
- Managed allocation: geometry 100 rebuilds after warmup = 0 B
- Unity EditMode: 173 / 173 PASS
- Image review correction: ribbon windingをdisplay正面へ修正し、Orbit Phaseを全体2D回転へ変更
- Production prefab / FBX / placement schema / Connect UI: unchanged

## WP2 desktop evidence

- Persistence: schema v6、`targetInputSlot` A〜D、`windowPanelPreset`
- Migration: v1〜v5をv6へ移行。v5 Range／Threshold parameterを保持
- Runtime: Window Panel着信を従来Averageから除外し、4 slotを独立評価。Energyだけを観測用出力へ反映
- Connect UX: target-first、空きslot自動割当、4本上限、右stick左右でslot、右stick上下でpreset
- Save/restore: slot、presetともplacement JSONへ保存し、Room／theme再構築後もrecordから復元
- Unity EditMode: 181 / 181 PASS
- Production prefab / FBX / graphic view connection: unchanged（WP3 / WP4まで保留）
- Quest UX: preset、slot、Range／Threshold回帰、再起動復元をPASS。40→38 recordsはユーザーの意図した削除
