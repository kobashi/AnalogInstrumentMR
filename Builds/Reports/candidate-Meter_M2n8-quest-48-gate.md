# Meter M2n8 Quest 3 48-object acceptance gate

Date: 2026-08-18
Device: Quest 3 (`eureka`)
Theme: KineticSafety
Scenario: 48 objects, 13-archetype baseline mix, 1.35 m, 72 Hz, 15 s warm-up + 600 s measurement

## Builds

| Build | APK | SHA-256 |
| --- | --- | --- |
| M2n8 isolated candidate | `Builds/QuestReview/AnalogInstrumentMR-Meter_M2n8-review-quest3.apk` | `da39a9075865c1ca91497961bf7502b9758aac2890a6fbcef06b0f97c85bc48b` |
| Current active baseline | `Builds/Performance/AnalogInstrumentMR-v0.2.0-perfgate-quest3.apk` | `3a10cb1c507c286ba36c6c83fc67d8c9b76f1ec23b50380301fc5736ae3b1231` |

## Results

| Metric | Active baseline | M2n8 candidate | Candidate delta |
| --- | ---: | ---: | ---: |
| CPU p95 | 14.385 ms | 14.552 ms | +0.167 ms (+1.16%) |
| Frame p95 | 14.381 ms | 14.552 ms | +0.171 ms (+1.19%) |
| Delayed frames | 0.014% | 0.025% | +0.011 percentage points |
| GPU p95 | 0.000 ms | 0.000 ms | unavailable in both builds |
| GC collections | 0 | 3 | +3 (observe) |
| Maximum GC allocation in frame | 0 B | 0 B | 0 B |
| Unity allocated memory | 138,984,798 B | 139,093,958 B | +109,160 B (+0.08%) |
| Fatal errors | 0 | 0 | 0 |
| Thermal stop | no | no | no |
| End temperature | 45.0°C | 43.0°C | — |

Both builds report `diagnostic=REVIEW` because Quest/OpenXR returns GPU timing as 0 and the `FrameTimingManager` CPU/frame sample includes the 72 Hz pacing interval. This is the same limitation documented for the earlier R2 candidate. The external acceptance decision therefore uses baseline non-regression, delayed-frame rate, allocation, stability, memory, and thermal evidence.

The candidate deltas are small, delayed frames remain far below 1%, maximum per-frame GC allocation is 0 B, memory is stable, and no fatal or thermal stop occurred. The three collection-count events in the candidate run are retained as an observation; they did not recur in the candidate 64-object run and were not accompanied by recorded per-frame allocation.

Verdict: **PASS (external baseline-relative acceptance), GC collection count OBSERVE**

Evidence:

- Candidate host: `Builds/Reports/perfgate-48-KineticSafety-20260818-162555.log` (`428bc0aee9b0564f548fb4d983dcdcbe2cbcbdb23d1f8fae0137227bcaf1d6ce`)
- Candidate device: `Builds/Reports/perfgate-48-KineticSafety-20260818-162555-device.log` (`8f1368524be00f4d4f52d9deac67eb67a73d2a4ae910d10a2c910abcd83fbe4a`)
- Baseline host: `Builds/Reports/perfgate-48-KineticSafety-20260818-165351.log` (`b0b8c7f4922677715050a191dcab4b8b30ab60ddf6ebbb4a7f063673b08857ad`)
- Baseline device: `Builds/Reports/perfgate-48-KineticSafety-20260818-165351-device.log` (`33e374f0e573aabd704f20b77cd7edc4aa1c9b242e9b5a24ec8902c97e858a06`)
