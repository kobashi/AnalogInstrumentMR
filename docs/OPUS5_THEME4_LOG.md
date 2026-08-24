# 第4テーマ試作ログ

`docs/OPUS5_THEME4_SESSION_HANDOFF.md` に従って作業する並行セッション専用の記録。

**節番号は `T1.` `T2.` … と独自に振る。** `docs/OPUS5_CODEX_ALIGNMENT.md` の通し番号と混ぜない。
alignment docへは追記しない（同時appendで書き込みが消えるため。handoff §1.1）。

試作完了後、要約のみを本体セッションがalignment docへ1節として統合する。

各節に含めるもの: 変更内容 / 実測値 / 全成果物のSHA-256 / 触っていないものを列挙したgate段落。

---

（ここから記録）

T1. `docs/OPUS5_THEME4_SESSION_HANDOFF.md`と`docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md`を読み、
Phase 1に着手した。並行セッションではなく本体セッションで直列に進める判断（§239.1の変更）。

T2. `Tools/Blender/opus5_theme4_reference_survey.py`を書き、既存V6 ProductionReadyの
MeterRound / Lever / Toggleを3テーマ分read-onlyで実測した。authoring frameは
**mount面 max Y == 0、正面 −Y**（FBX変換でUnityのZ=0 / +Zになる）。
回転軸は`MockInstrumentFactory.cs`で確認し、Meterが`Vector3.forward`（Blender Y軸）、
Lever / Toggleが`Vector3.right`（Blender X軸）。**仮定せず実測・確認した。**

T3. 発見: **既存3テーマのenvelopeは互いに一致していない。**
MeterRoundは0.162 / 0.142 / 0.154幅と揃わず、3テーマともP0 spec表の0.140を超える。
handoff §11の完了条件「envelope・pivot・可動域が既存3テーマと一致する」は
そのままでは定義不能である。**P0 spec表の値を上限として採用した。**

T4. `Tools/Blender/opus5_theme4_machined_ergonomics_p1.py`で3機種のgreyboxを構築した。
booleanは使わず、明示的なbmesh shellの積層のみ。理由はbooleanがn-gonを残し、
完了条件のnon-manifold 0を脅かすため。

T5. 修正した自分の誤り（1）: 可動部の頂点を原点基準で作りながらpivotへ親付けし、
`matrix_parent_inverse`で位置を保持していたため、handle / switchがpivot上に乗らず
**mount面を突き抜けた**（maxY +0.004 / +0.002）。可動部はpivotローカルで作るのが正しい。

T6. 修正した自分の誤り（2）: **swept envelope gateを自分で発明していた。**
可動域を含めてenvelope内に収まることをgateにしたが、greybox factory自身のLever
（pivot Unity z=0.065、grip 0.16先、±24°）は**z=−0.011すなわち壁の裏まで振れる**。
envelope契約はrest poseの寸法であり、既存3テーマもこのgateを通らない。
**計測は残しgateからは外した。**

T7. 修正した自分の誤り（3）: MeterRoundのfront housingを**中空リングでなく中実シリンダー**で
作っていたため、dial・collar・needleがhousing内部に飲み込まれ、計器が無地の円盤に見えていた。
annulusへ変更。tubeはslugより高コストなのでHOUSING_SEGMENTSを24→20へ下げて予算内に収めた。

T8. 修正した自分の誤り（4）: Lever / Toggleのplate四隅の座ぐりボルトを`y_face=0.0`
（mount面＝壁側の裏面）に置いており、**壁に埋まって完全に不可視**だった。plate前面へ移した。
MeterRoundの4本もflange間に埋もれていたため、bezel前面（荷重経路上）へ移した。

T9. 修正した自分の誤り（5）: 輝度測定で被写体マスクの閾値を0.10としたが、
**背景の輝度が0.196**であり、背景ピクセルを被写体として集計していた。
p5が全テーマ0.196で並んでいたのがその証拠。モード値による背景マスクへ修正した。

