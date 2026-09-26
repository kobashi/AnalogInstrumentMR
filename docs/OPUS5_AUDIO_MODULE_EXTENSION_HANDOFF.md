# Opus 5 audio-module extension visual handoff

Status: **Phase A/B accepted; Unity Gate C candidate promoted to production**

Prepared: 2026-09-10

Dispatched: 2026-09-10 to the existing shape-refinement task
`AnalogInstrumentMR v0.3 開発目標`. Phase A and Phase B were subsequently
accepted, transferred to this worktree with supplied hashes intact, and
integrated as isolated candidate `AudioModules_Ext_A1_B1` on 2026-09-11.

Unity integration branch/worktree:

- branch: `codex/audio-module-visuals`
- worktree: `/Users/kblab/.codex/worktrees/9772/AnalogInstrumentMR`

Opus shape-refinement checkout:

- `/Users/kblab/Documents/AnalogInstrumentMR`

This document extends `OPUS5_AUDIO_MODULE_VISUAL_HANDOFF.md`. If the earlier
handoff disagrees with this document for the six module kinds listed below,
this document takes precedence.

## 1. Objective and scope

Create dedicated, readable FBX visuals for four newly implemented modules and
bring two existing module visuals up to the current Gate/Trigger port contract.
The Phase A family contains six Orbital Analog candidates:

- new `audio.vca` / `AudioVca`;
- new `audio.mixer` / `AudioMixer`;
- new `audio.filter` / `AudioFilter`;
- new `audio.envelope` / `AudioEnvelope`;
- revised `audio.lfo` / `AudioLfo` with Gate and Trigger output jacks;
- revised `audio.sequencer` / `AudioSequencer` with Gate and Trigger output
  jacks.

Do not make only the four new modules. The current accepted LFO and Sequencer
FBXs predate the routed `gate.out` and `trigger.out` ports, so the two revised
assets are part of the same acceptance gate.

Opus 5 owns Blender shape, topology, UV/layout, deterministic FBX export, and
candidate renders. Codex owns Unity import, runtime binding, validators,
production promotion, documentation, git, and Quest acceptance.

## 2. Approved execution plan

### Phase A — Orbital Analog visual gate

Create the six Orbital Analog candidates above as one family. The VCA, Mixer,
Filter, and Envelope must have distinct functional silhouettes. LFO and
Sequencer must retain the accepted family identity while gaining the required
physical Gate/Trigger jacks and legends.

Stop after the editable/triangulated Blender sources, FBXs, audit reports, and
fixed candidate renders are complete. Do not begin the other themes until
Codex and the user accept this six-module family.

### Phase B — remaining themes, only after Phase A acceptance

Adapt the accepted shapes to:

- Forge Brass;
- Kinetic Safety;
- Machined Ergonomics.

Phase B will contain 18 candidates. It must not be started during Phase A.

### Phase C — Unity integration, owned by Codex

After all candidates pass their visual and structural gates, Codex will extend
the candidate validator and manifest, import the candidates in isolation, bind
both runtime surfaces, create theme prefabs/materials, render comparison sheets,
promote the accepted assets, run EditMode tests, and build/test on Quest.

## 3. Frozen geometry and runtime contract

Every candidate must obey all of the following:

- Unity envelope: `0.24 x 0.20 x 0.10 m` (`X x Y x Z`).
- Origin: center of the mounting plane.
- Mounting plane: local `Z = 0`; outward direction: local `+Z`.
- Geometry may not extend behind the mounting plane by more than `1 mm`.
- Blender/Unity mapping: Blender `X -> Unity X`, Blender `Z -> Unity Y`,
  Blender `-Y -> Unity +Z`.
- FBX export: `-Z Forward / Y Up`, unit scale in metres.
- Root scale in Unity: `(1, 1, 1)`.
- Maximum `5,000` triangles per module.
- Target maximum `9` Renderers and `3` semantic material roles. Unity's hard
  greybox ceiling is 10 Renderers; using the tenth requires an explicit REVIEW
  note and Codex approval.
- No Collider, Animator, Camera, Light, audio component, script, or constraint
  in the FBX.
- Existing placement type IDs, normalized values, Audio Patch records,
  interaction collider, and `AudioSocket` must not change.
