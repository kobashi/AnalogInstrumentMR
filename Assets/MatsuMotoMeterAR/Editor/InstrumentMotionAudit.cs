using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using MatsuMotoMeterAR.Instruments;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class InstrumentMotionAudit
    {
        private const string ReportDirectory = "Builds/Reports";
        private const float MinimumVisibleMotionMeters = 0.005f;
        private const float MinimumAxisAlignment = 0.98f;
        private const float MountPlaneTolerance = 0.002f;

        private static readonly MockInstrumentTheme[] Themes =
        {
            MockInstrumentTheme.OrbitalAnalog,
            MockInstrumentTheme.ForgeBrass,
            MockInstrumentTheme.KineticSafety,
            MockInstrumentTheme.MachinedErgonomics
        };

        private static readonly MockInstrumentKind[] Kinds =
        {
            MockInstrumentKind.Lever,
            MockInstrumentKind.ToggleSwitch,
            MockInstrumentKind.ThrottleLever,
            MockInstrumentKind.PowerSlider
        };

        [MenuItem("Tools/MatsuMotoMeterAR/Audit Control Motion")]
        public static void Run()
        {
            Directory.CreateDirectory(ReportDirectory);
            var report = new StringBuilder();
            report.AppendLine("# Instrument motion audit");
            report.AppendLine();
            report.AppendLine(
                "| Theme | Control | States | Visible travel | Axis alignment | " +
                "Minimum mount Z | Result |");
            report.AppendLine("| --- | --- | ---: | ---: | ---: | ---: | --- |");

            var failures = new List<string>();
            foreach (var theme in Themes)
            {
                foreach (var kind in Kinds)
                    AuditControl(theme, kind, report, failures);
                RenderContactSheet(theme);
            }

            var reportPath = Path.Combine(
                ReportDirectory,
                "instrument-motion-audit.md");
            File.WriteAllText(reportPath, report.ToString());
            AssetDatabase.Refresh();
            if (failures.Count > 0)
            {
                throw new InvalidOperationException(
                    "Instrument motion audit failed:\n" +
                    string.Join("\n", failures));
            }

            Debug.Log(
                $"Instrument motion audit passed: {Themes.Length * Kinds.Length} " +
                $"theme/control combinations. Report: {reportPath}");
        }

        private static void AuditControl(
            MockInstrumentTheme theme,
            MockInstrumentKind kind,
            StringBuilder report,
            List<string> failures)
        {
            var root = MockInstrumentFactory.Create(
                kind,
                new Pose(Vector3.zero, Quaternion.identity),
                preview: false,
                theme: theme);
            try
            {
                var interaction =
                    root.GetComponent<InstrumentGreyboxContract>()
                        ?.InstrumentInteraction;
                var motion = interaction?.Motion;
                if (motion?.MovingPart == null)
                {
                    AddFailure(
                        failures,
                        theme,
                        kind,
                        "missing moving part");
                    return;
                }

                var stateCount = StateCount(kind);
                var firstRotation = Quaternion.identity;
                var lastRotation = Quaternion.identity;
                var firstPosition = Vector3.zero;
                var lastPosition = Vector3.zero;
                var firstRendererCenter = Vector3.zero;
                var lastRendererCenter = Vector3.zero;
                var minimumMountZ = float.PositiveInfinity;
                for (var state = 0; state < stateCount; state++)
                {
                    interaction.SetNormalizedValue(
                        state / (float)(stateCount - 1));
                    var movingRenderer =
                        motion.MovingPart.GetComponentInChildren<Renderer>();
                    if (movingRenderer == null)
                    {
                        AddFailure(
                            failures,
                            theme,
                            kind,
                            "moving part has no renderer");
                        return;
                    }

                    minimumMountZ = Mathf.Min(
                        minimumMountZ,
                        MinimumLocalForward(
                            root.transform,
                            motion.MovingPart.GetComponentsInChildren<Renderer>()));
                    if (state == 0)
                    {
                        firstRotation = motion.MovingPart.rotation;
                        firstPosition = motion.MovingPart.position;
                        firstRendererCenter = movingRenderer.bounds.center;
                    }
                    if (state == stateCount - 1)
                    {
                        lastRotation = motion.MovingPart.rotation;
                        lastPosition = motion.MovingPart.position;
                        lastRendererCenter = movingRenderer.bounds.center;
                    }
                }

                var visibleTravel =
                    Vector3.Distance(firstRendererCenter, lastRendererCenter);
                var axisAlignment = AxisAlignment(
                    kind,
                    root.transform,
                    firstPosition,
                    lastPosition,
                    firstRotation,
                    lastRotation);
                var passed =
                    visibleTravel >= MinimumVisibleMotionMeters &&
                    axisAlignment >= MinimumAxisAlignment &&
                    minimumMountZ >= -MountPlaneTolerance;
                if (!passed)
                {
                    AddFailure(
                        failures,
                        theme,
                        kind,
                        $"travel={visibleTravel:F4}, axis={axisAlignment:F4}, " +
                        $"mountZ={minimumMountZ:F4}");
                }

                report.Append("| ")
                    .Append(theme)
                    .Append(" | ")
                    .Append(MockInstrumentCatalog.GetDisplayName(kind))
                    .Append(" | ")
                    .Append(stateCount)
                    .Append(" | ")
                    .Append(Format(visibleTravel))
                    .Append(" m | ")
                    .Append(Format(axisAlignment))
                    .Append(" | ")
                    .Append(Format(minimumMountZ))
                    .Append(" m | ")
                    .Append(passed ? "PASS" : "FAIL")
                    .AppendLine(" |");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static float AxisAlignment(
            MockInstrumentKind kind,
            Transform root,
            Vector3 firstPosition,
            Vector3 lastPosition,
            Quaternion firstRotation,
            Quaternion lastRotation)
        {
            if (kind == MockInstrumentKind.PowerSlider)
            {
                var movement = lastPosition - firstPosition;
                return movement.sqrMagnitude > 0.000001f
                    ? Mathf.Abs(Vector3.Dot(
                        movement.normalized,
                        root.up))
                    : 0f;
            }

            var delta = lastRotation * Quaternion.Inverse(firstRotation);
            delta.ToAngleAxis(out var angle, out var axis);
            if (angle > 180f)
                angle = 360f - angle;
            var expectedAxis =
                kind == MockInstrumentKind.Lever ||
                kind == MockInstrumentKind.ToggleSwitch ||
                kind == MockInstrumentKind.ThrottleLever
                    ? root.right
                    : root.forward;
            return angle > 1f
                ? Mathf.Abs(Vector3.Dot(
                    axis.normalized,
                    expectedAxis))
                : 0f;
        }

        private static float MinimumLocalForward(
            Transform root,
            IReadOnlyList<Renderer> renderers)
        {
            var minimum = float.PositiveInfinity;
            foreach (var renderer in renderers)
            {
                var bounds = renderer.bounds;
                for (var x = -1; x <= 1; x += 2)
                {
                    for (var y = -1; y <= 1; y += 2)
                    {
                        for (var z = -1; z <= 1; z += 2)
                        {
                            var corner = bounds.center +
                                         Vector3.Scale(
                                             bounds.extents,
                                             new Vector3(x, y, z));
                            minimum = Mathf.Min(
                                minimum,
                                root.InverseTransformPoint(corner).z);
                        }
                    }
                }
            }
            return minimum;
        }

        private static void RenderContactSheet(MockInstrumentTheme theme)
        {
            var roots = new List<GameObject>();
            var cameraObject = new GameObject("[Audit] Camera");
            var lightObject = new GameObject("[Audit] Light");
            var camera = cameraObject.AddComponent<Camera>();
            var light = lightObject.AddComponent<Light>();
            try
            {
                var slot = 0;
                const int columns = 6;
                foreach (var kind in Kinds)
                {
                    var stateCount = StateCount(kind);
                    for (var state = 0; state < stateCount; state++)
                    {
                        var column = slot % columns;
                        var row = slot / columns;
                        var root = MockInstrumentFactory.Create(
                            kind,
                            new Pose(
                                new Vector3(
                                    (column - 2.5f) * 0.34f,
                                    (2f - row) * 0.42f,
                                    0f),
                                Quaternion.identity),
                            preview: false,
                            theme: theme);
                        root.GetComponent<InstrumentGreyboxContract>()
                            ?.InstrumentInteraction
                            ?.SetNormalizedValue(
                                state / (float)(stateCount - 1));
                        roots.Add(root);
                        slot++;
                    }
                }

                camera.orthographic = true;
                camera.orthographicSize = 1.15f;
                camera.aspect = 4f / 3f;
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = new Color(0.012f, 0.018f, 0.025f);
                camera.transform.SetPositionAndRotation(
                    new Vector3(0f, 0f, 3f),
                    Quaternion.Euler(0f, 180f, 0f));
                light.type = LightType.Directional;
                light.intensity = 1.2f;
                light.transform.rotation = Quaternion.Euler(35f, -35f, 0f);

                const int width = 1600;
                const int height = 1200;
                var target = new RenderTexture(
                    width,
                    height,
                    24,
                    RenderTextureFormat.ARGB32);
                var previousActive = RenderTexture.active;
                camera.targetTexture = target;
                camera.Render();
                RenderTexture.active = target;
                var image = new Texture2D(
                    width,
                    height,
                    TextureFormat.RGBA32,
                    false);
                image.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                image.Apply();
                File.WriteAllBytes(
                    Path.Combine(
                        ReportDirectory,
                        $"instrument-motion-{theme}.png"),
                    image.EncodeToPNG());
                camera.targetTexture = null;
                RenderTexture.active = previousActive;
                UnityEngine.Object.DestroyImmediate(image);
                UnityEngine.Object.DestroyImmediate(target);
            }
            finally
            {
                foreach (var root in roots)
                    UnityEngine.Object.DestroyImmediate(root);
                UnityEngine.Object.DestroyImmediate(cameraObject);
                UnityEngine.Object.DestroyImmediate(lightObject);
            }
        }

        private static int StateCount(MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.Lever =>
                    MockInstrumentMotion.LeverDetentCount,
                MockInstrumentKind.ToggleSwitch => 2,
                MockInstrumentKind.ThrottleLever =>
                    MockInstrumentMotion.ThrottleDetentCount,
                MockInstrumentKind.PowerSlider =>
                    MockInstrumentMotion.PowerSliderDetentCount,
                _ => 2
            };
        }

        private static void AddFailure(
            ICollection<string> failures,
            MockInstrumentTheme theme,
            MockInstrumentKind kind,
            string reason)
        {
            failures.Add($"{theme}/{kind}: {reason}");
        }

        private static string Format(float value)
        {
            return value.ToString("0.0000", CultureInfo.InvariantCulture);
        }
    }
}
