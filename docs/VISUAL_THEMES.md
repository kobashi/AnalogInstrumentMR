# Visual theme concepts

Status: **5テーマのコンセプト正本**
Updated: **2026-09-25**

## 1. Purpose

本書は、配置する計器、操作部、表示装置、音響モジュールに共通する5テーマの
コンセプトと、制作時の判断基準を定義する。テーマ差は単なる色替えではなく、
シルエット、部品構成、材料、表示、発光、操作音を組み合わせて成立させる。

機種ごとのnode、pivot、port、display surface、signal surface、visual envelope、
操作範囲は共通contractを維持する。テーマを切り替えても機能、値、接続、配置姿勢は
変えない。詳細な造形規則は各style guide、Superfineの製造形状は
[Superfine handoff](OPUS5_SUPERFINE_HANDOFF.md)を参照する。

## 2. Concept map

| Theme / ID | 中核コンセプト | 第一印象 | 主な形状言語 | 材質・光 |
| --- | --- | --- | --- | --- |
| Orbital Analog / `orbital-analog` | 宇宙船内のアナログ・電子混成計器 | 密度が高いが読みやすい、使い込まれた標準装備 | 埋め込み円形計器、厚い円筒housing、多層bezel、柔らかい角丸frame | charcoal塗装金属、aged bronze、off-white insert、warm amber |
| Forge Brass / `forge-brass` | 使い込まれた機械室の保守可能な計器 | 重い、低い、機械的、長寿命 | 鋳物の量感、段付きrim、短い円筒、真鍮retainer、rivet、球grip | cast iron、aged brass/copper、抑制したwarm amber |
| Kinetic Safety / `kinetic-safety` | 高エネルギー設備の安全操作部 | 防護されている、緊張感がある、即読性が高い | 面取り角形shroud、太いguard、corner protection、保護された円形操作部 | matte graphite、限定したorange/yellow、強いvalue contrast |
| Machined Ergonomics / `machined-ergonomics` | 人間工学から組み立てられた量産精密機器 | 清潔、軽量、合理的、触り方が分かる | 2-piece housing、parting/shut line、軸受、gasket、非対称grip、合理的fastener | warm-grey樹脂、anodized metal、dark elastomer、soft cyan |
| Superfine / `superfine` | 実部品と組立順序が読める高密度な製造装置 | 精密、堅牢、奥行きが深い、現場投入可能 | folded-steel tray、mounting flange、returned edge、molded bezel、実hardware、corner bumper | dark steel/graphite、cool metal、cyan readout、限定したorange warning |

テーマの距離感は次のように捉える。

- **Orbital Analog**は全体の基準となるレトロフューチャーな計器体系。
- **Forge Brass**は時間と質量を感じる機械設備へ寄せる。
- **Kinetic Safety**は防護と警告を形状の主役にする。
- **Machined Ergonomics**は軽さ、量産性、手への適合を主役にする。
- **Superfine**はKinetic Safetyのlayoutを起点にしつつ、板金、締結、保持、シールの
  実在感を主役にした独立テーマである。Kinetic Safetyの単なる高polygon版ではない。

## 3. Theme definitions

### 3.1 Orbital Analog

宇宙船の隔壁に長期間組み込まれてきた、アナログ計器と初期電子表示の混成系を
想定する。情報量は多いが、暗い内部、明るい目盛り、暖色の焦点というdepth hierarchyで
読みやすさを保つ。円形moduleの反復を基本とし、音響モジュールでも柔らかい角丸frameと
密度のあるanalog-electronic panel rhythmを維持する。

- **形状:** recessed face、多層bezel、円筒housing、細いarcとtick、控えめなfastener。
- **表示:** dark displayにwarm ivory/amberを中心とした細線。原色accentは状態識別に限定する。
- **操作感:** 標準的で癖が少なく、機械感と電子感の中間。5テーマ比較の基準にする。
- **避ける:** 固有作品のpanel配置、艦船記号、ロゴ、特徴的なscreen graphicの複製。

詳細: [Orbital Analog style guide](ORBITAL_ANALOG_STYLE_GUIDE.md)

### 3.2 Forge Brass

