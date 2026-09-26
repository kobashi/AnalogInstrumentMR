# Opus 5 Superfine theme handoff

Status: **第5テーマとして本番登録P完了。更新APKのQuest実機動作はユーザー確認PASS。Q1負荷試験とB1上限確定は後回し。2026-09-25。**
SuperfineはKinetic Safetyを基にした独立テーマであり、C2、C3、C4の隔離検証を経て24機種を本番登録した。
更新APKのbuild / install / human実機動作確認は完了。定量的なQuest 48 / 64負荷試験は未実施。

## 1. Origin and scope

- 現行モデルを修正・置換せず、Kinetic Safetyをベースに独立テーマ
  **Superfine**を作る。
- Kinetic Safetyを含む既存テーマのmodel、FBX、prefab、material、texture、GUIDを変更しない。
- 三角形上限の引き上げはSuperfineだけを対象とし、既存共通上限5,000は変更しない。
- Superfine上限は一律に先決めせず、機種別実数とQuest負荷試験を根拠にB1で決定する。
- まず代表試作、Kinetic Safety比較、三角形数、可動部／pivot互換、性能見積を確認し、
  他機種展開と本番登録はその後に判断する。

ユーザーはP1 prototypeを承認し、6機種へのS1展開を指示した。S1は完了し、
CodexはC1としてUnityへ隔離取り込みした。production登録はしていない。

設計意図（R0）は、折曲げsteel tray、mounting flange、returned-edge panel、
gasket reveal、molded window bezel、実ハードウェアで保持されたjack、pot nut上の
skirted knob、button-head screw、corner bumperを備えた製造可能な製品として読む形状。
readout、knob、port、fastener XY、legend、signal routeは承認済みKinetic Safety
Ext-B1 layoutを維持する。

## 2. Ownership

| Area | Owner |
|---|---|
| Blender shape、topology、UV、deterministic FBX、render、Tier A audit | Opus 5 |
| Unity import、runtime binding、validator、機種別cap、production登録、docs、git、Quest acceptance | Codex |

## 3. Stage plan and gates

| Stage | Content | Owner | State |
|---|---|---|---|
| R0 | Manufacturing spec、parts/BOM、assembly order、depth ladder | Opus 5 | done |
| P1 | Filter prototype + Kinetic Safety comparison | Opus 5 | done、user-approved |
| S1 | 6機種、比較sheet、Tier A | Opus 5 | **done、Codex受領** |
| C1 | 隔離Unity candidate import、contract、binding | Codex | done、Sequencer端子不足を検出 |
| F1 | Sequencer `port_trigger_in` fix-back | Opus 5 | **done、Codex受領** |
| C2 | F1 Sequencerだけを差し替えた隔離再取り込み | Codex | **done、0 contract FAIL / 3 REVIEW** |
| S2 | 残るaudio 4機種（Oscillator / Noise / Delay / Output） | Opus 5 | **done、Codex受領** |
| C3 | S2 4機種の隔離Unity candidate import | Codex | **done、0 FAIL / 0 REVIEW** |
| N0 | 非audio 14機種のscope / runtime contract確定 | Codex | **done** |
| N1 | 非audio代表4機種のshape pilot | Opus 5 | **done、shape受領** |
| N2 | 非audio全14機種のBlender成果物 | Opus 5 | **done、12機種受領 / 2機種fix-back** |
| N2-F1 | WindowPanel contract / Rotary可変detent対応 | Opus 5 | **done、Codex受領** |
| C4 | N2 + N2-F1の隔離Unity candidate import | Codex | **done、0 FAIL / 7 REVIEW** |
| Q1 | Quest 48-object gate / 64-object stress | Codex | **ユーザー指示により後回し** |
| B1 | S1実数 + Q1から機種別Superfine capを決定 | Codex + user | **暫定値算出済み、未採用** |
| P0 | 24機種のproduction mapping / GUID / rollback準備 | Codex | **done、production mutationなし** |
| P | 第5テーマとしてproduction登録 | Codex | **done、24機種登録済み** |

Opus 5は各担当stage後に停止する。F1以降は新しい指示なしに開始しない。

## 4. Contract

### 4.1 共通契約

- envelope 0.24 × 0.20 × 0.10 m、originはmount-plane centre、mount plane後方は最大1 mm
  （Superfine S1は0 mm）。
- Blender/Unity axis mapping、FBX exportは`-Z` forward、`Y` up、metres、
  `mesh_smooth_type=EDGE`、explicit FIXED/EAR_CLIP triangulation。
- required nodeは各1個。catalogue portごとに同名の`port_*` nodeを1個持つ。
- `display_surface`: separate flat mesh、2 triangles、UV0 0..1、+Z。
- `signal_surface`: separate renderer、UV0 0..1、`EmissionDisplay` role。
- renderer 7（limit 9）、material role 3種:
  `Housing` / `FaceMetal` / `EmissionDisplay`。
- knob full-turn clearance、arrowなし、Mixerはphysical input 1個。

注: S1作成後にSequencerへstep-trigger入力が追加されたため、現行catalogue契約は
`port_trigger_in`も要求する。S1 Sequencerはこのnodeを持たずC1ではFAILとなったが、F1で
node、jack hardware、`TRIGGER IN` legendを追加した。位置は`(-88, -24, 54) mm`で、C2ではPASS。

### 4.2 Superfine固有差分

| Item | Kinetic Safety | Superfine | C1 result |
|---|---:|---:|---|
| Panel front Z | 20 mm | 48 mm | PASS |
| `parameter_knob_pivot` Z | 25 mm | **55 mm** | 6機種PASS |
| `port_*` node Z | 26 mm | **54 mm** | 存在する全port PASS |
| Overall depth | 41.8–44.6 mm | 78.6 mm | PASS、100 mm envelope内 |
| Knob shaft | static | `parameter_knob`の一部 | 5状態motion PASS |
| Triangle cap | 5,000 | B1で機種別決定 | 5,000超はREVIEW |

### 4.3 Budget verdict convention

B1までは共通5,000超を**REVIEW**とする。PASSやFAILへ読み替えない。
共通上限`InstrumentGreyboxSpecification.TriangleBudgetPerInstrument = 5000`は変更しない。

## 5. S1成果物

Package: `ArtSource/Blender/BrushUp/Opus5/AudioModules_Superfine_S1/`

| Kind | Placement | Superfine tris | Kinetic Safety tris | Tier A | FBX SHA-256 |
|---|---|---:|---:|---|---|
| VCA | `audio.vca` | 4,808 | 3,792 | PASS | `73972fd0bd6a3dd3d54ec77ad71a54f7b8d557a53c63579684dbe9e0ab678883` |
| Mixer | `audio.mixer` | 4,940 | 4,392 | PASS | `41390e5938a7d2bf7d968b971da4ce98de6e31c27cafa1c76f9bf3bf792f61ff` |
| Filter | `audio.filter` | 4,838 | 4,066 | PASS | `310cf990528e9e22e1ab4fceeec2221cebf7ccd956c68bd67d4fdb67eab9ca3a` |
| Envelope | `audio.envelope` | 5,496 | 4,416 | REVIEW | `25a661784f9ab937ca5c77fcc9ddf73d40e64c11d4509dca46e496b36d10729b` |
| LFO | `audio.lfo` | 7,122 | 4,852 | REVIEW | `69ebf1459348ac09a179b93a4c856e08b151b8f34928b9b450177cafd6fb3e3b` |
| Sequencer | `audio.sequencer` | 6,498（F1） | 4,234 | REVIEW（triangle）/ contract PASS | `e41fd5234bcb0b007ff1746ef01be6d13693f30038a822f5dbd70072380041f5` |

- 元checkoutの`SHA256SUMS.txt`は**223 / 223 OK**。上表6 FBXも全て一致。
- Opus Tier A: PASS 45 / FAIL 0 / REVIEW 3 / N/A 0。
- Opus motion: 各機種0 / 181 intersect、minimum clearance 0.6 mm。
- Unity C1 motion: 6機種 × 5 statesすべてPASS。
- performance estimate（F1反映後）: 平均5,617 tris/module、48台平均約270k tris、64台平均約359k tris、
  全台LFOなら約456k tris。renderer/material/texture countはKinetic Safetyと同等。

F1 packageは
`ArtSource/Blender/BrushUp/Opus5/AudioModules_Superfine_F1/`。元checkoutで
`SHA256SUMS.txt`を**40 / 40 OK**と確認した。F1はSequencerだけを変更し、triangleは
5,474から6,498へ増加した（jack 288、collar 160、legend 576）。新端子を既存4端子列へ
詰め込まず入力側上段へ分離した配置は、S1/F1比較とfront/raking close-upで識別性、既存信号経路、
他端子との非干渉を確認し、C2で受領した。

関連packageは記録としてread-only扱いとする。R0のuniform 7,000/8,000 cap案は、
SuperfineだけをB1で機種別決定する後続方針によりsuperseded。

## 6. Codex decisions / answers

