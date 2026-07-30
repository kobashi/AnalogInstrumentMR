using System;
using System.IO;
using MatsuMotoMeterAR.Instruments;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class V6ModelReplacementStagingBuilder
    {
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates";
        private const string StagingRoot =
            CandidateRoot + "/V6ReplacementStaging";

        private static readonly ThemeEntry[] Themes =
        {
            new(
                "OrbitalAnalog",
                new Color(0.10f, 0.68f, 0.78f),
                3.2f),
            new(
                "ForgeBrass",
                new Color(0.78f, 0.28f, 0.025f),
                2.8f),
            new(
                "KineticSafety",
                new Color(0.02f, 0.62f, 0.76f),
                3.4f)
        };

        private static readonly ModelEntry[] Models =
        {
            new("MeterRound", "needle_pivot"),
            new("Lever", "handle_pivot"),
            new("Toggle", "switch_pivot"),
            new("Rotary", "knob_pivot"),
            new("Button", "button_travel"),
            new("Lamp", "indicator"),
            new("Throttle", "throttle_pivot"),
            new("PowerSlider", "slider_travel"),
            new("StatusIndicator", "indicator"),
            new("MeterMedium", "needle_pivot"),
            new("MeterLarge", "needle_pivot"),
            new("WindowMeter", "needle_pivot"),
            new("WindowPanel", "vane_pivot")
        };

        private const float StandardBumpScale = 0.32f;
        private const float MediumBumpScale = 0.28f;
        private const float LargeBumpScale = 0.24f;

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build V6 Staging Prefabs")]
        public static void Build()
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var theme in Themes)
                BuildTheme(theme);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            Debug.Log(
                "V6 replacement staging is ready. Active models and " +
                "prefabs were not modified.");
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Apply V6 Staging to Production")]
        public static void ApplyToProduction()
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var backupRoot =
                $"Builds/ModelReplacementBackups/" +
                $"V6PreSwitch_{DateTime.Now:yyyyMMdd_HHmmss}";
            foreach (var theme in Themes)
            {
                foreach (var model in Models)
                {
                    var staged =
                        $"{CandidateRoot}/{theme.Folder}/" +
                        "ThemeHardSurfaceV6Material/" +
                        $"SM_{model.Key}_{theme.Folder}_V6_Material.fbx";
                    var active =
                        $"Assets/MatsuMotoMeterAR/Content/Themes/" +
                        $"{theme.Folder}/Models/" +
                        $"SM_{model.Key}_{theme.Folder}.fbx";
                    BackupIfPresent(active, backupRoot);
                    CopyRequired(staged, active);
                }

                var activePrefabRoot =
                    $"Assets/MatsuMotoMeterAR/Resources/" +
                    $"{theme.Folder}/Prefabs";
                foreach (var model in Models)
                {
                    BackupIfPresent(
                        $"{activePrefabRoot}/" +
                        $"PF_Visual_{model.Key}_{theme.Folder}.prefab",
                        backupRoot);
                }
                BackupIfPresent(
                    $"Assets/MatsuMotoMeterAR/Content/Themes/" +
                    $"{theme.Folder}/Materials/" +
                    $"MAT_{theme.Folder}_Atlas.mat",
                    backupRoot);
                BackupIfPresent(
                    $"Assets/MatsuMotoMeterAR/Content/Themes/" +
                    $"{theme.Folder}/Materials/" +
                    $"MAT_{theme.Folder}_Emissive.mat",
                    backupRoot);
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            OrbitalAnalogUnityAssetBuilder.Rebuild();
            RefinedModelReplacementValidator.ValidateActivePrefabs();
            Debug.Log(
                $"V6 production replacement completed. Backup: {backupRoot}");
        }

        private static void BuildTheme(ThemeEntry theme)
        {
            var textureRoot =
                $"Assets/MatsuMotoMeterAR/Content/Themes/{theme.Folder}/" +
                "Textures/ThemeMaterialV6";
            var modelRoot =
                $"{CandidateRoot}/{theme.Folder}/" +
                "ThemeHardSurfaceV6Material";
            var materialRoot =
                $"{StagingRoot}/{theme.Folder}/Materials";
            var prefabRoot =
                $"{StagingRoot}/{theme.Folder}/Prefabs";
            Directory.CreateDirectory(materialRoot);
            Directory.CreateDirectory(prefabRoot);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

            foreach (var atlasSuffix in new[] { "", "_Medium", "_Large" })
            {
                ConfigureTexture(
                    $"{textureRoot}/T_{theme.Folder}_V6_Atlas" +
                    $"{atlasSuffix}_BaseColor.png",
                    false);
                ConfigureTexture(
                    $"{textureRoot}/T_{theme.Folder}_V6_Atlas" +
                    $"{atlasSuffix}_Normal.png",
                    true);
                ConfigureTexture(
                    $"{textureRoot}/T_{theme.Folder}_V6_Atlas" +
                    $"{atlasSuffix}_MetallicSmoothness.png",
                    false,
                    linear: true);
                ConfigureTexture(
                    $"{textureRoot}/T_{theme.Folder}_V6_Atlas" +
                    $"{atlasSuffix}_Emission.png",
                    false);
            }

            foreach (var model in Models)
            {
                ConfigureModel(
                    $"{modelRoot}/" +
                    $"SM_{model.Key}_{theme.Folder}_V6_Material.fbx");
            }

            var opaque = BuildOpaqueMaterial(
                materialRoot,
                textureRoot,
                theme.Folder,
                "",
                StandardBumpScale);
            var emissive = BuildEmissiveMaterial(
                materialRoot,
                textureRoot,
                theme,
                "",
                StandardBumpScale);
            var largeOpaque = BuildOpaqueMaterial(
                materialRoot,
                textureRoot,
                theme.Folder,
                "_Large",
                LargeBumpScale);
            var largeEmissive = BuildEmissiveMaterial(
                materialRoot,
                textureRoot,
                theme,
                "_Large",
                LargeBumpScale);
            var mediumOpaque = BuildOpaqueMaterial(
                materialRoot,
                textureRoot,
                theme.Folder,
                "_Medium",
                MediumBumpScale);
            var mediumEmissive = BuildEmissiveMaterial(
                materialRoot,
                textureRoot,
                theme,
                "_Medium",
                MediumBumpScale);
            foreach (var model in Models)
            {
                BuildPrefab(
                    modelRoot,
                    prefabRoot,
                    theme.Folder,
                    model,
                    IsLargeAsset(model.Key)
                        ? largeOpaque
                        : IsMediumAsset(model.Key)
                            ? mediumOpaque
                            : opaque,
                    IsLargeAsset(model.Key)
                        ? largeEmissive
                        : IsMediumAsset(model.Key)
                            ? mediumEmissive
                            : emissive);
            }
        }

        private static Material BuildOpaqueMaterial(
            string materialRoot,
            string textureRoot,
            string theme,
            string scaleSuffix,
            float bumpScale)
        {
            var material = LoadOrCreateMaterial(
                $"{materialRoot}/MAT_{theme}_V6_Atlas" +
                $"{scaleSuffix}_Staging.mat");
            ConfigureLitMaterial(
                material,
                textureRoot,
                theme,
                scaleSuffix,
                bumpScale);
            material.DisableKeyword("_EMISSION");
            material.SetColor("_EmissionColor", Color.black);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material BuildEmissiveMaterial(
            string materialRoot,
            string textureRoot,
            ThemeEntry theme,
            string scaleSuffix,
            float bumpScale)
        {
            var material = LoadOrCreateMaterial(
                $"{materialRoot}/" +
                $"MAT_{theme.Folder}_V6_Emissive" +
                $"{scaleSuffix}_Staging.mat");
            ConfigureLitMaterial(
                material,
                textureRoot,
                theme.Folder,
                scaleSuffix,
                bumpScale);
            material.SetTexture(
                "_EmissionMap",
                LoadTexture(
                    $"{textureRoot}/" +
                    $"T_{theme.Folder}_V6_Atlas" +
                    $"{scaleSuffix}_Emission.png"));
            material.SetColor(
                "_EmissionColor",
                theme.EmissionColor * theme.EmissionStrength);
            material.EnableKeyword("_EMISSION");
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void ConfigureLitMaterial(
            Material material,
            string textureRoot,
            string theme,
            string scaleSuffix,
            float bumpScale)
        {
            var atlasPrefix =
                $"{textureRoot}/T_{theme}_V6_Atlas{scaleSuffix}";
            material.SetTexture(
                "_BaseMap",
                LoadTexture($"{atlasPrefix}_BaseColor.png"));
            material.SetTexture(
                "_BumpMap",
                LoadTexture($"{atlasPrefix}_Normal.png"));
            material.SetTexture(
                "_MetallicGlossMap",
                LoadTexture(
                    $"{atlasPrefix}_MetallicSmoothness.png"));
            material.SetFloat("_BumpScale", bumpScale);
            material.SetFloat("_Metallic", 1f);
            material.SetFloat("_Smoothness", 1f);
            material.EnableKeyword("_NORMALMAP");
            material.EnableKeyword("_METALLICSPECGLOSSMAP");
        }

        private static bool IsLargeAsset(string key)
        {
            return key == "MeterLarge" ||
                   key == "WindowMeter" ||
                   key == "WindowPanel";
        }

        private static bool IsMediumAsset(string key)
        {
            return key == "MeterMedium";
        }

        private static Material LoadOrCreateMaterial(string path)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null)
            {
                throw new InvalidOperationException(
                    "Universal Render Pipeline/Lit shader was not found.");
            }

            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(material, path);
            }
            else
            {
                material.shader = shader;
            }
            return material;
        }

        private static void BuildPrefab(
            string modelRoot,
            string prefabRoot,
            string theme,
            ModelEntry model,
            Material opaque,
            Material emissive)
        {
            var modelPath =
                $"{modelRoot}/SM_{model.Key}_{theme}_V6_Material.fbx";
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (source == null)
                throw new FileNotFoundException($"Missing V6 FBX: {modelPath}");

            var imported =
                PrefabUtility.InstantiatePrefab(source) as GameObject;
            if (imported == null)
            {
                throw new InvalidOperationException(
                    $"Could not instantiate V6 FBX: {modelPath}");
            }

            var prefabName = $"PF_Visual_{model.Key}_{theme}";
            var root = new GameObject(prefabName);
            imported.transform.SetParent(root.transform, false);
            imported.transform.localPosition = Vector3.zero;
            imported.transform.localRotation =
                Quaternion.Euler(-90f, 0f, 0f);
            imported.transform.localScale = Vector3.one;

            try
            {
                MoveVisualInFrontOfMountPlane(imported);
                foreach (var renderer in
                         root.GetComponentsInChildren<Renderer>(true))
                {
                    var sourceMaterials = renderer.sharedMaterials;
                    var replacements =
                        new Material[sourceMaterials.Length];
                    for (var index = 0;
                         index < sourceMaterials.Length;
                         index++)
                    {
                        var sourceMaterial = sourceMaterials[index];
                        replacements[index] =
                            sourceMaterial != null &&
                            sourceMaterial.name.Contains(
                                "Emissive",
                                StringComparison.OrdinalIgnoreCase)
                                ? emissive
                                : opaque;
                    }
                    renderer.sharedMaterials = replacements;
                }

                foreach (var collider in
                         root.GetComponentsInChildren<Collider>(true))
                {
                    UnityEngine.Object.DestroyImmediate(collider);
                }

                var motionTarget = FindNode(
                    root.transform,
                    model.MotionTarget);
                var manifest = root.AddComponent<ThemeVisualManifest>();
                var indicatorRenderer =
                    model.Key == "Lamp"
                        ? FindRenderer(
                            root.transform,
                            model.MotionTarget)
                        : null;
                var stateRenderers =
                    model.Key == "StatusIndicator"
                        ? new[]
                        {
                            FindRenderer(root.transform, "status_safe"),
                            FindRenderer(root.transform, "status_warn"),
                            FindRenderer(root.transform, "status_danger")
                        }
                        : null;
                manifest.Configure(
                    motionTarget,
                    indicatorRenderer,
                    stateRenderers);

                var prefabPath =
                    $"{prefabRoot}/{prefabName}.prefab";
                if (PrefabUtility.SaveAsPrefabAsset(root, prefabPath) == null)
                {
                    throw new InvalidOperationException(
                        $"Could not save staging prefab: {prefabPath}");
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static Transform FindNode(
            Transform root,
            string expectedName)
        {
            foreach (var candidate in
                     root.GetComponentsInChildren<Transform>(true))
            {
                if (candidate.name == expectedName)
                    return candidate;
            }
            throw new MissingReferenceException(
                $"{root.name} is missing {expectedName}.");
        }

        private static Renderer FindRenderer(
            Transform root,
            string expectedName)
        {
            var node = FindNode(root, expectedName);
            var renderer = node.GetComponentInChildren<Renderer>(true);
            if (renderer == null)
            {
                throw new MissingReferenceException(
                    $"{root.name}/{expectedName} has no Renderer.");
            }
            return renderer;
        }

        private static void MoveVisualInFrontOfMountPlane(GameObject visual)
        {
            var renderers = visual.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0)
                return;
            var bounds = renderers[0].bounds;
            for (var index = 1; index < renderers.Length; index++)
                bounds.Encapsulate(renderers[index].bounds);
            if (bounds.min.z < 0f)
            {
                visual.transform.localPosition +=
                    Vector3.forward * -bounds.min.z;
            }
        }

        private static Texture2D LoadTexture(string path)
        {
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null)
                throw new FileNotFoundException($"Missing texture: {path}");
            return texture;
        }

        private static void ConfigureTexture(
            string path,
            bool normalMap,
            bool linear = false)
        {
            if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
            {
                throw new FileNotFoundException(
                    $"Texture importer was not found: {path}");
            }
            importer.textureType =
                normalMap
                    ? TextureImporterType.NormalMap
                    : TextureImporterType.Default;
            importer.sRGBTexture = !linear && !normalMap;
            importer.mipmapEnabled = true;
            importer.textureCompression =
                TextureImporterCompression.Compressed;
            importer.SaveAndReimport();
        }

        private static void ConfigureModel(string path)
        {
            if (AssetImporter.GetAtPath(path) is not ModelImporter importer)
                throw new FileNotFoundException($"Missing model: {path}");
            importer.bakeAxisConversion = true;
            importer.globalScale = 1f;
            importer.importAnimation = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.addCollider = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            importer.SaveAndReimport();
        }

        private static void CopyRequired(string source, string destination)
        {
            if (!File.Exists(source))
                throw new FileNotFoundException($"Missing staged FBX: {source}");
            var directory = Path.GetDirectoryName(destination);
            if (!string.IsNullOrEmpty(directory))
                Directory.CreateDirectory(directory);
            File.Copy(source, destination, true);
        }

        private static void BackupIfPresent(
            string source,
            string backupRoot)
        {
            if (!File.Exists(source))
                return;
            var destination = Path.Combine(backupRoot, source);
            var directory = Path.GetDirectoryName(destination);
            if (!string.IsNullOrEmpty(directory))
                Directory.CreateDirectory(directory);
            File.Copy(source, destination, true);
        }

        private readonly struct ThemeEntry
        {
            public ThemeEntry(
                string folder,
                Color emissionColor,
                float emissionStrength)
            {
                Folder = folder;
                EmissionColor = emissionColor;
                EmissionStrength = emissionStrength;
            }

            public string Folder { get; }
            public Color EmissionColor { get; }
            public float EmissionStrength { get; }
        }

        private readonly struct ModelEntry
        {
            public ModelEntry(string key, string motionTarget)
            {
                Key = key;
                MotionTarget = motionTarget;
            }

            public string Key { get; }
            public string MotionTarget { get; }
        }
    }
}
