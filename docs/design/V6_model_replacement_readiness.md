# V6 model replacement readiness

## State

V6 is active in the production theme FBX files and `Resources` prefabs. The
isolated staging area remains available for later replacement passes.

## Prepared assets

- 39 production-ready Blender sources:
  `ArtSource/Blender/ThemeHardSurfaceV6/<Theme>/BL_<Object>_<Theme>_V6_ProductionReady.blend`
- 39 triangulated staging FBX files:
  `Assets/MatsuMotoMeterAR/Content/RefinedCandidates/<Theme>/ThemeHardSurfaceV6Material/`
- 39 Unity staging prefabs:
  `Assets/MatsuMotoMeterAR/Content/RefinedCandidates/V6ReplacementStaging/<Theme>/Prefabs/`
- Three texture-density classes per theme: standard instruments, medium
  `MeterMedium`, and large `MeterLarge`/`WindowMeter`/`WindowPanel` objects.
- Each density class has a shared opaque and emissive URP material pair.
  Individual objects still use no more than two materials.

## Runtime contracts

- Root prefab name remains `PF_Visual_<Object>_<Theme>`.
- Motion nodes retain the existing names used by `ThemeVisualManifest`.
- Button exports now contain the required `button` movable node.
- Status indicators retain independent `status_safe`, `status_warn`, and
  `status_danger` renderers.
- Static parts and each movable island are merged. Most instruments use two
  renderers; status indicators use four.
- Mesh UVs are remapped into the shared 2x2 atlas:
  body top-left, metal top-right, gasket bottom-left, readout bottom-right.
- Materials are collapsed to the runtime budget of opaque plus emissive.
- Standard, medium, and large atlases repeat body/metal detail 3/5, 5/8, and
  8/12 times so surface marks retain a comparable apparent physical size.
- Normal strength is reduced to 0.32, 0.28, and 0.24 as model size increases
  to prevent coarse relief under close Quest lighting.
- `MeterMedium` uses a 2x front scale and 1.55x depth scale; `MeterLarge` uses
  a 3x front scale and 2.05x depth scale. Both add size-specific frames,
  secondary scales, seated fasteners, and theme-specific service structures.
- The staging prefab builder moves visuals in front of the mount plane without
  modifying model pivots.

## Validation

Run:

1. `Tools/MatsuMotoMeterAR/Model Replacement/Build V6 Staging Prefabs`
2. `Tools/MatsuMotoMeterAR/Model Replacement/Validate V6 Staging Prefabs`

Latest report:
`Builds/Reports/v6-staged-visual-prefab-validation.md`

All 39 staged prefabs pass hierarchy, motion target, renderer, material,
triangle, bounds, and mount-plane checks.

## Production replacement checklist

1. Back up the active model/prefab GUID mapping.
2. Copy staged FBX files to the active theme model paths while retaining the
   active `.meta` files.
3. Promote the V6 opaque and emissive materials to the active theme material
   paths.
4. Rebuild the 39 active `Resources` prefabs and their
   `ThemeVisualManifest` references.
5. Promote the V6 bounds envelopes to
   `InstrumentGreyboxSpecification` so placement margins match the refined
   visuals.
6. Validate active prefabs, then build and inspect on Quest.
