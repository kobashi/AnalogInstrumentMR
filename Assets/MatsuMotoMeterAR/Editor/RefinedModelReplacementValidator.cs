using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using MatsuMotoMeterAR.Instruments;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class RefinedModelReplacementValidator
    {
        private const string ReportDirectory = "Builds/Reports";
        private const string CandidateDirectory =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates";
        private const string V6StagingDirectory =
            CandidateDirectory + "/V6ReplacementStaging";
        private const float BoundsTolerance = 0.001f;
        private const float MountPlaneTolerance = 0.001f;

        private static readonly ThemeEntry[] Themes =
        {
            new("OrbitalAnalog", MockInstrumentTheme.OrbitalAnalog),
            new("ForgeBrass", MockInstrumentTheme.ForgeBrass),
            new("KineticSafety", MockInstrumentTheme.KineticSafety)
        };

        private static readonly ModelEntry[] Models =
        {
            new(
                "MeterRound",
                MockInstrumentKind.RoundMeter,
                "needle_pivot",
                "needle"),
            new(
                "MeterMedium",
                MockInstrumentKind.RoundMeterMedium,
                "needle_pivot",
                "needle"),
            new(
                "MeterLarge",
                MockInstrumentKind.RoundMeterLarge,
                "needle_pivot",
                "needle"),
            new(
                "Lever",
                MockInstrumentKind.Lever,
                "handle_pivot",
                "handle"),
            new(
                "Toggle",
                MockInstrumentKind.ToggleSwitch,
                "switch_pivot",
                "switch"),
            new(
                "Rotary",
                MockInstrumentKind.RotaryKnob,
                "knob_pivot",
                "knob"),
            new(
                "Button",
                MockInstrumentKind.PushButton,
                "button_travel",
                "button"),
            new(
                "Lamp",
                MockInstrumentKind.IndicatorLamp,
                "indicator",
                "indicator"),
            new(
                "Throttle",
                MockInstrumentKind.ThrottleLever,
                "throttle_pivot",
                "throttle_handle"),
            new(
                "PowerSlider",
                MockInstrumentKind.PowerSlider,
                "slider_travel",
                "slider_handle"),
            new(
                "StatusIndicator",
                MockInstrumentKind.StatusIndicator,
                "indicator",
                "indicator",
                requiredActive: false),
            new(
                "WindowMeter",
                MockInstrumentKind.WindowMeter,
                "needle_pivot",
                "needle",
                requiredActive: false),
            new(
                "WindowPanel",
                MockInstrumentKind.WindowPanel,
                "vane_pivot",
                "vane",
                requiredActive: false)
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/Validate Selected FBX")]
        public static void ValidateSelectedFbx()
        {
            var paths = SelectedFbxPaths();
            if (paths.Count == 0)
            {
                throw new InvalidOperationException(
                    "Select one or more replacement FBX assets in the " +
                    "Project window.");
            }

            var report = CreateReport(
                "Selected replacement FBX validation");
            var failures = new List<string>();
            foreach (var path in paths)
            {
                if (!TryResolveModel(path, out var model))
                {
                    failures.Add(
                        $"{path}: filename must contain a supported model key.");
                    AppendFailure(report, path, "unknown model key");
                    continue;
                }

                ValidateFbx(path, model, report, failures);
            }

            Finish(
                "selected-refined-model-validation.md",
                report,
                failures);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Prepare and Validate All Candidates")]
        public static void ValidateCandidateDirectory()
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var paths = CandidateFbxPaths();
            if (paths.Count == 0)
            {
                throw new InvalidOperationException(
                    $"No replacement FBX assets were found under " +
                    $"{CandidateDirectory}.");
            }

            foreach (var path in paths)
                ConfigureCandidateImporter(path);

            var report = CreateReport(
                "Gemini refined replacement candidate validation");
            var failures = new List<string>();
            foreach (var path in paths)
            {
                if (!TryResolveModel(path, out var model))
                {
                    failures.Add(
                        $"{path}: filename must contain a supported model key.");
                    AppendFailure(report, path, "unknown model key");
                    continue;
                }

                ValidateFbx(path, model, report, failures);
            }

            Finish(
                "gemini-refined-candidate-validation.md",
                report,
                failures);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/Validate Active Prefabs")]
        public static void ValidateActivePrefabs()
        {
            var report = CreateReport(
                "Active visual prefab replacement baseline");
            var failures = new List<string>();
            foreach (var theme in Themes)
            {
                foreach (var model in Models)
                {
                    var path =
                        $"Assets/MatsuMotoMeterAR/Resources/" +
                        $"{theme.Folder}/Prefabs/" +
                        $"PF_Visual_{model.Key}_{theme.Folder}.prefab";
                    ValidatePrefab(
                        path,
                        theme,
                        model,
                        report,
                        failures);
                }
            }

            Finish(
                "active-visual-prefab-validation.md",
                report,
                failures);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate V6 Staging Prefabs")]
        public static void ValidateV6StagingPrefabs()
        {
            var report = CreateReport(
                "V6 staged visual prefab validation");
            var failures = new List<string>();
            foreach (var theme in Themes)
            {
                foreach (var model in Models)
                {
                    var path =
                        $"{V6StagingDirectory}/{theme.Folder}/Prefabs/" +
                        $"PF_Visual_{model.Key}_{theme.Folder}.prefab";
                    ValidatePrefab(
                        path,
                        theme,
                        model,
                        report,
                        failures,
                        allowOptionalFallback: false);
                }
            }

            Finish(
                "v6-staged-visual-prefab-validation.md",
                report,
                failures);
        }

        private static void ValidateFbx(
            string path,
            ModelEntry model,
            StringBuilder report,
            List<string> failures)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (asset == null)
            {
                AddFailure(failures, path, "FBX was not imported as a model.");
                AppendFailure(report, path, "missing imported model");
                return;
            }

            if (AssetImporter.GetAtPath(path) is ModelImporter importer)
            {
                if (Mathf.Abs(importer.globalScale - 1f) > 0.0001f)
                    AddFailure(failures, path, "Scale Factor must be 1.");
                if (importer.importAnimation)
                    AddFailure(failures, path, "Import Animation must be off.");
                if (importer.importCameras)
                    AddFailure(failures, path, "Import Cameras must be off.");
                if (importer.importLights)
                    AddFailure(failures, path, "Import Lights must be off.");
                if (importer.addCollider)
                    AddFailure(failures, path, "Generate Colliders must be off.");
            }

            var instance = PrefabUtility.InstantiatePrefab(asset) as GameObject;
            if (instance == null)
            {
                AddFailure(failures, path, "Could not instantiate imported FBX.");
                AppendFailure(report, path, "instantiation failed");
                return;
            }

            try
            {
                instance.transform.SetPositionAndRotation(
                    Vector3.zero,
                    Quaternion.Euler(-90f, 0f, 0f));
                instance.transform.localScale = Vector3.one;
                var result = InspectVisual(instance, model);
                AppendResult(report, path, result);
                foreach (var problem in result.Problems)
                    AddFailure(failures, path, problem);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static void ValidatePrefab(
            string path,
            ThemeEntry theme,
            ModelEntry model,
            StringBuilder report,
            List<string> failures,
            bool allowOptionalFallback = true)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null)
            {
                if (allowOptionalFallback && !model.RequiredActive)
                {
                    AppendOptionalFallback(report, path);
                    return;
                }
                AddFailure(failures, path, "Active visual prefab is missing.");
                AppendFailure(report, path, "missing prefab");
                return;
            }

            var instance = PrefabUtility.InstantiatePrefab(prefab) as GameObject;
            if (instance == null)
            {
                AddFailure(failures, path, "Could not instantiate visual prefab.");
                AppendFailure(report, path, "instantiation failed");
                return;
            }

            try
            {
                instance.transform.SetPositionAndRotation(
                    Vector3.zero,
                    Quaternion.identity);
                var expectedName =
                    $"PF_Visual_{model.Key}_{theme.Folder}";
                var result = InspectVisual(
                    instance,
                    model,
                    allowOptionalFallback
                        ? null
                        : V6ReplacementEnvelope(model.Kind));
                if (instance.name != expectedName)
                    result.Problems.Add($"Root name must be {expectedName}.");
                if (instance.transform.localScale != Vector3.one)
                    result.Problems.Add("Prefab root scale must be (1, 1, 1).");

                var manifests =
                    instance.GetComponents<ThemeVisualManifest>();
                if (manifests.Length != 1)
                {
                    result.Problems.Add(
                        "Prefab root must have exactly one ThemeVisualManifest.");
                }
                else
                {
                    var manifest = manifests[0];
                    var expectedTarget =
                        FindNode(instance.transform, model.MotionTarget);
                    if (manifest.MotionTarget == null)
                        result.Problems.Add("Manifest motion target is missing.");
                    else if (manifest.MotionTarget != expectedTarget)
                    {
                        result.Problems.Add(
                            $"Manifest motion target must reference " +
                            $"{model.MotionTarget}.");
                    }
                    if (model.Kind == MockInstrumentKind.IndicatorLamp &&
                        manifest.IndicatorRenderer == null)
                    {
                        result.Problems.Add(
                            "Lamp manifest indicator renderer is missing.");
                    }
                    if (model.Kind == MockInstrumentKind.StatusIndicator &&
                        !HasThreeStatusRenderers(manifest.StateRenderers))
                    {
                        result.Problems.Add(
                            "Status manifest must reference SAFE, WARN, and " +
                            "DANGER renderers.");
                    }
                }

                AppendResult(report, path, result);
                foreach (var problem in result.Problems)
                    AddFailure(failures, path, problem);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static InspectionResult InspectVisual(
            GameObject instance,
            ModelEntry model,
            Vector3? boundsEnvelope = null)
        {
            var result = new InspectionResult();
            var motionTarget = FindNode(
                instance.transform,
                model.MotionTarget);
            if (motionTarget == null)
            {
                result.Problems.Add(
                    $"Missing motion target {model.MotionTarget}.");
            }
            if (FindNode(instance.transform, model.MovablePart) == null)
            {
                result.Problems.Add(
                    $"Missing movable node {model.MovablePart}.");
            }
            if (model.Kind == MockInstrumentKind.StatusIndicator)
            {
                RequireNode(instance.transform, "status_safe", result);
                RequireNode(instance.transform, "status_warn", result);
                RequireNode(instance.transform, "status_danger", result);
            }

            if (instance.GetComponentsInChildren<Collider>(true).Length > 0)
                result.Problems.Add("Visual contains a Collider.");
            if (instance.GetComponentsInChildren<Light>(true).Length > 0)
                result.Problems.Add("Visual contains a realtime Light.");
            if (instance.GetComponentsInChildren<Camera>(true).Length > 0)
                result.Problems.Add("Visual contains a Camera.");
            if (instance.GetComponentsInChildren<Animator>(true).Length > 0)
                result.Problems.Add("Visual contains an Animator.");

            var renderers =
                instance.GetComponentsInChildren<Renderer>(true);
            result.Renderers = renderers.Length;
            var spec = InstrumentGreyboxSpecification.Get(model.Kind);
            if (result.Renderers == 0)
                result.Problems.Add("Visual has no Renderer.");
            if (result.Renderers > spec.RendererBudget)
            {
                result.Problems.Add(
                    $"Renderer count {result.Renderers} exceeds " +
                    $"budget {spec.RendererBudget}.");
            }

            var materials = new HashSet<Material>();
            foreach (var renderer in renderers)
            {
                foreach (var material in renderer.sharedMaterials)
                {
                    if (material != null)
                        materials.Add(material);
                }
            }
            result.Materials = materials.Count;
            if (result.Materials >
                InstrumentGreyboxSpecification
                    .SharedMaterialBudgetPerInstrument)
            {
                result.Problems.Add(
                    $"Material count {result.Materials} exceeds budget " +
                    $"{InstrumentGreyboxSpecification.SharedMaterialBudgetPerInstrument}.");
            }

            result.Triangles = CountTriangles(instance);
            var triangleBudget = TriangleBudget(model.Kind);
            if (result.Triangles > triangleBudget)
            {
                result.Problems.Add(
                    $"Triangle count {result.Triangles} exceeds budget " +
                    $"{triangleBudget}.");
            }

            if (renderers.Length > 0)
            {
                var bounds = renderers[0].bounds;
                for (var index = 1; index < renderers.Length; index++)
                    bounds.Encapsulate(renderers[index].bounds);
                result.Bounds = bounds.size;
                result.MinimumMountZ = bounds.min.z;
                var envelope = boundsEnvelope ?? spec.BoundsSize;
                if (bounds.size.x > envelope.x + BoundsTolerance ||
                    bounds.size.y > envelope.y + BoundsTolerance ||
                    bounds.size.z > envelope.z + BoundsTolerance)
                {
                    result.Problems.Add(
                        $"Bounds {Format(bounds.size)} exceed envelope " +
                        $"{Format(envelope)}.");
                }
                if (bounds.min.z < -MountPlaneTolerance)
                {
                    result.Problems.Add(
                        $"Visual extends behind mount plane: " +
                        $"{bounds.min.z:F4} m.");
                }
            }

            return result;
        }

        private static Vector3 V6ReplacementEnvelope(
            MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.Lever =>
                    new Vector3(0.18f, 0.256f, 0.102f),
                MockInstrumentKind.ToggleSwitch =>
                    new Vector3(0.125f, 0.17f, 0.088f),
                MockInstrumentKind.RotaryKnob =>
                    new Vector3(0.153f, 0.153f, 0.112f),
                MockInstrumentKind.PushButton =>
                    new Vector3(0.137f, 0.137f, 0.096f),
                MockInstrumentKind.IndicatorLamp =>
                    new Vector3(0.143f, 0.119f, 0.115f),
                MockInstrumentKind.StatusIndicator =>
                    new Vector3(0.185f, 0.125f, 0.100f),
                MockInstrumentKind.ThrottleLever =>
                    new Vector3(0.24f, 0.34f, 0.16f),
                MockInstrumentKind.PowerSlider =>
                    new Vector3(0.17f, 0.34f, 0.195f),
                MockInstrumentKind.RoundMeterMedium =>
                    new Vector3(0.36f, 0.36f, 0.145f),
                MockInstrumentKind.RoundMeterLarge =>
                    new Vector3(0.55f, 0.55f, 0.205f),
                MockInstrumentKind.WindowMeter =>
                    new Vector3(1.20f, 0.75f, 0.202f),
                MockInstrumentKind.WindowPanel =>
                    new Vector3(1.60f, 0.90f, 0.22f),
                _ => new Vector3(0.17f, 0.17f, 0.082f)
            };
        }

        private static int CountTriangles(GameObject root)
        {
            var triangles = 0;
            foreach (var filter in root.GetComponentsInChildren<MeshFilter>(true))
            {
                if (filter.sharedMesh != null)
                    triangles += filter.sharedMesh.triangles.Length / 3;
            }
            foreach (var renderer in
                     root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (renderer.sharedMesh != null)
                    triangles += renderer.sharedMesh.triangles.Length / 3;
            }
            return triangles;
        }

        private static Transform FindNode(Transform root, string nodeName)
        {
            foreach (var candidate in
                     root.GetComponentsInChildren<Transform>(true))
            {
                if (candidate.name == nodeName)
                    return candidate;
            }
            return null;
        }

        private static void RequireNode(
            Transform root,
            string nodeName,
            InspectionResult result)
        {
            if (FindNode(root, nodeName) == null)
                result.Problems.Add($"Missing status node {nodeName}.");
        }

        private static bool HasThreeStatusRenderers(Renderer[] renderers)
        {
            return renderers != null &&
                   renderers.Length >= 3 &&
                   renderers[0] != null &&
                   renderers[1] != null &&
                   renderers[2] != null;
        }

        private static int TriangleBudget(MockInstrumentKind kind)
        {
            return InstrumentGreyboxSpecification.GetTriangleBudget(kind);
        }

        private static List<string> SelectedFbxPaths()
        {
            var paths = new List<string>();
            foreach (var guid in Selection.assetGUIDs)
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (path.EndsWith(
                        ".fbx",
                        StringComparison.OrdinalIgnoreCase))
                {
                    paths.Add(path);
                }
            }
            return paths;
        }

        private static List<string> CandidateFbxPaths()
        {
            var paths = new List<string>();
            foreach (var guid in AssetDatabase.FindAssets(
                         "t:GameObject",
                         new[] { CandidateDirectory }))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                if (path.EndsWith(
                        ".fbx",
                        StringComparison.OrdinalIgnoreCase))
                {
                    paths.Add(path);
                }
            }
            paths.Sort(StringComparer.Ordinal);
            return paths;
        }

        private static void ConfigureCandidateImporter(string path)
        {
            if (AssetImporter.GetAtPath(path) is not ModelImporter importer)
                return;

            var changed = false;
            changed |= SetIfDifferent(
                importer.globalScale,
                1f,
                value => importer.globalScale = value);
            changed |= SetIfDifferent(
                importer.importAnimation,
                false,
                value => importer.importAnimation = value);
            changed |= SetIfDifferent(
                importer.importCameras,
                false,
                value => importer.importCameras = value);
            changed |= SetIfDifferent(
                importer.importLights,
                false,
                value => importer.importLights = value);
            changed |= SetIfDifferent(
                importer.addCollider,
                false,
                value => importer.addCollider = value);
            if (changed)
                importer.SaveAndReimport();
        }

        private static bool SetIfDifferent<T>(
            T current,
            T expected,
            Action<T> setter)
        {
            if (EqualityComparer<T>.Default.Equals(current, expected))
                return false;
            setter(expected);
            return true;
        }

        private static bool TryResolveModel(
            string path,
            out ModelEntry model)
        {
            var filename = Path.GetFileNameWithoutExtension(path);
            foreach (var candidate in Models)
            {
                if (filename.Contains(
                        candidate.Key,
                        StringComparison.OrdinalIgnoreCase))
                {
                    model = candidate;
                    return true;
                }
            }
            model = default;
            return false;
        }

        private static StringBuilder CreateReport(string title)
        {
            var report = new StringBuilder();
            report.Append("# ").AppendLine(title);
            report.AppendLine();
            report.AppendLine(
                "| Asset | Triangles | Renderers | Materials | " +
                "Bounds (m) | Minimum Z | Result |");
            report.AppendLine(
                "| --- | ---: | ---: | ---: | --- | ---: | --- |");
            return report;
        }

        private static void AppendResult(
            StringBuilder report,
            string path,
            InspectionResult result)
        {
            report.Append("| `")
                .Append(path)
                .Append("` | ")
                .Append(result.Triangles)
                .Append(" | ")
                .Append(result.Renderers)
                .Append(" | ")
                .Append(result.Materials)
                .Append(" | ")
                .Append(Format(result.Bounds))
                .Append(" | ")
                .Append(result.MinimumMountZ.ToString("F4"))
                .Append(" | ")
                .Append(result.Problems.Count == 0
                    ? "PASS"
                    : "FAIL: " + string.Join("; ", result.Problems))
                .AppendLine(" |");
        }

        private static void AppendFailure(
            StringBuilder report,
            string path,
            string problem)
        {
            report.Append("| `")
                .Append(path)
                .Append("` | - | - | - | - | - | FAIL: ")
                .Append(problem)
                .AppendLine(" |");
        }

        private static void AppendOptionalFallback(
            StringBuilder report,
            string path)
        {
            report.Append("| `")
                .Append(path)
                .Append("` | - | - | - | - | - | ")
                .AppendLine("NOT INSTALLED (RUNTIME GREYBOX FALLBACK) |");
        }

        private static void AddFailure(
            ICollection<string> failures,
            string path,
            string problem)
        {
            failures.Add($"{path}: {problem}");
        }

        private static void Finish(
            string reportName,
            StringBuilder report,
            IReadOnlyCollection<string> failures)
        {
            Directory.CreateDirectory(ReportDirectory);
            var reportPath = Path.Combine(ReportDirectory, reportName);
            File.WriteAllText(reportPath, report.ToString());
            AssetDatabase.Refresh();
            if (failures.Count > 0)
            {
                throw new InvalidOperationException(
                    $"Model replacement validation failed. Report: " +
                    $"{reportPath}\n" +
                    string.Join("\n", failures));
            }

            Debug.Log(
                $"Model replacement validation passed. Report: {reportPath}");
        }

        private static string Format(Vector3 value)
        {
            return $"{value.x:F4} × {value.y:F4} × {value.z:F4}";
        }

        private readonly struct ThemeEntry
        {
            public ThemeEntry(
                string folder,
                MockInstrumentTheme theme)
            {
                Folder = folder;
                Theme = theme;
            }

            public string Folder { get; }
            public MockInstrumentTheme Theme { get; }
        }

        private readonly struct ModelEntry
        {
            public ModelEntry(
                string key,
                MockInstrumentKind kind,
                string motionTarget,
                string movablePart,
                bool requiredActive = true)
            {
                Key = key;
                Kind = kind;
                MotionTarget = motionTarget;
                MovablePart = movablePart;
                RequiredActive = requiredActive;
            }

            public string Key { get; }
            public MockInstrumentKind Kind { get; }
            public string MotionTarget { get; }
            public string MovablePart { get; }
            public bool RequiredActive { get; }
        }

        private sealed class InspectionResult
        {
            public readonly List<string> Problems = new();
            public int Triangles;
            public int Renderers;
            public int Materials;
            public Vector3 Bounds;
            public float MinimumMountZ;
        }
    }
}
