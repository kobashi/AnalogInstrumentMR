# V6 asset の既知欠陥

確認済みで未修正のV6アセット欠陥を記録する。修正はそれぞれの担当スコープで
別変更として行い、ここへ結果を追記する。

## D-1. Button 3テーマの emissive glyph が生成時に失われている

- 状態: **candidate解決済み、production未統合**（Gate A承認、alignment §51）
- 影響範囲: `OrbitalAnalog/Button`, `ForgeBrass/Button`, `KineticSafety/Button`
- 検出: `Tools/Blender/opus5_uv_atlas_audit_all.py`（39モデルsemantic role監査、
  2026-08-09）。`unexpected_missing_readout` として継続的に失敗する
- 分類確定: `docs/OPUS5_CODEX_ALIGNMENT.md` §10.2

### 症状

3テーマとも、Button の V6 Retopo に `readout` role を持つ面が1枚も無い。
`MAT_<Theme>_V5_Readout` の datablock は残っているが、参照する object が無い。
結果としてButtonは暗所で光る要素を一切持たない。

runtime契約（shared material 2枚**以下**）には違反しないため、validatorは
通ってしまう。

### 原因

`Tools/Blender/generate_theme_hardsurface_v6_remaining.py` の `add_button_detail`:

```python
travel = descendant_named(root, "button_travel")
remove_mesh_descendants(travel)
```

V5の `generate_theme_silhouette_v5_remaining.build_button` は、cap / dome と
一緒に `button_glyph` を `mats["readout"]` で作り `button_travel` へ親付けする
（同ファイル内、`v4.accent_bar("button_glyph", 0.030, 0.006, 0.0, 0.0,
glyph_surface, mats["readout"])`）。

V6のdetail passは可動島のmeshを**全削除**してから plunger / face / gasket を
body と metal だけで作り直しており、glyph を再生成していない。3テーマで
同じコードパスを通るため、症状が揃って出る。

### 修正方針

1. `add_button_detail` の各テーマ分岐で、face を作った後に readout の glyph を
   再生成し `travel` へ親付けする。深さは V5 の `glyph_surface`
   （orbital 0.058 / forge 0.112 / kinetic 0.080）を起点に、V6で作り直した
   face の前面へ合わせ直す
2. 再生成後に検証する
   - triangle budget（Button は 5,000 以下）
   - runtime material 契約が opaque + emissive の2枚以内に収まること
   - `button_travel` の 14 mm 押下全域で glyph が guide へ不自然に貫通しないこと
   - `opus5_uv_atlas_audit_all.py` の `unexpected_missing_readout` が空になること
3. 固定条件の視覚比較（emissive OFF / ON）を取る

Gemini レビュー（`docs/reviews/`）の MODEL 05 「ボタン表面に機能アイコンを
テクスチャ（Emissive）で追加」とも整合する。glyph 形状を戻したうえで、
アイコン自体を atlas 側で表現するかは別途判断する。

### 着手条件

現行の Kinetic Safety 3-model pilot（MeterRound / Lever / Throttle）の範囲外。
pilot の candidate 専用 Unity staging を止めない。ただし39モデルへの形状
brush-up展開、または active asset 更新の前には本項目を通すこと
（`docs/OPUS5_CODEX_ALIGNMENT.md` §10.2）。

## D-2. ForgeBrass Buttonのplungerが押下中にhousingへ貫通する

- 状態: **未修正（candidate計測で確認）**
- 影響範囲: `ForgeBrass/Button`
- 検出: Button D-1 candidateの0〜14 mm exact triangle-triangle sweep
  （`docs/OPUS5_CODEX_ALIGNMENT.md` §50.4、§51）
- D-1との関係: glyphの有無にかかわらず同一に発生し、D-1が追加した接触ではない

### 症状

`forge_button_v6_octagonal_plunger`が4 mm押下から`housing`へ接触し、29 sample中21 sample、
最大62 triangleで重なる。guide / gasketの摺動interfaceとは別のnon-interface pairである。

