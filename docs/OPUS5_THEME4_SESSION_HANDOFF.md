# 第4テーマ試作セッション ハンドオフ

新しいセッションで**4つ目のテーマを試作**するための引き継ぎ文書。
既存3テーマのrefineを進めるセッションと**並行**して動くことを前提にしている。

この文書だけで着手できるように書いてあるが、判断の根拠は
`docs/OPUS5_CODEX_ALIGNMENT.md` にある。迷ったら常にそちらが正である。

---

## 0. 最初に読むもの（この順で）

| 対象 | 何が書いてあるか |
|---|---|
| `docs/OPUS5_CODEX_ALIGNMENT.md` §236 | **新規3Dモデル制作の標準手順**（Phase 0〜4）。この試作の手順書そのもの |
| 同 §237 | 4つ目のテーマの規模実測と、着手時に決まっている必要がある事項 |
| 同 §230.2 / §231.6 | contractの書き方の実例（Trend Monitorの固定契約と、テーマ別に変える箇所の表） |
| `docs/ORBITAL_ANALOG_STYLE_GUIDE.md` ほか2件 | 既存3テーマのstyle guide。**新テーマも同じ形式で書く** |
| `docs/VISUAL_THEMES.md` | テーマ全体の位置づけ |

全文を読む必要はない。§236と§231.6の2箇所が実務上の中心である。

---

## 1. 並行作業の衝突回避（最重要・最初に守る）

**同一のworking treeを2セッションが共有する。** 以下は破ると相手の作業を壊す。

### 1.1 `docs/OPUS5_CODEX_ALIGNMENT.md` へ追記しない

15,000行超のファイルへ両セッションが append すると片方の書き込みが消える。
このセッションの記録は**専用ファイル** `docs/OPUS5_THEME4_LOG.md` に書く。
節番号は `T1.` `T2.` … と独自に振る（alignment docの通し番号と混ぜない）。
試作が終わった時点で、要約だけをalignment docへ1節として統合する（統合作業は本体セッション側で行う）。

### 1.2 触ってよいpathは以下だけ

```
ArtSource/Blender/BrushUp/Opus5/<NewTheme>/     ← 新規作成。ここが唯一の成果物置き場
Tools/Blender/opus5_theme4_*.py                 ← 新規script。この接頭辞のみ
docs/OPUS5_THEME4_LOG.md                        ← 作業記録
docs/<NEW_THEME>_STYLE_GUIDE.md                 ← style guide（Phase 0確定後）
```

### 1.3 触ってはいけないpath（既存の禁止事項に加えて）

- `Assets/` 配下すべて（Unity。Codexの領域）
- `Builds/` 配下すべて
- `ArtSource/Blender/BrushUp/Opus5/{OrbitalAnalog,ForgeBrass,KineticSafety}/`
- `Tools/Blender/` の既存script（**読んで再利用するのは可、編集は不可**）
- `docs/OPUS5_CODEX_ALIGNMENT.md`

### 1.4 git操作の可否

**まず知っておくこと: commitしても試作成果物は保全されない。**
`.gitignore` 55行目が `ArtSource/Blender/BrushUp/**` を無視対象にしている。設計意図は
同ファイルのコメントに明記されており、承認されたsource / FBX / report / visual evidenceは
**hashとGate C evidenceが確定した後、専用のpromotion commitでforce-addする**運用である。
Phase 1のprototypeは承認前なので、**force-addは方針違反になる。**
`.blend`、`.fbx`、render画像、JSON reportはディスク上に在ることが唯一の保全である。

| 操作 | 可否 |
|---|---|
| `git status` / `git diff` / `git log` などの読み取り | **可** |
| `git add <明示path>` + `git commit`（script・docsのみ） | **可**（下記の条件つき） |
| `git add -A` / `git add .` / `git commit -a` | **禁止** |
| `git checkout` / `switch` / `branch` / `stash` / `reset` | **禁止** |
| `git push` | **禁止**（ユーザー判断で不可と決定済み） |

- **`add -A`系が禁止な理由**: このtreeには変更21件・未追跡98件があり、Codexの
  Unity作業（`ProjectSettings`、material、Editor script）と本体セッションのdocsを巻き込む
