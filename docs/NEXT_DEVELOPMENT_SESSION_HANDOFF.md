# Next development session handoff

Status: **ready for a new development session**

Prepared: 2026-09-02

Released baseline: `v0.3.0-concept.1` at commit
`368676403e21ca0295d4f20fda335adae272f688`

## 1. Start point

`v0.3.0-concept.1` is closed and published as a GitHub source pre-release.
At release close, `main`, `origin/main`, and the annotated release tag identified
the same commit. Later documentation commits may move `main`; the immutable
released baseline remains the tag commit above. The local worktree was clean
when this handoff was prepared. The release contains the expanded-Git-LFS
full-source archive and its SHA-256 manifest; the locally signed Quest APK is
test evidence and was not published.

Do not reopen release preparation or reinterpret an explicitly skipped check as
a release failure. Start future work from current `main` on a new `codex/` branch.
Do not commit directly to `main`.

The next version number is intentionally undecided. Select it only after the
first coherent scope is agreed; do not assume `v0.4` or another release label.

## 2. Source-of-truth order

When older notes disagree, use this order:

1. This handoff for the next-session boundary and priorities.
2. [`releases/v0.3.0-concept.1.md`](releases/v0.3.0-concept.1.md) for released
   behavior and validation evidence.
3. [`V0_3_DEVELOPMENT_ROADMAP.md`](V0_3_DEVELOPMENT_ROADMAP.md) for completed
   feature rationale and deferred work.
4. Current production assets, runtime code, tests, and generated audit reports.
5. [`OPUS5_CODEX_ALIGNMENT.md`](OPUS5_CODEX_ALIGNMENT.md) only as historical
   evidence for a specific model revision or decision.

`OPUS5_CODEX_ALIGNMENT.md` contains superseded intermediate diagnoses and stop
gates. Do not read its 300-plus sections as a current open-task list.
`V6_KNOWN_DEFECTS.md` also contains candidate-era status text; verify each item
against current production before treating it as an active defect.

## 3. Released baseline that must remain intact

- Unity `6000.3.19f1`; Blender authoring `5.2.x`.
- Four themes and 14 instrument types: 56 active visual prefabs.
- Operation, Edit, and Connect modes.
- Direct, Invert, Range, and Threshold connections with editable parameters.
- Average, Sum, Minimum, Maximum, and Priority multi-input composition.
- Trend Monitor with up to four input histories and a composed-output history.
- Window Panel with Energy, Balance, Phase, and Detail slots plus Orbit, Rose,
  and Lissajous presets.
- Placement schema v7, Room ownership, Spatial Anchors, persistence, and migration.
- Supported placement gate remains 48 objects per Room; 64 is stress
  characterization, not a supported count.
- Latest recorded regression baseline: EditMode 220 / 220, active visual prefabs
  56 / 56, control motion 16 / 16, signal visuals 8 / 8.

Any schema or interaction change must preserve v1-v7 migration and existing
saved placements unless a separately approved migration policy says otherwise.

## 4. Remaining development lanes

These are future-development items, not unfinished release actions. Keep the
lanes separate so model work does not silently alter runtime contracts and UI
work does not expand into signal-processing semantics.

### Lane A — targeted 3D model and material refinement

Start here because it has a concrete, already observed defect and limited
runtime risk.

1. **Machined Ergonomics Throttle and PowerSlider surface stripes.** Their body
   Normal Map reads as an oversized repeating stripe at Quest viewing distance.
   Freeze accepted geometry, motion, grip UVs, BaseColor, fastener access, and
   collider behavior. Compare physical pitch, UV direction, and lower-strength
   versus finer-grain normal treatments. Require fixed-camera A/B images before
   promotion and Quest A/B before final acceptance.
2. **Image-based production survey.** Render the current 56 active prefabs at
   fixed front and oblique cameras, with motion endpoints and OFF/ON states where
   relevant. Use visual review to nominate bounded defects; validator output by
   itself is not evidence that a model looks better. Do not start a wholesale
   56-model remodel.
3. **Meter cover-glass decision.** Transparent curved glass is not currently a
   standard requirement because of Quest transparency, sorting, and performance
   cost. Add it only if an image/Quest comparison demonstrates sufficient value.
4. **Sealed internal geometry optimization.** The accepted AuditKit sweep found
   fully occluded internal disks, including the Medium/Large meter full-diameter
   disks. Treat removal as optional optimization, not a visual defect. First
   prove no structural, shading, or export role depends on each disk.

For every new or modified Blender/FBX candidate:

- keep production assets untouched until isolated staging and Gate C pass;
- run the accepted Tier A AuditKit before Gate B;
- preserve node names, pivots, material roles, GUIDs, motion range, and collider
  contracts unless the approved task explicitly changes one;
- provide part renders, assembled renders, fixed-camera baseline/candidate
  comparisons, and a compact report;
- do not commit `.blend1`, exploratory renders, or bulk diagnostic output;
- ask before adding a Blender add-on, library, or external FBX validator.

### Lane B — UI and interaction improvement

No new UI design has been approved yet. Begin with a short usability audit, not
an implementation sweep.

