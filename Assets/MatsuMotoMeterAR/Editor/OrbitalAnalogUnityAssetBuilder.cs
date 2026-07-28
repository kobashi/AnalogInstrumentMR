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
            ("OrbitalAnalog", "OrbitalAnalog", new Color(1f, 0.56f, 0.12f)),
            ("ForgeBrass", "ForgeBrass", new Color(1f, 0.42f, 0.08f)),
            ("KineticSafety", "KineticSafety", new Color(1f, 0.26f, 0.02f))
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
            var materialRoot = themeRoot + "/Materials";
            var prefabRoot =
                $"Assets/MatsuMotoMeterAR/Resources/{folder}/Prefabs";
            Directory.CreateDirectory(materialRoot);
            Directory.CreateDirectory(prefabRoot);

            ConfigureTexture($"{textureRoot}/T_{suffix}_Atlas_Normal.png", true);
            ConfigureTexture(
                $"{textureRoot}/T_{suffix}_Atlas_MetallicSmoothness.png",
                false,
                linear: true);
            ConfigureTexture(
                $"{textureRoot}/T_{suffix}_Atlas_Emission.png",
                false,
                linear: true);
            foreach (var asset in Assets)
                ConfigureModel($"{modelRoot}/SM_{asset.Key}_{suffix}.fbx");

            var opaque = BuildOpaqueMaterial(materialRoot, textureRoot, suffix);
            var emissive = BuildEmissiveMaterial(
                materialRoot,
                textureRoot,
                suffix,
                emissionColor);
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
        }

        private static Material BuildOpaqueMaterial(
            string materialRoot,
            string textureRoot,
            string suffix)
        {
            var material = LoadOrCreateMaterial(
                $"{materialRoot}/MAT_{suffix}_Atlas.mat");
            material.SetTexture(
                "_BaseMap",
                LoadTexture($"{textureRoot}/T_{suffix}_Atlas_BaseColor.png"));
            material.SetTexture(
                "_BumpMap",
                LoadTexture($"{textureRoot}/T_{suffix}_Atlas_Normal.png"));
            material.SetTexture(
                "_MetallicGlossMap",
                LoadTexture(
                    $"{textureRoot}/T_{suffix}_Atlas_MetallicSmoothness.png"));
            material.EnableKeyword("_NORMALMAP");
            material.EnableKeyword("_METALLICSPECGLOSSMAP");
            material.SetFloat("_Metallic", 1f);
            material.SetFloat("_Smoothness", 1f);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material BuildEmissiveMaterial(
            string materialRoot,
            string textureRoot,
            string suffix,
            Color emissionColor)
        {
            var material = LoadOrCreateMaterial(
                $"{materialRoot}/MAT_{suffix}_Emissive.mat");
            material.SetTexture(
                "_BaseMap",
                LoadTexture($"{textureRoot}/T_{suffix}_Atlas_BaseColor.png"));
            material.SetTexture(
                "_EmissionMap",
                LoadTexture($"{textureRoot}/T_{suffix}_Atlas_Emission.png"));
            material.SetColor("_EmissionColor", emissionColor * 1.5f);
            material.EnableKeyword("_EMISSION");
            EditorUtility.SetDirty(material);
            return material;
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
                manifest.Configure(
                    motionTarget,
                    key == "Lamp" ? motionTarget.GetComponent<Renderer>() : null);

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