- **branch切り替えが禁止な理由**: working treeを共有しているため、HEADを動かすと
  もう一方のセッションのbranchも同時に動く。独自branchが要る場合でも
  **`git worktree`は使えない** — 参照実装（`opus5_trend_monitor_prototype.py`、
  `opus5_meter_m2n5_slot_normalized.py`、`opus5_fbx_adapter_completion.py`、
  `opus5_publish.py`）はいずれも**未追跡**であり、新しいworktreeには存在しない
- **commitしてよいのは** `Tools/Blender/opus5_theme4_*.py` と
  `docs/OPUS5_THEME4_LOG.md` / `docs/<NEW_THEME>_STYLE_GUIDE.md` を
  **明示的にpathspecで指定した場合のみ。** これは§236.3（build scriptがソース、
  `.blend`は出力）とも整合する

---

## 2. 実行環境

```bash
scripts/run-blender.sh --background --factory-startup --python Tools/Blender/<script>.py -- --project-root "$PWD"
```

- Blender **5.2.0 LTS**。`blender_compat.require_v6_pipeline()` で検証する
- **headlessでは `bpy.ops.ed.undo()` が動かない。** 状態は明示的に保存・復元する
- Blender実行は数十秒〜数分かかる。タイムアウトを短く設定しない
- 座標: 1 unit = 1 m。既存計器はZ-up、mount面 `max Y == 0`、正面 −Y。
  ただし**Trend Monitorだけ別契約**（mount面 `local Z = 0`、表示面 `local +Z`）。
  作る機種の契約を必ず先に確認する

---

## 3. 手順（§236 Phase 0〜4）

### Phase 0 — テーマの性格を「形」で定義する ★2026-08-22 承認済み・完了

**ここが唯一の本当のblockerである。** 既存3つは色ではなく形の性格で分かれている。

| テーマ | 形の性格 |
|---|---|
| Orbital Analog | 薄いcharcoal housing、控えめな角丸bezel、広いdark display、最小限のcorner fastener |
| Forge Brass | 鋳鉄系housing、brass retaining frame、chart-recorder風、透明cover無し |
| Kinetic Safety | graphite shroud、太いguarded bezel、orange/yellow accentはbody側の小面積だけ |

4つ目も**同じ粒度の1〜2文**が要る。単なる色替えは§232で明示的に禁じられている。

**この方向付けはユーザー/Codexが決めるものであり、セッションが独断で確定しない。**
未確定のまま着手する場合は、案を2〜3提示して選んでもらうこと。参考として、
形の距離が既存3つから最も遠い方向の例:

- **Clinical White 系**: 継ぎ目の少ない一体成形、fastenerを見せない、大きな角R、
  フラッシュマウントbezel、刻線は極細 — 既存3つはいずれも「厚い縁と留具が見える」形なので対比が効く
- **Aviation Black 系**: 黒アルマイト、深い円筒hood（グレアシールド）、ロック付きbezel —
  奥行き方向の形で差を作る

決まったら `docs/<NEW_THEME>_STYLE_GUIDE.md` を既存3件と同じ節構成
（Direction / Shape language / Materials and maps）で書く。

**このPhaseは完了している。** ユーザー承認により第4テーマは
**「Machined Ergonomics」**に確定した。方針は `docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md`
（85行、`## Direction` / `## Part-construction language` / `## Ergonomic language` /
`## Geometry versus texture` / `## Materials and maps` / `## Runtime limits`）にある。
**着手前に全文を読むこと。** 以下は要点であって、これだけで作業しない。

- 既存3テーマが暗い母材（cast iron / charcoal / graphite）を共有するのに対し、
  **明るい成形樹脂body + anodizedアルミの機械加工accent + dark elastomerのgrip insert**。
  grayscaleでもvalue差で識別できることを狙う
- 形は「1個の塊」ではなく**組み立てられた部品群**として作る。分割面をシルエットに現し、
  シャットラインは実寸0.8〜1.2 mm相当で1モデル内一定、成形部側面に1〜3°の抜き勾配
- 締結は座ぐり穴＋キャップボルトを**荷重経路上へ**置く。等間隔の装飾ねじにしない
- **geometryで作るもの**: 主分割面と段差、座ぐり窪みとボス、ガスケット溝、軸受カラー、
  end stop、グリップ断面変化と指かかり。
  **normal map / textureへ委ねるもの**: 副次シャットライン、ねじ頭の溝、刻印、シボ、目盛り、label。
  **シャットラインを全部geometry化しない**（三角形は主分割面と可動部clearanceへ優先配分）
