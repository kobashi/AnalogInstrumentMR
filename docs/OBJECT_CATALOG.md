# Object catalog and preparation plan

## Scope

計器、操作部品、表示部品を機能と外観に分離し、MRUK Plane／Volumeの任意面への
配置と3テーマの切り替えを検証する。共通contractを先に固定し、テーマ別Visualを
交換してもSpatial Anchor、操作状態、接続を維持する。

## Implemented catalog

右スティック左右は次の順で移動し、右スティック上下はカテゴリ先頭へジャンプする。

| Category | Order | Type ID |
| --- | ---: | --- |
| Meters | 1 | `meter.round` |
| Meters | 2 | `meter.round.medium` |
| Meters | 3 | `meter.round.large` |
| Meters | 4 | `meter.window` |
| Indicators | 5 | `indicator.lamp` |
| Indicators | 6 | `indicator.status` |
| Indicators | 7 | `panel.window` |
| Switches | 8 | `control.toggle` |
| Switches | 9 | `control.button` |
| Switches | 10 | `control.rotary` |
| Motion | 11 | `control.lever` |
| Motion | 12 | `control.throttle` |
| Motion | 13 | `control.power_slider` |

全13種類を3テーマで実装済みで、すべてPlane／Volumeの任意面へ配置できる。
Mesh raycastは配置対象にしない。

## Historical plan

### P0: Interaction and theme prototype

最初に制作する必須セット。すべて灰色モデル、3 テーマの簡易 skin、保存・復元に対応する。

| ID | Object | Surfaces | Interaction/state | Mock motion |
| --- | --- | --- | --- | --- |
| `meter.round` | 円形アナログメーター | Wall / Floor / Ceiling | 読取専用、0–1 value | 操作モード中の針微動 |
| `control.lever` | 縦型レバー | Wall / Floor | Triggerまたは接触Grip＋上下motion、5段階 | 面に垂直な片側48° sweep、5 detents |
| `control.toggle` | トグルスイッチ | Wall / Floor / Ceiling | On / Off | ノブ反転、クリック |
| `control.rotary` | ロータリーノブ | Wall / Floor | 連続値または段階値 | 回転、detent feedback |
| `control.button` | 押しボタン | Wall / Floor / Ceiling | 両手接触またはビーム＋TriggerのMomentary | 押下中の沈み込み、解放時復帰 |
| `indicator.lamp` | 単色状態ランプ | Wall / Floor / Ceiling | On / Off | 単色発光 |
| `indicator.status` | 多段階状態LED | Wall / Floor / Ceiling | Off / Safe / Warn / Danger | 緑・橙・赤の状態発光 |
| `control.throttle` | スロットルレバー | Wall / Floor | Triggerまたは接触Grip＋アークmotion、6段階 | engine quadrant型の片側70° sweep |
| `control.power_slider` | パワースライダー | Wall / Floor | Triggerまたは接触Grip＋上下motion、11段階 | 上下0.18 m travel |

P0 の目的は造形品質ではなく、同じ logic/collider/state に対してテーマ visual だけを安全に交換できることの検証とする。

### Initial greybox milestone

2026-07-17時点の初期マイルストーンでは、P0の6種類をUnity Primitiveから
runtime生成した。以下は当時の記録で、現在の操作は前節を正とする。

- 配置対象は `METERS / INDICATORS / SWITCHES / MOTION` の機能カテゴリ順に並べる。
  右スティック左右で種類、右スティック上下でカテゴリ先頭、左スティック左右で
  テーマを切り替え、緑色previewで形状を確認する。
- `A`で選択中の1種類を配置し、type IDとSpatial Anchor UUIDを保存する。
- Activity終了・再起動後は、保存したtype IDから同じ種類を復元する。
- 当初は種類別に配置面を制限していたが、現在は全種類を任意面へ配置できる。
- 初期自動アニメーションは、現在の操作モード・接続駆動へ置き換えた。

### P1: Instrument panel vertical slice

| ID | Object | Surfaces | Interaction/state | Mock motion |
| --- | --- | --- | --- | --- |
| `meter.linear` | 縦/横バー計器 | Wall / Floor | 表示のみ、0–1 value | バー量と色変化 |
| `display.scope` | 波形ディスプレイ | Wall / Floor | mode selection | スクロール波形、走査線 |
| `panel.compact` | 4 部品用コンパクトパネル | Wall | 子部品の集合 | 通電シーケンス |
| `meter.window` | 窓枠サイズ大型メーター | Wall / Floor / Ceiling | 表示値、0–1 value | 大型needle |
| `panel.window` | 窓枠サイズ宇宙船パネル | Wall / Floor / Ceiling | status value | 大型status vane |

