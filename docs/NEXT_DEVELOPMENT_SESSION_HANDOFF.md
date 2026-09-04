# Next development session handoff

Status: **instrument-audio implementation is committed and ready for the next session**

Prepared: 2026-09-04

Released baseline: `v0.3.0-concept.1` at
`368676403e21ca0295d4f20fda335adae272f688`

Implementation parent commit: `6e4c1967080dc72bd873b6f46beaf95c3256b327`
(`Prepare next development session handoff`)

Current branch: `codex/instrument-audio-contract`

## 1. Current repository state

The instrument-audio slice is implemented, verified, reviewed, and committed in
the commit containing this handoff. Begin the next session by confirming that the
working tree is clean and that the current branch contains this handoff.

Do not select a new version, update the changelog, create a PR, push, or tag a
release without an explicit instruction. The immutable released baseline remains
`v0.3.0-concept.1`.

`Assets/Resources/DevAgentSettings.asset` is an ignored local credential/settings
asset. Never inspect, print, stage, or publish its contents. After the latest
Quest build, the original path exists and the temporary quarantine path does not.

## 2. Product decisions

The following scope is approved and implemented:

- Give each instrument type a distinct operating sound.
- Use short click-like sounds for Switch ON/OFF, Lever, Slider steps, and
  Lamp/Indicator illumination.
- Vary Indicator/Lamp sound by level or stage.
- Synthesize display-dependent sound for Monitor and Panel.
- Give Meter a rotating-machine-like pitch response driven by its value.
- Add a modular audio system with oscillator, noise, LFO, sequencer, delay, and
  audio output nodes.
- Allow Meter, Trend Monitor, and Window Panel outputs to feed the modular audio
  graph while retaining their existing control-signal role.
- Persist modular audio parameters and connections.

The following validation decisions are also current:

- Physical Quest listening and controller-operation acceptance is deferred.
- The generic 48-object performance gate is skipped for this slice because it
  does not measure the requested audio-specific load. This is **SKIPPED**, not
  PASS.
- If performance work is reopened, measure representative modular topology,
  DSP/callback CPU, underruns, audio-thread allocation, and active voice counts.

## 3. Implemented audio behavior

### Instrument one-shots

- Switch ON and OFF use distinct short cues.
- Lever and Slider steps trigger short mechanical cues.
- Lamp and Indicator transitions use stage-dependent cues.
- Instrument theme/type influences the synthesis so device families do not all
  sound identical.
- Cues are synthesized at runtime; no external audio assets are required.

### Continuous instrument sources

- Meter exposes its value as a control output and a value-dependent motor tone
  as an audio output. Pitch changes with the meter value.
- Trend Monitor exposes value, signed slope, and spread as control outputs plus
  a display-driven audio texture.
- Window Panel exposes energy, balance, phase, and detail as control outputs plus
  a display-driven audio texture.

### Modular audio nodes

- Oscillator: selectable waveform.
- Noise: selectable noise color.
- LFO: selectable waveform and control-rate modulation output.
- Sequencer: fixed 16-step editable pattern.
- Delay: audio processing node.
- Audio Output: terminal playback node.

The graph uses typed ports and preserves existing signal connections. Invalid
audio/control connections are rejected by the connection contract.

## 4. Connect-mode interaction

Meter, Trend Monitor, and Window Panel have dual source roles:

- Select once to use the existing control-signal source role.
- Select the same source again to switch to its audio source role.
- Use the left stick to cycle the available typed outputs.

For Oscillator, Noise, LFO, and Sequencer parameters:

1. Select the module as the Connect-mode source.
2. Press `Y` to enter parameter editing.
3. Move the left stick horizontally to change waveform/noise color, or to select
   a sequencer step.
4. Move the right stick vertically to change the selected sequencer value in
   increments of `0.05`.
5. Press `A` or the left-stick click to save.
6. Press `B` to cancel and restore the original values.

Changes audition immediately. Cancel and save failure both restore the prior
runtime parameter state.

