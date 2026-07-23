# Orbital Analog Quest 3 placement and restore test

## Build under test

- Date: 2026-07-20
- Unity: `6000.3.19f1`
- APK: `Builds/Release/MatsuMotoMeterAR-v0.1.0-concept.1-quest3.apk`
- SHA-256:
  `587ab775004c0ced00df3413faaaedc7775d409aed961fef9c5277976f7f50d5`
- Android: ARM64、IL2CPP、Vulkan、Minimum API 32、Target API 34
- Signature: Android Debug certificate、APK Signature Scheme v2
- EditMode: 29 passed、0 failed

この版は`orbital-analog`のBlender/FBX visualを`VisualSocket`直下へ配置する。
Spatial Anchor root、type ID、15 mm surface offset、InteractionColliderは従来と同じ。

## Device status

2026-07-20にMeta Quest 3で実施。APK install、OpenXR
session、72 Hz、MRUK room loadを確認し、6種類すべてで配置、Activity強制終了、
再起動、同じtypeと実空間poseへのSpatial Anchor復元に成功した。各復元起動で
MRUKは`Success`、Unity／Android／Anchorエラーは0件だった。

現行placement storeは1スロットなので、6種類は同時配置ではなく以下の手順を
種類ごとに繰り返した。

## Common procedure

1. Quest 3でSpace Setup済みの部屋を開き、USB debuggingを許可する。
2. APKを`adb install -r`でinstallし、アプリを起動する。
3. `ROOM READY`を確認する。
4. 右スティック左右で対象種類を選択し、許可面へ照準する。
5. 緑previewが面から15 mm offsetされ、向きと寸法が正しいことを確認する。
6. `A`で配置し、保存完了表示と可動部の動作を確認する。
7. Activityを強制終了して再起動する。
8. 同じ種類が同じ実空間poseへ復元されることを確認する。
9. 右スティック押し込みで削除してから次の種類へ進む。

```sh
ADB="/Applications/Unity/Hub/Editor/6000.3.19f1/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb"
"$ADB" install -r Builds/Release/MatsuMotoMeterAR-v0.1.0-concept.1-quest3.apk
"$ADB" shell monkey -p com.DefaultCompany.MatsuMotoMeterAR 1
"$ADB" shell am force-stop com.DefaultCompany.MatsuMotoMeterAR
"$ADB" logcat -s Unity ActivityManager AndroidRuntime
```

## Six-type matrix

| Type ID | Primary surface | Expected motion | Restore |
| --- | --- | --- | --- |
| `meter.round` | Wall | needle ±55° | PASS (Quest 3, 2026-07-20) |
| `control.lever` | Wall / Floor | handle ±32°、Ceiling拒否 | PASS (Quest 3, 2026-07-20) |
| `control.toggle` | Wall | switch ±28° | PASS (Quest 3, 2026-07-20) |
| `control.rotary` | Wall / Floor | continuous rotation、Ceiling拒否 | PASS (Quest 3, 2026-07-20) |
| `control.button` | Wall | travel 14 mm | PASS (Quest 3, 2026-07-20) |
| `indicator.lamp` | Wall | amber emission pulse | PASS (Quest 3, 2026-07-20) |

各種類で、root scale `(1,1,1)`、visual colliderなし、InteractionCollider 1個、
再起動前後のtype ID一致も確認する。性能確認は72 Hzで行い、通常配置時に長い
フリーズや継続的なGC spikeがないことを記録する。

## Result

- Placement and restore: 6 / 6 PASS
- MRUK room load after restart: 6 / 6 `Success`
- Unity / Android / Anchor errors during restore: 0
- Lever / Rotary ceiling rejection: PASS
- Button / Lamp silhouette distinction: PASS
- Quest 3 continuous stability, 10 minutes: PASS
  - Process remained alive
  - Unity / Android errors: 0
  - CPU: 32.8% to 33.4% in Android `top` (600% = all six cores)
  - PSS: 473,622 KB to 473,873 KB (+251 KB)
  - RSS: 644,362 KB to 645,110 KB (+748 KB)
  - App swap: 32 KB, unchanged
  - Display period: 13,888,888 ns (72 Hz)
- Quest 3S physical test: deferred by project decision (2026-07-20)
- Quest 3 was disconnected after the test and remains offline while charging.
- App CPU/GPU frame-time p95: not captured; SurfaceFlinger does not expose
  OpenXR compositor frame timestamps for this layer
