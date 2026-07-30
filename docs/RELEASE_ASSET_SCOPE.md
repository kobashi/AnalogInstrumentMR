# Release asset scope

GitHub source releases contain the files needed to open, build, validate, and
continue development of AnalogInstrumentMR without publishing every intermediate
model iteration.

## Included

- Runtime Unity assets under `Assets/MatsuMotoMeterAR/Content/Themes/`
- Active visual prefabs under `Assets/MatsuMotoMeterAR/Resources/`
- The 39 final V6 Blender sources matching
  `ArtSource/Blender/ThemeHardSurfaceV6/*/*_ProductionReady.blend`
- Final V6 model validation reports
- Source texture atlases under `ArtSource/Textures/`
- Blender, texture, validation, and documentation generator scripts
- Curated V6 contact sheets under `docs/images/`
- Design specifications, style guides, and release verification records

Binary model, texture, and preview assets are stored through Git LFS.

## Local-only development history

The following remain available in a developer's working copy but are excluded
from GitHub releases:

- V4 hard-surface experiments
- V5 silhouette experiments
- pre-V6 refined candidates
- V6 retopology, triangulation, material-preview, and replacement-staging copies
- internal AI-review document packages and temporary review captures
- generated APKs, build reports, logs, and Unity cache directories

Excluding these duplicates keeps the source release focused while preserving
the production model, its generator, and its validation evidence.
