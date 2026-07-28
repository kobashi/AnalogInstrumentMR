# Kinetic Safety style guide

## Direction

高エネルギー設備の安全操作部を独自に抽象化する。graphiteの工業panelに、
orange/yellowの警告accentと明快なguardを組み合わせる。特定作品のロゴ、
固有記号、特徴的な配色配置は複製しない。

## Shape language

- 面取りした角形shroud、corner guard、太い支持材を主形状にする。
- 円形の操作部を角形guard内へ収め、Forge Brassとの差をsilhouetteで示す。
- safety stripeは補助情報として限定的に使い、操作方向と状態表示を阻害しない。
- guardも共通visual envelope内に収め、pivotと可動範囲を変えない。
- 窓枠サイズではgraphiteの埋め込みshroud、太い左右guard、orange/yellowの
  status vaneを使い、宇宙船内の高エネルギー区画用moduleとしてまとめる。
- 多段階状態LEDはgraphite housingへ幅広い警告バー形状のRGB lensを置く。

## Materials and maps

- Opaque: matte graphite metal + orange/yellow safety accent。
- Emissive: saturated orange。realtime lightは使わない。
- Theme共有の1K BaseColor、Normal、MetallicSmoothness、Emissionを使う。
- 強い発光や透明coverを増やさず、value contrastで視認性を確保する。

## Runtime limits

1 objectあたり1,500 triangles以下、mesh renderer 3以下（meterのみ4以下）、
shared materials 2以下、visual colliderなし。配置、anchor、interactionは
`InstrumentRoot`と共通socket側の責務とする。
