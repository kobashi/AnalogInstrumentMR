# Quest 48 / 64 object long-run performance

48 objectを配置上限に対するacceptance gate、64 objectを上限超過時のstress characterizationとして扱う。
両runは同一APK、theme、距離、72 Hz、600秒measurementで実行する。

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
| `MEASUREMENT_SECONDS` | 600 | matrixでは600のみ |
| `INTERVAL_SECONDS` | 30 | temperature / memory sampling間隔 |
| `COOLDOWN_TARGET_DECI_C` | 430 | run開始温度、0.1°C単位 |
| `COOLDOWN_TIMEOUT_SECONDS` | 1800 | 冷却待ち上限 |
| `APK` | performance gate APK | 同一APKを両runで使用 |
| `ADB` | Unity 6000.3.19f1 SDK | adb実体 |
| `INSTALL_APK` | 1 | 端末側が新しいbuildなら0でinstallを省略 |

単独runでは`DISTANCE_METERS`と`INSTRUMENT_KIND`も指定できる。matrix acceptanceでは未指定とし、
距離1.35 m、13 archetype混在baselineを使用する。

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
