using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class Theme4Phase5QuestReviewBuilder
    {
        internal const string OutputPath =
            "Builds/QuestReview/AnalogInstrumentMR-Theme4-P5-review-quest3.apk";

        private const string CandidateId = "Theme4_P5_Delivery";
        private const string ReviewDefine = "ANALOGMR_CANDIDATE_REVIEW";
        private const int MetaQuestBuildSubtarget = 6;
        private const string DevAgentSettingsPath =
            "Assets/Resources/DevAgentSettings.asset";
        private const string QuarantinedDevAgentSettingsPath =
            "Assets/MatsuMotoMeterAR/Editor/" +
            "DevAgentSettings.theme4-p5-review.local.asset";
        private const string ReviewConfigurationPath =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateReview/Resources/CandidateReviewConfiguration.json";
        private const string CandidateResourcePrefix =
            "Theme4_P5_Delivery/MachinedErgonomics/Prefabs/";

        private const string ReviewTheme = "OrbitalAnalog";

        private static readonly string[] Models =
        {
            "MeterRound", "Lever", "Toggle"
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build Phase 5 Quest Review APK")]
        public static void Build()
        {
            if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.Android)
            {
                throw new InvalidOperationException(
                    "The active build target must be Android / Meta Quest.");
            }

            var scenes = EditorBuildSettings.scenes
                .Where(scene => scene.enabled)
                .Select(scene => scene.path)
                .ToArray();
            if (scenes.Length == 0)
                throw new InvalidOperationException("No enabled build scenes found.");

            Theme4Phase5CandidateBuilder.PrepareQuestReviewResources();
            Directory.CreateDirectory(Path.GetDirectoryName(OutputPath));
            var options = new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = OutputPath,
                target = BuildTarget.Android,
                subtarget = MetaQuestBuildSubtarget,
                options = BuildOptions.None,
                extraScriptingDefines = new[] { ReviewDefine }
            };

            var previousFrameTimingStats = PlayerSettings.enableFrameTimingStats;
            var quarantined = false;
            var configurationCreated = false;
            PlayerSettings.enableFrameTimingStats = true;
            try
            {
                CreateReviewConfiguration();
                configurationCreated = true;
                quarantined = QuarantineDevAgentSettings();
                var report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                {
                    throw new InvalidOperationException(
                        $"Theme 4 P5 review build failed: " +
                        $"{report.summary.result}; " +
                        $"{report.summary.totalErrors} error(s).");
                }

                Debug.Log(
                    $"Theme 4 P5 Quest review APK built: {OutputPath}; " +
                    $"{report.summary.totalSize} bytes; define={ReviewDefine}.");
            }
            finally
            {
                PlayerSettings.enableFrameTimingStats =
                    previousFrameTimingStats;
                try
                {
                    if (quarantined)
                        RestoreDevAgentSettings();
                }
                finally
                {
                    if (configurationCreated)
                        DeleteReviewConfiguration();
                }
            }
        }

        internal static IReadOnlyList<ReviewMapping> ReviewMappings()
        {
            var mappings = new List<ReviewMapping>();
            foreach (var model in Models)
            {
                var resourcePath =
                    $"{CandidateResourcePrefix}PF_Visual_{model}_" +
                    "MachinedErgonomics";
                mappings.Add(new ReviewMapping(
                    $"PF_Visual_{model}_{ReviewTheme}",
                    resourcePath));
            }
            return mappings;
        }

        private static void CreateReviewConfiguration()
        {
            if (File.Exists(ReviewConfigurationPath))
            {
                throw new IOException(
                    "Candidate review configuration already exists: " +
                    ReviewConfigurationPath);
            }

            Directory.CreateDirectory(
                Path.GetDirectoryName(ReviewConfigurationPath));
            var configuration = new ReviewConfiguration
            {
                candidateId = CandidateId,
                entries = ReviewMappings()
                    .Select(mapping => new ReviewEntry
                    {
                        prefabName = mapping.PrefabName,
                        resourcePath = mapping.ResourcePath
                    })
                    .ToArray()
            };
            File.WriteAllText(
                ReviewConfigurationPath,
                JsonUtility.ToJson(configuration, true),
                new UTF8Encoding(false));
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        private static void DeleteReviewConfiguration()
        {
            if (!AssetDatabase.DeleteAsset(ReviewConfigurationPath) &&
                File.Exists(ReviewConfigurationPath))
            {
                throw new IOException(
                    "Could not remove generated candidate review " +
                    $"configuration: {ReviewConfigurationPath}");
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        private static bool QuarantineDevAgentSettings()
        {
            if (!File.Exists(DevAgentSettingsPath))
                return false;
            if (File.Exists(QuarantinedDevAgentSettingsPath))
            {
                throw new IOException(
                    "Review-build credential quarantine already exists: " +
                    QuarantinedDevAgentSettingsPath);
            }

            var error = AssetDatabase.MoveAsset(
                DevAgentSettingsPath,
                QuarantinedDevAgentSettingsPath);
            if (!string.IsNullOrEmpty(error))
            {
                throw new IOException(
                    $"Could not quarantine development credentials: {error}");
            }
            return true;
        }

        private static void RestoreDevAgentSettings()
        {
            if (!File.Exists(QuarantinedDevAgentSettingsPath))
            {
                throw new FileNotFoundException(
                    "Quarantined development credentials were lost.",
                    QuarantinedDevAgentSettingsPath);
            }
            if (File.Exists(DevAgentSettingsPath))
            {
                throw new IOException(
                    "Cannot restore development credentials because the " +
                    $"destination already exists: {DevAgentSettingsPath}");
            }

            var error = AssetDatabase.MoveAsset(
                QuarantinedDevAgentSettingsPath,
                DevAgentSettingsPath);
            if (!string.IsNullOrEmpty(error))
            {
                throw new IOException(
                    $"Could not restore development credentials: {error}");
            }
        }

        internal readonly struct ReviewMapping
        {
            public ReviewMapping(string prefabName, string resourcePath)
            {
                PrefabName = prefabName;
                ResourcePath = resourcePath;
            }

            public string PrefabName { get; }
            public string ResourcePath { get; }
        }

        [Serializable]
        private sealed class ReviewConfiguration
        {
            public string candidateId;
            public ReviewEntry[] entries;
        }

        [Serializable]
        private sealed class ReviewEntry
        {
            public string prefabName;
            public string resourcePath;
        }
    }
}
