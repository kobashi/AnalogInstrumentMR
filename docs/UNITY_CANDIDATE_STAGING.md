# Unity candidate staging manifest

Blender candidateをactive Unity assetへ直接入れず、candidate IDごとのResourcesへ隔離importする。
モデル追加のたびにUnity Editor codeへ配列を追加せず、JSON manifestのentry追加だけでstagingと
validatorの対象を更新できる。

## Manifest

検証済みの例:

`Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/Opus5_R2.json`

```json
{
  "schemaVersion": 1,
  "candidateId": "Opus5_R2_Manifest",
  "entries": [
    {
      "theme": "KineticSafety",
      "model": "MeterRound",
      "sourceFbx": "ArtSource/Blender/BrushUp/Opus5/.../candidate.fbx",
      "sourceReport": "ArtSource/Blender/BrushUp/Opus5/.../candidate.json"
    }
  ]
}
```

- `candidateId`: ASCII英数字、`_`、`-`のみ
- `theme`: `OrbitalAnalog`、`ForgeBrass`、`KineticSafety`
- `model`: Unityが対応する13 archetypeのkey
- `sourceFbx`: `ArtSource/Blender/BrushUp/Opus5/`配下の既存FBX
- `sourceReport`: 同じcandidate tree配下のJSON。省略可能
- 同じ`theme/model`を重複させない
- `theme`と`model`は既知の3テーマ・13 archetypeだけを受け付ける

schema v1は既存の単一revision候補との互換用である。複数revisionを合成するGate C候補は
schema v2を使う。

```json
{
  "schemaVersion": 2,
  "candidateId": "KineticSafety_Meters_B2_D3",
  "integrationStage": "GateB",
  "entries": [
    {
      "theme": "KineticSafety",
      "model": "MeterMedium",
      "sourceFbx": "ArtSource/Blender/BrushUp/Opus5/.../combined.fbx",
      "sourceReport": "ArtSource/Blender/BrushUp/Opus5/.../combined.json",
      "revision": "B2_D3",
      "includedRevisions": ["B2", "D3"],
      "requiredRevisions": ["B2", "D3"]
    }
  ]
}
```

- `GateB`: 未合成候補を隔離stagingできる。`requiredRevisions`不足はreadiness上BLOCKEDになる
- `GateC`: `requiredRevisions`がすべて`includedRevisions`に無ければmanifest自体を拒否する
- `revision`: FBXとして受け渡す合成revisionの識別子
- `includedRevisions`: 実際に形状へ含まれる変更
- `requiredRevisions`: Gate Cで失ってはならない承認済み変更

このためproduction baseline由来のD3だけをB2承認済みmeterへ適用し、brush-upを巻き戻すmanifestは
Gate Cへ昇格できない。
既知のmeter合成条件は`CandidateIntegrationPolicy`にも登録され、manifest側がrequiredからrevisionを
省略してもGate C validationとreadiness reportが不足を検出する。

source pathの絶対path、`..`によるcandidate tree外参照、未存在fileは拒否される。

## Build and validation

Unity Project windowでmanifest JSONを選び、次を実行する。

1. `Tools/MatsuMotoMeterAR/Model Replacement/Build Selected Candidate Manifest`
2. `Tools/MatsuMotoMeterAR/Model Replacement/Validate Selected Candidate Manifest`

出力先:

```text
Assets/MatsuMotoMeterAR/Content/RefinedCandidates/CandidateStaging/<candidateId>/
  candidate-manifest.json
  Models/<Theme>/
  Resources/<candidateId>/<Theme>/{Materials,Prefabs}/
```

builderはactive atlasを参照するcandidate専用materialとprefabを作る。active Resources、production
FBX、prefab、material、textureは変更しない。

validatorはmanifest記載prefabのroot、motion target、renderer、material、triangle、bounds、
mount面を検査する。stagingに保存したmanifest snapshotが選択元とbyte一致すること、および
manifestに無いprefabが同candidate ID配下へ残っていないことも必須とする。

`sourceReport`が指定されている場合は、reportのmodel identity、FBX path、triangleをUnity import結果と
照合する。reportにrenderer、material slot、candidate boundsが含まれる場合はそれらも照合する。
FBX handoffでは`sourceReport`を省略せず、FBX export reportを同時に渡すことを受入条件とする。

entryを削除・置換したmanifestで既存candidate IDを再利用すると、古いprefabをvalidatorが検出する。
履歴を残す候補は新しいcandidate IDを使う。既存stagingの削除は自動では行わない。

## Visual / motion / Quest review

Project windowでmanifest JSONを選ぶと、同じentry集合から次の処理を実行できる。

1. `Render Selected Candidate Manifest Visual Review`
   - active OFF / active ON / candidate OFF / candidate ONの4列
   - manifestのentry順に1行ずつ出力
   - `Builds/Reports/candidate-<candidateId>-unity-visual-contact-sheet.png`
2. `Audit Selected Candidate Manifest Motion`
   - Meter、Lever、Toggle、Rotary、Button、Throttle、PowerSlider、WindowMeter、WindowPanelを対象
   - 全状態のlinear / angular travel、axis alignment、mount Zを記録
   - Lamp / StatusIndicatorのような静的・発光状態モデルはskipする
