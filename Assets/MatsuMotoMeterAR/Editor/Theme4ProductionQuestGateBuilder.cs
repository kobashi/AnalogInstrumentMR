using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class Theme4ProductionQuestGateBuilder
    {
        internal const string OutputPath =
            "Builds/QuestReview/AnalogInstrumentMR-MachinedErgonomics-" +
            "production-gate-quest3.apk";
        internal const string PerformanceOutputPath =
            "Builds/Performance/AnalogInstrumentMR-MachinedErgonomics-" +
            "perfgate-quest3.apk";

        private const int MetaQuestBuildSubtarget = 6;
        private const string DevAgentSettingsPath =
            "Assets/Resources/DevAgentSettings.asset";
        private const string QuarantinedDevAgentSettingsPath =
            "Assets/MatsuMotoMeterAR/Editor/" +
            "DevAgentSettings.theme4-production-gate.local.asset";

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build Machined Ergonomics Production Gate APK")]
        public static void Build()
        {
            BuildTo(OutputPath, "production gate");
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build Machined Ergonomics Performance Gate APK")]
        public static void BuildPerformanceGate()
        {
            BuildTo(PerformanceOutputPath, "performance gate");
        }

        private static void BuildTo(string outputPath, string label)
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

            Theme4ProductionPromoter.Promote();
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            var options = new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = outputPath,
                target = BuildTarget.Android,
                subtarget = MetaQuestBuildSubtarget,
                options = BuildOptions.None
            };

            var previousFrameTimingStats = PlayerSettings.enableFrameTimingStats;
            var quarantined = false;
            PlayerSettings.enableFrameTimingStats = true;
            try
            {
                quarantined = QuarantineDevAgentSettings();
                var report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                    throw new InvalidOperationException(
                        $"Machined Ergonomics production gate build failed: " +
                        $"{report.summary.result}; " +
                        $"{report.summary.totalErrors} error(s).");
                Debug.Log(
                    $"Machined Ergonomics {label} APK built: " +
                    $"{outputPath}; {report.summary.totalSize} bytes.");
            }
            finally
            {
                PlayerSettings.enableFrameTimingStats = previousFrameTimingStats;
                if (quarantined)
                    RestoreDevAgentSettings();
            }
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
                DevAgentSettingsPath,
                QuarantinedDevAgentSettingsPath);
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
                QuarantinedDevAgentSettingsPath,
                DevAgentSettingsPath);
            if (!string.IsNullOrEmpty(error))
                throw new IOException(
                    "Could not restore credentials: " + error);
        }
    }
}
