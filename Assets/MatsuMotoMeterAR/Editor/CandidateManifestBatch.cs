using System;

namespace MatsuMotoMeterAR.Editor
{
    public static class CandidateManifestBatch
    {
        private const string ManifestEnvironmentVariable =
            "ANALOGMR_CANDIDATE_MANIFEST";

        public static void BuildValidateAndAudit()
        {
            var manifestPath = RequiredManifestPath();
            V6ModelReplacementStagingBuilder.BuildCandidateManifest(manifestPath);
            RefinedModelReplacementValidator.ValidateCandidateManifest(manifestPath);
            Opus5R2CandidateMotionAudit.AuditManifest(manifestPath);
        }

        public static void BuildOnly()
        {
            V6ModelReplacementStagingBuilder.BuildCandidateManifest(
                RequiredManifestPath());
        }

        public static void ValidateOnly()
        {
            RefinedModelReplacementValidator.ValidateCandidateManifest(
                RequiredManifestPath());
        }

        public static void AuditOnly()
        {
            Opus5R2CandidateMotionAudit.AuditManifest(
                RequiredManifestPath());
        }

        public static void RenderVisualReview()
        {
            Opus5R2CandidateVisualReview.RenderManifest(
                RequiredManifestPath());
        }

        public static void RenderShapeReview()
        {
            Opus5R2CandidateVisualReview.RenderCandidateOnlyManifest(
                RequiredManifestPath());
        }

        public static void RenderAudioModuleDisplayReview()
        {
            Opus5R2CandidateVisualReview.RenderAudioModuleDisplayManifest(
                RequiredManifestPath());
        }

        public static void RenderSuperfineComparison()
        {
            Opus5R2CandidateVisualReview.RenderSuperfineComparisonManifest(
                RequiredManifestPath());
        }

        public static void AuditSuperfineC1()
        {
            SuperfineCandidateC1Audit.Audit(RequiredManifestPath());
        }

        public static void AuditSuperfineNonAudioC4()
        {
            SuperfineNonAudioCandidateC4Audit.Audit(RequiredManifestPath());
        }

        public static void CompleteSuperfineNonAudioC4Evidence()
        {
            var manifestPath = RequiredManifestPath();
            SuperfineNonAudioCandidateC4Audit.Audit(manifestPath);
            Opus5R2CandidateVisualReview.RenderCandidateOnlyManifest(
                manifestPath);
            Opus5R2CandidateVisualReview.RenderSuperfineComparisonManifest(
                manifestPath);
        }

        public static void BuildQuestReview()
        {
            Opus5R2QuestReviewBuilder.BuildManifest(
                RequiredManifestPath());
        }

        public static void ReportGateCReadiness()
        {
            CandidateGateCReadiness.Report(RequiredManifestPath());
        }

        public static void PromoteProduction()
        {
            CandidateProductionPromoter.Promote(RequiredManifestPath());
        }

        private static string RequiredManifestPath()
        {
            var value = Environment.GetEnvironmentVariable(
                ManifestEnvironmentVariable);
            if (string.IsNullOrWhiteSpace(value))
            {
                throw new InvalidOperationException(
                    $"{ManifestEnvironmentVariable} must name a candidate " +
                    "manifest relative to the project root.");
            }
            return value.Replace('\\', '/');
        }
    }
}
