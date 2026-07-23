# Instrument greybox specification

## Purpose

円形メーター、レバー、トグル、ロータリーノブ、押しボタン、状態灯を、3テーマで共通利用できる制作基準として定義する。greyboxの目的は造形の完成ではなく、実寸、アンカー、操作範囲、可動軸、描画予算を固定し、テーマ制作で配置・復元や操作感を変えないことにある。

## Coordinate and hierarchy contract

- 単位は1 Unity unit = 1 m。
- `InstrumentRoot` のworld poseをSpatial Anchorのposeと一致させ、scaleは常に`(1, 1, 1)`とする。
- mount面はrootのlocal Z = 0、local +Zは実空間面から外向きとする。
- 既存の15 mm surface offsetは配置側の責務とし、モデルへ追加offsetを焼き込まない。
- visual、theme、animationを変更してもroot、`InteractionCollider`、type IDを交換しない。

```text
InstrumentRoot (Spatial Anchor)
├── MountOrigin
├── Logic
├── Interaction
│   └── InteractionCollider
├── VisualSocket
├── OcclusionProxy
├── LabelSocket
├── AudioSocket
└── VfxSocket
```

Primitive由来のColliderは削除し、通常モデルは`InteractionCollider`を1個だけ持つ。配置previewはColliderを持たない。

## P0 dimensions and motion

寸法はneutral poseでの、mount面に平行なX/Yと面からの突出Zの最大
visual envelope。装飾はこの範囲内に収める。可動部のsweepは下記Motionを
基準に`InteractionCollider`側で包含し、visual meshへColliderを追加しない。

| Type ID | X × Y × Z (m) | Motion | Surfaces |
| --- | --- | --- | --- |
| `meter.round` | 0.140 × 0.140 × 0.064 | needle ±55° | Wall / Floor / Ceiling |
| `control.lever` | 0.180 × 0.256 × 0.100 | handle ±32° | Wall / Floor |
| `control.toggle` | 0.120 × 0.170 × 0.064 | switch ±28° | Wall / Floor / Ceiling |
| `control.rotary` | 0.150 × 0.150 × 0.102 | continuous rotation | Wall / Floor |
| `control.button` | 0.130 × 0.130 × 0.090 | travel 0.014 m | Wall / Floor / Ceiling |
| `indicator.lamp` | 0.140 × 0.110 × 0.082 | pulse only | Wall / Floor / Ceiling |

可動部の機能IDは`needle`、`handle`、`switch`、`knob`、`button`、`indicator`とする。本制作prefabでは名前検索ではなくmanifestの明示参照へ移行する。

## Three design directions

テーマ差は`VisualSocket`以下のsilhouette detail、palette、label、audio、VFXに限定する。共通envelope、pivot、可動域、Colliderは変更しない。

| Theme ID | Direction | Shape and material proposal |
| --- | --- | --- |
| `forge-brass` | Forge Brass | 丸み、段付きrim、鋳鉄base、真鍮・銅accent。meterは二重bezel、leverは球grip、lampは簡略化したcageを使う。 |
| `orbital-analog` | Orbital Analog | 薄い黒panel、明るいdial、細いshaft、原色indicator。密度感はtick/label atlasで作り、greyboxでは面構成を増やさない。 |
| `kinetic-safety` | Kinetic Safety | 面取りguard、太い操作部、高コントラストのorange/yellow warning accent。角形shroud内に共通可動部を収める。 |

既存作品の固有ロゴ、象徴的形状、特徴的な配色配置は使用しない。初期defaultは`orbital-analog`とし、theme IDが欠落・未知の場合も同themeへfallbackする。

## Quest 3 / 3S budget

Quest 3Sを下限とし、両端末に同じ合格基準を適用する。

| Item | Greybox gate | Final P0 ceiling |
| --- | --- | --- |
| Triangles / object | 1.5k以下 | 5k以下 |
| Renderers / object | 3以下、meterのみ4 | 4以下 |
| Materials / object | shared opaque 1 | shared opaque + emissiveの2以下 |
| Textures / theme | none | 1K atlas 1枚、2Kは近接必須時のみ |
| Realtime lights | 0 | 0 |
| Transparency | 0 | lens/glassの必要箇所だけ |
| Managed allocation | steady state 0 B/frame | steady state 0 B/frame |

- 初期保証は1部屋24個。12 / 24 / 40個で余裕度を測る。
- 72 Hzの13.9 ms/frameに対し、アプリ側p95 CPU/GPU timeは各11 ms以下を暫定合格値とする。
- 24個時のcontent目安は120k triangles以下、renderer submissionsは通常72以下、meter混在時も96以下とする。
- 色、preview、点灯は共有materialと`MaterialPropertyBlock`で制御する。
- 常時Animatorと計器ごとのreal-time lightを使わない。`MockInstrumentMotion`は
  event-drivenとし、per-object `Update`を持たせない。
- Quest 3の40個・10分stressではCPU utilization p95 33%、app GPU p95 2.314 ms、
  skipped / stale / shader hitch 0だった。24個比の有意な悪化はなく、共有schedulerは
  不要と判断する。

## Gate 1 acceptance

- 6種類×3テーマでroot pose、unit scale、共通socket階層、共通Colliderが一致する。
- stable type IDとenum順を維持し、未知type IDは旧配置互換のため円形メーターへfallbackする。
- visual primitiveにColliderがなく、previewにはColliderがない。
- renderer、shared material、triangle上限をEditMode testで検査できる。
- レバーとロータリーだけが天井不可という既存面規則を維持する。
- 次工程で6種類それぞれを配置し、Activity終了後のSpatial Anchor復元をQuest 3で確認できる。

## Blender reference asset set

3テーマ×6種類をBlender原本、FBX、1K PBR texture、Unity prefabとして制作済み。

- Blender sources: `ArtSource/Blender/{OrbitalAnalog,ForgeBrass,KineticSafety}/`
- Unity FBX: `Assets/MatsuMotoMeterAR/Content/Themes/<Theme>/Models/`
- Shared maps: `Assets/MatsuMotoMeterAR/Content/Themes/<Theme>/Textures/`
- Unity prefabs: `Assets/MatsuMotoMeterAR/Resources/<Theme>/Prefabs/`
- Movable hierarchy: `needle_pivot/needle`、`handle_pivot/handle`、
  `switch_pivot/switch`、`knob_pivot/knob`、`button_travel/button`
- Static lamp node: `indicator`

| Asset | Orbital Analog tris | Forge Brass tris | Kinetic Safety tris | Mesh objects | Materials |
| --- | ---: | ---: | ---: | ---: | ---: |
| MeterRound | 1,300 | 1,492 | 1,476 | 3 | 2 |
| Lever | 372 | 428 | 460 | 2 | 2 |
| Toggle | 220 | 276 | 308 | 2 | 2 |
| Rotary | 356 | 412 | 444 | 2 | 2 |
| Button | 280 | 336 | 368 | 2 | 2 |
| Lamp | 396 | 452 | 484 | 2 | 2 |

全18アセットは1,500 triangles以下、0 collider、0 realtime lightで、
`.blend`とFBX再読込の両方を自動検証済み。Unity EditMode test 29件でも
3テーマ共通のroot/socket、外形、可動ノード、material予算を検証済み。

Blender sourceはZ-upで制作し、FBX export時にUnityのY-upへ変換する。Blender
`-Y` outwardがUnity local `+Z` outwardへ対応する。生成と検証手順は
`ArtSource/Blender/README.md`を参照する。