1. Exercise Operation, Edit, and Connect on Quest and list operations that are
   difficult to discover, require memorized controller input, or overload the
   HUD. Include Range/Threshold editing, composition kind/rank, Window Panel
   slot/preset selection, cancel/confirm, and restoration feedback.
2. Turn the findings into a small interaction contract: user goal, current
   sequence, proposed sequence, controller mapping, HUD state, cancel path,
   persistence effect, and backward-compatibility effect.
3. Implement one coherent UI slice at a time. Add EditMode tests for state
   transitions and perform Quest acceptance before beginning the next slice.

Do not redesign the accepted Trend Monitor and Window Panel rendering merely to
make the code uniform. Change them only for an observed usability or visual
problem. Keep runtime display coordinates theme-independent.

### Lane C — specification changes

The main deferred feature family is signal constraint processing:

- stale/invalid input metadata and timeout semantics;
- clamp and rate limiter;
- latched threshold/trip;
- explicit reset, reset authority, and persistence;
- fail-safe value and feedback-loop evaluation order.

This was intentionally excluded from `v0.3.0-concept.1`. Before code, define
what timestamp is authoritative, how stale state propagates through transforms
and composition, who may reset a latch, what survives restart, and how the UI
avoids implying functional-safety certification. It may be deferred again.

Other optional specification decisions are whether to obtain Quest/OpenXR GPU
timing, whether 64 objects should ever become a supported count, and whether to
add Quest 3S coverage. The prior decision to skip these remains valid until the
user explicitly reopens them.

## 5. Recommended execution order

1. Create a new `codex/` branch from current `main` and reproduce the baseline.
2. Complete Lane A item 1 as the first bounded candidate, including visual A/B.
3. Run the UI usability audit and ask the user to approve one UI contract.
4. Implement that single UI slice with tests and Quest acceptance.
5. Decide whether Lane C has enough product value and semantic clarity to open.
6. Only then select a version/release slice and update `CHANGELOG.md`.

Large model changes, UI redesign, schema changes, and performance experiments
should use separate branches and PRs. Merge only a coherent, independently
reversible slice. Do not combine an Opus-generated model revision with unrelated
Unity runtime changes in one commit.

## 6. Verification and tooling

Prefer Unity Pipeline against the running Editor for routine checks. Project
commands are registered in
`Assets/MatsuMotoMeterAR/Editor/ProjectPipelineCommands.cs`:

- `matsu_render_trend_monitor_review`
- `matsu_audit_control_motion`
- `matsu_audit_signal_visuals`
- `matsu_build_performance_gate`
- `matsu_build_performance_gate_status`

The performance build command requires explicit confirmation; do not bypass
that guard. Use `ConceptReleaseBuilder` for a release APK because it safely
quarantines and restores the ignored local Meta XR development-agent settings.
Never inspect, log, stage, or publish that local credential/settings asset.

Minimum checks are proportional to the change:

- UI/runtime: compile, focused EditMode tests, full EditMode, persistence and
  migration tests, then Quest interaction acceptance.
- Model/material: Tier A, isolated staging, fixed images, prefab validation,
  relevant motion/signal audit, Gate C, then Quest close-range acceptance.
- Schema/spec: migration fixtures for every supported older version, clone and
  round-trip tests, invalid-value normalization, restart restoration, and Quest.
- Performance: fixed count/theme/distance/temperature/update profile and a
  baseline-relative report. Never label a skipped run as PASS.

## 7. Opus collaboration boundary

The previous assigned Opus work is complete and no further Opus work is
authorized. The Claude application/session may still be open, but its project
task is in a stop state. Claude/Opus may be launched for a new, narrowly bounded
model candidate after Codex writes the scope and stop gate. Codex owns
production integration, documentation, Unity validation, git, PRs, and release
decisions. Opus must not modify active production assets, Unity
prefabs/materials, docs, git state, or external dependencies unless a new
instruction explicitly changes that boundary.

For the next Opus-assisted task, start a new alignment record rather than
continuing the large historical transcript. Record only scope, allowed paths,
frozen contracts, deliverables, evidence, and the exact stop gate.

## 8. Copy-paste prompt for the new Codex session

> Continue AnalogInstrumentMR from the published `v0.3.0-concept.1` baseline.
> First read `docs/NEXT_DEVELOPMENT_SESSION_HANDOFF.md`,
> `docs/releases/v0.3.0-concept.1.md`, the relevant current contract, and the
> current production code/assets. Verify that tag `v0.3.0-concept.1` points to
> commit `368676403e21ca0295d4f20fda335adae272f688`, that current `main` descends
> from that baseline, and that the worktree is clean. Do not reopen release work or infer current
> defects from superseded sections of `docs/OPUS5_CODEX_ALIGNMENT.md`.
> Propose the first bounded slice from the handoff priorities, with acceptance
> criteria and dependencies, and wait for agreement before large implementation.
> Use a new `codex/` branch. Preserve the released runtime, schema-v7 migration,
> 48-object support boundary, and current tests. For model work, require fixed
> image-based comparison plus Tier A / Gate C; for UI or specification changes,
> write the interaction or signal contract before implementation.
