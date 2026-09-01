# Quest 48 / 64 object long-run performance

48 objectを配置上限に対するacceptance gate、64 objectを上限超過時のstress characterizationとして扱う。
両runは同一APK、theme、距離、72 Hzで実行する。通常の比較Gateは600秒、
production昇格時の長時間Gateは1800秒measurementとする。

## Prepared command

QuestをUSB接続して十分に冷却した後、次を実行する。

```sh
"/Applications/Unity/Hub/Editor/6000.3.19f1/Unity.app/Contents/MacOS/Unity" \
  -batchmode -nographics -projectPath "$PWD" \
  -executeMethod MatsuMotoMeterAR.Editor.ConceptReleaseBuilder.BuildPerformanceGate \
  -quit
scripts/run-quest-performance-matrix.sh KineticSafety
```

専用APKは`Builds/Performance/AnalogInstrumentMR-v0.2.0-perfgate-quest3.apk`へ生成し、release APKを
上書きしない。matrix開始前にQuestを装着し、controller / hand trackingを有効にして
`Controller Required`などのsystem dialogが残っていないことを確認する。

処理順:

1. battery temperatureが43.0°C以下で3回連続するまで待機
2. APKをinstallして48 objectを15秒warm-up + 600秒測定
3. 43.0°C以下へ再冷却
4. 同じAPKで64 objectを15秒warm-up + 600秒測定
5. host、device logと`[PerfGate] FINAL`を一覧化

環境変数:

| Variable | Default | Purpose |
| --- | ---: | --- |
| `MEASUREMENT_SECONDS` | 600 | 600（比較）または1800（production長時間） |
| `INTERVAL_SECONDS` | 30 | temperature / memory sampling間隔 |
| `COOLDOWN_TARGET_DECI_C` | 430 | run開始温度、0.1°C単位 |
| `COOLDOWN_TIMEOUT_SECONDS` | 1800 | 冷却待ち上限 |
| `APK` | performance gate APK | 同一APKを両runで使用 |
| `ADB` | Unity 6000.3.19f1 SDK | adb実体 |
| `INSTALL_APK` | 1 | 端末側が新しいbuildなら0でinstallを省略 |
| `DISPLAY_MODE` | None | TrendMonitorの`None` / `Numeric` / `Graph`表示profile |

単独runでは`DISTANCE_METERS`と`INSTRUMENT_KIND`も指定できる。matrix acceptanceでは未指定とし、
距離1.35 m、既存6 archetype混在baselineを使用する。`INSTRUMENT_KIND=TrendMonitor`を
指定すると、Trend Monitor単独の表示負荷を測定できる。`DISPLAY_MODE=None`は表示componentを
無効化した筐体のみ、`Numeric`は静的な1入力数値、`Graph`は2入力とAverage合成線を5 Hzで更新する。
`Numeric` / `Graph`は`INSTRUMENT_KIND=TrendMonitor`との組み合わせに限る。同じAPK、配置、theme、
開始温度で3 profileを比較する。

```sh
MEASUREMENT_SECONDS=60 INSTRUMENT_KIND=TrendMonitor DISPLAY_MODE=None \
  scripts/run-quest-performance-gate.sh 48 KineticSafety
MEASUREMENT_SECONDS=60 INSTRUMENT_KIND=TrendMonitor DISPLAY_MODE=Numeric INSTALL_APK=0 \
  scripts/run-quest-performance-gate.sh 48 KineticSafety
MEASUREMENT_SECONDS=60 INSTRUMENT_KIND=TrendMonitor DISPLAY_MODE=Graph INSTALL_APK=0 \
  scripts/run-quest-performance-gate.sh 48 KineticSafety
```

## Recorded evidence

各runで次を保存する。

- APK pathとSHA-256
- count、theme、duration、distance、kind
- 30秒ごとのbattery level、temperature、PSS / RSS / swap
- CPU / GPU / frame p95、delayed frame率
- GC collection、最大frame allocation、Unity allocated memory
- fatal count、thermal stop有無

## Verdict

48 object:

