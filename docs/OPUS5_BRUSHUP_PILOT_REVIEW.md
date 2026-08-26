# Opus 5 brush-up pilot: Kinetic Safety MeterRound / Lever / Throttle

現在のrevisionは **R2**。R1のレビューを受けて、干渉計測の作り直し、Leverの
slot実装、形状の追い込みを行った。§9にR1からの変更点をまとめている。

## 1. Status

- branch: `codex/blender-5.2-migration`（維持）
- Blender: 5.2.0 LTS（`scripts/run-blender.sh` 経由）
- 対象: Kinetic Safety の `MeterRound`, `Lever`, `Throttle` のみ
- 編集元: `ArtSource/Blender/ThemeHardSurfaceV6/KineticSafety/BL_*_V6_Retopo.blend`
- 状態: `CANDIDATE`

`*_ProductionReady.blend`, `*_Material.blend`, `*_Triangulated.blend`、Unityの
active FBX / Prefab / Material / `.meta` / texture は1件も変更していない。
tracked fileの変更は `.gitignore` の4行のみ（texture toolingのvenvを除外する
ため。§5.8と [`docs/OPUS5_CODEX_ALIGNMENT.md`](OPUS5_CODEX_ALIGNMENT.md) §3）。

## 2. Deliverables

| 要求 (§14.2) | 提出物 |
| --- | --- |
| candidate Retopo Blend 3件 | `ArtSource/Blender/BrushUp/Opus5/KineticSafety/BL_*_V6_Opus5_R2_Retopo.blend` |
| 再現用Python | `Tools/Blender/opus5_brushup_kinetic_pilot.py` |
| Before / After contact sheet | `.../contact_sheets/` 39枚（13 shot × 3 model） |
| 可動端画像 | `pose_minimum` / `pose_maximum` / `pivot_closeup_minimum` / `pivot_closeup_maximum` |
| JSON report 3件 | `.../reports/<Object>_KineticSafety_V6_Opus5_R2.json` |
| smoke test結果 | `.../reports/smoke/*.smoke.json`（3/3 PASS） |
| 変更点・未解決点・次revision | 本書 §4〜§8 |

描画条件（camera位置、焦点距離、light、world、exposure、resolution）はBaselineと
候補で同一のリテラル値に固定してある。bounds由来の自動フレーミングは使っていない。

## 3. Contract verification

生成スクリプトは保存前に契約を検査し、違反があれば候補を書き出さずに
non-zero終了する。R2は全項目通過。

| 項目 | MeterRound | Lever | Throttle |
| --- | --- | --- | --- |
| root名一致 | PASS | PASS | PASS |
| root custom property 完全一致 | PASS | PASS | PASS |
| pivot transform 完全一致 | PASS | PASS | PASS |
| motion hierarchy | `needle_pivot/needle` | `handle_pivot/handle` | `throttle_pivot/throttle_handle` |
| triangles（三角化後） | 3,992 → **4,636** / 5,000 | 3,004 → **4,432** / 5,000 | 2,852 → **4,020** / 5,000 |
| non-manifold edges | 0 | 0 | 0 |
| zero-area faces | 0 | 0 | 0 |
| quad比率（Retopo段階） | 0.65 | 0.65 | 0.58 |
| bounds 拡大 | なし（-Y側が0.5 mm縮小） | なし（同一） | なし（同一） |
| mount面越え（静止部） | なし | なし | なし |
| material role 4種維持 | PASS | PASS | PASS |
| 新規Material追加 | 0 | 0 | 0 |
| Collider / Animator / Camera / Light | 0 | 0 | 0 |
| 未適用modifier | 0 | 0 | 0 |
| renderer島 | static 1 + movable 1 | static 1 + movable 1 | static 1 + movable 1 |
| Blender 5.2 smoke test | PASS | PASS | PASS |

Material roleは新規materialを作らずに維持している。`body` / `metal` / `readout`
は既存の `MAT_KineticSafety_V5_*` をそのまま使い、`gasket` は
`v6_theme_materials.assign_special_roles` が見る名前token（`gasket`, `washer`,
`bushing`, `pivot_boot`）を新規objectの名前に含めることで解決させている。
atlas quadrant、配色、role境界は未変更。

## 4. Changes per model

### 4.1 MeterRound

Baselineでは12角柱bezelの前面がそのまま盤面で、目盛りも同一平面、針はその
0〜4 mm前を浮いていた。奥行きが読める要素が存在しなかった。

