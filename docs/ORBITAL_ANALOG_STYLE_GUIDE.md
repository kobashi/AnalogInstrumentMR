# Orbital Analog style guide

## Reference extraction

2026-07-19に提供された2点の画像は、Orbital Analogテーマの方向性を判断する
ための参照資料として使用する。固有ロゴ、既存作品固有のpanel配置、文字、
図版そのものはmodelやtextureへ複製しない。

抽出する形状言語:

- 壁面へ深く埋没した円形instrument
- 厚い円筒housingと2～3層のbezel
- 暗いdial内部と、細く高密度な明色tick
- recessed face、前面rim、壁面の順に明確なdepth hierarchyを作る
- 大小の円形moduleを反復できる統一mount規格
- painted dark metal、aged bronze、brushed metalを少数の共有材で表現する
- 情報表示は細線、arc、短い目盛りを中心にし、装飾geometryを増やしすぎない

## Round-meter application

| Feature | Pilot implementation |
| --- | --- |
| Housing | 140 mmの低多角形円筒。mount面から前方へ伸びる |
| Bezel | 段付きrimと24分割の外周silhouette |
| Recess | dialを前端rimから約8 mm奥へ配置 |
| Dial | charcoal black |
| Marks | warm ivory/amberの41 tickと二重arc |
| Needle | 単一のamber needle。共有emissive材を使い`needle_pivot`で±55° |
| Glass | transparent meshを使わず、atlas上の弱い斜めhighlightで代替 |
| Wear | micro scratchをgeometry化せず、将来のatlas/normal更新で追加 |

## Control-family application

6種類を並べたとき、dark housing、aged-bronze rim、warm-amber focusの順で
同じdepth hierarchyを保つ。操作部の種類はsilhouetteと動きで識別し、
材質数を増やして識別しない。

| Asset | Shape grammar | Operation node |
| --- | --- | --- |
| Lever | 縦長plate、左右rail、球grip | `handle_pivot/handle`、local X片側48° |
| Toggle | 小型plate、短いcollar、細いshaft | `switch_pivot/switch`、local X片側56° |
| Rotary | 厚いknurled風knob、annular collar、単一index | `knob_pivot/knob`、連続回転 |
| Button | guard ring内の平たい円形cap | `button_travel/button`、14 mm |
| Lamp | cage ring内の丸いdome lens | `indicator`、発光pulseのみ |
| Throttle | engine quadrant、左右fork arm、幅広palm grip、6段階目盛 | `throttle_pivot/throttle_handle`、local X片側70° |
| Power slider | 縦slot、細いframe、横長carriage | `slider_travel/slider_handle`、0.18 m |

buttonとlampは同じamber focusを使うが、buttonはflat cap、lampはdome lensとし、
近距離だけでなくsilhouetteでも区別する。

## Density rules

- 単体meterは遠距離でも読めるprimary silhouetteを優先する。
- medium detailはbezel段差、major tick、hubで作る。
- fine detailはatlas内のminor tick、arc、wearへ限定する。
- 1個のモデルへpanel全体のgreeble密度を持ち込まない。
- console化するときはmeter、switch、button間のnegative spaceで密度を調整する。
- 窓枠サイズでは薄いcharcoal frameと深い大型dialを主形状にし、細い支持レールと
  amber vaneで宇宙船の隔壁／床／天井moduleとして読めるsilhouetteを作る。
- 多段階状態LEDは薄いcharcoal housingへ横長のRGB lensを埋め込み、
  `SAFE / WARN / DANGER`を緑・橙・赤の発光差で示す。

## Do not copy

- 参照画像内のpanel全体の配置
- 固有名称、ロゴ、艦船記号、文章
- 特徴的なscreen graphicsや波形の完全な形
- 参照画像の傷、汚れ、配線位置の一致
- 複数針や装飾機構による既存の`needle`操作contract変更

テーマの独自性は、charcoal/aged-bronze/warm-amber palette、24分割silhouette、
二重arcのdial grammar、共通mount envelopeの組み合わせで確保する。
