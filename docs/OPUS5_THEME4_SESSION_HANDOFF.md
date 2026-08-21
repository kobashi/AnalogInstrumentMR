# Claude Opus 5: Theme 4 session handoff

この1件で新しいセッションが着手できることを目的とする。並行セッションは
本書と`docs/OPUS5_THEME4_LOG.md`だけを起点にし、他セッションの未push成果へ
依存しない。

## 1. Objective

既存3テーマへ4つめのビジュアルテーマを追加する。方向性は次のとおり
（2026-08-21 承認）。

```text
工業デザイナーがパーツ構成や製造工程を意識した実在しそうなつなぎ目や
はめ込みを作り込み、かつ人間工学や使いやすさをイメージさせるデザインとする
```

作り込みの対象は装飾ではなく、分割面、シャットライン、抜き勾配、締結、
軸受、シール、グリップ断面といった製造上の必然と、手と目に対する配慮とする。

## 2. Theme identity

| Item | Value |
| --- | --- |
| Working label | Machined Ergonomics |
| Original design direction | 量産工業機器。分割面、はめ合い、締結、抜き勾配、人間工学グリップ |
| Theme ID | `machined-ergonomics` |
| Asset token | `MachinedErgonomics` |
| Display name | `MACHINED ERGONOMICS` |
| Style guide | `docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md` |

命名は本セッションの提案であり、Phase 2完了までは変更可能とする。Phase 3で
asset名、theme ID、PlayerPrefs値へ焼き込まれるため、名称変更はPhase 2までに
確定させる。

既存3テーマとの識別は、明るい成形樹脂の母材とアルマイト金属という value
差で行う。既存3テーマはいずれも暗い母材のため、grayscale silhouetteでも
区別できる見込みだが、これはPhase 1のcontact sheetで実測確認する。

## 3. Scope

並行して進めるのは Phase 0〜2 までとする。量産とUnity取り込みは先行させない。

| Phase | 内容 | 本系統での扱い |
| --- | --- | --- |
| Phase 0 | 方向性確定、style guide、識別性方針、命名 | 実施可 |
| Phase 1 | 代表3種のgreybox / proportion candidate | 実施可 |
| Phase 2 | 代表3種のRetopo candidate、視覚レビュー資料、JSON report | 実施可。ここで停止 |
| Phase 3 | 13種への量産展開、atlas、triangulate、FBX | 着手しない |
| Phase 4 | Unity prefab、theme catalog拡張、EditMode、Quest gate | 着手しない |

Phase 3以降は別承認とし、`docs/GATE_C_INTEGRATION.md`のacceptance orderへ従う。

Phase 4が触る既存実装（着手しないが、Phase 2の設計判断で影響を見積もる）:

- `Assets/MatsuMotoMeterAR/Runtime/Instruments/MockInstrumentThemeCatalog.cs`
  の`Count = 3`、`GetThemeId`、`GetDisplayName`、`FromThemeId`、`GetPalette`
- `MockInstrumentTheme` enumの追加順とPlayerPrefsの既存値互換
- 左スティック左右のtheme cycleが3→4段になること
- active visual prefabが39→52個になること
- Quest 48 / 64 matrixとtexture常駐量への影響

## 4. Repository baseline

- Repository: `kobashi/AnalogInstrumentMR`
- Branch: `claude/opus5-theme4-handoff-i14wfz`
- Base: `origin/main` `c0cfd5b`
- Unity: `6000.3.19f1`
- Supported Blender: `5.2.x`（`scripts/run-blender.sh`経由でのみ起動する）
- Target device: Meta Quest 3

現行のV6 production asset、Unity prefab、texture atlasを正として扱う。
V4 / V5 / pre-V6 candidateを新テーマの契約根拠にしない。

## 5. Environment note

2026-08-21時点のClaude Code remoteコンテナにはBlenderが導入されておらず、
`scripts/run-blender.sh --print-bin`は`Blender was not found`を返す。

- Phase 0はこの環境で完了できる。
- Phase 1〜2はBlender 5.2.xを実行できる環境が必要である。実行できない
  セッションは、生成スクリプトと検証手順の記述までを行い、生成物を
  作成済みと記録しない。

## 6. Authoritative references

着手前に次を読む。

- `docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md`
- `docs/VISUAL_THEMES.md`
- `docs/GREYBOX_INSTRUMENT_SPEC.md`
- `docs/OBJECT_CATALOG.md`
- `docs/3D_MODEL_QUALITY_FLOOR_V4.md`
- `docs/OPUS5_3D_MODEL_BRUSHUP_HANDOFF.md`（作業手順とレビュー資料の書式）
- `docs/GATE_C_INTEGRATION.md`
- `docs/MODEL_REPLACEMENT_WORKFLOW.md`
- `ArtSource/Blender/README.md`
- 既存3テーマのstyle guide（silhouette差の判断基準として）

## 7. Non-negotiable contract

新テーマでも次を変更しない。

- 1 Unity unit = 1 m、root scaleは常に`(1, 1, 1)`
- mount面はUnity local `Z = 0`、local `+Z`が面から外向き
- Blender X → Unity X、Blender Z → Unity Y、Blender `-Y` outward → Unity `+Z`
- FBX export: `-Z Forward / Y Up`
- `GREYBOX_INSTRUMENT_SPEC.md`のtype IDごとのvisual envelope
- 可動ノード名と可動域
  - `needle_pivot/needle`、`handle_pivot/handle`、`switch_pivot/switch`、
    `knob_pivot/knob`、`button_travel/button`、`indicator`、
    `throttle_pivot/throttle_handle`、`slider_travel/slider_handle`、
    `vane_pivot/vane`