- `kinetic_v6_dial_pan` を追加し、盤面を `y = -0.0725` へ後退（bezel前縁から8.0 mm）
- `kinetic_v6_bezel_ring` を追加（面取り段付きring、前面 `y = -0.0805`）
- `kinetic_v6_inner_retainer` を追加してbezel層と盤面層を分離
- `kinetic_v6_glass_gasket` を角断面のシール形状へ作り直し（gasket role）
- 13本の目盛りを後退した盤面へ再配置（`y = -0.0715..-0.0745`、針下2.5 mm）、
  5本の主目盛りを太く長く
- `kinetic_v6_dial_arc` を追加（内周の発光アーク帯）
- 針を作り直し: テーパーブレード（根元3.6 mm）、20 mmの金属カウンターウェイト、
  二段ハブ（r = 11.8 mm / 5.4 mm）
- 円形部品の分割数を20 → 24へ（近接時にdial rimの多角形が見えていた）

### 4.2 Lever

- **shaft slotを実装**（§5.2）。`housing` と `recess_insert` を作り直した
- `kinetic_v6_bearing_cap_0/1`（内径14 mmのボルト留めcollar、各3本のボルト）を追加
- `kinetic_v6_detent_quadrant`（可動面内の円弧板、-6°〜+54°）を追加。
  housing recess床 `y = -0.041` へ干渉しない範囲に収めてある
- detent tooth 5個 + 発光index mark 5個を 0/12/24/36/48° に追加。
  歯は台形断面（等幅ブロックの列は近接でgreebleに見えるため）
- `kinetic_v6_slot_guide_0/1`（shoulderから5.6 mm突出するguide rib）を追加
- `kinetic_v6_handle_channel_0/1`（slot縁と面一のguide lip）を追加。
  12 mm軸のsweep上端 `z = -0.013` を避けて `z = -0.008` から立ち上げてある

pivot周辺のgasket roleは既存の `kinetic_v6_bearing_washer_*`（`washer` token）
がすでに担っているため、重複するbushingは追加していない。

### 4.3 Throttle

- movable island `throttle_handle` を作り直し
  - 等幅アーム2本 → テーパーfork arm + 中央web
  - `throttle_fork_brace` で2本のforkを連結
  - palm gripをくびれのある本体 + 冠状のpalm面へ造形。baselineのgrip box
    （`y -0.085..-0.120`, `z 0.083..0.141`）は維持し、controller grip位置関係を変えていない
  - 滑り止めinsert 4本（gasket role）をpalm面から1.5 mm突出。前面は
    baselineと同じ `y = -0.120`
  - `throttle_grip_readout_index` を追加してquadrant scaleを指す
- `KineticSafety_throttle_v6_limit_stop_0/1` を `y = -0.046..-0.0625` へ作り直し（§5.3）
- `kinetic_v6_throttle_pedestal_0/1` を追加。軸が板から浮かず支持構造へ着地する
- `kinetic_v6_throttle_bushing_0/1`（gasket role）を軸周りに追加
- `kinetic_v6_throttle_quadrant_0/1`（可動面内の円弧slot cheek）を追加
- CUTOFF / FULL の端部blockをscaleへ追加
- scaleを左cheekへミラー。baselineは `+X` 側にしか目盛りがなく、片側専用の
  取り付けに見えていた

## 5. Interference measurement

### 5.1 How it is measured

可動域を掃引し、可動島の各三角形と静止meshの各三角形について**正確な交差判定**を
行い、交差線の実座標を求めている。`BVHTree.overlap()` は広域判定でしかなく
（数十mm離れた三角形も対にする）、単独では使えない。

pivot近傍の「軸受としての意図的な埋め込み」を区別するため、pivotからの距離が
interface半径を超える接触だけを不具合として数える。interface半径は各modelの
軸受span（Lever 45 mm、Throttle 58 mm、MeterRound 16 mm）に合わせてある。
全サンプルはJSONの `motion_checks_before` / `motion_checks_after` にある。

| Model | Baseline: interface外接触 | R2: interface外接触 |
| --- | ---: | ---: |
| MeterRound | 157 | **0** |
| Lever | 204 | **0** |
| Throttle | 0 | **0** |

### 5.2 MeterRound: 針が盤面へ埋まっていた（修正済み）