### 扱い

D-1 candidateの承認とKineticSafety Gate Bは妨げない。ただし、ForgeBrassを含む39 candidateの
Gate C完了およびactive asset更新前に、意図した内部収納か視覚上の貫通欠陥かを断面・外観・
可動全域で判定する。欠陥ならhousing内部clearanceまたはplunger後端形状をcandidate経路で修正し、
pivot、14 mm travel、外観、triangle/material contractを維持して再監査する。

## D-3. Meterの針が掃引端で外周目盛へ接触する

- 状態: **D3差分は解決済み。OrbitalAnalog combined承認済み、KineticSafety combinedはD-6により承認撤回**
  （alignment §60-61、§67-73）
- 確認済み影響範囲: `KineticSafety/MeterRound`, `KineticSafety/MeterMedium`,
  `KineticSafety/MeterLarge`, `OrbitalAnalog/MeterMedium`, `OrbitalAnalog/MeterLarge`
- 予防修正対象: 上記5件に加え、同じendpoint tick familyで最接近0.2771 mmの
  `OrbitalAnalog/MeterRound`
- 非該当: `ForgeBrass` 3サイズ
- 検出: 9モデル、-55°〜+55°、45 sampleのexact triangle-triangle sweep
  （`docs/OPUS5_CODEX_ALIGNMENT.md` §57、§59）

### 症状と診断訂正

KineticSafetyでは`tick_3 / tick_9`、OrbitalAnalogでは`tick_4 / tick_12`が掃引端で針へ接触する。
KineticSafetyはRound / Medium / Largeで最大1 / 4 / 23 triangle、OrbitalAnalogはMedium / Largeで
最大5 / 16 triangleである。

初回診断の「主目盛5本が一律に内側へ伸びている」はaxis-aligned boundsから半径を推定した誤りだった。
vertexから直接測ると、修正対象は停止角に近い2目盛であり、角度ごとに内端半径が異なる。主目盛全体を
後退させない。

### candidateでの解決

比例clearanceを全位置へ適用した結果、掃引端2本に加えて中央1本も基準未満だったため、
KineticSafetyは`tick_3 / tick_6 / tick_9`、OrbitalAnalogは`tick_4 / tick_8 / tick_12`の
必要半径より内側の頂点だけを後退させた。6モデルとも0.7 / 1.4 / 2.1 mm以上を満たし、
外周tickの接触は0件になった。needle、pivot、sweep、目盛の外端・幅・向き、triangle / vertex数、
model boundsは不変である。

このD3 candidateはproduction baselineから生成した専用revisionで、既承認のKineticSafety
MeterRound R2およびMeterMedium / Large B2 brush-upを含まない。したがってKineticSafety 3件は
D3 Blendをそのままactive assetへ置換せず、Gate C前に承認済みbrush-up枝へ同じD3差分を合成して、
combined candidateとして視覚比較と全監査を再実行する。OrbitalAnalog 3件もD-4および将来のbrush-upと
合成した最終candidateで再監査する。

### 扱い

針の長さ、pivot、±55° sweep、目盛の意味を維持し、対象2目盛の内端だけを掃引包絡から後退させる。
clearanceはサイズに比例させ、Round / Medium / Largeでそれぞれ**0.7 / 1.4 / 2.1 mm以上**とする。
これは接触の無いForgeBrassの実測0.7106 / 1.4213 / 2.1319 mmを下回らない基準である。
修正後は9モデルのexact sweep、min / max画像、triangle / bounds / material contractを再監査する。

Gate B2 / B3のbrush-up差分承認と、影響しないarchetypeのGate B継続は妨げない。ただし、対象meterの
active asset統合およびGate C完了はcombined candidateの再監査完了まで保留する。

## D-4. OrbitalAnalog Meterのinner scaleが針と深さ方向に分離されていない

- 状態: **D3_D4 combined candidate解決済み、production未統合**（alignment §67-68）
- 影響範囲: `OrbitalAnalog/MeterRound`, `OrbitalAnalog/MeterMedium`,
  `OrbitalAnalog/MeterLarge`
