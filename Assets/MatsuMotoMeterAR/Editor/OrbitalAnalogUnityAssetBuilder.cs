using System;
using System.IO;
using System.Linq;
using MatsuMotoMeterAR.Instruments;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class OrbitalAnalogUnityAssetBuilder
    {
        private static readonly (string Folder, string Suffix, Color Emission)[] Themes =
        {
            ("OrbitalAnalog", "OrbitalAnalog", new Color(0.12f, 0.78f, 1f)),
            ("ForgeBrass", "ForgeBrass", new Color(1f, 0.62f, 0.22f)),
            ("KineticSafety", "KineticSafety", new Color(0.10f, 0.72f, 0.94f))
        };

        private static readonly (string Key, string Target)[] Assets =
        {
            ("MeterRound", "needle_pivot"),
            ("Lever", "handle_pivot"),
            ("Toggle", "switch_pivot"),
            ("Rotary", "knob_pivot"),
            ("Button", "button_travel"),
            ("Lamp", "indicator"),
            ("Throttle", "throttle_pivot"),
            ("PowerSlider", "slider_travel")
        };

        private static readonly (string Key, string Target)[] OptionalAssets =
        {
            ("StatusIndicator", "indicator"),
            ("MeterMedium", "needle_pivot"),
            ("MeterLarge", "needle_pivot"),
            ("WindowMeter", "needle_pivot"),
            ("WindowPanel", "vane_pivot"),
            ("TrendMonitor", "display_surface")
        };

        private const float StandardBumpScale = 0.32f;
        private const float MediumBumpScale = 0.28f;
        private const float LargeBumpScale = 0.24f;

        [MenuItem("Tools/MatsuMotoMeterAR/Rebuild Instrument Theme Assets")]
        public static void Rebuild()
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var theme in Themes)
                BuildTheme(theme.Folder, theme.Suffix, theme.Emission);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("All instrument theme materials and prefabs rebuilt.");
        }

        internal static void RebuildModel(string folder, string key)
        {
            foreach (var theme in Themes)
            {
                if (!string.Equals(theme.Folder, folder, StringComparison.Ordinal))
                    continue;

                string target = null;
                foreach (var asset in Assets)
                {
                    if (string.Equals(asset.Key, key, StringComparison.Ordinal))
                    {
                        target = asset.Target;
                        break;
                    }
                }
                if (target == null)
                {
                    foreach (var asset in OptionalAssets)
                    {
                        if (string.Equals(asset.Key, key, StringComparison.Ordinal))
                        {
                            target = asset.Target;
                            break;
                        }
                    }
                }
                if (target == null)
                    throw new InvalidDataException($"Unsupported visual model: {key}");

                var themeRoot =
                    $"Assets/MatsuMotoMeterAR/Content/Themes/{folder}";
                var modelRoot = themeRoot + "/Models";
                var materialRoot = themeRoot + "/Materials";
                var textureRoot = themeRoot + "/Textures/TrendMonitor";
                var prefabRoot =
                    $"Assets/MatsuMotoMeterAR/Resources/{folder}/Prefabs";
                var modelPath = $"{modelRoot}/SM_{key}_{theme.Suffix}.fbx";
                ConfigureModel(modelPath);
                if (key == "TrendMonitor")
                    ConfigureTrendMonitorTextures(textureRoot, theme.Folder);

                var scaleSuffix = IsLargeAsset(key)
                    ? "_Large"
                    : IsMediumAsset(key)
                        ? "_Medium"
                        : string.Empty;
                var opaque = key == "TrendMonitor"
                    ? BuildTrendMonitorRoleMaterial(
                        materialRoot, textureRoot, theme.Folder,
                        emissive: false)
                    : LoadRequiredMaterial(
                        $"{materialRoot}/MAT_{theme.Suffix}_Atlas{scaleSuffix}.mat");
                var emissive = key == "TrendMonitor"
                    ? BuildTrendMonitorRoleMaterial(
                        materialRoot, textureRoot, theme.Folder,
                        emissive: true)
                    : LoadRequiredMaterial(
                        $"{materialRoot}/MAT_{theme.Suffix}_Emissive{scaleSuffix}.mat");
                BuildPrefab(
                    modelRoot,
                    prefabRoot,
                    theme.Suffix,
                    key,
                    target,
                    opaque,
                    emissive,
                    key == "TrendMonitor"
                        ? BuildTrendMonitorDisplayMaterial(
                            materialRoot, theme.Folder)
                        : null);
                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                return;
            }

            throw new InvalidDataException($"Unsupported visual theme: {folder}");
        }

        private static void BuildTheme(
            string folder,
            string suffix,
            Color emissionColor)
        {
            var themeRoot =
                $"Assets/MatsuMotoMeterAR/Content/Themes/{folder}";
            var modelRoot = themeRoot + "/Models";
            var textureRoot = themeRoot + "/Textures";
            var v6TextureRoot = textureRoot + "/ThemeMaterialV6";
            var materialRoot = themeRoot + "/Materials";
            var prefabRoot =
                $"Assets/MatsuMotoMeterAR/Resources/{folder}/Prefabs";
            Directory.CreateDirectory(materialRoot);
            Directory.CreateDirectory(prefabRoot);

            foreach (var atlasSuffix in new[] { "", "_Medium", "_Large" })
            {
                ConfigureTexture(
                    $"{v6TextureRoot}/T_{suffix}_V6_Atlas" +
                    $"{atlasSuffix}_BaseColor.png",
                    false);
                ConfigureTexture(
                    $"{v6TextureRoot}/T_{suffix}_V6_Atlas" +
                    $"{atlasSuffix}_Normal.png",
                    true);
                ConfigureTexture(
                    $"{v6TextureRoot}/T_{suffix}_V6_Atlas" +
                    $"{atlasSuffix}_MetallicSmoothness.png",
                    false,
                    linear: true);
                ConfigureTexture(
                    $"{v6TextureRoot}/T_{suffix}_V6_Atlas" +
                    $"{atlasSuffix}_Emission.png",
                    false,
                    linear: true);
            }
            foreach (var asset in Assets)
                ConfigureModel($"{modelRoot}/SM_{asset.Key}_{suffix}.fbx");
            foreach (var asset in OptionalAssets)
            {
                var path = $"{modelRoot}/SM_{asset.Key}_{suffix}.fbx";
                if (AssetDatabase.LoadAssetAtPath<GameObject>(path) != null)
                    ConfigureModel(path);
            }

            var opaque = BuildOpaqueMaterial(
                materialRoot,
                v6TextureRoot,
                suffix,
                "",
                StandardBumpScale);
            var emissive = BuildEmissiveMaterial(
                materialRoot,
                v6TextureRoot,
                suffix,
                emissionColor,
                "",
                StandardBumpScale);
            var largeOpaque = BuildOpaqueMaterial(
                materialRoot,
                v6TextureRoot,
                suffix,
                "_Large",
                LargeBumpScale);
            var mediumOpaque = BuildOpaqueMaterial(
                materialRoot,
                v6TextureRoot,
                suffix,
                "_Medium",
                MediumBumpScale);
            var mediumEmissive = BuildEmissiveMaterial(
                materialRoot,
                v6TextureRoot,
                suffix,
                emissionColor,
                "_Medium",
                MediumBumpScale);
            var largeEmissive = BuildEmissiveMaterial(
                materialRoot,
                v6TextureRoot,
                suffix,
                emissionColor,
                "_Large",
                LargeBumpScale);
            var trendMonitorOpaque = BuildTrendMonitorRoleMaterial(
                materialRoot,
                themeRoot + "/Textures/TrendMonitor",
                suffix,
                emissive: false);
            var trendMonitorReadout = BuildTrendMonitorRoleMaterial(
                materialRoot,
                themeRoot + "/Textures/TrendMonitor",
                suffix,
                emissive: true);
            var trendMonitorDisplay = BuildTrendMonitorDisplayMaterial(
                materialRoot, suffix);
            foreach (var asset in Assets)
            {
                BuildPrefab(
                    modelRoot,
                    prefabRoot,
                    suffix,
                    asset.Key,
                    asset.Target,
                    opaque,
                    emissive);
            }
            foreach (var asset in OptionalAssets)
            {
                var path = $"{modelRoot}/SM_{asset.Key}_{suffix}.fbx";
                if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null)
                    continue;
                BuildPrefab(
                    modelRoot,
                    prefabRoot,
                    suffix,
                    asset.Key,
                    asset.Target,
                    asset.Key == "TrendMonitor"
                        ? trendMonitorOpaque
                        : IsLargeAsset(asset.Key)
                        ? largeOpaque
                        : IsMediumAsset(asset.Key)
                            ? mediumOpaque
                            : opaque,
                    asset.Key == "TrendMonitor"
                        ? trendMonitorReadout
                        : IsLargeAsset(asset.Key)
                        ? largeEmissive
                        : IsMediumAsset(asset.Key)
                            ? mediumEmissive
                            : emissive,
                    asset.Key == "TrendMonitor"
                        ? trendMonitorDisplay
                        : null);
            }
        }

        private static Material BuildOpaqueMaterial(
            string materialRoot,
            string textureRoot,
            string suffix,
            string scaleSuffix,
            float bumpScale)
        {
            var material = LoadOrCreateMaterial(
                $"{materialRoot}/MAT_{suffix}_Atlas{scaleSuffix}.mat");
            ConfigureLitMaterial(
                material,
                textureRoot,
                suffix,
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
            string suffix,
            Color emissionColor,
            string scaleSuffix,
            float bumpScale)
        {
            var material = LoadOrCreateMaterial(
                $"{materialRoot}/MAT_{suffix}_Emissive{scaleSuffix}.mat");
            ConfigureLitMaterial(
                material,
                textureRoot,
                suffix,
                scaleSuffix,
                bumpScale);
            material.SetTexture(
                "_EmissionMap",
                LoadTexture(
                    $"{textureRoot}/T_{suffix}_V6_Atlas" +
                    $"{scaleSuffix}_Emission.png"));
            material.SetColor("_EmissionColor", emissionColor * 1.5f);
            material.EnableKeyword("_EMISSION");
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material BuildTrendMonitorRoleMaterial(
            string materialRoot,
            string textureRoot,
            string theme,
            bool emissive)
        {
            var role = emissive ? "Readout" : "Opaque";
            var material = LoadOrCreateMaterial(
                $"{materialRoot}/MAT_{theme}_V6_TrendMonitor_{role}.mat");
            foreach (var property in new[]
                     {
                         "_BaseMap", "_MainTex", "_BumpMap",
                         "_MetallicGlossMap", "_EmissionMap"
                     })
            {
                if (material.HasProperty(property))
                    material.SetTexture(property, null);
            }
            material.DisableKeyword("_NORMALMAP");
            material.DisableKeyword("_METALLICSPECGLOSSMAP");

            var baseColor = (theme, emissive) switch
            {
                ("OrbitalAnalog", false) =>
                    new Color(0.09f, 0.12f, 0.14f, 1f),
                ("OrbitalAnalog", true) =>
                    new Color(0.02f, 0.42f, 0.50f, 1f),
                ("ForgeBrass", false) =>
                    new Color(0.20f, 0.16f, 0.12f, 1f),
                ("ForgeBrass", true) =>
                    new Color(0.58f, 0.31f, 0.035f, 1f),
                ("KineticSafety", false) =>
                    new Color(0.11f, 0.13f, 0.14f, 1f),
                _ => new Color(0.62f, 0.25f, 0.025f, 1f)
            };
            material.color = baseColor;
            if (material.HasProperty("_BaseColor"))
                material.SetColor("_BaseColor", baseColor);
            material.SetFloat("_Metallic", emissive ? 0.05f : 0.42f);
            material.SetFloat("_Smoothness", emissive ? 0.34f : 0.48f);
            if (emissive)
            {
                material.SetColor("_EmissionColor", baseColor * 3.2f);
                material.EnableKeyword("_EMISSION");
            }
            else
            {
                material.SetColor("_EmissionColor", Color.black);
                material.DisableKeyword("_EMISSION");
                var prefix = $"{textureRoot}/" +
                             $"T_{theme}_V6_TrendMonitor_T1";
                var baseColorTexture =
                    AssetDatabase.LoadAssetAtPath<Texture2D>(
                        prefix + "_BaseColor.png");
                var normalTexture =
                    AssetDatabase.LoadAssetAtPath<Texture2D>(
                        prefix + "_Normal.png");
                var metallicTexture =
                    AssetDatabase.LoadAssetAtPath<Texture2D>(
                        prefix + "_MetallicSmoothness.png");
                if (baseColorTexture != null && normalTexture != null &&
                    metallicTexture != null)
                {
                    material.color = Color.white;
                    material.SetColor("_BaseColor", Color.white);
                    material.SetTexture("_BaseMap", baseColorTexture);
                    material.SetTexture("_BumpMap", normalTexture);
                    material.SetTexture(
                        "_MetallicGlossMap", metallicTexture);
                    material.SetFloat("_BumpScale", 0.34f);
                    material.SetFloat("_Metallic", 1f);
                    material.SetFloat("_Smoothness", 1f);
                    material.EnableKeyword("_NORMALMAP");
                    material.EnableKeyword("_METALLICSPECGLOSSMAP");
                }
            }
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material BuildTrendMonitorDisplayMaterial(
            string materialRoot,
            string theme)
        {
            var material = LoadOrCreateMaterial(
                $"{materialRoot}/MAT_{theme}_V6_TrendMonitor_Display.mat");
            foreach (var property in new[]
                     {
                         "_BaseMap", "_MainTex", "_BumpMap",
                         "_MetallicGlossMap", "_EmissionMap"
                     })
            {
                if (material.HasProperty(property))
                    material.SetTexture(property, null);
            }
            material.DisableKeyword("_NORMALMAP");
            material.DisableKeyword("_METALLICSPECGLOSSMAP");
            material.DisableKeyword("_EMISSION");
            var color = new Color(0.012f, 0.020f, 0.028f, 1f);
            material.color = color;
            material.SetColor("_BaseColor", color);
            material.SetColor("_EmissionColor", Color.black);
            material.SetFloat("_Metallic", 0f);
            material.SetFloat("_Smoothness", 0.08f);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void ConfigureLitMaterial(
            Material material,
            string textureRoot,
            string suffix,
            string scaleSuffix,
            float bumpScale)
        {
            var atlasPrefix =
                $"{textureRoot}/T_{suffix}_V6_Atlas{scaleSuffix}";
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
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null)
                throw new InvalidOperationException("URP Lit shader was not found.");

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

        private static Material LoadRequiredMaterial(string path)
        {
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
                throw new FileNotFoundException("Required material missing", path);
            return material;
        }

        private static void BuildPrefab(
            string modelRoot,
            string prefabRoot,
            string suffix,
            string key,
            string targetName,
            Material opaque,
            Material emissive,
            Material display = null)
        {
            var expectedRootName = $"PF_Visual_{key}_{suffix}";
            var modelPath = $"{modelRoot}/SM_{key}_{suffix}.fbx";
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (model == null)
                throw new FileNotFoundException($"FBX model was not imported: {modelPath}");

            var modelInstance = PrefabUtility.InstantiatePrefab(model) as GameObject;
            if (modelInstance == null)
                throw new InvalidOperationException($"Could not instantiate {modelPath}.");
            var instance = new GameObject(expectedRootName);
            modelInstance.transform.SetParent(instance.transform, false);
            modelInstance.transform.localPosition = Vector3.zero;
            ConfigureImportedOrientation(
                modelInstance, key, targetName);
            modelInstance.transform.localScale = Vector3.one;

            try
            {
                instance.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                instance.transform.localScale = Vector3.one;
                MoveVisualInFrontOfMountPlane(modelInstance);
                ValidateNode(instance.transform, expectedRootName);
                var motionTarget = FindNode(instance.transform, targetName);

                foreach (var renderer in instance.GetComponentsInChildren<Renderer>(true))
                {
                    var source = renderer.sharedMaterials;
                    var replacements = new Material[source.Length];
                    for (var index = 0; index < source.Length; index++)
                    {
                        replacements[index] =
                            key == "TrendMonitor" &&
                            renderer.transform.name == "display_surface" &&
                            display != null
                                ? display
                                : IsEmissiveMaterialRole(source[index]?.name)
                                ? emissive
                                : opaque;
                    }
                    renderer.sharedMaterials = replacements;
                }

                foreach (var collider in instance.GetComponentsInChildren<Collider>(true))
                    UnityEngine.Object.DestroyImmediate(collider);

                var manifest = instance.GetComponent<ThemeVisualManifest>();
                if (manifest == null)
                    manifest = instance.AddComponent<ThemeVisualManifest>();
                var stateRenderers =
                    key == "StatusIndicator"
                        ? new[]
                        {
                            FindRenderer(instance.transform, "status_safe"),
                            FindRenderer(instance.transform, "status_warn"),
                            FindRenderer(instance.transform, "status_danger")
                        }
                        : null;
                manifest.Configure(
                    motionTarget,
                    key == "Lamp"
                        ? FindRenderer(instance.transform, targetName)
                        : null,
                    stateRenderers);

                var prefabPath = $"{prefabRoot}/{expectedRootName}.prefab";
                if (PrefabUtility.SaveAsPrefabAsset(instance, prefabPath) == null)
                    throw new InvalidOperationException($"Could not save {prefabPath}.");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static void ValidateNode(Transform root, string expectedName)
        {
            FindNode(root, expectedName);
        }

        private static Transform FindNode(Transform root, string expectedName)
        {
            foreach (var candidate in root.GetComponentsInChildren<Transform>(true))
            {
                if (candidate.name == expectedName)
                    return candidate;
            }
            throw new MissingReferenceException(
                $"{root.name} is missing required node {expectedName}.");
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

        private static void ConfigureImportedOrientation(
            GameObject imported,
            string key,
            string targetName)
        {
            if (key != "TrendMonitor")
            {
                imported.transform.localRotation =
                    Quaternion.Euler(-90f, 0f, 0f);
                return;
            }

            imported.transform.localRotation = Quaternion.identity;
            var displaySurface = FindNode(imported.transform, targetName);
            var mesh = displaySurface.GetComponent<MeshFilter>()?.sharedMesh;
            if (mesh == null || mesh.normals.Length == 0)
            {
                throw new MissingReferenceException(
                    "TrendMonitor display_surface has no mesh normals.");
            }
            var currentNormal = displaySurface.TransformDirection(
                mesh.normals[0]).normalized;
            imported.transform.rotation =
                Quaternion.FromToRotation(currentNormal, Vector3.forward) *
                imported.transform.rotation;
            var currentUp = Vector3.ProjectOnPlane(
                displaySurface.up,
                Vector3.forward).normalized;
            if (currentUp.sqrMagnitude < 0.000001f)
            {
                throw new InvalidOperationException(
                    "TrendMonitor display_surface has no usable up axis.");
            }
            var roll = Vector3.SignedAngle(
                currentUp,
                Vector3.up,
                Vector3.forward);
            imported.transform.rotation =
                Quaternion.AngleAxis(roll, Vector3.forward) *
                imported.transform.rotation;
        }

        private static bool IsEmissiveMaterialRole(string materialName)
        {
            return !string.IsNullOrWhiteSpace(materialName) &&
                   (materialName.Contains(
                        "Emissive", StringComparison.OrdinalIgnoreCase) ||
                    materialName.Contains(
                        "Readout", StringComparison.OrdinalIgnoreCase));
        }

        private static Texture2D LoadTexture(string path)
        {
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null)
                throw new FileNotFoundException($"Texture was not imported: {path}");
            return texture;
        }

        private static void ConfigureTexture(
            string path,
            bool normalMap,
            bool linear = false)
        {
            if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
                throw new FileNotFoundException($"Texture importer was not found: {path}");

            importer.textureType =
                normalMap ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = !linear && !normalMap;
            importer.mipmapEnabled = true;
            importer.textureCompression = TextureImporterCompression.Compressed;
            importer.SaveAndReimport();
        }

        internal static void ConfigureTrendMonitorTextures(
            string textureRoot,
            string theme)
        {
            var prefix = $"{textureRoot}/T_{theme}_V6_TrendMonitor_T1";
            var paths = new[]
            {
                prefix + "_BaseColor.png",
                prefix + "_Normal.png",
                prefix + "_MetallicSmoothness.png"
            };
            var present = paths.Count(File.Exists);
            if (present == 0)
                return;
            if (present != paths.Length)
            {
                throw new InvalidDataException(
                    $"{theme}: TrendMonitor texture set is incomplete.");
            }
            ConfigureTexture(paths[0], false);
            ConfigureTexture(paths[1], true);
            ConfigureTexture(paths[2], false, linear: true);
        }

        private static void ConfigureModel(string path)
        {
            if (AssetImporter.GetAtPath(path) is not ModelImporter importer)
                throw new FileNotFoundException($"Model importer was not found: {path}");

            importer.bakeAxisConversion = true;
            importer.globalScale = 1f;
            importer.importAnimation = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.addCollider = false;
            importer.SaveAndReimport();
        }
    }
}