Baselineの針hubは `y = -0.0735` まで後退しており、盤面である
`kinetic_polygon_bezel` の前面 `y = -0.077` より3.5 mm奥にあった。掃引全域で
1,054組が交差し、うち157組はhub半径の外側。盤面を後退させ、hubを盤面から
1.0 mm浮かせたことで **交差0組** になった。

### 5.3 Lever: shaftにslotが無かった（修正済み）

`lever_shaft`（半径8.5 mm）は `recess_insert` と console前面帯を
slotなしで貫通していた。接触点の実測位置は `z = 0.055`（insert上端）と
`z = 0.070`（console外周上端）で、発生するのは掃引の `φ = 0°..6°` のみだった。

R2では両方を作り直した。

- `housing`: pocketをconsole上端まで開口させ、幅25 mm × 高さ10 mmのslotにした。
  slot床は `y = -0.041` のままなので筐体は閉じたsolidを保つ。baselineのouter/
  pocket outlineの頂点、shoulder、trunnionはすべて同じ値で再現している
- `recess_insert`: `x = ±12.5..37 mm` の2枚のcheekと、軸のsweep下端より下に
  置いたbridgeへ分割した

結果、interface外接触は **204 → 0**。残る交差はすべてpivotから45 mm以内で、
軸がtrunnion bore内を通っている状態そのもの。

### 5.4 Throttle: 軸が下側limit stopを貫通していた（修正済み）

`KineticSafety_throttle_v6_limit_stop_0` は `y = -0.084` まで伸びており、
`throttle_axle`（半径16 mm）が全角度でその内部を通っていた。掃引全域で1,983組。
stopを `y = -0.0625` までに作り直し、R2ではこのstopとの交差は **0組**。

なお、この交差はpivotから58 mm以内だったため「interface外接触」としては
0件のままである。Throttleのbaselineにinterface外の貫通は無かった。

### 5.5 可動方向の符号（要確認）

`OrbitalAnalogVisualFactory` は theme visual の motion を次の値で設定している。

| Kind | axis | amplitude | rotationOffset | 実効角度範囲 |
| --- | --- | --- | ---: | --- |
| Meter | `Vector3.forward` | 55 | 0 | `-55° … +55°` |
| Lever | `Vector3.right` | 24 | -24 | `-48° … 0°` |
| Throttle | `Vector3.right` | 35 | -35 | `-70° … 0°` |

`MockInstrumentMotion.ApplyState` は `Lerp(-amplitude, amplitude, value) +
rotationOffsetDegrees` なので、LeverとThrottleは **片側掃引** であり、
authoringされたneutral姿勢が travel の一端になる。これは
`GREYBOX_INSTRUMENT_SPEC.md` の「初期角offsetを加えた片側sweep」と一致する。

掃引の向きはmount面から**外向き**（Blender `-Y` 方向、Blender `+X` 軸まわりの
正回転）でなければならない。逆符号を実測すると次のようになる。

- Lever: 掃引の-18°以降でhandleがmount面の裏側へ回り込み、最悪 `y = +0.090`
- Throttle: 同様に最悪 `y = +0.155`

本レポートは外向き（Lever `0°…+48°`、Throttle `0°…+70°`）を主系列として掃引し、
逆符号は各JSONの `mirrored_sign_check` に記録してある。**Unity側で実際に適用
される回転向きがこの解釈と一致するかは、Codex側でprefabを1回動かして確認して
ほしい。** 一致しない場合、現行のV6 production assetにもmount面貫通が存在する
ことになる。

### 5.6 MeterRoundのenvelopeはP0仕様を超過している（現状維持）

`GREYBOX_INSTRUMENT_SPEC.md` の `meter.round` は `0.140 × 0.140 × 0.064 m`
だが、現行V6の実測は `0.154 × 0.154 × 0.081 m` で、baselineの時点で超過している。
`docs/design/V6_model_replacement_readiness.md` の手順6-5が「V6 boundsを
`InstrumentGreyboxSpecification` へ昇格する」としているため、本パイロットでは
V6実測boundsを事実上のenvelopeとして扱い、**baselineを超えないこと** を合格条件に
した。仕様書側の数値更新はproduction統合時の判断事項として残す。

## 5.7 Atlas UV pass（項目1・前半、実施済み）

方針は「UVだけ直す」。atlas layout、role境界、配色、texture枚数、1024 px、
shared material 2枚はすべて不変。

### 計測した欠陥