- 検出: `orbital_v6_inner_scale_*`と針の-55°〜+55°、45 sample exact sweep
  （`docs/OPUS5_CODEX_ALIGNMENT.md` §57.3、§59）

### 症状

Medium / Largeでは`inner_scale_0 / 1`が3 sample、pivot直上の`inner_scale_2`が45/45 sampleで針へ
接触する。Roundはまだ接触しないが最接近が0.0238 mmしかなく、実質的に同一深さである。半径方向へ
後退させる先がないため、D-3の外周目盛修正では解決しない。

### 扱い

3サイズとも針とinner scaleを深さ方向へ分離する。実装前に、dial / glass / housingとの新規接触を
生まないY位置と、Round / Medium / Largeで0.7 / 1.4 / 2.1 mm以上のclearanceを満たす提案を
断面計測付きで提示する。針の長さ・pivot・sweep、readoutの視認性、mount / bounds contractは維持する。
D-4修正完了までOrbitalAnalog meter 3件のactive統合とGate C完了を保留する。

read-only調査では、外周側の弧を針の背後へ、Medium / Largeの中心markを針の前へ移す案が、
針との0.7 / 1.4 / 2.1 mm clearanceとbounds不変を満たした。前後関係と視覚差が小さい点は妥当である。
再調査で、移動するinner scale対needle以外の全static meshと、needle対その他static meshをpair別の
before / proposed差分としてexact判定した。3サイズとも新規接触0、problems 0で、Medium / Largeでは
中心markとdialの既存接触も各1件解消する。承認済みD3 candidateへD4を重ねた3サイズのcombined
candidateは、D3 tick clearanceとD4 depth clearanceを同時に満たし、39モデル監査と視覚比較をPASSした。

## D-5. Toggleの可動switchがretaining ringへ貫通する

- 状態: **Gate C readiness到達、production未統合**（alignment §65-116）
- 影響範囲: `OrbitalAnalog/Toggle`, `ForgeBrass/Toggle`, `KineticSafety/Toggle`
- 検出: 0°〜56°、27 sampleのobject別exact contact、clip cutaway、grid占有体積推定
- Gate B3との関係: production baseline由来で、B3 guard形状が追加した退行ではない

### 症状

可動`switch` meshが`KineticSafety_toggle_v6_fixed_retaining_ring`を横断する。
初期調査のgrid占有率32.9%は、後のmigration監査で低解像度grid依存と判明したため定量根拠から撤回した。
一方、deterministic mesh-level判定ではlegacy axleとaxle除去後shaftの実貫通が3テーマで確認され、
これはbore内周のshaft fitや表面接触ではない。

同じringと`KineticSafety_toggle_v6_hemisphere_joint`の重なりは別扱いとする。generatorはjoint radiusと
ring major radiusをともに0.024 mとして明示的にball retainerを構成しており、こちらは意図した
retaining stack overlapである。

### 原因

V5 `build_toggle`は`switch_shaft / switch_axle / grip`をjoinして単一`switch` meshにする。V6
`add_toggle_detail`は新しいhemisphere joint / retaining ring / socketを追加する前に
`remove_named_meshes(..., "switch_axle")`を呼ぶが、axleはすでに`switch`へjoin済みで独立objectではない。
したがって削除は何もせず、旧axle geometryが新しいretaining ring内へ残る。

connected component調査ではlegacy axleが27/27 sample接触する主因だったが、axleを除去してもshaftが
11〜14 / 27 sampleでring環材へ接触する。旧grid占有率7.4〜8.9%は定量根拠から撤回したが、二層判定で
1.434〜2.563 mmのpenetrationが残るため、shaft-in-bore fitとして許容できない。D-5はaxleだけでなく、
全travelでのshaft / ring clearanceも含む。

### 扱い

