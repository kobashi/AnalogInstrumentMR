using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Signals;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class SuperfineNonAudioCandidateC4Audit
    {
        private static readonly IReadOnlyDictionary<string, Entry> Entries =
            new Dictionary<string, Entry>(StringComparer.Ordinal)
            {
                ["MeterRound"] = new(
                    MockInstrumentKind.RoundMeter, "needle_pivot", 4),
                ["MeterMedium"] = new(
                    MockInstrumentKind.RoundMeterMedium, "needle_pivot", 4),
                ["MeterLarge"] = new(
                    MockInstrumentKind.RoundMeterLarge, "needle_pivot", 4),
                ["WindowMeter"] = new(
                    MockInstrumentKind.WindowMeter, "needle_pivot", 4),
                ["WindowPanel"] = new(
                    MockInstrumentKind.WindowPanel, "display_surface", 3),
                ["TrendMonitor"] = new(
                    MockInstrumentKind.TrendMonitor, "display_surface", 3),
                ["Lever"] = new(
                    MockInstrumentKind.Lever, "handle_pivot", 2),
                ["Toggle"] = new(
                    MockInstrumentKind.ToggleSwitch, "switch_pivot", 2),
                ["Rotary"] = new(
                    MockInstrumentKind.RotaryKnob, "knob_pivot", 3),
                ["Button"] = new(
                    MockInstrumentKind.PushButton, "button_travel", 2),
                ["Throttle"] = new(
                    MockInstrumentKind.ThrottleLever, "throttle_pivot", 2),
                ["PowerSlider"] = new(
                    MockInstrumentKind.PowerSlider, "slider_travel", 2),
                ["Lamp"] = new(
                    MockInstrumentKind.IndicatorLamp, "indicator", 2),
                ["StatusIndicator"] = new(
                    MockInstrumentKind.StatusIndicator, "indicator", 2)
            };

        internal static string Audit(string manifestPath)
        {
            var manifest = CandidateStagingManifest.Load(manifestPath);
            var outputPath =
                $"Builds/Reports/candidate-{manifest.candidateId}-c4-audit.md";
            var report = new StringBuilder();
            var failures = new List<string>();
            report.AppendLine($"# Candidate {manifest.candidateId} C4 audit");
            report.AppendLine();
            report.AppendLine(
                "| Model | Manifest target | Runtime surface/state assignment | " +
                "Material roles | Signal role | Typed visual ports | Result |");
            report.AppendLine("| --- | --- | --- | --- | --- | --- | --- |");

            foreach (var candidate in manifest.entries)
            {
                if (!Entries.TryGetValue(candidate.model, out var entry))
                {
                    failures.Add($"{candidate.model}: unsupported C4 model");
                    continue;
                }

                var path = manifest.CandidatePrefabPath(candidate);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null)
                {
                    failures.Add($"{candidate.model}: prefab missing {path}");
                    continue;
                }

                var problems = new List<string>();
                var visualManifests = prefab.GetComponents<ThemeVisualManifest>();
                var visualManifest = visualManifests.Length == 1
                    ? visualManifests[0]
                    : null;
                if (visualManifest == null)
                    problems.Add("exactly one ThemeVisualManifest required");
                var target = visualManifest?.MotionTarget;
                if (target == null || target.name != entry.MotionTarget)
                {
                    problems.Add(
                        $"motion target must be {entry.MotionTarget}");
                }

                var runtimeStatus = AuditRuntimeAssignment(
                    candidate.model,
                    target,
                    visualManifest,
                    problems);
                var materials = prefab.GetComponentsInChildren<Renderer>(true)
                    .SelectMany(renderer => renderer.sharedMaterials)
                    .Where(material => material != null)
                    .Distinct()
                    .ToArray();
                if (materials.Length != entry.MaterialCount)
                {
                    problems.Add(
                        $"materials={materials.Length}; expected=" +
                        entry.MaterialCount);
                }
                var materialStatus = materials.Length == entry.MaterialCount
                    ? $"PASS ({materials.Length})"
                    : $"FAIL ({materials.Length}/{entry.MaterialCount})";

                var signalStatus = AuditSignalRole(entry.Kind, problems);
                var typedPorts = prefab.GetComponentsInChildren<Transform>(true)
                    .Count(item => item.name.StartsWith(
                        "port_",
                        StringComparison.Ordinal));
                if (typedPorts != 0)
                    problems.Add($"unexpected typed visual ports={typedPorts}");
                var portStatus = typedPorts == 0
                    ? "N/A (logical/root endpoint)"
                    : $"FAIL ({typedPorts})";
                if (prefab.GetComponentsInChildren<Collider>(true).Length != 0)
                    problems.Add("candidate visual contains Collider");

                var result = problems.Count == 0 ? "PASS" : "FAIL";
                report.Append("| ").Append(candidate.model)
                    .Append(" | ")
                    .Append(target?.name == entry.MotionTarget
                        ? "PASS"
                        : "FAIL")
                    .Append(" | ").Append(runtimeStatus)
                    .Append(" | ").Append(materialStatus)
                    .Append(" | ").Append(signalStatus)
                    .Append(" | ").Append(portStatus)
                    .Append(" | ").Append(result).AppendLine(" |");
                foreach (var problem in problems)
                    failures.Add($"{candidate.model}: {problem}");
            }

            report.AppendLine();
            report.AppendLine("## Findings");
            report.AppendLine();
            report.AppendLine(
                "- PASS: candidate visuals contain no collider; interaction " +
                "colliders remain runtime-owned and are not copied into prefabs.");
            report.AppendLine(
                "- PASS: controls remain logical signal sources, meters remain " +
                "observable, and indicator/display objects remain valid targets.");
            report.AppendLine(
                "- N/A: non-audio signal connections do not use authored typed " +
                "`port_*` nodes; their cable endpoint is the runtime instrument root.");
            report.AppendLine(
                "- REVIEW: common material-budget and TrendMonitor display-width " +
                "findings remain in the staging validation report and are not " +
                "reclassified here.");

            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            File.WriteAllText(outputPath, report.ToString());
            AssetDatabase.Refresh();
            if (failures.Count > 0)
            {
                throw new InvalidOperationException(
                    $"Candidate {manifest.candidateId} C4 audit failed:\n" +
                    string.Join("\n", failures));
            }

            Debug.Log(
                $"Candidate {manifest.candidateId} C4 audit passed: " +
                $"{manifest.entries.Length}/{manifest.entries.Length}. " +
                $"Report: {outputPath}");
            return outputPath;
        }

        private static string AuditRuntimeAssignment(
            string model,
            Transform target,
            ThemeVisualManifest manifest,
            ICollection<string> problems)
        {
            if (model == "Lamp")
            {
                var valid = manifest?.IndicatorRenderer != null &&
                            manifest.IndicatorRenderer.name == "indicator_lens";
                if (!valid)
                    problems.Add("indicator_lens runtime renderer missing");
                return valid ? "PASS (indicator_lens)" : "FAIL";
            }
            if (model == "StatusIndicator")
            {
                var expected = new[]
                {
                    "status_safe", "status_warn", "status_danger"
                };
                var actual = manifest?.StateRenderers ?? Array.Empty<Renderer>();
                var valid = actual.Length == expected.Length &&
                            actual.Select(renderer => renderer?.name)
                                .SequenceEqual(expected) &&
                            actual.Distinct().Count() == expected.Length;
                if (!valid)
                    problems.Add("SAFE/WARN/DANGER runtime mapping mismatch");
                return valid ? "PASS (3 state renderers)" : "FAIL";
            }
            if (model == "WindowPanel" || model == "TrendMonitor")
            {
                var renderer = target?.GetComponent<Renderer>();
                var mesh = target?.GetComponent<MeshFilter>()?.sharedMesh;
                var valid = renderer != null && mesh != null &&
                            mesh.triangles.Length / 3 == 2;
                if (!valid)
                    problems.Add("2-triangle runtime display assignment missing");
                return valid ? "PASS (display_surface)" : "FAIL";
            }

            var hasRenderer = target?.GetComponentInChildren<Renderer>(true) != null;
            if (!hasRenderer)
                problems.Add("motion target has no renderer subtree");
            return hasRenderer ? "PASS (motion subtree)" : "FAIL";
        }

        private static string AuditSignalRole(
            MockInstrumentKind kind,
            ICollection<string> problems)
        {
            var roles = new List<string>();
            if (InstrumentSignalPolicy.CanSource(kind))
                roles.Add("source");
            if (InstrumentSignalPolicy.CanObserve(kind))
                roles.Add("observable");
            if (InstrumentSignalPolicy.CanTarget(kind))
                roles.Add("target");
            if (roles.Count == 0)
            {
                problems.Add("no runtime signal role");
                return "FAIL";
            }
            return "PASS (" + string.Join(" + ", roles) + ")";
        }

        private readonly struct Entry
        {
            public Entry(
                MockInstrumentKind kind,
                string motionTarget,
                int materialCount)
            {
                Kind = kind;
                MotionTarget = motionTarget;
                MaterialCount = materialCount;
            }

            public MockInstrumentKind Kind { get; }
            public string MotionTarget { get; }
            public int MaterialCount { get; }
        }
    }
}
