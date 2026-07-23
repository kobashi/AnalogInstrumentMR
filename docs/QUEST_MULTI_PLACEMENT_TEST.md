# concept.4 Quest 3 multiple placement and migration test

## Build under test

- Date: 2026-07-21
- Device: Meta Quest 3
- APK: `Builds/Release/MatsuMotoMeterAR-v0.1.0-concept.4-quest3.apk`
- SHA-256:
  `58e8ab5a20145d1d4b50b959bfc78ffa18119a1af2bb73cb40c711025ee00a44`
- Size: 66,928,961 bytes
- Unity EditMode: 48 passed、0 failed
- Quest 3S: プロジェクト判断で見送り

## Migration checks

concept.3で保存した状態灯、Forge Brass theme、論理値を残した状態から
`adb install -r`で上書きする。アプリは旧3キーをschema v1 JSONへ移すが、既存Anchorを
再作成・保存・削除しない。

| Check | Expected | Result |
| --- | --- | --- |
| Install / launch | 保存データを維持して起動 | PASS |
| Legacy migration | logにschema 1、revision 1、1 record | PASS |
| Existing anchor | 同じ実空間位置・向き | PASS |
| Existing visual/state | 同じ種類、theme、論理値 | PASS |
| Fatal errors | Unity / Android / Anchor fatal error 0 | PASS (0) |

## Multiple placement checks

1. 既存状態灯を残し、円形メーター、レバー、トグルを別々の壁位置へ追加する。
2. HUDの件数が`04/24`となることを確認する。
3. 各部品をrayとdirectで操作し、最も近い対象だけが変化することを確認する。
4. トグルを狙って右スティック押し込みし、トグルだけ削除され`03/24`となることを確認する。
5. themeを切り替え、残る3件のroot poseと個別論理値が維持されることを確認する。
6. 終了パネルから終了し、ADBで再起動する。
7. 3件が同じ位置、種類、theme、個別論理値で復元されることを確認する。

| Check | Result |
| --- | --- |
| Add without replacing prior placement | PASS |
| Count HUD | PASS |
| Nearest ray target | PASS |
| Direct global priority | PASS |
| Aimed delete only | PASS (`recordRemoved=True, saved=True`) |
| Theme swap for all roots | PASS |
| Three-anchor restart restore | PASS (`3/3 active`) |

操作中にトグルを選んだつもりの入力がレバーのままで、2個目のレバーが追加された。
診断ログでtype IDを確認し、不要レバーを照準削除した。最終保存は状態灯、円形メーター、
レバーの3 recordで、再起動後に`3/3 active`、unavailable 0、pending-delete 0を確認した。

## Runtime snapshot

3 Anchor再起動復元後の単点計測。

| Item | Result |
| --- | --- |
| PSS / RSS | 465,768 KB / 626,082 KB |
| App swap | 48 KB |
| VSYNC period | 13,888,888 ns (72 Hz) |
| Battery | 85%、USB powered / discharging |
| Temperature | 45.0°C |
| Fatal errors | 0 |

## 24-object performance gate

- 12 / 24 / 40 objectsで余裕度を測る。24が合否、40はstress report。
- 24個、72 Hz、10分でapp GPU p95 11 ms以下、72 Hz維持、CPU飽和・hitchなしを
  外部合格条件とする。OVR Metrics CSVはapp CPU timeを出さないため、CPUはutilizationと
  delivered frameで判定し、in-app CPU p95は診断値として残す。
- contentは120k triangles、96 renderer submissions、24 interaction colliders、
  realtime light 0以下。
- steady-state managed allocation 0 B/frame、fatal error 0、thermal stop 48°C。

EditMode aggregate content guardは3テーマそれぞれの6種類混在24個について、
120k triangles以下、96 renderer以下、interaction collider 24、realtime light 0をPASSした。

legacy移行、複数配置の実機回帰、24個10分72 Hz synthetic性能gateを完了した。

### Synthetic rendering gate

`concept.5-perfgate` APKは、保存済みplacementとSpatial Anchorを変更せずに、
ADBのIntent extraで6種類混在の12 / 24 / 40個を表示できる。性能モードでは
通常の配置controllerと開発用exit HUDを起動しない。

```bash
ADB="/Applications/Unity/Hub/Editor/6000.3.19f1/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb"
PACKAGE="com.DefaultCompany.MatsuMotoMeterAR"
ACTIVITY="com.unity3d.player.UnityPlayerGameActivity"
"$ADB" shell am force-stop "$PACKAGE"
"$ADB" shell am start -S -n "$PACKAGE/$ACTIVITY" \
  --ei matsu_perf_count 24 \
  --ei matsu_perf_duration 600 \
  --es matsu_perf_theme OrbitalAnalog
```

