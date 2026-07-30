using System;
using System.IO;
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
            ("WindowPanel", "vane_pivot")
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
                    IsLargeAsset(asset.Key)
                        ? largeOpaque
                        : IsMediumAsset(asset.Key)
                            ? mediumOpaque
                            : opaque,
                    IsLargeAsset(asset.Key)
                        ? largeEmissive
                        : IsMediumAsset(asset.Key)
                            ? mediumEmissive
                            : emissive);
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

        private static void BuildPrefab(
            string modelRoot,
            string prefabRoot,
            string suffix,
            string key,
            string targetName,
            Material opaque,
            Material emissive)
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
            modelInstance.transform.localRotation = Quaternion.Euler(-90f, 0f, 0f);
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
                            source[index] != null &&
                            source[index].name.Contains(
                                "Emissive",
                                StringComparison.OrdinalIgnoreCase)
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
