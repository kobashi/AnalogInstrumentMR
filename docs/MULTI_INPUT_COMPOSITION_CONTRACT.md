# Multiple-input composition contract

## Status

Priority 4 schema/runtime/desktop-UI, Trend Monitor diagnostics, and Quest 3
interaction acceptance complete. Schema v7 persists composition settings and
the runtime evaluates them with an allocation-free accumulator.

## Existing behavior

- Each connection transforms its source independently using Direct, Invert,
  Range, or Threshold.
- A normal target receives the arithmetic mean of all valid transformed inputs.
- A target with no valid input keeps its previous value.
- Window Panel is an explicit exception: slots A-D remain independent as
  Energy, Balance, Phase, and Detail. They are not composed by this policy.
- Trend Monitor keeps up to four per-connection histories and overlays a
  separate white composed-output history. The composed trace never replaces
  the individual traces.

## Composition kinds

| Kind | Result |
| --- | --- |
| Average | Arithmetic mean; compatibility default |
| Sum | Sum clamped to the normalized 0-1 range |
| Minimum | Lowest valid transformed input |
| Maximum | Highest valid transformed input |
| Priority | Value from the highest persisted priority rank |

All finite inputs are clamped to 0-1 before composition. NaN and infinity are
invalid and do not participate. If no valid input remains, composition reports
no output and the runtime preserves the target's previous value.

Priority uses the larger integer as the stronger rank. Equal ranks are resolved
by ordinal connection ID, not list order, so JSON reordering cannot change the
result. The UI should expose a small bounded rank rather than an unrestricted
integer.

## Persistence

Schema v7 adds:

- `signalCompositionKind` to `PlacementRecord`, defaulting to Average.
- `compositionPriority` to `SignalConnectionRecord`, defaulting to zero.

Migration from schema v6 preserves all connection transform parameters,
Window Panel slots, and graphic presets while assigning Average/zero defaults.
Unknown enum values normalize to Average. Window Panel ignores the target-level
composition field because its slot semantics are already explicit.

## Runtime and performance

- Transform each input before composition.
- Evaluate from the frame's source-value snapshot, then apply target outputs.
- Do not allocate lists, LINQ enumerables, materials, or meshes per frame.
- Report the selected kind, valid input count, and no-valid-input state to
  diagnostics and Trend Monitor.
- Stale-input handling requires timestamp/validity metadata that does not exist
  in schema v7. It remains a separate prerequisite for safety processing.

## Connect-mode controls

- Select a normal target by trigger, then use right stick up/down to cycle
  Average, Sum, Minimum, Maximum, and Priority.
- A target-kind change is saved transactionally and evaluated immediately. A
  save failure restores the previous kind.
- Select a connection with A. When its target uses Priority, right stick
  left/right changes the pending rank from 0 through 3.
- Left-stick press commits the pending transform, Window Panel slot, and
  priority together. Selecting the next connection without applying reloads the
  persisted rank and therefore discards the pending rank.
- Y continues to open Range/Threshold parameter editing. B continues to mean
  connection deletion in the selected-connection state.
- Window Panel is unchanged: right stick up/down edits its graphic preset and
  right stick left/right edits its A-D slot.

## Delivery sequence

1. Pure accumulator and Average-compatible evaluator refactor. **Complete**
2. Schema v7 migration, normalization, and runtime integration. **Complete**
3. Connect-mode target setting, live preview, and Priority rank editing.
   **Desktop and Quest 3 complete**
4. Trend Monitor diagnostics for individual inputs and composed output.
   **Desktop and Quest 3 complete**
5. Desktop regression, then Quest interaction/performance gates.
   **Complete**

## Quest 3 acceptance

2026-09-02の通常runtime受入で、Average／Sum／Minimum／Maximum／Priority、
priority rank 0〜3、Trend Monitorの個別入力と白色合成履歴、Window Panelの4 slotと
Orbit／Rose／Lissajous、再起動復元を確認した。global theme切替時にWindow Panelの
再生成済みgraphic viewへruntime参照を結び直す修正後、4テーマすべてでpreset変更と
Energy／Balance／Phase／Detail入力追従をPASSした。修正後のUnity EditModeは220 / 220 PASS。
