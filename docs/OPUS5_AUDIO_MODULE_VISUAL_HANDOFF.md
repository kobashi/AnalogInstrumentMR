# Opus 5 audio-module visual handoff

Status: **Phase A/B/C accepted; production integration and automated Quest smoke complete on 2026-09-05**

Prepared: 2026-09-05

Branch: `codex/audio-module-visuals`

## 1. Objective

Replace the shared procedural greybox appearance of the six dedicated audio
modules with readable, theme-specific FBX candidates. The object itself must
communicate module kind, current parameter, port role, and signal flow at normal
Quest viewing distance.

The six module kinds are:

- `audio.oscillator`
- `audio.noise`
- `audio.lfo`
- `audio.sequencer`
- `audio.delay`
- `audio.output`

Opus 5 owns Blender shape, topology, UV/layout, FBX export, and candidate renders.
Codex owns the Unity display runtime, materials, prefab construction, validators,
production promotion, documentation, git, and Quest acceptance.

## 2. Approved execution plan

### Phase A — one-theme family candidate

Create all six modules for **Orbital Analog only**. They must read as one family
while remaining identifiable by silhouette and front-panel composition. Stop
after Blender/FBX validation and fixed candidate renders. Do not begin the other
themes until Codex and the user accept the family direction.

### Phase B — theme expansion

The accepted six-module family was adapted to Forge Brass, Kinetic Safety, and
Machined Ergonomics. Together with Orbital Analog, the 24 Blender/FBX candidates
were accepted for isolated Unity integration on 2026-09-05.

### Phase C — Unity integration

Codex imported the candidates into isolated staging, bound the dynamic display,
created theme prefabs/materials, ran structural and motion validation, and
rendered the fixed-camera candidate sheet. Results are recorded in
`docs/OPUS5_AUDIO_MODULE_PHASE_C.md`. The accepted candidate was subsequently
promoted to all 24 active production prefabs and passed post-promotion validation.

## 3. Frozen runtime contract

Every candidate must obey all of the following:

- Unity envelope: `0.24 × 0.20 × 0.10 m` (`X × Y × Z`).
- Origin: center of the mounting plane.
- Mounting plane: local `Z = 0`; outward direction: local `+Z`.
- Geometry may not extend behind the mounting plane by more than `1 mm`.
- Blender/Unity mapping: Blender `X → Unity X`, Blender `Z → Unity Y`,
  Blender `-Y → Unity +Z`.
- FBX export: `-Z Forward / Y Up`, unit scale in metres.
- Root scale in Unity: `(1, 1, 1)`.
- Maximum `5,000` triangles per module.
- Maximum `9` Renderers and `3` semantic material roles.
- No Collider, Animator, Camera, Light, audio component, script, or constraint in
  the FBX.
- The existing placement type IDs, normalized values, Audio Patch records,
  interaction collider, and `AudioSocket` must not change.
- The parameter knob rotates around local `Z` through one full turn. Geometry
  must remain clear of the housing throughout that rotation.

Required transform/mesh names:

- `audio_module_root`
- `housing`
- `faceplate`
- `display_bezel`
- `display_surface`
- `parameter_knob_pivot`
- `parameter_knob`
- `parameter_index`

`display_surface` must be one flat rectangular mesh, separate from the bezel,
facing local `+Z`. Codex will replace its temporary Blender material with a
runtime-generated display. Do not bake live values into its texture.

Use one named port transform/mesh for every catalog port. Replace dots with
underscores:

- Oscillator: `port_pitch_in`, `port_gate_in`, `port_fm_in`, `port_audio_out`
- Noise: `port_gate_in`, `port_audio_out`
- LFO: `port_rate_in`, `port_reset_in`, `port_control_out`, `port_clock_out`,
  `port_audio_out`
- Sequencer: `port_clock_in`, `port_control_out`
- Delay: `port_audio_in`, `port_time_in`, `port_audio_out`
- Audio Output: `port_audio_in`

Ports must be reachable from the front and leave enough separation for a visible
connection cable. Input/output direction must be readable by an inward/outward
glyph or jack-ring treatment without relying only on color.

## 4. Common visual language

- Keep one mounting footprint and knob scale across the family.
- Give each module a distinct upper silhouette, bezel, or guard arrangement;
  port count alone is not sufficient identification.
- Put a short engraved identifier on the faceplate: `OSC`, `NOISE`, `LFO`,
  `SEQ`, `DLY`, or `OUT`.
