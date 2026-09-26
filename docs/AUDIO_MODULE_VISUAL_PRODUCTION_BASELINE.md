# Audio module production baseline

Date: 2026-09-05

Candidate: `AudioModules_A1_B1`

Before initial production registration, all 24 target audio-module FBXs and all
24 target visual prefabs were absent from the four production theme folders.
The twelve dedicated production materials—Housing, FaceMetal, and
EmissionDisplay for each of the four themes—were also absent. Existing non-audio
production models, prefabs, materials, textures, and `.meta` files are outside
the promotion set and must remain unchanged.

Because this is initial registration rather than replacement, rollback before a
dedicated git commit is removal of only the newly created 24 FBXs, 24 prefabs,
12 materials, and their generated `.meta` files. The promotion tool performs
that removal automatically if validation fails during the operation.