- 表示面は取付面法線から5〜15°手前へ傾ける。**ただしenvelopeのZ上限は超えない**
- 1 objectあたり1,500 triangles以下、renderer 3以下（meterのみ4以下）、shared materials 2以下

**注意 — material roleの数について。** style guideは`body` / `metal` / `gasket` / `readout`の
4 roleを維持すると書いているが、これは**authoring時のrole**である。
delivery正規化（Phase 4）では§186.1のname mappingにより`body`と`metal`は同一のopaque materialへ
落ち、最終的な**shared material 2以下**という同guideの制限と整合する。
矛盾ではないので、authoringでは4 roleのまま進めてよい。

### Phase 1 — pilot 3機種だけ、Blendのみ、FBXは作らない

13機種すべてを作らない。**MeterRound / Lever / Toggle** の3機種を先に作る。

**当初はMeterLarge + Buttonの2機種としていたが、変更した。**
その選択はテーマ方向が決まる前に「最大と最小の両端」という一般論で決めたものであり、
Machined Ergonomicsの主張（軸受、グリップ断面、detent、end stop、形状コーディング）を
**Buttonではほぼ検証できない。** 可動部と軸受を持つLever / Toggleが要る。
MeterRoundは表示面の傾斜と分割面を受け持つ。

- **手でモデリングしない。** build scriptがソース、`.blend`は出力。
  `Tools/Blender/opus5_trend_monitor_prototype.py` の構造をそのまま真似る:
  先頭に定数テーブル → `rounded_rectangle` / `slab` / `frame` / `plane` などの
  geometry helper → `build()` → `measure()` → 固定camera `shot()` → contact sheet
- 固定camera画像（正面・左右斜視・側面）と寸法reportを出して**停止し、承認を待つ**
- **FBXをここで出さない。** FBXがあるとUnity取り込みを誘発し、形状承認前に既成事実化する

### Phase 2 — 「固定する箇所 / テーマで変える箇所」を自分で書く

§231.6が実例。**作った本人が書く。** どの数値が構造的に効いていてどれが装飾かは
組んだ本人にしか分からない。

### Phase 3 — 残り11機種へ展開

`THEMES` spec dict に差分だけ記述する形（`opus5_trend_monitor_themes.py` の構造）。

### Phase 4 — delivery正規化とFBX

既存パスへ合流する。`opus5_meter_m2n5_slot_normalized.py`（export正規化 → role別join →
slot正規化）と `opus5_fbx_adapter_completion.py`（測定）を**再利用する。
新しい汎用validatorを作らない。**

到達目標: **renderer 3以下 / submesh 4以下 / material role 2以下。**

---

## 4. 出力先と命名

既存の慣例に合わせる。

```
ArtSource/Blender/BrushUp/Opus5/<NewTheme>/
  <Instrument>/BL_<Instrument>_<NewTheme>_V6_Opus5_P1_Retopo.blend
  <Instrument>/SM_<Instrument>_<NewTheme>_V6_Opus5_P1.fbx    ← Phase 4まで作らない
  review/Preview_<Instrument>_<NewTheme>_P1_<view>.png
  contact_sheets/ContactSheet_<Instrument>_<NewTheme>_P1.png
  reports/
```

root object名: `PF_Visual_<Instrument>_<NewTheme>_V6`

publishは `Tools/Blender/opus5_publish.py` の `publish()` を使う。
既存出力の置き換えを `publish_guard()` が拒否する仕組みになっている。

---

## 5. 絶対にやらないこと

- **上書き**: `*_ProductionReady.blend`、active FBX、Unity prefab / material / texture / `.meta`、
  runtime code、既存candidate成果物
- Unity import、prefab生成、active化、Quest APK build（**すべてCodexの領域**）
- 新しい汎用validatorやadd-onの研究
- **13機種の一括生成**（Phase 1のpilot 2機種で必ず停止して承認を取る）
- reportの字句修正のためだけの再build（Blender保存はbyte再現ではなくSHAが変わる。§222.4）

---

## 6. 独断で決めてはいけないこと

1. **テーマの方向付け**（Phase 0）— ユーザー/Codex判断
2. **material / atlas構成を既存に合わせるか** — 既存は
   `MAT_<Theme>_Atlas` / `_Atlas_Large` / `_Atlas_Medium` / `_Emissive` / `_Emissive_Large` / `_Emissive_Medium` の6件。
   合わせないと `Tools/Textures/build_v6_material_atlases.py` と §186.1 のname mappingが通らない
