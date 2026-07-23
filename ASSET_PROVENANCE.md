# Asset provenance

The instrument meshes, PBR texture atlases, and preview renders in this
repository are original procedural project assets.

## Reproducible source

- Blender generators: `Tools/Blender/generate_*.py`
- Blender source files and previews: `ArtSource/Blender/`
- Unity FBX and texture outputs: `Assets/MatsuMotoMeterAR/Content/`
- Unity prefabs and materials: `Assets/MatsuMotoMeterAR/Resources/`
- Validation scripts: `Tools/Blender/validate_*.py`
- Machine-readable validation reports: `ArtSource/Blender/**/*.report.json`

The generators create geometry and texture data through Blender and Python.
They do not import third-party models, textures, fonts, audio, characters,
logos, or uploaded reference images.

The project uses general industrial-control and retro space-opera design
vocabulary. It does not include artwork, logos, characters, screenshots, or
reference images from any third-party work. Contributors must not add content
unless they have the right to publish it under the license stated in
`ASSET_LICENSE.md`.
