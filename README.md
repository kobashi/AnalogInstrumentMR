# AnalogInstrumentMR

An experimental Unity 6 Mixed Reality project for placing modular analog
instruments and physical controls on walls, floors, and ceilings on Meta Quest.
Placed objects use Spatial Anchors for local persistence and can switch among
three original visual themes without recreating their anchor roots.

This is an independent, unofficial open-source project. It is not affiliated
with or endorsed by Meta, Unity, any artist, studio, publisher, or other rights
holder. No third-party logos, characters, artwork, screenshots, or uploaded
reference images are included. `MatsuMotoMeterAR` remains in some internal
Unity paths and namespaces as a historical development identifier.

## Project status

The `v0.1.0-concept.5-perfgate` source release includes:

- six object types: round meter, lever, toggle, rotary knob, push button, and
  status lamp
- three original themes: Orbital Analog, Forge Brass, and Kinetic Safety
- ray/direct interaction, haptics, and logical-state persistence
- schema-v1 storage for up to 24 placements, legacy migration, and targeted
  deletion
- Meta Spatial Anchor localization and multi-object restoration
- 12/24/40-object synthetic performance scenarios

Quest 3 verification passed the 24-object, 72 Hz, 10-minute performance gate,
three-theme smoke tests, three-anchor restart restoration, and normal-use user
acceptance. Quest 3S physical verification was intentionally deferred. See
[`docs/releases/v0.1.0-concept.5-perfgate.md`](docs/releases/v0.1.0-concept.5-perfgate.md).

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

## Requirements

- Unity `6000.3.19f1`
- Unity Android Build Support
- Android SDK & NDK Tools and OpenJDK installed through Unity Hub
- Git LFS
- Blender for regenerating or validating art source
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
5. [`ArtSource/Blender/README.md`](ArtSource/Blender/README.md)

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
