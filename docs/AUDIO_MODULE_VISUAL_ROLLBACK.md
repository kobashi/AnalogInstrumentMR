# Audio module visual rollback plan

Candidate: `AudioModules_A1_B1`

Latest promoted extension: `AudioModules_Ext_A1_B1`

The extension promotion completed on 2026-09-12. Its auditable backup is
`Builds/ModelReplacementBackups/AudioModules_Ext_A1_B1_20260912_053258` and
contains 56 files: the displaced LFO/Sequencer FBXs and prefabs for four themes,
the shared audio-module materials, and their `.meta` files.

To roll back the extension before a dedicated commit, restore those 56 files
to their repository-relative paths, then remove only the newly registered VCA,
Mixer, Filter, and Envelope production FBXs/prefabs and their `.meta` files
(16 models and 16 prefabs across four themes, counting assets without their
`.meta` companions). Preserve the isolated candidate and reports. Finally run
active prefab validation and the full EditMode suite.

## Original A1/B1 registration

This is an initial production registration: no earlier audio-module production
asset is overwritten. The pre-promotion state is recorded in
`docs/AUDIO_MODULE_VISUAL_PRODUCTION_BASELINE.md`. Production promotion completed
on 2026-09-05. Its auditable backup directory is
`Builds/ModelReplacementBackups/AudioModules_A1_B1_20260905_075531`; it contains
no displaced production assets because all 60 registered assets were new.

Before a dedicated git commit, rollback means removing only the newly registered
24 FBXs, 24 prefabs, twelve materials, and their generated `.meta` files. The
isolated candidate and reports remain reproducible evidence.

If the promoted files are committed and a regression appears later, revert only
that production-update commit, retain the A1/B1 Blender sources and isolated
candidate evidence, then rerun active prefab validation, full EditMode tests,
and the audio-inclusive Quest checks.

Do not delete or overwrite the source handoff, and do not change placement type
IDs, normalized values, `AudioSocket`, Audio Patch records, or persistent module
parameters during rollback.