legacy axle componentの除去案Bを採用候補とする。均一bore拡大とshaft縮径では、pivotがring深さ帯にあるため
接触0へ到達しないことをparameter sweepで確認した。ring全体を深さ方向へ退避するとshaft接触0になる一方、
hemisphere joint保持をほぼ失うため採用しない。

次に、shaftが通る掃引sectorだけを開く局所slot / keyhole形状をdesign-onlyで評価する。保持ringの側面・反対側を
残し、grip、pivot、0°〜56° travel、hemisphere jointの保持関係を維持したまま、`switch x ring`接触0、ring材占有0、
標準サイズ0.7 mm clearanceの可否を測る。この案でも成立しない場合に限り、残留占有の受入れまたはrest角 / pivot /
Unity offsetを含むmotion contract変更を判断する。B3 guard candidateへ直接混ぜず、欠陥修正を分離して全travel contact、
断面、triangle / bounds / hierarchy / material contractを再監査する。

D-5修正完了まで3テーマToggleのactive統合とGate C完了を保留する。whole
`switch x retaining_ring` pairをnamed allowanceにして欠陥を隠してはならない。

### 承認済みdesign proposalとnamed allowance

production ring断面を再構築する`arc_band`案は、テーマ固有profileとfacetを失うため不採用とした。
production ring copyからslot sectorだけをEXACT Booleanで除去する方式は、slot外surface deviation 0、
material / hierarchy維持、closed / manifold / outward、triangle非増加を満たす。

画像ベース比較と27 pose監査により、採用half angleはOrbitalAnalog ±17.0°、ForgeBrass ±19.5°、
KineticSafety ±22.0°とした。legacy axle componentを除去した状態でshaft / grip x ringは全pose clear、
最小surface separationは0.295772 / 0.372812 / 0.311540 mmである。

`hemisphere_joint x fixed_retaining_ring`はgeneratorが意図したball-retainer表現であり、ring保持帯内に閉じ、
外面突破、coplanar face、固定画像上のz-fightingがないため、**intentional visual assembly overlap**として
限定named allowanceに確定した。これはcollision-freeまたは保持力保証を意味せず、shaft / grip / axleやwhole
`switch x ring`へ拡張しない。KineticSafetyのseam変動0.198 mmはQuest motionでちらつきがないことを確認する。

Phase M2eで3テーマのisolated candidateを生成し、axle除去、27 poseの`switch x ring`接触0、承認済み最小間隔、
slot外surface deviation 0、mesh health、runtime hierarchy、object inventory、named allowance非悪化、新規contact 0を
確認した。よってD-5差分はcandidate解決済みとする。production / activeへの統合は未実施であり、拡張監査で検出した
`joint_socket`等との既存接触を別工程で分類するまでFBX / Unity stagingへ進めない。

Phase M2iで最終3 candidate（OrbitalAnalog D5、ForgeBrass D5_D10、KineticSafety D5）をFBXへexportし、別processの
Blender 5.2 `--factory-startup`再importで15 object、hierarchy、transform、14 custom properties、axle 0、ring開口、
27 pose clearance、named allowance非悪化を確認した。FBX handoff、Unity隔離staging、source report照合、motion audit、
GPU visual、EditMode 125/125、Quest 3実機視覚・操作をすべてPASSした。active / production統合はGate C判定まで行わない。

### Phase M2fで確定した追加named allowance

拡張監査により、次のpairを限定named allowanceとして確定した。

- 3テーマの`switch x joint_socket`: 接触線はすべて不透明な`hemisphere_joint`内部にあり、外部へ描画されない
- 3テーマの`hemisphere_joint x joint_socket`: socket全頂点がjoint内部にあり、surface crossing 0の内部assembly overlap
- ForgeBrassの`hemisphere_joint x housing`: 27 poseを通じた取付seamで、40 mmのhousing断面を突破せず、
  seam外形変動0.594 mmはjoint自身のfacet sagitta 0.859 mm以内

いずれも**intentional visual assembly overlap**であり、collision-free、物理的保持力、別pairへの許容拡張を意味しない。
ForgeBrassの`switch x limit_stop_1`は可視領域の深い沈み込みなのでallowanceに含めず、D-10へ分離する。

