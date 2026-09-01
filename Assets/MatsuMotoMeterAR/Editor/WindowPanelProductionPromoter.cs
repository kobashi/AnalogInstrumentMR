using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using MatsuMotoMeterAR.Instruments;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class WindowPanelProductionPromoter
    {
        private const string CandidateId = "WindowPanel_WP3_r2";
        private const string ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "WindowPanel_WP3_r2.json";
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging/WindowPanel_WP3_r2";
        private const string PreflightReportPath =
            "Builds/Reports/candidate-WindowPanel_WP3_r2-" +
            "production-preflight.md";

        private static readonly ThemeSpec[] Themes =
        {
            new(
                "OrbitalAnalog",
                "Assets/MatsuMotoMeterAR/Content/Themes/OrbitalAnalog/" +
                "Models/SM_WindowPanel_OrbitalAnalog.fbx"),
            new(
                "ForgeBrass",
                "Assets/MatsuMotoMeterAR/Content/Themes/ForgeBrass/" +
                "Models/SM_WindowPanel_ForgeBrass.fbx"),
            new(
                "KineticSafety",
                "Assets/MatsuMotoMeterAR/Content/Themes/KineticSafety/" +
                "Models/SM_WindowPanel_KineticSafety.fbx"),
            new(
                "MachinedErgonomics",
                "Assets/MatsuMotoMeterAR/Content/Themes/" +
                "MachinedErgonomics/Models/" +
                "SM_WindowPanel_MachinedErgonomics_V6_Opus5_P6C_R2.fbx")
        };

        private static readonly string[] MaterialRoles =
        {
            "Face", "Frame", "Trim"
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Preflight Window Panel WP4 Production Promotion")]
        public static void Preflight()
        {
            var manifest = RequireReadyManifest();
            var report = new StringBuilder();
            report.AppendLine($"# {CandidateId} production preflight");
            report.AppendLine();
            report.AppendLine("Result: **PASS**");
            report.AppendLine();
            report.AppendLine(
                "| Theme | Triangles | Renderers | Materials | " +
                "Active FBX | Active prefab | Result |");
            report.AppendLine(
                "| --- | ---: | ---: | ---: | --- | --- | --- |");

            foreach (var theme in Themes)
                ValidateTheme(manifest, theme, report);

            report.AppendLine();
            report.AppendLine("- Gate C readiness: 18 / 18");
            report.AppendLine("- Quest 48 / 64: DEFERRED by user");
            report.AppendLine("- Candidate dependencies after promotion: planned 0");
            report.AppendLine("- Active model and prefab GUIDs: preserved in place");
            report.AppendLine("- Production writes performed by preflight: 0");
            Directory.CreateDirectory(Path.GetDirectoryName(PreflightReportPath));
            File.WriteAllText(PreflightReportPath, report.ToString());
            AssetDatabase.Refresh();
            Debug.Log(
                $"{CandidateId} production promotion preflight PASS: " +
                PreflightReportPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Promote Window Panel WP4 to Production")]
        public static void Promote()
        {
            var manifest = RequireReadyManifest();
            Preflight();
            var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            var backupRoot =
                $"Builds/ModelReplacementBackups/{CandidateId}_{timestamp}";
            var managed = ResolveManagedPaths();
            Backup(managed, backupRoot);
            try
            {
                foreach (var theme in Themes)
                    PromoteTheme(theme);
                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                foreach (var theme in Themes)
                    ValidateProductionTheme(manifest, theme);
                WritePromotionReport(managed, backupRoot);
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

        private static CandidateStagingManifest RequireReadyManifest()
        {
            var manifest = CandidateStagingManifest.Load(ManifestPath);
            if (manifest.candidateId != CandidateId)
                throw new InvalidDataException(
                    $"Unexpected candidate at {ManifestPath}.");
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
            return manifest;
        }

        private static void ValidateTheme(
            CandidateStagingManifest manifest,
            ThemeSpec theme,
            StringBuilder report)
        {
            var entry = manifest.entries.Single(candidate =>
                candidate.theme == theme.Name &&
                candidate.model == "WindowPanel");
            RequireFile(theme.StagedModel);
            RequireFile(theme.StagedPrefab);
            RequireFile(theme.ActiveModel);
            RequireFile(theme.ActivePrefab);
            foreach (var role in MaterialRoles)
                RequireFile(theme.StagedMaterial(role));

            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                theme.StagedPrefab);
            if (prefab == null)
                throw new FileNotFoundException(
                    "Staged Window Panel prefab is not imported.",
                    theme.StagedPrefab);
            var problems = WindowPanelCandidateContractValidator
                .Evaluate(prefab);
            if (problems.Count > 0)
                throw new InvalidDataException(
                    $"{theme.Name}: {string.Join("; ", problems)}");
            var renderers = prefab.GetComponentsInChildren<Renderer>(true);
            var triangles = prefab.GetComponentsInChildren<MeshFilter>(true)
                .Where(filter => filter.sharedMesh != null)
                .Sum(filter => filter.sharedMesh.triangles.Length / 3);
            var roles = renderers
                .Select(renderer => MaterialRole(
                    renderer.sharedMaterial?.name))
                .ToArray();
            foreach (var role in MaterialRoles)
            {
                if (roles.Count(candidate => candidate == role) != 1)
                    throw new InvalidDataException(
                        $"{theme.Name}: material role {role} must occur once.");
            }
            if (renderers.Length != 3)
                throw new InvalidDataException(
                    $"{theme.Name}: expected 3 renderers, got " +
                    $"{renderers.Length}.");
            if (!File.Exists(entry.sourceReport))
                throw new FileNotFoundException(
                    "Source report missing.", entry.sourceReport);

            report.Append("| ")
                .Append(theme.Name)
                .Append(" | ")
                .Append(triangles)
                .Append(" | ")
                .Append(renderers.Length)
                .Append(" | 3 | `")
                .Append(theme.ActiveModel)
                .Append("` | `")
                .Append(theme.ActivePrefab)
                .AppendLine("` | PASS |");
        }

        private static void PromoteTheme(ThemeSpec theme)
        {
            File.Copy(theme.StagedModel, theme.ActiveModel, true);
            AssetDatabase.ImportAsset(
                theme.ActiveModel,
                ImportAssetOptions.ForceSynchronousImport |
                ImportAssetOptions.ForceUpdate);
            if (AssetImporter.GetAtPath(theme.ActiveModel) is
                ModelImporter importer)
            {
                importer.materialImportMode =
                    ModelImporterMaterialImportMode.ImportStandard;
                importer.addCollider = false;
                importer.SaveAndReimport();
            }

            var materials = new Dictionary<string, Material>(
                StringComparer.Ordinal);
            foreach (var role in MaterialRoles)
            {
                var source = AssetDatabase.LoadAssetAtPath<Material>(
                    theme.StagedMaterial(role));
                if (source == null)
                    throw new FileNotFoundException(
                        "Staged material missing.",
                        theme.StagedMaterial(role));
                var destinationPath = theme.ActiveMaterial(role);
                var destination = AssetDatabase.LoadAssetAtPath<Material>(
                    destinationPath);
                if (destination == null)
                {
                    Directory.CreateDirectory(
                        Path.GetDirectoryName(destinationPath));
                    destination = new Material(source)
                    {
                        name = $"MAT_{theme.Name}_V6_WindowPanel_{role}"
                    };
                    AssetDatabase.CreateAsset(destination, destinationPath);
                }
                else
                {
                    EditorUtility.CopySerialized(source, destination);
                    destination.name =
                        $"MAT_{theme.Name}_V6_WindowPanel_{role}";
                    EditorUtility.SetDirty(destination);
                }
                materials.Add(role, destination);
            }
            AssetDatabase.SaveAssets();

            var activeModel = AssetDatabase.LoadAssetAtPath<GameObject>(
                theme.ActiveModel);
            var activeMeshes = AssetDatabase.LoadAllAssetsAtPath(
                    theme.ActiveModel)
                .OfType<Mesh>()
                .GroupBy(mesh => mesh.name)
                .ToDictionary(group => group.Key, group => group.Single());
            if (activeModel == null || activeMeshes.Count == 0)
                throw new FileNotFoundException(
                    "Promoted FBX did not import.", theme.ActiveModel);

            var stagedPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                theme.StagedPrefab);
            var instance = PrefabUtility.InstantiatePrefab(stagedPrefab)
                as GameObject;
            if (instance == null)
                throw new InvalidOperationException(
                    $"Could not instantiate {theme.StagedPrefab}.");
            try
            {
                PrefabUtility.UnpackPrefabInstance(
                    instance,
                    PrefabUnpackMode.Completely,
                    InteractionMode.AutomatedAction);
                instance.name = $"PF_Visual_WindowPanel_{theme.Name}";
                foreach (var filter in
                         instance.GetComponentsInChildren<MeshFilter>(true))
                {
                    var meshName = filter.sharedMesh?.name;
                    if (meshName == null ||
                        !activeMeshes.TryGetValue(meshName, out var mesh))
                    {
                        throw new MissingReferenceException(
                            $"{theme.Name}: active mesh missing for " +
                            $"{meshName ?? "<null>"}.");
                    }
                    filter.sharedMesh = mesh;
                }
                foreach (var renderer in
                         instance.GetComponentsInChildren<Renderer>(true))
                {
                    var role = MaterialRole(renderer.sharedMaterial?.name);
                    renderer.sharedMaterial = materials[role];
                }
                foreach (var collider in
                         instance.GetComponentsInChildren<Collider>(true))
                    UnityEngine.Object.DestroyImmediate(collider);
                var display = Find(instance.transform, "display_surface");
                var visualManifest =
                    instance.GetComponent<ThemeVisualManifest>() ??
                    instance.AddComponent<ThemeVisualManifest>();
                visualManifest.Configure(display, null, null);
                if (PrefabUtility.SaveAsPrefabAsset(
                        instance, theme.ActivePrefab) == null)
                {
                    throw new IOException(
                        $"Could not save production prefab {theme.ActivePrefab}.");
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static void ValidateProductionTheme(
            CandidateStagingManifest manifest,
            ThemeSpec theme)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                theme.ActivePrefab);
            if (prefab == null)
                throw new FileNotFoundException(
                    "Production prefab missing.", theme.ActivePrefab);
            var problems = WindowPanelCandidateContractValidator
                .Evaluate(prefab);
            if (problems.Count > 0)
                throw new InvalidDataException(
                    $"{theme.Name}: {string.Join("; ", problems)}");
            var manifestComponent = prefab.GetComponent<ThemeVisualManifest>();
            if (manifestComponent?.MotionTarget == null ||
                manifestComponent.MotionTarget.name != "display_surface")
            {
                throw new InvalidDataException(
                    $"{theme.Name}: production display target is invalid.");
            }
            var forbidden = AssetDatabase.GetDependencies(
                    theme.ActivePrefab, true)
                .FirstOrDefault(path => path.Contains(
                    "/CandidateStaging/", StringComparison.Ordinal));
            if (forbidden != null)
                throw new InvalidDataException(
                    $"{theme.Name}: candidate dependency remains: {forbidden}");
            var entry = manifest.entries.Single(candidate =>
                candidate.theme == theme.Name &&
                candidate.model == "WindowPanel");
            if (!File.Exists(entry.sourceReport))
                throw new FileNotFoundException(
                    "Source report missing.", entry.sourceReport);
        }

        private static List<ManagedPath> ResolveManagedPaths()
        {
            return Themes.SelectMany(theme =>
                    new[] { theme.ActiveModel, theme.ActivePrefab }
                        .Concat(MaterialRoles.Select(theme.ActiveMaterial)))
                .SelectMany(path => new[] { path, path + ".meta" })
                .Distinct(StringComparer.Ordinal)
                .Select(path => new ManagedPath(path, File.Exists(path)))
                .ToList();
        }

        private static void Backup(
            IEnumerable<ManagedPath> managed,
            string backupRoot)
        {
            Directory.CreateDirectory(backupRoot);
            var report = new StringBuilder();
            report.AppendLine($"# {CandidateId} pre-promotion backup");
            report.AppendLine();
            report.AppendLine("| Path | Existed | SHA-256 before | ");
            report.AppendLine("| --- | --- | --- |");
            foreach (var item in managed)
            {
                if (item.Existed)
                {
                    var destination = Path.Combine(backupRoot, item.Path);
                    Directory.CreateDirectory(
                        Path.GetDirectoryName(destination));
                    File.Copy(item.Path, destination, true);
                }
                report.Append("| `")
                    .Append(item.Path)
                    .Append("` | ")
                    .Append(item.Existed ? "yes" : "no")
                    .Append(" | ")
                    .Append(item.Existed ? $"`{Digest(item.Path)}`" : "n/a")
                    .AppendLine(" |");
            }
            File.WriteAllText(
                Path.Combine(backupRoot, "backup-manifest.md"),
                report.ToString());
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
                            "Promotion backup missing.", source);
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

        private static void WritePromotionReport(
            IEnumerable<ManagedPath> managed,
            string backupRoot)
        {
            var report = new StringBuilder();
            report.AppendLine($"# {CandidateId} production promotion");
            report.AppendLine();
            report.AppendLine("Result: **APPLIED (Quest acceptance deferred)**");
            report.AppendLine();
            report.AppendLine($"Backup: `{backupRoot}`");
            report.AppendLine();
            report.AppendLine("| Asset | SHA-256 after promotion |");
            report.AppendLine("| --- | --- |");
            foreach (var item in managed.Where(item =>
                         !item.Path.EndsWith(".meta", StringComparison.Ordinal) &&
                         File.Exists(item.Path)))
            {
                report.AppendLine(
                    $"| `{item.Path}` | `{Digest(item.Path)}` |");
            }
            report.AppendLine();
            report.AppendLine("- Candidate dependencies: 0");
            report.AppendLine("- Window Panel contract: 4 / 4 PASS");
            report.AppendLine("- Quest acceptance: DEFERRED");
            Directory.CreateDirectory("Builds/Reports");
            File.WriteAllText(
                $"Builds/Reports/candidate-{CandidateId}-" +
                "production-promotion.md",
                report.ToString());
        }

        private static string MaterialRole(string materialName)
        {
            foreach (var role in MaterialRoles)
            {
                if (!string.IsNullOrWhiteSpace(materialName) &&
                    materialName.Contains(role, StringComparison.Ordinal))
                    return role;
            }
            throw new InvalidDataException(
                $"Unknown Window Panel material role: " +
                $"{materialName ?? "<null>"}.");
        }

        private static Transform Find(Transform root, string name)
        {
            var matches = root.GetComponentsInChildren<Transform>(true)
                .Where(item => item.name == name)
                .ToArray();
            if (matches.Length != 1)
                throw new MissingReferenceException(
                    $"Expected one {name}; actual={matches.Length}.");
            return matches[0];
        }

        private static void RequireFile(string path)
        {
            if (!File.Exists(path))
                throw new FileNotFoundException("Required file missing.", path);
        }

        private static string Digest(string path)
        {
            using var stream = File.OpenRead(path);
            using var sha = SHA256.Create();
            return string.Concat(
                sha.ComputeHash(stream).Select(value => value.ToString("x2")));
        }

        private readonly struct ThemeSpec
        {
            public ThemeSpec(string name, string activeModel)
            {
                Name = name;
                ActiveModel = activeModel;
            }

            public string Name { get; }
            public string ActiveModel { get; }
            public string StagedModel =>
                $"{CandidateRoot}/Models/{Name}/" +
                $"SM_WindowPanel_{Name}_V6_Material.fbx";
            public string StagedPrefab =>
                $"{CandidateRoot}/Resources/{CandidateId}/{Name}/Prefabs/" +
                $"PF_Visual_WindowPanel_{Name}.prefab";
            public string ActivePrefab =>
                $"Assets/MatsuMotoMeterAR/Resources/{Name}/Prefabs/" +
                $"PF_Visual_WindowPanel_{Name}.prefab";
            public string StagedMaterial(string role) =>
                $"{CandidateRoot}/Resources/{CandidateId}/{Name}/Materials/" +
                $"MAT_{Name}_V6_WindowPanel_{role}_Staging.mat";
            public string ActiveMaterial(string role) =>
                $"Assets/MatsuMotoMeterAR/Content/Themes/{Name}/Materials/" +
                $"MAT_{Name}_V6_WindowPanel_{role}.mat";
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
