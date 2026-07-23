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
