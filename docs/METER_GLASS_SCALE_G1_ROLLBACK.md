# MeterGlassScale G1 production rollback plan

Candidate `MeterGlassScale_G1` removes duplicate cover-glass scale meshes from
the Medium and Large meters in Orbital Analog and Forge Brass. Production
integration must remain one dedicated commit and must not modify Round meters,
shared materials, shared textures, or unrelated prefabs.

## Pre-integration active baseline

| Asset | SHA-256 |
| --- | --- |
| `Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Models/SM_MeterMedium_OrbitalAnalog.fbx` | `fb4801ece6197ab9b2912e21bc137c4c9458a25eec6128a2245e0939adcaf2ac` |
| `Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Models/SM_MeterLarge_OrbitalAnalog.fbx` | `d351d3a7a25380a7a76f1897bf3245ab71379b1c2fac32420887657dd50fda0b` |
| `Assets/MatsuMotoMeterAR/Resources/OrbitalAnalog/Prefabs/PF_Visual_MeterMedium_OrbitalAnalog.prefab` | `b21e3636b8621c2142777773ee96d37df34db81560450fd8ba19224d59df35f6` |
| `Assets/MatsuMotoMeterAR/Resources/OrbitalAnalog/Prefabs/PF_Visual_MeterLarge_OrbitalAnalog.prefab` | `f0b80e896d9e0ca7159c77928c90ab6e0bc05acdb8222af76023725ba37ed70d` |
| `Assets/MatsuMotoMeterAR/Content/Themes/ForgeBrass/Models/SM_MeterMedium_ForgeBrass.fbx` | `89aa5be6e8006181050862a11824992b28c0f75b5232dbd7f24cd97c57a18e39` |
| `Assets/MatsuMotoMeterAR/Content/Themes/ForgeBrass/Models/SM_MeterLarge_ForgeBrass.fbx` | `fdbb7068ef74f4e0c33b238a6c32c31e2534c95dcfbac18aba7a8046dc1c7e1d` |
| `Assets/MatsuMotoMeterAR/Resources/ForgeBrass/Prefabs/PF_Visual_MeterMedium_ForgeBrass.prefab` | `dbc1dc0ad6f69b8f4e13731036c7ed87a4d772cbccffbc588fa18a45ccec605d` |
| `Assets/MatsuMotoMeterAR/Resources/ForgeBrass/Prefabs/PF_Visual_MeterLarge_ForgeBrass.prefab` | `9dc1d32e8529c7d53f38f1ad68658c0ea6bd9a24f4ca9aa6e0bf575d5cc6d57c` |

The four active FBX `.meta` files must retain their existing GUIDs:

- Orbital Analog Medium: `2f3ef20c8ad294a3881977da015859da`
- Orbital Analog Large: `fe76e0633abf1451d87e08efe5bac463`
- Forge Brass Medium: `d1b71fc9d78624a1689daa9c631e1cab`
- Forge Brass Large: `de380be3bfe7847c3a9125aa4ff729e9`

## Integration boundary

1. Recompute the eight baseline hashes and stop if any differs.
2. Promote only the four listed FBXs and four corresponding active prefabs.
3. Preserve all existing `.meta` GUIDs and shared material references.
4. Run active prefab validation, motion audit, EditMode tests, and a production
   Quest smoke after promotion.
5. Record the promotion backup path and post-promotion hashes here.

## Rollback

Before promotion, rollback is simply to leave the isolated staging candidate
unused. After promotion, revert the single dedicated production-update commit,
then run active prefab validation and EditMode tests and verify that the eight
hashes above are restored. Keep the Blender sources, candidate FBXs, manifests,
reports, and staging evidence for diagnosis.

## Applied production state (2026-08-27)

Gate C reported 18/18 READY and the user accepted visual and performance checks
on Quest 3. The eight pre-integration hashes matched immediately before the
transaction. The recoverable local backup is:

`Builds/ModelReplacementBackups/MeterGlassScale_G1_20260827_111245`

| Asset | SHA-256 after promotion |
| --- | --- |
| `Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Models/SM_MeterMedium_OrbitalAnalog.fbx` | `c0e4b028fa19cd0f28d7f486a95eb60bff74286488f4d29389000db93d9c7474` |
| `Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Models/SM_MeterLarge_OrbitalAnalog.fbx` | `0a241cca9a946c1593d6044e5d76a96e963a742994778ad1a2877243000e54da` |
| `Assets/MatsuMotoMeterAR/Resources/OrbitalAnalog/Prefabs/PF_Visual_MeterMedium_OrbitalAnalog.prefab` | `b21e3636b8621c2142777773ee96d37df34db81560450fd8ba19224d59df35f6` |
| `Assets/MatsuMotoMeterAR/Resources/OrbitalAnalog/Prefabs/PF_Visual_MeterLarge_OrbitalAnalog.prefab` | `f0b80e896d9e0ca7159c77928c90ab6e0bc05acdb8222af76023725ba37ed70d` |
| `Assets/MatsuMotoMeterAR/Content/Themes/ForgeBrass/Models/SM_MeterMedium_ForgeBrass.fbx` | `bcd70858a86cd26757dd5d623ae25eaadaf3ddcaf765996998b4d2c187898693` |
| `Assets/MatsuMotoMeterAR/Content/Themes/ForgeBrass/Models/SM_MeterLarge_ForgeBrass.fbx` | `23b6be7d304c3ad667701cf4ece219fd093cd24ab0d4a914b7f9a8ebb73a67b4` |
| `Assets/MatsuMotoMeterAR/Resources/ForgeBrass/Prefabs/PF_Visual_MeterMedium_ForgeBrass.prefab` | `dbc1dc0ad6f69b8f4e13731036c7ed87a4d772cbccffbc588fa18a45ccec605d` |
| `Assets/MatsuMotoMeterAR/Resources/ForgeBrass/Prefabs/PF_Visual_MeterLarge_ForgeBrass.prefab` | `9dc1d32e8529c7d53f38f1ad68658c0ea6bd9a24f4ca9aa6e0bf575d5cc6d57c` |

Post-promotion checks:

- candidate dependencies: 0
- active prefab validation: PASS
- control motion audit: 16/16 PASS
- meter candidate motion audit: 4/4 PASS, 230° travel
- EditMode: 154/154 PASS
- production Concept Release APK build: PASS
- Quest install and launch: PASS
- active FBX GUIDs: unchanged
- active prefab YAML: unchanged (Unity-only float serialization noise removed)

The dedicated production-update commit containing this document is the single
Git revert target once committed.
