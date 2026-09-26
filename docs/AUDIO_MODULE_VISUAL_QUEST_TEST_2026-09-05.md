# Audio module visual Quest 3 test — 2026-09-05

Candidate: `AudioModules_A1_B1`

Result: **automated device smoke PASS after one device-only defect was fixed**

## Artifact and device

- APK: `Builds/QuestReview/AnalogInstrumentMR-InstrumentAudio-review-quest3.apk`
- SHA-256: `c86d9cd5c617af4e7cbeb2b75cd40429e67ac510fb92f7b9f534af23d3666ad4`
- Package: `com.DefaultCompany.MatsuMotoMeterAR`
- Version: `0.3.0` (`versionCode 3`)
- Device: Quest 3 `2G0YC1ZG2J02HL`
- Install: `adb install -r` PASS
- Cold launch: PASS (`TotalTime: 175 ms`, `WaitTime: 218 ms`)

The process remained alive and foreground-resumed with the headset awake. The
runtime restored 19 / 19 active placements, including three saved audio-module
placements.

## Defect found and corrected

The first device launch produced four UV-access errors and two vertex-access
errors from `AudioModuleDisplayView.EnsureDisplayUv`. The production FBX model
importers had Read/Write disabled, which is permitted in the Editor but prevents
CPU mesh-channel access in an Android Player build.

The production builder now enables `ModelImporter.isReadable` only for the 24
audio-module FBXs. A regression test verifies every production audio-module
importer. After reimport, rebuild, reinstall, and cold restart:

- UV access errors: 0
- vertex access errors: 0
- Unity exception lines: 0
- Android fatal exceptions: 0
- full EditMode suite: 297 / 297 PASS

## Audio and resource snapshot

- App audio track: active, 24 kHz stereo, per-track underruns 0
- Spatial audio renderer `num_render_underruns`: 0
- Total PSS: 483,369 KB
- Total RSS: 645,806 KB
- Instantaneous app CPU: 51.8% in Android `top` on a six-core 600% scale
- Thermal status: 0 (no throttling)
- Highest sampled CPU sensor: 42.69 °C
- Highest sampled GPU sensor: 39.83 °C

The Android mixer exposes accumulated device-wide counters; these are not
attributed to this application and are not used as acceptance evidence.

## Still requiring a person in the headset

This automated smoke does not establish visual legibility, reachability,
controller interaction, sound character, loudness, spatial impression, or
comfort. It exercised the three audio modules already present in saved placement
data, not every module/theme combination. A representative 48-object acceptance
run and 64-object audio stress run also remain pending.

## Connect role/selection fix deployment

A follow-up APK was built and installed after correcting Connect-mode source-role
switching and mixed connection selection.

- APK SHA-256:
  `8ef1a333e79b182941d26ec9cfa84ce523f6b9df68164347a3d805f3bbdf768d`
- Install on Quest 3 `2G0YC1ZG2J02HL`: PASS
- Package/version check: `0.3.0` (`versionCode 3`)
- Full EditMode suite: 299 / 299 PASS
- Fatal Android/Unity errors during the attempted launch: 0

The headset screen was off during the post-install automation. Quest intercepted
both launcher and direct-Activity attempts with its controller-required launch
check, so the process did not remain running. This is an environment state, not
an application crash. Put on/wake the headset and launch the installed app before
performing the controller acceptance steps below:

1. In Connect mode, select a Meter, Trend Monitor, or Window Panel as Source.
2. Release the right trigger, keep aiming at the same Source, and press it again.
   Confirm the HUD changes from `CONTROL SIGNAL` to `AUDIO PATCH` and initially
   selects `AUDIO.OUT`.
3. Press the same Source again and confirm it returns to `CONTROL SIGNAL` without
   losing an already selected Target.
4. With Audio Output, Trend Monitor, or Window Panel selected, press `A`
   repeatedly and confirm signal connections and audio patches can both be
   selected; `B` must delete only the currently displayed item.

## Adjustable parameter deployment — 2026-09-10

The worktree build containing adjustable control/audio parameter ranges was
installed over USB on Quest 3 `2G0YC1ZG2J02HL`.

- APK: `Builds/QuestReview/AnalogInstrumentMR-InstrumentAudio-review-quest3.apk`
- SHA-256: `a3b17df13b26433ca59eab94ceec9cdc2850d1245874d9c5652b20a0838f5d28`
- APK size: 79,287,463 bytes
- Unity Android build: PASS
- `adb install -r`: **Success**
- Package/version: `com.DefaultCompany.MatsuMotoMeterAR` / `0.3.0` / `versionCode 3`
- Device update time: `2026-09-10 10:06:31`
- Crash buffer after install/launch request: no entries

The launch request was intercepted by Quest's
`LaunchCheckControllerRequiredDialogActivity`; the application PID was absent.
The controller-required check must be acknowledged while wearing the headset
before runtime interaction and audio acceptance can begin.

## Gate/Trigger source deployment — 2026-09-10

The latest worktree build adds LFO/Sequencer Gate and Trigger outputs, typed
output-port selection, and editable Gate Length.

- APK SHA-256:
  `6dfa1fc7647005c2f4074b0270b38f76e1e009f4df86f4f5cb2548455c7ee7c8`
