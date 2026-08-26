using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class Theme4Phase1RawImportValidator
    {
        private const string SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics";
        private const string StagingRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging/Theme4_P1_Raw/Models/MachinedErgonomics";
        private const string ReportPath =
            "Builds/Reports/candidate-Theme4_P1-raw-import-validation.md";
        private const float BoundsTolerance = 0.002f;
        private const float CenterTolerance = 0.0001f;

        private static readonly AssetSpec[] Assets =
        {
            new(
                "MeterRound",
                "SM_MeterRound_MachinedErgonomics_V6_Opus5_P1.fbx",
                "PF_Visual_MeterRound_MachinedErgonomics_V6",
                "needle_pivot",
                "needle",
                Vector3.forward,
                new Vector3(0f, 0f, 0.052f),
                -115f,
                115f,
                2984,
                2,
                new Vector3(0.136f, 0.136174f, 0.064f),
                new Vector3(0f, 0.000583f, 0.032f),
                new Vector3(0.136f, 0.136174f, 0.064f),
                "034532bf845210f35c39d9a247536aedac6b1d60246078c74fdfdfa78d56f132"),
            new(
                "Lever",
                "SM_Lever_MachinedErgonomics_V6_Opus5_P1.fbx",
                "PF_Visual_Lever_MachinedErgonomics_V6",
                "handle_pivot",
                "handle",
                Vector3.right,
                new Vector3(0f, 0.080f, 0.018f),
                -48f,
                0f,
                4032,
                2,
                new Vector3(0.238811f, 0.438811f, 0.143796f),
                new Vector3(0f, 0f, 0.141581f),
                new Vector3(0.238810f, 0.438810f, 0.283162f),
                "9780c0b5c189498ad1f5254c45ea24584d582a1709d0d6199a5893ca547c5b42"),
            new(
                "Toggle",
                "SM_Toggle_MachinedErgonomics_V6_Opus5_P1.fbx",
                "PF_Visual_Toggle_MachinedErgonomics_V6",
                "switch_pivot",
                "switch",
                Vector3.right,
                new Vector3(0f, 0f, 0.042f),
                -56f,
                0f,
                2548,
                2,
                new Vector3(0.119084f, 0.169084f, 0.061f),
                new Vector3(0f, 0f, 0.053920f),
                new Vector3(0.119084f, 0.169084f, 0.107839f),
                "7870ef90a2c828031407cc169ffac2242552ab95c731b3f9c368d486fb4f0c56")
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build and Validate Phase 1 Raw FBX")]
        public static void BuildAndValidate()
        {
            Directory.CreateDirectory(StagingRoot);
            foreach (var spec in Assets)
            {
                var source = $"{SourceRoot}/{spec.FileName}";
                if (!File.Exists(source))
                    throw new FileNotFoundException("Theme 4 source FBX is missing.", source);
                var actualSha = Sha256(source);
                if (!string.Equals(actualSha, spec.Sha256, StringComparison.Ordinal))
                {
                    throw new InvalidDataException(
                        $"Theme 4 source SHA mismatch for {spec.Key}: {actualSha}");
                }
                File.Copy(source, $"{StagingRoot}/{spec.FileName}", true);
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var spec in Assets)
                ConfigureModelImporter($"{StagingRoot}/{spec.FileName}");
            ValidateImportedAssets();
        }

        private static void ConfigureModelImporter(string path)
        {
            if (AssetImporter.GetAtPath(path) is not ModelImporter importer)
                throw new FileNotFoundException("Theme 4 model importer is missing.", path);
            importer.bakeAxisConversion = true;
            importer.globalScale = 1f;
            importer.importAnimation = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.addCollider = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            importer.SaveAndReimport();
        }

        private static void ValidateImportedAssets()
        {
            var failures = new List<string>();
            var report = new StringBuilder();
            report.AppendLine("# Theme 4 Phase 1 raw FBX import validation");
            report.AppendLine();
            report.AppendLine(
                "Isolated raw-import check only. No active prefab, runtime theme, " +
                "material, or production asset was changed.");
            report.AppendLine();
            report.AppendLine(
                "| Asset | Triangles | Renderers | Pivot m | Rest bounds m | Swept collider m | Mount | Result |");
            report.AppendLine("| --- | ---: | ---: | --- | --- | --- | --- | --- |");

            foreach (var spec in Assets)
                ValidateAsset(spec, report, failures);

            report.AppendLine();
            report.AppendLine(failures.Count == 0 ? "Result: **PASS**" : "Result: **FAIL**");
            if (failures.Count > 0)
            {
                report.AppendLine();
                report.AppendLine("## Failures");
                report.AppendLine();
                foreach (var failure in failures)
                    report.AppendLine($"- {failure}");
            }

            Directory.CreateDirectory(Path.GetDirectoryName(ReportPath) ?? "Builds/Reports");
            File.WriteAllText(ReportPath, report.ToString());
            AssetDatabase.Refresh();
            if (failures.Count > 0)
            {
                throw new InvalidOperationException(
                    "Theme 4 Phase 1 raw FBX validation failed. See " + ReportPath);
            }
            Debug.Log("Theme 4 Phase 1 raw FBX validation PASS: " + ReportPath);
        }

        private static void ValidateAsset(
            AssetSpec spec,
            StringBuilder report,
            ICollection<string> failures)
        {
            var path = $"{StagingRoot}/{spec.FileName}";
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null)
            {
                failures.Add($"{spec.Key}: Unity could not load {path}.");
                AppendRow(
                    report,
                    spec,
                    0,
                    0,
                    default,
                    default,
                    default,
                    0f,
                    false,
                    false);
                return;
            }

            var coordinateRoot = new GameObject($"{spec.Key} Unity Coordinate Root");
            var instance = UnityEngine.Object.Instantiate(prefab, coordinateRoot.transform, false);
            instance.name = prefab.name;
            instance.transform.localPosition = Vector3.zero;
            instance.transform.localRotation = Quaternion.Euler(-90f, 0f, 0f);
            instance.transform.localScale = Vector3.one;
            try
            {
                var pivot = Find(instance.transform, spec.PivotName);
                var movingPart = Find(instance.transform, spec.MovingPartName);
                if (pivot == null)
                    failures.Add($"{spec.Key}: missing pivot {spec.PivotName}.");
                if (movingPart == null || movingPart.parent != pivot)
                {
                    failures.Add(
                        $"{spec.Key}: {spec.MovingPartName} is missing or is not a direct child of " +
                        $"{spec.PivotName}.");
                }

                var pivotPosition = pivot != null
                    ? coordinateRoot.transform.InverseTransformPoint(pivot.position)
                    : Vector3.positiveInfinity;

                var meshFilters = instance.GetComponentsInChildren<MeshFilter>(true);
                var renderers = instance.GetComponentsInChildren<Renderer>(true);
                var triangles = 0;
                var submeshes = 0;
                foreach (var filter in meshFilters)
                {
                    if (filter.sharedMesh == null)
                        continue;
                    triangles += filter.sharedMesh.triangles.Length / 3;
                    submeshes += filter.sharedMesh.subMeshCount;
                }

                var rest = VertexBounds(coordinateRoot.transform, meshFilters);
                var union = rest;
                var minimumMovingZ = float.PositiveInfinity;
                if (pivot != null)
                {
                    var movingFilters = movingPart != null
                        ? movingPart.GetComponentsInChildren<MeshFilter>(true)
                        : Array.Empty<MeshFilter>();
                    var motionProxy = new GameObject($"{spec.PivotName} Runtime Motion").transform;
                    motionProxy.SetParent(coordinateRoot.transform, false);
                    motionProxy.position = pivot.position;
                    motionProxy.rotation = coordinateRoot.transform.rotation;
                    pivot.SetParent(motionProxy, true);
                    for (var index = 0; index <= 96; index++)
                    {
                        var angle = Mathf.Lerp(
                            spec.MinimumAngle,
                            spec.MaximumAngle,
                            index / 96f);
                        motionProxy.localRotation = Quaternion.AngleAxis(angle, spec.Axis);
                        union.Encapsulate(VertexBounds(coordinateRoot.transform, meshFilters));
                        if (movingFilters.Length > 0)
                        {
                            minimumMovingZ = Mathf.Min(
                                minimumMovingZ,
                                VertexBounds(coordinateRoot.transform, movingFilters).min.z);
                        }
                    }
                }

                var expectedClearance = ExpectedMountClearance(spec.Key);
                var mountOk = rest.min.z >= -BoundsTolerance &&
                              minimumMovingZ >= -BoundsTolerance;
                var passed = true;
                passed &= CheckEqual(spec, "triangles", triangles, spec.Triangles, failures);
                passed &= CheckEqual(spec, "renderers", renderers.Length, spec.Renderers, failures);
                passed &= CheckEqual(spec, "submeshes", submeshes, 2, failures);
                if (pivot != null)
                {
                    passed &= CheckVector(
                        spec,
                        "pivot position",
                        pivotPosition,
                        spec.PivotPosition,
                        failures,
                        CenterTolerance);
                }
                passed &= CheckVector(spec, "rest bounds", rest.size, spec.RestSize, failures);
                passed &= CheckVector(spec, "swept size", union.size, spec.SweptSize, failures);
                passed &= CheckVector(
                    spec,
                    "swept centre",
                    union.center,
                    spec.SweptCenter,
                    failures,
                    CenterTolerance);
                if (Mathf.Abs(minimumMovingZ - expectedClearance) > BoundsTolerance)
                {
                    failures.Add(
                        $"{spec.Key}: moving-part mount clearance {minimumMovingZ:F6}, " +
                        $"expected {expectedClearance:F6}.");
                    passed = false;
                }
                if (!mountOk)
                {
                    failures.Add($"{spec.Key}: rest visual extends behind mount plane ({rest.min.z:F6} m).");
                    passed = false;
                }

                AppendRow(
                    report,
                    spec,
                    triangles,
                    renderers.Length,
                    pivotPosition,
                    rest,
                    union,
                    minimumMovingZ,
                    mountOk,
                    passed);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(coordinateRoot);
            }
        }

        private static Bounds VertexBounds(Transform root, MeshFilter[] filters)
        {
            var initialized = false;
            var result = new Bounds();
            foreach (var filter in filters)
            {
                var mesh = filter.sharedMesh;
                if (mesh == null)
                    continue;
                foreach (var vertex in mesh.vertices)
                {
                    var local = root.InverseTransformPoint(
                        filter.transform.TransformPoint(vertex));
                    if (!initialized)
                    {
                        result = new Bounds(local, Vector3.zero);
                        initialized = true;
                    }
                    else
                    {
                        result.Encapsulate(local);
                    }
                }
            }
            return result;
        }

        private static Transform Find(Transform root, string name)
        {
            foreach (var candidate in root.GetComponentsInChildren<Transform>(true))
            {
                if (candidate.name == name)
                    return candidate;
            }
            return null;
        }

        private static bool CheckEqual(
            AssetSpec spec,
            string label,
            int actual,
            int expected,
            ICollection<string> failures)
        {
            if (actual == expected)
                return true;
            failures.Add($"{spec.Key}: {label} {actual}, expected {expected}.");
            return false;
        }

        private static bool CheckVector(
            AssetSpec spec,
            string label,
            Vector3 actual,
            Vector3 expected,
            ICollection<string> failures,
            float tolerance = BoundsTolerance)
        {
            if ((actual - expected).magnitude <= tolerance)
                return true;
            failures.Add(
                $"{spec.Key}: {label} {Format(actual)}, expected {Format(expected)}.");
            return false;
        }

        private static void AppendRow(
            StringBuilder report,
            AssetSpec spec,
            int triangles,
            int renderers,
            Vector3 pivotPosition,
            Bounds rest,
            Bounds swept,
            float minimumMovingZ,
            bool mountOk,
            bool passed)
        {
            report.AppendLine(
                $"| {spec.Key} | {triangles} | {renderers} | {Format(pivotPosition)} | " +
                $"{Format(rest.size)} | " +
                $"{Format(swept.size)} @ {Format(swept.center)} | " +
                $"{(mountOk ? "PASS" : "FAIL")} ({minimumMovingZ * 1000f:F3} mm) | " +
                $"{(passed ? "PASS" : "FAIL")} |");
        }

        private static float ExpectedMountClearance(string key) => key switch
        {
            "MeterRound" => 0.0525f,
            "Lever" => 0.011402f,
            "Toggle" => 0.0338f,
            _ => 0f
        };

        private static string Format(Vector3 value) =>
            $"{value.x:F6} × {value.y:F6} × {value.z:F6}";

        private static string Sha256(string path)
        {
            using var stream = File.OpenRead(path);
            using var sha = SHA256.Create();
            return BitConverter.ToString(sha.ComputeHash(stream))
                .Replace("-", string.Empty)
                .ToLowerInvariant();
        }

        private sealed class AssetSpec
        {
            public AssetSpec(
                string key,
                string fileName,
                string rootName,
                string pivotName,
                string movingPartName,
                Vector3 axis,
                Vector3 pivotPosition,
                float minimumAngle,
                float maximumAngle,
                int triangles,
                int renderers,
                Vector3 restSize,
                Vector3 sweptCenter,
                Vector3 sweptSize,
                string sha256)
            {
                Key = key;
                FileName = fileName;
                RootName = rootName;
                PivotName = pivotName;
                MovingPartName = movingPartName;
                Axis = axis;
                PivotPosition = pivotPosition;
                MinimumAngle = minimumAngle;
                MaximumAngle = maximumAngle;
                Triangles = triangles;
                Renderers = renderers;
                RestSize = restSize;
                SweptCenter = sweptCenter;
                SweptSize = sweptSize;
                Sha256 = sha256;
            }

            public string Key { get; }
            public string FileName { get; }
            public string RootName { get; }
            public string PivotName { get; }
            public string MovingPartName { get; }
            public Vector3 Axis { get; }
            public Vector3 PivotPosition { get; }
            public float MinimumAngle { get; }
            public float MaximumAngle { get; }
            public int Triangles { get; }
            public int Renderers { get; }
            public Vector3 RestSize { get; }
            public Vector3 SweptCenter { get; }
            public Vector3 SweptSize { get; }
            public string Sha256 { get; }
        }
    }
}