1. **Pivot / port / socket / cable anchor**
   - knob motion targetはauthored `parameter_knob_pivot` nodeから解決されるため55 mmへ追従する。
   - interaction colliderはnode/bounds由来ではなく、audio共通の固定center
     `(0,0,0.05)` / size `(0.24,0.20,0.10)`。S1のpivotと存在する全portは内部にありC1 PASS。
   - `AudioSocket`はruntime instrument root原点に固定され、visual node由来ではない。
   - C2初回監査時点ではcable lineの表示端点もsource/target root位置を使用していた。後続の
     Unity修正で`sourcePortId` / `targetPortId`から`port_*` anchorを解決し、旧assetはroot fallbackとした。
2. **機種別triangle cap**
   - C2では決定しない。VCA/Mixer/Filterは共通5,000内、Envelope/LFO/SequencerはREVIEWを維持する。
   - B1ではQ1を通過した最終mesh実数に7.5%の編集余裕を加え、100 tris単位で切り上げた値を
     機種別候補にする。現S1だけからの仮値はVCA 5,200 / Mixer 5,400 / Filter 5,300 /
     Envelope 6,000 / LFO 7,700。F1 Sequencer実数6,498に同じ規則を当てる暫定候補は7,000で、
     いずれも未採用。
   - Q1/B1前にLFO reductionを必須にはしない。Q1で削減が必要になった場合のF1目標は
     **6,500 tris以下**（7 jack/legendと形状signatureを保持）を提案する。
3. **Registration shape**
   - theme ID案は`Superfine`。prefabは`PF_Visual_Audio<Kind>_Superfine`、production materialは
     `MAT_Superfine_AudioModule_{Housing|FaceMetal|EmissionDisplay}`、Resourcesは
     `Resources/Superfine/Prefabs`とする。
   - 第5テーマ追加はPの明示指示後のみ。Kinetic Safetyの`.meta`をコピーせず、Superfine assetごとに
     新規GUIDを発行する。C1のcandidate GUIDもKinetic Safetyとは独立している。
4. **6機種以外への展開**
   - S2でDelay / Oscillator / Noise / Outputを追加し、audio 10機種のBlender成果物は揃った。
   - meter/control系は未作成。global theme pickerへ第5テーマとして加える前に、catalogue全体を作るか、
     機種別theme availability/fallback仕様を定義する必要がある。

## 7. Prohibited until a later instruction

- 既存4テーマのmodel、FBX、prefab、material、texture、GUID変更。
- production path登録、theme picker追加、共通5,000 cap変更。
- `AudioModules_R2_A4_OA1`のコピー／変更。
- commit、push、PR、APK、Quest実機作業。
- REVIEWをPASSとして扱うこと。

## 8. Codex acceptance notes

2026-09-19、下書きを確認し本書へ受領した。C1では
`AudioModules_Superfine_S1` manifest（GateB）を作り、
`Assets/MatsuMotoMeterAR/Content/RefinedCandidates/CandidateStaging/AudioModules_Superfine_S1/`
へ6機種を隔離した。production Resourcesと既存4テーマは変更していない。

検証結果:

- source integrity: **PASS**（223 / 223 checksum OK、6 FBX SHA一致）
- VCA / Mixer / Filter contract: **PASS**
- Envelope / LFO: contract **PASS**、triangle **REVIEW**
- Sequencer: triangle **REVIEW**、現行契約`port_trigger_in`不足 **FAIL**
- renderer 7 / material role 3 / envelope / mount plane / display / signal surface: **PASS**
- runtime display + signal renderer assignment: **PASS**（6機種）
- 5-state motion: **PASS**（6機種）
- pivot 55 mm: **PASS**（6機種）
- 存在するport 54 mm + fixed interaction collider containment: **PASS**
- logical port connection: **PASS**、physical cable endpoint: **FAIL**（root基準）
- AudioSocket node-follow: **N/A**（runtime root固定設計）
- EditMode: **390 / 390 PASS**

Evidence:

- `Builds/Reports/candidate-AudioModules_Superfine_S1-staging-validation.md`
- `Builds/Reports/candidate-AudioModules_Superfine_S1-c1-audit.md`
- `Builds/Reports/candidate-AudioModules_Superfine_S1-motion-audit.md`
- `Builds/Reports/candidate-AudioModules_Superfine_S1-editmode-results.xml`
- `Builds/Reports/candidate-AudioModules_Superfine_S1-kinetic-vs-superfine-comparison.png`

F1候補は、Opus 5担当としてSequencerへ`port_trigger_in` node、jack hardware、legendを追加する1件。
cable endpointのport追従はUnity runtime側の修正候補であり、Opus 5形状修正ではない。
LFO 6,500 tris以下への削減はQ1/B1の結果が要求した場合だけF1へ追加する。

**C1で検出したSequencer端子不足はF1/C2で解消した。三角形3件のREVIEWとUnity runtime側の
cable endpoint FAILは維持し、本番昇格せず停止する。**

## 9. Codex → Opus 5: F1正式作業指示（2026-09-20）

この節をもってOpus 5へF1の開始を正式に指示する。対象は
`AudioSequencer Superfine SFS1`の現行Unity契約適合だけとし、次を実施する。

### 9.1 Required fix

- `port_trigger_in` nodeを正確に1個追加する。
- 対応するjack hardwareと`TRIGGER IN` legendを追加する。
- `port_trigger_in`のZは他のSuperfine portと同じ54 mmとする。
- 既存の`port_clock_in`、`port_control_out`、`port_gate_out`、
  `port_trigger_out`を維持する。
- `parameter_knob_pivot` Z=55 mm、display/signal surface、signal route、
  material role、mount plane、envelopeを維持する。
- 端子追加によるtriangle増加は必要最小限にする。5,000超は引き続きREVIEWとし、
  PASSまたはFAILへ読み替えない。

### 9.2 Output and revision

S1を上書きせず、次の新規packageへ出力する。

`ArtSource/Blender/BrushUp/Opus5/AudioModules_Superfine_F1/`

最低限、Sequencerのcage `.blend`、triangulated `.blend`、deterministic FBX、
inspection JSON、front/oblique/display/signal render、S1 comparison sheet、
`REPORT.md`、`MANIFEST.md`、`SHA256SUMS.txt`、Codex向けhandoff draftを含める。

### 9.3 Required validation

- required nodeの重複／不足0。FBX round-trip後も`port_trigger_in`を含む全portが一致。
- port Z=54 mm、knob pivot Z=55 mm。
- display/signal surface、renderer/material/bounds契約を維持。
- knob 5-state motion auditを実施し、干渉0。
- Tier AのPASS / FAIL / REVIEW / N/Aを分離して記録。
- S1との差分がSequencer trigger-input対応に限定されることを報告。
- `SHA256SUMS.txt`をrepository rootから検証し、件数と結果を報告。

### 9.4 Explicitly out of scope

- LFOのtriangle削減。他のSuperfine 5機種の変更。
- 既存S1 package、既存4テーマ、Ext/R2 packageの変更。
- Unity `Assets/`、`Builds/`、`docs/`、gitへの書込み。
- production登録、APK、Quest作業。
- cable endpoint問題の修正。これはUnity runtime側の担当とする。

F1完了後は停止し、変更node/形状、triangle数、Tier A、motion、FBX SHA-256、
checksum検証件数、S1との差分、handoff draftの絶対pathを報告する。

## 10. Codex F1受領 / C2 acceptance notes（2026-09-21）

Opus 5のF1回答を受領し、元checkoutでpackageを検証した。`SHA256SUMS.txt`は
**40 / 40 OK**、Sequencer F1 FBX SHA-256は
`e41fd5234bcb0b007ff1746ef01be6d13693f30038a822f5dbd70072380041f5`でhandoffと一致した。
F1のTier AはPASS 8 / FAIL 0 / REVIEW 1 / N/A 0、5-state motionは0 / 5 intersect、
181-state sweepは0 / 181 intersect、minimum clearanceは0.6 mm。F1形状を受領する。

C2は新規manifest `AudioModules_Superfine_C2`を用い、S1 candidateを上書きせず、VCA、Mixer、
Filter、Envelope、LFOはS1、SequencerだけをF1へ差し替えた。production Resources、既存4テーマ、
共通triangle capは変更していない。

- source integrity: **PASS**（F1 40 / 40 checksum、FBX SHA一致）
- 6機種のnode / port / renderer / material / envelope / display / signal contract: **PASS**
- Sequencer `port_trigger_in`、Z=54 mm、fixed interaction collider包含: **PASS**
- runtime display + signal renderer assignment: **PASS**（6機種）
- 5-state motion: **PASS**（6機種）
- triangle: VCA / Mixer / Filter **PASS**、Envelope 5,496 / LFO 7,122 /
  Sequencer 6,498は**REVIEW**
- cross-candidate dependency: **PASS**（0件）
- logical port connection: **PASS**、physical cable endpoint: **PASS**（§11で解消）
- AudioSocket node-follow: **N/A**（runtime root固定設計）
- EditMode: **391 / 391 PASS**

Evidence:

- `Builds/Reports/candidate-AudioModules_Superfine_C2-staging-validation.md`
- `Builds/Reports/candidate-AudioModules_Superfine_C2-c2-audit.md`
- `Builds/Reports/candidate-AudioModules_Superfine_C2-motion-audit.md`
- `Builds/Reports/candidate-AudioModules_Superfine_C2-editmode-results.xml`
- `Builds/Reports/candidate-AudioModules_Superfine_C2-kinetic-vs-superfine-comparison.png`

