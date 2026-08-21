# Machined Ergonomics style guide

## Direction

工業デザイナーが設計した実在しそうな量産機器を独自に抽象化する。装飾では
なく、パーツ構成と製造工程の必然からつなぎ目、はめ込み、締結、面の切り替えを
作り込み、同時に人間工学と使いやすさが形状から読み取れる状態にする。

既存3テーマが暗い母材（cast iron / charcoal / graphite）を共有するのに対し、
本テーマは明るい成形樹脂の母材とアルマイト金属を主とし、grayscaleでも
value差で即座に識別できるようにする。特定メーカーの製品意匠、ロゴ、
固有の型式表記は複製しない。

## Part-construction language

形状は「1個の塊」ではなく「組み立てられた部品群」として構成する。

- housingは上下または前後の2ピース構成とし、分割面をシルエットに現す。
- パーティングラインは意図した位置に通し、機能境界（操作部、表示部、
  取付部）と一致させる。曲面の途中で不自然に消えない。
- シャットラインの幅を1モデル内で一定に保ち、実寸で0.8〜1.2 mm相当とする。
  段差付きの印籠継ぎ、または突き当て面のどちらかを1モデル内で統一する。
- 成形部品の側面には1〜3°の抜き勾配を与え、リブ根元にはフィレットを置く。
- 樹脂部の肉厚は一様に見せ、補強が必要な箇所はリブとボスで説明する。
- 締結は座ぐり穴＋キャップボルト、または皿ねじとし、コーナー、リブ交点、
  荷重経路上へ配置する。等間隔に並べるだけの装飾ねじにしない。
- 可動部の軸受にはブッシング、カラー、止め輪のいずれかを与え、軸が
  housingへ直接埋まる表現を避ける。
- シールが要る箇所（表示面、可動軸、分割面）にはガスケット溝または
  Oリング溝を置き、`gasket` material roleと一致させる。
- 機械加工面と成形面の切り替えは、必ず分割面か段差の上で行う。

## Ergonomic language

- 手が触れる稜線は面取りまたはR2以上とし、握り部に鋭利な稜を残さない。
- グリップ断面は円ではなく非対称とし、握り方向と操作方向を触覚で示す。
  グリップ相当径は30〜40 mm相当を基準とする。
- 指かかり（thumb rest、finger relief）を1箇所だけ明示し、複数置かない。
- 表示面は取付面法線から5〜15°手前へ傾け、立位視点での映り込みと
  視認角を改善する。envelopeのZ上限は超えない。
- 操作部は形状コーディングで識別する。トグル、ロータリー、ボタンの
  キャップ形状を互いに触覚で区別できる断面にする。
- 誤操作防止は凹み配置、非対称ガード、detentの触覚で行い、
  操作方向を塞ぐカバーを追加しない。
- 可動端は形状で分かるようにし、end stopをgeometryで示す。

## Geometry versus texture

Quest予算内で成立させるため、つなぎ目の表現を次で分ける。

Geometryで作る:

- housingの主分割面と、そこに生じる段差
- 座ぐり穴の窪みとボスの立ち上がり
- ガスケット溝、軸受カラー、end stop
- グリップの断面変化と指かかり

Normal mapまたはtextureへ委ねる:

- 副次的なシャットラインと細いパネル目地
- ねじ頭の溝、刻印、型式表記、警告表示
- シボ（表面グレイン）と微細なwear
- 目盛り、数値、label

シャットラインをすべてgeometry化しない。三角形は主分割面と可動部の
clearanceへ優先配分する。

## Materials and maps

- Opaque: light warm greyの成形樹脂body + anodizedアルミの機械加工accent
  + dark elastomerのgrip insert。
- Accentのsignal colorは1色に限定し、状態表示と操作方向だけに使う。
- Emissive: neutral whiteからsoft cyanの低彩度。realtime lightは使わない。
- Theme共有の1K BaseColor、Normal、MetallicSmoothness、Emissionを使う。
- material roleは既存の`body` / `metal` / `gasket` / `readout`を維持し、
  本テーマではgasket roleをelastomer gripとシール溝の両方へ使う。
- 汚れと使用感は最小限とし、新品の量産品として読める状態を基準にする。

## Runtime limits

1 objectあたり1,500 triangles以下、mesh renderer 3以下（meterのみ4以下）、
shared materials 2以下、visual colliderなし。配置、anchor、interactionは
`InstrumentRoot`と共通socket側の責務とする。共通visual envelope、pivot、
可動範囲は既存3テーマと同一にし、テーマ差はsilhouette detail、palette、
label、audio、VFXへ限定する。
