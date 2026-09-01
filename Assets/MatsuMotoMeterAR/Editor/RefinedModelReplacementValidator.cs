using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
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
        private const string Opus5R2StagingDirectory =
            CandidateDirectory +
            "/CandidateStaging/Opus5_R2/Resources/Opus5_R2";
        private const string Opus5LargeStagingDirectory =
            CandidateDirectory +
            "/CandidateStaging/Opus5_Large/Resources/Opus5_Large";
        private const string Opus5MediumStagingDirectory =
            CandidateDirectory +
            "/CandidateStaging/Opus5_Medium/Resources/Opus5_Medium";
        private const string Opus5R2ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Opus5_R2.json";
        private const string MeterM2n3ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n3.json";
        private const string MeterM2n5ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n5.json";
        private const string MeterM2n7ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n7.json";
        private const string MeterM2n8ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n8.json";
        private const string TrendMonitorP1ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "TrendMonitor_P1.json";
        private const string TrendMonitorP2ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "TrendMonitor_P2.json";
        private const string WindowPanelWp3ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "WindowPanel_WP3_r2.json";
        private const float BoundsTolerance = 0.001f;
        private const float MountPlaneTolerance = 0.001f;

        private static readonly ThemeEntry[] Themes =
        {
            new("OrbitalAnalog", MockInstrumentTheme.OrbitalAnalog),
            new("ForgeBrass", MockInstrumentTheme.ForgeBrass),
            new("KineticSafety", MockInstrumentTheme.KineticSafety),
            new("MachinedErgonomics", MockInstrumentTheme.MachinedErgonomics)
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
                "display_surface",
                "display_surface",
                requiredActive: false),
            new(
                "TrendMonitor",
                MockInstrumentKind.TrendMonitor,
                "display_surface",
                "display_surface",
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

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Selected Candidate Manifest")]
        public static void ValidateSelectedCandidateManifest()
        {
            ValidateCandidateManifest(SelectedManifestPath());
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Trend Monitor P1 Manifest Candidate Staging")]
        public static void ValidateTrendMonitorP1CandidateManifest()
        {
            ValidateCandidateManifest(TrendMonitorP1ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Trend Monitor P2 Manifest Candidate Staging")]
        public static void ValidateTrendMonitorP2CandidateManifest()
        {
            ValidateCandidateManifest(TrendMonitorP2ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Opus 5 R2 Manifest Candidate Staging")]
        public static void ValidateOpus5R2ManifestCandidate()
        {
            ValidateCandidateManifest(Opus5R2ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Meter M2n3 Manifest Candidate Staging")]
        public static void ValidateMeterM2n3ManifestCandidate()
        {
            ValidateCandidateManifest(MeterM2n3ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Meter M2n5 Manifest Candidate Staging")]
        public static void ValidateMeterM2n5ManifestCandidate()
        {
            ValidateCandidateManifest(MeterM2n5ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Meter M2n7 Manifest Candidate Staging")]
        public static void ValidateMeterM2n7ManifestCandidate()
        {
            ValidateCandidateManifest(MeterM2n7ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Meter M2n8 Manifest Candidate Staging")]
        public static void ValidateMeterM2n8ManifestCandidate()
        {
            ValidateCandidateManifest(MeterM2n8ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Window Panel WP3 Manifest Candidate Staging")]
        public static void ValidateWindowPanelWp3ManifestCandidate()
        {
            ValidateCandidateManifest(WindowPanelWp3ManifestPath);
        }

        internal static void ValidateCandidateManifest(string manifestPath)
        {
            var manifest = CandidateStagingManifest.Load(manifestPath);
            var stagingDirectory =
                $"{CandidateDirectory}/CandidateStaging/" +
                $"{manifest.candidateId}/Resources/{manifest.candidateId}";
            var report = CreateReport(
                $"Candidate {manifest.candidateId} visual prefab validation");
            var failures = new List<string>();
            var expectedPrefabs =
                new HashSet<string>(StringComparer.Ordinal);
            foreach (var entry in manifest.entries)
            {
                var theme = FindTheme(entry.theme);
                var model = entry.model == "WindowPanel"
                    ? new ModelEntry(
                        "WindowPanel",
                        MockInstrumentKind.WindowPanel,
                        "display_surface",
                        "display_surface",
                        requiredActive: false)
                    : FindModel(entry.model);
                var path =
                    $"{stagingDirectory}/{theme.Folder}/Prefabs/" +
                    $"PF_Visual_{model.Key}_{theme.Folder}.prefab";
                expectedPrefabs.Add(path);
                ValidatePrefab(
                    path,
                    theme,
                    model,
                    report,
                    failures,
                    allowOptionalFallback: false,
                    sourceReport: LoadSourceReport(entry));
            }

            ValidateManifestSnapshot(
                manifestPath,
                manifest.candidateId,
                report,
                failures);
            ValidateNoUnexpectedPrefabs(
                stagingDirectory,
                expectedPrefabs,
                report,
                failures);

            Finish(
                $"candidate-{manifest.candidateId}-staging-validation.md",
                report,
                failures);
        }

        private static void ValidateManifestSnapshot(
            string sourcePath,
            string candidateId,
            StringBuilder report,
            List<string> failures)
        {
            var snapshotPath =
                $"{CandidateDirectory}/CandidateStaging/{candidateId}/" +
                "candidate-manifest.json";
            if (!File.Exists(snapshotPath))
            {
                AddFailure(failures, snapshotPath, "Manifest snapshot is missing.");
                AppendFailure(report, snapshotPath, "missing manifest snapshot");
                return;
            }
            if (!ManifestSnapshotsMatch(sourcePath, snapshotPath))
            {
                AddFailure(
                    failures,
                    snapshotPath,
                    "Manifest snapshot differs from the selected manifest.");
                AppendFailure(report, snapshotPath, "manifest snapshot mismatch");
            }
        }

        private static void ValidateNoUnexpectedPrefabs(
            string stagingDirectory,
            ISet<string> expectedPrefabs,
            StringBuilder report,
            List<string> failures)
        {
            if (!Directory.Exists(stagingDirectory))
                return;
            foreach (var path in UnexpectedPrefabPaths(
                         stagingDirectory,
                         expectedPrefabs))
            {
                AddFailure(
                    failures,
                    path,
                    "Prefab is not declared by the candidate manifest.");
                AppendFailure(report, path, "undeclared staged prefab");
            }
        }

        internal static bool ManifestSnapshotsMatch(
            string sourcePath,
            string snapshotPath)
        {
            return File.ReadAllBytes(sourcePath).AsSpan().SequenceEqual(
                File.ReadAllBytes(snapshotPath));
        }

        internal static IReadOnlyList<string> UnexpectedPrefabPaths(
            string stagingDirectory,
            ISet<string> expectedPrefabs)
        {
            var unexpected = new List<string>();
            if (!Directory.Exists(stagingDirectory))
                return unexpected;
            foreach (var file in Directory.GetFiles(
                         stagingDirectory,
                         "*.prefab",
                         SearchOption.AllDirectories))
            {
                var path = file.Replace('\\', '/');
                if (!expectedPrefabs.Contains(path))
                    unexpected.Add(path);
            }
            unexpected.Sort(StringComparer.Ordinal);
            return unexpected;
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Opus 5 R2 Candidate Staging")]
        public static void ValidateOpus5R2CandidateStaging()
        {
            const string themeFolder = "KineticSafety";
            var theme = Themes[2];
            var report = CreateReport(
                "Opus 5 R2 candidate visual prefab validation");
            var failures = new List<string>();
            foreach (var key in new[] { "MeterRound", "Lever", "Throttle" })
            {
                var model = FindModel(key);
                var path =
                    $"{Opus5R2StagingDirectory}/{themeFolder}/Prefabs/" +
                    $"PF_Visual_{key}_{themeFolder}.prefab";
                ValidatePrefab(
                    path,
                    theme,
                    model,
                    report,
                    failures,
                    allowOptionalFallback: false);
            }

            Finish(
                "opus5-r2-candidate-staging-validation.md",
                report,
                failures);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Opus 5 Large Candidate Staging")]
        public static void ValidateOpus5LargeCandidateStaging()
        {
            const string themeFolder = "KineticSafety";
            var theme = Themes[2];
            var report = CreateReport(
                "Opus 5 Large atlas candidate validation");
            var failures = new List<string>();
            foreach (var key in
                     new[] { "MeterLarge", "WindowMeter", "WindowPanel" })
            {
                var model = FindModel(key);
                var path =
                    $"{Opus5LargeStagingDirectory}/{themeFolder}/Prefabs/" +
                    $"PF_Visual_{key}_{themeFolder}.prefab";
                ValidatePrefab(
                    path,
                    theme,
                    model,
                    report,
                    failures,
                    allowOptionalFallback: false);
            }

            foreach (var profile in new[]
                     {
                         new TextureProfile("Control1K", 1024),
                         new TextureProfile("Same2K", 2048),
                         new TextureProfile("Finer2K", 2048)
                     })
            {
                ValidateLargeTextures(profile, report, failures);
            }

            Finish(
                "opus5-large-candidate-staging-validation.md",
                report,
                failures);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Validate Opus 5 Medium Candidate Staging")]
        public static void ValidateOpus5MediumCandidateStaging()
        {
            const string themeFolder = "KineticSafety";
            var theme = Themes[2];
            var report = CreateReport(
                "Opus 5 Medium atlas candidate validation");
            var failures = new List<string>();
            var model = FindModel("MeterMedium");
            var path =
                $"{Opus5MediumStagingDirectory}/{themeFolder}/Prefabs/" +
                $"PF_Visual_MeterMedium_{themeFolder}.prefab";
            ValidatePrefab(
                path,
                theme,
                model,
                report,
                failures,
                allowOptionalFallback: false);

            foreach (var profile in new[]
                     {
                         new TextureProfile("Control", 1024),
                         new TextureProfile("Fine", 1024)
                     })
            {
                ValidateMediumTextures(profile, report, failures);
            }

            Finish(
                "opus5-medium-candidate-staging-validation.md",
                report,
                failures);
        }

        private static void ValidateMediumTextures(
            TextureProfile profile,
            StringBuilder report,
            List<string> failures)
        {
            var root =
                $"{Opus5MediumStagingDirectory}/KineticSafety/" +
                $"AtlasProfiles/{profile.Name}";
            ValidateAtlasTextures(
                root,
                "_Medium",
                profile,
                report,
                failures);
        }

        private static void ValidateLargeTextures(
            TextureProfile profile,
            StringBuilder report,
            List<string> failures)
        {
            var root =
                $"{Opus5LargeStagingDirectory}/KineticSafety/" +
                $"AtlasProfiles/{profile.Name}";
            ValidateAtlasTextures(
                root,
                "_Large",
                profile,
                report,
                failures);
        }

        private static void ValidateAtlasTextures(
            string root,
            string atlasSuffix,
            TextureProfile profile,
            StringBuilder report,
            List<string> failures)
        {
            foreach (var suffix in new[]
                     {
                         "BaseColor",
                         "Normal",
                         "MetallicSmoothness",
                         "Emission"
                     })
            {
                var path =
                    $"{root}/T_KineticSafety_V6_Atlas{atlasSuffix}_{suffix}.png";
                var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                if (texture == null)
                {
                    AddFailure(failures, path, "Texture is missing.");
                    continue;
                }
                if (texture.width != profile.Size ||
                    texture.height != profile.Size)
                {
                    AddFailure(
                        failures,
                        path,
                        $"Expected {profile.Size}x{profile.Size}, got " +
                        $"{texture.width}x{texture.height}.");
                }
                if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
                {
                    AddFailure(failures, path, "TextureImporter is missing.");
                    continue;
                }
                if (!importer.mipmapEnabled)
                    AddFailure(failures, path, "Mipmaps must be enabled.");
                var normal = suffix == "Normal";
                if (normal &&
                    importer.textureType != TextureImporterType.NormalMap)
                {
                    AddFailure(failures, path, "Normal map type is required.");
                }
                var expectedSrgb =
                    suffix != "Normal" &&
                    suffix != "MetallicSmoothness";
                if (importer.sRGBTexture != expectedSrgb)
                {
                    AddFailure(
                        failures,
                        path,
                        $"sRGB must be {expectedSrgb}.");
                }
                report.AppendLine(
                    $"- texture `{profile.Name}/{suffix}`: " +
                    $"{texture.width}x{texture.height}, " +
                    $"format={texture.format}, mips={texture.mipmapCount}, " +
                    $"sRGB={importer.sRGBTexture}");
            }
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
            bool allowOptionalFallback = true,
            SourceReportExpectation sourceReport = null)
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
                    theme.Theme == MockInstrumentTheme.MachinedErgonomics
                        ? MachinedErgonomicsEnvelope(model.Kind)
                        : allowOptionalFallback
                            ? null
                            : V6ReplacementEnvelope(model.Kind),
                    triangleBudgetOverride:
                        model.Kind == MockInstrumentKind.WindowPanel &&
                        model.MotionTarget == "display_surface"
                            ? 8000
                            : theme.Theme ==
                              MockInstrumentTheme.MachinedErgonomics &&
                              model.Kind == MockInstrumentKind.Lever
                                ? 7000
                                : null,
                    materialBudgetOverride:
                        model.Kind == MockInstrumentKind.TrendMonitor ||
                        model.Kind == MockInstrumentKind.WindowPanel &&
                        model.MotionTarget == "display_surface"
                            ? 3
                            : null,
                    useDisplayPlaneContract:
                        theme.Theme == MockInstrumentTheme.MachinedErgonomics);
                if (instance.name != expectedName)
                    result.Problems.Add($"Root name must be {expectedName}.");
                if (instance.transform.localScale != Vector3.one)
                    result.Problems.Add("Prefab root scale must be (1, 1, 1).");

                if (model.Kind == MockInstrumentKind.WindowPanel &&
                    model.MotionTarget == "display_surface")
                {
                    result.Problems.AddRange(
                        WindowPanelCandidateContractValidator.Evaluate(instance));
                }

                if (sourceReport != null)
                {
                    CompareSourceReport(
                        sourceReport,
                        result);
                }

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

        private static SourceReportExpectation LoadSourceReport(
            CandidateStagingEntry entry)
        {
            if (string.IsNullOrWhiteSpace(entry.sourceReport))
                return null;

            var json = File.ReadAllText(entry.sourceReport);
            var document = JsonUtility.FromJson<CandidateSourceReport>(json);
            if (document == null)
            {
                throw new InvalidDataException(
                    $"Could not parse source report: {entry.sourceReport}");
            }

            var expectedIdentity = $"{entry.theme}/{entry.model}";
            var reportedIdentity = !string.IsNullOrWhiteSpace(document.model)
                ? document.model.Contains("/", StringComparison.Ordinal)
                    ? document.model
                    : $"{entry.theme}/{document.model}"
                : !string.IsNullOrWhiteSpace(document.theme) &&
                  !string.IsNullOrWhiteSpace(document.@object)
                    ? $"{document.theme}/{document.@object}"
                    : InferInventoryReportIdentity(
                        document.theme,
                        document.fbx,
                        json);
            var triangles = document.triangles > 0
                ? document.triangles
                : document.candidate?.triangles > 0
                    ? document.candidate.triangles
                    : document.gates?.triangles?.measured ?? 0;
            if (triangles <= 0 && json.Contains("\"inventory\""))
                triangles = SumIntegerFields(json, "loop_triangles");
            var renderers = document.renderers;
            if (renderers <= 0 && json.Contains("\"inventory\""))
                renderers = CountStringFieldValues(json, "type", "MESH");

            var reportedSha = !string.IsNullOrWhiteSpace(document.fbx_sha256)
                ? document.fbx_sha256
                : document.staged_sha256;
            if (!string.IsNullOrWhiteSpace(reportedSha))
            {
                var actualSha = Sha256(entry.sourceFbx);
                if (!string.Equals(
                        reportedSha,
                        actualSha,
                        StringComparison.OrdinalIgnoreCase))
                {
                    throw new InvalidDataException(
                        $"Source report FBX SHA-256 is {reportedSha}; " +
                        $"actual is {actualSha}: {entry.sourceFbx}");
                }
            }
            if (entry.revision == "WP3-r2" &&
                (document.blender_version != "5.2.0 LTS" ||
                 document.blender_binary !=
                 "/Applications/Blender 5.2.app/Contents/MacOS/Blender"))
            {
                throw new InvalidDataException(
                    $"WP3-r2 source report has unexpected Blender " +
                    $"provenance: {document.blender_version}, " +
                    $"{document.blender_binary}.");
            }
            var expectation = new SourceReportExpectation
            {
                Path = entry.sourceReport,
                Identity = reportedIdentity,
                ExpectedIdentity = expectedIdentity,
                ReportedFbx = document.fbx,
                ExpectedFbx = entry.sourceFbx,
                Triangles = triangles,
                Renderers = renderers,
                Submeshes = document.submeshes > 0
                    ? document.submeshes
                    : document.gates?.submesh_budget?.measured ?? 0,
                SubmeshBudget =
                    document.gates?.submesh_budget?.budget ?? 0,
                Materials = document.material_slots?.Length ?? 0
            };

            var bounds = document.candidate?.bounds;
            if (bounds == null &&
                document.bounds_min?.Length == 3 &&
                document.bounds_max?.Length == 3)
            {
                bounds = new CandidateSourceBounds
                {
                    min = document.bounds_min,
                    max = document.bounds_max
                };
                document.bounds_space = "unity_xyz";
            }
            if (bounds?.min?.Length == 3 && bounds.max?.Length == 3)
            {
                var blenderSize = new Vector3(
                    bounds.max[0] - bounds.min[0],
                    bounds.max[1] - bounds.min[1],
                    bounds.max[2] - bounds.min[2]);
                expectation.Bounds = document.bounds_space == "unity_xyz"
                    ? blenderSize
                    : new Vector3(
                        blenderSize.x,
                        blenderSize.z,
                        blenderSize.y);
            }
            return expectation;
        }

        private static string InferInventoryReportIdentity(
            string theme,
            string reportedFbx,
            string json)
        {
            if (string.IsNullOrWhiteSpace(theme) ||
                string.IsNullOrWhiteSpace(reportedFbx) ||
                !json.Contains("\"inventory\""))
            {
                return string.Empty;
            }

            var fileName = Path.GetFileNameWithoutExtension(reportedFbx);
            var prefix = "SM_";
            var suffix = $"_{theme}_V6_";
            if (!fileName.StartsWith(prefix, StringComparison.Ordinal) ||
                !fileName.Contains(suffix, StringComparison.Ordinal))
            {
                return string.Empty;
            }
            var start = prefix.Length;
            var end = fileName.IndexOf(suffix, StringComparison.Ordinal);
            return end <= start
                ? string.Empty
                : $"{theme}/{fileName.Substring(start, end - start)}";
        }

        private static int SumIntegerFields(string json, string field)
        {
            var matches = Regex.Matches(
                json,
                $"\\\"{Regex.Escape(field)}\\\"\\s*:\\s*(\\d+)",
                RegexOptions.CultureInvariant);
            var total = 0;
            foreach (Match match in matches)
                total += int.Parse(match.Groups[1].Value);
            return total;
        }

        private static int CountStringFieldValues(
            string json,
            string field,
            string value)
        {
            return Regex.Matches(
                json,
                $"\\\"{Regex.Escape(field)}\\\"\\s*:\\s*" +
                $"\\\"{Regex.Escape(value)}\\\"",
                RegexOptions.CultureInvariant).Count;
        }

        private static string Sha256(string path)
        {
            using var stream = File.OpenRead(path);
            using var algorithm = SHA256.Create();
            var hash = algorithm.ComputeHash(stream);
            return BitConverter.ToString(hash).Replace("-", string.Empty)
                .ToLowerInvariant();
        }

        private static void CompareSourceReport(
            SourceReportExpectation source,
            InspectionResult result)
        {
            if (source.Identity != source.ExpectedIdentity)
            {
                result.Problems.Add(
                    $"Source report identity is {source.Identity}; expected " +
                    $"{source.ExpectedIdentity} ({source.Path}).");
            }
            if (!string.IsNullOrWhiteSpace(source.ReportedFbx) &&
                !ReportedFbxMatches(source.ReportedFbx, source.ExpectedFbx))
            {
                result.Problems.Add(
                    $"Source report FBX is {source.ReportedFbx}; expected " +
                    $"{source.ExpectedFbx}.");
            }
            if (source.Triangles <= 0)
            {
                result.Problems.Add(
                    $"Source report has no candidate triangle count " +
                    $"({source.Path}).");
            }
            else if (result.Triangles != source.Triangles)
            {
                result.Problems.Add(
                    $"Unity triangles {result.Triangles} differ from source " +
                    $"report {source.Triangles}.");
            }
            if (source.Renderers > 0 && result.Renderers != source.Renderers)
            {
                result.Problems.Add(
                    $"Unity renderers {result.Renderers} differ from source " +
                    $"report {source.Renderers}.");
            }
            if (source.Submeshes > 0 && result.Submeshes != source.Submeshes)
            {
                result.Problems.Add(
                    $"Unity submeshes {result.Submeshes} differ from source " +
                    $"report {source.Submeshes}.");
            }
            if (source.SubmeshBudget > 0 &&
                result.Submeshes > source.SubmeshBudget)
            {
                result.Problems.Add(
                    $"Unity submeshes {result.Submeshes} exceed source " +
                    $"budget {source.SubmeshBudget}.");
            }
            if (source.Materials > 0 && result.Materials != source.Materials)
            {
                result.Problems.Add(
                    $"Unity materials {result.Materials} differ from source " +
                    $"report {source.Materials}.");
            }
            if (source.Bounds.HasValue &&
                !Approximately(result.Bounds, source.Bounds.Value))
            {
                result.Problems.Add(
                    $"Unity bounds {Format(result.Bounds)} differ from source " +
                    $"report {Format(source.Bounds.Value)}.");
            }
        }

        private static bool ReportedFbxMatches(
            string reported,
            string expected)
        {
            var normalizedReported = reported.Replace('\\', '/');
            var normalizedExpected = expected.Replace('\\', '/');
            return normalizedReported == normalizedExpected ||
                   (!normalizedReported.Contains('/') &&
                    normalizedReported == Path.GetFileName(normalizedExpected));
        }

        private static bool Approximately(Vector3 left, Vector3 right)
        {
            return Mathf.Abs(left.x - right.x) <= BoundsTolerance &&
                   Mathf.Abs(left.y - right.y) <= BoundsTolerance &&
                   Mathf.Abs(left.z - right.z) <= BoundsTolerance;
        }

        private static InspectionResult InspectVisual(
            GameObject instance,
            ModelEntry model,
            Vector3? boundsEnvelope = null,
            int? triangleBudgetOverride = null,
            int? materialBudgetOverride = null,
            bool useDisplayPlaneContract = false)
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
            if (model.Kind == MockInstrumentKind.TrendMonitor &&
                motionTarget != null)
            {
                if (useDisplayPlaneContract)
                    ValidateTrendMonitorDisplayPlane(motionTarget, result);
                else
                {
                    ValidateTrendMonitorDisplay(motionTarget, result);
                    RequireNode(instance.transform, "static_opaque", result);
                    RequireNode(instance.transform, "static_readout", result);
                }
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
            result.Submeshes = CountSubmeshes(renderers);
            var spec = InstrumentGreyboxSpecification.Get(model.Kind);
            var rendererBudget = boundsEnvelope.HasValue
                ? V6RendererBudget(model.Kind)
                : spec.RendererBudget;
            if (result.Renderers == 0)
                result.Problems.Add("Visual has no Renderer.");
            if (result.Renderers > rendererBudget)
            {
                result.Problems.Add(
                    $"Renderer count {result.Renderers} exceeds " +
                    $"budget {rendererBudget}.");
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
            var materialBudget = materialBudgetOverride ??
                InstrumentGreyboxSpecification
                    .SharedMaterialBudgetPerInstrument;
            if (result.Materials > materialBudget)
            {
                result.Problems.Add(
                    $"Material count {result.Materials} exceeds budget " +
                    $"{materialBudget}.");
            }

            result.Triangles = CountTriangles(instance);
            var triangleBudget = triangleBudgetOverride ??
                TriangleBudget(model.Kind);
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

        private static int V6RendererBudget(MockInstrumentKind kind)
        {
            return kind switch
            {
                // The accepted Toggle V6 Blender/FBX contract deliberately
                // preserves thirteen named mesh parts. The source report
                // comparison above still requires the imported count to match.
                MockInstrumentKind.ToggleSwitch => 13,
                _ => InstrumentGreyboxSpecification.Get(kind).RendererBudget
            };
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
                MockInstrumentKind.TrendMonitor =>
                    new Vector3(0.44f, 0.28f, 0.10f),
                _ => new Vector3(0.17f, 0.17f, 0.082f)
            };
        }

        private static Vector3 MachinedErgonomicsEnvelope(
            MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.Lever
                ? new Vector3(0.24f, 0.44f, 0.15f)
                : V6ReplacementEnvelope(kind);
        }

        private static void ValidateTrendMonitorDisplay(
            Transform displaySurface,
            InspectionResult result)
        {
            var filter = displaySurface.GetComponent<MeshFilter>();
            var renderer = displaySurface.GetComponent<Renderer>();
            var mesh = filter?.sharedMesh;
            if (renderer == null || mesh == null)
            {
                result.Problems.Add(
                    "TrendMonitor display_surface must have a MeshRenderer " +
                    "and MeshFilter.");
                return;
            }
            if (renderer.bounds.size.x < 0.36f - BoundsTolerance ||
                renderer.bounds.size.y < 0.18f - BoundsTolerance)
            {
                result.Problems.Add(
                    $"TrendMonitor display surface " +
                    $"{Format(renderer.bounds.size)} is smaller than " +
                    "0.36 x 0.18 m.");
            }
            foreach (var normal in mesh.normals)
            {
                var worldNormal = displaySurface.TransformDirection(normal)
                    .normalized;
                if (Vector3.Dot(worldNormal, Vector3.forward) < 0.999f)
                {
                    result.Problems.Add(
                        "TrendMonitor display normals must face local +Z.");
                    break;
                }
            }
            if (Vector3.Dot(displaySurface.up, Vector3.up) < 0.999f)
            {
                result.Problems.Add(
                    "TrendMonitor display up axis must face local +Y.");
            }
        }

        private static void ValidateTrendMonitorDisplayPlane(
            Transform displaySurface,
            InspectionResult result)
        {
            var filter = displaySurface.GetComponent<MeshFilter>();
            var renderer = displaySurface.GetComponent<Renderer>();
            var mesh = filter?.sharedMesh;
            if (renderer == null || mesh == null)
            {
                result.Problems.Add(
                    "TrendMonitor display_surface must have a MeshRenderer " +
                    "and MeshFilter.");
                return;
            }
            if (renderer.bounds.size.x < 0.36f - BoundsTolerance ||
                renderer.bounds.size.y < 0.18f - BoundsTolerance)
            {
                result.Problems.Add(
                    $"TrendMonitor display surface " +
                    $"{Format(renderer.bounds.size)} is smaller than " +
                    "0.36 x 0.18 m.");
            }

            var vertices = mesh.vertices
                .Select(displaySurface.TransformPoint)
                .ToArray();
            var maximumZ = vertices.Max(vertex => vertex.z);
            var triangles = mesh.triangles;
            var frontTriangles = 0;
            const float planeTolerance = 0.00001f;
            for (var index = 0; index < triangles.Length; index += 3)
            {
                var a = vertices[triangles[index]];
                var b = vertices[triangles[index + 1]];
                var c = vertices[triangles[index + 2]];
                if (Mathf.Abs(a.z - maximumZ) > planeTolerance ||
                    Mathf.Abs(b.z - maximumZ) > planeTolerance ||
                    Mathf.Abs(c.z - maximumZ) > planeTolerance)
                    continue;
                var normal = Vector3.Cross(b - a, c - a).normalized;
                if (Vector3.Dot(normal, Vector3.forward) < 0.999f)
                {
                    result.Problems.Add(
                        "TrendMonitor front face must point local +Z.");
                    return;
                }
                frontTriangles++;
            }
            if (frontTriangles != 2)
            {
                result.Problems.Add(
                    $"TrendMonitor front face must contain 2 triangles; " +
                    $"actual={frontTriangles}.");
            }

            var size = mesh.bounds.size;
            var axes = new[]
            {
                (extent: size.x, axis: Vector3.right),
                (extent: size.y, axis: Vector3.up),
                (extent: size.z, axis: Vector3.forward)
            };
            var heightAxis = axes.OrderByDescending(item => item.extent)
                .Skip(1).First().axis;
            if (Vector3.Dot(
                    displaySurface.TransformDirection(heightAxis).normalized,
                    Vector3.up) < 0.999f)
            {
                result.Problems.Add(
                    "TrendMonitor display up axis must face local +Y.");
            }
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

        private static int CountSubmeshes(Renderer[] renderers)
        {
            var submeshes = 0;
            foreach (var renderer in renderers)
            {
                Mesh mesh = renderer switch
                {
                    MeshRenderer meshRenderer =>
                        meshRenderer.GetComponent<MeshFilter>()?.sharedMesh,
                    SkinnedMeshRenderer skinned => skinned.sharedMesh,
                    _ => null
                };
                if (mesh != null)
                    submeshes += mesh.subMeshCount;
            }
            return submeshes;
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

        private static ModelEntry FindModel(string key)
        {
            foreach (var model in Models)
            {
                if (model.Key == key)
                    return model;
            }
            throw new ArgumentOutOfRangeException(
                nameof(key),
                key,
                "Unsupported model key.");
        }

        private static ThemeEntry FindTheme(string folder)
        {
            foreach (var theme in Themes)
            {
                if (theme.Folder == folder)
                    return theme;
            }
            throw new ArgumentOutOfRangeException(
                nameof(folder),
                folder,
                "Unsupported theme folder.");
        }

        private static string SelectedManifestPath()
        {
            return CandidateStagingManifest.SelectedAssetPath();
        }

        private static StringBuilder CreateReport(string title)
        {
            var report = new StringBuilder();
            report.Append("# ").AppendLine(title);
            report.AppendLine();
            report.AppendLine(
                "| Asset | Triangles | Renderers | Submeshes | Materials | " +
                "Bounds (m) | Minimum Z | Result |");
            report.AppendLine(
                "| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |");
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
                .Append(result.Submeshes)
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
                .Append("` | - | - | - | - | - | - | FAIL: ")
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

        private readonly struct TextureProfile
        {
            public TextureProfile(string name, int size)
            {
                Name = name;
                Size = size;
            }

            public string Name { get; }
            public int Size { get; }
        }

        private sealed class InspectionResult
        {
            public readonly List<string> Problems = new();
            public int Triangles;
            public int Renderers;
            public int Submeshes;
            public int Materials;
            public Vector3 Bounds;
            public float MinimumMountZ;
        }

        [Serializable]
        private sealed class CandidateSourceReport
        {
            public string theme;
            public string @object;
            public string model;
            public string fbx;
            public string fbx_sha256;
            public string staged_sha256;
            public int triangles;
            public int renderers;
            public int submeshes;
            public string[] material_slots;
            public string bounds_space;
            public float[] bounds_min;
            public float[] bounds_max;
            public string blender_binary;
            public string blender_version;
            public CandidateSourceSnapshot candidate;
            public CandidateSourceGates gates;
        }

        [Serializable]
        private sealed class CandidateSourceGates
        {
            public CandidateSourceTriangleGate triangles;
            public CandidateSourceSubmeshGate submesh_budget;
        }

        [Serializable]
        private sealed class CandidateSourceTriangleGate
        {
            public int measured;
        }

        [Serializable]
        private sealed class CandidateSourceSubmeshGate
        {
            public int measured;
            public int budget;
        }

        [Serializable]
        private sealed class CandidateSourceSnapshot
        {
            public int triangles;
            public CandidateSourceBounds bounds;
        }

        [Serializable]
        private sealed class CandidateSourceBounds
        {
            public float[] min;
            public float[] max;
        }

        private sealed class SourceReportExpectation
        {
            public string Path;
            public string Identity;
            public string ExpectedIdentity;
            public string ReportedFbx;
            public string ExpectedFbx;
            public int Triangles;
            public int Renderers;
            public int Submeshes;
            public int SubmeshBudget;
            public int Materials;
            public Vector3? Bounds;
        }
    }
}