- The parameter knob rotates around local `Z` through one full turn. Geometry
  and legends must remain clear throughout that rotation.

Required transform/mesh names:

- `audio_module_root`
- `housing`
- `faceplate`
- `display_bezel`
- `display_surface`
- `signal_surface`
- `parameter_knob_pivot`
- `parameter_knob`
- `parameter_index`

Each required name must occur exactly once.

### Display surface

`display_surface` must be a separate flat rectangular mesh facing local `+Z`,
with exactly two triangles and finite UV0 spanning approximately `0..1` in U
and V. Keep it separate from its bezel. Codex replaces its temporary material
with a runtime-generated display; do not bake live values into the texture.

### Signal-flow surface

`signal_surface` must be a separate flat mesh and Renderer, distinct from
`display_surface`, facing local `+Z`. It must have usable triangles and finite
UV0 spanning approximately `0..1` in U and V. It must share the same
`EmissionDisplay` material role as `display_surface`. Codex draws the animated
signal-flow texture at runtime. Do not model a tall fixed arrow or bake a live
flow state into it.

## 4. Frozen port contract

Use one front-reachable named port transform/mesh for every catalog port.
Replace dots with underscores.

- VCA: `port_audio_in`, `port_level_in`, `port_audio_out`
- Mixer: `port_audio_in`, `port_audio_out`
- Filter: `port_audio_in`, `port_cutoff_in`, `port_audio_out`
- Envelope: `port_gate_in`, `port_trigger_in`, `port_control_out`
- revised LFO: `port_rate_in`, `port_reset_in`, `port_control_out`,
  `port_clock_out`, `port_gate_out`, `port_trigger_out`, `port_audio_out`
- revised Sequencer: `port_clock_in`, `port_control_out`, `port_gate_out`,
  `port_trigger_out`

Important Mixer constraint: the single `port_audio_in` accepts multiple logical
patch cables. Do not invent four physical input-port names.

Leave enough space between ports for visible cable plugs and routing. Make
input/output direction readable by position, inward/outward glyph, or jack-ring
treatment; do not rely on color alone.

Candidate render colors:

- Audio: cyan;
- Control: amber;
- Clock: violet;
- Gate: green;
- Trigger and Reset: orange.

Gate and Trigger are live routed domains now. The earlier handoff's neutral/dim
Gate/Trigger treatment is superseded.

## 5. Module-specific visual intent

### VCA

- Engraved identifier: `VCA`.
- Legends: `IN`, `LEVEL`, `OUT`.
- Distinct motif: converging/attenuating signal and a controlled amplitude
  window or rising-level bars.
- Primary knob: manual level.
- Display area must accommodate `MAN`/`CV`, ten rising bars, and a horizontal
  level bar.

### Mixer

- Engraved identifier: `MIX` or `MIXER`.
- Legends: `IN`, `OUT`.
- Distinct motif: several activity paths converging into one bus/output.
- Primary knob: master gain.
- Display area must accommodate four compact channel activity bars and one
  master bar.
- Do not add four named input sockets; the runtime has one multi-cable logical
  input.

### Filter

- Engraved identifier: `LPF` or `FILTER`.
- Legends: `IN`, `CUTOFF`, `OUT`.
- Distinct motif: low-pass slope/cutoff arc and a restrained resonance-ring
  treatment.
- Primary knob: cutoff.
- Display area must accommodate a low-pass response curve with resonance bump,
  cutoff frequency in Hz, and a horizontal cutoff bar.
- Resonance is edited through the shared parameter UI in this revision. Do not
  add a second required physical knob.

### Envelope

- Engraved identifier: `ADSR` or `ENV`.
- Legends: `GATE`, `TRIG`, `CTRL`.
- Distinct motif: rise/hold/fall contour that is legible in silhouette and
  grayscale.
- The shared parameter knob is the physical primary control and manual gate
  action. The display shows current stage, level percentage, ADSR contour, and
  horizontal level bar.
- Do not add four functional A/D/S/R knobs. Those parameters are edited through
  the shared parameter editor in the current runtime.

### revised LFO

- Retain the accepted LFO silhouette, waveform/phase display area, knob
  clearance, and established Orbital Analog family language.
- Add distinct front jacks and labels for `GATE` and `TRIG` without crowding or
  shrinking the display beyond normal Quest legibility.
