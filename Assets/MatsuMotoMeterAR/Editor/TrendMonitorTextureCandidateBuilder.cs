using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class TrendMonitorTextureCandidateBuilder
    {
        private const string CandidateId = "TrendMonitor_Texture_T1";
        private const string Root =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging/TrendMonitor_Texture_T1";
        private static readonly string[] Themes =
        {
            "OrbitalAnalog", "ForgeBrass", "KineticSafety"
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Trend Monitor Texture T1 Candidate")]
        public static void Build()
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var report = new StringBuilder();
            report.AppendLine("# TrendMonitor Texture T1 staging");
            report.AppendLine();
            report.AppendLine("| Theme | Renderers | Materials | Candidate dependency | Result |");
            report.AppendLine("| --- | ---: | ---: | --- | --- |");
            foreach (var theme in Themes)
            {
                ConfigureTextures(theme);
                var materials = BuildMaterials(theme);
                var prefabPath = BuildPrefab(theme, materials);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                var renderers = prefab.GetComponentsInChildren<Renderer>(true);
                var materialCount = renderers
                    .SelectMany(renderer => renderer.sharedMaterials)
                    .Where(material => material != null)
                    .Distinct()
                    .Count();
                if (renderers.Length != 3 || materialCount != 3)
                {
                    throw new InvalidDataException(
                        $"{theme}: expected 3 renderers and 3 materials; " +
                        $"got {renderers.Length} and {materialCount}.");
                }
                var forbidden = AssetDatabase.GetDependencies(prefabPath, true)
                    .FirstOrDefault(path => path.Contains(
                        "/CandidateStaging/TrendMonitor_ThemeShapes_T1/",
                        StringComparison.Ordinal));
                if (forbidden != null)
                    throw new InvalidDataException(
                        $"{theme}: obsolete candidate dependency: {forbidden}");
                report.AppendLine(
                    $"| {theme} | 3 | 3 | production geometry only | PASS |");
            }
            report.AppendLine();
            report.AppendLine("- Housing: 1K BaseColor / Normal / MetallicSmoothness");
            report.AppendLine("- Readout: unchanged solid emissive role");
            report.AppendLine("- Display: dedicated dark untextured role");
            report.AppendLine("- Production assets modified: no");
            Directory.CreateDirectory("Builds/Reports");
            File.WriteAllText(
                $"Builds/Reports/candidate-{CandidateId}-staging.md",
                report.ToString());
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            Debug.Log($"{CandidateId} staging build PASS.");
        }

        private static void ConfigureTextures(string theme)
        {
            var prefix = $"{Root}/Textures/{theme}/" +
                         $"T_{theme}_V6_TrendMonitor_T1";
            ConfigureTexture(prefix + "_BaseColor.png", false, true);
            ConfigureTexture(prefix + "_Normal.png", true, false);
            ConfigureTexture(
                prefix + "_MetallicSmoothness.png", false, false);
        }

        private static void ConfigureTexture(
            string path,
            bool normal,
            bool sRgb)
        {
            if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
                throw new FileNotFoundException("Texture importer missing", path);
            importer.textureType = normal
                ? TextureImporterType.NormalMap
                : TextureImporterType.Default;
            importer.sRGBTexture = sRgb && !normal;
            importer.wrapMode = TextureWrapMode.Repeat;
            importer.mipmapEnabled = true;
            importer.maxTextureSize = 1024;
            importer.textureCompression = TextureImporterCompression.Compressed;
            importer.SaveAndReimport();
        }

        private static CandidateMaterials BuildMaterials(string theme)
        {
            var materialRoot =
                $"{Root}/Resources/{CandidateId}/{theme}/Materials";
            Directory.CreateDirectory(materialRoot);
            var texturePrefix = $"{Root}/Textures/{theme}/" +
                                $"T_{theme}_V6_TrendMonitor_T1";
            var housing = LoadOrCreate(
                $"{materialRoot}/MAT_{theme}_TrendMonitor_Housing_T1.mat");
            housing.color = Color.white;
            housing.SetColor("_BaseColor", Color.white);
            housing.SetTexture(
                "_BaseMap",
                LoadTexture(texturePrefix + "_BaseColor.png"));
            housing.SetTexture(
                "_BumpMap",
                LoadTexture(texturePrefix + "_Normal.png"));
            housing.SetTexture(
                "_MetallicGlossMap",
                LoadTexture(texturePrefix + "_MetallicSmoothness.png"));
            housing.SetFloat("_BumpScale", 0.34f);
            housing.SetFloat("_Metallic", 1f);
            housing.SetFloat("_Smoothness", 1f);
            housing.EnableKeyword("_NORMALMAP");
            housing.EnableKeyword("_METALLICSPECGLOSSMAP");
            housing.DisableKeyword("_EMISSION");
            housing.SetColor("_EmissionColor", Color.black);
            EditorUtility.SetDirty(housing);

            var readout = LoadOrCreate(
                $"{materialRoot}/MAT_{theme}_TrendMonitor_Readout_T1.mat");
            var readoutColor = theme switch
            {
                "OrbitalAnalog" => new Color(0.02f, 0.42f, 0.50f, 1f),
                "ForgeBrass" => new Color(0.58f, 0.31f, 0.035f, 1f),
                _ => new Color(0.62f, 0.25f, 0.025f, 1f)
            };
            ClearMaps(readout);
            readout.color = readoutColor;
            readout.SetColor("_BaseColor", readoutColor);
            readout.SetFloat("_Metallic", 0.05f);
            readout.SetFloat("_Smoothness", 0.34f);
            readout.SetColor("_EmissionColor", readoutColor * 3.2f);
            readout.EnableKeyword("_EMISSION");
            EditorUtility.SetDirty(readout);

            var display = LoadOrCreate(
                $"{materialRoot}/MAT_{theme}_TrendMonitor_Display_T1.mat");
            var displayColor = new Color(0.012f, 0.020f, 0.028f, 1f);
            ClearMaps(display);
            display.color = displayColor;
            display.SetColor("_BaseColor", displayColor);
            display.SetFloat("_Metallic", 0f);
            display.SetFloat("_Smoothness", 0.08f);
            display.SetColor("_EmissionColor", Color.black);
            display.DisableKeyword("_EMISSION");
            EditorUtility.SetDirty(display);
            return new CandidateMaterials(housing, readout, display);
        }

        private static void ClearMaps(Material material)
        {
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
        }

        private static string BuildPrefab(
            string theme,
            CandidateMaterials materials)
        {
            var activePath =
                $"Assets/MatsuMotoMeterAR/Resources/{theme}/Prefabs/" +
                $"PF_Visual_TrendMonitor_{theme}.prefab";
            var active = AssetDatabase.LoadAssetAtPath<GameObject>(activePath);
            if (active == null)
                throw new FileNotFoundException("Active prefab missing", activePath);
            var instance = PrefabUtility.InstantiatePrefab(active) as GameObject;
            if (instance == null)
                throw new InvalidOperationException($"Could not instantiate {activePath}");
            try
            {
                PrefabUtility.UnpackPrefabInstance(
                    instance,
                    PrefabUnpackMode.Completely,
                    InteractionMode.AutomatedAction);
                Assign(instance.transform, "static_opaque", materials.Housing);
                Assign(instance.transform, "static_readout", materials.Readout);
                Assign(instance.transform, "display_surface", materials.Display);
                var prefabRoot =
                    $"{Root}/Resources/{CandidateId}/{theme}/Prefabs";
                Directory.CreateDirectory(prefabRoot);
                var path = $"{prefabRoot}/PF_Visual_TrendMonitor_{theme}.prefab";
                if (PrefabUtility.SaveAsPrefabAsset(instance, path) == null)
                    throw new InvalidOperationException($"Could not save {path}");
                return path;
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static void Assign(
            Transform root,
            string nodeName,
            Material material)
        {
            var node = root.GetComponentsInChildren<Transform>(true)
                .FirstOrDefault(candidate => candidate.name == nodeName);
            var renderer = node?.GetComponent<Renderer>();
            if (renderer == null)
                throw new MissingReferenceException(
                    $"{root.name}: renderer node {nodeName} missing.");
            renderer.sharedMaterials = Enumerable
                .Repeat(material, renderer.sharedMaterials.Length)
                .ToArray();
        }

        private static Texture2D LoadTexture(string path)
        {
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null)
                throw new FileNotFoundException("Texture missing", path);
            return texture;
        }

        private static Material LoadOrCreate(string path)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null)
                throw new InvalidOperationException("URP Lit shader missing.");
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material != null)
            {
                material.shader = shader;
                return material;
            }
            material = new Material(shader);
            AssetDatabase.CreateAsset(material, path);
            return material;
        }

        private readonly struct CandidateMaterials
        {
            public CandidateMaterials(
                Material housing,
                Material readout,
                Material display)
            {
                Housing = housing;
                Readout = readout;
                Display = display;
            }

            public Material Housing { get; }
            public Material Readout { get; }
            public Material Display { get; }
        }
    }
}
