# Instrument audio contract

Status: **implementation contract**

Prepared: 2026-09-03

## 1. Goal and boundary

Every production instrument has an `AudioSocket`. This feature makes that
socket functional while preserving existing instrument geometry, interaction
ranges, and scalar signal semantics. Modular patch persistence extends the
released schema-v7 contract to schema v8; editable module parameters extend it
to schema v9 with backward migration.

Audio is derived from the current instrument kind, theme, value, and display
state. Audio playback state is not persisted. Placement previews are silent.
Restored instruments initialize silently; continuous sounds may fade in only
after restoration has applied the saved value.

The first implementation is divided into independently reversible slices:

1. value-change provenance and the common audio runtime;
2. mechanical and state-transition one-shots;
3. meter rotation-like continuous sound;
4. Trend Monitor and Window Panel sonification;
5. optional Quest listening/interaction acceptance and an audio-specific
   performance scenario if device validation is reopened.

The Machined Ergonomics surface-stripe candidate is separate work and must not
be combined with this feature.

## 2. State-change provenance

`MockInstrumentMotion` reports an event only when its normalized value actually
changes after normalization. The event carries the previous and current values,
detent indices, motion kind, and one of these origins:

- `UserInteraction`: trigger, grip, or other direct operation;
- `SignalGraph`: evaluated connection or Window Panel input;
- `Restore`: saved placement restoration;
- `ThemeChange`: visual/theme rebinding;
- `Programmatic`: other explicit runtime calls.

Initialization does not emit a change event. `Restore` and `ThemeChange` never
produce one-shot sounds. Repeated assignment of the same normalized value never
produces an event or sound.

## 3. Instrument mappings

| Instrument | Trigger | Audio response |
| --- | --- | --- |
| Toggle Switch | OFF/ON transition | short, direction-distinct switch click |
| Lever | each of 5 detents | heavy mechanical detent; direction changes timbre |
| Throttle | each of 6 detents | low metallic ratchet; direction changes timbre |
| Power Slider | each of 11 detents | short dry sliding tick; direction changes timbre |
| Rotary Knob | each eighth-turn step | short rotary click |
| Push Button | press and release | distinct down/up clicks |
| Indicator Lamp | OFF/LOW/MID/HIGH transition | destination-stage relay/electronic cue with per-boundary hysteresis |
| Status Indicator | OFF/SAFE/WARN/DANGER transition | short state-distinct relay click |
| Round Meter, Medium, Large | normalized reading | smoothed rotation-like pitch and harmonic change |
| Window Meter | normalized reading | smoothed rotation-like pitch and harmonic change |
| Trend Monitor | composed value, slope, spread, valid inputs | continuous generated signal/roar texture |
| Window Panel | Energy, Balance, Phase, Detail, preset | continuous preset-dependent generated texture |
| Oscillator | parameter knob and future typed inputs | Sine/Triangle/Saw/Square audio source |
| Noise | parameter knob and future Gate input | deterministic White/Pink/Brown audio source |
| LFO | rate knob and typed output selection | 0.05–20 Hz bipolar modulation at Control or Audio rate |
| Sequencer | lower/upper knob half selects 8/16 steps; position within half selects 40–240 BPM | fixed bipolar step pattern with internal or external clock |
| Delay | parameter knob | 20–750 ms bounded wet delay with protected 42% internal feedback |
| Audio Output | parameter knob and Audio input | limited full-3D streaming output |

If one update crosses several detents, the runtime reports the final transition
without creating an unbounded burst. Direct physical motion normally crosses
one detent at a time and therefore produces one click per step.

## 4. Continuous sonification

### Meter

Normalized value monotonically raises the perceived rotation rate and pitch.
Pitch and gain use smoothing so signal discontinuities do not create clicks.
The stopped region fades toward silence. Meter sound must not alter needle
motion or signal output.

### Trend Monitor

- composed output controls base pitch and gain;
- output slope controls modulation depth and brightness;
- spread between valid inputs controls roughness/noise;
- valid input count controls harmonic density;
- no valid input fades to silence and is not treated as an alarm.

### Window Panel

- Energy controls gain;
- Balance controls harmonic balance rather than bypassing 3D spatialization;
- Phase controls modulation phase/rate;
- Detail controls upper harmonics and noise;
- Orbit, Rose, and Lissajous select synthesis topology and crossfade without a
  discontinuity.

All synthesis parameters must be finite and clamped. Audio-thread code must not
allocate managed memory, access Unity objects unsafely, or mutate signal state.

## 5. Theme and spatial contract

The semantic event is common across themes. Theme profiles may change pitch,
decay, damping, and harmonic balance while keeping the same trigger behavior.
Changing theme updates the profile silently and keeps `AudioSocket`, interaction,
normalized value, and continuous-audio phase intact.

Instrument audio is emitted from `AudioSocket` with full 3D spatial blend,
logarithmic distance attenuation, Doppler disabled, and a bounded maximum
distance. One-shots and continuous sounds use separate mixer categories. A
master limiter and a continuous-voice budget prevent clipping and an unbounded
48-object sound field.

## 6. Acceptance

- every one-shot occurs once per accepted state transition;
- no one-shot occurs during creation, preview, restoration, or theme rebinding;
- signal assignments that normalize to the existing state remain silent;
- lamp hysteresis prevents threshold chatter;
- meter pitch is finite, smoothed, and monotonic with value;
- Monitor and Panel become silent when their input is unavailable;
- four themes preserve the same trigger semantics;
- existing schema-v1 through schema-v8 fixtures and round trips remain valid;
- full EditMode, active-prefab validation, motion audit, and signal-visual audit
  pass;
- if Quest validation is reopened, interaction confirms spatial position,
  transition timing, useful level, and absence of audible discontinuities;
- any future audio performance verdict uses an audio-specific patched scenario
  that measures DSP/callback behavior. The generic 48/64-object rendering gate
  is not an audio acceptance substitute.

## 7. Candidate implementation status

The initial runtime candidate on `codex/instrument-audio-contract` implements:

- origin-aware value-change events and silent restore/theme rebinding;
- generated theme-tuned one-shots for the six controls and two indicator kinds;
- lamp activation hysteresis;
- allocation-free sample filling for Meter, Trend Monitor, and Window Panel;
- continuous Meter pitch mapping, Trend value/slope/spread/input mapping, and
  Window Panel Energy/Balance/Phase/Detail/preset mapping;
- full-3D AudioSources and a nearest-first limit of eight continuous voices;
- output clamping, value smoothing, gain fades, and Window Panel preset
  interpolation.
- instrument-kind sound profiles with distinct pitch, decay, overtone,
  duration, and transient characteristics;
- four-stage Indicator Lamp sound state with OFF/LOW/MID/HIGH cues and
  hysteresis at every boundary. A multi-stage jump emits one destination cue;
- Connect-mode typed Patch cables, cyan Audio / amber Control / violet Clock /
  magenta selected rendering,
  per-module patch cycling with A, and deletion with B.

Desktop structural validation on 2026-09-04:

- Unity EditMode: **291 / 291 PASS**;
- active visual prefabs: **56 / 56 PASS**;
- control motion: **16 / 16 PASS**;
- signal visuals: **8 / 8 PASS**.

Quest listening and interaction timing are deferred by product decision.
The existing 48-object Performance Gate measures frame timing, process-level
CPU/GPU utilization, memory, thermal state, frame GC, and stability, but it
does not create a representative modular patch topology or record DSP CPU,
audio callback duration, underruns, audio-thread allocation, or active voice
counts. It is therefore skipped for this audio slice and is not reported as
PASS. Desktop tests do not promote any of these device-only items to PASS.

## 8. Modular audio continuation

The modular audio system is an independently reversible feature slice. Its
DSP foundation is now part of the 291-test implementation. It keeps the
existing scalar graph unchanged while defining typed `Control`, `Gate`,
`Trigger`, `Clock`, and `Audio` ports.

Implemented foundation:

- fixed-capacity block renderer: 32 nodes, 64 typed connections, and 1024
  mono frames per block;
- graph compilation with duplicate-edge rejection and zero-delay cycle
  rejection;
- four-waveform Oscillator and LFO, deterministic White/Pink/Brown Noise,
  8/16-step Sequencer, protected Delay, and bounded Audio Output nodes;
- standard typed port catalogs for the six dedicated module kinds and three
  existing-instrument source kinds;
- sample-accurate Audio edges and block-rate sample-and-hold Control edges;
- sample-accurate Clock edges with rising-edge step advancement and automatic
  internal-clock fallback;
- preallocated Delay ring buffers, feedback clamped to 0.92, internal-state
  clamping, and delay-boundary cycle compilation;
- finite/clamped rendering, source mixing, output limiting, and verified 0 B
  managed allocation across warmed render calls.

Oscillator, Noise, LFO, Sequencer, Delay, and Audio Output are registered placement
kinds with stable `audio.oscillator`, `audio.noise`, `audio.lfo`,
`audio.sequencer`, `audio.delay`, and `audio.output` type IDs. They have
theme-colored code-contract visuals, parameter-knob motion, preview behavior,
theme rebinding, and normal placement-value persistence. Audio Output owns a
full-3D streaming player and an initially silent compiled graph. Schema v8
stores typed Audio Patch records independently from scalar Signal connections.
Schema v9 adds per-placement Oscillator/LFO waveform, Noise color, and the
16-value Sequencer pattern.
Connect mode can patch or re-route an Oscillator/Noise/LFO `audio.out` to an
Audio Output `audio.in`. An LFO can also drive Oscillator `pitch.in` through
`control.out`, or `fm.in` through `audio.out`; left-stick horizontal selects
Control or Audio rate before confirmation. Runtime builds the complete
upstream LFO → Oscillator → Output topology and rebuilds only when placements
or patch records change. Cables use cyan for Audio, amber for Control, and
magenta for the selected patch. LFO `clock.out` can drive Sequencer `clock.in`;
without that edge the Sequencer runs from its 40–240 BPM internal clock. Its
`control.out` drives Oscillator `pitch.in`, producing the full
LFO → Sequencer → Oscillator → Output chain. The parameter knob's lower half
selects 8 steps and upper half selects 16, while its position within that half
sets tempo. Clock cables are violet. With a module endpoint selected, A cycles its
patches and B deletes the selected patch transactionally. Deleting either
endpoint also removes its patches. Authored FBX prefabs remain deferred.

Delay accepts Audio at `audio.in`, optional LFO time modulation at `time.in`,
and emits `audio.out`. Its placement value maps monotonically to 20–750 ms;
initial feedback is 0.42 and is hard-limited to 0.92 in DSP. The ring buffer is
preallocated and both stored feedback state and output are clamped. Acyclic
routes use block rendering. If ordinary topological compilation finds a cycle,
the graph retries only across Delay input boundaries and uses sample-wise
rendering with one-sample causal state. Cycles without Delay remain invalid.

The existing readout objects are also typed sources without losing their
existing scalar Signal target role:

- Round Meter variants and Window Meter expose `value.out` (Control) and a
  value-dependent `audio.out` motor tone;
- Trend Monitor exposes `value.out`, signed `slope.out`, `spread.out`
  (Control), and a generated `audio.out` texture;
- Window Panel exposes `energy.out`, `balance.out`, `phase.out`, `detail.out`
  (Control), and a generated `audio.out` texture.

In Connect mode these dual-role instruments are selected once for their
existing Signal target/edit behavior and selected again to switch to Audio
Patch source behavior. Left-stick horizontal cycles their output ports. A
Control port routes to Oscillator `pitch.in` or Delay `time.in`; `audio.out`
routes to Oscillator `fm.in`, Delay `audio.in`, or Audio Output `audio.in`.
Unavailable Trend/Panel inputs produce silent texture output. Their typed
control values remain finite and clamped.

Editable dedicated modules expose a compact Connect-mode parameter editor.
Select an Oscillator, Noise, LFO, or Sequencer as Source and press Y. For
Oscillator/LFO, left-stick horizontal cycles Sine/Triangle/Saw/Square; for
Noise it cycles White/Pink/Brown. For Sequencer, left-stick horizontal selects
one of the active 8/16 steps and right-stick vertical adjusts its bipolar value
in 0.05 increments. Changes are audible while editing. A or left-stick press
saves; B restores the complete pre-edit parameter state. Saved values are
normalized before serialization and restored onto the existing DSP node.

Implementation order:

1. No further device work in the current slice. Quest listening is deferred.
2. If audio performance is reopened, first add an audio-specific scenario and
   measurements for patched DSP load, callback timing/underruns, audio-thread
   allocation, and active voices. Do not substitute the generic 48-object gate.

Zero-delay audio cycles are rejected. A feedback route is valid only when it
contains a Delay. Oscillator phase, live delay buffers, playing clicks, and
limiter state will not be persisted.

Latest Quest deployment evidence on 2026-09-04:

- audio review APK built successfully at
  `Builds/QuestReview/AnalogInstrumentMR-InstrumentAudio-review-quest3.apk`;
- installed successfully on the connected Quest 3;
- APK size: 94 MB; SHA-256:
  `57a9a21bedb1a344a3de0a8f17da29ee5755a26859f73791804136c9bf8ff00d`;
- automated launch reached the Quest controller-required system dialog; no
  application process or Unity exception was available before that dialog.

The headset must be worn and the controller-required dialog accepted before
the listening, interaction timing, and profiling items can be promoted.