**Opus 5側の追加形状修正F1候補はない。Opus 5は停止を維持する。次の判断はCodex/userによる
Q1、B1、またはproduction登録のいずれかで、別指示を要する。**

## 11. Unity typed-port cable endpoint fix（2026-09-21）

`AudioPatchConnectionRecord`に保存済みの`sourcePortId` / `targetPortId`を接続線描画へ渡し、
`audio.out`を`port_audio_out`へ変換する規則でVisualSocket配下のauthored anchorを解決するようにした。
resolverは機器契約に属し、解決結果をcacheする。theme visualが差し替わった場合はcacheを無効化し、
要求nodeがない既存visual、UI source、legacy assetではinstrument rootへfallbackする。通常の
`SignalConnectionRecord`にはport IDがないため、その接続線は従来どおりroot基準を維持する。

C2 auditを再生成し、VCA / Mixer / Filter / Envelope / LFO / Sequencerの全catalogue portが対応する
`port_*` nodeへ解決されることを確認した。6機種のCable endpointsはすべて**PASS**。
AudioSocketは3D音響出力用としてruntime root原点に残し、今回のvisual cable anchorとは分離した。
EditModeはresolver、fallback、visual差し替え後のcache更新を追加して**393 / 393 PASS**。

Evidence:

- `Builds/Reports/candidate-AudioModules_Superfine_C2-c2-audit.md`
- `Builds/Reports/connection-port-anchor-editmode-results.xml`

**C2の機能FAILは0件。Envelope / LFO / Sequencerのtriangle REVIEW 3件とAudioSocket N/Aは
判定を維持し、REVIEWをPASSへ読み替えない。**

## 12. Codex → Opus 5: Superfine S2正式作業指示（2026-09-21）

Superfineを音響モジュール一式へ拡張するため、Opus 5へS2を正式発注する。対象はS1/F1に含まれない
次の4機種だけとする。

| Model | placement type | Required ports | Kinetic Safety B1 tris（参照） |
|---|---|---|---:|
| AudioOscillator | `audio.oscillator` | `port_pitch_in`, `port_gate_in`, `port_fm_in`, `port_audio_out` | 3,506 |
| AudioNoise | `audio.noise` | `port_gate_in`, `port_audio_out` | 3,026 |
| AudioDelay | `audio.delay` | `port_audio_in`, `port_time_in`, `port_audio_out` | 2,914 |
| AudioOutput | `audio.output` | `port_audio_in` | 2,298 |

### 12.1 Design source and scope

- 形状言語、製造構造、depth ladder、jack hardware、fastener、corner bumperは承認済みSuperfine S1/F1を継承する。
- 各機種のreadout、knob、port、legend、signal routeのXYと機能配置はKinetic Safety B1を参照する。
- 現行モデルの修正ではなく、独立theme `Superfine`の新規assetとして作る。
- S1/F1 package、既存4theme、production asset、Unity `Assets/`、`Builds/`、`docs/`を変更しない。
- `AudioModules_R2_A4_OA1`は参照、コピー、変更のいずれも禁止する。

### 12.2 Contract

- envelope 0.24 × 0.20 × 0.10 m、originはmount-plane centre、mount plane後方は最大1 mm。
- `parameter_knob_pivot` Z=55 mm、全`port_*` Z=54 mm。
- common nodeは各1個: `housing`, `faceplate`, `display_bezel`, `display_surface`,
  `parameter_knob_pivot`, `parameter_knob`, `parameter_index`。
- 上表のrequired portを各1個持ち、余分な`port_*` nodeを作らない。
- `display_surface`: separate flat mesh、2 triangles、UV0 0..1、local +Z。
- `signal_surface`: separate renderer、UV0 0..1、local +Z、displayと同じ`EmissionDisplay` material role。
- rendererは原則7、上限9。material roleは`Housing` / `FaceMetal` / `EmissionDisplay`の3種。
- knob shaftを`parameter_knob`に含め、5-state motionと181-state sweepで干渉0を確認する。
- deterministic FBX条件はS1/F1と同じ`-Z` forward、`Y` up、metres、explicit triangulationとする。

共通triangle上限5,000は変更しない。5,000以内を設計目標とするが、形状signature、可読性、実ハードウェア表現を
壊してまで削減しない。5,000超は**REVIEW**として実数と増加要因を報告し、PASSへ読み替えない。

### 12.3 Output

S1/F1を上書きせず、次の新規packageへ出力する。

`ArtSource/Blender/BrushUp/Opus5/AudioModules_Superfine_S2/`

revisionは`SFS2`、FBX名は`SM_Audio<Model>_Superfine_SFS2.fbx`とする。4機種それぞれについて、
cage `.blend`、triangulated `.blend`、deterministic FBX、inspection JSON、front/oblique/display/signal render、
Kinetic Safety B1 comparisonを用意する。さらに4機種contact sheet、Tier A集計、motion集計、`REPORT.md`、
`MANIFEST.md`、`SHA256SUMS.txt`、Codex向けhandoff draftを含める。

handoff draftは次の絶対pathへ置く。

`/Users/kblab/Documents/AnalogInstrumentMR/ArtSource/Blender/BrushUp/Opus5/AudioModules_Superfine_S2/OPUS5_SUPERFINE_S2_HANDOFF_DRAFT.md`

### 12.4 Required validation and stop condition

- required node不足／重複0、unexpected port 0、FBX round-trip後も一致。
- pivot 55 mm、port 54 mm、envelope、mount plane、display/signal surface、renderer/material契約を検証。
- Tier Aを実行し、PASS / FAIL / REVIEW / N/Aを分離する。
- knob 5-stateおよび181-state motion監査で干渉0。
- Kinetic Safety B1とSuperfine S2のtriangle差、bounds差、見た目の差を機種別に報告する。
- repository rootから`shasum -a 256 -c .../SHA256SUMS.txt`を実行し、件数と全件OKを報告する。

完了後は停止し、4 FBX SHA-256、triangle、bounds、Tier A、motion、checksum件数、変更ファイル一覧、
handoff draftの絶対pathを報告する。Unity取り込み、C3、Q1、B1、production登録、commit / push / PR / APK /
Quest作業は開始しない。

## 13. Codex → Opus 5: S2受領回答（2026-09-21）

Opus 5の`AudioModules_Superfine_S2`回答を受領した。元checkoutのrepository rootから
`SHA256SUMS.txt`を独立検証し、**121 / 121 OK**。4 FBX SHA-256はhandoff、REPORT、実ファイルで一致した。

| Model | Superfine S2 tris | Bounds (m) | Common 5,000 | FBX SHA-256 |
|---|---:|---|---|---|
| Oscillator | 4,842 | 0.234810 × 0.192993 × 0.078600 | PASS | `03717c93829dfb15a5cbf955c9fb019e3ece0c98d8ca432cfe5c2cef74a51f96` |
| Noise | 4,862 | 0.236059 × 0.191379 × 0.078600 | PASS | `9880476cb603d8b7859574e3e034d3578b5304a4db0c62bab0116f4d46ee71a5` |
| Delay | 4,902 | 0.234904 × 0.196101 × 0.078600 | PASS | `9e61e05bb7079469e06af2a295cf047a349fb9decbc6a6aaf292d26d006bd197` |
| Output | 3,026 | 0.234581 × 0.189016 × 0.078600 | PASS | `45b252198c7b407ce844b1f645c5ba3d17186d290489ec2a9d2de69e87a43bc1` |

独立確認結果:

- required node不足／重複／unexpected port: 0。FBX round-trip node / triangle一致、bounds差最大0.00002 mm。
- pivot Z=55 mm、全port Z=54 mm、renderer 7、material role 3、envelope、mount plane: PASS。
- display surface 2 triangles / UV0 / +Z、separate signal surface / EmissionDisplay: PASS。
- Tier A: **PASS 36 / FAIL 0 / REVIEW 0 / N/A 0**。envelope back-test discriminates=True。
- motion: 4機種とも5-state 0 / 5、181-state 0 / 181、minimum clearance 0.6 mm。
- Oscillator / Noise / Delayのjack tessellation 16→12は、5,000内へ収める局所変更として受領する。
- 曲面hullに合わせたreadout trimmingは必要面積を維持しており受領する。input legendをjack上、output legendを
  jack下へ置く変更も、trunk railとの重なりを避ける妥当な配置として比較シートで受領する。
- `AudioModules_R2_A4_OA1`、S1/F1、既存4theme、Unity、docs、git、productionにOpus 5側の変更なし。

**S2は無条件受領。Opus 5側のfix-back候補はなく、追加作業を開始せず停止を維持する。次はCodexのC3隔離
取り込みであり、production登録、Q1、B1、APK、Questは引き続き別指示を要する。**

## 14. Codex C3隔離取り込み acceptance notes（2026-09-21）

S2の4機種を新規manifest `AudioModules_Superfine_C3`から専用candidate stagingへ取り込んだ。
C2、production Resources、既存4テーマ、theme picker、共通triangle cap 5,000は変更していない。
これによりSuperfine audio 10機種は、S1/F1由来のC2 6機種とS2由来のC3 4機種に分離した
candidateとしてUnity上で揃った。本番themeとしては未登録である。