- APK size: 79,295,871 bytes
- Unity Android build: PASS
- Install on Quest 3 `2G0YC1ZG2J02HL`: **Success**
- Package/version: `com.DefaultCompany.MatsuMotoMeterAR` / `0.3.0` /
  `versionCode 3`
- Device-reported update time: `2026-09-10 17:43:39`
- Crash buffer after launch request: no entries

Automated launch was again intercepted by the controller-required check, so
the process PID was not present. Headset interaction and audio acceptance are
still pending.

### Launch follow-up — 2026-09-10 19:13 JST

After the headset controller check was acknowledged, the same APK launched
successfully:

- Foreground activity: `UnityPlayerGameActivity`
- Application PID: `7243`
- Device state: `mWakefulness=Awake`
- Five-second stability check: process remained alive
- Crash/fatal Unity log scan: no entries
- Spatial renderer `num_render_underruns`: 0

AudioFlinger raw underrun counters are device-wide and are not attributed to
this application.

### Gate/Trigger interaction acceptance

Product-owner acceptance was recorded on 2026-09-10 with the requested
Gate/Trigger headset checks treated as confirmed:

- LFO and Sequencer Gate/Trigger output selection: PASS
- Envelope, Oscillator/Noise Gate, and LFO Reset patching: PASS
- Gate/Trigger cable colors: PASS
- Gate Length editing, save, and restore: PASS

This is a user-confirmed acceptance decision, separate from the automated
launch, crash-log, and renderer-underrun evidence above.

## Brown Noise/LFO correction deployment — 2026-09-09

The independent Unity worktree produced and installed a new Instrument Audio
Review APK containing Brown Noise level normalization and DSP-phase-driven LFO
hairline display.

- APK SHA-256:
  `0984139152945b283203b9f936b0f94e0a41c0c5a27dcfe4f72f328761a3ede6`
- APK size: 79,273,467 bytes
- Unity Android build: PASS
- Install on Quest 3 `2G0YC1ZG2J02HL`: PASS
- Package: `com.DefaultCompany.MatsuMotoMeterAR`
- Version: `0.3.0` (`versionCode 3`)
- Device-reported update time: `2026-09-09 15:53:20`
- Focused Brown Noise/LFO EditMode tests: 45 / 45 PASS

The device reported `mWakefulness=Awake`, but Quest intercepted the cold-launch
request with `LaunchCheckControllerRequiredDialogActivity`. The application PID
was absent and no Android/Unity fatal exception was logged. Runtime sound and
display acceptance therefore remain pending until a person wears the headset
and acknowledges the controller-required launch check.

## Ext-A1/B1 production visual deployment — 2026-09-12

The Instrument Audio Review APK was rebuilt after production promotion of the
24 `AudioModules_Ext_A1_B1` FBX/prefab pairs.

- APK SHA-256:
  `84d568bff976cb644f5ed07ab6fde7201d7c5b21a3be56e808e7fd74db798280`
- APK size: 81,348,551 bytes
- Unity Android build: PASS
- Install on Quest 3 `2G0YC1ZG2J02HL`: **Success**
- Package/version: `com.DefaultCompany.MatsuMotoMeterAR` / `0.3.0` /
  `versionCode 3`
- Device-reported update time: `2026-09-12 21:40:01`
- Local build settings: restored; quarantine path clear
- Crash buffer after launch request: no application/Unity fatal entry

The launch request returned `Status: ok` but foregrounded
`LaunchCheckControllerRequiredDialogActivity`. The application PID was absent.
Put on the headset and acknowledge the controller check before evaluating the
new VCA/Mixer/Filter/Envelope visuals, the revised LFO/Sequencer ports, cable
alignment, interaction, or audio-load behavior.

### Ext-A1/B1 headset follow-up — 2026-09-18

The controller check was cleared. The same installed APK remained version
`0.3.0` / versionCode `3`, last updated `2026-09-12 21:40:01`.

- Foreground application activity: `UnityPlayerGameActivity`.
- Application PID: `26477`; remained unchanged through the observation.
- Application/Unity crash-buffer entries: 0.
- Application error/exception entries in the sampled PID log: 0.
- AudioFlinger application track over 15 seconds: underruns `7 -> 7`,
  overruns `469 -> 469`, write errors `0`.
- Spatial renderer: `num_render_underruns 0 -> 0`.
- Product-owner headset observation of the new VCA/Mixer/Filter/Envelope
  visuals, revised LFO/Sequencer port presentation, operation, and sound:
  **no issue reported**.

The nonzero AudioFlinger counters predate this 15-second sample and did not
increase during it. This is a live smoke observation, not a representative
multi-module audio-load stress measurement. Do not mark the deferred 48/64
Quest stress gates as executed or passed on this basis.

### Audio-load acceptance decision — 2026-09-18

The product owner explicitly accepted the audio-load test as **PASS**. This
closes the audio-load product-acceptance item by user decision. The measured
evidence remains the 15-second live audio smoke above; a representative
multi-module graph, 48/64-object stress runs, and sustained CPU/DSP/thermal
measurements were not performed. Those quantitative gates remain unmeasured,
not measured PASS. This decision does not record completion of the separate
source-connection test scenarios.
