using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class Theme4BatchBQuestReviewBuilder
    {
        internal const string OutputPath =
            "Builds/QuestReview/AnalogInstrumentMR-Theme4-MachinedErgonomics-14-" +
            "review-quest3.apk";

        private const string CandidateId = "Theme4_MachinedErgonomics_14_FullGate";
        private const string ReviewDefine = "ANALOGMR_CANDIDATE_REVIEW";
        private const int MetaQuestBuildSubtarget = 6;
        private const string DevAgentSettingsPath =
            "Assets/Resources/DevAgentSettings.asset";
        private const string QuarantinedDevAgentSettingsPath =
            "Assets/MatsuMotoMeterAR/Editor/" +
            "DevAgentSettings.theme4-full14-review.local.asset";
        private const string ReviewConfigurationPath =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateReview/Resources/CandidateReviewConfiguration.json";
        private const string CandidateResourcePrefix =
            "Theme4_MachinedErgonomics_14_FullGate/MachinedErgonomics/Prefabs/";
        private const string ReviewTheme = "OrbitalAnalog";

        private static readonly string[] Models =
        {
            "MeterRound", "MeterMedium", "MeterLarge", "Lever", "Toggle",
            "Rotary", "Button", "Lamp", "StatusIndicator", "Throttle",
            "PowerSlider", "WindowMeter", "WindowPanel", "TrendMonitor"
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build Machined Ergonomics 14 Quest Review APK")]
        public static void Build()
        {
            if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.Android)
                throw new InvalidOperationException(
                    "The active build target must be Android / Meta Quest.");

            var scenes = EditorBuildSettings.scenes
                .Where(scene => scene.enabled)
                .Select(scene => scene.path)
                .ToArray();
            if (scenes.Length == 0)
                throw new InvalidOperationException("No enabled build scenes found.");

            Theme4BatchBFullGateBuilder.PrepareQuestReviewResources();
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
                    throw new InvalidOperationException(
                        $"Theme 4 fastener-access review build failed: " +
                        $"{report.summary.result}; " +
                        $"{report.summary.totalErrors} error(s).");
                Debug.Log(
                    $"Theme 4 fastener-access Quest review APK built: {OutputPath}; " +
                    $"{report.summary.totalSize} bytes.");
            }
            finally
            {
                PlayerSettings.enableFrameTimingStats = previousFrameTimingStats;
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

        private static ReviewMapping[] ReviewMappings()
        {
            return Models.Select(model => new ReviewMapping
            {
                prefabName = $"PF_Visual_{model}_{ReviewTheme}",
                resourcePath =
                    $"{CandidateResourcePrefix}PF_Visual_{model}_" +
                    "MachinedErgonomics"
            }).ToArray();
        }

        private static void CreateReviewConfiguration()
        {
            if (File.Exists(ReviewConfigurationPath))
                throw new IOException(
                    "Candidate review configuration already exists: " +
                    ReviewConfigurationPath);
            Directory.CreateDirectory(Path.GetDirectoryName(
                ReviewConfigurationPath));
            var configuration = new ReviewConfiguration
            {
                candidateId = CandidateId,
                entries = ReviewMappings()
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
                throw new IOException(
                    "Could not remove review configuration: " +
                    ReviewConfigurationPath);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        private static bool QuarantineDevAgentSettings()
        {
            if (!File.Exists(DevAgentSettingsPath))
                return false;
            if (File.Exists(QuarantinedDevAgentSettingsPath))
                throw new IOException(
                    "Credential quarantine exists: " +
                    QuarantinedDevAgentSettingsPath);
            var error = AssetDatabase.MoveAsset(
                DevAgentSettingsPath, QuarantinedDevAgentSettingsPath);
            if (!string.IsNullOrEmpty(error))
                throw new IOException(
                    "Could not quarantine credentials: " + error);
            return true;
        }

        private static void RestoreDevAgentSettings()
        {
            if (!File.Exists(QuarantinedDevAgentSettingsPath))
                throw new FileNotFoundException(
                    "Quarantined credentials lost",
                    QuarantinedDevAgentSettingsPath);
            if (File.Exists(DevAgentSettingsPath))
                throw new IOException(
                    "Credential restore destination exists: " +
                    DevAgentSettingsPath);
            var error = AssetDatabase.MoveAsset(
                QuarantinedDevAgentSettingsPath, DevAgentSettingsPath);
            if (!string.IsNullOrEmpty(error))
                throw new IOException(
                    "Could not restore credentials: " + error);
        }

        [Serializable]
        private sealed class ReviewConfiguration
        {
            public string candidateId;
            public ReviewMapping[] entries;
        }

        [Serializable]
        private sealed class ReviewMapping
        {
            public string prefabName;
            public string resourcePath;
        }
    }
}
