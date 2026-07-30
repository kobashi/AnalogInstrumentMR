# Quest v0.2.0 Release Smoke Test

This checklist is the final physical interaction gate for
`v0.2.0-concept.1`. Run it on Meta Quest 3 with the normal runtime, not a
synthetic performance scenario.

## Candidate

| Item | Value |
| --- | --- |
| APK | `Builds/Release/AnalogInstrumentMR-v0.2.0-concept.1-quest3.apk` |
| SHA-256 | `62f6010e656f6795733ffe9ca88063a2bb9173102cba009187c911a926bc7c57` |
| Version | `0.2.0` (`versionCode 2`) |
| Package | `com.DefaultCompany.MatsuMotoMeterAR` |
| Device | Meta Quest 3 |
| Automated install/start | PASS |
| Fatal/exception log scan after launch | PASS |
| Existing placement Room classification | PASS: 22 current / 26 other |

## Physical interaction checklist

Keep the safe-exit check until last.

- [x] Existing placements and connections restore after the upgrade install.
- [x] Moving from one scanned Room to another switches the HUD Room indicator,
      Plane/Volume wireframes, and visible instruments after a short debounce.
- [x] Returning to the first Room restores its Spatial Anchors without moving or
      duplicating its instruments.
- [x] `X` cycles Operation → Edit → Connect without losing controller alignment.
- [x] In Operation mode, holding left stick click for two seconds locks `X`;
      repeating the hold unlocks it.
- [x] In Edit mode, right stick left/right changes the object and up/down jumps
      between functional categories.
- [x] In Edit mode with no selection, left stick left/right changes the theme.
- [x] A new object can be placed on a Plane or Volume face; preview and placed
      materials render correctly.
- [x] A selected object shows its move target; `A` confirms the move.
- [x] `B` deletes an aimed unselected object, and right stick click deletes it
      while switching the add target to that object type.
- [x] With multiple objects selected, right stick directions rotate the layout
      around the first selection; `B` clears the selection and `Y` does nothing.
- [x] Multi-selection alignment/distribution preserves the original order and
      remains a preview until `A` confirms it.
- [x] In Operation mode, beam plus trigger operates buttons and supported
      controls.
- [x] Grip plus controller motion operates lever, throttle, and power slider
      without a visible grip-position offset.
- [x] Connected LED/meter output responds to its input and animates.
- [x] In Connect mode, source-to-target connection creation works and connection
      lines are colored by type.
- [x] With one connected object selected, `A` cycles its incoming and outgoing
      connections; `B` deletes the selected connection.
- [x] Left stick left/right changes Direct/Invert/Range/Threshold, and left stick
      click confirms the mode and clears only the connection selection.
- [x] In Edit mode, holding left stick click for two seconds exits safely.

## Result

- Date: 2026-07-30
- Result: PASS
- Notes: Full physical interaction checklist, including multi-Room switching,
  return restoration, editing, operation, connection, and safe exit, passed on
  Meta Quest 3.