| Model | Unity tris | Contract / runtime surfaces / cable endpoints | 5-state motion | Common 5,000 | Result |
|---|---:|---|---|---|---|
| Oscillator | 4,842 | PASS | PASS | PASS | PASS |
| Noise | 4,862 | PASS | PASS | PASS | PASS |
| Delay | 4,902 | PASS | PASS | PASS | PASS |
| Output | 3,026 | PASS | PASS | PASS | PASS |

C3検証結果:

- source integrity: **PASS**（S2 FBX / inspection reportのSHA-256は§13と一致）
- required node / port、renderer 7、material role 3、envelope、mount plane: **PASS**（4機種）
- knob pivot Z=55 mm、全port Z=54 mm、固定interaction collider包含: **PASS**
- display / signal surfaceのruntime割当: **PASS**
- typed-port cable endpoint解決: **PASS**
- 5-state motion: **PASS**（4機種、minimum mount Z=51.6 mm）
- triangle: **PASS 4 / REVIEW 0 / FAIL 0**
- cross-candidate dependency: **PASS**（0件）
- `AudioSocket` visual node-follow: **N/A**（3D音響用runtime root原点を維持する設計）
- Unity EditMode: **394 / 394 PASS、failure 0**

Kinetic Safety / SuperfineのOFF・ONを並べた4機種比較シートを生成し、形状、readout、signal surfaceの
実行時表示を確認した。Opus 5へ戻す形状修正候補はない。

Evidence:

- `Builds/Reports/candidate-AudioModules_Superfine_C3-staging-validation.md`
- `Builds/Reports/candidate-AudioModules_Superfine_C3-c3-audit.md`
- `Builds/Reports/candidate-AudioModules_Superfine_C3-motion-audit.md`
- `Builds/Reports/candidate-AudioModules_Superfine_C3-editmode-results.xml`
- `Builds/Reports/candidate-AudioModules_Superfine_C3-kinetic-vs-superfine-comparison.png`
- `Builds/Reports/candidate-AudioModules_Superfine_C3-imported-files.sha256`

**C3は完了。Opus 5側のF1候補はなく停止を維持する。次はQ1（Quest 48-object gate / 64-object stress）
またはB1だが、APK / Quest実機作業とproduction登録は引き続き別指示を要する。**

## 15. Codex → Opus 5: Superfine非audio拡張 N1 pilot正式作業指示（2026-09-21）

ユーザー決定により、Superfineをaudio moduleだけでなく、現行カタログの**非audio全14機種**へ拡張する。
Kinetic Safetyの現行機能配置とruntime contractを基準にしつつ、既存モデルの修正や色替えではなく、
Superfine S1/S2と同じ製造形状言語を持つ独立theme assetとして新規作成する。

### 15.1 全対象と機能契約

| Family | Model | Required authored nodes / surfaces | Runtime motion / states |
|---|---|---|---|
| Meter | MeterRound | `needle_pivot/needle` | 115° sweep、5-state audit |
| Meter | MeterMedium | `needle_pivot/needle` | 115° sweep、5-state audit |
| Meter | MeterLarge | `needle_pivot/needle` | 115° sweep、5-state audit |
| Meter | WindowMeter | `needle_pivot/needle` | 115° sweep、5-state audit |
| Panel | WindowPanel | `display_surface`のみ、legacy analog node禁止 | 固定graphic surface、read-only signal state |
| Monitor | TrendMonitor | `display_surface` | OFF / numeric / graph表示面 |
| Control | Lever | `handle_pivot/handle` | runtime −48°..0°、既定5 detent |
| Control | Toggle | `switch_pivot/switch` | ±28°、2 state |
| Control | Rotary | `knob_pivot/knob` | Z-axis rotation、parameter detent対応 |
| Control | Button | `button_travel/button` | 14 mm press、2 state |
| Control | Throttle | `throttle_pivot/throttle_handle` | ±35°、既定6 detent |
| Control | PowerSlider | `slider_travel/slider_handle` | 180 mm travel、既定11 detent |
| Indicator | Lamp | `indicator` separate renderer | OFF + low / medium / high発光確認 |
| Indicator | StatusIndicator | `indicator`, `status_safe`, `status_warn`, `status_danger` | 4 state |

ノード名、親子関係、local axis、pivot位置、可動範囲、display面の向きとUVは現行Unity契約を固定条件とする。
形状はKinetic Safety production / accepted candidateをread-only referenceとして比較するが、FBX、Blend、Prefab、
material、texture、`.meta`、GUIDをコピーまたは変更しない。

### 15.2 N1 pilot対象

N1では全14機種を一括生成せず、次の4機種だけで形状言語と機能面を確認する。

1. `MeterRound`: bezel、glass、scale、needle pivot、視認性を代表する。
2. `Lever`: bearing、guard、grip、detentと可動clearanceを代表する。
3. `Lamp`: separate emitter、段階発光時のlens / hood / bezelを代表する。
4. `TrendMonitor`: 大型display surface、bezel、runtime表示の視認性を代表する。

Superfine audioのfolded steel tray、returned edge、gasket reveal、molded bezel、保持された操作部、
button-head fastener、corner bumperという製造可能な語彙を継承する。ただしaudio moduleの0.24 × 0.20 m外形や
55 / 54 mm Zを転用せず、各機種の`InstrumentGreyboxSpecification` envelopeと現行pivotを守る。

### 15.3 N1成果物

出力先は既存packageを上書きしない次の新規directoryとする。

`ArtSource/Blender/BrushUp/Opus5/Superfine_NonAudio_N1_Pilot/`

revisionは`SFN1P`。各機種についてclean cage `.blend`、fixed-camera front / oblique / side、
neutralと可動／表示状態のrender、寸法・node・bounds・triangle・renderer・material-role report、
Kinetic Safetyとの同一camera比較を作る。4機種contact sheet、`REPORT.md`、`MANIFEST.md`、
`SHA256SUMS.txt`、handoff draftを含める。

handoff draft:

`/Users/kblab/Documents/AnalogInstrumentMR/ArtSource/Blender/BrushUp/Opus5/Superfine_NonAudio_N1_Pilot/OPUS5_SUPERFINE_NONAUDIO_N1_HANDOFF_DRAFT.md`

N1は**shape pilot**であり、FBX、triangulated delivery Blend、Unity assetはまだ作らない。

### 15.4 Budgetと監査

- MeterRound / Lever / Lampは現行common 5,000 triangles、TrendMonitorは現行large 25,000 trianglesを
  比較基準として実数を報告する。pilotでの超過はFAILに丸めず**REVIEW**とする。
- renderer / materialは現行機種別runtime budgetを変更しない前提で、authoring roleとdelivery正規化案を分けて報告する。
- collider、Realtime Light、AudioSourceをBlender / FBXへ含めない。
- mount plane後方、envelope、可動部と固定部の干渉、display法線、UV0、emitterの独立rendererを監査する。
- MeterRound / Leverは5 state、LampはOFF / low / medium / high、TrendMonitorはOFF / numeric / graphで比較する。
- PASS / FAIL / REVIEW / N/Aを分離し、REVIEWをPASSへ読み替えない。

### 15.5 N1承認後の展開計画

- N2-A controls / indicators: Lever、Toggle、Rotary、Button、Throttle、PowerSlider、Lamp、StatusIndicator。
- N2-B meters / displays: MeterRound、MeterMedium、MeterLarge、WindowMeter、WindowPanel、TrendMonitor。
- N2で全14機種のtriangulated Blend、deterministic FBX、inspection JSON、motion audit、比較sheetを揃える。
- CodexはN2受領後、C4 candidate stagingへ隔離取り込みする。本番theme登録は行わない。

### 15.6 禁止事項と停止条件

- audio S1/F1/S2、C2/C3、既存4theme、production asset、共通triangle cap、runtime codeを変更しない。
- `AudioModules_R2_A4_OA1`を参照、コピー、変更しない。
- Unity `Assets/`、`Builds/`、`docs/`、git、commit / push / PR、APK、Quest作業を行わない。
- N1の4機種以外へ展開しない。FBXを出力しない。

N1完了後は停止し、4機種のshape判断、bounds、triangle、node/pivot、state/motion、Tier判定、
checksum件数、変更ファイル一覧、handoff draft絶対pathを報告する。N2はユーザー/Codex承認後に別指示で開始する。

## 16. Codex → Opus 5: N1受領回答とN2正式作業指示（2026-09-21）

### 16.1 N1独立検証と受領

元checkoutのrepository rootから`SHA256SUMS.txt`を検証し、**72 / 72 OK**。package全体は
`SHA256SUMS.txt`と`MANIFEST.md`を含めて74 filesであり、handoff draft §冒頭の「70 files」は誤記、
REPORT §9の「72 files（MANIFESTとSHA256SUMSを除く）」が正しい。N1 assetをこの訂正だけで再buildしない。

