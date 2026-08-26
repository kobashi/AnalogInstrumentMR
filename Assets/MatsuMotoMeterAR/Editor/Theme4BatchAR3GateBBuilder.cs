using UnityEditor;

namespace MatsuMotoMeterAR.Editor
{
    /// <summary>
    /// Imports the R3 Throttle and PowerSlider into isolated staging and runs
    /// the existing formal structural validator.  The proposal atlas is not
    /// used here because its UV scale is still under review.
    /// </summary>
    internal static class Theme4BatchAR3GateBBuilder
    {
        private const string ManifestPath =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging/Theme4_P6_BatchA_R3_GateB/" +
            "candidate-source-manifest.json";

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build and Validate Batch A R3 Structural Candidate")]
        public static void BuildAndValidate()
        {
            V6ModelReplacementStagingBuilder.BuildCandidateManifest(ManifestPath);
            RefinedModelReplacementValidator.ValidateCandidateManifest(ManifestPath);
            Opus5R2CandidateMotionAudit.AuditManifest(ManifestPath);
        }
    }
}