T10. 発見: **V6 ProductionReady Blendにはシェーディングが入っていない。**
Principledのbase colorは未接続で既定の0.8グレー、atlas画像はデータブロックとして
存在するがノードに繋がっていない（見た目はUnity側で組む設計）。
そのまま描画すると4テーマが同じ粘土色で並び、**§10.2のT9判定が原理的に不可能**だった。
比較時のみBaseColorを結線する処理を入れた（保存はしない）。

T11. 発見: 共有ヘルパー`opus5_brushup_kinetic_review.py`のGLYPHSテーブルに**`K`が無く**、
これまで生成された全contact sheetのKineticSafetyラベルが`INETICSAFETY`になっていた。
1エントリ追加で修正した。

T12. PHASE 1 COMPLETE（gate通過）。ただし造形の読みやすさに差がある。
MeterRoundは既存3種と同等に読めるが、**Lever / Toggleは明らかに弱い。**
形状承認の判断を待つ。詳細は`docs/OPUS5_CODEX_ALIGNMENT.md` §246。

T13. ユーザー要望により、**手が触れる部分へローレット状の滑り止め歯**を追加した。
style guideの「Geometry versus texture」はシボ（表面グレイン）をnormal mapへ委ねるが、
**計器スケールでグリップとして読める粗さの歯はgeometry側**である。
共有1K atlasでは歯のピッチが数texelにしかならず、normal mapでは成立しない。
`knurl()`ヘルパーを追加し、Lever gripへ9枚、Toggle gripへ7枚の歯を入れた。
可動部のtriangle予算に余裕が大きいため（上限1,500に対しhandle 48 / switch 36）、形状で表現できる。

T14. 歯の初期値（duty 0.55、proud 1.3 mm）は溝が広く深すぎて**独立したフィンに見えた。**
ローレットは大部分が山で溝が細いので、duty 0.72、proud 1.0 / 0.9 mmへ調整した。

T15. 修正した自分の誤り（6）: **Toggleのswitchを手前（−Y）向きに作っていた。**
既存3テーマは全て**上（+Z）に立つシャフト**である（実測: OrbitalAnalogのswitch_pivotは
z = 0、switchはz = 0.075まで伸びる）。正面から見て潰れ、ブロックの塊にしか見えなかった原因。
立ち上がる形へ作り直し、end stopもshaftを挟む位置へ移した。

T16. Phase 1再提出。triangle: MeterRound 1,384 / Lever 728 / Toggle 632。
全gate通過、non-manifold 0、zero-area 0。**FBXは作っていない。**

T17. ユーザー要望により、ローレットを**ベゼルと整備用の取り外し部**へ拡張した。
`toothed_annulus()`を追加。annulusの外周半径を1セグメントおきに変えるだけなので、
**歯はセグメント数以上の三角形を消費しない。**
MeterRoundのbezelを32セグメント16歯の押さえリングへ、
Lever / Toggleのshell前面へ`access_cap()`（ローレット付きねじ込みキャップ）を追加した。

T18. 判断: MeterRoundのbezel前面にあった座ぐりボルト4本を**削除した。**
ローレットリングは「手で回して外す」、座ぐりボルトは「工具を持ってこい」であり、
**同一部品に両方あると信号が矛盾する。**housingの締結は2枚のフランジ挟みと
その間のガスケットで読ませる。浮いた予算でHOUSING_SEGMENTSを20→26へ戻した。

T19. 最終。triangle: MeterRound 1,320 / Lever 916 / Toggle 820。全gate通過。
non-manifold 0、zero-area 0。**FBXは作っていない。**

T20. ユーザー指摘「テーパーを入れる。全体的にキューブの素人モデリングになっている。
ドライバー用の溝や穴も欲しい」への対応。指摘は妥当である。
2°の抜き勾配は視認できず、**稜線が一切面取りされていない**ことが原因だった。

