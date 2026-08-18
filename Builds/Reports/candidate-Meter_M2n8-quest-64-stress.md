# Meter M2n8 Quest 3 64-object stress characterization

Date: 2026-08-18
Device: Quest 3 (`eureka`)
Theme: KineticSafety
Scenario: 64 objects, 13-archetype baseline mix, 1.35 m, 72 Hz, 15 s warm-up + 600 s measurement

## Results

| Metric | Active baseline | M2n8 candidate | Candidate delta |
| --- | ---: | ---: | ---: |
| CPU p95 | 14.492 ms | 14.475 ms | −0.017 ms (−0.12%) |
| Frame p95 | 14.494 ms | 14.476 ms | −0.018 ms (−0.12%) |
| Delayed frames | 0.021% | 0.025% | +0.004 percentage points |
| GPU p95 | 0.000 ms | 0.000 ms | unavailable in both builds |
| GC collections | 0 | 0 | 0 |
| Maximum GC allocation in frame | 0 B | 0 B | 0 B |
| Unity allocated memory | 139,482,070 B | 139,585,982 B | +103,912 B (+0.07%) |
| Fatal errors | 0 | 0 | 0 |
| Thermal stop | no | no | no |
| End temperature | 45.0°C | 44.0°C | — |

The candidate has no measurable CPU/frame regression relative to the active baseline. Delayed frames remain far below 1%, maximum per-frame GC allocation is 0 B, Unity allocated-memory delta is below 0.1%, and neither build crashes or reaches the thermal stop.

Verdict: **PASS as 64-object stress characterization**

Evidence:

- Candidate host: `Builds/Reports/perfgate-64-KineticSafety-20260818-163737.log` (`6d09b76fc07759f36ddd9e1d24ac03b65352a2122b9a5cf994bb386448c1512d`)
- Candidate device: `Builds/Reports/perfgate-64-KineticSafety-20260818-163737-device.log` (`b1d07e60d4745959af66740222af59233a28eb76dba7999299aa1bfe61c8a257`)
- Baseline host: `Builds/Reports/perfgate-64-KineticSafety-20260818-170903.log` (`178c1bf3ad982a1f6ae857a9f9375f2d44efb8799f306fa2fe199f279d85dc3a`)
- Baseline device: `Builds/Reports/perfgate-64-KineticSafety-20260818-170903-device.log` (`f01fbfc72776153e60a9bce59165219227fbf8373dac348c0f5f90e92a4aad64`)
