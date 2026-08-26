using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using MatsuMotoMeterAR.Instruments;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class Theme4ProductionPromoter
    {
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging/Theme4_MachinedErgonomics_14_FullGate";
        private const string ProductionContentRoot =
            "Assets/MatsuMotoMeterAR/Content/Themes/MachinedErgonomics";
        private const string ProductionModelRoot =
            ProductionContentRoot + "/Models";
        private const string ProductionMaterialRoot =
            ProductionContentRoot + "/Materials";
        private const string ProductionTextureRoot =
            ProductionContentRoot + "/Textures";
        private const string ProductionPrefabRoot =
            "Assets/MatsuMotoMeterAR/Resources/MachinedErgonomics/Prefabs";
        private const string ReportPath =
            "Builds/Reports/machined-ergonomics-production-promotion.md";

        private static readonly AssetSpec[] Assets =
        {
            new("MeterRound", "SM_MeterRound_MachinedErgonomics_V6_Opus5_P5.fbx", 4796, 2, 3),
            new("MeterMedium", "SM_MeterMedium_MachinedErgonomics_V6_Opus5_FA_R3.fbx", 2816, 2, 3),
            new("MeterLarge", "SM_MeterLarge_MachinedErgonomics_V6_Opus5_FA_R3.fbx", 3104, 2, 3),
            new("Lever", "SM_Lever_MachinedErgonomics_V6_Opus5_FA_R4.fbx", 6792, 2, 3),
            new("Toggle", "SM_Toggle_MachinedErgonomics_V6_Opus5_FA_R4.fbx", 3540, 2, 3),
            new("Rotary", "SM_Rotary_MachinedErgonomics_V6_Opus5_FA_R3.fbx", 1492, 2, 4),
            new("Button", "SM_Button_MachinedErgonomics_V6_Opus5_FA_R1.fbx", 2008, 2, 3),
            new("Lamp", "SM_Lamp_MachinedErgonomics_V6_Opus5_FA_R1.fbx", 1332, 2, 3),
            new("StatusIndicator", "SM_StatusIndicator_MachinedErgonomics_V6_Opus5_FA_R1.fbx", 1476, 4, 5),
            new("Throttle", "SM_Throttle_MachinedErgonomics_V6_Opus5_R4_B3U_R2.fbx", 4706, 2, 2),
            new("PowerSlider", "SM_PowerSlider_MachinedErgonomics_V6_Opus5_R4_B3U_R2.fbx", 4600, 2, 2),
            new("WindowMeter", "SM_WindowMeter_MachinedErgonomics_V6_Opus5_P6C_R2.fbx", 3124, 2, 3),
            new("WindowPanel", "SM_WindowPanel_MachinedErgonomics_V6_Opus5_P6C_R2.fbx", 2556, 2, 3),
            new("TrendMonitor", "SM_TrendMonitor_MachinedErgonomics_V6_Opus5_P6C.fbx", 1336, 2, 3)
        };

        private static readonly string[] TextureRoles =
        {
            "BaseColor", "Normal", "MetallicSmoothness", "Emission"
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Promote Machined Ergonomics 14 to Production")]
        public static void Promote()
        {
            Theme4BatchBFullGateBuilder.BuildAndValidate();
            CreateDirectories();
            CopyModels();
            CopyTextures();
            CopyMaterials();
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            CopyAndDetachPrefabs();
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateAndReport();
            Debug.Log(
                "Machined Ergonomics production promotion: PASS\n" +
                ReportPath);
        }

        private static void CreateDirectories()
        {
            Directory.CreateDirectory(ProductionModelRoot);
            Directory.CreateDirectory(ProductionMaterialRoot);
            Directory.CreateDirectory(ProductionTextureRoot);
            Directory.CreateDirectory(ProductionPrefabRoot);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        private static void CopyModels()
        {
            foreach (var spec in Assets)
            {
                CopyAsset(
                    $"{CandidateRoot}/Models/{spec.ModelFile}",
                    $"{ProductionModelRoot}/{spec.ModelFile}");
            }
        }

        private static void CopyTextures()
        {
            foreach (var role in TextureRoles)
            {
                var file = $"T_MachinedErgonomics_P4_Atlas_{role}.png";
                CopyAsset(
                    $"{CandidateRoot}/Textures/{file}",
                    $"{ProductionTextureRoot}/{file}");
            }
        }

        private static void CopyMaterials()
        {
            CopyMaterial("Opaque", "MAT_MachinedErgonomics_Opaque");
            CopyMaterial("Emissive", "MAT_MachinedErgonomics_Emissive");
            CopyMaterial(
                "TrendDisplayOpaque",
                "MAT_MachinedErgonomics_TrendDisplayOpaque");

            var opaque = LoadMaterial("MAT_MachinedErgonomics_Opaque");
            opaque.SetTexture("_BaseMap", LoadTexture("BaseColor"));
            opaque.SetTexture("_BumpMap", LoadTexture("Normal"));
            opaque.SetTexture(
                "_MetallicGlossMap", LoadTexture("MetallicSmoothness"));
            EditorUtility.SetDirty(opaque);

            var emissive = LoadMaterial("MAT_MachinedErgonomics_Emissive");
            emissive.SetTexture("_BaseMap", LoadTexture("Emission"));
            EditorUtility.SetDirty(emissive);

            var display = LoadMaterial(
                "MAT_MachinedErgonomics_TrendDisplayOpaque");
            display.SetTexture("_BaseMap", null);
            display.SetColor(
                "_BaseColor", new Color(0.012f, 0.020f, 0.028f, 1f));
            EditorUtility.SetDirty(display);
        }

        private static void CopyMaterial(string candidateSuffix, string name)
        {
            var source =
                $"{CandidateRoot}/Materials/" +
                $"MAT_MachinedErgonomics_Full14_{candidateSuffix}.mat";
            var destination = $"{ProductionMaterialRoot}/{name}.mat";
            CopyAsset(source, destination);
            var material = AssetDatabase.LoadAssetAtPath<Material>(destination);
            if (material == null)
                throw new FileNotFoundException("Copied material missing", destination);
            material.name = name;
            EditorUtility.SetDirty(material);
        }

        private static void CopyAndDetachPrefabs()
        {
            var opaque = LoadMaterial("MAT_MachinedErgonomics_Opaque");
            var emissive = LoadMaterial("MAT_MachinedErgonomics_Emissive");
            var display = LoadMaterial(
                "MAT_MachinedErgonomics_TrendDisplayOpaque");

            foreach (var spec in Assets)
            {
                var source =
                    $"{CandidateRoot}/Prefabs/PF_Visual_{spec.Key}_" +
                    "MachinedErgonomics_Full14.prefab";
                var destination = PrefabPath(spec);
                CopyAsset(source, destination);

                var root = PrefabUtility.LoadPrefabContents(destination);
                try
                {
                    root.name = $"PF_Visual_{spec.Key}_MachinedErgonomics";
                    if (root.transform.childCount != 1)
                        throw new InvalidDataException(
                            spec.Key + ": expected exactly one imported FBX root");
                    var imported = root.transform.GetChild(0).gameObject;
                    if (PrefabUtility.IsPartOfPrefabInstance(imported))
                    {
                        PrefabUtility.UnpackPrefabInstance(
                            imported,
                            PrefabUnpackMode.Completely,
                            InteractionMode.AutomatedAction);
                    }

                    var meshes = AssetDatabase.LoadAllAssetsAtPath(
                            $"{ProductionModelRoot}/{spec.ModelFile}")
                        .OfType<Mesh>()
                        .GroupBy(mesh => mesh.name)
                        .ToDictionary(group => group.Key, group => group.Single());
                    foreach (var filter in root.GetComponentsInChildren<
                                 MeshFilter>(true))
                    {
                        if (filter.sharedMesh == null ||
                            !meshes.TryGetValue(filter.sharedMesh.name, out var mesh))
                        {
                            throw new MissingReferenceException(
                                $"{spec.Key}: production mesh missing for " +
                                filter.sharedMesh?.name);
                        }
                        filter.sharedMesh = mesh;
                    }

                    foreach (var renderer in root.GetComponentsInChildren<
                                 Renderer>(true))
                    {
                        var assigned = renderer.sharedMaterials
                            .Select(material =>
                            {
                                var name = material != null
                                    ? material.name
                                    : string.Empty;
                                if (name.Contains("TrendDisplay"))
                                    return display;
                                return name.Contains("Emissive")
                                    ? emissive
                                    : opaque;
                            })
                            .ToArray();
                        renderer.sharedMaterials = assigned;
                    }

                    if (PrefabUtility.SaveAsPrefabAsset(root, destination) == null)
                        throw new IOException(
                            "Could not save production prefab: " + destination);
                }
                finally
                {
                    PrefabUtility.UnloadPrefabContents(root);
                }
            }
        }

        private static void ValidateAndReport()
        {
            var report = new StringBuilder();
            report.AppendLine("# Machined Ergonomics production promotion");
            report.AppendLine();
            report.AppendLine(
                "| Asset | Triangles | Renderers | Submeshes | " +
                "Manifest | Dependencies | Result |");
            report.AppendLine("|---|---:|---:|---:|---|---|---|");

            foreach (var spec in Assets)
            {
                var path = PrefabPath(spec);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null)
                    throw new FileNotFoundException("Production prefab missing", path);
                var filters = prefab.GetComponentsInChildren<MeshFilter>(true);
                var renderers = prefab.GetComponentsInChildren<Renderer>(true);
                var triangles = filters.Sum(filter =>
                    filter.sharedMesh.triangles.Length / 3);
                var submeshes = filters.Sum(filter =>
                    filter.sharedMesh.subMeshCount);
                var manifest = prefab.GetComponent<ThemeVisualManifest>();
                var dependencies = AssetDatabase.GetDependencies(path, true);
                var forbidden = dependencies.FirstOrDefault(dependency =>
                    dependency.Contains(
                        "CandidateStaging/Theme4_MachinedErgonomics_14_FullGate"));

                if (triangles != spec.Triangles ||
                    renderers.Length != spec.Renderers ||
                    submeshes != spec.Submeshes)
                    throw new InvalidDataException(
                        $"{spec.Key}: production geometry contract mismatch");
                if (manifest == null || manifest.MotionTarget == null)
                    throw new InvalidDataException(
                        $"{spec.Key}: production manifest invalid");
                if (prefab.GetComponentsInChildren<Collider>(true).Length != 0 ||
                    prefab.GetComponentsInChildren<Light>(true).Length != 0 ||
                    prefab.GetComponentsInChildren<Camera>(true).Length != 0 ||
                    prefab.GetComponentsInChildren<Animator>(true).Length != 0)
                    throw new InvalidDataException(
                        $"{spec.Key}: forbidden production component");
                if (forbidden != null)
                    throw new InvalidDataException(
                        $"{spec.Key}: candidate dependency remains: {forbidden}");
                if (renderers.SelectMany(renderer => renderer.sharedMaterials)
                    .Any(material => material == null || material.shader == null ||
                        material.shader.name == "Hidden/InternalErrorShader"))
                    throw new InvalidDataException(
                        $"{spec.Key}: invalid production material");

                report.AppendLine(
                    $"| {spec.Key} | {triangles} | {renderers.Length} | " +
                    $"{submeshes} | PASS | PASS | PASS |");
            }

            var display = LoadMaterial(
                "MAT_MachinedErgonomics_TrendDisplayOpaque");
            if (display.GetColor("_BaseColor").maxColorComponent > 0.05f)
                throw new InvalidDataException(
                    "TrendMonitor production display is not dark neutral");

            report.AppendLine();
            report.AppendLine("- Theme ID: `machined-ergonomics`");
            report.AppendLine("- Production prefabs: 14 / 14");
            report.AppendLine("- Candidate dependencies: 0");
            report.AppendLine("- Existing three theme roots: unchanged");
            report.AppendLine("- Quest production gate: OPEN");
            Directory.CreateDirectory(
                Path.GetDirectoryName(ReportPath) ?? "Builds/Reports");
            File.WriteAllText(ReportPath, report.ToString());
        }

        private static void CopyAsset(string source, string destination)
        {
            if (AssetDatabase.LoadMainAssetAtPath(source) == null)
                throw new FileNotFoundException("Promotion source missing", source);
            if (AssetDatabase.LoadMainAssetAtPath(destination) != null &&
                !AssetDatabase.DeleteAsset(destination))
                throw new IOException(
                    "Could not replace production asset: " + destination);
            if (!AssetDatabase.CopyAsset(source, destination))
                throw new IOException(
                    $"Could not promote asset: {source} -> {destination}");
        }

        private static Material LoadMaterial(string name)
        {
            var path = $"{ProductionMaterialRoot}/{name}.mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
                throw new FileNotFoundException("Production material missing", path);
            return material;
        }

        private static Texture2D LoadTexture(string role)
        {
            var path =
                $"{ProductionTextureRoot}/" +
                $"T_MachinedErgonomics_P4_Atlas_{role}.png";
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null)
                throw new FileNotFoundException("Production texture missing", path);
            return texture;
        }

        private static string PrefabPath(AssetSpec spec)
        {
            return $"{ProductionPrefabRoot}/" +
                   $"PF_Visual_{spec.Key}_MachinedErgonomics.prefab";
        }

        private readonly struct AssetSpec
        {
            public AssetSpec(
                string key,
                string modelFile,
                int triangles,
                int renderers,
                int submeshes)
            {
                Key = key;
                ModelFile = modelFile;
                Triangles = triangles;
                Renderers = renderers;
                Submeshes = submeshes;
            }

            public string Key { get; }
            public string ModelFile { get; }
            public int Triangles { get; }
            public int Renderers { get; }
            public int Submeshes { get; }
        }
    }
}