| Model | tris | bounds / envelope | node / motion | Codex visual decision |
|---|---:|---|---|---|
| MeterRound | 2,760 | PASS | PASS | shape受領、glass REVIEW維持 |
| Lever | 1,096 | PASS | PASS | shape受領 |
| Lamp | 1,376 | PASS | N/A motion | shapeと4段階発光を受領 |
| TrendMonitor | 1,434 | PASS | PASS display geometry | shape受領、state sheetは要修正 |

Opus 5 Tier Aの**PASS 32 / FAIL 0 / REVIEW 1 / N/A 7**はそのまま記録し、MeterRound
`sealed_geometry` REVIEWをPASSへ読み替えない。Kinetic Safety比較とfamily sheetで、4機種が単純な色替えではなく、
Superfine audioと同じ製造形状言語を機種別envelopeへ展開していることを確認した。

Codex visual reviewでは、TrendMonitorのOFF / numeric / graph sheetが3状態ともほぼ白一色で、表示内容を
目視判別できなかった。これはshape FAILではないが、**runtime display visual REVIEW**としてN2で解消する。

### 16.2 Opus 5からの4質問への回答

1. **MeterRound glass**: modelled glassを残す。`static_opaque`へ結合しない。N2 deliveryは
   `static_opaque` / `static_readout` / `needle` / **separate transparent `glass`**の最大4 rendererとする。
   透明materialを含むmaterial数が現行共通budgetを超える場合はSuperfine固有**REVIEW**として記録し、
   勝手にglassを削除したり不透明化してPASSへ丸めない。
2. **delivery normalization**: Lever 3 renderer、Lamp 2 rendererは提案どおり受領する。TrendMonitorは
   `static_opaque` / `static_metal` / `display_surface`の最大3 rendererを許容するが、solid 2 rendererは
   同一opaque shared materialを使い、displayとの合計material roleを現行contract内に収める。
   MeterRoundだけは上記4 renderer案へ変更する。
3. **Lamp emission**: runtimeはnormalized valueから明度を変え、theme warning色をbase / emissionへ適用する。
   N2 lensは白〜neutralのemissive対応surfaceとし、色をgeometry / textureへ焼き込まない。比較renderでは
   representative warning hueを用いてOFF / low / medium / highの差を読めるようにする。
4. **TrendMonitor reference**: Kinetic Safety 190 trisは現行productionの意図された最小frameとして確認する。
   形状を模倣する必要はなく、Superfineのfull case / bezel / bumper案を維持してよい。N2 FBXはcanonical
   `-Z Forward / Y Up`で出力し、candidate側に−90°補正を持ち込まない。

補足: Leverの現行runtime契約は`amplitude=24°`、`rotationOffset=-24°`なので、実際のlocal deltaは
**−48°..0°**である。N1の5状態は正しく、§15.1の旧「±24°」表記を訂正した。

### 16.3 N2 scope

N1をshape承認し、非audio全14機種のN2制作を正式発注する。N1 packageを上書きせず、次の新規packageへ出力する。

`ArtSource/Blender/BrushUp/Opus5/Superfine_NonAudio_N2/`

revisionは`SFN2`。対象を次の2 batchとして管理するが、handoffとchecksumは1 packageにまとめる。

- N2-A controls / indicators: Lever、Toggle、Rotary、Button、Throttle、PowerSlider、Lamp、StatusIndicator。
- N2-B meters / displays: MeterRound、MeterMedium、MeterLarge、WindowMeter、WindowPanel、TrendMonitor。

N1のMeterRound、Lever、Lamp、TrendMonitorは承認shapeを基準にdelivery化し、他10機種は同じSuperfine形状言語で
展開する。各機種のenvelope、required node、parent、axis、pivot、motion range、state count、display / emitter surfaceは
現行Unity contractを固定条件とする。Kinetic Safetyの現行production / accepted assetはread-only比較に限る。

### 16.4 N2 deliverablesとvalidation

14機種それぞれについて、clean cage Blend、triangulated delivery Blend、deterministic FBX、inspection JSON、
front / oblique / side、全motion/state render、Kinetic Safety同一camera比較を作る。全機種contact sheet、
motion/state sheet、Tier A集計、renderer / material normalization表、`REPORT.md`、`MANIFEST.md`、
`SHA256SUMS.txt`、Codex向けhandoff draftを含める。

handoff draft:

`/Users/kblab/Documents/AnalogInstrumentMR/ArtSource/Blender/BrushUp/Opus5/Superfine_NonAudio_N2/OPUS5_SUPERFINE_NONAUDIO_N2_HANDOFF_DRAFT.md`

- FBXは`-Z Forward / Y Up`、metres、explicit triangulation。round-trip後のnode、triangle、bounds一致を検証する。
- delivery meshには用途に適したUV0を必須とし、display surfaceは0..1、local +Z、2 trianglesを基本とする。
- smallは現行5,000、largeは現行25,000を比較基準とし、超過はFAILへ丸めず**REVIEW**として実数を残す。
- 5-state / full-range motion、mount plane、envelope、fixed/moving interference、renderer/material、emitter、
  display visibility、z-fighting、sealed geometryを監査する。
- MeterRound glassのsealed / material REVIEWは維持してよい。glassを落として解消しない。
- TrendMonitorのOFF / numeric / graphは、画面内容が同一camera sheetで明瞭に異なることを画像とpixel差で確認する。
- LampとStatusIndicatorは全段階の色・明度を識別できること。発光色はbakeせずruntime差替え可能にする。
- PASS / FAIL / REVIEW / N/Aを分離し、REVIEWをPASSへ読み替えない。
- checksum件数は`SHA256SUMS.txt`実行結果、除外ファイル、package総数を相互に一致させる。

### 16.5 禁止事項と停止条件

既存4theme、audio Superfine package / candidate、N1、production asset、common budget、runtime code、Unity
`Assets/` / `Builds/` / `docs/`、git、`AudioModules_R2_A4_OA1`を変更しない。commit / push / PR、APK、Quest、
Unity import、C4、本番登録を行わない。

N2完了後は停止し、14 FBX SHA-256、triangle、bounds、node/pivot、renderer/material、Tier A、motion/state、
checksum件数、変更ファイル一覧、handoff draft絶対pathを報告する。C4はCodex受領後の別工程とする。

## 17. Codex → Opus 5: N2条件付き受領とN2-F1正式作業指示（2026-09-21）

### 17.1 N2独立検証

元checkoutで`Superfine_NonAudio_N2/SHA256SUMS.txt`を検証し、**256 / 256 OK**。package 258 files、
14 FBX、14 cage Blend、14 triangulated Blend、14 inspection JSONが揃っている。全機種がtriangle budgetと
envelope内、mount plane後方0 mm、FBX round-trip node / triangle一致である。TrendMonitorのOFF / numeric /
graphはN1と異なり明瞭に識別でき、N1のruntime-display visual REVIEWは解消した。

Opus 5 Tier Aの**PASS 116 / FAIL 0 / REVIEW 20 / N/A 18**は報告値として保持し、material、glass、
sealed geometry、contact seamのREVIEWをPASSへ読み替えない。Codex側で現行Unity production contractと照合した結果、
次の追加判定を行う。

- 12機種: shape / node / motionのN2成果を受領。
- WindowPanel: **contract FAIL**。現行productionはWP3-r2以降の固定`display_surface`方式であり、
  `WindowPanelCandidateContractValidator`は`vane` / `vane_pivot`をlegacy nodeとして明示的に禁止する。
- Rotary: **visual semantics REVIEW**。parameter step countはruntimeで変更可能なのに、11本の目盛が固定11 detentを
  表して見える。機能FAILではないが、可変step設計と外観を一致させるためF1で修正する。

従ってN2を**条件付き受領**とし、C4はN2-F1受領まで開始しない。

### 17.2 Opus 5からの4質問への回答

1. **material budget**: C4ではcommon shared-material budgetを変更せず、Superfine candidate固有の暫定値として
   meter / display / statusは最大4、Rotary / TrendMonitorは最大3を許容し、超過分を**REVIEW**で保持する。
   glass、dark readout、independent emitterを削ってPASSにしない。正式値はC4実測とQuest負荷後のB2で決める。
2. **StatusIndicator**: housing + 3 lensの4 rendererと、rendererを持たないparent `indicator` nodeを受領する。
   `status_safe` / `status_warn` / `status_danger`をThemeVisualManifestのstate rendererへ割り当てる形で正しい。
3. **WindowPanel pivot**: `(460, -20, 190) mm`の`vane_pivot`は受領しない。現行契約では機械vane自体がなく、
   唯一の`display_surface`が固定表示基準である。read-only meter signalはLogic側rendererなしtargetで維持される。
4. **Rotary detents**: full 360° rotationとruntime可変detentは正しいが、外観の11固定目盛は採用しない。
   knobの単一indexは維持し、周囲はcontinuous scaleまたは段数を意味しない少数のorientation markとする。

### 17.3 N2-F1 scope

N2 packageを上書きせず、WindowPanelとRotaryだけを次へ新規出力する。

`ArtSource/Blender/BrushUp/Opus5/Superfine_NonAudio_N2_F1/`

revisionは`SFN2F1`。

#### WindowPanel

