using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class WindowPanelQuestReviewBuilder
    {
        private const string OutputPath =
            "Builds/QuestReview/" +
            "AnalogInstrumentMR-WindowPanel-WP1-review-quest3.apk";
        private const string ReviewDefine =
            "ANALOGMR_WINDOW_PANEL_WP1_REVIEW";
        private const int MetaQuestBuildSubtarget = 6;
        private const string DevAgentSettingsPath =
            "Assets/Resources/DevAgentSettings.asset";
        private const string QuarantinedDevAgentSettingsPath =
            "Assets/MatsuMotoMeterAR/Editor/DevAgentSettings.local.asset";

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Window Panel/" +
            "Build WP1 Quest Review APK")]
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
                throw new InvalidOperationException(
                    "No enabled build scenes were found.");

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
            PlayerSettings.enableFrameTimingStats = true;
            var quarantined = false;
            try
            {
                quarantined = QuarantineDevAgentSettings();
                var report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                    throw new InvalidOperationException(
                        $"WP1 review build failed: {report.summary.result}; " +
                        $"{report.summary.totalErrors} error(s).");
                Debug.Log(
                    $"WP1 Quest review APK built: {OutputPath}; " +
                    $"{report.summary.totalSize} bytes; define={ReviewDefine}.");
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
            {
                throw new IOException(
                    "Review-build credential quarantine already exists: " +
                    QuarantinedDevAgentSettingsPath);
            }
            var error = AssetDatabase.MoveAsset(
                DevAgentSettingsPath,
                QuarantinedDevAgentSettingsPath);
            if (!string.IsNullOrEmpty(error))
                throw new IOException(
                    $"Could not quarantine development credentials: {error}");
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
