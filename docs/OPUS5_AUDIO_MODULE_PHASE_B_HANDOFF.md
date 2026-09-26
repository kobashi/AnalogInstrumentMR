# Opus 5 audio-module visual handoff — Phase B

Status: **Phase B complete and accepted for isolated Unity integration on 2026-09-05**

This document extends `docs/OPUS5_AUDIO_MODULE_VISUAL_HANDOFF.md`. The accepted
Orbital Analog Phase A family is the shape and layout baseline. Opus 5 owns only
the Blender source, FBX export, fixed candidate renders, and Blender-side audit
for this phase. Codex retains ownership of Unity import, runtime display binding,
prefabs/materials, Gate C, production promotion, documentation, git, and Quest
acceptance.

## 1. Authorized scope

Create the following 18 candidates:

- Forge Brass: Oscillator, Noise, LFO, Sequencer, Delay, Output
- Kinetic Safety: Oscillator, Noise, LFO, Sequencer, Delay, Output
- Machined Ergonomics: Oscillator, Noise, LFO, Sequencer, Delay, Output

Together with the accepted six Orbital Analog A1 candidates, this completes the
24-model Blender/FBX candidate set.

Write only under:

`ArtSource/Blender/BrushUp/Opus5/AudioModules_B1/`

Do not modify `Assets/`, `Builds/`, `Packages/`, `ProjectSettings/`, `docs/`,
the A1 output directory, production assets, or git state. Do not commit, push,
open a PR, import into Unity, or start production promotion.

## 2. Accepted Phase A decisions

- The Orbital Analog family direction is accepted as the shared functional
  layout baseline.
- Keep `parameter_index` as the moving pointer.
- Keep port transforms as empties with their existing custom properties; jack
  geometry may remain integrated into the faceplate.
- Keep function-specific display sizes. Do not force one screen size across all
  six module kinds. Preserve enough usable area for each dynamic display listed
  in the A1 handoff.
- Raised legend slabs are acceptable for Blender candidates. Codex may replace
  fine legends with an atlas or texture treatment during Unity integration.
- Deliberate shallow interpenetration used to prevent z-fighting/contact seams
  is accepted when it continues to pass the audit.
- Improve the Delay front-view silhouette in all four themes. For Orbital
  Analog, do not rewrite A1; demonstrate the intended improvement in B1 theme
  variants by stepping or offsetting the terrace/echo treatment in depth as well
  as height. It must remain distinct from Noise in front and grayscale views.
- Reframe `closeup_display` so the module identifier is not needlessly cropped
  when this can be done without weakening display inspection.

## 3. Frozen runtime contract

The complete contract in `docs/OPUS5_AUDIO_MODULE_VISUAL_HANDOFF.md` remains in
force, including:

- envelope `0.24 x 0.20 x 0.10 m`, mounting plane and axis mapping;
- maximum 5,000 triangles per module;
- maximum 9 Renderers and 3 semantic material roles;
- required root, housing, faceplate, display, knob, index, and port names;
- flat separate `display_surface` with no baked live value;
- no Collider, Animator, Camera, Light, audio component, script, or constraint
  in exported FBX;
- clear full-turn knob motion and front-reachable ports;
- readable input/output direction independent of color.

This audio-module-specific contract takes precedence over the lower generic
limits in older theme style guides. Do not redesign runtime controls or ports.

## 4. Theme directions

Read and follow these source guides without modifying them:

- `docs/FORGE_BRASS_STYLE_GUIDE.md`
- `docs/KINETIC_SAFETY_STYLE_GUIDE.md`
- `docs/MACHINED_ERGONOMICS_STYLE_GUIDE.md`

### Forge Brass

Use a dark cast-iron body, aged brass/copper functional framing, stepped rims,
short cylindrical details, restrained rivet/knurl vocabulary, and warm amber
display light. Preserve legibility and avoid transparent glass.

### Kinetic Safety

Use a graphite industrial panel, chamfered rectangular shrouds, substantial
corner/side guards, and limited orange/yellow safety accents. The silhouette
must not collapse into Forge Brass when viewed in grayscale.

### Machined Ergonomics

Use a light warm-grey two-piece molded body, anodized metal functional parts,
dark elastomer/gasket accents, consistent parting/shut lines, justified fastener
placement, and an original manufacturable assembly language. Use neutral white
to soft-cyan display light. Keep the display within the common envelope even if
its face is given a slight ergonomic viewing angle.

Do not borrow a recognizable product, film, or game design. Theme differences
must read through silhouette, construction, and grayscale value—not only color.

## 5. Naming and deliverables

Use deterministic names such as:

`SM_Audio<Kind>_<Theme>_B1.fbx`

where `<Kind>` is `Oscillator`, `Noise`, `LFO`, `Sequencer`, `Delay`, or
`Output`, and `<Theme>` is `ForgeBrass`, `KineticSafety`, or
`MachinedErgonomics`.

Produce:

- 18 clean-cage `.blend` files;
- 18 deterministically triangulated `.blend` files;
- 18 FBX files;
- front, oblique-left, oblique-right, display close-up, and port close-up render
  for every candidate;
- per-theme color and grayscale contact sheets;
- one cross-theme sheet comparing all four themes by module kind, using A1
  renders read-only for the Orbital Analog column;
- close-up legibility sheets;
- machine-readable per-candidate inspection reports, aggregate build summary,
  Tier A audit, file manifest, and SHA-256 hashes;
- `REPORT.md` describing counts, bounds, triangles, renderers, material roles,
  port transforms, audit results, deviations, and open decisions.

Do not retain Blender `.blend1` backup files in the final B1 deliverable tree.
Report the exact final file count and disk usage from the filesystem.

## 6. Acceptance and stop gate

Every one of the 18 FBXs must pass all applicable Tier A checks with no FAIL,
REVIEW, or unexecuted/N/A result counted as a pass. Visually verify:

- one coherent six-module family inside each theme;
- immediate theme separation in color and grayscale;
- immediate module-kind separation, especially Noise versus Delay;
- readable module identifiers, port legends, and direction glyphs;
- unobstructed display surfaces, knob range, and cable attachment points;
- no z-fighting, buried marks, contact seams, or envelope regression.

Fix failures inside B1 and regenerate dependent FBX, renders, sheets, hashes,
and reports. Then stop. Do not begin Unity or production work. Return a concise
completion report and the paths to the cross-theme, color, grayscale, and
legibility sheets for Codex review.