T21. `chamfer()`（bmesh.ops.bevel、面角25°以上の稜線のみ）、
`driver_slot()`（2つの山の間の谷をマイナス溝として読ませる。booleanを使わない理由は
n-gonとnon-manifoldのリスク）、`driver_port()`（縁付きの凹んだアクセス穴）を追加した。

T22. 全稜線の面取りは**三角形が約3.7倍**になり、
MeterRound 2,752 / Lever 4,068 / Toggle 3,288となって
style guideの「1 objectあたり1,500 triangles以下」を大きく超えた。
**大きな平面（plate、shell、grip）に限定**した。小物（ねじ、detent、stop、port）は
5 mm程度の寸法であり、0.6 mmの面取りは最初のmipで消えるため入れていない。

T23. 最終。MeterRound 1,384（body 1,296 / needle 88）、
Lever 1,796（body 1,224 / handle 572）、Toggle 1,464（body 1,024 / switch 440）。
全gate通過、non-manifold 0、zero-area 0。**FBXは作っていない。**

T24. ユーザー要望「大きな部品はカバーや取り付け用のドライバーの穴や穴を塞ぐカバー、
取り付け用の嵌め込みなどを入れる」への対応。次のヘルパーを追加した。
`mount_hole()`（縁＋皿座＋奥のボア床の3リングで「開けて座ぐった穴」に見せる）、
`blanking_plug()`（溝付きの塞ぎ栓）、`cover_panel()`（面取り＋四隅の溝付きねじのカバー板）、
`register_step()`（印籠継ぎ＝嵌め込み段）、`cable_gland()`（導管ボス＋ローレットナット＋スタブ）、
`nameplate()`（銘板座）、`rib()`（補強リブ）。

T25. 配置。MeterRoundへ嵌め込み段・グランド・塞ぎ栓。
Toggleへ嵌め込み段・銘板座・補強リブ2本・取付穴・塞ぎ栓。
Leverへ嵌め込み段・カバー板・グランド・銘板座・取付穴2箇所・塞ぎ栓。

T26. **カバー板をハンドルの真後ろに置いていた**ため、主要な視点から全く見えなかった。
シェル左側の空き面へ移動した。

T27. triangle上限の扱いを変更した。**greybox gateの1,500/objectでは
この部品構成語彙が収まらない**（MeterRound body 1,640、Lever body 2,312）。
`GREYBOX_INSTRUMENT_SPEC.md`はFinal P0 ceilingを5,000としているため、
**今回は5,000をgateとし、1,500の超過をreportに明示**した。
承認済みstyle guideの数値変更にあたるため、**独断で確定せずユーザー確認を待つ**。

T28. ユーザー指摘「レバーの棒と軸の接合のデザインが雑。角で溶接してるような感じで一体感不足」。
指摘は妥当。原因は2つあった。(1)ハブが**角断面のステム**で、回転軸と同心の
ボスになっていなかった。(2)腕が**等断面の棒**で、`frustum_box`はY方向（抜き勾配方向）にしか
断面を変えられず、長さ方向に細らせる手段が無かった。結果として2つの箱が角で重なるだけだった。

T29. `tapered_arm()`（長さ方向に断面が変わる4面の腕）と
`clamp_hub()`（回転軸と同心の割りハブ＋締め付けボルト）を追加した。
腕をハブから生やし、根元32 mm→首17 mmへ連続的に細らせた。
同じ欠陥がToggleのswitchにもあったため、小さい寸法で同様に作り直した。

T30. 更新。Lever handle 572 → 856、Toggle switch 440 → 724。
body側は変更なし。全gate通過、non-manifold 0、zero-area 0。**FBXは作っていない。**

T31. ユーザー承認により、1 objectあたりのtriangle上限を**1,500 → 5,000**へ引き上げた。
`docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md`の`## Runtime limits`を更新し、
承認日と根拠を併記した。scriptのgateも仮定ではなく確定として書き直した。