- root命名 `PF_Visual_<Object>_MachinedErgonomics_V6`
- material role `body` / `metal` / `gasket` / `readout`
- Visual hierarchyへCollider、Animator、Camera、realtime Light、
  runtime scriptを追加しない

人間工学のための表示面の傾きは、envelopeのZ上限内で行う。envelopeを広げる
必要が出た場合は作業を止め、影響範囲と比較画像を提示して承認を得る。

## 8. Primary risk

このテーマ固有の最大risk は、つなぎ目の作り込みがtriangle予算を超えることである。

- シャットラインを全周geometryで作ると、小型計器で5,000 trianglesを超える。
- 主分割面と可動clearanceをgeometry、副次的な目地と刻印をnormal mapへ回す
  配分をPhase 1で決め、Phase 2で実測する。
- 明るい母材はbevel highlightのコントラストが下がるため、暗い3テーマと
  同じbevel幅では近接時に段差が読めない可能性がある。固定camera画像で
  判定し、数値だけで合格としない。

## 9. Phase 0 deliverables

- `docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md`
- 本handoff
- `docs/OPUS5_THEME4_LOG.md`
- `docs/VISUAL_THEMES.md`への検討開始の記録

完了条件: 次のセッションが本書だけで Phase 1 へ着手でき、テーマ名、ID、
palette方針、geometry / texture配分方針、禁止事項が確定していること。

## 10. Phase 1 deliverables

代表3種を`meter.round`、`control.lever`、`control.toggle`とする。分割面、
軸受、グリップ、形状コーディングという本テーマの論点をこの3種で網羅できる。

作業領域（既存assetを上書きしない）:

```text
ArtSource/Blender/Theme4/MachinedErgonomics/
├── BL_MeterRound_MachinedErgonomics_P1_Greybox.blend
├── BL_Lever_MachinedErgonomics_P1_Greybox.blend
├── BL_Toggle_MachinedErgonomics_P1_Greybox.blend
├── Preview_*_P1_*.png
└── reports/
```

再現用Pythonは`Tools/Blender/generate_theme4_machined_ergonomics.py`へ置き、
input / output pathを引数で受け取り、production sourceを上書きせず、
例外時にnon-zeroで終了する。外部add-onとnetwork依存を追加しない。

完了条件:

- 3種のenvelope、pivot、可動域が既存3テーマと一致する
- 1,500 triangles以下、renderer 3以下（meterのみ4）、shared material 2以下
- non-manifold edge 0、zero-area face 0
- 既存3テーマとの4テーマ横並びgrayscale contact sheetで識別できる

## 11. Phase 2 deliverables

Phase 1承認後に、同じ3種をquad主体のRetopo candidateへ引き上げる。

- `*_P2_Retopo.blend`
- 固定camera / 固定lightのPNG: grayscale 3/4、反対3/4、side profile、
  topology、PBR emissive OFF / ON、neutral / min / max可動、pivot近接
- `reports/<Object>_MachinedErgonomics_P2.json`
  （`OPUS5_3D_MODEL_BRUSHUP_HANDOFF.md`第13節のkeyへ合わせ、計測値のみ記録）
- `Tools/Blender/smoke_test_blender_52.py`によるcandidate smoke test結果
- 変更点、未解決点、推奨する次revision

Phase 2はレビュー資料の提出をもって停止する。承認なしにPhase 3へ進まない。

## 12. Prohibited actions

明示的な承認なしに次を行わない。

- 13種類への量産展開、および4テーマ目のUnity取り込み
- `*_ProductionReady.blend`、active Unity FBX / Prefab / Material / `.meta`の変更
- `MockInstrumentThemeCatalog`の`Count`、enum、theme ID、palette変更
- 既存3テーマのasset、style guide、texture atlas layoutの変更
- root、pivot、motion targetのrename
- interaction colliderまたはruntime logicの変更
- Blender versionの変更、add-on / dependency / network assetの追加
- 視覚受け入れ前にPhaseを完了扱いにすること
- 計測していない数値をreportまたはlogへ記録すること

## 13. Work log rules

作業記録は`docs/OPUS5_THEME4_LOG.md`へ追記する。並行セッションは自分の
連番`T1.` `T2.` …で書き、他セッションの番号を再利用しない。書式と衝突回避は
同ファイル冒頭の規約に従う。

## 14. Initial instruction to the next session

```text
AnalogInstrumentMRへ4つめのビジュアルテーマ Machined Ergonomics を追加する。

最初に docs/OPUS5_THEME4_SESSION_HANDOFF.md と
docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md を読み、そこから参照される
runtime契約、greybox spec、quality floorを確認すること。

今回の範囲は Phase 1 とし、meter.round / control.lever / control.toggle の
greybox candidateだけを作る。ArtSource/Blender/Theme4/MachinedErgonomics/ へ
出力し、既存3テーマのasset、ProductionReady、Unity FBX、Prefab、Material、
.meta、MockInstrumentThemeCatalog を変更しないこと。

Blenderは scripts/run-blender.sh 経由で 5.2.x を使う。envelope、pivot、
可動域、root命名、material roleを維持する。envelope変更が必要なら作業を止め、
理由と比較資料を提示すること。

つなぎ目は主分割面だけをgeometryで作り、副次的な目地と刻印はnormal mapへ
残す。triangle予算超過が見えた時点で配分を報告すること。

3種のgreyboxと4テーマ横並びgrayscale contact sheetが揃った時点で停止し、
Phase 2以降へ進まないこと。作業記録は docs/OPUS5_THEME4_LOG.md へ
自分の連番で追記する。
```
