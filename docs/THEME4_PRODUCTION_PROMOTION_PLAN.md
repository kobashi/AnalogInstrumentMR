# Machined Ergonomics production promotion plan

## Goal

受入済みの`MachinedErgonomics` 14機種を、既存3テーマを上書きせず、第4テーマとしてproductionへ登録する。
theme IDは`machined-ergonomics`、表示名は`MACHINED ERGONOMICS`とする。

第4テーマ本番登録は2026-08-26にユーザー承認済み。自動Gate、Quest APK導入、
production theme cycle／visual／operation確認までPASS。48 objects 30分acceptanceと、ユーザー判断で
短縮した64 objects 10分stress characterizationも完了した。

## Frozen input

- candidate root:
  `Assets/MatsuMotoMeterAR/Content/RefinedCandidates/CandidateStaging/Theme4_MachinedErgonomics_14_FullGate`
- Unity Gate report:
  `Builds/Reports/theme4-machined-ergonomics-14-full-unity-gate.md`
- models: 14 / 14 PASS
- EditMode: 150 / 150 PASS
- Quest review APK SHA-256:
  `8634904246490d74f849f26057761b9baf56ea7299deb5d1fccffb4bca997510`
- Quest visual / motion / TrendMonitor contrast: user PASS

## Promotion changes

### 1. Production assets

既存テーマと同じ分離規約で新規追加する。

- `Assets/MatsuMotoMeterAR/Resources/MachinedErgonomics/Prefabs/`: 14機種。
  名前は`PF_Visual_<Key>_MachinedErgonomics`
- `Assets/MatsuMotoMeterAR/Content/Themes/MachinedErgonomics/Models/`: 14 FBX
- `Assets/MatsuMotoMeterAR/Content/Themes/MachinedErgonomics/Materials/`:
  opaque、emissive、TrendMonitor専用dark display
- `Assets/MatsuMotoMeterAR/Content/Themes/MachinedErgonomics/Textures/`:
  1K BaseColor / Normal / MetallicSmoothness / Emission

既存`OrbitalAnalog`、`ForgeBrass`、`KineticSafety`のasset、GUID、材質、textureは変更しない。
candidate review用Resources overrideとcompile defineはproduction経路へ持ち込まない。

### 2. Runtime registration

- `MockInstrumentTheme`へ末尾値`MachinedErgonomics = 3`を追加し、既存数値を維持する
- `MockInstrumentThemeCatalog.Count`を4へ変更する
- ID、表示名、palette、round-trip、cycle、preference fallbackを追加する
- `InstrumentThemeVisualFactory.ThemeFolder()`へ`MachinedErgonomics`を追加する
- 14機種すべてがproduction Resourcesから解決され、primitive fallbackが0であることを検証する
- performance configurationで`MachinedErgonomics`と`machined-ergonomics`を解決可能にする

### 3. Audits and tests

- motion auditとsignal visual auditを4テーマへ拡張する
- production validatorへ第4テーマ14 prefabを追加する
- theme ID一意性、round-trip、cycle forward/backward、保存復元を更新する
- 全14機種×4テーマの共通root/socket/manifest契約を確認する
- TrendMonitorはdark display、depth-tested text、LineRenderer、複数入力履歴を確認する
- materialはURP Error Shader 0、visual Collider / Light / Camera / Animator 0とする
- EditMode全件、motion 14/14、signal visual、production prefab validationをPASSさせる

### 4. Quest gates

1. production相当の第4テーマAPKで、theme cycleが4テーマを一周する
2. Machined Ergonomicsの14機種がすべて専用prefabで、primitive fallbackがない
3. 既存3テーマの外観、操作、信号表示に明白な回帰がない
4. WindowMeter / WindowPanelが±115°、TrendMonitorが正面配置・dark displayである
5. 48 objectsを最低30分、続いて64 objectsを最低30分動作させ、発熱、フレーム落ち、
   tracking、anchor、signal更新、LineRenderer memoryを記録する

実測では48 objectsを1800秒完了した。64 objectsは途中でユーザーが15分以内で十分と判断し、正式な
端末`FINAL`を残せる600秒runへ短縮した。48はexternal stability PASS、64はGC collection 15回と
開始温度44 CをOBSERVEとするstress PASS。混在baselineはsignal connection / 履歴更新を駆動しないため、
動的LineRenderer負荷は後工程の専用matrixへ分離する。

## Promotion gate

production昇格の実装はユーザーによる「第4テーマ本番登録」の明示承認を受けて開始した。
正式release / merge / tagは別承認とし、隔離branch上の全自動GateとQuest Gateを先に行う。

## Recovery

第4テーマは新規Resources rootと末尾enumだけで追加する。Gate失敗時は新規theme登録と新規rootを
同一commit単位で戻し、既存3テーマへ影響を残さない。candidate成果物と受入証跡は保持する。
