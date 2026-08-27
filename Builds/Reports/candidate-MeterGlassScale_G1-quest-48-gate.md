# MeterGlassScale G1 Quest 3 48-object acceptance gate

- Date: 2026-08-27
- Device: Quest 3 (`eureka`)
- Candidate: `MeterGlassScale_G1`
- APK: `Builds/QuestReview/AnalogInstrumentMR-MeterGlassScale_G1-review-quest3.apk`
- APK SHA-256: `0d18791779233bd63e07299ec5be1b9cb4ecb2ea3f9abf82a5ed14c0ee0bc554`

Result: **PASS — user-accepted Quest performance test**

The accepted APK contains the Medium and Large meter candidates for Orbital
Analog and Forge Brass. The change deletes only the duplicate
`secondary_scale_*` meshes: 17 marks from each Medium model and 25 from each
Large model. Renderer count remains 2, submesh count remains 4, and material
count remains 2 for every candidate; triangle counts strictly decrease.

Two host attempts to start the abbreviated automated 48-object capture were
blocked before the application started by the Quest system
`LaunchCheckControllerRequiredDialogActivity`. The corresponding host logs are
retained at:

- `Builds/Reports/perfgate-48-OrbitalAnalog-20260827-105730.log`
- `Builds/Reports/perfgate-48-OrbitalAnalog-20260827-105940.log`

They are diagnostic records, not failed application runs. The user subsequently
reported the performance test as PASS on the connected Quest 3. This explicit
device acceptance, together with the strictly reduced geometry and unchanged
renderer/material contract, is the acceptance decision for this localized
cleanup.