T32. 修正した自分の誤り（7）: **Leverの5つのdetentが全て中心線上に積み重なっていた。**
配置がz座標だけ弧で計算され、**x座標が0.0のまま**だった。
さらに振り出すはずの行が`* 0.0`で乗算されており無効化されていた（デッドコード）。
x = arc·sin(θ)、z = pivot_z + arc·cos(θ)で正しく弧上へ配置し、寸法も大きくした。

T33. 引き上げた予算で、pivot周りの金物（bearing boss、end stop、detent）へ面取りを及ぼした。
§249.4で「ブロックの集合に見える」と自己報告していた領域である。
Lever 3,168 → 3,456、Toggle 2,088 → 2,216。**5,000以内。**

T34. ユーザー指摘「レバーが巨大化したSwitchの形状である。支点は本体内に収め形状を持たなくて良い。
台座にスリットを設けてレバーがテコで内部の機構に作用しているようになっていれば良い」。
**構造そのものの誤りであり、指摘は妥当。**支点・軸受ボス・カラー・detentブロック・end stopを
すべてシェル外面に出していたため、大型のトグルスイッチにしか見えなかった。

T35. `build_lever()`を全面的に書き直した。支点をハウジング内（y = -0.012）へ収め、
シェル面にスリット（28 × 52 mm）を開け、腕が−Y方向へ出る構造にした。
外部の金物はすべて撤去。代わりにスリット内の摺動板、スリット縁のガイドリム、
スリット脇の5つのdetentマークを設けた。腕はX軸まわりに振れ、先端がスリットを上下に走る。

T36. 修正した自分の誤り（8）: シェル面を**4枚の箱**で作ってスリットを構成したところ、
各箱の面取りが継ぎ目として見え、**「4枚のパネルをねじ止めした面」に見えた。**
`rect_frame()`（穴を持つ1つの閉じたシェル）を追加して1枚の成形品にした。

T37. 修正した自分の誤り（9）: `emit()`が`normal_update()`のみで
**面の巻き方向を揃えていなかった。**閉じたシェルでも向きが不整合だと
`bevel`が穴を作る。`rect_frame`は生成直後はnon-manifold 0だが、
面取り後に**40本のnon-manifold edge**が出ていた。
`bmesh.ops.recalc_face_normals()`を`emit()`へ追加して解消（40 → 0）。
**全プリミティブに効く修正である。**

T38. 更新。Lever 3,132（body 2,604 / handle 528）。全gate通過、non-manifold 0、zero-area 0。
**FBXは作っていない。**

T39. ユーザー要望「レバーは腕全体で引くようなサイズが欲しい。可動域は120度ほど欲しい」。
サイズと可動域はいずれも共有契約に抵触するため、影響範囲を先に確定した。
`InstrumentGreyboxSpecification.LeverMaximumAngleDegrees = 24f`（runtime C#、Codex領域）、
spec表の`control.lever` 0.180 × 0.256 × 0.100 / ±24°、
承認済みstyle guideの「共通visual envelope、pivot、可動範囲は既存3テーマと同一」の3点。

T40. 続くユーザー指示「レバーの可動域は元の契約に合わせて良い。pivotが台座内であれば良い」により、
**可動域は±24°へ戻した。runtime定数は触っていない。**
サイズのみ0.240 × 0.440 × 0.150へ拡大し、pivotは台座内（y = -0.018）に維持した。
長いストロークは角度ではなく**腕の長さ**で得ている。

T41. 修正した自分の誤り（10）: **`world_bounds`が`bound_box`を使っていた。**
オブジェクトのローカルAABBの8隅を変換して外接矩形を取ると、
**回転した部品でAABBが膨張する（箱の箱）。**
Leverのsweepで「腕が壁の裏へ26 mm入る」と報告したが、
実頂点で測ると最遠点は**壁の手前9 mm**だった。
頂点から直接測るよう修正した。**これまで報告したswept値はすべて過大である。**

T42. 修正した自分の誤り（11）: `swept_bounds`が可動域の**両端と中央の3点しか**見ていなかった。
120°のような広い範囲では最悪値が端点に来るとは限らない。25点走査へ変更した。
これによりToggleのswept深さが**0.0647 → 0.0894 m**へ変わった。従来値は過小報告だった。

