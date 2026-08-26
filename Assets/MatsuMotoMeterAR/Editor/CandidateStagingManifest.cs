using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    [Serializable]
    internal sealed class CandidateStagingManifest
    {
        private const string AllowedSourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/";
        private static readonly HashSet<string> SupportedThemes = new(
            new[] { "OrbitalAnalog", "ForgeBrass", "KineticSafety" },
            StringComparer.Ordinal);
        private static readonly HashSet<string> SupportedModels = new(
            new[]
            {
                "MeterRound", "Lever", "Toggle", "Rotary", "Button",
                "Lamp", "Throttle", "PowerSlider", "StatusIndicator",
                "MeterMedium", "MeterLarge", "WindowMeter", "WindowPanel",
                "TrendMonitor"
            },
            StringComparer.Ordinal);

        public int schemaVersion;
        public string candidateId;
        public string integrationStage;
        public CandidateStagingEntry[] entries;
        public CandidateGateCEvidence gateCEvidence;

        public string ResourceRoot =>
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            $"CandidateStaging/{candidateId}/Resources/{candidateId}";

        public static string SelectedAssetPath()
        {
            var selected = Selection.activeObject;
            var path = selected == null
                ? string.Empty
                : AssetDatabase.GetAssetPath(selected);
            if (string.IsNullOrWhiteSpace(path) ||
                !path.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException(
                    "Select one candidate manifest JSON asset in the " +
                    "Project window.");
            }
            return path;
        }

        public string CandidatePrefabPath(CandidateStagingEntry entry)
        {
            return $"{ResourceRoot}/{entry.theme}/Prefabs/" +
                   $"PF_Visual_{entry.model}_{entry.theme}.prefab";
        }

        public static string ActivePrefabPath(CandidateStagingEntry entry)
        {
            return "Assets/MatsuMotoMeterAR/Resources/" +
                   $"{entry.theme}/Prefabs/" +
                   $"PF_Visual_{entry.model}_{entry.theme}.prefab";
        }

        public static CandidateStagingManifest Load(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
                throw new ArgumentException("Manifest path is required.", nameof(path));
            if (!File.Exists(path))
                throw new FileNotFoundException("Candidate manifest is missing.", path);

            var manifest = JsonUtility.FromJson<CandidateStagingManifest>(
                File.ReadAllText(path));
            if (manifest == null)
                throw new InvalidDataException($"Could not parse manifest: {path}");

            var problems = manifest.ValidateDefinition();
            if (problems.Count > 0)
            {
                throw new InvalidDataException(
                    $"Invalid candidate manifest {path}:\n" +
                    string.Join("\n", problems));
            }
            return manifest;
        }

        public IReadOnlyList<string> ValidateDefinition()
        {
            var problems = new List<string>();
            if (schemaVersion != 1 && schemaVersion != 2)
                problems.Add($"schemaVersion must be 1 or 2, got {schemaVersion}.");
            if (!IsSafeIdentifier(candidateId))
            {
                problems.Add(
                    "candidateId must contain only ASCII letters, digits, " +
                    "underscore, or hyphen.");
            }
            if (entries == null || entries.Length == 0)
            {
                problems.Add("entries must contain at least one candidate.");
                return problems;
            }

            if (schemaVersion == 2 &&
                integrationStage != CandidateIntegrationStages.GateB &&
                integrationStage != CandidateIntegrationStages.GateC)
            {
                problems.Add("schemaVersion 2 integrationStage must be GateB or GateC.");
            }

            var identities = new HashSet<string>(StringComparer.Ordinal);
            for (var index = 0; index < entries.Length; index++)
            {
                var entry = entries[index];
                var label = $"entries[{index}]";
                if (entry == null)
                {
                    problems.Add($"{label} is null.");
                    continue;
                }
                if (!IsSafeIdentifier(entry.theme))
                    problems.Add($"{label}.theme is not a safe identifier.");
                else if (!SupportedThemes.Contains(entry.theme))
                    problems.Add($"{label}.theme is unsupported: {entry.theme}.");
                if (!IsSafeIdentifier(entry.model))
                    problems.Add($"{label}.model is not a safe identifier.");
                else if (!SupportedModels.Contains(entry.model))
                    problems.Add($"{label}.model is unsupported: {entry.model}.");

                var identity = $"{entry.theme}/{entry.model}";
                if (!identities.Add(identity))
                    problems.Add($"Duplicate candidate entry: {identity}.");

                ValidateSourcePath(
                    entry.sourceFbx,
                    ".fbx",
                    $"{label}.sourceFbx",
                    required: true,
                    problems);
                ValidateSourcePath(
                    entry.sourceReport,
                    ".json",
                    $"{label}.sourceReport",
                    required: false,
                    problems);

                if (schemaVersion == 2)
                    ValidateLineage(entry, label, problems);
            }
            return problems;
        }

        public IReadOnlyList<string> MissingRequiredRevisions(
            CandidateStagingEntry entry)
        {
            var included = new HashSet<string>(
                entry?.includedRevisions ?? Array.Empty<string>(),
                StringComparer.Ordinal);
            var missing = new List<string>();
            var required = new HashSet<string>(
                entry?.requiredRevisions ?? Array.Empty<string>(),
                StringComparer.Ordinal);
            if (entry != null)
            {
                required.UnionWith(
                    CandidateIntegrationPolicy.RequiredRevisions(
                        entry.theme,
                        entry.model));
            }
            foreach (var revision in required)
            {
                if (!string.IsNullOrWhiteSpace(revision) &&
                    !included.Contains(revision) &&
                    !missing.Contains(revision))
                {
                    missing.Add(revision);
                }
            }
            missing.Sort(StringComparer.Ordinal);
            return missing;
        }

        private void ValidateLineage(
            CandidateStagingEntry entry,
            string label,
            ICollection<string> problems)
        {
            if (!IsSafeIdentifier(entry.revision))
                problems.Add($"{label}.revision is not a safe identifier.");

            ValidateRevisionSet(
                entry.includedRevisions,
                $"{label}.includedRevisions",
                required: true,
                problems);
            ValidateRevisionSet(
                entry.requiredRevisions,
                $"{label}.requiredRevisions",
                required: true,
                problems);

            if (integrationStage != CandidateIntegrationStages.GateC)
                return;

            var missing = MissingRequiredRevisions(entry);
            if (missing.Count > 0)
            {
                problems.Add(
                    $"{label} cannot enter GateC; missing required revisions: " +
                    string.Join(", ", missing) + ".");
            }
            if (string.IsNullOrWhiteSpace(entry.sourceReport))
                problems.Add($"{label}.sourceReport is required for GateC.");
        }

        private static void ValidateRevisionSet(
            string[] revisions,
            string label,
            bool required,
            ICollection<string> problems)
        {
            if (revisions == null || revisions.Length == 0)
            {
                if (required)
                    problems.Add($"{label} must contain at least one revision.");
                return;
            }

            var unique = new HashSet<string>(StringComparer.Ordinal);
            for (var index = 0; index < revisions.Length; index++)
            {
                var revision = revisions[index];
                if (!IsSafeIdentifier(revision))
                    problems.Add($"{label}[{index}] is not a safe identifier.");
                else if (!unique.Add(revision))
                    problems.Add($"{label} contains duplicate revision {revision}.");
            }
        }

        private static void ValidateSourcePath(
            string path,
            string extension,
            string label,
            bool required,
            ICollection<string> problems)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                if (required)
                    problems.Add($"{label} is required.");
                return;
            }

            var normalized = path.Replace('\\', '/');
            if (!normalized.StartsWith(AllowedSourceRoot, StringComparison.Ordinal) ||
                normalized.Contains("../", StringComparison.Ordinal) ||
                Path.IsPathRooted(path))
            {
                problems.Add(
                    $"{label} must stay under {AllowedSourceRoot}.");
            }
            if (!normalized.EndsWith(extension, StringComparison.OrdinalIgnoreCase))
                problems.Add($"{label} must end with {extension}.");
            if (!File.Exists(normalized))
                problems.Add($"{label} does not exist: {normalized}.");
        }

        private static bool IsSafeIdentifier(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return false;
            foreach (var character in value)
            {
                var allowed =
                    character is >= 'A' and <= 'Z' or
                    >= 'a' and <= 'z' or
                    >= '0' and <= '9' or '_' or '-';
                if (!allowed)
                    return false;
            }
            return true;
        }
    }

    [Serializable]
    internal sealed class CandidateStagingEntry
    {
        public string theme;
        public string model;
        public string sourceFbx;
        public string sourceReport;
        public string revision;
        public string[] includedRevisions;
        public string[] requiredRevisions;
    }

    internal static class CandidateIntegrationStages
    {
        public const string GateB = "GateB";
        public const string GateC = "GateC";
    }

    internal static class CandidateIntegrationPolicy
    {
        private static readonly Dictionary<string, string[]> Requirements = new(
            StringComparer.Ordinal)
        {
            ["KineticSafety/MeterRound"] = new[] { "R2", "D3" },
            ["KineticSafety/MeterMedium"] = new[] { "B2", "D3" },
            ["KineticSafety/MeterLarge"] = new[] { "B2", "D3" },
            ["OrbitalAnalog/MeterRound"] = new[] { "D3", "D4" },
            ["OrbitalAnalog/MeterMedium"] = new[] { "D3", "D4" },
            ["OrbitalAnalog/MeterLarge"] = new[] { "D3", "D4" },
            ["OrbitalAnalog/Toggle"] = new[] { "D5" },
            ["ForgeBrass/Toggle"] = new[] { "D5", "D10" },
            ["KineticSafety/Toggle"] = new[] { "D5" }
        };

        public static IReadOnlyList<string> RequiredRevisions(
            string theme,
            string model)
        {
            return Requirements.TryGetValue($"{theme}/{model}", out var revisions)
                ? revisions
                : Array.Empty<string>();
        }
    }

    [Serializable]
    internal sealed class CandidateGateCEvidence
    {
        public string semanticUvAudit;
        public string fixedCameraVisualReview;
        public string motionAudit;
        public string unityStagingValidation;
        public string editModeTests;
        public string quest48Gate;
        public string quest64Stress;
        public string rollbackPlan;
    }
}