### P2: Room-scale atmosphere

| ID | Object | Surfaces | Role | Mock motion |
| --- | --- | --- | --- | --- |
| `machine.floor-console` | 自立コンソール | Floor | 複数計器の操作台 | メーター・ランプ連動 |
| `machine.power-unit` | 動力ユニット | Floor / Wall | 室内の機能中枢 | ローター、脈動、熱表現 |
| `fixture.ceiling-sensor` | 天井センサー | Ceiling | 周囲走査 | 首振り、走査光 |
| `fixture.vent` | 換気/冷却ユニット | Wall / Ceiling | 背景機械 | ファン回転、ルーバー動作 |
| `fixture.conduit` | 配管・ケーブル導管 | Wall / Floor / Ceiling | オブジェクト間の視覚接続 | 流量ランプ、微振動 |
| `indicator.beacon` | 警告ビーコン | Wall / Floor / Ceiling | 警告状態の共有 | 回転/パルス発光 |

P2 の導管は空間アンカー間を自動接続する機能を将来追加できるが、初期版は単独配置オブジェクトとして扱う。

## Common prefab contract

すべての配置オブジェクトは次の共通構造を持つ。

```text
InstrumentRoot
├── MountOrigin
├── Logic
├── Interaction
│   ├── InteractionCollider
│   └── GrabOrPokeOrigin
├── VisualSocket
│   └── ThemeVisual (runtime instance)
├── OcclusionProxy
├── LabelSocket
├── AudioSocket
└── VfxSocket
```

- `InstrumentRoot`: Spatial Anchor と保存 ID に対応する。不用意に scale しない。
- `MountOrigin`: 壁・床・天井の接触面。ローカル +Z を面から外向きの forward とする。
- `Logic`: 値、状態遷移、イベントを保持し、theme asset を参照しない。
- `Interaction`: collider と操作範囲を保持する。テーマ間で形状と操作感を揃える。
- `VisualSocket`: `themeId + instrumentTypeId` で解決した visual prefab を生成する。
- `OcclusionProxy`: 現実空間との遮蔽・選択判定に使う単純形状。theme visual と分離する。
- Socket 群: ラベル、音、VFX の位置をテーマ側が上書きできるようにする。

テーマ visual は共通の movable part ID を `ThemeVisualManifest` の明示的な Transform 参照として公開する。名前による runtime 検索は行わず、欠落を Editor 検証で検出する。

- `needle`
- `handle`
- `switch`
- `knob`
- `button`
- `indicator`
- `screen`

P0の実寸、共通階層、3テーマ案、Quest性能上限は
[Instrument greybox specification](GREYBOX_INSTRUMENT_SPEC.md) を正とする。

## Data assets

次の ScriptableObject を準備する。

| Asset | Contents |
| --- | --- |
| `InstrumentDefinition` | type ID、表示名、許可面、寸法、mount offset、logic prefab、状態 schema |
| `ThemeDefinition` | theme ID、default materials、audio/VFX profile、fallback theme |
| `InstrumentVisualSet` | type ID と theme ID から visual prefab を解決する表 |
| `ThemeVisualManifest` | 針、ハンドル、スイッチ、ランプ、画面等の可動部参照 |
| `InteractionProfile` | 可動範囲、snap/detent、haptics、操作方式 |
| `AnimationProfile` | 回転速度、針応答、点滅周期、idle variation |
| `AssetBudgetProfile` | LOD、triangle、material、texture、animation cost の上限 |

## Folder and naming convention

```text
Assets/MatsuMotoMeterAR/
├── Runtime/
│   ├── Instruments/
│   ├── Interaction/
│   ├── Themes/
│   └── Placement/
├── Content/
│   ├── Shared/
│   ├── Themes/
│   │   ├── Steampunk/
│   │   ├── RetroSpaceOpera/
│   │   └── KineticMechaLab/
│   └── InstrumentDefinitions/
└── Tests/
```

命名例:

- `PF_Logic_MeterRound`
- `PF_Visual_MeterRound_Steampunk`
- `MAT_Steampunk_Brass`
- `SO_Instrument_MeterRound`
- `SO_Theme_Steampunk`

