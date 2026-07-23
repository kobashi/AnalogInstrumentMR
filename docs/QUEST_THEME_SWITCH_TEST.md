# concept.2 Quest 3 theme switch and restore test

## Build under test

- Date: 2026-07-20
- Device: Meta Quest 3
- APK: `Builds/Release/MatsuMotoMeterAR-v0.1.0-concept.2-quest3.apk`
- SHA-256:
  `835a2594d11b917bbe3398344fde9028b0b2ff70a01b84bdfb8d5739ca755e8c`
- Android: ARM64、IL2CPP、Vulkan、Minimum API 32、Target API 34
- Unity EditMode: 32 passed、0 failed

Quest 3S実機検証はプロジェクト判断で見送る。

## Procedure and result

| Check | Procedure | Result |
| --- | --- | --- |
| Install / launch | `adb install -r`後に起動 | PASS |
| MRUK room | 起動後にroom dataをload | PASS (`Success`) |
| Preview theme cycle | 右スティック上でOrbital Analog → Kinetic Safety → Forge Brass → Orbital Analog | PASS |
| Placed visual replacement | Kinetic Safetyを壁へ配置し、Forge Brassへ切り替え | PASS |
| Root pose retention | theme交換前後の位置、向き、種類を目視比較 | PASS |
| Global theme persistence | Forge Brass選択後にActivityを強制終了・再起動 | PASS |
| Spatial Anchor restore | 同じForge Brass、種類、実空間位置、向きへ復元 | PASS |
| Visual integrity | pink、欠落、二重表示がない | PASS |
| Runtime errors | Unity / Android / Spatial Anchor fatal error | 0 |

配置済みオブジェクトの交換ではSpatial Anchor付き`InstrumentRoot`を再生成せず、
`VisualSocket`以下だけを交換する。既存のanchor UUID keyとtype ID keyは変更せず、
global themeは独立した`settings.instrument.themeId`へ保存する。

## Runtime snapshot

復元確認後の単点計測。

| Item | Result |
| --- | --- |
| Process | alive |
| CPU (`top`, 600% = 6 cores) | 37.0% |
| PSS | 473,028 KB |
| RSS | 641,962 KB |
| App swap | 28 KB |
| Display refresh | 72.00 Hz |
| VSYNC period | 13,888,888 ns |

起動時バッテリーは69%。USB給電中だったが`Weak Charger: true`で、終了時54%、
45.0°Cだった。検証終了後はアプリをforce-stopした。

## Ten-minute continuous stability

2026-07-21に、保存済みForge Brassを復元した`concept.2`をQuest 3で10分間
連続実行した。30秒間隔、全21点でprocess、CPU、PSS、RSS、swap、battery、
temperatureを取得した。

| Item | Result |
| --- | --- |
| Duration / samples | 10 minutes / 21 |
| Process remained alive | PASS |
| CPU | 26.9% to 38.4% (`600%` = all six cores) |
| PSS | 465,057 KB to 466,666 KB (+1,609 KB) |
| RSS | 633,434 KB to 636,798 KB (+3,364 KB) |
| App swap | 4 KB, unchanged |
| Display refresh | 72.00 Hz |
| VSYNC period | 13,888,888 ns |
| Unity / Android / Anchor fatal errors | 0 |
| Temperature | 44.0°C to 45.0°C |
| Battery during timed interval | 91% to 87% |

USBは今回も`Weak Charger: true`、battery statusはdischargingだった。48°Cを
thermal stop条件としたが到達しなかった。試験終了後はアプリをforce-stopした。

## Expected platform warnings

再起動時に、Quest runtimeが提供しない任意OpenXR extension
（parametric haptics、space sharing）の`ErrorFunctionUnsupported` warningが3件
出た。OpenXR session、MRUK、theme、anchor機能には影響せず、アプリ例外ではない。

## Conclusion

`concept.2`のglobal theme切り替え、配置済みvisual交換、theme保存、Activity再起動後の
Spatial Anchor／theme同時復元、10分連続安定性はQuest 3でPASSした。
長時間theme連打と24個配置性能は、複数配置store実装後のperformance gateで行う。
