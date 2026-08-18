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

        public static void RenderVisualReview()
        {
            Opus5R2CandidateVisualReview.RenderManifest(
                RequiredManifestPath());
        }

        public static void BuildQuestReview()
        {
            Opus5R2QuestReviewBuilder.BuildManifest(
                RequiredManifestPath());
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