高温、油、振動のある機械室で保守され続ける計器を想定する。装飾的な
「スチームパンク」ではなく、暗い鋳物の母材を真鍮や銅の保持部品が支える、重く
修理可能な構造としてまとめる。視覚的な重心は低く、発光より材料とself-shadowで読む。

- **形状:** cast mass、厚い段付きrim、短い円筒、retaining frame、rivet、knurl、球grip。
- **表示:** warm amber。透明glassへの依存を避け、発光はruntime displayと状態表示へ集中させる。
- **操作感:** 大きめの質量と明確なdetentを感じる、低く重い機械音。
- **避ける:** 真鍮色を塗っただけのOrbital Analog、過剰な配管や装飾歯車、読取りを妨げる汚れ。

詳細: [Forge Brass style guide](FORGE_BRASS_STYLE_GUIDE.md)

### 3.3 Kinetic Safety

高エネルギー設備を誤操作から守り、危険状態を即座に伝える操作部を想定する。
警告色そのものではなく、操作部を囲うguard、角形shroud、強い支持材によって安全機器と
認識できることを優先する。orange/yellowは小面積の機能accentに留める。

- **形状:** chamfered rectangular shroud、太いside/corner guard、保護された円形操作部。
- **表示:** graphite上の高contrast表示。警告色と発光は状態・操作方向に集中させる。
- **操作感:** 応答が速く、警告装置らしい硬く明瞭なclick。曖昧な遷移を作らない。
- **避ける:** safety stripeだけによる差別化、Forge Brassと同じ円形silhouette、過剰な発光。

詳細: [Kinetic Safety style guide](KINETIC_SAFETY_STYLE_GUIDE.md)

### 3.4 Machined Ergonomics

工業デザイナーが人の手、視線、組立工程、量産方法から設計した、実在しそうな精密機器を
想定する。装飾線ではなく、housing分割、軸受、seal、fastener、clearanceに理由を持たせる。
既存の暗い3テーマと異なり、明るい成形樹脂の面積を大きくしてgrayscaleでも識別する。

- **形状:** 2-piece molded housing、一定幅のshut line、座ぐり、gasket溝、軸受、非対称grip。
- **表示:** neutral whiteからsoft cyan。表示面は必要に応じて視線側へわずかに傾ける。
- **操作感:** 軽く精密で、減衰の効いた節度感。触覚だけでも操作方向を理解できる形を優先する。
- **避ける:** 理由のない装飾ねじ、塊から削り出しただけの外形、暗色テーマの単純な白色化。

詳細: [Machined Ergonomics style guide](MACHINED_ERGONOMICS_STYLE_GUIDE.md)

### 3.5 Superfine

Kinetic Safetyで確立した機能layoutを保ちながら、外装、保持、締結、シール、取付の各部品が
実際に組み立てられる製品として読めるところまで造形を細分化する。前面だけを装飾するのではなく、
深いtrayとreturned edgeによって側面・取付面を含む構造を成立させる。

- **形状:** folded-steel tray、mounting flange、returned-edge panel、gasket reveal、molded
  window bezel、jack保持hardware、pot nut上のskirted knob、button-head screw、corner bumper。
- **表示:** dark steelとcool metalを背景にcyanを主表示、orangeを警告へ限定する。表示面と
  signal surfaceは実行時描画のため独立した平面・material roleとして維持する。
- **操作感:** 小さな機構まで解像する、短く高域寄りの精密なclick。堅牢さは残しつつ鈍重にしない。
- **避ける:** Kinetic Safety assetの上書き、既存形状へのdetail貼り足し、色だけの差、
  意味のない高密度化、共通interaction contractをvisualに合わせて変更すること。

詳細: [Superfine handoff](OPUS5_SUPERFINE_HANDOFF.md)

## 4. Interaction-sound identity

テーマ別の操作音は、同じ操作cueと機種別profileを保ったまま、基準周波数で質感を分ける。
これはswitch、lever、slider、rotary、button、lamp、indicator等の短い操作SEの識別であり、
OscillatorやNoiseなど音響モジュールの信号出力音色をテーマで変更する規則ではない。

| Theme | 現行基準周波数 | 音の狙い |
| --- | ---: | --- |
| Forge Brass | 470 Hz | 低く重い金属機構 |
| Machined Ergonomics | 690 Hz | 減衰の効いた精密機構 |
| Orbital Analog | 790 Hz | 機械と電子の中間にある標準音 |
| Kinetic Safety | 930 Hz | 硬く明瞭な安全装置の応答 |
| Superfine | 1180 Hz | 短く高精細な小機構の応答 |

