# Gate C candidate integration

Gate Cは、承認済みの独立candidateを1モデル1系統へ合成し、Unity active assetへ統合できる状態かを
判定するgateである。Blender candidateの単純置換や、別revisionの巻き戻しを防ぐことを最優先にする。

## Candidate lineage

同じ`theme/model`に複数の承認済みrevisionがある場合、schema v2 manifestで次を明示する。

- `includedRevisions`: handoff FBXへ実際に含まれるrevision
- `requiredRevisions`: Gate Cで維持が必須のrevision
- `revision`: 合成成果物自身の識別子

Gate Bでは未合成状態を記録できる。Gate Cへ昇格すると、requiredの一つでもincludedに無いentryは
manifest validationで停止する。

現在の既知の合成条件:

| Identity | Required lineage | 理由 |
| --- | --- | --- |
| KineticSafety/MeterRound | R2 + D3 | pilot brush-upと外周tick clearance |
| KineticSafety/MeterMedium | B2 + D3 | meter brush-upと外周tick clearance |
| KineticSafety/MeterLarge | B2 + D3 | meter brush-upと外周tick clearance |
| OrbitalAnalog/MeterRound | D3 + D4 | 外周tickとinner scale depth |
| OrbitalAnalog/MeterMedium | D3 + D4 | 外周tickとinner scale depth |
| OrbitalAnalog/MeterLarge | D3 + D4 | 外周tickとinner scale depth |

D4は未承認candidateのため、現時点のOrbitalAnalog required lineageは計画値でありGate Cへは進めない。

## Required evidence

schema v2 manifestの`gateCEvidence`には次のpathを設定する。

```json
"gateCEvidence": {
  "semanticUvAudit": "ArtSource/.../audit_39_combined.json",
  "fixedCameraVisualReview": "ArtSource/.../combined_review_index.json",
  "motionAudit": "Builds/Reports/candidate-motion-audit.md",
  "unityStagingValidation": "Builds/Reports/candidate-staging-validation.md",
  "editModeTests": "Builds/Reports/editmode-results.xml",
  "quest48Gate": "Builds/Reports/perfgate-48-....log",
  "quest64Stress": "Builds/Reports/perfgate-64-....log",
  "rollbackPlan": "docs/...-rollback.md"
}
```

Unityメニュー`Report Selected Candidate Gate C Readiness`は、lineageと各pathの存在を一覧化する。
証跡の内容自体の合否判定は各監査toolが担当し、readiness reportは欠落と組み合わせ事故を防ぐ。

## Acceptance order

1. Blenderで承認済みrevisionを合成し、production sourceとは別名で保存する
2. combined candidateの39モデルsemantic / UV監査と対象motion sweepを実行する
3. fixed-camera Before / Afterを視覚レビューする
4. FBXとexport reportを生成し、schema v2 manifestでisolated stagingする
5. Unity validator、motion audit、EditModeを実行する
6. Quest 48-objectをacceptance gate、64-objectをstress characterizationとして実行する
7. readiness reportが全項目PASSであることを確認する
8. production更新専用commitを作り、active FBX / prefab / material / textureだけを置換する

## Rollback

production更新commitの直前に、active asset pathとSHA-256、対応candidate ID、Unity test結果を記録する。
問題が出た場合はproduction更新commitだけをrevertし、Blender原本、candidate tree、監査証跡は保持する。
staging builderはactive Resourcesへ書き込まないため、Gate C以前のrollbackにactive asset操作は不要である。

Gate C完了前にcandidate staging directoryをproduction扱いしたり、baseline由来candidateをactive FBXへ
直接コピーしてはならない。
