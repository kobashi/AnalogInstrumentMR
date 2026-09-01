# TrendMonitor Texture T1 rollback

Texture T1 promotion is limited to the three existing TrendMonitor production
prefabs, their housing/readout/display materials, and three 1K runtime maps per
theme. Geometry FBX files are not replaced.

Before writing, the dedicated promoter records every existing managed file and
its `.meta` file under
`Builds/ModelReplacementBackups/TrendMonitor_Texture_T1_<timestamp>/`.
New texture and display-material paths are recorded as initially absent.

If promotion validation fails, existing files are restored byte for byte and
new files are deleted. For a later regression, restore the timestamped backup
or revert only the Texture T1 production-promotion commit. Preserve the
candidate maps, manifest, reports, and fixed-camera images for diagnosis.

Managed production paths per theme:

- `Content/Themes/<Theme>/Textures/TrendMonitor/T_<Theme>_V6_TrendMonitor_T1_{BaseColor,Normal,MetallicSmoothness}.png`
- `Content/Themes/<Theme>/Materials/MAT_<Theme>_V6_TrendMonitor_{Opaque,Readout,Display}.mat`
- `Resources/<Theme>/Prefabs/PF_Visual_TrendMonitor_<Theme>.prefab`