T43. 修正した自分の誤り（12）: envelopeを**report していたがgateに入れていなかった。**
Leverが1.75 mm超過した状態でgates=Trueと出ていた。`rest_envelope` gateを追加した。

T44. rest時の腕の傾きが浅いと、±24°の−側で腕が壁に入る（maxY +0.036）。
傾きを約25°へ増やして解消した（maxY +0.006、実質ゼロ）。
**既存3テーマのLeverは全travelで壁を貫通する（§246.4）ため、本テーマの方が良い。**

T45. 修正した自分の誤り（13）: **Leverのグリップの滑り止めが本体から剥離していた。**
`knurl()`はaxis="z"のとき一定のyにリブを積む実装だったが、
§254で腕を約25°傾けたため、**グリップのyが長さ方向に移動し、帯だけ元の位置に取り残された。**
最大で約15 mmずれていた。`slope`（dy/dz）引数を追加し、リブがグリップの中心線に追従するようにした。

Toggleのswitch gripは傾いていない（`frustum_box`でyが一定）ため影響を受けていない。

T46. ユーザー指摘「ネジ類は操作時の引っ掛かりをなくすために沈頭鋲のようにするべき」。妥当。
`fastener()`は座ぐりボスを**面より前へ突き出す**構造だった（ボスが面から depth 分手前）。
面より奥へ座を彫った**皿頭**へ作り直した。平らなland、その奥へ落ちる円錐座、
面より奥に沈んだ頭、さらに奥のドライバー溝という順で、**全要素がy_face以降（奥側）**に来る。
`blanking_plug()`も同様に沈めた。

T47. 検証。単体で頂点を測定し、fastener は面に対し **+0.000 mm（面一）**。
blanking_plug は最初 **−0.152 mm 突出**していた（溝のランドが面より手前）。
溝を depth×0.12 → 0.22 奥へ移して +0.000 mm にした。

T48. 途中の計測ミス: ねじ位置から半径12 mmで頂点を探したところ、
**シェル（面より28 mm手前）を拾って「−28 mm突出」と誤判定**した。
部品単体で測り直して解決。**近傍探索の半径が対象より大きいと別部品を拾う。**

T49. 更新。MeterRound 1,728 / Lever 3,312（body 2,828）/ Toggle 2,328（body 1,604）。
全gate通過、non-manifold 0、zero-area 0。**FBXは作っていない。**

T50. ユーザー指摘「ネジのはめ込みに隙間がないため、形状として認識できない」。**妥当。**
§256で座を面より奥へ彫った結果、**booleanを使わない以上パネル面に穴が無く、
円錐座も頭も板の内部に完全に埋まって外から見えなくなっていた。**
近接レンダでパネルが真っ平らに写ったのがその証拠である。

T51. 2度目の失敗。頭を面より僅かに出す方針へ変えたが、
溝を`driver_slot()`（長方形のランド2枚）で作ったため、
**丸い頭ではなく板2枚が貼り付いて見えた。**

T52. `half_disc()`と`slotted_head()`を追加。**半円2枚＋隙間**で丸い皿頭に溝が入った形にした。
突出は0.5〜0.6 mm（頂点実測 −0.600 mm）で、シルエットの縁と陰影の切れ目は出るが
引っ掛かる量ではない。座のリングと合わせて「丸い座に溝付きの頭」として読める。

T53. **重大な作業ミス**: `fastener()`の書き換えで置換範囲を
`def fastener`〜`def join`と広く取ったため、**間にあった補助関数14個をまとめて削除した。**
`chamfer`、`driver_slot`、`mount_hole`、`blanking_plug`、`cover_panel`、`register_step`、
`cable_gland`、`nameplate`、`rib`、`toothed_annulus`、`access_cap`、`rect_frame`、
`knurl`、`tapered_arm`、`clamp_hub`が失われた。
scriptは未追跡でgitから復元できなかったため、全て手で書き直して復元した。
**範囲指定の置換は、範囲内に何があるかを確認してから行うべきだった。**

