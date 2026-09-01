using System;
using System.IO;
using System.Security.Cryptography;
using MatsuMotoMeterAR.Instruments;
using Unity.Pipeline.Commands;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    public static class ProjectPipelineCommands
    {
        private const string TrendReviewPath =
            "Builds/Reports/production-TrendMonitor-composition-review.png";
        private const string MotionAuditPath =
            "Builds/Reports/instrument-motion-audit.md";
        private const string SignalAuditPath =
            "Builds/Reports/signal-visual-audit.md";
        private const string PerformanceGatePath =
            "Builds/Performance/" +
            "AnalogInstrumentMR-v0.2.0-perfgate-quest3.apk";

        private static string performanceGateStatus = "idle";
        private static string performanceGateMessage =
            "No Pipeline performance-gate build has been requested.";
        private static bool performanceGatePending;

        static ProjectPipelineCommands()
        {
            EditorApplication.update += ProcessQueuedPerformanceGateBuild;
        }

        [CliCommand(
            "matsu_render_trend_monitor_review",
            "Render the four-theme production Trend Monitor composition " +
            "review and return its artifact digest.",
            MainThreadRequired = true,
            Tags = new[] { "matsu/review" })]
        public static ProjectPipelineResult RenderTrendMonitorReview()
        {
            Opus5R2CandidateVisualReview
                .RunTrendMonitorCompositionReview();
            return Completed(
                "matsu_render_trend_monitor_review",
                "Rendered production Trend Monitor composition review.",
                TrendReviewPath);
        }

        [CliCommand(
            "matsu_audit_control_motion",
            "Run the project control-motion audit for every production " +
            "theme and return its report digest.",
            MainThreadRequired = true,
            Tags = new[] { "matsu/audit" })]
        public static ProjectPipelineResult AuditControlMotion()
        {
            InstrumentMotionAudit.Run();
            return Completed(
                "matsu_audit_control_motion",
                "Control-motion audit passed.",
                MotionAuditPath);
        }

        [CliCommand(
            "matsu_audit_signal_visuals",
            "Run the production signal-visual audit and return its report " +
            "digest.",
            MainThreadRequired = true,
            Tags = new[] { "matsu/audit" })]
        public static ProjectPipelineResult AuditSignalVisuals()
        {
            SignalVisualAudit.Run();
            return Completed(
                "matsu_audit_signal_visuals",
                "Signal-visual audit passed.",
                SignalAuditPath);
        }

        [CliCommand(
            "matsu_build_performance_gate",
            "Queue the project-specific Quest performance-gate APK build. " +
            "Requires confirm=true; use dry_run=true to inspect the plan.",
            MainThreadRequired = true,
            Tags = new[] { "matsu/build" })]
        public static ProjectPipelineResult QueuePerformanceGateBuild(
            [CliArg(
                "confirm",
                "Required to queue the APK build.")]
            bool confirm = false,
            [CliArg(
                "dry_run",
                "Return the build plan without starting a build.")]
            bool dryRun = false)
        {
            if (dryRun)
            {
                return Planned(
                    "matsu_build_performance_gate",
                    $"Would build the Android Quest performance gate to " +
                    $"{PerformanceGatePath}. Active target: " +
                    $"{EditorUserBuildSettings.activeBuildTarget}.",
                    PerformanceGatePath);
            }

            if (!confirm)
            {
                throw new InvalidOperationException(
                    "The performance-gate APK build requires confirm=true.");
            }

            if (performanceGateStatus == "queued" ||
                performanceGateStatus == "running")
            {
                throw new InvalidOperationException(
                    "A Pipeline performance-gate build is already active.");
            }

            performanceGateStatus = "queued";
            performanceGateMessage =
                "Quest performance-gate APK build queued.";
            performanceGatePending = true;
            return CurrentPerformanceGateResult();
        }

        [CliCommand(
            "matsu_build_performance_gate_status",
            "Read the state and artifact digest of the last Pipeline Quest " +
            "performance-gate build.",
            MainThreadRequired = true,
            Tags = new[] { "matsu/build" })]
        public static ProjectPipelineResult PerformanceGateBuildStatus()
        {
            return CurrentPerformanceGateResult();
        }

        private static void ProcessQueuedPerformanceGateBuild()
        {
            if (!performanceGatePending ||
                performanceGateStatus != "queued")
            {
                return;
            }

            performanceGatePending = false;
            performanceGateStatus = "running";
            performanceGateMessage =
                "Quest performance-gate APK build is running.";
            try
            {
                ConceptReleaseBuilder.BuildPerformanceGate();
                performanceGateStatus = "completed";
                performanceGateMessage =
                    "Quest performance-gate APK build completed.";
            }
            catch (Exception exception)
            {
                performanceGateStatus = "failed";
                performanceGateMessage = exception.Message;
                Debug.LogException(exception);
            }
        }

        private static ProjectPipelineResult CurrentPerformanceGateResult()
        {
            return Result(
                "matsu_build_performance_gate",
                performanceGateStatus != "failed",
                performanceGateStatus,
                performanceGateMessage,
                PerformanceGatePath,
                requireArtifact: performanceGateStatus == "completed");
        }

        private static ProjectPipelineResult Completed(
            string command,
            string message,
            string outputPath)
        {
            return Result(
                command,
                true,
                "completed",
                message,
                outputPath,
                requireArtifact: true);
        }

        private static ProjectPipelineResult Planned(
            string command,
            string message,
            string outputPath)
        {
            return Result(
                command,
                true,
                "dry-run",
                message,
                outputPath,
                requireArtifact: false);
        }

        private static ProjectPipelineResult Result(
            string command,
            bool success,
            string status,
            string message,
            string outputPath,
            bool requireArtifact)
        {
            var absolutePath = AbsoluteProjectPath(outputPath);
            var exists = File.Exists(absolutePath);
            if (requireArtifact && !exists)
            {
                throw new FileNotFoundException(
                    $"Expected Pipeline artifact was not created: " +
                    $"{outputPath}",
                    absolutePath);
            }

            return new ProjectPipelineResult
            {
                Success = success,
                Command = command,
                Status = status,
                Message = message,
                OutputPath = outputPath,
                ArtifactExists = exists,
                ArtifactBytes = exists
                    ? new FileInfo(absolutePath).Length
                    : 0L,
                ArtifactSha256 = exists
                    ? Sha256(absolutePath)
                    : null
            };
        }

        private static string AbsoluteProjectPath(string relativePath)
        {
            var projectPath = Path.GetFullPath(
                Path.Combine(Application.dataPath, ".."));
            return Path.GetFullPath(
                Path.Combine(projectPath, relativePath));
        }

        private static string Sha256(string path)
        {
            using var algorithm = SHA256.Create();
            using var stream = File.OpenRead(path);
            return BitConverter.ToString(
                    algorithm.ComputeHash(stream))
                .Replace("-", string.Empty)
                .ToLowerInvariant();
        }
    }

    [Serializable]
    public sealed class ProjectPipelineResult
    {
        public bool Success { get; set; }
        public string Command { get; set; }
        public string Status { get; set; }
        public string Message { get; set; }
        public string OutputPath { get; set; }
        public bool ArtifactExists { get; set; }
        public long ArtifactBytes { get; set; }
        public string ArtifactSha256 { get; set; }
    }
}
