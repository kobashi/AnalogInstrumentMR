# v0.3 development roadmap proposal

## Goal

v0.3の主目標は、接続した信号をその場で読み取り、意図した変換を安全に調整できる
MR計器環境にすることである。機能追加と並行して、Quest 3で近接表示に耐える3Dモデル
品質を、画像比較と実機確認を含む再現可能なgateで段階的に改善する。

すべてをv0.3へ詰め込まず、最初のrelease sliceを「monitor MVP + 接続parameter編集 +
対象を絞った3D品質改善」とする。複雑な複数入力合成と信号処理nodeは、その基盤を再利用
して後続sliceへ進める。

## Priority 0: baseline and release gates

1. `main`の133 EditMode tests、39 active visual prefabs、Quest 48 / 64 matrixを
   v0.3の回帰baselineとして固定する。
2. 3D候補はactive assetへ直接上書きせず、manifest-driven isolated stagingから
   Gate Cを通す。
3. 固定cameraのbaseline / candidate画像、Prefab Preview、Quest実機を視覚受入の
   必須証跡とする。数値検査だけで見栄えの改善を判定しない。
4. Blender作業領域の中間revision、`.blend1`、診断画像はGitへ一括追加しない。
   採用source、FBX、compact report、最終比較画像だけを専用commitで追跡する。

## Priority 1: monitor MVP

最初に独立配置型のTrend Monitorとして数値表示と低頻度trend graphを実装する。
既存計器へのoverlay案は、表示面の向きと機種ごとの面積差が大きいため撤回する。
図形表示は同じ表示基盤を使うが、MVPの完了条件には含めない。

- 最大4入力の現在値、min / max、接続状態を色分け表示
- 入力ごとの固定長ring bufferによる短時間trend graph
- 通常の操作sourceに加え、読取専用meterの値を観測専用入力として接続可能
- Trend Monitorをtargetとして先に選び、その後に入力元を選ぶ接続UX
- 表示更新頻度を信号評価頻度から分離し、Quest向けに上限を設定
- per-frame allocation、動的Material生成、無制限mesh rebuildを禁止
- monitorが未接続・無効値・範囲外を明確に表示

価値は高く、既存のDirect / Invert / Range / Threshold接続を変更せず観測できるため、
後続機能の診断UIにもなる。

## Priority 2: connection parameter editing

**完了（2026-08-27）:** schema v5、接続単位のRange入出力min / max、Threshold値・
ABOVE / BELOW、HUD preview、取消、保存・復元を実装し、EditMode 162 / 162とQuest 3実機をPASS。
hysteresisは実際のchattering要件が確認された場合の後続拡張とする。

既存接続を作り直さず、RangeとThresholdのparameterをEdit / Connect UIから変更できる
ようにする。

- Rangeの入力min / maxと出力min / max
- Thresholdの閾値、比較方向、必要ならhysteresis
- Direct / Invertを含む共通preview
- schema移行、保存・復元、取消、異常値clamp
- monitor上で変換前後を確認できること

monitorを先に置くことで、parameter編集の結果をQuest内で直接確認できる。

## Priority 3: targeted 3D model quality lane

39モデルの全面作り直しは行わず、既知欠陥、利用頻度、近接時の視認性で順番を決める。

1. Toggle D5 / D10候補: 既存の3テーマcandidateを最新Gate C schemaへ再整理し、証跡の
   不足を補う。production昇格は別承認とする。
2. Button D1 / D2: emissive glyph復元とForge Brass plunger clearanceを同じcandidateで
   解決し、OFF / ONと押下全域を確認する。
3. Orbital Analog meters D3 / D4: tickとinner scaleのclearance修正を、M2n8で確立した
   full-dial visual gateへ合わせる。
4. Kinetic Safety WindowMeter / WindowPanel D7 / D8: 可動部の交差をdesign proposalから
   解決する。
5. その他のモデルは共通contact sheetで視覚reviewし、具体的な欠陥または明確な品質差が
   確認できたものだけ候補化する。

### 完了（2026-08-27）: Lever geometry G2

- **Kinetic Safety Lever:** `handle`全体ではなく、負向きだった98頂点のグリップ主成分だけを
  反転し、正向きだった棒・軸元・上部小部品を維持した。上端へ薄い専用キャップを追加して
  内部が見える開口を閉じた。
