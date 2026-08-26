using UnityEditor;

namespace MatsuMotoMeterAR.Editor
{
    internal static class Theme4BatchBGateBBuilder
    {
        private const string ManifestPath =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging/Theme4_P6_BatchB_GateB/" +
            "candidate-source-manifest.json";

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build and Validate Phase 3 Batch B Structural Candidate")]
        public static void BuildAndValidate()
        {
            V6ModelReplacementStagingBuilder.BuildCandidateManifest(ManifestPath);
            RefinedModelReplacementValidator.ValidateCandidateManifest(ManifestPath);
        }
    }
}