- `vane`、`vane_pivot`、`needle`、`needle_pivot`、analog scale / ticksを削除する。
- `display_surface`を正確に1個持ち、MeshFilter / MeshRenderer、2 triangles、UV0 0..1、instrument local +Z normal、
  local +Y up、coplanarとする。これは固定motion targetで、回転させない。
- glass overlayを置かず、runtime procedural graphicが直接見える構造とする。
- deliveryは最大3 renderer / 3 material roleを目標とし、OFF / numeric / graphを明瞭に比較する。
- 現行`WindowPanelCandidateContractValidator`相当のlegacy-node拒否をBlender側監査へ追加する。

#### Rotary

- `knob_pivot/knob`、local +Z full 360°、単一index、envelope、renderer budgetを維持する。
- 11 detentを示す固定tick列を削除する。continuous ringまたは段数非依存のorientation markへ置換する。
- 0 / 45 / 90 / ... / 315°のmotion auditを維持し、任意2〜最大step countで誤認しない外観にする。

### 17.4 Deliverables / stop

2機種についてcage Blend、triangulated Blend、deterministic FBX、inspection JSON、全state render、N2との
before / after、Kinetic Safety比較、Tier A、`REPORT.md`、`MANIFEST.md`、`SHA256SUMS.txt`、handoff draftを作る。

handoff draft:

`/Users/kblab/Documents/AnalogInstrumentMR/ArtSource/Blender/BrushUp/Opus5/Superfine_NonAudio_N2_F1/OPUS5_SUPERFINE_NONAUDIO_N2_F1_HANDOFF_DRAFT.md`

既存4theme、N1、N2、audio Superfine、production、common budget、runtime code、Unity、git、
`AudioModules_R2_A4_OA1`を変更しない。commit / push / PR、APK、Quest、C4、本番登録を行わない。

完了後は停止し、変更形状、node差、triangle、renderer / material、FBX SHA-256、Tier A、checksum件数、
変更ファイル一覧、handoff draft絶対pathを報告する。C4はN2の他12機種とN2-F1の2機種を組み合わせる。

## 18. Codex → Opus 5: N2-F1受領回答（2026-09-22）

### 18.1 独立検証

元checkoutのrepository rootから`Superfine_NonAudio_N2_F1/SHA256SUMS.txt`を検証し、**53 / 53 OK**。
packageはchecksum対象53 filesに`MANIFEST.md`と`SHA256SUMS.txt`を加えた**55 files**である。Opus 5 handoff
draft冒頭の「51 / 51 OK」「package 53 files」は件数誤記であり、この実測値を正とする。成果物の欠落や
checksum不一致ではないため、packageの再生成は要求しない。

2 FBXのSHA-256は次のとおり。

- WindowPanel: `d5f13bbdf59e0503761e6dd78eab4e60c61c3447b68ea34494db38d4de0015e4`
- Rotary: `a847a887e497620e66852ee33d40c454d4eea49ae3fca6f4709b5a89568c02e2`

Tier Aの**PASS 18 / FAIL 0 / REVIEW 3 / N/A 3**を報告値のまま保持する。material budget 2件と
WindowPanel contact seam 1件をPASSへ読み替えない。FBX round-trip、node list、triangle、bounds、mount plane、
envelope、legacy-node rejection、sealed geometry、z-fighting、Rotary 8-state motionは提出証跡と一致した。

### 18.2 受領判断

- **WindowPanel: 受領。** `vane` / `vane_pivot` / analog scale / ticks / glass overlayは除去され、唯一の
  `display_surface`は2 triangles、UV0 0..1、local +Z、固定motion targetである。1,434 triangles、3 renderer、
  3 material role。OFF / numeric / graphは比較sheetで明瞭に識別できる。
- **Rotary: 受領。** 11固定tick列は除去され、段数を表さないcontinuous collarへ置換された。
  `knob_pivot` / `knob`、単一index、local +Z full 360°、8-state motionを維持する。2,664 triangles、
  3 renderer、3 material role。collarは可変step semanticsと衝突しないため現案を採用する。

これによりN2の他12機種とN2-F1の2機種、合計14機種をC4隔離取り込み対象として受領する。

### 18.3 Opus 5からの3確認への回答

1. Rotary continuous collarは現案を受領し、ringなしへの再変更は要求しない。
2. C4ではSuperfine固有の暫定material値を使用し、3 roleをexpected **REVIEW**として保持する。common budgetは
   変更しない。
3. 14機種のcombined candidate manifestはC4でCodexが作成するため、Opus 5による再buildやcombined manifest生成は
   不要である。

Opus 5のN2-F1工程は完了。次はCodex所有のC4であり、production登録、theme picker、APK、Questはまだ行わない。

## 19. Codex: 非audio全14機種のC4隔離Unity取り込み（2026-09-22）

### 19.1 取り込み範囲

N2の12機種とN2-F1のWindowPanel / Rotaryを、combined candidate
`Superfine_NonAudio_C4`として隔離取り込みした。production Resources、既存4テーマ、theme picker、共通triangle
cap、`AudioModules_R2_A4_OA1`は変更していない。candidate manifestは14 entriesで、WindowPanel / Rotaryだけが
revision `SFN2F1`、他12機種が`SFN2`である。cross-candidate dependencyは0件。

### 19.2 検証結果

- staging contract: **PASS 7 / REVIEW 7 / FAIL 0**。Lever、Toggle、Button、Throttle、PowerSlider、Lamp、
  StatusIndicatorがPASS。MeterRound / Medium / Large / WindowMeter / WindowPanel / TrendMonitor / Rotaryは
  common material budget 2に対する3〜4 roleをREVIEWとして保持した。
- triangle: 14機種すべて現行small / large上限内でPASS。共通上限は変更していない。
- TrendMonitor: displayは0.348 × 0.188 mで、旧minimum width 0.36 mに対して**REVIEW**。表示面割当と
  Kinetic Safety比較上の可読性はPASSだが、寸法差をPASSへ読み替えない。
- motion: meter 4機種の230°、Lever 48°、Toggle 56°、Rotary 360°、Button 14 mm、Throttle 70°、
  PowerSlider 180 mm、固定WindowPanelが全てPASS。Lamp / StatusIndicator / TrendMonitorはgeneric motion監査N/Aで、
  C4 runtime binding監査により各emitter / display surfaceをPASSした。
- runtime binding / signal role: **14 / 14 PASS**。WindowPanel / TrendMonitorのdisplay、Lampの段階点灯、
  StatusIndicatorの3 state rendererを確認した。非audio objectはauthored typed `port_*`を持たず、論理信号の
  cable endpointはinstrument rootであるためtyped visual portは**N/A**。interaction colliderはruntime所有で、
  candidate visual内には含めない。
- Unity EditMode: **395 / 395 PASS、failure 0、skipped 0**。

### 19.3 比較証跡

- Kinetic Safety / Superfine比較:
  `Builds/Reports/candidate-Superfine_NonAudio_C4-kinetic-vs-superfine-comparison.png`
  (`0b16c611e170e57d20842a4c4159f8bc905014eb43971d07fc64959cd26e43a8`)
- Superfine Unity shape contact sheet:
  `Builds/Reports/candidate-Superfine_NonAudio_C4-unity-shape-contact-sheet.png`
  (`622caac924281133c897420fe8d2bc2d460de3fbe7d5e55ee4e01089a96933cd`)
- staging validation / motion / runtime audit:
  `Builds/Reports/candidate-Superfine_NonAudio_C4-staging-validation.md`、
  `Builds/Reports/candidate-Superfine_NonAudio_C4-motion-audit.md`、
  `Builds/Reports/candidate-Superfine_NonAudio_C4-c4-audit.md`
- EditMode XML:
  `Builds/Reports/candidate-Superfine_NonAudio_C4-editmode-results.xml`
  (`f8bd01074723bfc19781acc27c5e2f1d57be6013455d42d9da04e6afa00cbfd5`)

### 19.4 F1候補と停止

必須のOpus 5 fix-backはない。material role超過はC4で予定していたSuperfine固有REVIEWであり、形状削減を
要求しない。TrendMonitorの0.348 m幅だけは、将来旧0.36 m minimumを厳格維持すると判断した場合の
**条件付きF1候補**として残す。現状は表示内容とruntime割当が確認できるためC4をFAILにはしない。

**C4はcandidate-onlyで完了し、ここで停止する。Q1、B1、production登録、APK、Questは別指示を要する。**

## 20. Codex: Q1後回しとP0本番昇格準備（2026-09-22）

ユーザー指示によりQ1のQuest 48-object gate / 64-object stressを後回しとした。Q1結果を前提とするB1の
機種別上限は確定せず、candidate実数 + 7.5%を100 triangles単位で切り上げた値を**未採用の暫定値**として
記録する。共通5,000 capと既存validatorは変更していない。

本番assetを変更しないP0 readiness監査を追加し、C2 6機種、C3 4機種、C4 14機種の合計24機種を横断した。

- 24 unique candidate FBX / prefab pair: PASS
- candidate FBX / prefab GUID uniqueness: PASS
- cross-candidate dependency: 0、PASS
- `Content/Themes/Superfine` / `Resources/Superfine` production target collision: 0、PASS
- runtime theme catalogue: 既存4テーマのまま、PASS
- production mutation: **NONE**