T54. 更新。MeterRound 1,756 / Lever 3,724（body 3,240）/ Toggle 2,548（body 1,824）。
全gate通過、non-manifold 0、zero-area 0。**FBXは作っていない。**

T55. §254.2の未決事項について、ユーザー判断で**大型Leverを既存`control.lever`とする**ことが決まった。
新規type ID `control.lever_pull`は起こさない。

T56. §261.4の待機解除を受け、Theme 4 Phase 1の造形を再開した。
自分で「弱い」と報告していた**MeterRoundのダイヤル面**へ着手した。
ダイヤルが平坦な無地の皿で、既存3テーマの目盛り付きダイヤルに比べて空虚だった。

T57. ダイヤルを「筐体に落とし込まれた別部品」として作り直した。
座繰りリング（dial_rebate）、目盛りが載る環状の座（scale_land）、
可動端（±115°）を示すインデックスピン2本を追加した。
**目盛りと数字そのものはatlasへ委ねる**というstyle guideの分担は変えていない。
geometryが負うのは「それらが載る場所」であり、これは銘板座と同じ理屈である。

T58. MeterRound body 1,668 → 2,620。上限5,000に対し余裕がある。
全gate通過、non-manifold 0、zero-area 0。**FBXは作っていない。**

T59. ユーザー要望「メーターにはメモリが欲しい」。目盛りをgeometryで入れた。
`radial_tick()`を追加（`frustum_box`は軸平行なので、半径方向を向く目盛りは8頂点を直接置く）。
主目盛り12本・副目盛り11本の計23本を−25°〜205°（針の±115°に対応）へ配置した。
**style guideは目盛りをatlasへ委ねているため、これは意図的な逸脱である。**

T60. ユーザー要望「レバーは筐体側に貫通する部分、梃子の作用点側が欲しい」。
支点より下へ伸びる短腕（`handle_tail`）とローラー（`handle_roller`）を可動部へ追加し、
筐体側にはそれが当たるカム板（`cam_plate`）とピン（`cam_pin`）を置いた。

T61. 修正した自分の誤り（14）: **腕の根元（幅54 mm）がスリット（幅40 mm）より太く、
肩がパネルに乗って開口を完全に塞いでいた。**作用点側を作っても何も見えなかった。
スリットを62 mmへ広げ、腕を46 mmへ細めて左右に8 mmずつ隙間を作った。

T62. 修正した自分の誤り（15）: カム板を`pivot_z - 0.044`へ置いたが、
**スリットの下端より外**であり視認できなかった。`pivot_z - 0.030`へ移した。
ローラーも同様にスリット内へ入れた。

T63. 更新。MeterRound 2,984（body 2,896）/ Lever 3,988（body 3,320 / handle 668）/ Toggle 2,548。
全gate通過、non-manifold 0、zero-area 0。**FBXは作っていない。**

T64. §265でPhase 1形状が承認された。目盛りのgeometry化も承認され、
style guideの文言更新はCodex側で行うとされた。

T65. §265.4の成果物を作成。`export_fbx()`を追加し、承認済みLegacy FBX設定
（`opus5_toggle_fbx_handoff.EXPORT_SETTINGS`に`use_triangles=False`、
`mesh_smooth_type="EDGE"`を上書き）で3機種を隔離treeへ出力した。
`use_triangles=False`は`emit()`が既にFIXED / EAR_CLIPで三角化済みのため、
exporterにBEAUTYで切り直させないためである。

T66. `pose_bounds()`を追加し、−amplitude / 0 / +amplitudeの3姿勢のboundsを記録した。
Blender座標に加え**Unity座標（x, z, −y）へ変換した値**と、
3姿勢の**和集合（collider_union_unity）**も算出した。
Codexが`InteractionCollider`を切る際に軸変換をやり直さずに済むようにするためである。