3. **45ファイルのテーマ名直書きをどう扱うか** — runtime catalog / Editor / manifestを持つ**Codexの領域**。
   試作段階では**1ファイルも触らない**（試作はBlender側で完全に隔離できる）

---

## 7. 既知の落とし穴（実際に踏んだもの）

- **material roleは形を作る前に決める。** `display_surface`にaccent材質を割り当てて
  画面が全面オレンジになった事例がある。roleは後段のjoin単位を決めるので、後から動かすと構造が変わる
- **絶対値gateをbuild script内にassertとして埋める。** 新規制作は差分検証が使えないため、
  envelope / opening / normal / triangle数を生成直後にその場で判定するしかない
- **triangulateは `quad_method="FIXED", ngon_method="EAR_CLIP"`。**
  既定の `BEAUTY` はBlenderの表示triangulationと違う対角線を選ぶ
- **`mesh_smooth_type="EDGE"`（`"FACE"` ではない）。** FACEはsplit normalを落とす
- **join後にsmooth normalが壊れる**（異方scale下）。join前のpartsから**位置のみで照合して**復元する
- **角度は `atan2(|cross|, dot)`。** `acos(dot)` は1近傍で誤差を増幅し幻の0.008°を生む
- **驚く数値が出たら、まず測定を疑う。** 新規制作は比較対象が無く誤報に気付きにくい。
  このプロジェクトでは測定側のバグが「自信のある誤報」を繰り返し生んでいる

---

## 8. 現在の状況（2026-08-22時点）

- 既存3テーマ: 各13モデル。Meter 3種のみproduction統合済み（Quest実機PASS）。
  Trend MonitorはUnity staging + Quest review APKまで到達。ToggleはFBX正規化済みでUnity未通過。
  **残り9機種は未着手**
- Codexの作業は停止中。§233 / §235への応答と、`display_surface` role、
  Toggle `V5_Metal`統合可否の2判断が未回答
- 4つ目のテーマは§237で「既存3テーマのrefine完了後」と記録したが、
  ユーザー判断により**試作のみ並行で先行**することになった

---

## 9. 先行したクラウドセッションの成果（2026-08-22 追記）

この試作は最初**誤ってクラウドセッションで開始された。** そのセッションは
`origin/claude/opus5-theme4-handoff-i14wfz` へ1 commit（`366ad68`）をpush済みである。

### 9.1 なぜクラウド側は手順書を持っていなかったか

**この引き継ぎ文書もalignment docも未追跡**（gitに無い）ため、クラウドのcloneには存在しなかった。
参照実装の `opus5_*.py` 82件も同様に未追跡で、クラウドからは見えない。
結果としてクラウドセッションは手順書無しで動き、引き継ぎ文書を独自に書き直し、
**本来ユーザー判断であるPhase 0のテーマ方向も自分で決めている。**
これは§240.5で報告した「未追跡ファイルの範囲」の問題が実際に表面化した事例である。

### 9.2 内容（Phase 0のみ。Blender作業は無し）

| ファイル | 内容 |
|---|---|
| `docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md` | テーマ方向「Machined Ergonomics」85行 |
| `docs/OPUS5_THEME4_LOG.md` | 作業ログ59行（**本文書とpath衝突**） |
| `docs/OPUS5_THEME4_SESSION_HANDOFF.md` | クラウド側が書いた別版227行（**本文書とpath衝突**） |
| `docs/VISUAL_THEMES.md` / `CHANGELOG.md` | 追記（本文書§1.3の禁止path） |

**この方向付けは検討に値する。** 既存3テーマが暗い母材（cast iron / charcoal / graphite）を
共有するのに対し、明るい成形樹脂＋アルマイト金属を主とし、grayscaleでもvalue差で識別できる。
パーティングライン、抜き勾配、荷重経路上の締結、ブッシング、ガスケット溝といった
**製造工程の必然から形を作る**言語になっており、§232が禁じる「単なる色替え」から明確に離れている。

**ただし採否はユーザー/Codex判断である**（§236.2）。セッションが引き継いで確定しない。

### 9.3 このbranchをcheckoutしてはいけない