readiness report:

`Builds/Reports/superfine-production-readiness.md`

SHA-256: `a796d77a71981cf29a4eec507c4b5e5ddade163fc54584c5b98bb42d3a28f023`

判定は**READY WITH DEFERRED GATES**。Pでは既存enum値0..3を維持して`Superfine = 4`を追加し、theme ID
`superfine`、display name `SUPERFINE`、palette、cycle / parse / persistence、visual factoryの
`Resources/Superfine/Prefabs` routingを追加する。24機種はfresh GUIDで一括登録し、audio 3 roleとnon-audio
4 roleのcanonical production materialへ再結線する。candidate staging依存を0にしたうえでatomic backup /
rollbackを必須とする。

暫定audio capはVCA 5,200、Mixer 5,400、Filter 5,300、Envelope 6,000、LFO 7,700、Sequencer 7,000、
Oscillator 5,300、Noise 5,300、Delay 5,300、Output 3,300。これらはB1採用値ではなく、Q1後回し中も
triangle REVIEWをPASSへ読み替えない。

P0追加後のUnity 6000.3.19f1 EditModeは**395 / 395 PASS、failure 0、skipped 0**。結果XMLは
`Builds/Reports/superfine-p0-editmode-results.xml`
（SHA-256 `1fbc2db1368d28a15d420518254c018e6ee7fd0af7d3520f452fa31219b8342c`）。

**P0を完了。本節は本番登録直前のreadiness snapshotである。Pの適用結果は§21を正とする。**

## 21. Codex: 第5テーマとして本番登録Pを完了（2026-09-22）

ユーザー指示によりPを実行し、既存enum値0..3を保持したまま`Superfine = 4`を追加した。theme IDは
`superfine`、表示名は`SUPERFINE`、catalogue countは5である。palette、theme cycle / parse / persistence、
visual factory、display / signal色、操作音のtheme差を5テーマ対応へ拡張した。

### 21.1 本番asset

- C2 6機種 + C3 4機種 + C4 14機種を、24 FBX / 24 prefabとして一括登録した。
- canonical materialはaudio 3種、non-audio 4種、合計7種。
- production pathは`Assets/MatsuMotoMeterAR/Content/Themes/Superfine`と
  `Assets/MatsuMotoMeterAR/Resources/Superfine`。
- candidateまたはKinetic Safetyの`.meta`をコピーせず、production assetへfresh GUIDを発行した。
- production prefabから`/CandidateStaging/`への依存は0件。
- 既存4テーマのmodel、FBX、prefab、material、texture、GUIDは変更していない。

昇格レポートは`Builds/Reports/superfine-production-promotion.md`
（SHA-256 `8832200ead1124bf0d9d126ce6e53436b4d6f85a69a2aaa04d8cb8ace20a78b6`）。
atomic rollback記録は`Builds/ModelReplacementBackups/Superfine_P_20260922_111623`、手順は
`docs/SUPERFINE_PRODUCTION_ROLLBACK.md`に記録した。

### 21.2 検証

- Superfine専用active prefab validation: **PASS**、既存REVIEWは保持。
  `Builds/Reports/superfine-active-visual-prefab-validation.md`
  （SHA-256 `5e3300d0108aa2cf70206975ae77d6eb73fffd36c6336f626afed518b5703ec5`）。
- production motion audit: **PASS**。Lever 5状態、Toggle 2状態、Throttle 6状態、PowerSlider 11状態。
- production signal visual audit: **PASS**。Lampの明度差0.880、StatusIndicatorの状態差0.950。
- Unity 6000.3.19f1 EditMode: **397 / 397 PASS、failure 0、skipped 0**。
  `Builds/Reports/superfine-production-editmode-results.xml`
  （SHA-256 `b761f04b955f4eaa484d3171252f22c94a44d32c87b6930f288a111da82129bb`）。

### 21.3 deferred gateとREVIEW

Q1 Quest 48-object gate / 64-object stressはユーザー指示により後回しで、**PASSではない**。B1の機種別capも
未採用の暫定値のままとする。共通triangle cap 5,000は変更していない。

- Audio triangle REVIEW: Envelope 5,496、LFO 7,122、Sequencer 6,498。
- Non-audio material REVIEW: MeterRound / Medium / Large / WindowMeter / WindowPanel / TrendMonitor / Rotary。
- TrendMonitor display width REVIEW: 0.348 m（旧minimum 0.36 m）。
- 24-object aggregate renderer: Superfine 116（既存acceptance 103を超過）。Q1までdeferred REVIEW。

これらをPASSへ読み替えずに本番登録した。負荷試験、APK、Quest実機作業は本工程に含めていない。

**Pは完了。次の未完工程はQ1負荷試験と、その結果に基づくB1上限確定である。**

## 22. Codex: B1 preflightとQ1実行経路を準備（2026-09-23）

Q1を後回しとするユーザー判断は維持し、B1 capを採用せずにpreflightだけを完了した。本番audio 10機種の
triangle実数と、実数 + 7.5%を100単位で切り上げた暫定capを
`Builds/Reports/superfine-b1-preflight.md`へ固定した。暫定値は§20から変わらず、すべて**NOT ADOPTED**である。

Quest host scriptは第5テーマ登録後も`Superfine`を拒否し、audio kindを指定できない状態だったため、
`scripts/run-quest-performance-gate.sh`を5テーマとaudio 10 kindへ対応させた。48/64 matrixにも
`INSTRUMENT_KIND`転送を追加した。`bash -n`と、`Superfine` + `AudioLfo`がargument validationを通過してADB確認まで
到達するpreflightをPASSした。APK build、install、Quest接続、負荷計測は行っていない。

Q1の主scenarioは48 × AudioLFO（341,856 tris / 336 prefab renderers）をacceptance、64 × AudioLFO
（455,808 tris / 448 prefab renderers）をcharacterizationとする。AudioSequencer 48台をruntime/display cross-checkに
使用する。これはgeometry cap用のvisual gateであり、接続済みaudio graphのDSP負荷試験を代替しない。

**B1 preflightは完了。Q1 / B1の状態はdeferred / NOT ADOPTEDのまま。**

## 23. Codex: Quest review APKをbuild / installして自動smokeを完了（2026-09-24）

Unity 6000.3.19f1で最新worktreeからInstrument Audio Review APKをbuildした。APKは84,169,119 bytes、
SHA-256 `99844afee7045a3149635464066b40c41ad003c09ffc6d5bb29dd88080382b29`、package versionは
0.3.0 / versionCode 3。Quest 3 `2G0YC1ZG2J02HL`へ`adb install -r`で上書きし、COLD launchはStatus ok。
PID 5570は15秒後も維持され、Fatal / ANR / Unity errorは0件だった。

証跡は`Builds/Reports/superfine-quest-smoke-2026-09-24.md`。これはbuild / install / launchの自動smoke
PASSであり、ヘッドセット内の24機種表示、controller操作、接続、音のhuman acceptanceとQ1 48/64負荷試験は
未判定である。B1 capもNOT ADOPTEDのままとする。

## 24. Quest表示不具合 F2: Window Panelモデル修正要求（2026-09-24）

Quest実機で、SuperfineのWindow Panelにランタイム図形が表示されない。ForgeBrassでは同じランタイム処理で
図形が表示される。Superfine専用のランタイムquad、専用material、強制UV差し替えによる暫定対処はユーザー判断で
不採用とし、Codex側から撤回した。既存4テーマを含む表示契約をモデル側で満たす方針とする。

Unity production prefab監査で原因を確定した。

- ForgeBrass Window Panelの`display_surface` mesh local boundsは
  `(1.200, 0.660, 0.000) m`で、ランタイム図形scaleは`(0.540, 0.540, 0.540)`。
- Superfine Window Panelの`display_surface` mesh local boundsは
  `(1.384, 0.000, 0.664) m`で、面がmesh local XZに寝ている。
- 現ランタイムはdisplay meshのlocal X/Y extentsから図形寸法を得るため、Superfineではworld heightが0となり、
  ランタイム図形scaleが`(0, 0, 0)`になる。これが非表示の直接原因である。
- root-localでは面の法線+Z、triangle winding、determinant、UV0、手前の遮蔽物なしを満たしていたため、従来validatorが
  mesh-local軸不整合を見逃していた。

監査証跡:

- `Builds/Reports/superfine-display-geometry-audit.md`
- `Builds/Reports/superfine-display-runtime-ForgeBrass-WindowPanel.png`
- `Builds/Reports/superfine-display-runtime-Superfine-WindowPanel.png`
- Quest画面: `/private/tmp/analogmr-quest-superfine-current.png`（作業ホスト上の一時証跡）

### 24.1 Opus 5へのF2要求

`SM_WindowPanel_Superfine_SFN2F1`を基に、`Superfine_NonAudio_N2_F2`としてWindow Panelだけを修正する。

1. `display_surface`のmesh dataをlocal XY平面へ置く。mesh local boundsはX > 0、Y > 0、Z = 0とする。
2. mesh local normal / triangle frontを+Z、UV0をU/Vとも0..1、UVの上方向をlocal +Yとする。
3. object transformは可能ならrotation identity / positive unit scaleへapplyする。Unity prefab-root localでは現在の表示面中心
   `(0, 0, 0.196) m`、表示寸法`1.384 × 0.664 m`、正面+Zを維持する。