3. `Build Selected Candidate Manifest Quest Review APK`
   - staging build、validator、motion auditを先に実行する
   - build中だけ`CandidateReviewConfiguration.json`をResourcesへ生成し、manifest記載prefabへ切り替える
   - build終了時に一時configurationを削除し、隔離した`DevAgentSettings.asset`を必ず復元する

視覚sheetの生成にはGPUが必要である。CLIで実行する場合、`-nographics`では背景だけの画像になるため、
visual reviewだけは`-batchmode`とGPU有効状態で実行する。staging、validator、motion audit、EditModeは
`-nographics`でよい。

Quest review APKの生成はmanifest受入時の条件コンパイル確認には使えるが、Blender candidate gateごとに
実機を接続する必要はない。実機確認はFBX handoff後かGate Dで行う。

## Gate C readiness report

schema v2 manifestの`gateCEvidence`へ監査成果物を記録し、Project windowでmanifestを選択して
`Report Selected Candidate Gate C Readiness`を実行する。結果は
`Builds/Reports/candidate-<candidateId>-gate-c-readiness.md`へ出る。

自動列挙する項目:

- entryごとのrevision lineageとFBX export report
- 39モデルsemantic / UV監査
- fixed-camera視覚比較
- 可動entryがある場合のmotion audit
- Unity staging validator
- EditMode結果
- Quest 48-object acceptance gate
- Quest 64-object stress characterization
- production更新前のrollback plan

証跡pathが未設定または存在しない項目は`BLOCKED`になる。Gate C manifestへ切り替えただけでは
production assetは変更されない。詳細は`docs/GATE_C_INTEGRATION.md`を参照する。

## Verified baseline

`Opus5_R2.json`のMeterRound / Lever / ThrottleをUnity 6000.3.19f1で生成・検証した。

| model | triangles | renderers | materials | result |
| --- | ---: | ---: | ---: | --- |
| MeterRound | 4,636 | 2 | 2 | PASS |
| Lever | 4,432 | 2 | 2 | PASS |
| Throttle | 4,020 | 2 | 2 | PASS |

source report照合を含むstaging validatorと汎用motion auditの結果:

| model | motion states | angular travel | axis alignment | result |
| --- | ---: | ---: | ---: | --- |
| MeterRound | 5 | 110° | 1.0000 | PASS |
| Lever | 5 | 48° | 1.0000 | PASS |
| Throttle | 6 | 70° | 1.0000 | PASS |

GPU有効のUnity比較sheetを生成して3モデル×4条件を確認した。`ANALOGMR_CANDIDATE_REVIEW`を使う
汎用Quest APKもbuild成功し、一時configuration削除とdevelopment credential復元を確認した。
EditModeは**119/119 PASS**（manifest新規7件を含む）。これはmanifest staging基盤の検証であり、
production integration gateや各brush-up candidateの視覚・motion承認を代替しない。

### Toggle D5 / D10 M2i handoff

`Toggle_D5_D10_M2i.json`でOrbitalAnalog D5、ForgeBrass D5_D10、KineticSafety D5を隔離stageした。
M2i inventory reportのFBX SHA-256、triangle合計、MESH数をUnity import後と照合し、3件とも13 renderer、
1 material、mount plane逸脱0でvalidator PASS。motion auditも3 state / 56° / axis alignment 1.0000で3/3 PASS、
EditModeは125/125 PASSした。GPU比較sheetとQuest review APKは次へ出力する。

- `Builds/Reports/candidate-Toggle_D5_D10_M2i-unity-visual-contact-sheet.png`
- `Builds/QuestReview/AnalogInstrumentMR-Toggle_D5_D10_M2i-review-quest3.apk`

この時点ではQuest実機受入までactive / productionへ昇格しない。

Quest 3実機では3テーマのOFF / ON、切替中の動き、正面・斜視、手元距離、D-5軸・リング、ForgeBrass D-10
ストッパーを確認し、欠損、ちらつき、めり込み、過大gap、不自然な操作感なしで**PASS**した。motion auditの
3 stateは0° / 28° / 56°の監査sampleであり、runtime Toggle自体は二状態である。これにより本candidateは
Gate C readinessへ進められるが、active / production昇格はGate C判定まで行わない。

## B2 / B3 FBX handoff

Gate B2 / B3は現時点でBlend candidate段階であり、FBXとexport reportが無い間はmanifestへ追加しない。
Opus 5からFBX handoffが来たら、candidate revisionごとに新しいmanifestと`candidateId`を作り、次の順で
受け入れる。

1. FBX、export report、承認済みBlend report / review indexの対応を確認
2. manifest buildとsource report照合validator
3. GPU有効のactive / candidate比較sheet
4. 可動モデルのmanifest motion audit
5. Blender gateで報告されたtriangle、bounds、hierarchy、motionとの差分が無いことを確認
6. Gate Dで必要になった時だけQuest review APKと実機受入

## Change partition

並行作業のcommitは次の単位へ分ける。

- Opus 5: Blender generator / reviewer、candidate Blend、Blender report / image、alignment回答
- Codex: Unity manifest staging / validator / visual / motion / Quest review基盤、EditMode test、本書
- candidate handoff: 承認済みrevisionのFBX、export report、manifestだけを独立commit
- production integration: active FBX / prefab / material / texture / `.meta`の置換を別commit・別gateで実施

`Builds/`、Unityが生成した`CandidateStaging/`、一時review configurationはcommit対象にしない。