- Preserve `display_surface` geometry and UV behavior needed for the runtime
  DSP-phase hairline. Do not bake a phase marker.
- Do not remove or rename `RATE`, `RESET`, `CTRL`, `CLK`, or `AUDIO`.

### revised Sequencer

- Retain the accepted Sequencer silhouette and the display area sized for the
  compact `2 x 8` step grid.
- Add distinct front jacks and labels for `GATE` and `TRIG`.
- Do not add sixteen physical sliders/buttons; step editing remains in the
  runtime interaction UI.
- Do not remove or rename `CLK` or `CTRL`.

## 6. Common visual language and themes

- Keep the mounting footprint and primary knob scale consistent with the
  accepted six-module family.
- The four new module kinds must not read as one common box distinguished only
  by labels or port count.
- Preserve legibility in grayscale through silhouette, bezel, guard, jack
  layout, position, and glyphs.
- Use short ASCII legends. Avoid tiny paragraph text, third-party logos,
  copyrighted likenesses, and recognizable replicas of real products.
- Target readability at approximately `0.6-1.0 m` Quest viewing distance.
- Material roles are exactly `Housing`, `FaceMetal`, and `EmissionDisplay`.
  Small accents must reuse those materials/atlas regions.

Orbital Analog Phase A direction:

- dark spacecraft-console housing;
- softly rounded or circular instrument framing;
- off-white/gray face inserts;
- restrained red/orange/green/cyan accents;
- dense but readable analog-electronic panel rhythm;
- an original design matching the already accepted Orbital Analog audio family.

Future Phase B themes must extend their current production family identity,
not recolor Orbital Analog:

- Forge Brass: cast mass, stepped rims, serviceable brass retention structure;
- Kinetic Safety: chamfered guards, robust protected controls, limited warning
  accents;
- Machined Ergonomics: lightweight two-part machined/molded construction,
  rational touch clearances, and restrained parting/shut lines.

## 7. Phase A output location and deliverables

In the original Opus checkout, write only under:

`ArtSource/Blender/BrushUp/Opus5/AudioModules_Ext_A1/`

Required output:

- six editable clean-cage `.blend` sources;
- six deterministically triangulated `.blend` files;
- six candidate `.fbx` files;
- front, left-oblique, and right-oblique fixed renders for each module;
- one six-module color contact sheet and one grayscale contact sheet;
- one close-up sheet proving display, signal-flow, port, and legend legibility;
- one JSON report per module containing Blender version, source/output hashes,
  triangle count, Renderer/submesh count, material slots and semantic roles,
  node names, Unity-space bounds, UV0 results, non-manifold count,
  degenerate-face count, and FBX round-trip result;
- `REPORT.md` with exact file list, hashes, audit tally, limitations, and REVIEW
  items.

Suggested candidate names:

- `SM_AudioVca_OrbitalAnalog_ExtA1.fbx`
- `SM_AudioMixer_OrbitalAnalog_ExtA1.fbx`
- `SM_AudioFilter_OrbitalAnalog_ExtA1.fbx`
- `SM_AudioEnvelope_OrbitalAnalog_ExtA1.fbx`
- `SM_AudioLFO_OrbitalAnalog_ExtA1.fbx`
- `SM_AudioSequencer_OrbitalAnalog_ExtA1.fbx`

Run the accepted Opus5 Tier A audit on every FBX. Report each result as
`PASS / FAIL / REVIEW / N/A`; never count N/A or an unexecuted check as PASS.

## 8. Prohibited actions

During Phase A, Opus 5 must not:

- write outside `ArtSource/Blender/BrushUp/Opus5/AudioModules_Ext_A1/`;
- modify any existing audio-module source package, especially
  `AudioModules_R2_A4_OA1`;
- modify `Assets/`, `Builds/`, docs, production/delivery FBX, prefabs,
  materials, textures, `.meta` files, tools, tests, or git state;
- install an add-on, Python package, font, material library, or external tool;
- begin Phase B, Unity import, production promotion, commit, push, PR, APK, or
  Quest work;
- reinterpret a `REVIEW` result as PASS.

## 9. Phase A stop gate

Stop immediately after all six Phase A candidates, reports, audits, and fixed
renders are complete. Reply with:

1. exact changed/generated file list;
2. triangle, Renderer, submesh, and material-role summary;
3. required-node and port-node result table;
4. Tier A audit result table;
5. contact-sheet absolute paths and SHA-256 values;
6. Blender-source, triangulated-source, and FBX hashes;
7. deviations, REVIEW items, and unresolved decisions.

Do not continue to another theme or modify production assets while waiting for
Codex and user review.

## 10. Codex acceptance notes

The current Unity candidate validator still describes the previously accepted
six-module port list. Codex will update it only during Phase C, after the new
candidates exist, so the active production LFO/Sequencer assets are not made to
fail prematurely.

Phase C acceptance must verify at least:

- exact common nodes and exact ports above;
- display/signal surfaces, UVs, materials, and front normals;
- envelope, origin, scale, triangle, Renderer, and material budgets;
- knob full-turn clearance;
- display and signal-flow runtime binding for all four new modules;
- LFO/Sequencer Gate/Trigger cable origin alignment;
- color and grayscale identification across all four themes;
- focused EditMode tests and Quest visual/interaction smoke.

## 11. Unity integration and production result

The isolated Gate C integration completed on 2026-09-11:

- candidate manifest: `AudioModules_Ext_A1_B1`, schema 2, Gate C;
- 24 unique entries: VCA, Mixer, Filter, Envelope, revised LFO, and revised
  Sequencer across all four themes;
- eight LFO/Sequencer entries carry explicit replacement lineage to
  `AudioModules_A1_B1`;
- source `SHA256SUMS.txt`: Ext-A1 PASS and Ext-B1 PASS;
- Unity staging/contract validation: 24/24 PASS;
- cross-candidate dependencies: 0;
- five-state motion audit: 24/24 PASS;
- focused EditMode: 19/19 PASS;
- full EditMode: 341/341 PASS;
- Gate C readiness: READY, 58/58 checks PASS; Quest 48/64 checks remain
  explicitly deferred by the existing Quest deferral record.

Evidence is indexed in
`Builds/Reports/candidate-AudioModules_Ext_A1_B1-source-integrity.md` and
`Builds/Reports/candidate-AudioModules_Ext_A1_B1-gate-c-readiness.md`. The two
GPU review sheets are the candidate-only 24-module shape sheet and the
four-theme runtime display/signal-flow sheet in `Builds/Reports`.

Production promotion was explicitly requested and completed on 2026-09-12:

- 24 production FBXs/prefabs applied across four themes;
- VCA, Mixer, Filter, and Envelope registered for the first time;
- LFO and Sequencer replaced with the revised Gate/Trigger geometry;
- active prefab validation: PASS;
- production candidate dependencies: 0;
- pre-promotion classification/boundary tests: 11/11 PASS;
- post-promotion production/budget tests: 2/2 PASS;
- post-promotion full EditMode: 351/351 PASS;
- rollback backup:
  `Builds/ModelReplacementBackups/AudioModules_Ext_A1_B1_20260912_053258`.

The 24-instrument static Renderer ceiling is now 103, equal to the measured
worst case: 101 accepted Kinetic Safety visual Renderers plus two runtime
Renderers. No spare headroom was added. This is a static content-budget check,
not the deferred audio-specific Quest stress profile.

The promoted APK was built and installed on Quest 3 on 2026-09-12:

- APK SHA-256:
  `84d568bff976cb644f5ed07ab6fde7201d7c5b21a3be56e808e7fd74db798280`;
- actual size: 81,348,551 bytes;
- `adb install -r`: Success;
- device update time: `2026-09-12 21:40:01`;
- automated launch: held by Quest's controller-required dialog;
- application/Unity crash entry: none.

On 2026-09-18 the controller check was cleared. The promoted APK was foreground
with a stable PID, no application/Unity crash or sampled error entry, and no
increase in application AudioFlinger or spatial-renderer underrun counters over
15 seconds. The product owner reported no issue with the new module visuals,
revised ports, operation, or sound. Representative audio-inclusive load stress
remains deferred; the short smoke sample is not a substitute for it.

The product owner subsequently declared the audio-load test **PASS** on
2026-09-18. This closes product acceptance by user decision, while the
representative graph and 48/64-object quantitative stress measurements remain
unexecuted; they are not reported as measured PASS.