- **Orbital Analog Lever:** 棒とグリップ間の15.78 mmの空隙を、既存`handle`内の接合カラーで
  橋渡しした。可動pivot、Renderer 2、Material 2を維持した。
- FBX round-tripの全成分で正体積、boundary edge 0、non-manifold edge 0。Active Prefabと
  5状態Motion Audit、Quest 3近接視覚確認をPASSした。

各候補は、形状contract、triangle / renderer / material予算、全可動域、固定画像、Quest
近接・1 m表示、48 / 64構成への影響を確認する。透明glassは現状のQuest負荷と描画順問題を
増やすため標準要件にせず、必要性が実機画像で示された場合だけ別検討する。

### Deferred visual and instrument redesign backlog

次の3件は後工程で扱う。第4テーマproduction Gate、48 / 64 objects長時間試験、現在のrelease作業を
止めて着手しない。実装開始時には個別candidate、固定画像、Quest Gateを設ける。

1. **形状・texture完了（2026-08-29）: 既存3テーマのTrend Monitorをテーマ固有形状へ再設計する。**
   Kinetic Safety / Forge Brass / Orbital Analogの同一筐体を、ThemeShapes T1で各style guideに
   沿った固有silhouette、bezel、取付意匠へ置換し、画像受領、Gate C、本番登録まで完了した。
   `TrendMonitor_Texture_T1`はユーザーの固定画像受領後にGate Cへ進め、テーマ専用1K
   BaseColor／Normal／MetallicSmoothnessと、筐体模様を混入させない暗色display materialを
   productionへ登録した。Active Prefab 56 / 56、EditMode 165 / 165をPASSし、
   Quest 48 / 64だけはユーザー指示により明示保留している。
   display plane寸法・正面方向・overlay fit・最大4入力・LineRenderer契約は共通化し、
   テーマ差によって表示面座標やruntime signal処理を分岐させない。
2. **完了（2026-08-27）: Orbital Analog／Forge Brass meterのカバー上の重複目盛を除去。**
   MeterGlassScale G1としてMedium／Largeの`secondary_scale_*`だけを削除し、文字盤側の
   主目盛、針、230°の可動範囲を維持した。固定画像、Prefab、Quest 3実機、48配置gate、
   64配置stressをPASSし、元FBX GUIDを維持してproductionへ昇格済み。
3. **production desktop完了（2026-09-01）／Quest受入延期: Window Panelを4テーマ共通で非メーター型graphic instrumentへ再設計する。**
   meter、針、vane、アナログ目盛を使わず、2Dの幾何学的なparametric図形を表示する。
   複数入力を受け付け、入力ごとに位置、回転、scale、色、位相、変形量など明示されたparameterへ
   割り当て、連続animationとして描画する。入力欠損・無効値・停止時の表示方針、parameter範囲、
   合成順序、保存schemaを定義する。図形はテーマ固有frame / textureの内側で共通座標系を使い、
   Quest向けにallocation、更新Hz、頂点数、material数へ上限を設ける。

   実装前契約は`docs/WINDOW_PANEL_GRAPHICS_CONTRACT.md`に固定した。最大4入力を平均せず
   Energy / Balance / Phase / Detailの4 slotへ割り当て、Orbit / Rose / Lissajousの3 presetを
   shared coordinateで描画する。WP1の隔離runtime prototype、WP2のschema v6／UI、WP3の
   4-theme model candidateの順にGateを分離する。

   WP1隔離runtime prototypeは2026-08-31にtechnical PASS。3 preset、4 slot、invalid表示、
   256 vertex／768 index固定budget、geometry 100回再生成0 B、EditMode 173 / 173を確認した。
   続くWP2でschema v6／Connect UI、WP3-r2でBlender 5.2由来の4テーマ固有frame、WP4で
   production runtime統合まで完了した。production固定画像は4テーマ×3 presetの12 / 12 PASS、
   candidate依存0、EditMode 187 / 187、候補defineなしの通常APK生成をPASSした。Quest上のvisual／
   interaction／48／64だけはユーザー指示により延期する。