- Use short ASCII port legends matching the port names. Avoid small paragraph
  text and do not use copyrighted logos or recognizable product designs.
- Reserve a large, dark, high-contrast display near the upper half and keep the
  parameter knob reachable without covering the display.
- Preserve legibility in grayscale through shape, position, and glyphs.
- Audio ports use a cyan ring, Control uses amber, and Clock uses violet in the
  candidate render. Gate and Trigger/Reset ports remain neutral/dim with etched
  `G` and `T` identifiers because their runtime routing is not yet enabled.
- Material roles are `Housing`, `FaceMetal`, and `EmissionDisplay`. Small color
  differences should share materials/atlas regions rather than create extra
  material slots.

Orbital Analog direction for Phase A:

- dark spacecraft-console housing;
- softly rounded or circular instrument framing;
- off-white/gray face inserts;
- restrained red/orange/green/cyan accents;
- dense but readable analog-electronic panel rhythm;
- original design with no direct borrowing from a specific film, game, or
  historical product.

## 5. Dynamic display content to accommodate

Opus provides the physical display area and fixed legends. Codex will implement
the following live display after the FBX candidate is accepted.

### Oscillator

- active Sine/Triangle/Saw/Square waveform glyph;
- frequency readout over the current `55–1760 Hz` range;
- knob position arc;
- `PITCH`, `GATE`, `FM`, and `OUT` port legends.

### Noise

- active `WHITE`, `PINK`, or `BROWN` state;
- output-level bar for the current `0.02–0.35` range;
- `GATE` and `OUT` legends.

### LFO

- active waveform glyph;
- `0.05–20 Hz` rate readout;
- animated phase marker;
- `RATE`, `RESET`, `CTRL`, `CLK`, and `AUDIO` legends.

### Sequencer

- sixteen steps as a compact `2 × 8` grid within one display surface;
- active step, selected step, and bipolar step value;
- `8/16` step mode and `40–240 BPM` readout;
- `CLK` and `CTRL` legends.

### Delay

- `20–750 ms` time readout;
- echo/tap spacing graphic;
- `IN`, `TIME`, and `OUT` legends;
- do not add Feedback or Mix knobs in this revision; those controls are future
  scope and remain fixed in the current runtime.

### Audio Output

- gain readout over the current `0–200%` range;
- compact output level meter area;
- one `IN` legend;
- a restrained grille/radiating-wave motif may distinguish the silhouette, but
  it must not imply that the mesh itself emits audio.

## 6. Phase A deliverables

Write only under:

`ArtSource/Blender/BrushUp/Opus5/AudioModules_A1/`

Required output:

- six editable clean-cage `.blend` sources;
- six deterministically triangulated `.blend` files;
- six candidate `.fbx` files;
- front, left-oblique, and right-oblique renders for each module;
- one six-module color contact sheet and one grayscale contact sheet;
- one close-up sheet proving port-label and display-area legibility;
- one JSON report per module containing Blender version, input/source hashes,
  triangle count, object/node names, bounds, material roles, non-manifold count,
  degenerate-face count, and FBX round-trip result;
- a compact `REPORT.md` with file hashes and known limitations.

Suggested candidate names:

`SM_Audio<Kind>_OrbitalAnalog_A1.fbx`

where `<Kind>` is `Oscillator`, `Noise`, `Lfo`, `Sequencer`, `Delay`, or `Output`.

Run the accepted Opus5 Tier A audit on each FBX. Report results as
`PASS / FAIL / REVIEW / N/A`; do not count N/A or unexecuted checks as PASS.

## 7. Prohibited actions

Opus 5 must not:

- write anywhere outside `ArtSource/Blender/BrushUp/Opus5/AudioModules_A1/`;
- modify `Assets/`, `Builds/`, production/delivery FBX, prefabs, materials,
  textures, `.meta` files, existing tools, documentation, or git state;
- install an add-on, Python package, font, material library, or external tool;
- use generated third-party logos or copyrighted product likenesses;
- start Phase B, Unity import, production promotion, commit, push, or PR work;
- reinterpret a `REVIEW` result as PASS.

## 8. Stop gate

Stop immediately after the six Phase A candidates, reports, audits, and fixed
renders are complete. Reply with:

1. exact changed/generated file list;
2. triangle/material/renderer-node summary;
3. audit result table;
4. contact-sheet paths and SHA-256 values;
5. FBX/source hashes;
6. deviations, REVIEW items, and unresolved decisions.

Do not continue to another theme or modify production assets while waiting for
Codex and user review.
