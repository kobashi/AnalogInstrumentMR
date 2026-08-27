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
                if (!File.Exists(activeModel))
                    throw new FileNotFoundException("Active model missing", activeModel);
                if (!File.Exists(activePrefab))
                    throw new FileNotFoundException("Active prefab missing", activePrefab);
                assets.Add(
                    new PromotionAsset(
                        entry,
                        stagedModel,
                        activeModel,
                        activePrefab));
            }
            return assets;
        }

        private static void BackupAll(
            IEnumerable<PromotionAsset> assets,
            string backupRoot)
        {
            foreach (var asset in assets)
            {
                Backup(asset.ActiveModel, backupRoot);
                Backup(asset.ActivePrefab, backupRoot);
                Backup(asset.ActiveModel + ".meta", backupRoot);
                Backup(asset.ActivePrefab + ".meta", backupRoot);
            }
        }

        private static void RestoreAll(
            IEnumerable<PromotionAsset> assets,
            string backupRoot)
        {
            foreach (var asset in assets)
            {
                Restore(asset.ActiveModel, backupRoot);
                Restore(asset.ActivePrefab, backupRoot);
                Restore(asset.ActiveModel + ".meta", backupRoot);
                Restore(asset.ActivePrefab + ".meta", backupRoot);
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
                string activePrefab)
            {
                Entry = entry;
                StagedModel = stagedModel;
                ActiveModel = activeModel;
                ActivePrefab = activePrefab;
            }

            public CandidateStagingEntry Entry { get; }
            public string StagedModel { get; }
            public string ActiveModel { get; }
            public string ActivePrefab { get; }
        }
    }
}