## D-6. KineticSafety Meter brush-up追加部品がneedle pivotでなくmodel原点に配置される

- 状態: **R2 / B2およびKinetic combined承認撤回、新revision修復待ち**（alignment §72-73）
- 影響範囲: `KineticSafety/MeterRound`, `KineticSafety/MeterMedium`,
  `KineticSafety/MeterLarge`のbrush-up candidate
- production baselineへの影響: なし
- 検出: `needle_pivot`とboss / counterweight / zone bandのworld position、全sweep contact

### 症状と原因

`needle_pivot`のworld ZはRound / Medium / Largeで-4 / -8 / -12 mmだが、承認時のbuilderは追加部品を
model原点Z=0で生成していた。Medium / Large combined BlendをCodexがBlender 5.2で直接開いた確認でも、
pivot Z=-8 / -12 mmに対してbossとcounterweightのoriginはZ=0だった。counterweightはpivot配下へ
parentされているため、pivotから偏心した位置を回転する。

builderをpivot基準へ直すと、Mediumのcounterweightがpolygon bezelへ新規接触する。したがって座標だけを
機械的に直して旧承認を維持できず、部品寸法または採用部品の再設計が必要である。

Blender 5.2での独立triangle照合により、motion auditorのpair label / world transformは正しく、接触は実在すると
確認した。`kinetic_polygon_bezel`は名称と外周vertex半径からringに見えるが、実体は`v4.cylinder_y`で生成した
solid 12角柱であり、front cap triangleが中心を横断する。vertexの最小半径だけでは面内部を判定できない。
counterweightはこのcap面と交差しているため、監査結果を縮小で黙らせず、depth分離またはdial / bezel構造を
再設計する。

### 扱い

既存R2 / B2 / R2_D3 / B2_D3成果物は上書き・削除・復元せず、失敗を含む監査証跡として凍結する。
MeterRoundはR3、MeterMedium / LargeはB2Pなどの新revisionをproduction baselineから生成し、すべての
追加部品を実pivot基準へ置く。Mediumのcounterweightは縮小・形状変更・不採用を比較し、全sweepで新規接触0、
機能説明と視覚品質が両立する案を選ぶ。修復brush-up承認後にだけ、承認済みD3頂点差分を新revisionへ再合成する。

## D-7. KineticSafety WindowMeterのneedleがdial・armor ring・9 ticksへ貫通する

- 状態: **baseline欠陥、design proposal待ち**（alignment §72-73）
- 影響範囲: `KineticSafety/WindowMeter`
- 検出: -55°〜+55°、23 sampleのobject別exact contact

needleは全23 sampleでdialおよびarmor ringへ接触し、15本中9本の`window_tick`とも掃引中に接触する。
B5 candidateのboss追加前後で同一なのでB5が導入した退行ではないが、active統合可能な状態ではない。
needle / dial / armor ring / tickの深さ・半径を断面計測し、pivot、sweep、readout、mount、boundsを維持して
全接触を解消するdesign proposalを先に作る。B5 candidateは提案解決後にcombinedとして再提出する。

## D-8. KineticSafety WindowPanelのvaneがdisplay・status bar・inner bezelへ貫通する

- 状態: **baseline欠陥、design proposal待ち**（alignment §72-73）
- 影響範囲: `KineticSafety/WindowPanel`
- 検出: -42°〜+42°、29 sampleのobject別exact contact

vaneは`kinetic_recessed_display`、3本すべての`kinetic_status_bar`、
`kinetic_v6_segmented_inner_bezel`へ掃引中に接触する。B5 candidateのcap / hood追加前後で同一だが、
表示部を可動部が横切るため許容interfaceにはしない。vaneと表示層の深さ分離または掃引envelope外への
表示再配置をdesign-onlyで比較し、pivot、±42° sweep、表示意味、mount、boundsを維持する。

## D-9. [クローズ] KineticSafety Meterのneedle blade侵入という旧判定

- 状態: **クローズ。surface tangentをvolume penetrationと誤分類していた**（alignment §79-92）
- 影響範囲: `KineticSafety/MeterRound`, `KineticSafety/MeterLarge`
- 非該当: `KineticSafety/MeterMedium`のneedle blade
- 検出: joined needleをconnected componentへ分けた-55°〜+55°、23 sample exact sweep

### 症状と帰属

`needle`はbladeとhub軸を含むjoined meshである。component別に測ると、hub軸は3サイズとも
`kinetic_polygon_bezel`へ接触するが全接触点がbearing radius内にあり、意図したmount接触である。
一方、bladeはRoundで半径約2.0〜42.9 mm、Largeで約5.9〜118.7 mmまでplateへ接触し、
bearing radius外へ達する。Mediumではblade対plate接触は観測されない。

`kinetic_polygon_bezel`は名称上bezelだが、実体は中心capを持つsolid 12角柱である。Round / Largeのbladeは
このcap面を横切っており、軸受許可やnamed allowanceで隠してはならない。サイズ間の非対称は単なる
world pivotずれではなく、blade / plateの寸法比にも依存する。

### 扱い

D-6はbrush-up追加部品のpivot配置不良、D-9はproduction baselineのblade / plate関係なので別欠陥として扱う。
中心を開口して実bezel化する案はcounterweight clearanceとD-9を同時に解く有力候補だが、現design surveyは
counterweightだけを開口後sweepしている。候補生成前にneedleを含む可動島全体を再監査し、D-3の既知tick接触と
D-9解消、新規接触0を分けて証明する。plateのtriangle数もbefore / afterを同一metricで再計測し、固定カメラで
開口後のbezel幅、文字盤・zone bandの視認性、hub / boss支持を比較する。

補正survey（alignment §81-82）では、小開口後もRound / Largeのblade接触が残るだけでなく、Mediumの
`needle x plate`がbaselineの軸受内hub接触から半径約38〜80 mmの軸受外接触へ変化した。pair名が同じため
`new pair 0`では検出できなかったcandidate退行である。さらにLargeのjoined baseline監査はcomponent別監査と
矛盾している。円形outer ringで元12角形外周を膨らませる案は採用せず、category遷移guardとcomponent監査を
修正してから、元外周保存の開口案とD-9修正案を再比較する。

D-9単独によるKineticSafety MeterRound / Largeのactive統合・Gate C保留は解除する。
D-3、D-6など他項目のgateは引き続き有効である。

### §83で判明した監査primitiveの問題

joined / component不一致のtriangleを追跡すると、bladeについて欠陥根拠としていた軸受外交点は
plate裏面との深さ0接触だった可能性が高い。従来の`triangle_contact_points()`はsurface contactを返すが、
それだけではvolume penetrationを証明しない。一方、別の内外判定では3サイズともhub側がplate材内部へ入り、
深さは3.50 / 5.43 / 7.18 mmとサイズ比例した。これは意図したmount構造の可能性がある。

このため「Round / Largeのbladeがsolid plateへ侵入する」というD-9の旧結論を確定事項として使わない。
接触点は消さず、正規化signed distanceとclosed-mesh内外判定を分離した二層監査でhub / blade別に再測定する。
bladeのtolerance超penetrationが0ならD-9は誤分類としてcloseし、存在する場合だけcomponent、pose、depthを根拠に
欠陥を継続する。再分類完了までは既存成果物を削除・上書きしない。

### Phase M1での最終判定

Blender 5.2の二層監査で3サイズ、23 poseを再測定した結果、blade componentはすべて
surface tangent、crossing 0、0.01 mm超penetration 0だった。最深値はRound 0.000009 mm、
Medium 0、Large 0.000029 mmで、いずれもboundary tolerance 0.0001 mm以内である。

