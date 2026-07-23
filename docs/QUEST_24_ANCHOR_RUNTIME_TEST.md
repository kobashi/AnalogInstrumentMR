# Quest 3 real 24 Anchor runtime test

> Optional extended verification. 2026-07-23のプロジェクト判断により、本手順は
> release必須条件ではない。最終実機判定は`QUEST_USER_ACCEPTANCE_TEST.md`に従い、
> 通常使用で問題がなければPASSとする。

## Scope

Quest 3の通常runtimeで6種類×4、合計24個の実Spatial Anchorを配置し、個別操作状態、
global theme、Activity再起動後の復元、10分72 Hz性能を確認する。
synthetic performance scenarioは使用しない。Quest 3S実機検証はプロジェクト判断で
見送る。

## Build under test

- Device: Meta Quest 3
- APK: `Builds/Release/MatsuMotoMeterAR-v0.1.0-concept.5-perfgate-quest3.apk`
- Size: 66,944,913 bytes
- SHA-256:
  `03aae5d6ca35b15a6aedb1e0919d1fbb883434b3fd11f5c6b2e7c4d455a6c2ab`
- Unity EditMode: 62 / 62 PASS
- Thermal stop: 48°C

## Preconditions

- [ ] Quest 3 battery 60%以上、開始温度45°C以下
- [ ] USB debugが`device`、OVR Metrics Tool 86.0.0.0.0が利用可能
- [ ] Guardian / room setup完了、MRUKが壁面を認識
- [ ] APK hashが上記と一致
- [ ] 既存3 recordを削除して0/24から開始することを確認
- [ ] wall gridへ24個を置ける約1.6 m × 1.2 mの領域を確保

既存3 recordの削除は保存済みtest Anchorを破棄する操作なので、実行直前に明示確認する。
照準＋右stick clickで1件ずつ削除し、毎回
`recordRemoved=True, saved=True`を確認する。0/24後に再起動し、record、
pending-delete、unavailableが0であることを確認する。`pm clear`やuninstallで
初期化すると保存Anchorを孤児化し得るため使用しない。
leverとrotaryは天井へ配置しない。本試験では比較しやすいよう全24個を壁面へ置く。

## Placement matrix

6列×4段のwall gridを使う。type列は左から右、段A–Dは上から下とし、中心間隔を
横25 cm以上、縦30 cm以上空ける。HUDが`24/24`へ達するまで同じslotへ重ねて置かない。

| Row | Meter | Lever | Toggle | Rotary | Button | Lamp |
| --- | --- | --- | --- | --- | --- | --- |
| A | M-A | L-A | T-A | R-A | B-A | I-A |
| B | M-B | L-B | T-B | R-B | B-B | I-B |
| C | M-C | L-C | T-C | R-C | B-C | I-C |
| D | M-D | L-D | T-D | R-D | B-D | I-D |

各配置後にHUD件数が1増え、保存成功HUD / logがあり、既存rootが移動・置換されないことを
確認する。`24/24`到達後もpreviewは表示される現仕様なので、A入力が`LIMIT`として拒否され、
25件目のrecord / Anchorを作らないことを確認する。
4 / 8 / 12 / 16 / 20 / 24件の節目を記録し、save failure時は中断する。最終logで
24件のplacement ID / Anchor UUIDがunique、各type IDが4件であることを確認する。

## Interaction state matrix

全24個を操作した証拠としてA / B / C / Dをそれぞれ1 / 2 / 3 / 4回Triggerする。
A–Cはray、Dはdirectで操作し、haptics、HUDの入力種別と値、隣接個体が変化しないことを
確認する。押しボタンは保持中の沈みと解放後0への復帰を確認する。

| Type | A: 1回 | B: 2回 | C: 3回 | D: 4回 |
| --- | ---: | ---: | ---: | ---: |
| Round meter | 0.75 | 1.00 | 0.00 | 0.25 |
| Lever | 0.00 | 1.00 | 0.00 | 1.00 |
| Toggle | 0.00 | 1.00 | 0.00 | 1.00 |
| Rotary | 0.125 | 0.250 | 0.375 | 0.500 |
| Push button | 0 after release | 0 | 0 | 0 |
| Status lamp | 0.00 | 1.00 | 0.00 | 1.00 |

