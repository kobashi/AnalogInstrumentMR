using System;
using System.IO;
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

        internal static string RenderManifest(string manifestPath)
        {
            return RenderManifest(manifestPath, neutralShapeReview: false);
        }

        internal static string RenderNeutralManifest(string manifestPath)
        {
            return RenderManifest(manifestPath, neutralShapeReview: true);
        }

        private static string RenderManifest(
            string manifestPath,
            bool neutralShapeReview)
        {
            var manifest = CandidateStagingManifest.Load(manifestPath);
            var outputPath =
                $"Builds/Reports/candidate-{manifest.candidateId}-" +
                (neutralShapeReview
                    ? "unity-neutral-shape-contact-sheet.png"
                    : "unity-visual-contact-sheet.png");
            var cameraObject = new GameObject("[Review] Camera");
            var lightObject = new GameObject("[Review] Light");
            var camera = cameraObject.AddComponent<Camera>();
            var light = lightObject.AddComponent<Light>();
            var columnCount = neutralShapeReview ? 2 : 4;
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
                    var activePath =
                        CandidateStagingManifest.ActivePrefabPath(entry);
                    var candidatePath = manifest.CandidatePrefabPath(entry);
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
                    (neutralShapeReview
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

        private static void RenderIntoSheet(
            Texture2D sheet,
            Camera camera,
            string path,
            Framing framing,
            bool emissionEnabled,
            int column,
            int row,
            int rowCount,
            bool neutralMaterial = false)
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
                camera.orthographicSize = framing.OrthographicSize;
                camera.transform.SetPositionAndRotation(
                    new Vector3(
                        0f,
                        0f,
                        bounds.center.z + framing.CameraDistance),
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
