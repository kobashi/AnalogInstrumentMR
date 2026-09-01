# Window Panel WP3-r2 rollback plan

Status: candidate-only; production promotion has not started.

## Current rollback boundary

`WindowPanel_WP3_r2` is isolated under
`Assets/MatsuMotoMeterAR/Content/RefinedCandidates/CandidateStaging/WindowPanel_WP3_r2/`.
Removing the candidate staging directory and its generated review APK restores
the pre-candidate runtime because production FBX, prefabs, and materials are
unchanged.

## Promotion prerequisites

Before any production write, capture a backup manifest containing path, GUID,
and SHA-256 for each affected Window Panel FBX, prefab, and material. Promotion
must be atomic across all four themes and preserve the current production
assets until the replacement validates successfully.

## Rollback after a future promotion

Restore every asset and `.meta` file from the promotion backup, refresh Unity,
run active-prefab validation and the full EditMode suite, then rebuild the
normal Quest review APK. Do not use the generic candidate promoter until its
Window Panel orientation, `display_surface`, and fourth-theme handling are
explicitly validated.
