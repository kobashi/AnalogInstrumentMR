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
    internal static class TrendMonitorTextureProductionPromoter
    {
        private const string CandidateId = "TrendMonitor_Texture_T1";
        private const string ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "TrendMonitor_Texture_T1.json";
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging/TrendMonitor_Texture_T1";
        private static readonly string[] Themes =
        {
            "OrbitalAnalog", "ForgeBrass", "KineticSafety"
        };
        private static readonly string[] MapRoles =
        {
            "BaseColor", "Normal", "MetallicSmoothness"
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Promote Trend Monitor Texture T1 to Production")]
        public static void Promote()
        {
            var manifest = CandidateStagingManifest.Load(ManifestPath);
            if (manifest.candidateId != CandidateId)
                throw new InvalidOperationException(
                    $"Unexpected candidate manifest at {ManifestPath}.");
            var failures = CandidateGateCReadiness.Evaluate(
                    manifest, File.Exists)
                .Where(check => !check.Passed)
                .ToArray();
            if (failures.Length > 0)
            {
                throw new InvalidOperationException(
                    $"{CandidateId} is not Gate C ready:\n" +
                    string.Join("\n", failures.Select(
                        failure => $"{failure.Id}: {failure.Detail}")));
            }

            var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            var backupRoot =
                $"Builds/ModelReplacementBackups/{CandidateId}_{timestamp}";
            var managed = ResolveManagedPaths();
            Backup(managed, backupRoot);
            try
            {
                CopyTextures();
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                foreach (var theme in Themes)
                    OrbitalAnalogUnityAssetBuilder.RebuildModel(
                        theme, "TrendMonitor");
                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                ValidateProduction();
                RefinedModelReplacementValidator.ValidateActivePrefabs();
                WriteReport(managed, backupRoot);
                Debug.Log(
                    $"{CandidateId} production promotion PASS. " +
                    $"Backup: {backupRoot}");
            }
            catch
            {
                Restore(managed, backupRoot);
                throw;
            }
        }

        private static List<ManagedPath> ResolveManagedPaths()
        {
            var paths = new List<string>();
            foreach (var theme in Themes)
            {
                var textureRoot =
                    $"Assets/MatsuMotoMeterAR/Content/Themes/{theme}/" +
                    "Textures/TrendMonitor";
                paths.AddRange(MapRoles.Select(role =>
                    $"{textureRoot}/T_{theme}_V6_TrendMonitor_T1_{role}.png"));
                var materialRoot =
                    $"Assets/MatsuMotoMeterAR/Content/Themes/{theme}/Materials";
                paths.AddRange(new[]
                {
                    $"{materialRoot}/MAT_{theme}_V6_TrendMonitor_Opaque.mat",
                    $"{materialRoot}/MAT_{theme}_V6_TrendMonitor_Readout.mat",
                    $"{materialRoot}/MAT_{theme}_V6_TrendMonitor_Display.mat",
                    $"Assets/MatsuMotoMeterAR/Resources/{theme}/Prefabs/" +
                    $"PF_Visual_TrendMonitor_{theme}.prefab"
                });
            }
            return paths
                .SelectMany(path => new[] { path, path + ".meta" })
                .Select(path => new ManagedPath(path, File.Exists(path)))
                .ToList();
        }

        private static void Backup(
            IEnumerable<ManagedPath> managed,
            string backupRoot)
        {
            Directory.CreateDirectory(backupRoot);
            foreach (var item in managed.Where(item => item.Existed))
            {
                var destination = Path.Combine(backupRoot, item.Path);
                Directory.CreateDirectory(Path.GetDirectoryName(destination));
                File.Copy(item.Path, destination, true);
            }
        }

        private static void Restore(
            IEnumerable<ManagedPath> managed,
            string backupRoot)
        {
            foreach (var item in managed)
            {
                if (item.Existed)
                {
                    var source = Path.Combine(backupRoot, item.Path);
                    if (!File.Exists(source))
                        throw new FileNotFoundException(
                            "Texture promotion backup missing", source);
                    Directory.CreateDirectory(Path.GetDirectoryName(item.Path));
                    File.Copy(source, item.Path, true);
                }
                else if (File.Exists(item.Path))
                {
                    File.Delete(item.Path);
                }
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        private static void CopyTextures()
        {
            foreach (var theme in Themes)
            {
                var sourceRoot = $"{CandidateRoot}/Textures/{theme}";
                var destinationRoot =
                    $"Assets/MatsuMotoMeterAR/Content/Themes/{theme}/" +
                    "Textures/TrendMonitor";
                Directory.CreateDirectory(destinationRoot);
                foreach (var role in MapRoles)
                {
                    var name =
                        $"T_{theme}_V6_TrendMonitor_T1_{role}.png";
                    var source = $"{sourceRoot}/{name}";
                    if (!File.Exists(source))
                        throw new FileNotFoundException(
                            "Candidate texture missing", source);
                    File.Copy(source, $"{destinationRoot}/{name}", true);
                }
            }
        }

        private static void ValidateProduction()
        {
            foreach (var theme in Themes)
            {
                var prefabPath =
                    $"Assets/MatsuMotoMeterAR/Resources/{theme}/Prefabs/" +
                    $"PF_Visual_TrendMonitor_{theme}.prefab";
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (prefab == null)
                    throw new FileNotFoundException(
                        "Production prefab missing", prefabPath);
                var renderers = prefab.GetComponentsInChildren<Renderer>(true);
                var materials = renderers
                    .SelectMany(renderer => renderer.sharedMaterials)
                    .Where(material => material != null)
                    .Distinct()
                    .ToArray();
                if (renderers.Length != 3 || materials.Length != 3)
                    throw new InvalidDataException(
                        $"{theme}: expected 3 renderers / 3 materials; " +
                        $"got {renderers.Length} / {materials.Length}.");
                var display = renderers.FirstOrDefault(
                    renderer => renderer.transform.name == "display_surface");
                var displayMaterial = display?.sharedMaterial;
                if (displayMaterial == null ||
                    !displayMaterial.name.Contains("Display",
                        StringComparison.Ordinal))
                    throw new InvalidDataException(
                        $"{theme}: dedicated display material missing.");
                if (displayMaterial.GetTexture("_BaseMap") != null ||
                    displayMaterial.GetColor("_BaseColor").maxColorComponent > 0.05f)
                    throw new InvalidDataException(
                        $"{theme}: display must stay dark and untextured.");
                var forbidden = AssetDatabase.GetDependencies(prefabPath, true)
                    .FirstOrDefault(path => path.Contains(
                        "/CandidateStaging/", StringComparison.Ordinal));
                if (forbidden != null)
                    throw new InvalidDataException(
                        $"{theme}: candidate dependency remains: {forbidden}");
            }
        }

        private static void WriteReport(
            IEnumerable<ManagedPath> managed,
            string backupRoot)
        {
            var report = new StringBuilder();
            report.AppendLine($"# {CandidateId} production promotion");
            report.AppendLine();
            report.AppendLine("Result: **APPLIED**");
            report.AppendLine();
            report.AppendLine($"Backup: `{backupRoot}`");
            report.AppendLine();
            report.AppendLine("| Asset | SHA-256 |");
            report.AppendLine("| --- | --- |");
            foreach (var item in managed.Where(item =>
                         !item.Path.EndsWith(".meta", StringComparison.Ordinal) &&
                         File.Exists(item.Path)))
                report.AppendLine(
                    $"| `{item.Path}` | `{Digest(item.Path)}` |");
            report.AppendLine();
            report.AppendLine("- Production FBX changed: no");
            report.AppendLine("- Candidate dependencies: 0");
            report.AppendLine("- Display dark/untextured: 3 / 3 PASS");
            report.AppendLine("- Active prefab validation: PASS");
            Directory.CreateDirectory("Builds/Reports");
            File.WriteAllText(
                $"Builds/Reports/candidate-{CandidateId}-" +
                "production-promotion.md",
                report.ToString());
        }

        private static string Digest(string path)
        {
            using var stream = File.OpenRead(path);
            using var sha = SHA256.Create();
            return string.Concat(
                sha.ComputeHash(stream).Select(value => value.ToString("x2")));
        }

        private readonly struct ManagedPath
        {
            public ManagedPath(string path, bool existed)
            {
                Path = path;
                Existed = existed;
            }

            public string Path { get; }
            public bool Existed { get; }
        }
    }
}