## Preparation workflow

### Gate 1: Contract greybox

1. P0 の 6 部品を Unity primitive で作る。
2. 実寸メートル単位、pivot、`MountOrigin`、操作 collider を統一する。
3. Mock state と animation を logic 側から動かす。
4. 壁・床・天井の Mock Room で配置制約を検証する。
5. Play Mode を止めても配置データを復元できるようにする。

### Gate 2: Theme interchange

1. P0 それぞれに 3 つの簡易 visual prefab を作る。
2. global theme を runtime で切り替える。
3. visual の交換中も値、スイッチ状態、レバー位置を保持する。
4. theme asset 欠落時の default fallback をテストする。

### Gate 3: Quest interaction

1. コントローラー ray と direct interaction で P0 を操作する。
2. 手の追跡は controller 操作成立後に追加する。
3. Passthrough 上で実寸、可読距離、操作 collider を確認する。
4. 12、24、40 オブジェクト時の 72 Hz、p95 CPU/GPU time、GC allocation、draw call、発光/透明コストを実機計測する。

### Gate 4: Art production

1. P0 の theme style sheet と material atlas を先に承認する。
2. high-poly/low-poly、UV、bake、LOD、collision proxy を制作する。
3. P1、P2 の順でカタログを増やす。
4. 特定作品の固有デザインを複製せず、各 working label を独自の形状言語へ発展させる。

## Initial Quest budgets

実機計測前の暫定上限。P0 の結果から更新する。

| Item | P0 target |
| --- | --- |
| Triangles | 小型部品 5k 以下、複合パネル 25k 以下 |
| Materials | 小型部品 1–2、複合パネル 4 以下 |
| Texture | 原則 1K atlas、近接必須部のみ 2K |
| Lights | 計器ごとの real-time light は使用しない |
| Emission | shared material + parameter 制御 |
| Transparency | 画面・ガラスの必要箇所だけに限定 |
| Animation | 常時 Animator を避け、共有 update または shader animation を検討 |
| LOD | P1/P2 の大型・複雑物は LOD を必須とする |

代表シーンは 72 Hz（13.9 ms/frame）を必須基準とし、OS compositor 等の余裕を確保するためアプリ側の p95 CPU/GPU time は各 11 ms 以下を暫定目標とする。通常動作中の managed allocation は 0 B/frame に近づける。

## Surface and safety rules

- 天井配置はセンサー、状態灯、ファン等の表示・演出中心とし、頻繁な直接操作を要求しない。
- 床配置は歩行障害に見える位置や実在家具との重なりを避け、ユーザーの足元直近には確定できない clearance を設ける。
- 壁操作部は想定到達範囲と視認距離を検査し、高すぎる/低すぎる位置には警告を出す。
- 各 `InstrumentDefinition` に footprint、壁からの突出量、操作 clearance を持たせ、配置 preview で占有範囲を示す。
- Guardian/Boundary を妨げず、緊急時にテーマや配置物を一括非表示・削除できる導線を用意する。

## Acceptance criteria for asset preparation

- P0 の 6 部品に stable type ID が割り当てられている。
- 3 テーマ × 6 部品の visualが同じprefab contractを満たす。
- 壁・床・天井の許可ルールと mount orientation が自動テスト可能である。
- visual を交換しても logic、Spatial Anchor、操作状態が失われない。
- collision proxy と visual mesh が分離され、テーマ間の操作感が同等である。
- 可動部 slot、LOD、bounds、surface contract の欠落を Editor 検証で検出できる。
- Quest 3 / 3S の 72 Hz 実機計測結果を記録できる。

## Approved initial decisions

2026-07-13 に次の初期方針を承認済み。

| Decision | Initial release policy |
| --- | --- |
| Theme scope | 部屋全体の global theme。計器単位 override は将来拡張とする |
| Primary interaction | Controller ray / direct controller を優先し、hand tracking は後続フェーズで追加する |
| Object capacity | 1 部屋あたり最大 24 個を初期保証範囲とする |
| Catalog order | P0 → P1 → P2 の順で制作する |
| Theme switching | 短い transition を挟み、操作中の部品は操作終了後に交換する |

性能試験では保証範囲の 24 個に加え、余裕度確認として 12 個と 40 個のケースも測定する。計器同士の機能連動は P1 の compact panel から導入する。