T67. §265.3のreport修正を反映。`envelope_gate`を`rest pose only`へ、
`swept_within_envelope`をreport-onlyと明記、`all_passed`が`gates`のみの集約である旨を追記した。

T68. §267でCodexが**私の誤り**を指摘した。runtimeは
`Mathf.Lerp(-amplitude, amplitude, value) + rotationOffset`で負のoffsetが付くため、
実可動域はLever **−48°〜0°**、Toggle **−56°〜0°**である。
私は±24° / ±28°の対称で監査していた。
§246.2でfactoryの`rotationOffset: -LeverMaximumAngleDegrees`を読んでいたのに追い切っていない。

T69. **符号の対応を仮定せず実測した。**Blender −48..0とBlender 0..+48の両方でunionを取り、
Codexの実測max Z 0.2835 mと突き合わせた結果、
**Blender 0..+48が一致し、−48..0は一致しない**（0.2425 m）。
したがって**FBXの軸変換で回転符号が反転する。Unity −48° = Blender +48°**である。

T70. 貫通量の食い違いを調査した。可動部の頂点で97点走査したところ、
Blender +48°での最大maxYは**−0.0021**（壁の手前2.1 mm）で**貫通していない。**
Codexの実測は−0.010205である。
**Unityの`Renderer.bounds`は回転オブジェクトでAABBが膨張する** — §254.4で
自分自身に見つけたのと同じ現象であり、これが差の説明になり得る。
ただし裕度2.1 mmは薄いため、形状側にも余裕を取った。

T71. 修正内容。監査角をLever `[0,12,24,36,48]`（Unity `[0,-12,-24,-36,-48]`）、
Toggle `[0,56]`（Unity `[0,-56]`）へ。`sweep_style`を
`one-sided with negative runtime offset`へ。
`mount_clearance`（97点走査、頂点実測）を追加。
tail / roller / camを引き込み、裕度を**2.1 mm → 11.4 mm**へ拡大した。

T72. 結果。clearance Lever +11.402 mm / Toggle +33.8 mm / MeterRound +52.5 mm、
いずれも全姿勢で壁を越えない。Toggleは形状変更なしでreport訂正のみ（§267.3(5)どおり）。

T73. §269でCodexが検証器を`Renderer.bounds`から実頂点方式へ修正し、
**§268.3で私が指摘したAABB膨張が原因だったと確認された。**
Lever clearance 11.402 mmもcollider unionも私の値と一致し、Unity raw-import gateはPASS。

T74. §269.2のreport整合修正を実施。geometryは一切変更していない。
`swept_bounds()`が`sweep_deg`未設定時に**旧対称fallback（±amplitude）へ落ちていた**ため、
`collider_union_unity`（片側）と`swept_*`（対称）が同一report内で矛盾していた。
`sweep_scan()`へ統合し、**掃引に関する全数値を1回の97姿勢走査から生成**するようにした。
走査範囲はLever `[0, 48]`、Toggle `[0, 56]`、MeterRound `[-115, 115]`。

T75. `gates`へ`runtime_motion_clearance`を追加し`all_passed`へ含めた。
top-level `note`を`Phase 1 isolated FBX generated; Unity production integration is blocked`へ更新。

T76. 追加検証: **姿勢由来のcollider unionと97姿勢走査由来のunionが一致するか**を照合する
`collider_union_matches_continuous_scan`を入れた。3機種とも`agrees: true`。
一致しなければ最悪値がdetentの間にあることになり、姿勢リストが基準として不適切になる。

T77. FBXのSHAが変わったがbytesは同一（86,108ほか）。
FBXヘッダの`CreationTimeStamp`が毎回変わるためであり、**geometryは無変更**である。
triangle、bounds、clearance、collider unionはすべて§268と同値。

