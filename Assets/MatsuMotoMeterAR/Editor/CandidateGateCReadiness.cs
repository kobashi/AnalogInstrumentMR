using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal readonly struct CandidateGateCCheck
    {
        public CandidateGateCCheck(string id, bool passed, string detail)
        {
            Id = id;
            Passed = passed;
            Detail = detail;
        }

        public string Id { get; }
        public bool Passed { get; }
        public string Detail { get; }
    }

    internal static class CandidateGateCReadiness
    {
        private static readonly HashSet<string> MotionModels = new(
            new[]
            {
                "MeterRound", "MeterMedium", "MeterLarge", "Lever", "Toggle",
                "Rotary", "Button", "Throttle", "PowerSlider", "WindowMeter",
                "WindowPanel"
            },
            StringComparer.Ordinal);

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Report Selected Candidate Gate C Readiness")]
        public static void ReportSelectedManifest()
        {
            var manifest = CandidateStagingManifest.Load(
                CandidateStagingManifest.SelectedAssetPath());
            var checks = Evaluate(manifest, File.Exists);
            var report = BuildMarkdown(manifest, checks);
            var directory = "Builds/Reports";
            Directory.CreateDirectory(directory);
            var path = $"{directory}/candidate-{manifest.candidateId}-gate-c-readiness.md";
            File.WriteAllText(path, report);

            var failures = checks.Count(check => !check.Passed);
            Debug.Log(
                $"[CandidateGateC] {manifest.candidateId}: " +
                $"{checks.Count - failures}/{checks.Count} checks PASS -> {path}");
        }

        internal static IReadOnlyList<CandidateGateCCheck> Evaluate(
            CandidateStagingManifest manifest,
            Func<string, bool> fileExists)
        {
            if (manifest == null)
                throw new ArgumentNullException(nameof(manifest));
            if (fileExists == null)
                throw new ArgumentNullException(nameof(fileExists));

            var checks = new List<CandidateGateCCheck>
            {
                new(
                    "manifest-schema-v2",
                    manifest.schemaVersion == 2,
                    $"schemaVersion={manifest.schemaVersion}"),
                new(
                    "integration-stage-gate-c",
                    manifest.integrationStage == CandidateIntegrationStages.GateC,
                    $"integrationStage={manifest.integrationStage ?? "<missing>"}")
            };

            foreach (var entry in manifest.entries ?? Array.Empty<CandidateStagingEntry>())
            {
                var identity = $"{entry.theme}/{entry.model}";
                var missing = manifest.MissingRequiredRevisions(entry);
                checks.Add(
                    new CandidateGateCCheck(
                        $"lineage:{identity}",
                        missing.Count == 0,
                        missing.Count == 0
                            ? $"included={Join(entry.includedRevisions)}"
                            : $"missing={string.Join(",", missing)}"));
                checks.Add(
                    Artifact(
                        $"fbx-report:{identity}",
                        entry.sourceReport,
                        fileExists));
            }

            var evidence = manifest.gateCEvidence;
            checks.Add(Artifact("semantic-uv-audit", evidence?.semanticUvAudit, fileExists));
            checks.Add(Artifact(
                "fixed-camera-visual-review",
                evidence?.fixedCameraVisualReview,
                fileExists));
            if ((manifest.entries ?? Array.Empty<CandidateStagingEntry>())
                .Any(entry => MotionModels.Contains(entry.model)))
            {
                checks.Add(Artifact("motion-audit", evidence?.motionAudit, fileExists));
            }
            checks.Add(Artifact(
                "unity-staging-validation",
                evidence?.unityStagingValidation,
                fileExists));
            checks.Add(Artifact("edit-mode-tests", evidence?.editModeTests, fileExists));
            checks.Add(Artifact("quest-48-gate", evidence?.quest48Gate, fileExists));
            checks.Add(Artifact("quest-64-stress", evidence?.quest64Stress, fileExists));
            checks.Add(Artifact("rollback-plan", evidence?.rollbackPlan, fileExists));
            return checks;
        }

        internal static string BuildMarkdown(
            CandidateStagingManifest manifest,
            IReadOnlyList<CandidateGateCCheck> checks)
        {
            var failures = checks.Count(check => !check.Passed);
            var builder = new StringBuilder();
            builder.AppendLine($"# Gate C readiness: {manifest.candidateId}");
            builder.AppendLine();
            builder.AppendLine(failures == 0 ? "Overall: **READY**" : "Overall: **BLOCKED**");
            builder.AppendLine();
            builder.AppendLine("| Check | Result | Detail |");
            builder.AppendLine("| --- | --- | --- |");
            foreach (var check in checks)
            {
                builder.AppendLine(
                    $"| {check.Id} | {(check.Passed ? "PASS" : "BLOCKED")} | " +
                    $"{check.Detail.Replace("|", "\\|")} |");
            }
            return builder.ToString();
        }

        private static CandidateGateCCheck Artifact(
            string id,
            string path,
            Func<string, bool> fileExists)
        {
            var present = !string.IsNullOrWhiteSpace(path) && fileExists(path);
            return new CandidateGateCCheck(
                id,
                present,
                string.IsNullOrWhiteSpace(path) ? "<missing>" : path);
        }

        private static string Join(string[] values)
        {
            return values == null ? "<missing>" : string.Join(",", values);
        }
    }
}
