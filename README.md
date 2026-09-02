# AnalogInstrumentMR

The Quest application is displayed as `AnalogInstrumentMR`. Its legacy Android
package identifier remains `com.DefaultCompany.MatsuMotoMeterAR` so upgrades
retain saved placement data and permissions.

An experimental Unity 6 Mixed Reality project for placing modular analog
instruments and physical controls on walls, floors, and ceilings on Meta Quest.
Placed objects use Spatial Anchors for local persistence and can switch among
four visual themes without recreating their anchor roots.

This is an independent, unofficial open-source project. It is not affiliated
with or endorsed by Meta, Unity, any artist, studio, publisher, or other rights
holder. No third-party logos, characters, artwork, screenshots, or uploaded
reference images are included. `MatsuMotoMeterAR` remains in some internal
Unity paths and namespaces as a historical development identifier.

## Project status

The latest published pre-release is `v0.2.0-concept.1`. The `main` development
baseline is preparing the proposed `v0.3.0-concept.1` release candidate. It
adds Blender 5.2 authoring support, manifest-driven candidate Gate C
validation, four production themes, signal monitors, editable connection
parameters, parametric Window Panels, and explicit multi-input composition.

The application includes:

- 14 instrument types in four functional categories: meters, indicators,
  switches, and motion controls
- 56 authored visual prefabs: 14 instrument types in each of Orbital Analog,
  Forge Brass, Kinetic Safety, and Machined Ergonomics
- Operation, Edit, and Connect modes
- two-hand beam/trigger interaction, contact buttons, and grip-motion lever,
  throttle, and power-slider controls
- placement on any usable face of an MRUK Plane or Volume
- overlap avoidance, grid/nearby alignment, multi-selection, move,
  directional rotation, distribution preview, and confirmation
- type-colored Direct, Invert, Range, and Threshold signal connections
- Quest-side Range and Threshold parameter editing, with preview, cancel,
  save, and restore
- a four-input Trend Monitor with per-input history and a separate composed
  output trace
- a four-input Window Panel with Energy, Balance, Phase, and Detail slots and
  Orbit, Rose, and Lissajous graphic presets
- target-selectable Average, Sum, Minimum, Maximum, and Priority composition
- schema-v7 persistence for up to 48 placements per Room, 192 placements
  across all Rooms, and 192 connections, including Room UUID ownership,
  connection parameters, display settings, composition settings, and runtime
  Current Room switching
- shared Spatial Anchors, restoration, and automatic re-anchoring

The current development baseline passes all 220 Unity EditMode tests, 56 active
visual-prefab checks, 16 control-motion checks, and 8 signal-visual checks.
Quest 3 passed the Machined Ergonomics 48-object 30-minute stability gate, the
shortened 64-object 10-minute stress characterization, Trend Monitor display
profiling, multi-input composition, Window Panel interaction, four-theme
switching, and restart restoration. Quest 3S remains unverified. The candidate
assessment is recorded in
[`docs/releases/v0.3.0-concept.1.md`](docs/releases/v0.3.0-concept.1.md).

The proposed next-development priorities are documented in
[`docs/V0_3_DEVELOPMENT_ROADMAP.md`](docs/V0_3_DEVELOPMENT_ROADMAP.md).

This repository distributes source only. It does not provide or support an
official APK, store build, production package identifier, or production
signing key.

## Get the complete source

The Blender, FBX, texture, and preview assets use Git LFS. Clone with Git LFS
rather than relying on GitHub's automatically generated source archive:

```sh
git lfs install
git clone https://github.com/kobashi/AnalogInstrumentMR.git
cd AnalogInstrumentMR
git lfs pull
```

Tagged releases also provide a separately named `full-source` archive with the
LFS objects included. No APK is included in that archive.

## Requirements

- Unity `6000.3.19f1`
- Unity Android Build Support
- Android SDK & NDK Tools and OpenJDK installed through Unity Hub
- Git LFS
- Blender `5.2.x` for regenerating or validating art source
- A developer-enabled Quest and USB debugging only for device testing

Unity Package Manager restores the pinned Unity and Meta XR dependencies from
`Packages/manifest.json`. Those dependencies are not covered by this project's
open-source licenses; review [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Open, test, and build

1. Add this repository root to Unity Hub and open it with `6000.3.19f1`.
2. Allow Package Manager to resolve the pinned dependencies.
3. Run `Tools > MatsuMotoMeterAR > Run EditMode Tests`.
4. For a local Quest build, switch the active target to Android / Meta Quest.
5. Run `Tools > MatsuMotoMeterAR > Build Concept Release APK`.

The local build uses the project's development package identifier and Android
debug signing unless you configure your own values. Generated APKs and logs are
ignored by Git.

For environment setup, USB debugging, MRUK, and Quest procedures, start with:

1. [`docs/MR_FOUNDATION_SETUP.md`](docs/MR_FOUNDATION_SETUP.md)
2. [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
4. [`docs/GREYBOX_INSTRUMENT_SPEC.md`](docs/GREYBOX_INSTRUMENT_SPEC.md)
5. [`docs/MODEL_REPLACEMENT_WORKFLOW.md`](docs/MODEL_REPLACEMENT_WORKFLOW.md)
6. [`docs/RELEASE_ASSET_SCOPE.md`](docs/RELEASE_ASSET_SCOPE.md)
7. [`ArtSource/Blender/README.md`](ArtSource/Blender/README.md)

## Asset provenance

The included meshes and textures are procedurally authored by the generator
scripts in this repository. See [`ASSET_PROVENANCE.md`](ASSET_PROVENANCE.md)
for the source/output map and contribution requirements.

## Licenses

- Code, Unity scenes/settings, and authoring scripts:
  [MIT](LICENSE)
- Original models, textures, prefabs, previews, and documentation:
  [CC BY 4.0](ASSET_LICENSE.md)
- Unity, Meta XR, OpenXR, Blender, and other dependencies:
  their respective licenses, summarized in
  [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

Contributions are described in [`CONTRIBUTING.md`](CONTRIBUTING.md). Security
reports should follow [`SECURITY.md`](SECURITY.md).
