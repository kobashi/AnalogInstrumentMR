using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class SuperfineProductionPromoter
    {
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging";
        private const string ManifestRoot =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests";
        private const string ProductionContentRoot =
            "Assets/MatsuMotoMeterAR/Content/Themes/Superfine";
        private const string ProductionModelRoot =
            ProductionContentRoot + "/Models";
        private const string ProductionMaterialRoot =
            ProductionContentRoot + "/Materials";
        private const string ProductionPrefabRoot =
            "Assets/MatsuMotoMeterAR/Resources/Superfine/Prefabs";
        private const string ReportPath =
            "Builds/Reports/superfine-production-promotion.md";

        private static readonly string[] ManifestPaths =
        {
            $"{ManifestRoot}/AudioModules_Superfine_C2.json",
            $"{ManifestRoot}/AudioModules_Superfine_C3.json",
            $"{ManifestRoot}/Superfine_NonAudio_C4.json"
        };

        private static readonly MaterialSpec[] Materials =
        {
            new(
                "AudioModule_Housing",
                "AudioModules_Superfine_C2",
                "MAT_Superfine_AudioModule_Housing_Staging.mat",
                "MAT_Superfine_AudioModule_Housing.mat"),
            new(
                "AudioModule_FaceMetal",
                "AudioModules_Superfine_C2",
                "MAT_Superfine_AudioModule_FaceMetal_Staging.mat",
                "MAT_Superfine_AudioModule_FaceMetal.mat"),
            new(
                "AudioModule_EmissionDisplay",
                "AudioModules_Superfine_C2",
                "MAT_Superfine_AudioModule_EmissionDisplay_Staging.mat",
                "MAT_Superfine_AudioModule_EmissionDisplay.mat"),
            new(
                "NonAudio_Housing",
                "Superfine_NonAudio_C4",
                "MAT_Superfine_NonAudio_Housing_Staging.mat",
                "MAT_Superfine_NonAudio_Housing.mat"),
            new(
                "NonAudio_FaceMetal",
                "Superfine_NonAudio_C4",
                "MAT_Superfine_NonAudio_FaceMetal_Staging.mat",
                "MAT_Superfine_NonAudio_FaceMetal.mat"),
            new(
                "NonAudio_EmissionDisplay",
                "Superfine_NonAudio_C4",
                "MAT_Superfine_NonAudio_EmissionDisplay_Staging.mat",
                "MAT_Superfine_NonAudio_EmissionDisplay.mat"),
            new(
                "NonAudio_Glass",
                "Superfine_NonAudio_C4",
                "MAT_Superfine_NonAudio_Glass_Staging.mat",
                "MAT_Superfine_NonAudio_Glass.mat")
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Superfine/" +
            "Promote 24 Models to Production")]
        public static void Promote()
        {
            var entries = LoadEntries();
            Preflight(entries);
            var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            var backupRoot =
                $"Builds/ModelReplacementBackups/Superfine_P_{timestamp}";
            Directory.CreateDirectory(backupRoot);
            File.WriteAllText(
                Path.Combine(backupRoot, "README.md"),
                "# Superfine initial registration rollback\n\n" +
                "No previous Superfine production assets existed. Remove only " +
                "the newly created Superfine production roots and revert the " +
                "theme-registration code changes to roll back.\n");

            try
            {
                CreateProductionFolders();
                var productionMaterials = CopyMaterials();
                foreach (var entry in entries)
                    PromoteEntry(entry, productionMaterials);

                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                ValidateProduction(entries);
                WriteReport(entries, backupRoot);
            }
            catch
            {
                RollbackCreatedAssets();
                throw;
            }

            Debug.Log(
                "Superfine 24-model production promotion: PASS. " +
                $"Report: {ReportPath}");
        }

        private static List<PromotionEntry> LoadEntries()
        {
            var result = new List<PromotionEntry>();
            foreach (var manifestPath in ManifestPaths)
            {
                var manifest = CandidateStagingManifest.Load(manifestPath);
                foreach (var entry in manifest.entries)
                {
                    result.Add(
                        new PromotionEntry(
                            manifest.candidateId,
                            entry.model));
                }
            }
            return result;
        }

        private static void Preflight(IReadOnlyCollection<PromotionEntry> entries)
        {
            if (entries.Count != 24 ||
                entries.Select(entry => entry.Model).Distinct().Count() != 24)
            {
                throw new InvalidDataException(
                    "Superfine production promotion requires 24 unique models.");
            }
            if (AssetDatabase.IsValidFolder(ProductionContentRoot) ||
                AssetDatabase.IsValidFolder("Assets/MatsuMotoMeterAR/Resources/Superfine"))
            {
                throw new InvalidOperationException(
                    "Superfine production roots already exist; initial " +
                    "registration refuses to overwrite them.");
            }

            foreach (var entry in entries)
            {
                RequireAsset(entry.CandidateModel);
                RequireAsset(entry.CandidatePrefab);
            }
            foreach (var material in Materials)
                RequireAsset(material.SourcePath);
        }

        private static void CreateProductionFolders()
        {
            EnsureFolder("Assets/MatsuMotoMeterAR/Content/Themes", "Superfine");
            EnsureFolder(ProductionContentRoot, "Models");
            EnsureFolder(ProductionContentRoot, "Materials");
            EnsureFolder("Assets/MatsuMotoMeterAR/Resources", "Superfine");
            EnsureFolder("Assets/MatsuMotoMeterAR/Resources/Superfine", "Prefabs");
        }

        private static Dictionary<string, Material> CopyMaterials()
        {
            var result = new Dictionary<string, Material>(StringComparer.Ordinal);
            foreach (var spec in Materials)
            {
                var destination =
                    $"{ProductionMaterialRoot}/{spec.DestinationFile}";
                CopyWithFreshGuid(spec.SourcePath, destination);
                var material = AssetDatabase.LoadAssetAtPath<Material>(destination);
                if (material == null)
                    throw new InvalidDataException($"Material copy failed: {destination}");
                material.name = Path.GetFileNameWithoutExtension(spec.DestinationFile);
                EditorUtility.SetDirty(material);
                result.Add(spec.Key, material);
            }
            AssetDatabase.SaveAssets();
            return result;
        }

        private static void PromoteEntry(
            PromotionEntry entry,
            IReadOnlyDictionary<string, Material> materials)
        {
            CopyWithFreshGuid(entry.CandidateModel, entry.ProductionModel);
            AssetDatabase.ImportAsset(
                entry.ProductionModel,
                ImportAssetOptions.ForceSynchronousImport |
                ImportAssetOptions.ForceUpdate);

            var productionMeshes = AssetDatabase
                .LoadAllAssetsAtPath(entry.ProductionModel)
                .OfType<Mesh>()
                .GroupBy(mesh => mesh.name, StringComparer.Ordinal)
                .ToDictionary(group => group.Key, group => group.First(),
                    StringComparer.Ordinal);
            var candidatePrefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                entry.CandidatePrefab);
            var root = PrefabUtility.InstantiatePrefab(candidatePrefab) as GameObject;
            if (root == null)
                throw new InvalidDataException(
                    $"Could not instantiate candidate prefab: {entry.CandidatePrefab}");
            try
            {
                PrefabUtility.UnpackPrefabInstance(
                    root,
                    PrefabUnpackMode.Completely,
                    InteractionMode.AutomatedAction);
                foreach (var filter in root.GetComponentsInChildren<MeshFilter>(true))
                {
                    if (filter.sharedMesh == null)
                        continue;
                    if (!productionMeshes.TryGetValue(
                            filter.sharedMesh.name,
                            out var replacement))
                    {
                        throw new InvalidDataException(
                            $"{entry.Model}: production mesh missing for " +
                            filter.sharedMesh.name);
                    }
                    filter.sharedMesh = replacement;
                }

                foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
                {
                    var assigned = renderer.sharedMaterials;
                    for (var index = 0; index < assigned.Length; index++)
                        assigned[index] = ResolveMaterial(assigned[index], materials);
                    renderer.sharedMaterials = assigned;
                }

                root.name = $"PF_Visual_{entry.Model}_Superfine";
                PrefabUtility.SaveAsPrefabAsset(root, entry.ProductionPrefab);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
            AssetDatabase.ImportAsset(
                entry.ProductionPrefab,
                ImportAssetOptions.ForceSynchronousImport |
                ImportAssetOptions.ForceUpdate);
            RequireFreshGuid(entry.CandidatePrefab, entry.ProductionPrefab);
        }

        private static Material ResolveMaterial(
            Material source,
            IReadOnlyDictionary<string, Material> materials)
        {
            if (source == null)
                throw new InvalidDataException("Candidate renderer material is null.");
            foreach (var item in materials)
            {
                if (source.name.Contains(item.Key, StringComparison.Ordinal))
                    return item.Value;
            }
            throw new InvalidDataException(
                $"Unmapped Superfine material: {source.name}.");
        }

        private static void ValidateProduction(
            IReadOnlyCollection<PromotionEntry> entries)
        {
            foreach (var entry in entries)
            {
                RequireAsset(entry.ProductionModel);
                RequireAsset(entry.ProductionPrefab);
                RequireFreshGuid(entry.CandidateModel, entry.ProductionModel);
                RequireFreshGuid(entry.CandidatePrefab, entry.ProductionPrefab);

                var forbidden = AssetDatabase
                    .GetDependencies(entry.ProductionPrefab, true)
                    .FirstOrDefault(path => path.Contains(
                        "/CandidateStaging/",
                        StringComparison.Ordinal));
                if (forbidden != null)
                {
                    throw new InvalidDataException(
                        $"{entry.ProductionPrefab}: candidate dependency " +
                        $"remains: {forbidden}");
                }
            }
            foreach (var spec in Materials)
                RequireFreshGuid(spec.SourcePath, spec.DestinationPath);

            RefinedModelReplacementValidator.ValidateSuperfineActivePrefabs();
        }

        private static void WriteReport(
            IEnumerable<PromotionEntry> entries,
            string backupRoot)
        {
            var report = new StringBuilder();
            report.AppendLine("# Superfine production promotion");
            report.AppendLine();
            report.AppendLine("Result: **APPLIED**");
            report.AppendLine();
            report.AppendLine($"Rollback record: `{backupRoot}`");
            report.AppendLine();
            report.AppendLine("| Asset | SHA-256 |");
            report.AppendLine("| --- | --- |");
            foreach (var spec in Materials)
            {
                report.AppendLine(
                    $"| `{spec.DestinationPath}` | " +
                    $"`{Digest(spec.DestinationPath)}` |");
            }
            foreach (var entry in entries.OrderBy(item => item.Model))
            {
                report.AppendLine(
                    $"| `{entry.ProductionModel}` | " +
                    $"`{Digest(entry.ProductionModel)}` |");
                report.AppendLine(
                    $"| `{entry.ProductionPrefab}` | " +
                    $"`{Digest(entry.ProductionPrefab)}` |");
            }
            report.AppendLine();
            report.AppendLine("- Production models: 24");
            report.AppendLine("- Production prefabs: 24");
            report.AppendLine("- Canonical materials: 7");
            report.AppendLine("- Candidate dependencies: 0");
            report.AppendLine("- Fresh GUID checks: PASS");
            report.AppendLine("- Active prefab validation: PASS (REVIEW retained)");
            Directory.CreateDirectory(Path.GetDirectoryName(ReportPath));
            File.WriteAllText(ReportPath, report.ToString());
            AssetDatabase.Refresh();
        }

        private static void RollbackCreatedAssets()
        {
            if (AssetDatabase.IsValidFolder(
                    "Assets/MatsuMotoMeterAR/Resources/Superfine"))
            {
                AssetDatabase.DeleteAsset(
                    "Assets/MatsuMotoMeterAR/Resources/Superfine");
            }
            if (AssetDatabase.IsValidFolder(ProductionContentRoot))
                AssetDatabase.DeleteAsset(ProductionContentRoot);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        private static void CopyWithFreshGuid(string source, string destination)
        {
            if (!AssetDatabase.CopyAsset(source, destination))
            {
                throw new IOException(
                    $"Could not copy asset: {source} -> {destination}");
            }
            AssetDatabase.ImportAsset(
                destination,
                ImportAssetOptions.ForceSynchronousImport |
                ImportAssetOptions.ForceUpdate);
            RequireFreshGuid(source, destination);
        }

        private static void RequireFreshGuid(string source, string destination)
        {
            var sourceGuid = AssetDatabase.AssetPathToGUID(source);
            var destinationGuid = AssetDatabase.AssetPathToGUID(destination);
            if (string.IsNullOrEmpty(sourceGuid) ||
                string.IsNullOrEmpty(destinationGuid) ||
                sourceGuid == destinationGuid)
            {
                throw new InvalidDataException(
                    $"Fresh GUID requirement failed: {source} -> {destination}");
            }
        }

        private static void RequireAsset(string path)
        {
            if (string.IsNullOrWhiteSpace(path) ||
                AssetDatabase.LoadMainAssetAtPath(path) == null)
            {
                throw new FileNotFoundException("Required asset missing", path);
            }
        }

        private static void EnsureFolder(string parent, string child)
        {
            var path = $"{parent}/{child}";
            if (!AssetDatabase.IsValidFolder(path))
                AssetDatabase.CreateFolder(parent, child);
        }

        private static string Digest(string path)
        {
            using var stream = File.OpenRead(path);
            using var sha = SHA256.Create();
            return string.Concat(
                sha.ComputeHash(stream).Select(value => value.ToString("x2")));
        }

        private readonly struct PromotionEntry
        {
            public PromotionEntry(string candidateId, string model)
            {
                CandidateId = candidateId;
                Model = model;
            }

            public string CandidateId { get; }
            public string Model { get; }
            public string CandidateModel =>
                $"{CandidateRoot}/{CandidateId}/Models/Superfine/" +
                $"SM_{Model}_Superfine_V6_Material.fbx";
            public string CandidatePrefab =>
                $"{CandidateRoot}/{CandidateId}/Resources/{CandidateId}/" +
                $"Superfine/Prefabs/PF_Visual_{Model}_Superfine.prefab";
            public string ProductionModel =>
                $"{ProductionModelRoot}/SM_{Model}_Superfine.fbx";
            public string ProductionPrefab =>
                $"{ProductionPrefabRoot}/PF_Visual_{Model}_Superfine.prefab";
        }

        private readonly struct MaterialSpec
        {
            public MaterialSpec(
                string key,
                string candidateId,
                string sourceFile,
                string destinationFile)
            {
                Key = key;
                CandidateId = candidateId;
                SourceFile = sourceFile;
                DestinationFile = destinationFile;
            }

            public string Key { get; }
            public string CandidateId { get; }
            public string SourceFile { get; }
            public string DestinationFile { get; }
            public string SourcePath =>
                $"{CandidateRoot}/{CandidateId}/Resources/{CandidateId}/" +
                $"Superfine/Materials/{SourceFile}";
            public string DestinationPath =>
                $"{ProductionMaterialRoot}/{DestinationFile}";
        }
    }
}