ON/OFF、操作方向、detent、lamp段階、indicator状態はcueごとのpitchとtimbreで追加識別する。
テーマ差だけで状態を表現せず、同一テーマ内でもOFF / SAFE / WARN / DANGERや
LOW / MID / HIGHを聞き分けられる状態を維持する。実装契約は
[Instrument audio contract](INSTRUMENT_AUDIO_CONTRACT.md)を参照する。

## 5. Cross-theme review rules

新規model、refine、表示変更は次の順に判定する。

1. **Silhouette:** grayscaleの正面・斜視でテーマを識別できるか。
2. **Construction:** housing、retainer、guard、fastener、sealがテーマの部品構成に従うか。
3. **Readability:** 0.6〜1.0 mのQuest視距離で機能、状態、操作方向が読めるか。
4. **Motion:** 可動部の形状がpivot、clearance、操作範囲を視覚的に説明するか。
5. **Runtime surface:** display / signal surfaceが実行時表示を妨げず、theme materialと両立するか。
6. **Sound:** theme、機種、方向、状態段階を過度な音量差に頼らず識別できるか。
7. **Contract:** theme変更だけを理由にnode名、port位置の意味、interaction、保存schemaを変えていないか。

色を外した時にテーマ差が消える場合は未完成とする。反対に、形状差のために共通機能contractが
崩れる場合も不合格とする。

## 6. Origin and naming history

初期開発時の方向性ラベルは次のとおり。現在の正式名は上記5テーマを使う。

| Working label | Original design direction |
| --- | --- |
| Steampunk | 真鍮、銅、鋳鉄、リベット、配管、アナログ圧力計、蒸気や機械振動 |
| Retro Space Opera | 黒い計器盤、円形メーター、密集した目盛り、原色ランプ、手描き感のある宇宙船操作卓 |
| Kinetic Mecha Lab | 大胆な警告色、工業的パネル分割、過剰なスケール感、鋭いシルエット、勢いのある作動演出 |

`Retro Space Opera` と `Kinetic Mecha Lab` は、一般的なレトロ宇宙オペラと
工業的メカ表現を、固有作品に依存しない独自のアートディレクションへ整理した
内部テーマ名とする。特定作品の固有形状、ロゴ、キャラクター、配色配置、
特徴的な意匠を複製しない。

## 7. Architecture

操作機能と表示を分離する。

- `InstrumentController`: 値、状態、イベント、保存対象データを管理する。
- `ControlInteraction`: レバー角度、スイッチ状態、押下、掴み判定を管理する。
- `ThemeDefinition`: テーマ ID、共通 material、audio、VFX、animation profile を保持する ScriptableObject。
- `InstrumentVisualSet`: `instrumentTypeId` ごとのテーマ別 prefab を解決する。
- `ThemeService`: 現在テーマの選択、保存、runtime 切り替え、fallback を管理する。

物理 collider、interaction anchor、可動範囲、イベント名はテーマ間で共通の contract を使う。テーマ prefab は同じ attachment point 名と可動部 ID を実装する。

## 8. Switching behavior

- 初期版は承認済み方針として、部屋全体の global theme を切り替える。
- 計器単位の override は初期リリースに含めないが、将来追加できるデータ構造にする。
- 切り替え時も Spatial Anchor、計器値、レバー位置、スイッチ状態を保持する。
- 短い transition を使用し、操作中のオブジェクトは即時交換せず操作終了後に切り替える。
- テーマアセットのロード失敗時は default theme を表示し、操作機能は維持する。

## 9. Historical mock scope

初期3テーマのMockでは各テーマにつき、次の最小セットを灰色モデルと簡易materialで用意した。

1. 円形メーター
2. 縦型レバー
3. トグルスイッチ
4. ロータリーノブ
5. 押しボタン
6. 状態ランプ

本制作前に、同一のcontrollerとcollider contractで6種類×3テーマを生成できることを検証する。実寸とテーマ別の造形案は [Instrument greybox specification](GREYBOX_INSTRUMENT_SPEC.md) を参照する。

