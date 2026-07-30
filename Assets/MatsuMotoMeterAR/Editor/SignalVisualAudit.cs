using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;
using MatsuMotoMeterAR.Signals;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class SignalVisualAudit
    {
        private const string ReportPath =
            "Builds/Reports/signal-visual-audit.md";

        private static readonly int BaseColorId =
            Shader.PropertyToID("_BaseColor");
        private static readonly int ColorId =
            Shader.PropertyToID("_Color");

        private static readonly MockInstrumentTheme[] Themes =
        {
            MockInstrumentTheme.OrbitalAnalog,
            MockInstrumentTheme.ForgeBrass,
            MockInstrumentTheme.KineticSafety
        };

        [MenuItem("Tools/MatsuMotoMeterAR/Audit Signal Visuals")]
        public static void Run()
        {
            var report = new StringBuilder();
            report.AppendLine("# Signal visual audit");
            report.AppendLine();
            report.AppendLine(
                "| Theme | Target | Signal states | Visual delta | Result |");
            report.AppendLine("| --- | --- | --- | ---: | --- |");
            var failures = new List<string>();

            foreach (var theme in Themes)
            {
                AuditLamp(theme, report, failures);
                AuditStatus(theme, report, failures);
            }

            Directory.CreateDirectory(
                Path.GetDirectoryName(ReportPath) ??
                "Builds/Reports");
            File.WriteAllText(ReportPath, report.ToString());
            AssetDatabase.Refresh();
            if (failures.Count > 0)
            {
                throw new InvalidOperationException(
                    "Signal visual audit failed:\n" +
                    string.Join("\n", failures));
            }

            Debug.Log(
                $"Signal visual audit passed: {Themes.Length * 2} " +
                $"theme/target combinations. Report: {ReportPath}");
        }

        private static void AuditLamp(
            MockInstrumentTheme theme,
            StringBuilder report,
            ICollection<string> failures)
        {
            var sourceRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.RotaryKnob,
                Pose.identity,
                theme: theme);
            var targetRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.IndicatorLamp,
                Pose.identity,
                theme: theme);
            try
            {
                var source = Interaction(sourceRoot);
                var target = Interaction(targetRoot);
                var manifest = targetRoot.GetComponentInChildren<
                    ThemeVisualManifest>();
                var renderer = manifest?.IndicatorRenderer;
                if (renderer == null)
                {
                    AddFailure(
                        failures,
                        theme,
                        "Lamp",
                        "missing indicator renderer");
                    return;
                }

                source.SetNormalizedValue(0f);
                Evaluate(source, target);
                var off = ReadColor(renderer);
                source.SetNormalizedValue(1f);
                Evaluate(source, target);
                var on = ReadColor(renderer);
                var delta = ColorDelta(off, on);
                var passed =
                    Mathf.Approximately(target.NormalizedValue, 1f) &&
                    delta > 0.25f;
                Append(
                    report,
                    theme,
                    "Lamp",
                    "0.00 → 1.00",
                    delta,
                    passed);
                if (!passed)
                {
                    AddFailure(
                        failures,
                        theme,
                        "Lamp",
                        $"normalized={target.NormalizedValue:F2}, " +
                        $"visualDelta={delta:F3}");
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(sourceRoot);
                UnityEngine.Object.DestroyImmediate(targetRoot);
            }
        }

        private static void AuditStatus(
            MockInstrumentTheme theme,
            StringBuilder report,
            ICollection<string> failures)
        {
            var sourceRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.RotaryKnob,
                Pose.identity,
                theme: theme);
            var targetRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.StatusIndicator,
                Pose.identity,
                theme: theme);
            try
            {
                var source = Interaction(sourceRoot);
                var target = Interaction(targetRoot);
                var manifest = targetRoot.GetComponentInChildren<
                    ThemeVisualManifest>();
                var states = manifest?.StateRenderers;
                if (states == null || states.Length < 3)
                {
                    AddFailure(
                        failures,
                        theme,
                        "Status",
                        "missing SAFE/WARN/DANGER renderers");
                    return;
                }

                source.SetNormalizedValue(0f);
                Evaluate(source, target);
                var off = ReadColor(states[2]);
                source.SetNormalizedValue(1f);
                Evaluate(source, target);
                var danger = ReadColor(states[2]);
                var delta = ColorDelta(off, danger);
                var passed =
                    target.StateName == "DANGER" &&
                    delta > 0.25f;
                Append(
                    report,
                    theme,
                    "Status",
                    "OFF → DANGER",
                    delta,
                    passed);
                if (!passed)
                {
                    AddFailure(
                        failures,
                        theme,
                        "Status",
                        $"state={target.StateName}, " +
                        $"visualDelta={delta:F3}");
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(sourceRoot);
                UnityEngine.Object.DestroyImmediate(targetRoot);
            }
        }

        private static void Evaluate(
            MockInstrumentInteraction source,
            MockInstrumentInteraction target)
        {
            var instruments = new Dictionary<
                string,
                MockInstrumentInteraction>
            {
                ["source"] = source,
                ["target"] = target
            };
            var connections = new[]
            {
                new SignalConnectionRecord
                {
                    connectionId = "audit",
                    sourcePlacementId = "source",
                    targetPlacementId = "target",
                    transformKind = (int)SignalTransformKind.Direct
                }
            };
            new SignalGraphEvaluator().Evaluate(
                connections,
                instruments);
        }

        private static MockInstrumentInteraction Interaction(
            GameObject root)
        {
            return root.GetComponent<InstrumentGreyboxContract>()
                .InstrumentInteraction;
        }

        private static Color ReadColor(Renderer renderer)
        {
            var properties = new MaterialPropertyBlock();
            renderer.GetPropertyBlock(properties);
            if (renderer.sharedMaterial != null &&
                renderer.sharedMaterial.HasProperty(BaseColorId))
            {
                return properties.GetColor(BaseColorId);
            }
            return properties.GetColor(ColorId);
        }

        private static float ColorDelta(Color a, Color b)
        {
            return Mathf.Max(
                Mathf.Abs(a.r - b.r),
                Mathf.Abs(a.g - b.g),
                Mathf.Abs(a.b - b.b));
        }

        private static void Append(
            StringBuilder report,
            MockInstrumentTheme theme,
            string target,
            string states,
            float delta,
            bool passed)
        {
            report.Append("| ")
                .Append(theme)
                .Append(" | ")
                .Append(target)
                .Append(" | ")
                .Append(states)
                .Append(" | ")
                .Append(delta.ToString("F3"))
                .Append(" | ")
                .Append(passed ? "PASS" : "FAIL")
                .AppendLine(" |");
        }

        private static void AddFailure(
            ICollection<string> failures,
            MockInstrumentTheme theme,
            string target,
            string problem)
        {
            failures.Add($"{theme}/{target}: {problem}");
        }
    }
}