- fatal error 0、thermal stopなし
- steady-state GC allocation 0 B/frameを目標
- delayed frame 1%未満
- 有効な場合、CPU / GPU p95各11 ms以下
- GPU timingがQuest/OpenXRで0の場合は`UNAVAILABLE`として外部計測とframe p95で判定する

64 object:

- acceptance保証点ではないため、48と同じ閾値を強制しない
- crash、thermal、memory growth、frame degradationを48との差分として記録する
- 64の失敗だけで48の合格を取り消さないが、Gate C release noteへstress限界を記載する

candidate統合前にactive asset baselineを測り、Gate C combined candidate統合後に同じmatrixを再実行する。
run間でAPK、theme、開始温度条件を変えない。

## Machined Ergonomics production result (2026-08-26)

第4productionテーマの登録後にQuest 3実機で測定した。APKは
`Builds/Performance/AnalogInstrumentMR-MachinedErgonomics-perfgate-quest3.apk`、
SHA-256は`89c22fa4a0cfb6fe41d26ca6a618b6b565f235452853297a82db9404a03f3eff`。
themeは`MachinedErgonomics`、距離1.35 m、72 Hz、6機種混在baselineを使用した。

| Metric | 48 objects acceptance | 64 objects stress |
| --- | ---: | ---: |
| Measurement | 1800 s | 600 s |
| Samples | 129,610 | 42,883 |
| CPU p95 | 14.434 ms | 14.561 ms |
| GPU p95 | 0.000 ms (`UNAVAILABLE`) | 0.000 ms (`UNAVAILABLE`) |
| Frame p95 | 14.431 ms | 14.555 ms |
| Delayed frames | 0.017% | 0.047% |
| GC collections | 0 | 15 (`OBSERVE`) |
| Maximum GC allocation in frame | 0 B | 0 B |
| Unity allocated memory | 140,292,174 B | 140,250,982 B |
| Temperature | 43.0 -> 43.0 C (42.0–43.0 C) | 44.0 -> 45.0 C |
| Fatal / thermal stop | 0 / no | 0 / no |

48 objectsは30分全体を記録し、steady-state PSSは60秒時455,834 KBから終了時453,449 KBへ
2,385 KB減少した。delayed frameは1%を十分下回り、GC collectionとframe allocationは0、fatalと
thermal stopも0である。Quest/OpenXRのGPU timingは0で、CPU/frame p95は72 Hz pacingを含むため
内部diagnosticは`REVIEW`となるが、外部stability gateは**PASS**とする。

64 objectsはユーザー判断により長時間runを早期短縮した。正式な`FINAL`を残すため、対応済みの
600秒measurementとして再実行した。開始温度44.0 Cは比較開始条件43.0 C以下を満たさないため、
baseline同条件のacceptance比較には使わずstress characterizationに限定する。steady-state PSSは
60秒時443,696 KBから終了時446,486 KBへ2,790 KB増、delayed frame 0.047%、frame allocation 0 B、
fatal / thermal stop 0である。GC collection 15回を`OBSERVE`として残し、結果は
**PASS as stress characterization**とする。

Evidence:

- 48 host: `Builds/Reports/perfgate-48-MachinedErgonomics-20260826-200429.log`
  (`c9c9eed847326845e282c8df485f9bf04a90cdce54c0e47585a23689e14d61af`)
- 48 device: `Builds/Reports/perfgate-48-MachinedErgonomics-20260826-200429-device.log`
  (`409acf08a81426ce3457716ee794d218ffa1e405e000f68211fbef2c0e62656b`)
- 64 host: `Builds/Reports/perfgate-64-MachinedErgonomics-20260826-204407.log`
  (`9245450a593ff05eb3a2570084b186412c1dbf90166bddf87a43d5fec54a308c`)
- 64 device: `Builds/Reports/perfgate-64-MachinedErgonomics-20260826-204407-device.log`
  (`838550a018f9f27166b63ac9f099c0003eef13112d42d19b1ef42b22d38807bb`)

この混在baselineにはTrendMonitorの静的筐体と表示componentが含まれるが、signal connectionと履歴更新は
駆動しない。動的TrendMonitorおよび将来のparametric WindowPanelは、表示更新なし／ありを同一配置で
比較する専用matrixを別途実行する。
