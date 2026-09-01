# TrendMonitor ThemeShapes T1 rollback

Production promotion is limited to the TrendMonitor FBX, two role materials,
and generated visual prefab for OrbitalAnalog, ForgeBrass, and KineticSafety.
The promotion tool creates an auditable timestamped rollback location under
`Builds/ModelReplacementBackups/TrendMonitor_ThemeShapes_T1_<timestamp>/`
before writing production assets.

Affected active paths:

- `Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/Models/SM_TrendMonitor_OrbitalAnalog.fbx`
- `Assets/MatsuMotoMeterAR/Content/Themes/ForgeBrass/Models/SM_TrendMonitor_ForgeBrass.fbx`
- `Assets/MatsuMotoMeterAR/Content/Themes/KineticSafety/Models/SM_TrendMonitor_KineticSafety.fbx`
- the corresponding three `PF_Visual_TrendMonitor_<Theme>.prefab` files under `Assets/MatsuMotoMeterAR/Resources/`
- the corresponding `MAT_<Theme>_V6_TrendMonitor_Opaque.mat` and
  `MAT_<Theme>_V6_TrendMonitor_Readout.mat` files

T1 is the first production registration of these assets in the three themes,
so its initial timestamped location is intentionally empty: there was no prior
FBX, prefab, material, or `.meta` file to copy. If validation fails during
promotion, the tool deletes every newly created managed path automatically. If
a later regression is found, revert only the production-promotion commit (or
delete the listed assets and their `.meta` files). A later replacement of T1
will back up the then-existing files normally. Preserve the T1 candidate tree,
manifest, and evidence for diagnosis.
