# concept.3 Quest 3 ray/direct interaction test

## Build under test

- Date: 2026-07-21
- Device: Meta Quest 3
- APK: `Builds/Release/MatsuMotoMeterAR-v0.1.0-concept.3-quest3.apk`
- SHA-256:
  `5fc8700287e898fefd110e87388f23283bd0381917f42a3baf03cff4e3450db1`
- Unity EditMode: 35 passed、0 failed
- Quest 3S: プロジェクト判断で見送り

## Preconditions

1. Quest 3をデータ対応USBで接続する。
2. 開発者モードを有効にし、ヘッドセット内のUSBデバッグ許可を承認する。
3. `adb devices -l`が`device`状態のQuest 3を1台表示することを確認する。
4. APKを`adb install -r`でインストールし、アプリを起動する。

## Test matrix

各種類を壁へ配置し、最初に1–5 mのray、次にコントローラー先端を近づけたdirectで
右Triggerを操作する。操作ごとに短いhapticsとHUDの`RAY TRIGGER`または
`DIRECT TRIGGER`、論理値を確認する。

| 種類 | Ray期待値 | Direct期待値 | Result |
| --- | --- | --- | --- |
| 円形メーター | 目盛りが0.25進む | 同じ | PASS |
| レバー | 反対端へ切り替わる | 同じ | PASS |
| トグル | 反対端へ切り替わる | 同じ | PASS |
| ロータリーノブ | 1/8回転進む | 同じ | PASS |
| 押しボタン | 保持中に沈み、解放で戻る | 同じ | PASS |
| 状態灯 | 点灯／消灯が切り替わる | 同じ | PASS |

## Automated startup checks

| Check | Result |
| --- | --- |
| `adb install -r` | PASS |
| Version | PASS (`0.1.0`, versionCode 1) |
| Activity foreground / process alive | PASS |
| OpenXR / Quest 3 recognition | PASS |
| MRUK room load | PASS (`Success`) |
| Spatial Anchor localization | PASS |
| Display refresh | PASS (72 Hz) |
| Unity / Android fatal exception at startup | 0 |

## Regression checks

| Check | Procedure | Result |
| --- | --- | --- |
| Held-trigger edge | Triggerを保持し、離すまで連続動作しない | PASS |
| Direct priority | 接触中にrayも当たる姿勢で操作し、HUDが`DIRECT`となる | PASS |
| Exit priority | 終了パネルを狙ってTriggerし、計器状態が変わらない | PASS |
| Theme retention | 非初期値にしてthemeを切り替え、値とposeを維持する | PASS |
| Activity restore | 非初期値で終了・再起動し、anchor、theme、値を復元する | PASS |
| Existing controls | A配置、stick種類/theme選択、stick click削除が動く | PASS |
| Runtime errors | Unity / Android / Spatial Anchor fatal errorが0 | PASS (0) |

## Runtime snapshot

6種類と再起動復元の確認後に取得した単点計測。

| Item | Result |
| --- | --- |
| Process | alive |
| PSS / RSS | 471,363 KB / 641,590 KB |
| App swap | 4 KB |
| VSYNC period | 13,888,888 ns (72 Hz) |
| Battery | 65%、USB powered / charging |
| Temperature | 45.0°C |
| Fatal errors | 0 |

## Conclusion

Quest 3で3テーマ×6種類のray/direct操作、held-trigger edge、haptics、終了操作優先、
theme交換後の論理値／pose維持、Activity再起動後のSpatial Anchor／theme／論理値復元を
PASSした。Quest 3S実機検証は見送りとする。