## Theme and persistence

1. 24個のroot poseと上記状態を確認する。
2. Orbital Analog → Kinetic Safety → Forge Brassの順にglobal themeを切り替える。
3. 各切り替えで24個すべての`VisualSocket`だけが交換され、root poseと状態が維持される
   ことを確認する。
4. 最終themeをForge Brassとして保存する。
5. アプリ内終了パネルから終了し、process消失を確認する。
6. 通常起動し、restore完了まで操作しない。
7. logでschema 1、24 record、`24/24 active`、unavailable 0、
   pending-delete 0を確認する。
8. grid slot、type、Forge Brass、状態matrix、Collider操作対象が一致することを確認する。
9. ghost、duplicate、pink material、欠落、root poseの目視ずれがないことを確認する。
10. restore所要時間を記録する。既存仕様に閾値がないため新しい合否値は設定しないが、
    MRUK timeoutやAnchor localization warningがあれば中断して調査する。

## Ten-minute normal-runtime performance

24/24復元完了後、操作せず15秒待ってからOVR Metrics ToolのAdvanced + GPU CSVを
600秒記録する。通常起動なので`matsu_perf_*` Intent extraは付けない。

```bash
ADB="/Applications/Unity/Hub/Editor/6000.3.19f1/PlaybackEngines/AndroidPlayer/SDK/platform-tools/adb"
PACKAGE="com.DefaultCompany.MatsuMotoMeterAR"
ACTIVITY="com.unity3d.player.UnityPlayerGameActivity"

"$ADB" shell am start -S -n "$PACKAGE/$ACTIVITY"
# 24/24 restore完了をlogと目視で確認し、15秒settle後に記録開始
"$ADB" shell am broadcast \
  -a com.oculus.ovrmonitormetricsservice.ENABLE_PRESET_ADVANCED_PLUS_GPU \
  -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver
"$ADB" shell am broadcast \
  -a com.oculus.ovrmonitormetricsservice.ENABLE_CSV \
  -n com.oculus.ovrmonitormetricsservice/.SettingsBroadcastReceiver
```

30秒ごとにprocess、battery、temperature、PSS/RSS/swapを記録する。48°C到達時は
即force-stopして冷却後に最初から再計測する。終了後はCSVを無効化し、アプリを停止する。
最初と最後の各60秒は頭を左右へ動かして24個を走査し、visible tearを目視確認する。
性能試験後にもう一度通常起動し、`24/24 active`、unavailable 0、pending-delete 0と
全状態 / themeを確認して、計測中にstore / Anchorが壊れていないことを確定する。

## Acceptance

| Gate | Pass condition | Result |
| --- | --- | --- |
| Placement count | HUD 24/24、24 unique record / Anchor |  |
| Type distribution | 6種類が各4個 |  |
| Individual state | state matrixと一致 |  |
| Theme swap | 24 root pose / state維持、Forge Brass保存 |  |
| Restart restore | 24/24 active、unavailable 0、pending-delete 0 |  |
| Visual integrity | ghost / duplicate / pink / missing 0 |  |
| Display | 72 Hz維持、平均72 fps以上 |  |
| App GPU | p95 11 ms未満 |  |
| CPU | sustained saturationなし |  |
| Frames | skipped / early / shader hitch 0、stale 1%未満 |  |
| Memory | steady-state PSS増加10%未満、swap増加なし |  |
| Runtime | process完走、fatal error 0 |  |
| GC | 通常non-Development runtimeでは直接計測不可。synthetic gateのGC 0を別証跡とする | N/A |
| Thermal | 48°C未満 |  |
| Visible tear | 頭部移動・ray/direct操作中に裂け、段差、ずれなし |  |

## Evidence

- Host log:
- Device log:
- OVR CSV:
- Start / end battery:
- Temperature range:
- Final placement revision:
- Restore duration:
- Placement matrix photo / screenshot:
- Notes:
