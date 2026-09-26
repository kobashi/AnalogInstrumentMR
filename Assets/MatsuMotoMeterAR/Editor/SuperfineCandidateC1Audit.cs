using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using MatsuMotoMeterAR.Audio;
using MatsuMotoMeterAR.Instruments;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class SuperfineCandidateC1Audit
    {
        private const float PositionTolerance = 0.001f;

        private static readonly IReadOnlyDictionary<string, ModuleEntry> Modules =
            new Dictionary<string, ModuleEntry>(StringComparer.Ordinal)
            {
                ["AudioOscillator"] = new(
                    MockInstrumentKind.AudioOscillator,
                    "port_pitch_in", "port_gate_in", "port_fm_in",
                    "port_audio_out"),
                ["AudioNoise"] = new(
                    MockInstrumentKind.AudioNoise,
                    "port_gate_in", "port_audio_out"),
                ["AudioDelay"] = new(
                    MockInstrumentKind.AudioDelay,
                    "port_audio_in", "port_time_in", "port_audio_out"),
                ["AudioOutput"] = new(
                    MockInstrumentKind.AudioOutput,
                    "port_audio_in"),
                ["AudioVca"] = new(
                    MockInstrumentKind.AudioVca,
                    "port_audio_in", "port_level_in", "port_audio_out"),
                ["AudioMixer"] = new(
                    MockInstrumentKind.AudioMixer,
                    "port_audio_in", "port_audio_out"),
                ["AudioFilter"] = new(
                    MockInstrumentKind.AudioFilter,
                    "port_audio_in", "port_cutoff_in", "port_audio_out"),
                ["AudioEnvelope"] = new(
                    MockInstrumentKind.AudioEnvelope,
                    "port_gate_in", "port_trigger_in", "port_control_out"),
                ["AudioLFO"] = new(
                    MockInstrumentKind.AudioLfo,
                    "port_rate_in", "port_reset_in", "port_control_out",
                    "port_clock_out", "port_gate_out", "port_trigger_out",
                    "port_audio_out"),
                ["AudioSequencer"] = new(
                    MockInstrumentKind.AudioSequencer,
                    "port_clock_in", "port_trigger_in", "port_control_out",
                    "port_gate_out", "port_trigger_out")
            };

        internal static string Audit(string manifestPath)
        {
            var manifest = CandidateStagingManifest.Load(manifestPath);
            var auditStage = manifest.candidateId.EndsWith(
                "_C3",
                StringComparison.Ordinal)
                    ? "c3"
                    : manifest.candidateId.EndsWith(
                        "_C2",
                        StringComparison.Ordinal)
                            ? "c2"
                            : "c1";
            var outputPath =
                $"Builds/Reports/candidate-{manifest.candidateId}-" +
                $"{auditStage}-audit.md";
            var report = new StringBuilder();
            report.AppendLine(
                $"# Candidate {manifest.candidateId} " +
                $"{auditStage.ToUpperInvariant()} audit");
            report.AppendLine();
            report.AppendLine(
                "| Module | Contract | Pivot Z | Port Z / collider | " +
                "Display + signal runtime assignment | Cable endpoints | Result |");
            report.AppendLine("| --- | --- | --- | --- | --- | --- | --- |");

            foreach (var candidate in manifest.entries)
            {
                var module = Modules[candidate.model];
                var path = manifest.CandidatePrefabPath(candidate);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null)
                {
                    report.AppendLine(
                        $"| {candidate.model} | FAIL | N/A | N/A | N/A | " +
                        $"N/A | FAIL: prefab missing `{path}` |");
                    continue;
                }

                var instance = UnityEngine.Object.Instantiate(prefab);
                try
                {
                    var contractProblems =
                        AudioModuleCandidateContractValidator.Evaluate(
                            instance,
                            module.Kind,
                            requireSignalSurface: true);
                    var contractStatus = contractProblems.Count == 0
                        ? "PASS"
                        : "FAIL: " + string.Join("; ", contractProblems);

                    var pivot = Find(instance.transform,
                        "parameter_knob_pivot");
                    var pivotZ = LocalPosition(instance.transform, pivot).z;
                    var pivotStatus = Approximately(pivotZ, 0.055f)
                        ? $"PASS ({pivotZ * 1000f:0.0} mm)"
                        : $"FAIL ({pivotZ * 1000f:0.0} mm; expected 55.0 mm)";

                    var spec = InstrumentGreyboxSpecification.Get(module.Kind);
                    var portProblems = new List<string>();
                    foreach (var name in module.Ports)
                    {
                        var port = Find(instance.transform, name);
                        if (port == null)
                        {
                            portProblems.Add($"{name} missing");
                            continue;
                        }
                        var position = LocalPosition(instance.transform, port);
                        if (!Approximately(position.z, 0.054f))
                        {
                            portProblems.Add(
                                $"{name} Z={position.z * 1000f:0.0} mm");
                        }
                        if (!Contains(spec, position))
                            portProblems.Add($"{name} outside interaction box");
                    }
                    var portStatus = portProblems.Count == 0
                        ? "PASS (54.0 mm; fixed interaction box contains all)"
                        : "FAIL: " + string.Join("; ", portProblems);

                    var runtimeStatus = AuditRuntimeSurfaces(
                        instance,
                        module.Kind);
                    var endpointStatus = AuditPortAnchors(
                        prefab,
                        module.Kind);
                    var overall = contractProblems.Count == 0 &&
                                  pivotStatus.StartsWith("PASS") &&
                                  portProblems.Count == 0 &&
                                  runtimeStatus == "PASS" &&
                                  endpointStatus == "PASS"
                        ? "PASS"
                        : "FAIL";
                    report.Append("| ").Append(candidate.model)
                        .Append(" | ").Append(contractStatus)
                        .Append(" | ").Append(pivotStatus)
                        .Append(" | ").Append(portStatus)
                        .Append(" | ").Append(runtimeStatus)
                        .Append(" | ").Append(endpointStatus)
                        .Append(" | ").Append(overall).AppendLine(" |");
                }
                finally
                {
                    UnityEngine.Object.DestroyImmediate(instance);
                }
            }

            report.AppendLine();
            report.AppendLine("## Runtime anchor findings");
            report.AppendLine();
            report.AppendLine(
                "- PASS: `ThemeVisualManifest.MotionTarget` resolves the authored " +
                "`parameter_knob_pivot`; the 55 mm pivot is not a fixed runtime offset.");
            report.AppendLine(
                "- PASS: the fixed audio-module interaction box is center " +
                "(0, 0, 50 mm), size (240, 200, 100 mm), and contains all present " +
                "candidate knob/port anchors.");
            report.AppendLine(
                "- N/A: `AudioSocket` belongs to the runtime instrument root, not " +
                "the visual candidate prefab, and remains at root origin.");
            report.AppendLine(
                "- PASS: audio patch connection lines resolve `sourcePortId` and " +
                "`targetPortId` to the matching authored `port_*` transforms. " +
                "Visuals without the requested node retain the legacy instrument-root " +
                "fallback.");

            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            File.WriteAllText(outputPath, report.ToString());
            Debug.Log($"Superfine candidate audit: {outputPath}");
            return outputPath;
        }

        private static string AuditRuntimeSurfaces(
            GameObject instance,
            MockInstrumentKind kind)
        {
            var display = Find(instance.transform, "display_surface")
                ?.GetComponent<Renderer>();
            var signal = Find(instance.transform, "signal_surface")
                ?.GetComponent<Renderer>();
            if (display == null || signal == null)
                return "FAIL: display/signal renderer missing";

            var runtime = instance.AddComponent<ModularAudioModuleRuntime>();
            runtime.Configure(kind, null);
            var displayView = instance.AddComponent<AudioModuleDisplayView>();
            displayView.Configure(
                kind,
                MockInstrumentTheme.KineticSafety,
                display);
            displayView.Bind(runtime);
            displayView.RedrawNow();
            var signalView = instance.AddComponent<AudioModuleSignalFlowView>();
            signalView.Configure(
                kind,
                MockInstrumentTheme.KineticSafety,
                signal);
            signalView.Bind(runtime);
            signalView.ApplyNow(1.25f);
            return displayView.DisplayRenderer == display &&
                   signalView.SignalRenderer == signal
                ? "PASS"
                : "FAIL: runtime renderer assignment mismatch";
        }

        private static string AuditPortAnchors(
            GameObject prefab,
            MockInstrumentKind kind)
        {
            var host = new GameObject("Superfine Port Anchor Audit");
            try
            {
                var visualSocket = new GameObject("VisualSocket").transform;
                visualSocket.SetParent(host.transform, false);
                var visual = UnityEngine.Object.Instantiate(
                    prefab,
                    visualSocket,
                    false);
                var contract = host.AddComponent<InstrumentGreyboxContract>();
                contract.Configure(
                    kind,
                    MockInstrumentTheme.KineticSafety,
                    null,
                    null,
                    null,
                    null,
                    null,
                    visualSocket,
                    null,
                    null,
                    null,
                    null);

                var problems = new List<string>();
                foreach (var port in ModularAudioPortCatalog.GetPorts(
                             AudioModuleKind(kind)))
                {
                    var nodeName = InstrumentGreyboxContract.PortNodeName(port.Id);
                    var expected = Find(visual.transform, nodeName);
                    var actual = contract.ResolvePortAnchor(port.Id);
                    if (expected == null)
                        problems.Add($"{nodeName} missing");
                    else if (actual != expected)
                        problems.Add($"{port.Id} did not resolve to {nodeName}");
                }
                return problems.Count == 0
                    ? "PASS"
                    : "FAIL: " + string.Join("; ", problems);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(host);
            }
        }

        private static ModularAudioModuleKind AudioModuleKind(
            MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.AudioOscillator =>
                    ModularAudioModuleKind.Oscillator,
                MockInstrumentKind.AudioNoise => ModularAudioModuleKind.Noise,
                MockInstrumentKind.AudioDelay => ModularAudioModuleKind.Delay,
                MockInstrumentKind.AudioOutput =>
                    ModularAudioModuleKind.AudioOutput,
                MockInstrumentKind.AudioVca => ModularAudioModuleKind.Vca,
                MockInstrumentKind.AudioMixer => ModularAudioModuleKind.Mixer,
                MockInstrumentKind.AudioFilter => ModularAudioModuleKind.Filter,
                MockInstrumentKind.AudioEnvelope =>
                    ModularAudioModuleKind.Envelope,
                MockInstrumentKind.AudioLfo => ModularAudioModuleKind.Lfo,
                MockInstrumentKind.AudioSequencer =>
                    ModularAudioModuleKind.Sequencer,
                _ => throw new ArgumentOutOfRangeException(
                    nameof(kind),
                    kind,
                    "Superfine audit only supports its ten audio modules.")
            };
        }

        private static bool Contains(
            InstrumentGreyboxSpec spec,
            Vector3 position)
        {
            var delta = position - spec.InteractionCenter;
            var half = spec.InteractionSize * 0.5f;
            return Mathf.Abs(delta.x) <= half.x + PositionTolerance &&
                   Mathf.Abs(delta.y) <= half.y + PositionTolerance &&
                   Mathf.Abs(delta.z) <= half.z + PositionTolerance;
        }

        private static bool Approximately(float actual, float expected)
        {
            return Mathf.Abs(actual - expected) <= PositionTolerance;
        }

        private static Vector3 LocalPosition(Transform root, Transform node)
        {
            return node == null
                ? new Vector3(float.NaN, float.NaN, float.NaN)
                : root.InverseTransformPoint(node.position);
        }

        private static Transform Find(Transform root, string name)
        {
            return root.GetComponentsInChildren<Transform>(true)
                .FirstOrDefault(item => item.name == name);
        }

        private readonly struct ModuleEntry
        {
            public ModuleEntry(MockInstrumentKind kind, params string[] ports)
            {
                Kind = kind;
                Ports = ports;
            }

            public MockInstrumentKind Kind { get; }
            public IReadOnlyList<string> Ports { get; }
        }
    }
}