Window Panelの再設計は単なる3D置換ではなく、複数入力compositionと新しい表示runtimeを伴う。
Priority 4の入力合成モデルと整合させ、外観制作をsignal / persistence契約より先行させない。

## Priority 4: multiple-input composition

現在の暗黙的な平均合成を明示設定へ置き換える。

**基盤完了（2026-09-01）:** 現行経路を監査し、`docs/MULTI_INPUT_COMPOSITION_CONTRACT.md`へ
Average／Sum／Minimum／Maximum／Priority、無効入力、Priority tie-break、schema移行、allocation制約を
固定した。第一段階としてallocation-free accumulatorを追加し、既存evaluatorをAverage互換のまま移行した。
この第一段階のUnity EditModeは196 / 196 PASSだった。

**schema/runtime完了（2026-09-01）:** schema v7へtarget単位の`signalCompositionKind`と
connection単位の`compositionPriority`（0〜3）を追加した。v6はAverage／priority 0へ移行し、既存Window Panel
slot、graphic preset、Range／Threshold parameterを維持する。runtimeは保存済みの5方式をtargetごとに評価する。
Unity EditModeは203 / 203 PASS。設定UIとTrend Monitor合成診断は次段階とする。

**desktop UI完了（2026-09-01）:** Connectモードで通常targetの合成方式を右stick上下から変更し、
即時保存・再評価できる。Priority targetのconnectionは右stick左右でrank 0〜3をpreviewし、左stick押下で
確定する。Window Panelのpreset／slot操作、Range／Threshold parameter編集を維持する。Unity EditModeは
206 / 206 PASS。Quest操作受入とTrend Monitor合成診断は保留する。

- Average / Sum / Min / Max / Priorityの最小構成
- 入力欠損、無効値、更新停止時の方針
- 順序依存性と保存schema
- monitorで各入力と合成結果を確認

接続parameterモデルとmonitorが安定した後に着手する。合成UIと信号評価を同時に設計し直す
ことを避ける。

## Priority 5: safety signal processing

Limiter、rate limit、manual reset、latched tripを候補とする。安全装置という名称だけで実機の
安全保証を示さず、アプリ内の信号制約機能として扱う。

- clamp / rate limiter
- latched threshold + explicit reset
- invalid / stale input時のfail-safe値
- reset権限と状態保存
- feedback loopと発振を防ぐ評価順序

複数入力合成と共通のgraph評価・診断基盤を使い、個別機能ごとの特殊経路を増やさない。

## Quest performance policy

- 48 objectsをrelease gate、64 objectsをstress characterizationとして維持
- monitor追加後は表示なし / 数値 / graphの同一配置比較を実施
- CPU frame time、GPU frame time、thermal、memory、dropped framesをbaseline-relativeで記録
- graph sample数と描画更新Hzを設定可能にし、長時間試験では固定値をreportへ残す
- 3D candidate昇格後も同じ48 / 64 matrixを再実行し、見た目と性能を別々に合格させる

## Tooling policy

新しい技術領域や検証基盤へ着手する前に、Blender標準機能、定番add-on、公式SDK、保守中の
OSS libraryを調査する。導入候補が有効な場合は、目的、license、更新状況、Quest / Unity /
Blender 5.2との互換性、既存project-specific validatorとの役割分担を提示し、ユーザー確認後に
導入する。

現在のOpus作業領域にある多数のdiagnostic scriptは、そのまま正式QAへ入れない。再利用する
場合は、実モデルで価値を示した最小機能、fixture、CLI、依存関係、実行時間を整理した小さな
toolへ切り出す。新しいvalidator研究を3Dモデル改善より優先しない。

## Proposed v0.3 exit criteria

- 独立Trend MonitorがQuest 3で最大4入力の数値・trendを表示し、操作sourceと
  読取専用meterの保存済み接続を観測できる
- Range / Threshold parameterをQuest内で編集・保存・復元できる
- 優先3D候補のうち少なくとも1 familyがGate Cと実機視覚受入を完了する
- EditMode、39 prefab、motion、signal visual、Quest 48 gateがPASSする
- Quest 64 stressの結果と、未解決の性能・視覚課題がrelease noteへ記録される

複数入力合成とsafety処理は基盤までをv0.3へ含められるが、exit criteriaを遅らせる場合は
後続pre-releaseへ分ける。
