# Claude Opus 5: V6 3D model brush-up handoff

## 1. Objective

AnalogInstrumentMR の V6 3D モデルを、既存の Unity runtime 契約と Quest 3
性能予算を維持したまま視覚的に改善する。

初回作業は全39モデルへ展開しない。まず Kinetic Safety の代表3モデルで
パイロットを実施し、形状品質、可動干渉、視覚レビュー、Unity staging 検証を
完了してから残りへ展開する。

パイロット対象:

1. `MeterRound`: 計器の奥行き、ベゼル、針、盤面の読みやすさ
2. `Lever`: 軸受、ガイド、detent、可動端クリアランス
3. `Throttle`: パームグリップ、トラック、支持構造、70度可動域

この作業の優先順位は次のとおり。

1. runtime 契約と可動範囲を壊さない
2. Quest 3 の性能予算を守る
3. 固定画像で確認できるシルエットと機械的説得力を改善する
4. 近接表示のシェーディングと材質ロールを改善する
5. 細かな傷、刻印、ローレット等は可能な限りtextureへ委ねる

## 2. Repository baseline

- Repository: `kobashi/AnalogInstrumentMR`
- Blender migration branch: `codex/blender-5.2-migration`
- Blender migration commit: `452475277b97207a848a1cbfa72be2a36d041676`
- Draft PR: [#2 Migrate Blender tooling to 5.2](https://github.com/kobashi/AnalogInstrumentMR/pull/2)
- Supported Blender: `5.2.x`
- Migration baseline: `5.2.0 LTS`
- Unity: `6000.3.19f1`
- Target device: Meta Quest 3

PR #2 が未mergeの場合は上記branchから開始する。`main` のmerge commit
`6d9266d`だけを基準にすると、Blender 5.2互換層とsmoke testが含まれない。

作業開始時に以下を確認する。

```sh
git status -sb
scripts/run-blender.sh --version
scripts/run-blender.sh --print-bin
```

PATH上の `blender` を直接使用しない。すべて `scripts/run-blender.sh` 経由で
Blender 5.2を起動する。

## 3. Authoritative references

作業前に次を読む。

- `ArtSource/Blender/README.md`
- `docs/MODEL_REPLACEMENT_WORKFLOW.md`
- `docs/design/V6_model_replacement_readiness.md`
- `docs/3D_MODEL_QUALITY_FLOOR_V4.md`
- `docs/GREYBOX_INSTRUMENT_SPEC.md`
- `docs/VISUAL_THEMES.md`
- `docs/KINETIC_SAFETY_STYLE_GUIDE.md`
- `docs/reviews/Gemini_3Dモデルレビュー_2026-07-29.txt`

現行のV6 production asset、Unity prefab、texture atlasを正として扱う。
古いV4/V5やpre-V6 candidateを新しいruntime契約の根拠にしない。

## 4. Input files

形状編集は `ProductionReady.blend` ではなく、quad主体の編集可能な
`Retopo.blend` から開始する。

```text
ArtSource/Blender/ThemeHardSurfaceV6/KineticSafety/
├── BL_MeterRound_KineticSafety_V6_Retopo.blend
├── BL_Lever_KineticSafety_V6_Retopo.blend
└── BL_Throttle_KineticSafety_V6_Retopo.blend
```

`ProductionReady.blend` は三角化、runtime renderer単位の結合、atlas UV変換、
opaque＋emissiveへの材質統合が済んでいる。Brush-up用の編集元にしない。

`Material.blend` はPBR確認用の中間成果物であり、形状の原本にはしない。

## 5. Candidate workspace and naming

既存ファイルを上書きせず、次のlocal candidate directoryを使用する。

```text
ArtSource/Blender/BrushUp/Opus5/KineticSafety/
├── BL_MeterRound_KineticSafety_V6_Opus5_R1_Retopo.blend
├── BL_Lever_KineticSafety_V6_Opus5_R1_Retopo.blend
├── BL_Throttle_KineticSafety_V6_Opus5_R1_Retopo.blend
├── Preview_MeterRound_KineticSafety_V6_Opus5_R1_*.png
├── Preview_Lever_KineticSafety_V6_Opus5_R1_*.png
├── Preview_Throttle_KineticSafety_V6_Opus5_R1_*.png
└── reports/
```

生成または変更を再現するPythonは次へ置く。

```text
Tools/Blender/opus5_brushup_kinetic_pilot.py
```

命名規則:

- `Opus5`: 作業系統
- `R1`, `R2`, ...: 人または視覚モデルのレビューを受けたrevision
- `Retopo`: 非三角化の編集可能原本
- `Triangulated`: 検証用派生物。承認前はproduction pathへ置かない
- 拡張子は `.blend`。`.blender` は使用しない

## 6. Non-negotiable runtime contract

### 6.1 Coordinate and transform contract

- 1 Blender unit = 1 metre
- BlenderはZ-up
- Blender X -> Unity X
- Blender Z -> Unity Y
- Blender `-Y` outward -> Unity local `+Z` outward
- FBX exportは `-Z Forward / Y Up`
- root scaleは常に `(1, 1, 1)`
- mount面はUnity local `Z = 0`
- mount面の後方へ1 mmを超えて突出しない
- rootとmotion nodeへ未適用の負scaleを残さない

### 6.2 Root contract

root名を変更しない。

```text
PF_Visual_<Object>_<Theme>_V6
```

パイロットでは次の3つとなる。

```text
PF_Visual_MeterRound_KineticSafety_V6
PF_Visual_Lever_KineticSafety_V6
PF_Visual_Throttle_KineticSafety_V6
```

rootの既存custom propertyを削除または変更しない。

- `instrument_type_id`
- `theme_id`
- `unity_mount_axis`
- 品質、制作方式、atlas、replacementに関する既存metadata

### 6.3 Motion hierarchy contract

| Object | Required hierarchy | Motion acceptance |
| --- | --- | --- |
| MeterRound / MeterMedium / MeterLarge | `needle_pivot/needle` | 針の全域で盤面、glass、frameへ干渉しない |
| Lever | `handle_pivot/handle` | `-24° / neutral / +24°`でbaseへ干渉しない |
| Toggle | `switch_pivot/switch` | `-28° / +28°`でcollarへ干渉しない |
| Rotary | `knob_pivot/knob` | 連続回転で偏心しない |
| Button | `button_travel/button` | 14 mm押下でguideへ不自然に貫通しない |
| Lamp | `indicator` | node名を維持する |
| Throttle | `throttle_pivot/throttle_handle` | 70度arcの両端でhousingへ干渉しない |
| PowerSlider | `slider_travel/slider_handle` | local Y方向0.18 mの全域でrailへ干渉しない |
| StatusIndicator | `indicator` + three states | `status_safe`, `status_warn`, `status_danger`を独立維持 |
| WindowMeter | `needle_pivot/needle` | 大型針の全域でframeへ干渉しない |
| WindowPanel | `vane_pivot/vane` | `-42° / +42°`でframeへ干渉しない |

Pivot位置、local axis、親子関係は原則として変更しない。形状改善のため変更が
不可避な場合は作業を止め、次を提示して承認を得る。

- 変更理由
- old/new position
- old/new local axis
- neutral、minimum、maximumの比較画像
- Unity interactionと保存済みnormalized valueへの影響

### 6.4 Components that must not be added

Visual hierarchyへ次を追加しない。

- Collider
- Animator
- Camera
- realtime Light
- runtime script/component
- external add-onがないと評価できないmodifierまたはnode group

操作判定はUnity runtime側の `InteractionCollider` が担当する。見た目に合わせて
Blender側へColliderを追加しない。

## 7. Geometry and Quest budget

### 7.1 Limits

- 小型modelと標準meter: 5,000 triangles以下
- `MeterMedium`, `MeterLarge`, `WindowMeter`, `WindowPanel`: 25,000 triangles以下
- non-manifold edge: 0
- zero-area face: 0
- 通常面はquad主体
- 平面cap以外の大きなngonを避ける
- Boolean適用結果への単純Decimateをfinal meshにしない
- bevel、weighted normal、smoothingを近接視認で破綻させない
- 可動部と静止部は契約上必要なislandを維持する

大型modelへ高密度detailを追加する場合は、Quest受け入れ前にLOD方針を提示する。

### 7.2 Geometry versus texture

Geometryで表現する:

- silhouetteへ影響するbezel、guard、support、grip
- 近接時に明確な段差となるpanel layer
- pivot housing、bearing、bushing、joint、end stop
- 操作方向と可動範囲を説明するmajor guide
- 実際の空隙と可動clearance

Textureまたはnormal mapへ残す:

- micro scratch、細かなwear
- knurlingの微細な山
- 小さなscrew head、浅いengraving
- meter scale、数値、label
- 微細なgroove、surface grain

形状密度を増やすこと自体を品質改善と見なさない。1～3 m離れたQuest視点での
識別性、近接時のbevel highlight、機械構造の理解しやすさを優先する。

## 8. Material and UV contract

Retopo/Material段階では4つのsemantic material roleを維持する。

| Role | Atlas quadrant | Meaning |
| --- | --- | --- |
| `body` | top-left | housing、painted panel |
| `metal` | top-right | exposed metal、bearing、fastener |
| `gasket` | bottom-left | rubber、seal、grip insert |
| `readout` | bottom-right | dial、mark、emissive surface |

各Blender Materialの `v6_material_role` custom propertyを維持する。新materialを
追加する場合も4 roleのいずれかを設定する。

最終Unity contractは1modelあたり最大2 shared materials:

1. opaque atlas
2. emissive atlas

StatusIndicatorの3状態rendererもshared materialを使用する。個別model専用の
textureやmaterialを無断で追加しない。

Texture atlasはstandard、medium、largeの3 density classを使用する。
Brush-upで既存atlasの配色、role境界、UV quadrantを変更しない。

## 9. Theme art direction

Kinetic Safetyのパイロットで保持すべき特徴:

- dark navy / graphite body
- cool gunmetal
- dense black anti-slip rubber
- controlled cyan luminous resin
- chamfered guard、太いsupport、impact-resistant silhouette
- 警戒表現は機能的に使用し、装飾だけのmilitary clutterへ寄せない
- damage、rust、汚れを過剰にしない

3テーマへ展開する場合、grayscaleでも識別できるsilhouette差を維持する。

- Orbital Analog: thin、precise、compact、refined spacecraft instrument
- Forge Brass: stepped rim、cast mass、aged brass、maintained industrial machine
- Kinetic Safety: protected、chamfered、rugged、functional safety hardware

## 10. Pilot improvement brief

### 10.1 MeterRound / Kinetic Safety

Required improvements:

- bezelからdial faceまでの奥行きを読みやすくする
- needleとhubを近接・中距離の両方で認識できる太さへ調整する
- guard、bezel、dial、gasketのlayer関係を明確にする
- needle全可動域でdialまたはfront layerへ干渉させない

Avoid:

- glass transparency前提の表現
- 細かすぎる立体目盛り
- meter envelopeの拡大
- readoutをbody materialへ統合すること

### 10.2 Lever / Kinetic Safety

Required improvements:

- pivot周辺へbearing coverまたはbushingの機械的根拠を与える
- detent方向を説明するguideまたはindexを追加する
- gripとarmの材質・形状差を明確にする
- `-24° / neutral / +24°`でbase、guard、slotへ干渉させない

Avoid:

- `handle_pivot`を見た目だけに合わせて移動すること
- gripを大きくしてinteraction envelopeを変えること
- guardによってcontroller接近方向を塞ぐこと

### 10.3 Throttle / Kinetic Safety

Required improvements:

- palm gripへ大きなergonomic contourとanti-slip insertを与える
- track、fork/support、pivot housingの構造を説明可能にする
- CUTOFF / IDLE / FULL方向を形状またはreadout roleで読みやすくする
- 70度arc両端でgrip、arm、housingを干渉させない

Avoid:

- palm grip boxとの位置関係を変更すること
- decorative cableや細いpartを増やしすぎること
- 片側からしか成立しないasymmetric mountを導入すること

## 11. Reproducible implementation requirement

`.blend` の手作業編集だけで完了しない。可能な変更はBlender Pythonへ記録し、
同じbaselineからcandidateを再生成できるようにする。

`Tools/Blender/opus5_brushup_kinetic_pilot.py` は最低限次を満たす。

- Blender 5.2 compatibility preflightを実行する
- inputとoutput pathを引数で受け取る
- production sourceを上書きしない
- 既存root、metadata、motion hierarchyを検査する
- candidateを指定directoryへ保存する
- topology、bounds、material role、pivot情報をJSONへ出力する
- Python exception時にnon-zeroで終了する

外部networkやdownloadへ依存しない。外部Blender add-onを導入しない。

## 12. Required visual review artifacts

`.blend`だけでは視覚レビュー完了としない。各modelについて固定cameraと固定lightで
次のPNGを出力する。

1. grayscale front three-quarter
2. grayscale opposite three-quarter
3. side profile
4. topology / wireframe
5. PBR emissive OFF
6. PBR emissive ON
7. neutral pose
8. minimum motion pose
9. maximum motion pose
10. pivot close-up at both motion limits

画像にはmodel全体を収め、candidate間でcamera、focal length、exposure、world、
resolutionを固定する。Beauty shotだけでなく、失敗を発見できる角度を含める。

比較用contact sheetには同じ条件の `Before / After` を横並びにする。Blender 4.5
previewとのpixel hash一致は要求しない。Blender 5.2 EEVEEではtone、emission、
exposureが変わり得るため、次を人と視覚modelで評価する。

- silhouetteとtheme識別性
- bevel highlightとdark-face readability
- moving partとstatic partの分離
- mount面と可動端のpenetration
- emissive OFF時のreadout構造
- emissive ON時の白飛びと色のにじみ
- 1～3 m相当の縮小表示での判読性

## 13. Required report per model

`reports/<Object>_<Theme>_V6_Opus5_R1.json` に次を記録する。

```json
{
  "source": "original Retopo path",
  "candidate": "candidate Retopo path",
  "blender_version": "5.2.x",
  "root": "PF_Visual_..._V6",
  "changes": [],
  "unchanged_contracts": [],
  "vertices": 0,
  "triangles": 0,
  "triangle_budget": 5000,
  "non_manifold_edges": 0,
  "zero_area_faces": 0,
  "bounds_before": {},
  "bounds_after": {},
  "pivot_before": {},
  "pivot_after": {},
  "material_roles": ["body", "metal", "gasket", "readout"],
  "motion_checks": [],
  "known_risks": [],
  "status": "CANDIDATE"
}
```

数値を推測で書かない。Blender sceneから計測して記録する。

## 14. Validation workflow

### 14.1 Static and FBX smoke test

candidateを保存した後、productionを上書きしない一時directoryで検査する。

```sh
candidate_smoke_dir="$(mktemp -d)"

scripts/run-blender.sh --background --factory-startup \
  --python Tools/Blender/smoke_test_blender_52.py -- \
  --source ArtSource/Blender/BrushUp/Opus5/KineticSafety/BL_Lever_KineticSafety_V6_Opus5_R1_Retopo.blend \
  --expected-root PF_Visual_Lever_KineticSafety_V6 \
  --output-dir "$candidate_smoke_dir"
```

MeterRoundとThrottleにも同じ検査を行う。

この段階では `scripts/run-blender-52-smoke.sh --all` を合格条件にしない。このsuiteは
現行の39個の `ProductionReady.blend` を対象としており、candidate承認後の回帰確認に
使用する。

### 14.2 Review gate

Opus 5は次を提出した時点で作業を止める。

- candidate Retopo Blend 3件
- 再現用Python
- Before / After contact sheet
- 可動端画像
- JSON report 3件
- smoke test結果
- 変更点、未解決点、推奨する次revision

Codexまたは担当者が次を確認するまでは、`Material.blend`, `Triangulated.blend`,
`ProductionReady.blend`, Unity FBX、Prefabを上書きしない。

### 14.3 Approval after pilot

パイロット承認後にのみ次へ進む。

1. candidate用Material/PBR previewを生成する
2. candidateを決定論的にtriangulateする
3. shared 2x2 atlasへUVをremapする
4. opaque＋emissiveへmaterialをcollapseする
5. staging FBXとstaging prefabを生成する
6. hierarchy、motion target、renderer、material、triangle、boundsを検証する
7. Unity motion auditを実行する
8. Quest 3でneutral、可動端、暗所emissive、24-object performanceを確認する
9. 合格後にProductionReadyとactive FBXを置換する

## 15. Prohibited actions

明示的な承認なしに次を行わない。

- 39個すべてのmodelを一括変更する
- 現行 `*_ProductionReady.blend` を保存し直す
- active Unity FBX、Prefab、Material、`.meta`を置換する
- root、pivot、motion targetをrenameする
- interaction colliderまたはruntime logicを変更する
- texture atlas layoutを変更する
- Blender exporterをLegacy FBXから切り替える
- Blender versionを5.2以外へ変更する
- 新しいdependency、add-on、network assetを追加する
- visual acceptance前にproduction integrationを完了扱いにする

## 16. Definition of done for the pilot

パイロットは次のすべてを満たしたときだけ完了とする。

- 3 candidate Retopo BlendがBlender 5.2で開ける
- baselineから再現用Pythonで生成できる
- root、metadata、motion hierarchyが完全一致する
- pivotとlocal axisが承認なしに変わっていない
- triangle、renderer、material、bounds予算内
- non-manifold edgeとzero-area faceが0
- neutralと両可動端でpenetrationがない
- Before / After画像で改善理由を説明できる
- PBR OFF / ONで材質roleとemissiveが読める
- smoke testが3/3 PASS
- production assetとUnity active assetが未変更
- 人と視覚modelがパイロットの展開可否を判断できる

## 17. Initial instruction to Claude Opus 5

以下を最初の依頼として使用できる。

```text
AnalogInstrumentMRのV6 3Dモデルをbrush-upする。

最初に docs/OPUS5_3D_MODEL_BRUSHUP_HANDOFF.md と、そこから参照される
runtime契約、model replacement、V6 readiness、style guideを読むこと。

今回はKineticSafetyのMeterRound、Lever、Throttleだけをパイロット対象とする。
ArtSource/Blender/ThemeHardSurfaceV6/KineticSafetyの*_Retopo.blendを編集元とし、
ProductionReady、Unity FBX、Prefab、Material、.metaを上書きしないこと。

Blender 5.2をscripts/run-blender.sh経由で使用する。root名、metadata、pivot、
motion hierarchy、unit、axis、mount面、triangle/material/renderer予算を維持する。

各modelについて、candidate Retopo Blend、再現用Blender Python、計測JSON、
固定cameraのBefore/After、topology、PBR OFF/ON、neutral/min/max可動画像を作る。

見た目の改善よりruntime契約を優先し、pivot変更が必要なら作業を止めて理由と
比較資料を提示する。3 candidateとレビュー資料が揃った時点で停止し、全39modelや
productionへの展開は開始しないこと。
```