`export_v6_replacement_candidates.smart_unwrap` は各objectを**結合前に**
`scale_to_bounds=True` で展開し、その結果をrole象限いっぱいへ写している。
3 mmのボルトも340 mmのconsoleも象限全体を占めるため、象限へ焼かれている
タイリングdetail（body ×3, metal ×5）がパーツごとに全く違う物理サイズで出る。

| Model | housing | 最小パーツ | 較差 |
| --- | ---: | ---: | ---: |
| MeterRound | 1,095 tx/m (154 mm) | 45,493 tx/m (6.4 mm tick) | ×41.6 |
| Lever | 1,035 tx/m (180 mm) | 61,499 tx/m (4.7 mm index) | ×59.4 |
| Throttle | 735 tx/m (340 mm) | 20,834 tx/m (10.7 mm bolt) | ×28.4 |

### 対応

`Tools/Blender/opus5_uv_atlas_pass.py`。象限いっぱいへの引き伸ばしをやめ、
**物理サイズに比例した象限内サブ矩形**へ写す。サブ矩形の位置はobject名の
ハッシュで決定論的に散らし、同role同士が同じパッチを見ないようにしている。

| Model | 較差 before → after | 達成密度 |
| --- | --- | --- |
| MeterRound | ×41.6 → **×1.21** | 604〜729 tx/m |
| Lever | ×59.4 → **×1.17** | 611〜718 tx/m |
| Throttle | ×28.4 → **×1.19** | 611〜725 tx/m |

clampされたパーツは0件。3モデルとも同じ604〜729 tx/mの帯に収まったので、
モデルをまたいでも同じ粒度になる。出力は `*_Opus5_R2_AtlasUV.blend` と
`reports/*_AtlasUV.json`。

### プレビューと量産の不一致も直した

`v6_theme_materials` はGenerated座標のBOX投影、量産は象限UV + opaque/emissive
2枚への統合で、**別のマッピング**だった。つまり従来の `pbr_emissive_*` は
Unityでの見え方を予測していない。比較描画は量産と同じUV経路・同じ2枚構成へ
揃えてある（`contact_sheets/ContactSheet_*_AtlasUV_*.png`、左=量産UV、
右=定密度UV、形状はどちらもR2）。

### ここで判明した上限（次の判断事項）

密度を揃えた結果、粒度が一律に粗いことが見えるようになった。象限は
0.46 × 1024 = 471テクセル、bodyのdetail_repeatsは3なので1リピート=157テクセル。
700 tx/mでは **1リピート = 224 mm** になる。表面の粒として機能しない。

機械加工面らしい25〜30 mmの粒を出すには repeats を3 → 約24へ上げる必要があり、
そのとき1リピートは元画像で約43 px。1Kのテーマ共有アトラスで定密度を保つ限り、
これが上限になる。選択肢は次のいずれか。

1. repeatsを上げる（layout・枚数・サイズは不変、textureの**中身**だけ変わる）
2. テーマatlasを2Kへ上げる（`GREYBOX_INSTRUMENT_SPEC` の「1K 1枚、2Kは近接必須時のみ」への例外承認が要る）
3. 現状の粗い粒で妥協する

## 5.8 detail_repeats（項目1・後半）

方針は「repeatsを上げる」。Pillowを導入して本物のbuilderで検証した（§環境は
`Tools/Textures/README.md`）。**この環境で再生成した45枚は出荷済みPNGと
ピクセル完全一致**するので、builderの再現性は担保されている。

### 単純な引き上げは効かない

repeatsを上げるだけでは逆にディテールが落ちる。bodyの象限で実測:

| 設定 | BaseColor rms | Normal mean&#124;xy&#124; | 粒の物理サイズ |
| --- | ---: | ---: | ---: |
| 現行 3/5/3 | 0.00203 | 0.14182 | 224 mm |
| 10/16/10 | 0.00050 | 0.04778 | 67 mm |
| 16/21/16 | 0.00082 | 0.03474 | 42 mm |
| 16/21/16 + 調整 | 0.00094 | **0.08320** | 42 mm |

原因は `build_v6_material_atlases.py` の定数がタイルサイズに紐づいている点。

- `mirrored_detail_swatch` はswatchを `512 / repeats` pxへ**縮小してから**タイルする
- `normalize_swatch` は `source - GaussianBlur(radius=18)` で高周波を取り出す。
  32 pxのタイルに18 pxのblurをかければほぼ何も残らない
- `normal_from_swatch` の `radius=2.2` も同じくタイルサイズに追随しない