4. node名`display_surface`、root名、Housing / FaceMetal / EmissionDisplayの3 role、renderer数3、既存外形、
   triangle budget 25,000以内を維持する。追加の表示quad、追加material、追加rendererは作らない。
5. blend、triangulated blend、FBX、inspection JSON、front / oblique / state render、SHA256SUMS、handoff draftを納品する。
   inspection JSONにはmesh-local bounds、object transform、root-local bounds、normal、UV spanを明記する。

Codex側はmodel受領後、隔離candidateとして取り込み、強化したWindow Panel contract validator、runtime scale、Unity比較render、
EditMode、Questで検証する。本番FBX / prefabの置換はcandidate合格後に別工程で行う。

### 24.2 Superfine音響モジュールは別調査

production 10機種の`display_surface`は、root-local正面+Z、triangle front dot 1、positive determinant、中央9点の前面遮蔽0を
確認した。ForgeBrassと同じくauthored UV0は無いが、共通ランタイムがUVを生成する。Unity実レンダリングでは直接生成と
ForgeBrass→Superfineテーマ切替の両方でVCAの文字・バー表示を確認した。したがって現時点で音響10機種の3Dモデルを
不良と断定せず、Opusへ形状変更は要求しない。Quest固有または配置preview / operation状態の実行経路をCodex側で追跡する。

**Opusの次ターンは24.1のWindow Panel F2のみ。音響10機種は待機する。**

## 25. Codex: Window Panel N2-F2を受領し本番反映（2026-09-24）

Opus 5の`Superfine_NonAudio_N2_F2`を受領した。元checkoutで
`SHA256SUMS.txt`を検証し、**31 / 31 OK**。Window Panel FBXのSHA-256は
`8c732c8b41fc0b1fc45d5f15a3aa4f76c1fb60770d7700809223e9dcc9d20b88`で、handoff記載値と一致した。

Opus 5から提示された2点には次のように回答する。

1. `display_surface` objectがファイル内で`Rx(+90°)`を持つ構成を受領する。Unity取込後にmesh-local XY、
   root-local正面+Z、positive determinantが成立しているため、全モデルをZ-forwardへ作り直す追加F3は不要。
2. pivot `(0, 0, 196) mm`への移動を受領する。root-local表示面中心 `(0, 0, 0.196) m`を維持し、
   runtime graphicの配置と固定motion契約にも一致する。

`Superfine_NonAudio_N2_F2`として隔離取り込み後、強化済みWindow Panel契約、motion audit、固定比較画像、
関連EditMode 4 / 4をPASSした。Kinetic Safety比較画像でもF2の外形を維持したまま図形表示を確認した。
Gate Cは12 / 12成立し、Quest 48 / 64負荷試験だけ従来方針どおりDEFERREDとした。

本番反映後の実測は次の通り。

- mesh local bounds: `(1.384, 0.664, 0) m`
- root-local表示面中心: `(0, 0, 0.196) m`
- runtime graphic scale: `(0.543273, 0.543273, 0.543273)`（旧値`0,0,0`）
- triangles / renderers / materials: `1,434 / 3 / 3`
- 全EditMode: **413 / 413 PASS**
- candidate dependency: 0
- rollback: `Builds/ModelReplacementBackups/Superfine_NonAudio_N2_F2_20260924_205114`

本番PrefabのSHA-256は
`3c2ecf2c16b236f6cfc2abe391275d02d9cb409ef5415e98ac98ae8b0e5f31ee`。
3 materialの共通上限超過は既知の**REVIEW**を維持し、PASSへ読み替えない。

主要証跡:

- `Builds/Reports/candidate-Superfine_NonAudio_N2_F2-staging-validation.md`
- `Builds/Reports/candidate-Superfine_NonAudio_N2_F2-kinetic-vs-superfine-comparison.png`
- `Builds/Reports/candidate-Superfine_NonAudio_N2_F2-gate-c-readiness.md`
- `Builds/Reports/candidate-Superfine_NonAudio_N2_F2-production-promotion.md`
- `Builds/Reports/superfine-display-geometry-audit.md`
- `Builds/Reports/superfine-display-runtime-Superfine-WindowPanel.png`
- `Builds/Reports/superfine-n2-f2-postpromotion-editmode-results.xml`

音響10機種についても原因を確定した。SuperfineだけFBX importerの`Read/Write`が無効で、Quest Player上の
`AudioModuleDisplayView.EnsureDisplayUv()`がmesh UV / verticesを読めず例外停止していた。既存4テーマは
`isReadable: 1`、Superfine 10機種は`isReadable: 0`である。これはUnity importer設定の不整合であり、
**Opus 5の音響モデル修正は不要**。Codex側で全10機種を`isReadable: 1`へ統一し、production importer設定、
candidate staging builder、display契約validatorへ再発防止を追加した。Window Panel F2と合わせた全EditModeは
**413 / 413 PASS**。更新APK
`Builds/QuestReview/AnalogInstrumentMR-InstrumentAudio-review-quest3.apk`を生成し、SHA-256
`c4370b8a7b756752764cac39cedfd6b2ceaa7b3f801236283c71cbce582bc741`、Questへの`adb install -r`はSuccess。
起動時はQuestのcontroller-required system dialogで待機したため、この時点では人間による最終表示確認を
未判定とした。その後の実機確認結果は§26に記録する。

**N2-F2は無条件受領し本番反映済み。Opus 5側の追加F3は不要で停止を維持する。**

## 26. Quest human acceptance（2026-09-25）

ユーザーが更新APKを実機で操作し、正常動作を確認した。これにより§25で未判定だった
人間による最終実機動作確認を**PASS**とする。直近の修正対象であるSuperfine Window Panelの
runtime図形表示と、Superfine音響モジュールの情報表示を含む更新APKについて、追加の不具合報告はない。

この受入は通常の表示・操作に対するhuman acceptanceであり、48台acceptance / 64台stressの
定量負荷試験Q1を代替しない。Q1は従来方針どおり**DEFERRED**、B1機種別capは
**NOT ADOPTED**のまま維持する。Opus 5へ追加のmodel修正は要求しない。

## 27. Opus 5 → Codex: 音響モジュール使い方ガイドを main へ公開（2026-09-26）

**この節はOpus 5が記入した。** 本文書でOpus 5が書き込むのは初めてであり、作業依頼では
なく連絡である。Codexへ判断や作業を求めるものは末尾の1点のみ。

### 27.1 何をしたか

ユーザーの指示により、音響モジュールの利用者向け資料を作成し、**`main`へ直接commit /
pushした**。

- commit: `c6ed7f5` "Add modular audio module user guide"（`3686764..c6ed7f5`）
- 追加: `docs/AUDIO_MODULE_USER_GUIDE.md`（380行、新規）
- 変更: `README.md`（+4行。既存docsリストの下へ当該ガイドへのリンクを1段落追加）
- 他のファイルは変更していない。差分は2ファイル・384行追加のみ

内容は、5つのsignal domainと接続規則、trigger / gateの違いとEnvelopeでの挙動差、
ADSRの実値、接続時の自動port選択、定番patch 8種、症状別の切り分け手順。
port名・初期値・範囲・振る舞いは`Assets/MatsuMotoMeterAR/Runtime/Audio/`
（`ModularAudioPort.cs`、`ModularAudioNodes.cs`、`ModularAudioGraph.cs`、
`ModularAudioPatchPolicy.cs`）の実装から読み取っており、一般的なシンセ解説ではない。

### 27.2 Codexが知らない可能性がある点

`docs/`はこれまでCodexの担当領域で、Opus 5は一度も書き込んでいなかった。今回が例外で、
**Codexが次に`main`を取り込むとき、この2ファイルが増えている**。Codex側の作業ブランチ
`codex/audio-module-visuals`（`d419d44`、未commit 560件）には触れていない。

### 27.3 期限のある注記が1つ入っている（Codexへの唯一の依頼）

ガイドが説明している実装は**`main`には存在しない**。`Runtime/Audio/`は
`codex/audio-module-visuals`にしかなく、`main`にはmergeされていない。公開リポジトリの
読者が該当コードを探して見つけられないため、ガイド冒頭の引用ブロックに次の断りを入れた。

> 執筆時点で、その実装は`main`にはマージされていない（ブランチ
> `codex/audio-module-visuals`、コミット`d419d44`）。`main`を見ても該当コードは
> 存在しないので注意。

**音響システムが`main`へmergeされた時点で、この断り書きは削除が必要**である。残したまま
にすると文書が事実と異なる状態になる。merge作業を行うCodex側で同時に落とすか、Opus 5へ
指示してほしい。

### 27.4 触れていないもの

Superfineの全package（N2 / N2-F1 / N2-F2、audio各種）、N1 pilot、既存4テーマ、
production asset / prefab、共通budget、runtime code、`Assets/`、`Builds/`、
Codex worktreeの未commit変更。`main`への変更は27.1の2ファイルのみで、他のbranchへは
pushしていない。Opus 5の各packageはpush後もchecksum全件OK、FAILED 0。
