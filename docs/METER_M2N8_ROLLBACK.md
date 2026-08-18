# Meter M2n8 production rollback plan

Candidate `Meter_M2n8` remains isolated until Gate C is READY. Production integration must be a dedicated commit containing only the approved KineticSafety meter FBX/prefab replacement and directly required metadata updates.

## Pre-integration active baseline

| Asset | SHA-256 |
| --- | --- |
| `Assets/MatsuMotoMeterAR/Content/Themes/KineticSafety/Models/SM_MeterRound_KineticSafety.fbx` | `9a1edbb88413b37de0b1c08230bf4ba6e172025c0cada064d2f3744a9aa77c2d` |
| `Assets/MatsuMotoMeterAR/Content/Themes/KineticSafety/Models/SM_MeterMedium_KineticSafety.fbx` | `57a3e26edd470daabc8d420604dc3b206a6a47306169ec581f79eb570314f853` |
| `Assets/MatsuMotoMeterAR/Content/Themes/KineticSafety/Models/SM_MeterLarge_KineticSafety.fbx` | `da50d76de2729b78cd1a19b45cd2b63cb3c52a677f145846209a0937bc97b0ac` |
| `Assets/MatsuMotoMeterAR/Resources/KineticSafety/Prefabs/PF_Visual_MeterRound_KineticSafety.prefab` | `cd018690fd0225896b9340282ca41fbe95405967b9285d225563af955a22d8b1` |
| `Assets/MatsuMotoMeterAR/Resources/KineticSafety/Prefabs/PF_Visual_MeterMedium_KineticSafety.prefab` | `8d164a62575ec38ddd7df1f93a1530eaad9967aac34e71ae9c8a165006efdf15` |
| `Assets/MatsuMotoMeterAR/Resources/KineticSafety/Prefabs/PF_Visual_MeterLarge_KineticSafety.prefab` | `7fa4da920447cd24466acb9f2381498babb8bb647f43502993f9a24bb2705eb3` |

The three active FBX `.meta` files must retain their existing GUIDs. Shared KineticSafety materials and textures are not part of the M2n8 replacement and must not change in the production-update commit.

## Integration boundary

Before creating the production-update commit:

1. Recompute the six active hashes above and stop if they differ.
2. Confirm the production-update diff contains only the three KineticSafety meter FBXs, three active prefabs, required manifest/release documentation, and no unrelated shared-worktree changes.
3. Run active prefab validation, meter motion audit, EditMode tests, fixed-camera review, and Quest smoke after replacement.
4. Record the production-update commit SHA in this document or the release note.

## Rollback procedure

If a post-integration regression is found, revert only the dedicated production-update commit. Do not delete the M2n8 Blender source, candidate FBXs, reports, isolated staging assets, or Gate C evidence. Re-run active prefab validation and EditMode tests after the revert, then confirm the six active hashes match this baseline.

Before a production-update commit exists, rollback requires no active asset operation: keep `Meter_M2n8` in isolated staging and leave production unchanged.

## Applied production state (2026-08-18)

The user authorized production promotion after Gate C reported 16/16 PASS. The pre-integration hashes above matched before any active file was written. The local recoverable backup is:

`Builds/ModelReplacementBackups/Meter_M2n8_20260818_173501`

| Asset | SHA-256 after promotion |
| --- | --- |
| `Assets/MatsuMotoMeterAR/Content/Themes/KineticSafety/Models/SM_MeterRound_KineticSafety.fbx` | `9f32dd5e72a1e0f9ee0c2a2c91c9ba5abb08fba5858a7016bef456f340e2d916` |
| `Assets/MatsuMotoMeterAR/Content/Themes/KineticSafety/Models/SM_MeterMedium_KineticSafety.fbx` | `c7707591299ea9675746f7819f2b6fe5e28e4b71fa6b4d30803f30c992a47f57` |
| `Assets/MatsuMotoMeterAR/Content/Themes/KineticSafety/Models/SM_MeterLarge_KineticSafety.fbx` | `a4e81579fba1d31e4723ae25c95ea91ac323e6ffe77323ff76b7cc192e0249e6` |
| `Assets/MatsuMotoMeterAR/Resources/KineticSafety/Prefabs/PF_Visual_MeterRound_KineticSafety.prefab` | `ac9fcea7d55f9e722d0aa3cf3733d4d28a9b89ad4eea17930bb19107b5ac7287` |
| `Assets/MatsuMotoMeterAR/Resources/KineticSafety/Prefabs/PF_Visual_MeterMedium_KineticSafety.prefab` | `aac00cf27f912abbdc51d798fa218bfcf8ac690ead20224fc01b4508e23921d3` |
| `Assets/MatsuMotoMeterAR/Resources/KineticSafety/Prefabs/PF_Visual_MeterLarge_KineticSafety.prefab` | `706cf53783070ef26ee98044fd03d5e62cedb660900a229ce3f13290db1695e8` |
| `Assets/MatsuMotoMeterAR/Content/Themes/KineticSafety/Materials/MAT_KineticSafety_Meter_Solid_Opaque.mat` | `ab150998f3dd26d0a58bd08798be3eb35dfd41e3687e028466f5a6535beb0cb6` |
| `Assets/MatsuMotoMeterAR/Content/Themes/KineticSafety/Materials/MAT_KineticSafety_Meter_Solid_Readout.mat` | `76172390602ba49f6b137f0e8c2509e4a2b16cddd42defc7b267b025a54f017a` |

The three FBX and three prefab `.meta` GUIDs remained unchanged. The two new meter-specific solid materials reproduce the accepted isolated-review material contract without referencing candidate-staging assets or modifying shared atlas materials.

Post-promotion checks:

- active prefab validation: 39/39 PASS
- promoted meters: 4,640 / 6,096 / 6,880 triangles; 3 renderers; 4 submeshes; 2 materials
- fixed-camera active/candidate parity review: PASS
- EditMode: 133/133 PASS
- production smoke APK build and ZIP integrity: PASS
- Quest install / launch: PASS
- Quest production visual smoke: PASS (Round flicker, Medium/Large ticks and ring clearance, min/max endpoints, OFF/ON materials)

Quest smoke was accepted by the user on 2026-08-18. The dedicated production-update commit is the commit containing this document; use that commit as the single revert target.
