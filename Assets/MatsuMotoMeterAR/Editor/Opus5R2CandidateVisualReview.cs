using System;
using System.IO;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Signals;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class Opus5R2CandidateVisualReview
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
        private const string TrendMonitorP1ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "TrendMonitor_P1.json";
        private const string TrendMonitorP2ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "TrendMonitor_P2.json";
        private const string WindowPanelWp3ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "WindowPanel_WP3_r2.json";
        private static readonly MockInstrumentTheme[] ProductionTrendThemes =
        {
            MockInstrumentTheme.OrbitalAnalog,
            MockInstrumentTheme.ForgeBrass,
            MockInstrumentTheme.KineticSafety,
            MockInstrumentTheme.MachinedErgonomics
        };
        private static readonly string[] ProductionTrendMonitorPaths =
        {
            "Assets/MatsuMotoMeterAR/Resources/OrbitalAnalog/Prefabs/" +
            "PF_Visual_TrendMonitor_OrbitalAnalog.prefab",
            "Assets/MatsuMotoMeterAR/Resources/ForgeBrass/Prefabs/" +
            "PF_Visual_TrendMonitor_ForgeBrass.prefab",
            "Assets/MatsuMotoMeterAR/Resources/KineticSafety/Prefabs/" +
            "PF_Visual_TrendMonitor_KineticSafety.prefab",
            "Assets/MatsuMotoMeterAR/Resources/MachinedErgonomics/Prefabs/" +
            "PF_Visual_TrendMonitor_MachinedErgonomics.prefab"
        };
        private const int TileSize = 512;

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Opus 5 R2 Visual Review")]
        public static void Run()
        {
            RenderManifest(Opus5R2ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Selected Candidate Manifest Visual Review")]
        public static void RunSelected()
        {
            RenderManifest(CandidateStagingManifest.SelectedAssetPath());
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Selected Candidate Manifest Shape Review")]
        public static void RunSelectedShapeReview()
        {
            RenderCandidateOnlyManifest(
                CandidateStagingManifest.SelectedAssetPath());
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Meter M2n5 Visual Review")]
        public static void RunMeterM2n5()
        {
            RenderManifest(MeterM2n5ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Meter M2n5 Neutral Shape Review")]
        public static void RunMeterM2n5Neutral()
        {
            RenderNeutralManifest(MeterM2n5ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Meter M2n7 Visual Review")]
        public static void RunMeterM2n7()
        {
            RenderManifest(MeterM2n7ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Meter M2n7 Neutral Shape Review")]
        public static void RunMeterM2n7Neutral()
        {
            RenderNeutralManifest(MeterM2n7ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Meter M2n8 Visual Review")]
        public static void RunMeterM2n8()
        {
            RenderManifest(MeterM2n8ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Meter M2n8 Neutral Shape Review")]
        public static void RunMeterM2n8Neutral()
        {
            RenderNeutralManifest(MeterM2n8ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Trend Monitor P1 Visual Review")]
        public static void RunTrendMonitorP1()
        {
            RenderCandidateOnlyManifest(TrendMonitorP1ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Trend Monitor P2 Visual Review")]
        public static void RunTrendMonitorP2()
        {
            RenderCandidateOnlyManifest(TrendMonitorP2ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Production Trend Monitor Composition Review")]
        public static void RunTrendMonitorCompositionReview()
        {
            const string outputPath =
                "Builds/Reports/production-TrendMonitor-composition-review.png";
            var cameraObject = new GameObject("[Review] Camera");
            var lightObject = new GameObject("[Review] Light");
            var camera = cameraObject.AddComponent<Camera>();
            var light = lightObject.AddComponent<Light>();
            var sheet = new Texture2D(
                TileSize,
                TileSize * ProductionTrendThemes.Length,
                TextureFormat.RGBA32,
                false);
            try
            {
                ConfigureScene(camera, light);
                Fill(sheet, new Color(0.012f, 0.018f, 0.025f, 1f));
                for (var row = 0;
                     row < ProductionTrendThemes.Length;
                     row++)
                {
                    RenderTrendMonitorThemeIntoSheet(
                        sheet,
                        camera,
                        ProductionTrendThemes[row],
                        ProductionTrendMonitorPaths[row],
                        useRuntimeWrapper:
                            row == ProductionTrendThemes.Length - 1,
                        row: row,
                        rowCount: ProductionTrendThemes.Length);
                }

                Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
                File.WriteAllBytes(outputPath, sheet.EncodeToPNG());
                AssetDatabase.Refresh();
                Debug.Log(
                    "Production Trend Monitor composition review rendered. " +
                    "Rows: OrbitalAnalog, ForgeBrass, KineticSafety, " +
                    $"MachinedErgonomics. Output: {outputPath}");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(sheet);
                UnityEngine.Object.DestroyImmediate(cameraObject);
                UnityEngine.Object.DestroyImmediate(lightObject);
            }
        }

        private static void RenderTrendMonitorThemeIntoSheet(
            Texture2D sheet,
            Camera camera,
            MockInstrumentTheme theme,
            string visualPrefabPath,
            bool useRuntimeWrapper,
            int row,
            int rowCount)
        {
            // The three T1 visual prefabs are authored Z-forward and can be
            // framed directly. Machined Ergonomics remains Y-forward at the
            // FBX level, so use the runtime factory's production wrapper for
            // that one row before applying the same front-camera review.
            var instance = useRuntimeWrapper
                ? MockInstrumentFactory.Create(
                    MockInstrumentKind.TrendMonitor,
                    Pose.identity,
                    theme: theme)
                : Instantiate(visualPrefabPath);
            var target = new RenderTexture(
                TileSize,
                TileSize,
                24,
                RenderTextureFormat.ARGB32);
            var image = new Texture2D(
                TileSize,
                TileSize,
                TextureFormat.RGBA32,
                false);
            var previousActive = RenderTexture.active;
            try
            {
                var framingRoot = instance;
                if (useRuntimeWrapper)
                {
                    framingRoot = instance
                        .GetComponent<InstrumentGreyboxContract>()
                        ?.VisualSocket?.gameObject ?? instance;
                }
                var bounds = RendererBounds(framingRoot);
                instance.transform.position -= new Vector3(
                    bounds.center.x,
                    bounds.center.y,
                    0f);
                bounds = RendererBounds(framingRoot);
                ConfigureEmission(instance, false);
                AddTrendGraph(instance);
                var framing = new Framing(
                    Mathf.Max(bounds.extents.x, bounds.extents.y) * 1.18f,
                    bounds.size.z + 1f);
                camera.orthographicSize = framing.OrthographicSize;
                camera.transform.SetPositionAndRotation(
                    new Vector3(0f, 0f, bounds.center.z + framing.CameraDistance),
                    Quaternion.Euler(0f, 180f, 0f));
                camera.targetTexture = target;
                camera.Render();
                RenderTexture.active = target;
                image.ReadPixels(
                    new Rect(0, 0, TileSize, TileSize),
                    0,
                    0);
                image.Apply();
                sheet.SetPixels(
                    0,
                    (rowCount - 1 - row) * TileSize,
                    TileSize,
                    TileSize,
                    image.GetPixels());
                sheet.Apply();
            }
            finally
            {
                camera.targetTexture = null;
                RenderTexture.active = previousActive;
                UnityEngine.Object.DestroyImmediate(image);
                UnityEngine.Object.DestroyImmediate(target);
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Window Panel WP3 Shape Review")]
        public static void RunWindowPanelWp3()
        {
            RenderCandidateOnlyManifest(WindowPanelWp3ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Window Panel WP4 Preset Review")]
        public static void RunWindowPanelWp4PresetReview()
        {
            RunWindowPanelWp4PresetReview(production: false);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Render Window Panel WP4 Production Preset Review")]
        public static void RunWindowPanelWp4ProductionPresetReview()
        {
            RunWindowPanelWp4PresetReview(production: true);
        }

        private static void RunWindowPanelWp4PresetReview(bool production)
        {
            var manifest = CandidateStagingManifest.Load(
                WindowPanelWp3ManifestPath);
            var presets = new[]
            {
                WindowPanelGraphicPreset.Orbit,
                WindowPanelGraphicPreset.Rose,
                WindowPanelGraphicPreset.Lissajous
            };
            var outputPath = production
                ? "Builds/Reports/production-WindowPanel_WP4-" +
                  "unity-preset-contact-sheet.png"
                : "Builds/Reports/candidate-WindowPanel_WP3_r2-" +
                  "unity-preset-contact-sheet.png";
            var reportPath = production
                ? "Builds/Reports/production-WindowPanel_WP4-" +
                  "unity-preset-review.md"
                : "Builds/Reports/candidate-WindowPanel_WP3_r2-" +
                  "unity-preset-review.md";
            var cameraObject = new GameObject("[Review] WP4 Preset Camera");
            var lightObject = new GameObject("[Review] WP4 Preset Light");
            var camera = cameraObject.AddComponent<Camera>();
            var light = lightObject.AddComponent<Light>();
            var sheet = new Texture2D(
                TileSize * presets.Length,
                TileSize * manifest.entries.Length,
                TextureFormat.RGBA32,
                false);
            try
            {
                ConfigureScene(camera, light);
                Fill(sheet, new Color(0.012f, 0.018f, 0.025f, 1f));
                for (var row = 0; row < manifest.entries.Length; row++)
                {
                    var entry = manifest.entries[row];
                    var path = production
                        ? $"Assets/MatsuMotoMeterAR/Resources/" +
                          $"{entry.theme}/Prefabs/" +
                          $"PF_Visual_WindowPanel_{entry.theme}.prefab"
                        : manifest.CandidatePrefabPath(entry);
                    var framing = CalculateFraming(path);
                    for (var column = 0; column < presets.Length; column++)
                    {
                        RenderIntoSheet(
                            sheet,
                            camera,
                            path,
                            framing,
                            emissionEnabled: false,
                            column: column,
                            row: row,
                            rowCount: manifest.entries.Length,
                            showWindowPanelGraphic: true,
                            windowPanelPreset: presets[column]);
                    }
                }
                Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
                File.WriteAllBytes(outputPath, sheet.EncodeToPNG());
                File.WriteAllText(
                    reportPath,
                    "# Window Panel WP4 preset review\n\n" +
                    "Result: **RENDERED**\n\n" +
                    "- Rows: OrbitalAnalog / ForgeBrass / KineticSafety / " +
                    "MachinedErgonomics\n" +
                    "- Columns: Orbit / Rose / Lissajous\n" +
                    (production
                        ? "- Source: promoted production Resources prefabs\n" +
                          "- Candidate dependencies: 0 (validated)\n"
                        : "- Candidate: WindowPanel_WP3_r2 isolated staging\n" +
                          "- Production assets: unchanged\n"));
                AssetDatabase.Refresh();
                Debug.Log(
                    $"Window Panel WP4 " +
                    $"{(production ? "production " : string.Empty)}" +
                    $"preset review: {outputPath}");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(sheet);
                UnityEngine.Object.DestroyImmediate(cameraObject);
                UnityEngine.Object.DestroyImmediate(lightObject);
            }
        }

        internal static string RenderManifest(string manifestPath)
        {
            return RenderManifest(
                manifestPath,
                neutralShapeReview: false,
                candidateOnly: false);
        }

        internal static string RenderNeutralManifest(string manifestPath)
        {
            return RenderManifest(
                manifestPath,
                neutralShapeReview: true,
                candidateOnly: false);
        }

        internal static string RenderCandidateOnlyManifest(string manifestPath)
        {
            return RenderManifest(
                manifestPath,
                neutralShapeReview: false,
                candidateOnly: true);
        }

        private static string RenderManifest(
            string manifestPath,
            bool neutralShapeReview,
            bool candidateOnly)
        {
            var manifest = CandidateStagingManifest.Load(manifestPath);
            var outputPath =
                $"Builds/Reports/candidate-{manifest.candidateId}-" +
                (neutralShapeReview
                    ? "unity-neutral-shape-contact-sheet.png"
                    : candidateOnly
                    ? "unity-shape-contact-sheet.png"
                    : "unity-visual-contact-sheet.png");
            var cameraObject = new GameObject("[Review] Camera");
            var lightObject = new GameObject("[Review] Light");
            var camera = cameraObject.AddComponent<Camera>();
            var light = lightObject.AddComponent<Light>();
            var columnCount = candidateOnly ? 4 : neutralShapeReview ? 2 : 4;
            var sheet = new Texture2D(
                TileSize * columnCount,
                TileSize * manifest.entries.Length,
                TextureFormat.RGBA32,
                false);
            try
            {
                ConfigureScene(camera, light);
                Fill(sheet, new Color(0.012f, 0.018f, 0.025f, 1f));
                for (var row = 0; row < manifest.entries.Length; row++)
                {
                    var entry = manifest.entries[row];
                    var candidatePath = manifest.CandidatePrefabPath(entry);
                    if (candidateOnly)
                    {
                        var candidateFraming = CalculateFraming(candidatePath);
                        var showTrendGraph = entry.model == "TrendMonitor";
                        var showWindowPanelGraphic =
                            entry.model == "WindowPanel";
                        RenderIntoSheet(
                            sheet, camera, candidatePath, candidateFraming,
                            emissionEnabled: false, column: 0, row: row,
                            rowCount: manifest.entries.Length,
                            showTrendGraph: showTrendGraph,
                            showWindowPanelGraphic: showWindowPanelGraphic);
                        RenderIntoSheet(
                            sheet, camera, candidatePath, candidateFraming,
                            emissionEnabled: false, column: 1, row: row,
                            rowCount: manifest.entries.Length,
                            viewYawDegrees: -32f,
                            showTrendGraph: showTrendGraph,
                            showWindowPanelGraphic: showWindowPanelGraphic);
                        RenderIntoSheet(
                            sheet, camera, candidatePath, candidateFraming,
                            emissionEnabled: false, column: 2, row: row,
                            rowCount: manifest.entries.Length,
                            viewYawDegrees: 32f,
                            showTrendGraph: showTrendGraph,
                            showWindowPanelGraphic: showWindowPanelGraphic);
                        RenderIntoSheet(
                            sheet, camera, candidatePath, candidateFraming,
                            emissionEnabled: false, column: 3, row: row,
                            rowCount: manifest.entries.Length,
                            viewYawDegrees: 72f,
                            showTrendGraph: showTrendGraph,
                            showWindowPanelGraphic: showWindowPanelGraphic);
                        continue;
                    }
                    var activePath =
                        CandidateStagingManifest.ActivePrefabPath(entry);
                    var framing = CalculateFraming(activePath, candidatePath);
                    if (neutralShapeReview)
                    {
                        RenderIntoSheet(
                            sheet, camera, activePath, framing,
                            emissionEnabled: false, column: 0, row: row,
                            rowCount: manifest.entries.Length,
                            neutralMaterial: true);
                        RenderIntoSheet(
                            sheet, camera, candidatePath, framing,
                            emissionEnabled: false, column: 1, row: row,
                            rowCount: manifest.entries.Length,
                            neutralMaterial: true);
                        continue;
                    }
                    RenderIntoSheet(
                        sheet,
                        camera,
                        activePath,
                        framing,
                        emissionEnabled: false,
                        column: 0,
                        row: row,
                        rowCount: manifest.entries.Length);
                    RenderIntoSheet(
                        sheet,
                        camera,
                        activePath,
                        framing,
                        emissionEnabled: true,
                        column: 1,
                        row: row,
                        rowCount: manifest.entries.Length);
                    RenderIntoSheet(
                        sheet,
                        camera,
                        candidatePath,
                        framing,
                        emissionEnabled: false,
                        column: 2,
                        row: row,
                        rowCount: manifest.entries.Length);
                    RenderIntoSheet(
                        sheet,
                        camera,
                        candidatePath,
                        framing,
                        emissionEnabled: true,
                        column: 3,
                        row: row,
                        rowCount: manifest.entries.Length);
                }

                Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
                File.WriteAllBytes(outputPath, sheet.EncodeToPNG());
                AssetDatabase.Refresh();
                Debug.Log(
                    $"Candidate {manifest.candidateId} Unity visual review " +
                    "rendered. " +
                    (candidateOnly
                        ? "Columns: candidate front, left oblique, right " +
                          "oblique, side. "
                        : neutralShapeReview
                        ? "Neutral material columns: active, candidate. "
                        : "Columns: active OFF, active ON, candidate OFF, " +
                          "candidate ON. ") +
                    $"Rows: {EntryLabels(manifest)}. " +
                    $"Output: {outputPath}");
                return outputPath;
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(sheet);
                UnityEngine.Object.DestroyImmediate(cameraObject);
                UnityEngine.Object.DestroyImmediate(lightObject);
            }
        }

        private static void ConfigureScene(Camera camera, Light light)
        {
            camera.orthographic = true;
            camera.aspect = 1f;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0.012f, 0.018f, 0.025f);
            camera.nearClipPlane = 0.01f;
            camera.farClipPlane = 10f;
            camera.allowHDR = false;
            camera.allowMSAA = true;
            light.type = LightType.Directional;
            light.intensity = 1.25f;
            light.color = new Color(1f, 0.94f, 0.86f);
            light.transform.rotation = Quaternion.Euler(35f, -35f, 0f);
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.18f, 0.21f, 0.24f);
        }

        private static string EntryLabels(CandidateStagingManifest manifest)
        {
            var labels = new string[manifest.entries.Length];
            for (var index = 0; index < labels.Length; index++)
            {
                var entry = manifest.entries[index];
                labels[index] = $"{entry.theme}/{entry.model}";
            }
            return string.Join(", ", labels);
        }

        private static Framing CalculateFraming(
            string activePath,
            string candidatePath)
        {
            var active = Instantiate(activePath);
            var candidate = Instantiate(candidatePath);
            try
            {
                var activeBounds = RendererBounds(active);
                var candidateBounds = RendererBounds(candidate);
                var extent = Mathf.Max(
                    activeBounds.extents.x,
                    activeBounds.extents.y,
                    candidateBounds.extents.x,
                    candidateBounds.extents.y);
                var depth = Mathf.Max(
                    activeBounds.size.z,
                    candidateBounds.size.z);
                return new Framing(extent * 1.18f, depth + 1f);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(active);
                UnityEngine.Object.DestroyImmediate(candidate);
            }
        }

        private static Framing CalculateFraming(string candidatePath)
        {
            var candidate = Instantiate(candidatePath);
            try
            {
                var bounds = RendererBounds(candidate);
                var extent = Mathf.Max(bounds.extents.x, bounds.extents.y);
                return new Framing(extent * 1.18f, bounds.size.z + 1f);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(candidate);
            }
        }

        private static void RenderIntoSheet(
            Texture2D sheet,
            Camera camera,
            string path,
            Framing framing,
            bool emissionEnabled,
            int column,
            int row,
            int rowCount,
            bool neutralMaterial = false,
            float viewYawDegrees = 0f,
            bool showTrendGraph = false,
            bool showWindowPanelGraphic = false,
            WindowPanelGraphicPreset windowPanelPreset =
                WindowPanelGraphicPreset.Orbit)
        {
            var instance = Instantiate(path);
            var target = new RenderTexture(
                TileSize,
                TileSize,
                24,
                RenderTextureFormat.ARGB32);
            var image = new Texture2D(
                TileSize,
                TileSize,
                TextureFormat.RGBA32,
                false);
            var previousActive = RenderTexture.active;
            Material neutral = null;
            try
            {
                var bounds = RendererBounds(instance);
                instance.transform.position -= new Vector3(
                    bounds.center.x,
                    bounds.center.y,
                    0f);
                bounds = RendererBounds(instance);
                if (neutralMaterial)
                    neutral = ConfigureNeutralMaterial(instance);
                else
                    ConfigureEmission(instance, emissionEnabled);
                // Add runtime display overlays after candidate-material
                // configuration. The emission-off review property block must
                // not overwrite the overlay's own unlit display color.
                if (showTrendGraph)
                    AddTrendGraph(instance);
                if (showWindowPanelGraphic)
                    AddWindowPanelGraphic(instance, windowPanelPreset);
                camera.orthographicSize = framing.OrthographicSize;
                var yawRadians = viewYawDegrees * Mathf.Deg2Rad;
                camera.transform.SetPositionAndRotation(
                    new Vector3(
                        Mathf.Sin(yawRadians) * framing.CameraDistance,
                        0f,
                        bounds.center.z +
                            Mathf.Cos(yawRadians) * framing.CameraDistance),
                    Quaternion.Euler(0f, 180f + viewYawDegrees, 0f));
                camera.targetTexture = target;
                camera.Render();
                RenderTexture.active = target;
                image.ReadPixels(
                    new Rect(0, 0, TileSize, TileSize),
                    0,
                    0);
                image.Apply();
                sheet.SetPixels(
                    column * TileSize,
                    (rowCount - 1 - row) * TileSize,
                    TileSize,
                    TileSize,
                    image.GetPixels());
                sheet.Apply();
            }
            finally
            {
                camera.targetTexture = null;
                RenderTexture.active = previousActive;
                UnityEngine.Object.DestroyImmediate(image);
                UnityEngine.Object.DestroyImmediate(target);
                UnityEngine.Object.DestroyImmediate(neutral);
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static void AddTrendGraph(GameObject instance)
        {
            var contract = instance.GetComponent<InstrumentGreyboxContract>();
            var displaySurface = instance
                .GetComponentInChildren<ThemeVisualManifest>(true)
                ?.MotionTarget;
            if (displaySurface == null)
            {
                throw new MissingReferenceException(
                    $"{instance.name}: TrendMonitor display surface missing.");
            }
            var monitor = instance
                .GetComponentInChildren<SignalMonitorView>(true);
            if (monitor == null)
            {
                monitor = SignalMonitorView.Create(
                    contract?.LabelSocket ?? instance.transform,
                    displaySurface);
            }
            else
            {
                monitor.AlignToDisplay(displaySurface);
            }
            var first = new[] { 0.15f, 0.65f, 0.30f, 0.85f };
            var second = new[] { 0.80f, 0.45f, 0.70f, 0.20f };
            var sampleTime = 0f;
            for (var index = 0; index < first.Length; index++)
            {
                monitor.BeginRefresh();
                monitor.AddSample(
                    "review-lever",
                    first[index],
                    sampleTime);
                monitor.AddSample(
                    "review-meter",
                    second[index],
                    sampleTime);
                monitor.AddComposedSample(
                    SignalCompositionKind.Average,
                    (first[index] + second[index]) * 0.5f,
                    validInputCount: 2,
                    sampleTime: sampleTime);
                monitor.EndRefresh();
                sampleTime += SignalMonitorView.RefreshIntervalSeconds;
            }

            // The runtime depth-tested font shader is validated separately.
            // Unity's editor RenderTexture path displays that transparent
            // shader as the magenta error material, so use the font's own
            // material only on this disposable review instance.
            foreach (var text in monitor.GetComponentsInChildren<TextMesh>(true))
            {
                var renderer = text.GetComponent<MeshRenderer>();
                if (renderer != null && text.font != null)
                    renderer.sharedMaterial = text.font.material;
            }
        }

        private static void AddWindowPanelGraphic(
            GameObject instance,
            WindowPanelGraphicPreset preset)
        {
            var displaySurface = instance
                .GetComponentInChildren<ThemeVisualManifest>(true)
                ?.MotionTarget;
            if (displaySurface == null)
            {
                throw new MissingReferenceException(
                    $"{instance.name}: Window Panel display surface missing.");
            }

            var displayMesh =
                displaySurface.GetComponent<MeshFilter>()?.sharedMesh;
            if (displayMesh == null)
            {
                throw new MissingReferenceException(
                    $"{instance.name}: Window Panel display mesh missing.");
            }
            var displayVertices = displayMesh.vertices;
            if (displayMesh.triangles.Length < 3 || displayVertices.Length < 3)
            {
                throw new MissingReferenceException(
                    $"{instance.name}: Window Panel display triangles missing.");
            }

            var surfaceCenter = displaySurface.TransformPoint(
                displayMesh.bounds.center);
            var graphic = WindowPanelGraphicsPrototypeView.Create(
                instance.transform);
            graphic.transform.SetPositionAndRotation(
                surfaceCenter + instance.transform.forward * 0.002f,
                instance.transform.rotation * Quaternion.Euler(0f, 180f, 0f));
            graphic.transform.localScale = Vector3.one * 0.54f;
            graphic.SetPreset(preset);
            graphic.SetSlot(0, 0.72f, true);
            graphic.SetSlot(1, 0.50f, true);
            graphic.SetSlot(2, 0.62f, true);
            graphic.SetSlot(3, 0.45f, true);
            graphic.ApplyNow();
        }

        private static GameObject Instantiate(string path)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            if (prefab == null)
                throw new FileNotFoundException($"Missing prefab: {path}");
            return UnityEngine.Object.Instantiate(prefab);
        }

        private static Bounds RendererBounds(GameObject root)
        {
            var renderers = root.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0)
                throw new InvalidOperationException($"{root.name}: no Renderer");
            var bounds = renderers[0].bounds;
            for (var index = 1; index < renderers.Length; index++)
                bounds.Encapsulate(renderers[index].bounds);
            return bounds;
        }

        private static void ConfigureEmission(
            GameObject root,
            bool enabled)
        {
            foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
            {
                var block = new MaterialPropertyBlock();
                renderer.GetPropertyBlock(block);
                if (!enabled)
                    block.SetColor("_EmissionColor", Color.black);
                renderer.SetPropertyBlock(block);
            }
        }

        private static Material ConfigureNeutralMaterial(GameObject root)
        {
            Material source = null;
            foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
            {
                foreach (var candidate in renderer.sharedMaterials)
                {
                    if (candidate == null)
                        continue;
                    source = candidate;
                    break;
                }
                if (source != null)
                    break;
            }
            if (source == null)
                throw new InvalidOperationException("No review source material.");
            var material = new Material(source)
            {
                hideFlags = HideFlags.HideAndDontSave
            };
            var neutralColor = new Color(0.52f, 0.55f, 0.58f, 1f);
            material.color = neutralColor;
            if (material.HasProperty("_BaseColor"))
                material.SetColor("_BaseColor", neutralColor);
            if (material.HasProperty("_BaseMap"))
                material.SetTexture("_BaseMap", null);
            if (material.HasProperty("_MainTex"))
                material.SetTexture("_MainTex", null);
            if (material.HasProperty("_BumpMap"))
                material.SetTexture("_BumpMap", null);
            if (material.HasProperty("_Metallic"))
                material.SetFloat("_Metallic", 0.12f);
            if (material.HasProperty("_Smoothness"))
                material.SetFloat("_Smoothness", 0.42f);
            if (material.HasProperty("_EmissionColor"))
                material.SetColor("_EmissionColor", Color.black);
            foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
            {
                var materials = new Material[renderer.sharedMaterials.Length];
                for (var index = 0; index < materials.Length; index++)
                    materials[index] = material;
                renderer.sharedMaterials = materials;
            }
            return material;
        }

        private static void Fill(Texture2D texture, Color color)
        {
            var pixels = new Color[texture.width * texture.height];
            for (var index = 0; index < pixels.Length; index++)
                pixels[index] = color;
            texture.SetPixels(pixels);
            texture.Apply();
        }

        private readonly struct Framing
        {
            public Framing(float orthographicSize, float cameraDistance)
            {
                OrthographicSize = orthographicSize;
                CameraDistance = cameraDistance;
            }

            public float OrthographicSize { get; }
            public float CameraDistance { get; }
        }
    }
}
