using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using MatsuMotoMeterAR.Instruments;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class Opus5R2CandidateMotionAudit
    {
        private const string Opus5R2ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Opus5_R2.json";
        private const string MeterM2n5ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n5.json";
        private const string MeterM2n7ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n7.json";
        private const string MeterM2n8ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n8.json";
        private const float MinimumVisibleMotionMeters = 0.005f;
        private const float MinimumVisibleRotationDegrees = 5f;
        private const float MinimumAxisAlignment = 0.98f;
        private const float MountPlaneTolerance = 0.002f;

        private static readonly AuditEntry[] Entries =
        {
            new(
                "MeterRound",
                MockInstrumentMotion.MotionKind.Meter,
                5,
                Vector3.forward,
                InstrumentGreyboxSpecification.MeterSweepDegrees,
                0f,
                AuditMode.Rotation),
            new(
                "MeterMedium",
                MockInstrumentMotion.MotionKind.Meter,
                5,
                Vector3.forward,
                InstrumentGreyboxSpecification.MeterSweepDegrees,
                0f,
                AuditMode.Rotation),
            new(
                "MeterLarge",
                MockInstrumentMotion.MotionKind.Meter,
                5,
                Vector3.forward,
                InstrumentGreyboxSpecification.MeterSweepDegrees,
                0f,
                AuditMode.Rotation),
            new(
                "Lever",
                MockInstrumentMotion.MotionKind.Lever,
                MockInstrumentMotion.LeverDetentCount,
                Vector3.right,
                InstrumentGreyboxSpecification.LeverMaximumAngleDegrees,
                -InstrumentGreyboxSpecification.LeverMaximumAngleDegrees,
                AuditMode.Rotation),
            new(
                "Toggle",
                MockInstrumentMotion.MotionKind.Toggle,
                3,
                Vector3.right,
                28f,
                -28f,
                AuditMode.Rotation),
            new(
                "Rotary",
                MockInstrumentMotion.MotionKind.Rotate,
                5,
                Vector3.forward,
                1f,
                0f,
                AuditMode.Rotation),
            new(
                "Button",
                MockInstrumentMotion.MotionKind.Press,
                3,
                Vector3.back,
                0.014f,
                0f,
                AuditMode.Translation),
            new(
                "Throttle",
                MockInstrumentMotion.MotionKind.Throttle,
                MockInstrumentMotion.ThrottleDetentCount,
                Vector3.right,
                InstrumentGreyboxSpecification.ThrottleMaximumAngleDegrees,
                -InstrumentGreyboxSpecification.ThrottleMaximumAngleDegrees,
                AuditMode.Rotation),
            new(
                "PowerSlider",
                MockInstrumentMotion.MotionKind.PowerSlider,
                MockInstrumentMotion.PowerSliderDetentCount,
                Vector3.up,
                InstrumentGreyboxSpecification.PowerSliderTravelMeters,
                0f,
                AuditMode.Translation),
            new(
                "WindowMeter",
                MockInstrumentMotion.MotionKind.Meter,
                5,
                Vector3.forward,
                InstrumentGreyboxSpecification.MeterSweepDegrees,
                0f,
                AuditMode.Rotation),
            new(
                "WindowPanel",
                MockInstrumentMotion.MotionKind.Meter,
                5,
                Vector3.forward,
                InstrumentGreyboxSpecification.MeterSweepDegrees,
                0f,
                AuditMode.Rotation)
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Audit Opus 5 R2 Candidate Motion")]
        public static void Run()
        {
            AuditManifest(Opus5R2ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Audit Selected Candidate Manifest Motion")]
        public static void RunSelected()
        {
            AuditManifest(CandidateStagingManifest.SelectedAssetPath());
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Audit Meter M2n5 Candidate Motion")]
        public static void RunMeterM2n5()
        {
            AuditManifest(MeterM2n5ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Audit Meter M2n7 Candidate Motion")]
        public static void RunMeterM2n7()
        {
            AuditManifest(MeterM2n7ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Audit Meter M2n8 Candidate Motion")]
        public static void RunMeterM2n8()
        {
            AuditManifest(MeterM2n8ManifestPath);
        }

        internal static string AuditManifest(string manifestPath)
        {
            var manifest = CandidateStagingManifest.Load(manifestPath);
            var reportPath =
                $"Builds/Reports/candidate-{manifest.candidateId}-" +
                "motion-audit.md";
            var report = new StringBuilder();
            report.AppendLine(
                $"# Candidate {manifest.candidateId} motion audit");
            report.AppendLine();
            report.AppendLine(
                "| Control | States | Linear travel | Angular travel | " +
                "Axis alignment | Minimum mount Z | Result |");
            report.AppendLine(
                "| --- | ---: | ---: | ---: | ---: | ---: | --- |");
            var failures = new List<string>();
            var audited = 0;
            foreach (var candidate in manifest.entries)
            {
                if (!TryFindEntry(candidate.model, out var entry))
                    continue;
                Audit(
                    manifest.CandidatePrefabPath(candidate),
                    $"{candidate.theme}/{candidate.model}",
                    entry,
                    report,
                    failures);
                audited++;
            }

            Directory.CreateDirectory(Path.GetDirectoryName(reportPath));
            File.WriteAllText(reportPath, report.ToString());
            AssetDatabase.Refresh();
            if (failures.Count > 0)
            {
                throw new InvalidOperationException(
                    $"Candidate {manifest.candidateId} motion audit failed:\n" +
                    string.Join("\n", failures));
            }

            Debug.Log(
                $"Candidate {manifest.candidateId} motion audit passed: " +
                $"{audited}/{audited}; static entries skipped=" +
                $"{manifest.entries.Length - audited}. Report: {reportPath}");
            return reportPath;
        }

        private static void Audit(
            string path,
            string label,
            AuditEntry entry,
            StringBuilder report,
            ICollection<string> failures)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null)
            {
                failures.Add($"{label}: missing prefab {path}");
                return;
            }

            var instance = PrefabUtility.InstantiatePrefab(prefab) as GameObject;
            if (instance == null)
            {
                failures.Add($"{label}: could not instantiate prefab");
                return;
            }
            if (PrefabUtility.IsPartOfPrefabInstance(instance))
            {
                PrefabUtility.UnpackPrefabInstance(
                    instance,
                    PrefabUnpackMode.Completely,
                    InteractionMode.AutomatedAction);
            }

            try
            {
                instance.transform.SetPositionAndRotation(
                    Vector3.zero,
                    Quaternion.identity);
                var visualManifest = instance.GetComponent<ThemeVisualManifest>();
                if (visualManifest?.MotionTarget == null)
                {
                    failures.Add($"{label}: missing motion target");
                    return;
                }

                var movingPart = CreateRuntimeMotionTarget(
                    visualManifest.MotionTarget,
                    instance.transform);
                var logic = new GameObject("[Audit] Logic");
                logic.transform.SetParent(instance.transform, false);
                var motion = logic.AddComponent<MockInstrumentMotion>();
                motion.Configure(
                    entry.MotionKind,
                    movingPart,
                    entry.Axis,
                    entry.Range,
                    0f,
                    rotationOffset: entry.RotationOffset);

                var previousRotation = Quaternion.identity;
                var firstCenter = Vector3.zero;
                var maximumLinearTravel = 0f;
                var cumulativeAngularTravel = 0f;
                var maximumAxisAlignment = 0f;
                var minimumMountZ = float.PositiveInfinity;
                for (var state = 0; state < entry.StateCount; state++)
                {
                    motion.SetNormalizedValue(
                        state / (float)(entry.StateCount - 1));
                    var renderer =
                        movingPart.GetComponentInChildren<Renderer>(true);
                    if (renderer == null)
                    {
                        failures.Add(
                            $"{label}: moving part has no renderer");
                        return;
                    }

                    minimumMountZ = Mathf.Min(
                        minimumMountZ,
                        MinimumLocalForward(
                            instance.transform,
                            movingPart.GetComponentsInChildren<Renderer>(true)));
                    if (state == 0)
                    {
                        previousRotation = movingPart.rotation;
                        firstCenter = renderer.bounds.center;
                    }
                    else
                    {
                        maximumLinearTravel = Mathf.Max(
                            maximumLinearTravel,
                            Vector3.Distance(
                                firstCenter,
                                renderer.bounds.center));
                        var delta =
                            movingPart.rotation *
                            Quaternion.Inverse(previousRotation);
                        delta.ToAngleAxis(out var angle, out var axis);
                        if (angle > 180f)
                            angle = 360f - angle;
                        cumulativeAngularTravel += angle;
                        previousRotation = movingPart.rotation;
                        if (angle > 1f)
                        {
                            maximumAxisAlignment = Mathf.Max(
                                maximumAxisAlignment,
                                Mathf.Abs(Vector3.Dot(
                                    axis.normalized,
                                    instance.transform.TransformDirection(
                                        entry.Axis).normalized)));
                        }
                    }
                }

                var visibleMotionPassed = entry.Mode == AuditMode.Rotation
                    ? cumulativeAngularTravel >= MinimumVisibleRotationDegrees &&
                      maximumAxisAlignment >= MinimumAxisAlignment
                    : maximumLinearTravel >= MinimumVisibleMotionMeters;
                var passed = visibleMotionPassed &&
                             minimumMountZ >= -MountPlaneTolerance;
                if (!passed)
                {
                    failures.Add(
                        $"{label}: linear={maximumLinearTravel:F4}, " +
                        $"angular={cumulativeAngularTravel:F2}, " +
                        $"axis={maximumAxisAlignment:F4}, " +
                        $"mountZ={minimumMountZ:F4}");
                }

                report.Append("| ")
                    .Append(label)
                    .Append(" | ")
                    .Append(entry.StateCount)
                    .Append(" | ")
                    .Append(maximumLinearTravel.ToString("F4"))
                    .Append(" m | ")
                    .Append(cumulativeAngularTravel.ToString("F2"))
                    .Append("° | ")
                    .Append(entry.Mode == AuditMode.Rotation
                        ? maximumAxisAlignment.ToString("F4")
                        : "n/a")
                    .Append(" | ")
                    .Append(minimumMountZ.ToString("F4"))
                    .Append(" m | ")
                    .Append(passed ? "PASS" : "FAIL")
                    .AppendLine(" |");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static bool TryFindEntry(string key, out AuditEntry result)
        {
            foreach (var entry in Entries)
            {
                if (entry.Key != key)
                    continue;
                result = entry;
                return true;
            }
            result = default;
            return false;
        }

        private static Transform CreateRuntimeMotionTarget(
            Transform source,
            Transform coordinateRoot)
        {
            var proxy = new GameObject(
                $"{source.name} Runtime Motion").transform;
            proxy.SetParent(coordinateRoot, false);
            proxy.position = source.position;
            proxy.rotation = coordinateRoot.rotation;
            proxy.localScale = Vector3.one;
            source.SetParent(proxy, true);
            return proxy;
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

        private readonly struct AuditEntry
        {
            public AuditEntry(
                string key,
                MockInstrumentMotion.MotionKind motionKind,
                int stateCount,
                Vector3 axis,
                float range,
                float rotationOffset,
                AuditMode mode)
            {
                Key = key;
                MotionKind = motionKind;
                StateCount = stateCount;
                Axis = axis;
                Range = range;
                RotationOffset = rotationOffset;
                Mode = mode;
            }

            public string Key { get; }
            public MockInstrumentMotion.MotionKind MotionKind { get; }
            public int StateCount { get; }
            public Vector3 Axis { get; }
            public float Range { get; }
            public float RotationOffset { get; }
            public AuditMode Mode { get; }
        }

        private enum AuditMode
        {
            Rotation,
            Translation
        }
    }
}
