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
    internal static class SuperfineProductionReadiness
    {
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging";
        private const string ManifestRoot =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests";
        private const string ReportPath =
            "Builds/Reports/superfine-production-readiness.md";

        private static readonly (string Path, int Count)[] Manifests =
        {
            ($"{ManifestRoot}/AudioModules_Superfine_C2.json", 6),
            ($"{ManifestRoot}/AudioModules_Superfine_C3.json", 4),
            ($"{ManifestRoot}/Superfine_NonAudio_C4.json", 14)
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Superfine/" +
            "Report Production Readiness (No Changes)")]
        public static void Report()
        {
            var problems = new List<string>();
            var rows = new List<EntryRow>();
            var identities = new HashSet<string>(StringComparer.Ordinal);
            var candidateGuids = new HashSet<string>(StringComparer.Ordinal);

            foreach (var manifestSpec in Manifests)
            {
                var manifest = CandidateStagingManifest.Load(manifestSpec.Path);
                if (manifest.entries.Length != manifestSpec.Count)
                {
                    problems.Add(
                        $"{manifest.candidateId}: expected {manifestSpec.Count} " +
                        $"entries, actual {manifest.entries.Length}.");
                }

                foreach (var entry in manifest.entries)
                {
                    var identity = $"{entry.theme}/{entry.model}";
                    if (!identities.Add(identity))
                        problems.Add($"Duplicate identity: {identity}.");
                    if (!string.Equals(
                            entry.theme,
                            "Superfine",
                            StringComparison.Ordinal))
                    {
                        problems.Add($"Unexpected theme: {identity}.");
                    }

                    var model =
                        $"{CandidateRoot}/{manifest.candidateId}/Models/" +
                        $"Superfine/SM_{entry.model}_Superfine_V6_Material.fbx";
                    var prefab =
                        $"{CandidateRoot}/{manifest.candidateId}/Resources/" +
                        $"{manifest.candidateId}/Superfine/Prefabs/" +
                        $"PF_Visual_{entry.model}_Superfine.prefab";
                    RequireFile(model, problems);
                    RequireFile(prefab, problems);
                    RequireFile(entry.sourceReport, problems);
                    RequireDistinctGuid(model, candidateGuids, problems);
                    RequireDistinctGuid(prefab, candidateGuids, problems);
                    RejectCrossCandidateDependencies(
                        prefab,
                        manifest.candidateId,
                        problems);

                    var productionModel =
                        "Assets/MatsuMotoMeterAR/Content/Themes/Superfine/" +
                        $"Models/SM_{entry.model}_Superfine.fbx";
                    var productionPrefab =
                        "Assets/MatsuMotoMeterAR/Resources/Superfine/Prefabs/" +
                        $"PF_Visual_{entry.model}_Superfine.prefab";
                    if (File.Exists(productionModel) || File.Exists(productionPrefab))
                    {
                        problems.Add(
                            $"Production collision exists for {entry.model}.");
                    }

                    rows.Add(
                        new EntryRow(
                            manifest.candidateId,
                            entry.model,
                            TriangleCount(prefab),
                            model,
                            prefab,
                            productionModel,
                            productionPrefab));
                }
            }

            if (rows.Count != 24)
                problems.Add($"Expected 24 combined entries, actual {rows.Count}.");

            var hasRegisteredEnum = Enum.GetNames(typeof(MockInstrumentTheme))
                .Contains("Superfine", StringComparer.Ordinal);
            if (hasRegisteredEnum || MockInstrumentThemeCatalog.Count != 4)
            {
                problems.Add(
                    "Superfine is already partially registered in the runtime " +
                    "theme catalogue; P0 requires the four-theme baseline.");
            }

            Directory.CreateDirectory(Path.GetDirectoryName(ReportPath));
            File.WriteAllText(
                ReportPath,
                BuildReport(rows, problems));
            AssetDatabase.Refresh();

            if (problems.Count > 0)
            {
                throw new InvalidOperationException(
                    "Superfine production readiness BLOCKED:\n" +
                    string.Join("\n", problems));
            }

            Debug.Log(
                "Superfine production readiness: READY WITH DEFERRED GATES. " +
                $"No production assets changed. {ReportPath}");
        }

        private static string BuildReport(
            IReadOnlyCollection<EntryRow> rows,
            IReadOnlyCollection<string> problems)
        {
            var report = new StringBuilder();
            report.AppendLine("# Superfine production readiness (P0)");
            report.AppendLine();
            report.AppendLine(
                problems.Count == 0
                    ? "Overall: **READY WITH DEFERRED GATES**"
                    : "Overall: **BLOCKED**");
            report.AppendLine();
            report.AppendLine("- Production mutation: **NONE**");
            report.AppendLine("- Candidate sources: C2 (6) + C3 (4) + C4 (14) = 24");
            report.AppendLine("- Runtime theme catalogue: four-theme baseline retained");
            report.AppendLine("- Q1 Quest load gate: **DEFERRED BY USER**");
            report.AppendLine("- B1 machine-specific caps: **PROVISIONAL / NOT ADOPTED**");
            report.AppendLine("- P production registration: **NOT APPLIED**");
            report.AppendLine();

            report.AppendLine("## Candidate-to-production map");
            report.AppendLine();
            report.AppendLine("| Candidate | Model | Tris | Proposed cap | Production model | Production prefab |");
            report.AppendLine("| --- | --- | ---: | ---: | --- | --- |");
            foreach (var row in rows.OrderBy(item => item.Model))
            {
                report.AppendLine(
                    $"| {row.Candidate} | {row.Model} | {row.Triangles} | " +
                    $"{ProposedCap(row)} | `{row.ProductionModel}` | " +
                    $"`{row.ProductionPrefab}` |");
            }
            report.AppendLine();
            report.AppendLine(
                "Proposed audio caps are documentation-only values calculated " +
                "as final candidate triangles + 7.5%, rounded up to 100. " +
                "Non-audio rows retain the current shared small/large cap. " +
                "None become validator limits until B1 is explicitly completed.");
            report.AppendLine();

            report.AppendLine("## P implementation requirements");
            report.AppendLine();
            report.AppendLine("1. Add enum value `Superfine = 4`; keep existing numeric values 0..3 unchanged.");
            report.AppendLine("2. Change catalogue count to 5; register ID `superfine`, display name `SUPERFINE`, palette, parse, normalize, and cycle.");
            report.AppendLine("3. Add `Superfine` resource-folder routing and all 24 prefab names to the runtime visual factory.");
            report.AppendLine("4. Create fresh production GUIDs; never copy Kinetic Safety or candidate `.meta` files.");
            report.AppendLine("5. Create one canonical audio material set (Housing / FaceMetal / EmissionDisplay), and one non-audio set (Housing / FaceMetal / EmissionDisplay / Glass); relink all production prefabs away from candidate staging.");
            report.AppendLine("6. Promote all 24 models atomically with backup and rollback; reject any remaining `/CandidateStaging/` dependency.");
            report.AppendLine("7. Extend theme persistence, theme-selection UI, palette-dependent audio/display colours, validators, and EditMode tests from four to five themes.");
            report.AppendLine("8. Keep Q1/B1 marked deferred; do not relabel triangle or material REVIEW as PASS.");
            report.AppendLine();

            report.AppendLine("## Known deferred reviews");
            report.AppendLine();
            report.AppendLine("- Audio triangle REVIEW: Envelope 5,496; LFO 7,122; Sequencer 6,498.");
            report.AppendLine("- Non-audio material REVIEW: four meters, WindowPanel, TrendMonitor, Rotary.");
            report.AppendLine("- TrendMonitor display width REVIEW: 0.348 m versus legacy minimum 0.36 m.");
            report.AppendLine();

            if (problems.Count > 0)
            {
                report.AppendLine("## Blocking findings");
                report.AppendLine();
                foreach (var problem in problems)
                    report.AppendLine($"- {problem}");
            }
            else
            {
                report.AppendLine("## Structural audit");
                report.AppendLine();
                report.AppendLine("- PASS: 24 unique Superfine model/prefab pairs are present.");
                report.AppendLine("- PASS: candidate FBX/prefab GUIDs are unique.");
                report.AppendLine("- PASS: cross-candidate dependencies are absent.");
                report.AppendLine("- PASS: production target paths have no collisions.");
                report.AppendLine("- PASS: runtime remains on the four-theme baseline before P.");
            }
            return report.ToString();
        }

        private static int ProposedCap(EntryRow row)
        {
            if (!row.Model.StartsWith("Audio", StringComparison.Ordinal))
                return row.Model == "MeterLarge" ||
                       row.Model == "WindowMeter" ||
                       row.Model == "WindowPanel"
                    ? 25000
                    : 5000;
            return Mathf.CeilToInt(row.Triangles * 1.075f / 100f) * 100;
        }

        private static void RequireFile(
            string path,
            ICollection<string> problems)
        {
            if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
                problems.Add($"Required file is missing: {path ?? "<null>"}.");
        }

        private static void RequireDistinctGuid(
            string path,
            ISet<string> guids,
            ICollection<string> problems)
        {
            if (!File.Exists(path))
                return;
            var guid = AssetDatabase.AssetPathToGUID(path);
            if (string.IsNullOrEmpty(guid))
                problems.Add($"Asset GUID is missing: {path}.");
            else if (!guids.Add(guid))
                problems.Add($"Duplicate candidate GUID {guid}: {path}.");
        }

        private static void RejectCrossCandidateDependencies(
            string prefab,
            string candidateId,
            ICollection<string> problems)
        {
            if (!File.Exists(prefab))
                return;
            var ownRoot = $"/CandidateStaging/{candidateId}/";
            foreach (var dependency in AssetDatabase.GetDependencies(prefab, true))
            {
                if (dependency.Contains("/CandidateStaging/", StringComparison.Ordinal) &&
                    !dependency.Contains(ownRoot, StringComparison.Ordinal))
                {
                    problems.Add(
                        $"{prefab}: cross-candidate dependency {dependency}.");
                }
            }
        }

        private static int TriangleCount(string prefabPath)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            return prefab == null
                ? 0
                : prefab.GetComponentsInChildren<MeshFilter>(true)
                    .Where(filter => filter.sharedMesh != null)
                    .Sum(filter => filter.sharedMesh.triangles.Length / 3);
        }

        private readonly struct EntryRow
        {
            public EntryRow(
                string candidate,
                string model,
                int triangles,
                string candidateModel,
                string candidatePrefab,
                string productionModel,
                string productionPrefab)
            {
                Candidate = candidate;
                Model = model;
                Triangles = triangles;
                CandidateModel = candidateModel;
                CandidatePrefab = candidatePrefab;
                ProductionModel = productionModel;
                ProductionPrefab = productionPrefab;
            }

            public string Candidate { get; }
            public string Model { get; }
            public int Triangles { get; }
            public string CandidateModel { get; }
            public string CandidatePrefab { get; }
            public string ProductionModel { get; }
            public string ProductionPrefab { get; }
        }
    }
}