オブジェクトの全カタログ、prefab contract、制作ゲートは [Object catalog and preparation plan](OBJECT_CATALOG.md) に定義する。

### 2026-07-20 production status

- 3テーマ×6種類のBlender原本、FBX、preview、1K PBR maps、Unity prefabを制作済み。
- Forge Brass / Kinetic Safetyを含む全18 prefabで共通root/socket、pivot、
  envelope、collider分離をUnity EditMode testで確認済み（29 / 29 PASS）。
- Orbital AnalogはQuest 3で6種類の配置・復元と10分安定性を確認済み。
- Quest 3S実機検証はプロジェクト判断で見送る。
- global theme切り替えを左スティック左右へ実装済み。theme IDは独立した
  PlayerPrefs設定へ保存し、既存のanchor UUID／type ID schemaは変更しない。
- 配置済みオブジェクトはSpatial Anchor rootを維持したまま`VisualSocket`だけを
  交換する。Unity EditModeでroot pose、socket、Collider、kind不変性を確認済み。
- `concept.2`はQuest 3で3テーマ切り替え、配置済みvisual交換、Activity再起動後の
  Forge Brass／Spatial Anchor同時復元を確認済み。詳細は
  [Quest 3 theme switch and restore test](QUEST_THEME_SWITCH_TEST.md)を参照する。

### 2026-07-30 V6 production status

- 丸形メーター小・中・大を含む13種類×3テーマ、計39個のV6 Visual Prefabを導入済み。
- 全39 prefabで共通root/socket、可動target、0 Collider、0 realtime Light、
  種類別triangle上限、取付面クリアランスを検証済み。
- テーマ切り替えは左スティック左右へ割り当て、Spatial Anchor、配置姿勢、
  normalized value、接続を維持したまま`VisualSocket`だけを交換する。
- 最終Blender原本は
  `ArtSource/Blender/ThemeHardSurfaceV6/*/*_ProductionReady.blend`を正とする。

## 10. Quest asset budget

- 1 テーマあたりの texture atlas と material 数に上限を設ける。
- material instance の乱立を避け、色や発光は property block または共通 parameter で制御する。
- 可動アニメーションは可能な限り軽量な transform animation とし、常時計算する Animator を増やしすぎない。
- LOD、mesh complexity、透明・発光・パーティクルの上限をテーマ間で揃える。
- 5テーマを無条件に常駐させず、必要に応じてAddressables等による遅延ロードを検討する。

## 11. Acceptance criteria

- production catalogの24種類が5テーマすべてで表示できる。
- runtime 切り替え後も配置位置と操作状態が変わらない。
- theme prefab が欠落しても default theme へ復帰し、操作不能にならない。
- テーマごとの collider と操作感が同等である。
- 各テーマを色だけでなくsilhouetteと部品構成から識別できる。
- 操作SEはテーマ差、機種差、方向・状態差を維持する。
- Quest 3 / 3S 上でテーマ切り替えによる長いフリーズや継続的な GC spike が発生しない。

## 12. Current production status

### 2026-09-22 Superfine production status

- Kinetic Safetyを製造形状の基準にした独立テーマ`Superfine`を、第5テーマとして本番登録した。
- theme enumは既存値0..3を保持して`Superfine = 4`、theme IDは`superfine`、表示名は`SUPERFINE`。
- audio 10機種とnon-audio 14機種、計24種類のFBX / prefabをfresh GUIDで登録した。
- production prefabからcandidate stagingへの依存は0件。既存4テーマのassetとGUIDは変更していない。
- theme切り替え、保存・復元、display / signal色、theme別操作音を5テーマ対応にした。
- Unity EditModeは413 / 413 PASS。Superfine専用active prefab、motion、signal visual auditもPASS。
- 2026-09-25に更新APKのQuest実機操作をユーザーが確認し、human acceptanceはPASS。
- Quest負荷試験は後回しであり未判定。24-object renderer 116、triangle / material / TrendMonitor幅の
  既知差分はREVIEWのままで、共通budgetは変更していない。
- 詳細は[Superfine handoff](OPUS5_SUPERFINE_HANDOFF.md)、rollbackは
  [Superfine production rollback](SUPERFINE_PRODUCTION_ROLLBACK.md)を参照する。