`matsu_perf_count`は12、24、40だけを受理する。themeは`OrbitalAnalog`、
`ForgeBrass`、`KineticSafety`を指定できる。`matsu_perf_duration`は60秒smokeまたは
600秒full gateを受理する。15秒warmup後に指定時間を計測し、
計測開始時と`[PerfGate] FINAL`をlogcatへ出す。測定中は診断HUDを非表示にして
計測器自身のsteady-state allocationを避ける。アプリ内の
`FrameTimingManager`値は診断用とする。最終判定は同じ区間のOVR Metrics Toolまたは
MQDH Performance Analyzerからapp GPU time、CPU utilization、delivered frameを採用する。
direct app CPU timeを取得できるtoolを使う場合だけCPU time p95も併記する。

起動時に72 Hzを要求し、実値が72 Hzでなければ測定を開始しない。
これはstatic rendering / contentとinteraction collider存在時の性能gateであり、
通常のMRUK raycast、interaction resolver、24個の実Spatial Anchor localization /
restore負荷を代替しない。厳密な24実配置gateは任意の拡張試験とし、最終実機判定は
通常runtimeのユーザー受入試験で問題がなければPASSとする。

APK install、起動、30秒ごとのbattery / thermal / memory採取、48°C thermal stop、
最終PerfGate / fatal log採取は次で自動化できる。

```bash
./scripts/run-quest-performance-gate.sh 24 OrbitalAnalog
```

結果はgitignoredの`Builds/Reports/perfgate-*.log`へ保存する。OVR Metrics Toolまたは
MQDHの記録は同時に開始し、app GPU p95、CPU utilization、frame deliveryを転記する。
同じAPKで繰り返し測定する場合は`INSTALL_APK=0`で再インストールを省略できる。
スクリプトは起動PIDを最大30秒待ち、10秒時点で起動を一度再試行する。

### Quest 3 synthetic 24 result (2026-07-22)

OrbitalAnalog、24個、72 Hzで15秒warmup後に600秒を完走した。

| Metric | Result | Verdict |
| --- | ---: | --- |
| Samples | 43,200（600秒 × 72 Hz） | PASS |
| Delayed frames | 0.021% | PASS（1%未満） |
| GC collections | 0 | PASS |
| Max GC allocated in frame | 0 B | PASS |
| Fatal errors | 0 | PASS |
| Temperature | 44–46°C | PASS（48°C未満） |
| PSS | 441,604 → 447,945 KB（+1.44%） | PASS（10%未満） |
| RSS | 601,374 → 609,962 KB（+1.43%） | PASS（10%未満） |
| Swap PSS | 48 KB fixed | PASS |
| In-app CPU p95 | 14.234 ms | REVIEW |
| In-app GPU p95 | unavailable（0 ms） | REVIEW |

`FrameTimingManager`のCPU値は72 Hz waitを含む可能性があり、GPU値はQuest OpenXRで
取得できなかった。このためstability / thermal / memory / GC gateはPASS、最終CPU/GPU
p95 verdictはOVR Metrics ToolまたはMQDHでの再計測までPENDINGとする。

Host report:
`Builds/Reports/perfgate-24-OrbitalAnalog-20260722-191938.log`

### Quest 3 OVR Metrics synthetic 24 result (2026-07-23)

公式OVR Metrics Tool 86.0.0.0.0のAdvanced + GPU CSVを同時記録し、
OrbitalAnalog 24個、15秒warmup後の600秒（CSV timestamp 15,001–614,043 ms、
600 row）を集計した。

| Metric | Result | Verdict |
| --- | ---: | --- |
| Average frame rate | min 71 / mean 72.637 / p95 73 fps | PASS |
| App GPU time | mean 2.260 / p95 2.310 / max 2.402 ms | PASS（11 ms未満） |
| GPU utilization | mean 32.25% / p95 33% | PASS |
| CPU utilization | mean 18.99% / p95 34% / max 53% | PASS（飽和なし） |
| Stale / skipped / early frame | 1 / 0 / 0 | PASS |
| Shader hitches | 0 | PASS |
| Screen tear count | 29 | OBSERVE |
| App PSS | 418–434 MB、区間差+16 MB | PASS |
| Temperature | 45–47°C | PASS（48°C未満） |
| In-app delayed frames | 0.019% | PASS（1%未満） |
| GC collections / fatal errors | 0 / 0 | PASS |

72 Hzの描画、GPU、CPU utilization、stability、thermal、memory gateはPASS。
OVR CSVにapp CPU time列がないため、当初のCPU p95 11 ms値との直接比較は行わない。
`FrameTimingManager`のin-app CPU p95 14.264 msはvsync waitを含み得る診断値として
`REVIEW`のまま残す。screen tear 29回は次の実Anchor通常runtime試験で再確認する。

