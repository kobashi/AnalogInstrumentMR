using System;
using System.Collections.Generic;
using System.IO;
using MatsuMotoMeterAR.Editor;
using NUnit.Framework;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class CandidateStagingManifestTests
    {
        private const string SourceFbx =
            "ArtSource/Blender/BrushUp/Opus5/KineticSafety/staging/fbx/" +
            "SM_MeterRound_KineticSafety_V6_Opus5_R2_Material.fbx";
        private const string SourceReport =
            "ArtSource/Blender/BrushUp/Opus5/KineticSafety/staging/fbx/" +
            "SM_MeterRound_KineticSafety_V6_Opus5_R2_Material.json";

        [Test]
        public void Load_AcceptsVerifiedR2Manifest()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/Opus5_R2.json");

            Assert.That(manifest.schemaVersion, Is.EqualTo(1));
            Assert.That(manifest.entries, Has.Length.EqualTo(3));
        }

        [Test]
        public void Load_AcceptsMeterM2n7Manifest()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/Meter_M2n7.json");

            Assert.That(manifest.schemaVersion, Is.EqualTo(2));
            Assert.That(manifest.candidateId, Is.EqualTo("Meter_M2n7"));
            Assert.That(manifest.entries, Has.Length.EqualTo(3));
        }

        [Test]
        public void Load_AcceptsMeterM2n8Manifest()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/Meter_M2n8.json");

            Assert.That(manifest.schemaVersion, Is.EqualTo(2));
            Assert.That(manifest.candidateId, Is.EqualTo("Meter_M2n8"));
            Assert.That(manifest.entries, Has.Length.EqualTo(3));
        }

        [Test]
        public void Load_AcceptsTrendMonitorP2Manifest()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/TrendMonitor_P2.json");

            Assert.That(manifest.schemaVersion, Is.EqualTo(2));
            Assert.That(manifest.candidateId, Is.EqualTo("TrendMonitor_P2"));
            Assert.That(manifest.entries, Has.Length.EqualTo(3));
            Assert.That(manifest.entries[0].includedRevisions,
                Is.EqualTo(new[] { "P1", "P2" }));
            Assert.That(manifest.entries[2].revision, Is.EqualTo("P1"));
        }

        [TestCase("MAT_KineticSafety_V5_Readout", true)]
        [TestCase("MAT_KineticSafety_V6_Emissive", true)]
        [TestCase("MAT_KineticSafety_V5_Body", false)]
        [TestCase("MAT_KineticSafety_V5_Metal", false)]
        [TestCase("MAT_KineticSafety_V6_Gasket", false)]
        public void MaterialRoleMapping_MapsReadoutAndEmissiveOnly(
            string materialName,
            bool expectedEmissive)
        {
            Assert.That(
                V6ModelReplacementStagingBuilder
                    .IsEmissiveMaterialRole(materialName),
                Is.EqualTo(expectedEmissive));
        }

        [Test]
        public void ValidateDefinition_RejectsDuplicateIdentity()
        {
            var manifest = ValidManifest();
            manifest.entries = new[] { ValidEntry(), ValidEntry() };

            AssertProblemsContain(
                manifest,
                "Duplicate candidate entry: KineticSafety/MeterRound.");
        }

        [Test]
        public void Schema2GateB_RecordsUnresolvedCompositionWithoutRejectingCandidate()
        {
            var manifest = ValidSchema2Manifest(CandidateIntegrationStages.GateB);
            manifest.entries[0].includedRevisions = new[] { "D3" };
            manifest.entries[0].requiredRevisions = new[] { "D3" };

            Assert.That(manifest.ValidateDefinition(), Is.Empty);
            Assert.That(
                manifest.MissingRequiredRevisions(manifest.entries[0]),
                Is.EqualTo(new[] { "B2" }));
        }

        [Test]
        public void Schema2GateC_RejectsCandidateThatWouldDiscardRequiredBrushUp()
        {
            var manifest = ValidSchema2Manifest(CandidateIntegrationStages.GateC);
            manifest.entries[0].includedRevisions = new[] { "D3" };
            manifest.entries[0].requiredRevisions = new[] { "D3" };

            AssertProblemsContain(
                manifest,
                "cannot enter GateC; missing required revisions: B2");
        }

        [Test]
        public void Schema2GateC_AcceptsCombinedLineage()
        {
            var manifest = ValidSchema2Manifest(CandidateIntegrationStages.GateC);

            Assert.That(manifest.ValidateDefinition(), Is.Empty);
            Assert.That(
                manifest.MissingRequiredRevisions(manifest.entries[0]),
                Is.Empty);
        }

        [Test]
        public void TogglePolicy_RequiresD5AndForgeD10()
        {
            Assert.That(
                CandidateIntegrationPolicy.RequiredRevisions(
                    "OrbitalAnalog", "Toggle"),
                Is.EqualTo(new[] { "D5" }));
            Assert.That(
                CandidateIntegrationPolicy.RequiredRevisions(
                    "ForgeBrass", "Toggle"),
                Is.EqualTo(new[] { "D5", "D10" }));
            Assert.That(
                CandidateIntegrationPolicy.RequiredRevisions(
                    "KineticSafety", "Toggle"),
                Is.EqualTo(new[] { "D5" }));
        }

        [Test]
        public void GateCReadiness_EnumeratesLineageAndRequiredEvidence()
        {
            var manifest = ValidSchema2Manifest(CandidateIntegrationStages.GateC);
            manifest.gateCEvidence = CompleteEvidence("present");

            var checks = CandidateGateCReadiness.Evaluate(
                manifest,
                path => path == "present" || path == SourceReport);

            Assert.That(checks, Is.Not.Empty);
            Assert.That(checks, Has.All.Matches<CandidateGateCCheck>(check => check.Passed));
            Assert.That(
                checks,
                Has.Some.Matches<CandidateGateCCheck>(
                    check => check.Id == "quest-48-gate"));
            Assert.That(
                checks,
                Has.Some.Matches<CandidateGateCCheck>(
                    check => check.Id == "quest-64-stress"));
        }

        [Test]
        public void GateCReadiness_BlocksMissingRevisionAndVisualEvidence()
        {
            var manifest = ValidSchema2Manifest(CandidateIntegrationStages.GateB);
            manifest.entries[0].includedRevisions = new[] { "D3" };
            manifest.entries[0].requiredRevisions = new[] { "D3" };
            manifest.gateCEvidence = CompleteEvidence("present");
            manifest.gateCEvidence.fixedCameraVisualReview = string.Empty;

            var checks = CandidateGateCReadiness.Evaluate(manifest, _ => true);

            Assert.That(
                checks,
                Has.Some.Matches<CandidateGateCCheck>(
                    check => check.Id == "lineage:KineticSafety/MeterMedium" &&
                             !check.Passed && check.Detail.Contains("B2")));
            Assert.That(
                checks,
                Has.Some.Matches<CandidateGateCCheck>(
                    check => check.Id == "fixed-camera-visual-review" &&
                             !check.Passed));
        }

        [TestCase("UnknownTheme", "MeterRound", ".theme is unsupported")]
        [TestCase("KineticSafety", "UnknownModel", ".model is unsupported")]
        public void ValidateDefinition_RejectsUnsupportedIdentity(
            string theme,
            string model,
            string expected)
        {
            var manifest = ValidManifest();
            manifest.entries[0].theme = theme;
            manifest.entries[0].model = model;

            AssertProblemsContain(manifest, expected);
        }

        [Test]
        public void ValidateDefinition_RejectsTraversalOutsideCandidateTree()
        {
            var manifest = ValidManifest();
            manifest.entries[0].sourceFbx =
                "ArtSource/Blender/BrushUp/Opus5/../outside.fbx";

            AssertProblemsContain(
                manifest,
                "must stay under ArtSource/Blender/BrushUp/Opus5/");
        }

        [Test]
        public void ManifestSnapshotsMatch_DetectsByteDifference()
        {
            WithTemporaryDirectory(directory =>
            {
                var source = Path.Combine(directory, "source.json");
                var same = Path.Combine(directory, "same.json");
                var different = Path.Combine(directory, "different.json");
                File.WriteAllText(source, "{\"value\":1}\n");
                File.WriteAllText(same, "{\"value\":1}\n");
                File.WriteAllText(different, "{\"value\":2}\n");

                Assert.That(
                    RefinedModelReplacementValidator
                        .ManifestSnapshotsMatch(source, same),
                    Is.True);
                Assert.That(
                    RefinedModelReplacementValidator
                        .ManifestSnapshotsMatch(source, different),
                    Is.False);
            });
        }

        [Test]
        public void UnexpectedPrefabPaths_ReturnsOnlyUndeclaredPrefabs()
        {
            WithTemporaryDirectory(directory =>
            {
                var declared = Path.Combine(directory, "Declared.prefab")
                    .Replace('\\', '/');
                var stale = Path.Combine(directory, "Stale.prefab")
                    .Replace('\\', '/');
                File.WriteAllText(declared, "declared");
                File.WriteAllText(stale, "stale");

                var result = RefinedModelReplacementValidator
                    .UnexpectedPrefabPaths(
                        directory,
                        new HashSet<string>(StringComparer.Ordinal)
                        {
                            declared
                        });

                Assert.That(result, Is.EqualTo(new[] { stale }));
            });
        }

        private static CandidateStagingManifest ValidManifest()
        {
            return new CandidateStagingManifest
            {
                schemaVersion = 1,
                candidateId = "TestCandidate",
                entries = new[] { ValidEntry() }
            };
        }

        private static CandidateStagingManifest ValidSchema2Manifest(string stage)
        {
            var entry = ValidEntry();
            entry.model = "MeterMedium";
            entry.revision = "B2_D3";
            entry.includedRevisions = new[] { "B2", "D3" };
            entry.requiredRevisions = new[] { "B2", "D3" };
            return new CandidateStagingManifest
            {
                schemaVersion = 2,
                candidateId = "TestCombinedCandidate",
                integrationStage = stage,
                entries = new[] { entry }
            };
        }

        private static CandidateGateCEvidence CompleteEvidence(string path)
        {
            return new CandidateGateCEvidence
            {
                semanticUvAudit = path,
                fixedCameraVisualReview = path,
                motionAudit = path,
                unityStagingValidation = path,
                editModeTests = path,
                quest48Gate = path,
                quest64Stress = path,
                rollbackPlan = path
            };
        }

        private static CandidateStagingEntry ValidEntry()
        {
            return new CandidateStagingEntry
            {
                theme = "KineticSafety",
                model = "MeterRound",
                sourceFbx = SourceFbx,
                sourceReport = SourceReport
            };
        }

        private static void AssertProblemsContain(
            CandidateStagingManifest manifest,
            string expected)
        {
            Assert.That(
                string.Join("\n", manifest.ValidateDefinition()),
                Does.Contain(expected));
        }

        private static void WithTemporaryDirectory(Action<string> action)
        {
            var directory = Path.Combine(
                Path.GetTempPath(),
                $"analoginstrumentmr-manifest-tests-{Guid.NewGuid():N}");
            Directory.CreateDirectory(directory);
            try
            {
                action(directory);
            }
            finally
            {
                Directory.Delete(directory, true);
            }
        }
    }
}
