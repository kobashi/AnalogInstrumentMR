# 3D Model Quality Floor V4

基準モデルは `Lever_KineticSafety_HS_V3_Retopo` とする。

## Modeling

- Boolean適用結果のDecimateを最終メッシュとして使用しない。
- 独立したクリーンケージから形状を構築する。
- 主外形、凹部、段差、保護構造、締結部をシルエットで識別可能にする。
- 平面キャップ以外はQuad主体とし、三角化前の編集用Blendを保存する。
- Unity向けFBXは決定論的に三角化したBlendから出力する。
- 非多様体エッジと縮退面は0とする。

## Runtime contract

- Blender X → Unity X
- Blender Z → Unity Y
- Blender -Y outward → Unity +Z outward
- FBX export: `-Z Forward / Y Up`
- 操作部は既存契約のノード名を維持する。
  - Meter: `needle_pivot/needle`
  - Lever: `handle_pivot/handle`
  - Toggle: `switch_pivot/switch`
  - Rotary: `knob_pivot/knob`
  - Button: `button_travel/button`
  - Lamp and Status: `indicator`
  - Throttle: `throttle_pivot/throttle_handle`
  - Power slider: `slider_travel/slider_handle`
  - Window panel: `vane_pivot/vane`

## Budgets

- 小型計器・操作部: 5,000 triangles以下
- WindowMeter / WindowPanel: 25,000 triangles以下
- 可動軸はモデルの見た目の軸受と一致させる。
- マテリアルはHousing、Metal、Emissionの最大3系統を基本とする。
- ColliderとRealtime LightはFBXへ含めない。

## Deliverables

- Retopo source Blend
- Triangulated Blend
- FBX candidate
- Standard preview
- Topology preview
- JSON validation report

候補は `HardSurfacePrototype/V4` に出力し、本番Prefabへ自動的に統合しない。