blur半径とgainをタイルサイズに比例させる（`opus5_candidate_atlas_build.py --tuned`）と
normalの起伏は 0.03474 → 0.08320 まで回復し、現行の約59%を保ったまま
粒は224 mm → 42 mmになる。候補は `textures/Repeats{A,B,BT}/`、比較は
`contact_sheets/ContactSheet_*_AtlasDetail_Repeats*.png`。

恒久対応は `build_v6_material_atlases.py` のswatch定数をタイルサイズ相対へ直す
こと。tracked fileの変更になるためCodexとの合意事項として
[`docs/OPUS5_CODEX_ALIGNMENT.md`](OPUS5_CODEX_ALIGNMENT.md) §4.2へ出した。

### 破棄した検証

一度、既存atlasの象限を再タイリングする方式で評価しようとしたが、
すでに縮小・正規化済みの象限をさらに縮小するためbuilderと等価にならず、
結果を過小評価していた。スクリプトと生成物は削除済み。

## 6. Open items

1. **可動方向の確定**（§5.5）。Unity側で1回確認する。
2. **UVとテクスチャ**。次の作業として着手する。現状 ProductionReady のUVは
   `bpy.ops.uv.smart_project` の自動展開をatlas象限へ押し込んだもので、
   ハイポリからのnormal / AOベイクは行われていない。近接品質の天井はいま
   geometryではなくmap側にある。Geminiレビューの P1-2 も同じ指摘。
3. **atlas box projection**。`pbr_emissive_*` でguard側面に出る強いcyanは
   既存atlasのbox投影由来で、baselineと候補で同一。2の作業範囲。
4. **Throttle palm gripの指掛かり**。現状はcrown + 滑り止めinsertまで。
   指の凹みは2でnormal mapへ委ねる想定。
5. **triangle余裕**。MeterRound 364 / Lever 568 / Throttle 980。他テーマへ
   展開する場合、Forge BrassとOrbital Analogのbaselineは密度が異なるため、
   同じ手順で予算超過しないか個別に測る必要がある。

## 7. Not done (out of scope for the pilot)

- 39モデルへの展開
- `*_Material.blend` / `*_Triangulated.blend` / `*_ProductionReady.blend` の生成
- staging FBX / staging prefab の生成、Unity motion audit、Quest実機確認
- texture atlas の変更
- `scripts/run-blender-52-smoke.sh --all`（現行39 ProductionReady対象のため、
  候補承認後の回帰確認で使う）

## 8. Version control note

commitは行っていない。`ArtSource/Blender/BrushUp/` は現時点で untracked かつ
`.gitignore` の対象外なので、`git add .` を実行すると review PNG 約80 MBを
含めて全部が入る。

`.gitignore` の既存方針（`HardSurfacePrototype/`, `Refined/`,
`ThemeSilhouetteV5/` は除外し、`ThemeHardSurfaceV6/` は
`*_ProductionReady.blend` と `*.report.json` だけを残す）に揃えるなら、
BrushUp workspaceも「候補blendとreports/だけ追跡、review画像は除外」が自然だと
思われる。`.gitignore` はtracked fileなので本パイロットの範囲外として変更して
いない。

## 9. Changes from R1

R1提出後のレビューを受けた変更。

1. **干渉計測を作り直した。** R1は `BVHTree.overlap()` の結果をそのまま数えて
   いたが、これは広域判定で、数十mm離れた三角形も対にする。さらに接触位置を
   可動側三角形の重心で代表させていたため、joined meshの大きなfan三角形では
   位置が大きくずれていた。R2では三角形同士の正確な交差判定を行い、交差線の
   実座標で位置を判定している。**R1レポートの干渉数値は破棄してほしい。**
   結論が変わった項目:
   - Throttleの「762 → 128」は計測の副産物だった。baselineにinterface外の
     貫通は無かった（ただしlimit stopと軸の交差自体は実在し、修正済み）
   - MeterRoundの「360 → 0」の内訳は目盛りではなく盤面（bezel前面）だった
2. **Lever slotを実装した**（R1では未修正として次revisionへ送っていた）。
   interface外接触 204 → 0。
3. 形状の追い込み: MeterRoundの円形分割を24へ、Leverのdetent歯を台形へ、
   guide lipをslot縁と面一にして軸との干渉を解消。
4. 可動姿勢の描画枠を専用化した。R1ではThrottleの70°時にgripが画面外へ出ていた。