Host report:
`Builds/Reports/perfgate-24-OrbitalAnalog-20260723-103336.log`

OVR CSV:
`Builds/Reports/ovrmetrics-24-OrbitalAnalog-20260723-103349.csv`

### Quest 3 OVR Metrics synthetic 40 stress result (2026-07-23)

OrbitalAnalog 40個、15秒warmup後の600秒（CSV timestamp 15,001–614,044 ms、
600 row）をstress reportとして集計した。

| Metric | Result | Assessment |
| --- | ---: | --- |
| Average frame rate | min 72 / mean 72.665 / p95 73 fps | stable |
| App GPU time | mean 2.265 / p95 2.314 / max 2.373 ms | 24個比+0.004 ms p95 |
| GPU utilization | mean 32.20% / p95 33% | stable |
| CPU utilization | mean 18.65% / p95 33% / max 50% | no saturation |
| Stale / skipped / early frame | 0 / 0 / 0 | stable |
| Shader hitches | 0 | stable |
| Screen tear count | 45 | OBSERVE |
| App PSS | 422–439 MB、区間差+17 MB | stable |
| Temperature | 45–47°C | below stop limit |
| In-app delayed frames | 0.016% | stable |
| GC collections / fatal errors | 0 / 0 | stable |

保証点24個から40個へ増やしてもGPU p95、CPU utilization、72 Hz deliveryに
有意な悪化はなかった。`MockInstrumentMotion`はevent-drivenでper-object `Update`を
持たないため、共有schedulerへの移行は不要と判断する。screen tear countは24個の29回から45回へ
増えたため、通常runtime試験で継続観察する。

Host report:
`Builds/Reports/perfgate-40-OrbitalAnalog-20260723-123005.log`

OVR CSV:
`Builds/Reports/ovrmetrics-40-OrbitalAnalog-20260723-123016.csv`

### Quest 3 normal runtime screen-tear baseline (2026-07-23)

性能モードを使わず、保存済み3 recordを`3/3 active`で復元した通常runtimeを
60秒（CSV timestamp 5,000–64,010 ms、60 row）計測した。

| Metric | Result |
| --- | ---: |
| Average frame rate | min 72 / mean 72.583 / p95 73 fps |
| App GPU time | mean 2.483 / p95 2.539 / max 2.571 ms |
| CPU utilization | mean 21.12% / p95 36% / max 41% |
| GPU utilization | 34% fixed |
| Stale / skipped / early frame | 0 / 0 / 0 |
| Shader hitches | 0 |
| Screen tear count | 5 |
| Temperature | 45–46°C |

screen tearは通常runtimeでも5回/60秒（0.083回/秒）を記録した。24個syntheticは
29回/600秒（0.048回/秒）、40個syntheticは45回/600秒（0.075回/秒）であり、
40個化に固有の性能退行とは判断しない。OVR Metrics上の観察値として残し、
通常runtimeで頭を左右へ動かしながらメーター、レバー、状態灯を約60秒目視した結果、
横方向の裂け、瞬間的な段差、ずれは確認されなかった（`tearなし`）。CSV counterは
ユーザー可視の表示破綻を再現しなかったため、blocking issueとは扱わない。

OVR CSV:
`Builds/Reports/ovrmetrics-normal-runtime-3anchors-20260723-124357.csv`

### Quest 3 three-theme performance smoke (2026-07-23)

24個のForgeBrassとKineticSafetyを15秒warmup後に各60秒計測し、
OrbitalAnalogの600秒保証点結果と比較した。

| Theme | Duration | Mean fps | App GPU p95 | CPU util. p95 | Stale / skipped / hitch | Max temp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OrbitalAnalog | 600 s | 72.637 | 2.310 ms | 34% | 1 / 0 / 0 | 47°C |
| ForgeBrass | 60 s | 72.717 | 2.317 ms | 35% | 0 / 0 / 0 | 47°C |
| KineticSafety | 60 s | 72.650 | 2.302 ms | 39% | 0 / 0 / 0 | 46°C |

3テーマすべて72 Hzを維持し、app GPU p95は2.302–2.317 msだった。
shared material、1K texture、emissive差による有意な性能差は見られない。
両smokeとも4,321 in-app sample、delayed 0.046%、GC 0、fatal 0だった。

ForgeBrass reports:
`Builds/Reports/perfgate-24-ForgeBrass-20260723-130037.log`,
`Builds/Reports/ovrmetrics-24-ForgeBrass-20260723-130042.csv`

KineticSafety reports:
`Builds/Reports/perfgate-24-KineticSafety-20260723-130342.log`,
`Builds/Reports/ovrmetrics-24-KineticSafety-20260723-130347.csv`