hub componentは3サイズともplate内へ3.500 / 5.425 / 7.175 mm入るが、全pose共通、サイズ比例、
接触半径がbearing内であり、意図したmount構造と分類する。旧監査はRound / Largeのblade tangentを
crossingとして数え、「軸受外へ食い込む」と誤って解釈していた。

以上によりD-9は欠陥ではないとしてクローズする。Round / Largeのbladeが軸受外でclearance 0になる事実は
surface contact記録へ残すが、形状修正対象にはしない。既存の失敗証跡は監査primitive移行履歴として保持する。

## D-10. ForgeBrass Toggleのshaftがrest側limit stopへ沈み込む

- 状態: **Gate C readiness到達、production未統合**（alignment §107-116）
- 影響範囲: `ForgeBrass/Toggle`
- 検出: 0°〜56°、27 sampleのcomponent別exact contactと可視領域判定
- D-5との関係: productionとD-5 candidateに同値で存在し、D-5が導入した退行ではない

### 症状

`switch`のshaftが`ForgeBrass_toggle_v6_limit_stop_1`へ0°で2.893187 mm、2.1538°で1.555480 mm、
4.3077°で0.223896 mm侵入し、6.4615°以降はclearになる。最悪poseの接触点264点は他の不透明meshに
埋没しておらず、rest poseで露出したseamを形成する。stopの反対側へは突破していないが、終端で表面接触する
状態ではなく、shaftがstop内部へ沈んでいるためnamed allowanceにはしない。

### 原因と扱い

generatorはstopを`z = joint_radius * 1.55`へ置き、寸法を`joint_radius * 1.10 x 0.42 x 0.12`とする。
ForgeBrass固有のshaft / joint / support寸法との組合せで、rest側stopの内端がshaftの掃引包絡へ約2.9 mm入り込む。

production、D-5 candidate、generatorは直ちに変更しない。rest 0°でsurface crossing / tolerance超penetration 0、
表面間隔0〜0.10 mm、0°超で再侵入なしとなるstop位置・内端形状をdesign-onlyで比較する。反対側stop、switch、
D-5 ring slot、pivot、0°〜56° motion、hierarchy、material、外形バランスを維持し、全movable-static pairで
新規contact 0を確認してからisolated D-10 candidateを作る。D-10解決までForgeBrass ToggleのFBX / Unity staging、
active統合、Gate Cを保留する。

Phase M2gの3案比較では、stop全体の+Z移動はgripへ7.363223 mmの新規侵入を作るため不採用、全面後退は
接触を解消するがstopが目に見えて薄くなるため不採用とした。shaft幅へ左右0.6 mmを加えた半幅6.4496 mmだけを
座ぐり、floorをY=-55.0568 mmへ置く`seat_notch`案を承認する。0°の離隔0.050001 mm、0°超の再侵入0、
新規contact 0で、rest obliqueの画素差は0.617%。外側flankと9 mm奥行き、object identity、boundsを維持し、
追加triangleは38である。承認済みD-5 candidateへこの差分だけを加えたcombined candidateを次に生成する。

Phase M2hで承認済みD-5 candidateへ`seat_notch`だけを適用した
`BL_Toggle_ForgeBrass_V6_Opus5_D5_D10_Retopo.blend`（SHA-256 `dad488540fd16db33c8fc6dff189ef6844e630e959eb8aea14ef734ab21ccb8a`）を生成した。
D-5 sourceとの差分objectは`limit_stop_1`だけで、27 poseのcrossing / penetrating 0、rest離隔0.050012 mm、
再侵入0、新規contact 0、named allowance非悪化、mesh healthとruntime contractを確認した。D-10はcandidate解決済みとし、
FBX round-tripとUnity stagingを経るまでproduction / activeは変更しない。

Phase M2iのFBX round-tripでもseat半幅6.4496 mm、floor Y=-55.0568 mm、rest離隔0.050008 mm、再侵入0を復元した。
FBX handoff、Unity隔離staging、motion audit、GPU visual、EditMode 125/125、Quest 3実機視覚・操作をすべてPASSした。
production / active統合はGate C判定まで行わない。
