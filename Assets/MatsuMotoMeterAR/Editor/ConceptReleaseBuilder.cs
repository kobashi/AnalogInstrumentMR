using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class ConceptReleaseBuilder
    {
        private const string Version = "0.2.0";
        private const string ReleaseName = "v0.2.0-concept.1";
        private const string OutputDirectory = "Builds/Release";
        private const int MetaQuestBuildSubtarget = 6;
        private const string DevAgentSettingsPath =
            "Assets/Resources/DevAgentSettings.asset";
        private const string QuarantinedDevAgentSettingsPath =
            "Assets/MatsuMotoMeterAR/Editor/DevAgentSettings.local.asset";

        [MenuItem("Tools/MatsuMotoMeterAR/Build Concept Release APK")]
        public static void Build()
        {
            BuildTo(
                $"{OutputDirectory}/AnalogInstrumentMR-{ReleaseName}-quest3.apk",
                "Concept release");
        }

        [MenuItem("Tools/MatsuMotoMeterAR/Build Performance Gate APK")]
        public static void BuildPerformanceGate()
        {
            BuildTo(
                "Builds/Performance/AnalogInstrumentMR-v0.2.0-perfgate-quest3.apk",
                "Performance gate");
        }

        [MenuItem("Tools/MatsuMotoMeterAR/Build Connection Parameter Review APK")]
        public static void BuildConnectionParameterReview()
        {
            BuildTo(
                "Builds/QuestReview/" +
                "AnalogInstrumentMR-ConnectionParameters-review-quest3.apk",
                "Connection parameter review");
        }

        private static void BuildTo(string outputPath, string label)
        {
            var scenes = EditorBuildSettings.scenes
                .Where(scene => scene.enabled)
                .Select(scene => scene.path)
                .ToArray();
            if (scenes.Length == 0)
                throw new InvalidOperationException("No enabled build scenes were found.");

            if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.Android)
            {
                throw new InvalidOperationException(
                    "The active build target must be Android / Meta Quest.");
            }

            if (PlayerSettings.bundleVersion != Version)
            {
                throw new InvalidOperationException(
                    $"Player version is {PlayerSettings.bundleVersion}; expected {Version}.");
            }

            var outputDirectory = Path.GetDirectoryName(outputPath);
            if (!string.IsNullOrEmpty(outputDirectory))
                Directory.CreateDirectory(outputDirectory);
            var options = new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = outputPath,
                target = BuildTarget.Android,
                subtarget = MetaQuestBuildSubtarget,
                options = BuildOptions.None
            };

            var previousFrameTimingStats = PlayerSettings.enableFrameTimingStats;
            PlayerSettings.enableFrameTimingStats = true;
            QuarantineDevAgentSettings();
            try
            {
                var report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                {
                    throw new InvalidOperationException(
                        $"Release build failed: {report.summary.result}; " +
                        $"{report.summary.totalErrors} error(s).");
                }

                Debug.Log(
                    $"{label} APK built: {outputPath}; " +
                    $"{report.summary.totalSize} bytes.");
            }
            finally
            {
                PlayerSettings.enableFrameTimingStats = previousFrameTimingStats;
                AssetDatabase.DeleteAsset(QuarantinedDevAgentSettingsPath);
            }
        }

        private static void QuarantineDevAgentSettings()
        {
            AssetDatabase.DeleteAsset(QuarantinedDevAgentSettingsPath);
            if (!File.Exists(DevAgentSettingsPath))
                return;

            var error = AssetDatabase.MoveAsset(
                DevAgentSettingsPath,
                QuarantinedDevAgentSettingsPath);
            if (!string.IsNullOrEmpty(error))
            {
                throw new InvalidOperationException(
                    $"Could not quarantine {DevAgentSettingsPath}: {error}");
            }
        }
    }
}
