# Blender source assets

Blender原本はUnityの`Assets`外で管理し、FBXとtextureだけをUnityへ渡す。

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
blender --background --factory-startup \
  --python Tools/Blender/generate_orbital_analog_meter.py -- \
  --project-root "$PWD"

blender --background --factory-startup \
  --python Tools/Blender/generate_remaining_themes.py -- \
  --project-root "$PWD"

blender --background --factory-startup \
  --python Tools/Blender/generate_throttle_power_controls.py -- \
  --project-root "$PWD"

blender --background \
  --python Tools/Blender/generate_gemini_refined_candidates.py -- \
  --project-root "$PWD"
```

検証:

```sh
blender --background --factory-startup \
  --python Tools/Blender/validate_orbital_analog_meter.py -- \
  --project-root "$PWD"

blender --background --factory-startup \
  --python Tools/Blender/validate_orbital_analog_controls.py -- \
  --project-root "$PWD"

blender --background --factory-startup \
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
