# Quest 3 user acceptance test

## Policy

2026-07-23のプロジェクト判断により、残るQuest 3実機検証は通常runtimeを自由に使用する
ユーザー受入試験とする。厳密な24 Anchor配置matrixや固定時間の計測はrelease blockerに
しない。使用中に問題が確認されなければPASSとする。

Quest 3S実機検証は引き続き見送る。

## Build

- APK: `Builds/Release/MatsuMotoMeterAR-v0.1.0-concept.5-perfgate-quest3.apk`
- Size: 66,944,913 bytes
- SHA-256:
  `03aae5d6ca35b15a6aedb1e0919d1fbb883434b3fd11f5c6b2e7c4d455a6c2ab`
- Signing: Android Debug certificate
- Distribution: private measurement only

## Usage

通常起動し、実際の利用に近い形で任意に使用する。以下は確認例であり、個数、順序、
時間を固定しない。

- 計器や操作部品を壁・床・天井へ配置する
- ray / directでメーター、レバー、トグル、ロータリー、ボタン、状態灯を操作する
- 3テーマを切り替える
- 複数配置、照準削除、24件上限を必要に応じて試す
- アプリを終了・再起動し、Spatial Anchor、種類、theme、状態を確認する
- 頭部移動中の表示、パススルー、controller入力、hapticsを確認する

## Verdict

次のようなユーザー可視・操作上の問題がなければPASSとする。

- crash、freeze、操作不能
- 保存済み配置の欠落、重複、原点飛び、明らかな位置ずれ
- 種類、theme、個別状態の誤復元
- pink material、欠落mesh、片眼表示、可視screen tear
- 明らかなフレーム低下、入力遅延、誤対象の操作・削除
- 異常発熱や安全上の問題

問題が見つかった場合は、再現手順、対象種類、theme、操作方法、再起動前後、可能なら
写真または動画を記録してFAIL / 要調査とする。問題がなければユーザー報告
`問題なし`をもってPASSとする。

## Result

- Date: 2026-07-23
- Duration: 任意（固定時間なし）
- Approximate placements: 任意（詳細未記録）
- Operations tried: 通常runtimeの自由使用
- Restart / restore: 任意（詳細未記録）
- User-visible issues: なし
- Verdict: **PASS**
- Notes: ユーザー報告`問題なし`。プロジェクト定義の最終実機受入条件を満たした。