## 5. Persistence and compatibility

- Current placement schema: **v9**.
- v8 and earlier placements migrate forward with safe audio defaults.
- v9 persists per-placement `audioWaveform`, `audioNoiseColor`, and
  `audioSequencerSteps`.
- Sequencer persistence is normalized to a fixed 16-step pattern.
- Runtime restoration applies saved parameters to the recreated audio nodes.
- Existing Room ownership, placement restoration, control connections, and
  schema v1-v8 migrations remain supported.

Key contract documents:

- [`INSTRUMENT_AUDIO_CONTRACT.md`](INSTRUMENT_AUDIO_CONTRACT.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)

## 6. Verification evidence

Latest completed checks:

- Modular audio focused EditMode tests: **38 / 38 PASS**.
- Placement/schema focused EditMode tests: **31 / 31 PASS**.
- Full EditMode suite: **291 / 291 PASS**.
- `git diff --check`: PASS.

Latest full-suite artifacts:

- Results: `/private/tmp/analog-module-params-full-tests.xml`
- Log: `/private/tmp/analog-module-params-full-tests.log`

Earlier unchanged structural baselines remain:

- Active visual prefabs: **56 / 56**.
- Control motion audit: **16 / 16**.
- Signal visual audit: **8 / 8**.

The documentation was changed after the 291-test run; production code was not.
There is no reason to rerun Unity solely for the handoff edit.

## 7. Quest build evidence

Latest review APK:

`Builds/QuestReview/AnalogInstrumentMR-InstrumentAudio-review-quest3.apk`

SHA-256:

`57a9a21bedb1a344a3de0a8f17da29ee5755a26859f73791804136c9bf8ff00d`

The APK was installed to Quest 3 device `2G0YC1ZG2J02HL`, and a launch event was
injected successfully. This proves build/install/launch plumbing only. It does
not count as in-headset interaction, listening, spatial-audio, or comfort
acceptance.

## 8. Remaining closeout work

No required implementation, review, or commit work remains in the approved
slice. Possible next actions are:

1. Choose version/changelog treatment only if the user opens a release task.
2. Push or open a PR only if requested.

Deferred work, not blockers for this slice:

- In-headset controller-operation and listening acceptance.
- Audio-specific Quest profiling under a representative modular graph.
- Optional Gate/Trigger/Reset semantics.
- Optional Delay feedback/mix and LFO depth controls.
- Optional additional FBX/audio-module visual assets.
- Broader output fan-out or advanced routing semantics.

## 9. Source-of-truth order

When older notes disagree, use this order:

1. This handoff for current worktree state and remaining actions.
2. [`INSTRUMENT_AUDIO_CONTRACT.md`](INSTRUMENT_AUDIO_CONTRACT.md) for the audio
   behavior, interaction, validation, and deferral decisions.
3. Current runtime/editor code and tests.
4. [`ARCHITECTURE.md`](ARCHITECTURE.md) for system structure.
5. [`releases/v0.3.0-concept.1.md`](releases/v0.3.0-concept.1.md) for the last
   released baseline.

Historical roadmap/alignment documents may contain superseded schema versions,
test totals, and open-task lists. Do not treat them as the current audio status.

## 10. Suggested continuation prompt

> Continue AnalogInstrumentMR on branch `codex/instrument-audio-contract`.
> Read `docs/NEXT_DEVELOPMENT_SESSION_HANDOFF.md` and
> `docs/INSTRUMENT_AUDIO_CONTRACT.md`, then inspect the current committed audio
> implementation and verify that the worktree is clean.
> Preserve all existing user changes and never inspect
> `Assets/Resources/DevAgentSettings.asset`. The instrument-audio slice is
> implemented; full EditMode is 291/291 PASS and the Quest review APK hash is
> recorded in the handoff. Physical Quest listening/interaction is deferred,
> and the generic 48-object performance gate is SKIPPED because it is not an
> audio-load measurement. Do not push, open a PR, change versioning, or tag
> unless explicitly instructed.
