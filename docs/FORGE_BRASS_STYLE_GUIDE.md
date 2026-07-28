# Forge Brass style guide

## Direction

使い込まれた機械室の計器を独自に抽象化する。鋳鉄の暗い母材に、古色のある
真鍮と銅を機能部のaccentとして配置する。特定作品のロゴ、固有記号、
象徴的な盤面レイアウトは使わない。

## Shape language

- 円形、段付きrim、厚いbezel、短い円筒を主形状にする。
- 固定部には小径rivets、操作部にはknurlまたは球gripを使う。
- meterの埋没感は奥行きとself-shadowで作り、透明glassへの依存を避ける。
- silhouette追加は共通visual envelope内に収め、pivotと可動範囲を変えない。
- 窓枠サイズでは厚い鋳鉄housingと真鍮色の構造レールを使い、壁だけでなく
  床機関区画や天井設備へ取り付けても支持構造が読める形にする。
- 多段階状態LEDは鋳色housingと丸い宝石状RGB lensを組み合わせる。

## Materials and maps

- Opaque: charcoal cast iron + aged brass/copper accent。
- Emissive: warm amber。realtime lightは使わない。
- Theme共有の1K BaseColor、Normal、MetallicSmoothness、Emissionを使う。
- 汚れは低コントラストとし、目盛りや操作方向の読みやすさを優先する。

## Runtime limits

1 objectあたり1,500 triangles以下、mesh renderer 3以下（meterのみ4以下）、
shared materials 2以下、visual colliderなし。配置、anchor、interactionは
`InstrumentRoot`と共通socket側の責務とする。
