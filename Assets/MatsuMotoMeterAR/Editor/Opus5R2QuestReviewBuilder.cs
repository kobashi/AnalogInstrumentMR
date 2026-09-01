using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class Opus5R2QuestReviewBuilder
    {
        public const string OutputPath =
            "Builds/QuestReview/AnalogInstrumentMR-Opus5-R2-review-quest3.apk";
        private const string ReviewDefine = "ANALOGMR_OPUS5_R2_REVIEW";
        private const string CandidateReviewDefine =
            "ANALOGMR_CANDIDATE_REVIEW";
        private const int MetaQuestBuildSubtarget = 6;
        private const string DevAgentSettingsPath =
            "Assets/Resources/DevAgentSettings.asset";
        private const string QuarantinedDevAgentSettingsPath =
            "Assets/MatsuMotoMeterAR/Editor/" +
            "DevAgentSettings.opus5-r2-review.local.asset";
        private const string CandidateReviewConfigurationPath =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateReview/Resources/CandidateReviewConfiguration.json";
        private const string Opus5R2ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Opus5_R2.json";
        private const string MeterM2n5ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n5.json";
        private const string MeterM2n7ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n7.json";
        private const string MeterM2n8ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n8.json";
        private const string TrendMonitorP1ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "TrendMonitor_P1.json";
        private const string TrendMonitorP2ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "TrendMonitor_P2.json";
        private const string WindowPanelWp3R2ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "WindowPanel_WP3_r2.json";

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Opus 5 R2 Quest Review APK")]
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

            V6ModelReplacementStagingBuilder.BuildOpus5R2Candidate();
            V6ModelReplacementStagingBuilder.BuildOpus5LargeCandidate();
            V6ModelReplacementStagingBuilder.BuildOpus5MediumCandidate();
            RefinedModelReplacementValidator
                .ValidateOpus5R2CandidateStaging();
            RefinedModelReplacementValidator
                .ValidateOpus5LargeCandidateStaging();
            RefinedModelReplacementValidator
                .ValidateOpus5MediumCandidateStaging();
            Opus5R2CandidateMotionAudit.Run();

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
            PlayerSettings.enableFrameTimingStats = true;
            try
            {
                quarantined = QuarantineDevAgentSettings();
                var report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                {
                    throw new InvalidOperationException(
                        $"Opus 5 R2 review build failed: " +
                        $"{report.summary.result}; " +
                        $"{report.summary.totalErrors} error(s).");
                }

                Debug.Log(
                    $"Opus 5 R2 Quest review APK built: {OutputPath}; " +
                    $"{report.summary.totalSize} bytes; define={ReviewDefine}.");
            }
            finally
            {
                PlayerSettings.enableFrameTimingStats = previousFrameTimingStats;
                if (quarantined)
                    RestoreDevAgentSettings();
            }
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Selected Candidate Manifest Quest Review APK")]
        public static void BuildSelectedManifest()
        {
            BuildManifest(CandidateStagingManifest.SelectedAssetPath());
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Opus 5 R2 Manifest Quest Review APK")]
        public static void BuildOpus5R2Manifest()
        {
            BuildManifest(Opus5R2ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Meter M2n5 Manifest Quest Review APK")]
        public static void BuildMeterM2n5Manifest()
        {
            BuildManifest(MeterM2n5ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Meter M2n7 Manifest Quest Review APK")]
        public static void BuildMeterM2n7Manifest()
        {
            BuildManifest(MeterM2n7ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Meter M2n8 Manifest Quest Review APK")]
        public static void BuildMeterM2n8Manifest()
        {
            BuildManifest(MeterM2n8ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Trend Monitor P1 Manifest Quest Review APK")]
        public static void BuildTrendMonitorP1Manifest()
        {
            BuildManifest(TrendMonitorP1ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Trend Monitor P2 Manifest Quest Review APK")]
        public static void BuildTrendMonitorP2Manifest()
        {
            BuildManifest(TrendMonitorP2ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Window Panel WP4 Candidate Quest Review APK")]
        public static void BuildWindowPanelWp4Candidate()
        {
            BuildManifest(WindowPanelWp3R2ManifestPath);
        }

        internal static string BuildManifest(string manifestPath)
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

            var manifest = CandidateStagingManifest.Load(manifestPath);
            V6ModelReplacementStagingBuilder.BuildCandidateManifest(manifestPath);
            RefinedModelReplacementValidator
                .ValidateCandidateManifest(manifestPath);
            Opus5R2CandidateMotionAudit.AuditManifest(manifestPath);

            var outputPath =
                $"Builds/QuestReview/AnalogInstrumentMR-" +
                $"{manifest.candidateId}-review-quest3.apk";
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            var options = new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = outputPath,
                target = BuildTarget.Android,
                subtarget = MetaQuestBuildSubtarget,
                options = BuildOptions.None,
                extraScriptingDefines = new[] { CandidateReviewDefine }
            };

            var previousFrameTimingStats = PlayerSettings.enableFrameTimingStats;
            var quarantined = false;
            var configurationCreated = false;
            PlayerSettings.enableFrameTimingStats = true;
            try
            {
                CreateCandidateReviewConfiguration(manifest);
                configurationCreated = true;
                quarantined = QuarantineDevAgentSettings();
                var report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                {
                    throw new InvalidOperationException(
                        $"Candidate {manifest.candidateId} review build failed: " +
                        $"{report.summary.result}; " +
                        $"{report.summary.totalErrors} error(s).");
                }

                Debug.Log(
                    $"Candidate {manifest.candidateId} Quest review APK " +
                    $"built: {outputPath}; {report.summary.totalSize} bytes; " +
                    $"define={CandidateReviewDefine}.");
                return outputPath;
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
                        DeleteCandidateReviewConfiguration();
                }
            }
        }

        private static void CreateCandidateReviewConfiguration(
            CandidateStagingManifest manifest)
        {
            if (File.Exists(CandidateReviewConfigurationPath))
            {
                throw new IOException(
                    "Candidate review configuration already exists: " +
                    CandidateReviewConfigurationPath);
            }

            var directory =
                Path.GetDirectoryName(CandidateReviewConfigurationPath);
            Directory.CreateDirectory(directory);
            var configuration = new CandidateReviewConfiguration
            {
                candidateId = manifest.candidateId,
                entries = manifest.entries.Select(entry =>
                    new CandidateReviewEntry
                    {
                        prefabName =
                            $"PF_Visual_{entry.model}_{entry.theme}",
                        resourcePath =
                            $"{manifest.candidateId}/{entry.theme}/Prefabs/" +
                            $"PF_Visual_{entry.model}_{entry.theme}"
                    }).ToArray()
            };
            File.WriteAllText(
                CandidateReviewConfigurationPath,
                JsonUtility.ToJson(configuration, true),
                new UTF8Encoding(false));
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        private static void DeleteCandidateReviewConfiguration()
        {
            if (!AssetDatabase.DeleteAsset(CandidateReviewConfigurationPath) &&
                File.Exists(CandidateReviewConfigurationPath))
            {
                throw new IOException(
                    "Could not remove generated candidate review " +
                    $"configuration: {CandidateReviewConfigurationPath}");
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        [Serializable]
        private sealed class CandidateReviewConfiguration
        {
            public string candidateId;
            public CandidateReviewEntry[] entries;
        }

        [Serializable]
        private sealed class CandidateReviewEntry
        {
            public string prefabName;
            public string resourcePath;
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
    }
}
