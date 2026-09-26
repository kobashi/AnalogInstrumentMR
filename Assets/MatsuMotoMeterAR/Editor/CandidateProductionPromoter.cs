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
    internal static class CandidateProductionPromoter
    {
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/CandidateStaging";

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Promote Selected Gate C Candidate to Production")]
        public static void PromoteSelected()
        {
            Promote(CandidateStagingManifest.SelectedAssetPath());
        }

        internal static void Promote(string manifestPath)
        {
            var manifest = CandidateStagingManifest.Load(manifestPath);
            var checks = CandidateGateCReadiness.Evaluate(manifest, File.Exists);
            var failures = checks.Where(check => !check.Passed).ToArray();
            if (failures.Length > 0)
            {
                throw new InvalidOperationException(
                    $"Candidate {manifest.candidateId} is not Gate C ready:\n" +
                    string.Join(
                        "\n",
                        failures.Select(check => $"{check.Id}: {check.Detail}")));
            }

            var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            var backupRoot =
                $"Builds/ModelReplacementBackups/" +
                $"{manifest.candidateId}_{timestamp}";
            var assets = ResolveAssets(manifest);
            BackupAll(assets, backupRoot);

            try
            {
                foreach (var asset in assets)
                {
                    Directory.CreateDirectory(
                        Path.GetDirectoryName(asset.ActiveModel));
                    File.Copy(asset.StagedModel, asset.ActiveModel, true);
                    AssetDatabase.ImportAsset(
                        asset.ActiveModel,
                        ImportAssetOptions.ForceSynchronousImport |
                        ImportAssetOptions.ForceUpdate);
                    if (IsAudioModule(asset.Entry.model))
                    {
                        OrbitalAnalogUnityAssetBuilder.RebuildAudioModule(
                            asset.Entry.theme,
                            asset.Entry.model);
                    }
                    else if (asset.Entry.theme == "Superfine")
                    {
                        RebuildSuperfineNonAudio(asset);
                    }
                    else
                    {
                        OrbitalAnalogUnityAssetBuilder.RebuildModel(
                            asset.Entry.theme,
                            asset.Entry.model);
                    }
                }

                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                RejectCandidateDependencies(assets);
                foreach (var asset in assets)
                    RefinedModelReplacementValidator.ValidateActivePrefab(
                        asset.Entry);
                WriteReport(manifest, assets, backupRoot);
                Debug.Log(
                    $"Candidate {manifest.candidateId} production promotion " +
                    $"PASS. Backup: {backupRoot}");
            }
            catch
            {
                RestoreAll(assets, backupRoot);
                throw;
            }
        }

        private static List<PromotionAsset> ResolveAssets(
            CandidateStagingManifest manifest)
        {
            var assets = new List<PromotionAsset>();
            foreach (var entry in manifest.entries)
            {
                var stagedModel =
                    $"{CandidateRoot}/{manifest.candidateId}/Models/" +
                    $"{entry.theme}/SM_{entry.model}_{entry.theme}_V6_Material.fbx";
                var activeModel =
                    $"Assets/MatsuMotoMeterAR/Content/Themes/{entry.theme}/" +
                    $"Models/SM_{entry.model}_{entry.theme}.fbx";
                var activePrefab =
                    $"Assets/MatsuMotoMeterAR/Resources/{entry.theme}/Prefabs/" +
                    $"PF_Visual_{entry.model}_{entry.theme}.prefab";
                var stagedPrefab = manifest.CandidatePrefabPath(entry);
                if (!File.Exists(stagedModel))
                    throw new FileNotFoundException("Staged model missing", stagedModel);
                if (!File.Exists(stagedPrefab))
                    throw new FileNotFoundException("Staged prefab missing", stagedPrefab);
                var activeModelExists = File.Exists(activeModel);
                var activePrefabExists = File.Exists(activePrefab);
                var initialRegistration =
                    (entry.model == "TrendMonitor" ||
                     IsAudioModule(entry.model)) &&
                    !activeModelExists &&
                    !activePrefabExists;
                if (!initialRegistration && !activeModelExists)
                    throw new FileNotFoundException("Active model missing", activeModel);
                if (!initialRegistration && !activePrefabExists)
                    throw new FileNotFoundException("Active prefab missing", activePrefab);
                if (activeModelExists != activePrefabExists)
                {
                    throw new InvalidDataException(
                        $"Active model/prefab presence differs for " +
                        $"{entry.theme}/{entry.model}.");
                }
                var materialRoot =
                    $"Assets/MatsuMotoMeterAR/Content/Themes/{entry.theme}/" +
                    "Materials";
                var managedMaterials = entry.model == "TrendMonitor"
                    ? new[]
                    {
                        $"{materialRoot}/" +
                        $"MAT_{entry.theme}_V6_TrendMonitor_Opaque.mat",
                        $"{materialRoot}/" +
                        $"MAT_{entry.theme}_V6_TrendMonitor_Readout.mat"
                    }
                    : IsAudioModule(entry.model)
                        ? new[]
                        {
                            $"{materialRoot}/" +
                            $"MAT_{entry.theme}_AudioModule_Housing.mat",
                            $"{materialRoot}/" +
                            $"MAT_{entry.theme}_AudioModule_FaceMetal.mat",
                            $"{materialRoot}/" +
                            $"MAT_{entry.theme}_AudioModule_EmissionDisplay.mat"
                        }
                        : Array.Empty<string>();
                assets.Add(
                    new PromotionAsset(
                        entry,
                        stagedModel,
                        stagedPrefab,
                        activeModel,
                        activePrefab,
                        managedMaterials));
            }
            return assets;
        }

        private static void RebuildSuperfineNonAudio(PromotionAsset asset)
        {
            var productionMeshes = AssetDatabase
                .LoadAllAssetsAtPath(asset.ActiveModel)
                .OfType<Mesh>()
                .GroupBy(mesh => mesh.name, StringComparer.Ordinal)
                .ToDictionary(
                    group => group.Key,
                    group => group.First(),
                    StringComparer.Ordinal);
            var candidatePrefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                asset.StagedPrefab);
            var root = PrefabUtility.InstantiatePrefab(candidatePrefab) as GameObject;
            if (root == null)
            {
                throw new InvalidDataException(
                    $"Could not instantiate candidate prefab: {asset.StagedPrefab}");
            }

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
                            $"{asset.Entry.model}: production mesh missing for " +
                            filter.sharedMesh.name);
                    }
                    filter.sharedMesh = replacement;
                }

                foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
                {
                    var assigned = renderer.sharedMaterials;
                    for (var index = 0; index < assigned.Length; index++)
                    {
                        assigned[index] = ResolveSuperfineNonAudioMaterial(
                            assigned[index]);
                    }
                    renderer.sharedMaterials = assigned;
                }

                root.name = $"PF_Visual_{asset.Entry.model}_Superfine";
                PrefabUtility.SaveAsPrefabAsset(root, asset.ActivePrefab);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
            AssetDatabase.ImportAsset(
                asset.ActivePrefab,
                ImportAssetOptions.ForceSynchronousImport |
                ImportAssetOptions.ForceUpdate);
        }

        private static Material ResolveSuperfineNonAudioMaterial(Material source)
        {
            if (source == null)
                throw new InvalidDataException("Candidate renderer material is null.");
            foreach (var role in new[]
                     {
                         "Housing", "FaceMetal", "EmissionDisplay", "Glass"
                     })
            {
                if (!source.name.Contains(role, StringComparison.Ordinal))
                    continue;
                var path =
                    "Assets/MatsuMotoMeterAR/Content/Themes/Superfine/" +
                    $"Materials/MAT_Superfine_NonAudio_{role}.mat";
                var material = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (material == null)
                    throw new FileNotFoundException("Production material missing", path);
                return material;
            }
            throw new InvalidDataException(
                $"Unmapped Superfine material: {source.name}.");
        }

        private static void BackupAll(
            IEnumerable<PromotionAsset> assets,
            string backupRoot)
        {
            // Keep an auditable rollback location even when every promoted asset
            // is an initial registration and therefore has no prior files.
            Directory.CreateDirectory(backupRoot);
            foreach (var asset in assets)
            {
                for (var index = 0; index < asset.ManagedPaths.Length; index++)
                {
                    if (asset.ManagedPathExisted[index])
                        Backup(asset.ManagedPaths[index], backupRoot);
                }
            }
        }

        private static void RestoreAll(
            IEnumerable<PromotionAsset> assets,
            string backupRoot)
        {
            foreach (var asset in assets)
            {
                for (var index = 0; index < asset.ManagedPaths.Length; index++)
                {
                    if (asset.ManagedPathExisted[index])
                        Restore(asset.ManagedPaths[index], backupRoot);
                    else
                        DeleteIfCreated(asset.ManagedPaths[index]);
                }
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        private static void Backup(string path, string backupRoot)
        {
            if (!File.Exists(path))
                throw new FileNotFoundException("Promotion backup source missing", path);
            var destination = Path.Combine(backupRoot, path);
            Directory.CreateDirectory(Path.GetDirectoryName(destination));
            File.Copy(path, destination, true);
        }

        private static void Restore(string path, string backupRoot)
        {
            var source = Path.Combine(backupRoot, path);
            if (!File.Exists(source))
                throw new FileNotFoundException("Promotion backup missing", source);
            File.Copy(source, path, true);
        }

        private static void DeleteIfCreated(string path)
        {
            if (File.Exists(path))
                File.Delete(path);
        }

        private static void RejectCandidateDependencies(
            IEnumerable<PromotionAsset> assets)
        {
            foreach (var asset in assets)
            {
                var forbidden = AssetDatabase.GetDependencies(
                        asset.ActivePrefab,
                        true)
                    .FirstOrDefault(path => path.Contains(
                        "/CandidateStaging/",
                        StringComparison.Ordinal));
                if (forbidden != null)
                {
                    throw new InvalidDataException(
                        $"{asset.ActivePrefab}: candidate dependency remains: " +
                        forbidden);
                }
            }
        }

        private static void WriteReport(
            CandidateStagingManifest manifest,
            IEnumerable<PromotionAsset> assets,
            string backupRoot)
        {
            var report = new StringBuilder();
            report.AppendLine($"# Candidate {manifest.candidateId} production promotion");
            report.AppendLine();
            report.AppendLine("Result: **APPLIED**");
            report.AppendLine();
            report.AppendLine($"Backup: `{backupRoot}`");
            report.AppendLine();
            report.AppendLine("| Asset | SHA-256 after promotion |");
            report.AppendLine("| --- | --- |");
            foreach (var asset in assets)
            {
                report.AppendLine(
                    $"| `{asset.ActiveModel}` | `{Digest(asset.ActiveModel)}` |");
                report.AppendLine(
                    $"| `{asset.ActivePrefab}` | `{Digest(asset.ActivePrefab)}` |");
                foreach (var material in asset.ManagedMaterials)
                {
                    report.AppendLine(
                        $"| `{material}` | `{Digest(material)}` |");
                }
            }
            report.AppendLine();
            report.AppendLine("- Candidate dependencies: 0");
            report.AppendLine("- Active prefab validation: PASS");
            var reportPath =
                $"Builds/Reports/candidate-{manifest.candidateId}-" +
                "production-promotion.md";
            Directory.CreateDirectory(Path.GetDirectoryName(reportPath));
            File.WriteAllText(reportPath, report.ToString());
        }

        private static string Digest(string path)
        {
            using var stream = File.OpenRead(path);
            using var sha = SHA256.Create();
            return string.Concat(
                sha.ComputeHash(stream).Select(value => value.ToString("x2")));
        }

        internal static bool IsAudioModule(string model)
        {
            return model == "AudioOscillator" ||
                   model == "AudioNoise" ||
                   model == "AudioLFO" ||
                   model == "AudioSequencer" ||
                   model == "AudioDelay" ||
                   model == "AudioOutput" ||
                   model == "AudioVca" ||
                   model == "AudioMixer" ||
                   model == "AudioFilter" ||
                   model == "AudioEnvelope";
        }

        private readonly struct PromotionAsset
        {
            public PromotionAsset(
                CandidateStagingEntry entry,
                string stagedModel,
                string stagedPrefab,
                string activeModel,
                string activePrefab,
                string[] managedMaterials)
            {
                Entry = entry;
                StagedModel = stagedModel;
                StagedPrefab = stagedPrefab;
                ActiveModel = activeModel;
                ActivePrefab = activePrefab;
                ManagedMaterials = managedMaterials ?? Array.Empty<string>();
                ManagedPaths = new[]
                    {
                        activeModel,
                        activeModel + ".meta",
                        activePrefab,
                        activePrefab + ".meta"
                    }
                    .Concat(
                        ManagedMaterials.SelectMany(
                            path => new[] { path, path + ".meta" }))
                    .ToArray();
                ManagedPathExisted = ManagedPaths
                    .Select(File.Exists)
                    .ToArray();
            }

            public CandidateStagingEntry Entry { get; }
            public string StagedModel { get; }
            public string StagedPrefab { get; }
            public string ActiveModel { get; }
            public string ActivePrefab { get; }
            public string[] ManagedMaterials { get; }
            public string[] ManagedPaths { get; }
            public bool[] ManagedPathExisted { get; }
        }
    }
}
