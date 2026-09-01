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
            var manifestPath = CandidateStagingManifest.SelectedAssetPath();
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
                    OrbitalAnalogUnityAssetBuilder.RebuildModel(
                        asset.Entry.theme,
                        asset.Entry.model);
                }

                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                RejectCandidateDependencies(assets);
                RefinedModelReplacementValidator.ValidateActivePrefabs();
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
                if (!File.Exists(stagedModel))
                    throw new FileNotFoundException("Staged model missing", stagedModel);
                var activeModelExists = File.Exists(activeModel);
                var activePrefabExists = File.Exists(activePrefab);
                var initialTrendMonitorRegistration =
                    entry.model == "TrendMonitor" &&
                    !activeModelExists &&
                    !activePrefabExists;
                if (!initialTrendMonitorRegistration && !activeModelExists)
                    throw new FileNotFoundException("Active model missing", activeModel);
                if (!initialTrendMonitorRegistration && !activePrefabExists)
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
                    : Array.Empty<string>();
                assets.Add(
                    new PromotionAsset(
                        entry,
                        stagedModel,
                        activeModel,
                        activePrefab,
                        managedMaterials));
            }
            return assets;
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

        private readonly struct PromotionAsset
        {
            public PromotionAsset(
                CandidateStagingEntry entry,
                string stagedModel,
                string activeModel,
                string activePrefab,
                string[] managedMaterials)
            {
                Entry = entry;
                StagedModel = stagedModel;
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
            public string ActiveModel { get; }
            public string ActivePrefab { get; }
            public string[] ManagedMaterials { get; }
            public string[] ManagedPaths { get; }
            public bool[] ManagedPathExisted { get; }
        }
    }
}