`docs/OPUS5_THEME4_SESSION_HANDOFF.md` と `docs/OPUS5_THEME4_LOG.md` は
**ローカルでは未追跡、cloud branch上では追跡されている。**
checkoutやmergeを行うとgitが拒否するか、**ローカルの本文書を上書きする。**

読むときはcheckoutせず、remote-tracking refから直接読む。

```bash
git show origin/claude/opus5-theme4-handoff-i14wfz:docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md
```

差分を見る場合も同様に `git diff codex/monitor-mvp...origin/claude/opus5-theme4-handoff-i14wfz`
までに留め、mergeしない。取り込む場合は**ユーザー承認後に、必要なファイルだけ個別に**行う。

---

## 10. 未解決のOPEN項目（クラウドセッションから回収）

クラウドセッションのログT8 / T9から回収した。**ローカルのログには存在しない**ため、
ここに移す。Phase 1着手時に引き継ぐこと。

### 10.1 OPEN — テーマ名とtheme IDが未確定

`Machined Ergonomics` / theme ID `machined-ergonomics` は**提案段階である。**
`Assets/MatsuMotoMeterAR/Runtime/Instruments/MockInstrumentThemeCatalog.cs` に
既存3件（`forge-brass` / `kinetic-safety` / `orbital-analog`）が焼き込まれており、
4つ目も同様にasset名とcatalogへ入る。

**Phase 2完了までに確定が必要。** 今なら変更コストは文書のみだが、
Phase 3以降はasset名の改名を伴う。**確定はユーザー/Codex判断であり、セッションが決めない。**

（クラウドのログはPlayerPrefsへ焼き込まれると記したが、実際の束縛先は
`MockInstrumentThemeCatalog.cs` である。`PlayerPrefs`はplacement保存に使われており別物。
指摘の本質は正しいが、束縛先の名前だけ訂正する。）

### 10.2 OPEN — 明るい母材でのbevel highlightコントラスト

既存3テーマは暗い母材（cast iron / charcoal / graphite）で、稜線をhighlightの
明暗差で読ませている。**Machined Ergonomicsは明るい成形樹脂body**であり、
同じbevel幅では稜線のコントラストが落ちる可能性がある。

シャットラインをgeometryとnormal mapのどちらへ配分するかにも影響する。
**Phase 1のBlender作業と固定camera画像でのみ判定できる。**
Phase 1の評価項目に必ず含めること。grayscale contact sheetでの識別可否を見る。

---

## 11. Phase 1の完了条件

- MeterRound / Lever / Toggleの3種で、envelope・pivot・可動域が**既存3テーマと一致する**
- 1 objectあたり1,500 triangles以下、renderer 3以下（meterのみ4以下）、shared material 2以下
- non-manifold edge 0、zero-area face 0
- 固定camera画像（正面・左右斜視・側面）
- **既存3テーマとの4テーマ横並びgrayscale contact sheet**で識別できる（§10.2の判定を兼ねる）
- 寸法report（object名、role、triangle、bounds、SHA-256）
- **FBXを作らない。** Unity取り込み・prefab生成・active化へ進まない

出力先とscript名は**本文書§4の規約に従う。**
クラウドセッションが提案した `ArtSource/Blender/Theme4/...` と
`Tools/Blender/generate_theme4_*.py` は**使わない** — 前者は`.gitignore`の
`ArtSource/Blender/BrushUp/**` に該当せず`.blend`がgitへ入ってしまい、
後者は§240.4でcommitを許可した`opus5_theme4_*.py`の範囲外である。

---

## 12. 次のセッションへ渡す初期依頼文

そのまま貼れる。

```
docs/OPUS5_THEME4_SESSION_HANDOFF.md を読んで、第4テーマ
Machined Ergonomics の Phase 1 を進めてください。

方針は docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md に確定済みです（全文を読むこと）。
Phase 0 は承認済みで完了しています。

Phase 1 は MeterRound / Lever / Toggle の3機種の shape prototype です。
Blend のみを作り、FBX は作りません。固定camera画像・4テーマ横並びの
grayscale contact sheet・寸法report を出して停止し、形状承認を待ってください。

着手前に §10 の OPEN 項目2件（テーマID未確定、明るい母材でのbevel
highlightコントラスト）を確認してください。後者は Phase 1 の評価項目です。

§1 の衝突回避規則と §4 の出力先・命名規約を必ず守ってください。
作業ログは docs/OPUS5_THEME4_LOG.md へ T1. から追記してください。
```