T78. ユーザー要望「全体的にテーパーを入れて筒や箱っぽさを軽減したい」。
**これはCodexがcloseしたPhase 1 geometryを再び開く変更である。**
`DRAFT_DEG`を2°→5°へ上げ、主要シェルへ明示的な絞りを追加した。
MeterRoundは外径を奥0.068→前0.060へ単調に減らし、Lever / Toggleはplateとshellの
遠端寸法を絞り、Leverにはplateとshellの間へ段付きスカートを追加した。

T79. 修正した自分の誤り（16）: MeterRoundで**内径まで一緒に絞ってしまい、
ベゼル開口（0.047）が目盛り外端（0.0481）より小さくなって目盛りを隠した。**
テーパーは**外径だけ**に掛けるべきであり、内径は開口を決めるので触ってはいけない。

T80. 更新後。MeterRound rest 0.136×0.136×0.064、Lever 0.2388×0.4388×0.1438、
Toggle 0.1191×0.1691×0.061。いずれもenvelope上限内で縮小方向。
clearanceはLever 11.402 / Toggle 33.8 / MeterRound 52.5 mmで不変。全gate通過。

T81. §274でCodexが「bodyとmetalの分離が最も弱い」と指摘。
`metal`のbase colourを0.415/0.428/0.450→0.300/0.312/0.332、
metallic 0.35→0.22、roughness 0.44→0.49へ調整した。
**§274.3が許した「metalだけ1回調整」の範囲である。**

T82. 役割ごとの実レンダ輝度を直接測る`role_swatches()`を追加した。
**計器全体のヒストグラムでは役割別の分離を測れない**（あらゆる面の向きが混ざるため）。
同一照明下の平板4枚で測る。

T83. 修正した自分の誤り（17）: swatchの標本位置を**画像幅の4等分**で取ったところ、
rigの余白のせいで両端が背景に落ち、gasketとreadoutが背景輝度0.194で同値になった。

T84. 修正した自分の誤り（18）: カメラ投影へ切り替えたが、
**平板は頂点側にcentreを与えてオブジェクト原点は(0,0,0)のまま**だったため、
4枚とも同一点へ投影され全て0.324になった。頂点重心を使うよう修正した。

T85. 測定結果。gasket 0.1764 → metal 0.3662 → body 0.5580 → readout 0.8664。
順序どおりに並び、最小差は**0.1898**。§274.2の指摘に対する定量的な回答になる。

T86. テーパー後の再測定で表面積が1.2406→**1.4047 m²**へ増えた（絞りで面が斜めになるため）。
均一texel密度は0.848→**0.797 texels/mm**へ下がった。readoutへ8%配分で2.676 texels/mmは不変。

T87. §277でCodexがテーパー後のgeometryと材質の両方を受け入れ、
Phase 1 gateを再closeした（Unity実頂点97姿勢PASS、SHA一致）。

T88. §277.3のreport-only修正2点を実施。
**Blend / FBX / 画像 / UV / palette を再生成してはならない**という制約があるため、
generatorを直したうえで、既存JSONへ算術的に補正を当てる
`Tools/Blender/opus5_theme4_report_axis_fix.py`を書いた。
生成器を再実行するとBlendもFBXも画像も書き変わってしまう。

T89. 修正内容（1）: `to_unity()`のUnity Yが`+Blender Z`だったが、
`bakeAxisConversion`＋import wrapperのX −90°回転で**Yも符号反転**する。
Codexの実測（MeterRound swept centre Y = +0.000583）が正である。
`(x, z, -y)` → **`(x, -z, -y)`**へ修正した。
**テーパーでメーターがZ方向に僅かに非対称になるまで、この誤りは観測できなかった。**

T90. 修正内容（2）: Phase 2の`atlas_layout.note`が「one object takes 56 per cent」と
数値を直書きしていたが、新形状では60.675%である。数値を持たない文へ改めた。

T91. 検証。3機種のcollider union centreがCodexの実測と完全一致。
Blend / FBXはSHA照合で無変更。
**副作用として`pivot_local_unity`のYも反転した**（Lever: −0.080 → +0.080）。
Codexの実測値が無い項目なので、staging側での確認を依頼する。
