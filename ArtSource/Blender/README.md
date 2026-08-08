# Blender source assets

Blender原本はUnityの`Assets`外で管理し、FBXとtextureだけをUnityへ渡す。

## Authoring version

- Supported authoring version: Blender `5.2.x`
- Migration baseline: Blender `5.2.0 LTS`
- Rollback reader: Blender `4.5.11 LTS`（移行完了までは削除しない）
- FBX exporter: `bpy.ops.export_scene.fbx` bundled Legacy FBX exporter

コマンドはPATH上の`blender`を直接呼ばず、`scripts/run-blender.sh`を使う。
macOSでは`/Applications/Blender 5.2.app`を優先し、別の配置は`BLENDER_BIN`で
指定する。launcherとPython preflightは5.2以外で生成処理を開始しない。

```sh
scripts/run-blender.sh --version
scripts/run-blender.sh --print-bin
```

5.2移行と新FBX exporterへの切り替えは同時に行わない。Unity出力の互換性を
確認するまでは従来のLegacy FBX operatorと`-Z Forward / Y Up`契約を維持する。

Blender 5.2のEEVEE識別子は`BLENDER_EEVEE`を使用する。4.5で生成した既存画像と
5.2のPBR previewには色調、発光、露出の差が生じ得るため、pixel hash一致は
要求しない。5.2でcontact sheetを再生成し、テーマ配色、材質role、Emissive
OFF／ON、暗部階調を視覚レビューして新しい基準画像を承認する。

## Theme asset sets

- `OrbitalAnalog/`: thin dark panel、bright dial、compact analog controls
- `ForgeBrass/`: cast-iron body、aged brass/copper accents、rivets
- `KineticSafety/`: graphite guards、chamfers、orange/yellow safety accents

各directoryには次を置く。

- Sources: `BL_*_<Theme>.blend`
- Previews: `Preview_*_<Theme>.png`
- Reports: `BL_*_<Theme>.report.json`

Orbital Analog scripts:

- Generator: `Tools/Blender/generate_orbital_analog_meter.py`
- Control generator: `Tools/Blender/generate_orbital_analog_controls.py`
- Validator: `Tools/Blender/validate_orbital_analog_meter.py`
- Control validator: `Tools/Blender/validate_orbital_analog_controls.py`

Forge Brass / Kinetic Safety scripts:

- Generator: `Tools/Blender/generate_remaining_themes.py`
- Validator: `Tools/Blender/validate_remaining_themes.py`

Throttle / power-slider scripts:

- Three-theme generator:
  `Tools/Blender/generate_throttle_power_controls.py`

Geminiレビュー反映済みの入れ替え候補:

- Generator:
  `Tools/Blender/generate_gemini_refined_candidates.py`
- Blender原本、preview、検証JSON:
  `ArtSource/Blender/Refined/<Theme>/`
- Unity確認用FBX:
  `Assets/MatsuMotoMeterAR/Content/RefinedCandidates/<Theme>/Models/`

Hard-surface V4 retopo candidates:

- Quality floor:
  `docs/3D_MODEL_QUALITY_FLOOR_V4.md`
- Kinetic Safety generator:
  `Tools/Blender/generate_hardsurface_kinetic_set_v4.py`
- Forge Brass / Orbital Analog generator:
  `Tools/Blender/generate_hardsurface_theme_variants_v4.py`
- Blender source, previews and reports:
  `ArtSource/Blender/HardSurfacePrototype/<Theme>/V4/`
- Unity candidate FBX:
  `Assets/MatsuMotoMeterAR/Content/RefinedCandidates/<Theme>/HardSurfacePrototype/V4/`

Blenderは通常のZ-up座標で制作する。

- Blender X → Unity X
- Blender Z → Unity Y
- Blender -Y outward → Unity +Z outward

FBXは`-Z Forward / Y Up`で出力する。UnityではScale Factor 1、Convert Units
ON、Generate Colliders OFF、Import Animation OFF、Material Import Noneを使う。
FBXをSpatial Anchor rootへ直接配置せず、visual prefabでwrapして
`InstrumentGreyboxContract.VisualSocket`直下へ置く。

再生成:

```sh
scripts/run-blender.sh --background --factory-startup \
  --python Tools/Blender/generate_orbital_analog_meter.py -- \
  --project-root "$PWD"

scripts/run-blender.sh --background --factory-startup \
  --python Tools/Blender/generate_remaining_themes.py -- \
  --project-root "$PWD"

scripts/run-blender.sh --background --factory-startup \
  --python Tools/Blender/generate_throttle_power_controls.py -- \
  --project-root "$PWD"

scripts/run-blender.sh --background \
  --python Tools/Blender/generate_gemini_refined_candidates.py -- \
  --project-root "$PWD"
```

検証:

```sh
scripts/run-blender.sh --background --factory-startup \
  --python Tools/Blender/validate_orbital_analog_meter.py -- \
  --project-root "$PWD"

scripts/run-blender.sh --background --factory-startup \
  --python Tools/Blender/validate_orbital_analog_controls.py -- \
  --project-root "$PWD"

scripts/run-blender.sh --background --factory-startup \
  --python Tools/Blender/validate_remaining_themes.py -- \
  --project-root "$PWD"
```

残り2テーマのvalidatorは12個すべてについて、root metadata、必須階層、
UV、camera/light/collider不在、triangle・renderer・material・外形予算、
4 texture map、FBX round-tripを検査する。

リファイン候補はUnityメニュー
`Tools > MatsuMotoMeterAR > Model Replacement >
Prepare and Validate All Candidates`でも一括検証する。本番FBX／Prefabは
この操作では上書きしない。

## Blender 5.2 non-destructive smoke test

最初の互換確認では原本を保存せず、FBXとJSON reportだけを一時directoryへ
出力する。次の例はOrbital AnalogのLeverを開き、root、mesh、triangle、material、
boundsとFBX出力を検査する。

```sh
analogmr_smoke_dir="$(mktemp -d)"
scripts/run-blender.sh --background --factory-startup \
  --python Tools/Blender/smoke_test_blender_52.py -- \
  --source ArtSource/Blender/ThemeHardSurfaceV6/OrbitalAnalog/BL_Lever_OrbitalAnalog_V6_ProductionReady.blend \
  --expected-root PF_Visual_Lever_OrbitalAnalog_V6 \
  --output-dir "$analogmr_smoke_dir"
```

代表モデルのsmokeが成功してから39個をstagingへ再生成する。本番FBX、Prefab、
`.meta`およびProductionReady Blendは、Unity validator、motion audit、contact
sheet比較が完了するまで上書きしない。

3テーマと代表的な可動／表示契約をまとめて検査する場合は次を使う。

```sh
scripts/run-blender-52-smoke.sh
scripts/run-blender-52-smoke.sh --all
```

出力先を固定する場合は`ANALOGMR_BLENDER_SMOKE_DIR`を指定する。suiteはLever、
MeterRound、Throttle、PowerSlider、StatusIndicator、WindowPanelの6件を検査する。
`--all`は13種類×3テーマのProductionReady Blend 39件を検査する。

代表suiteは共有PBR atlasをRetopo原本へ適用したEEVEE previewも一時出力する。
全件suiteは処理時間と成果物量を抑えるため、ProductionReady読込、構造集計、
Legacy FBX出力までを検査する。
