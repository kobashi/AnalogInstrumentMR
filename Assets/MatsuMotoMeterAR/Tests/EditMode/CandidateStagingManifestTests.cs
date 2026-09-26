using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using MatsuMotoMeterAR.Editor;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

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

        [Test]
        public void Load_AcceptsTrendMonitorThemeShapesT1Manifest()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/TrendMonitor_ThemeShapes_T1.json");

            Assert.That(manifest.schemaVersion, Is.EqualTo(2));
            Assert.That(
                manifest.integrationStage,
                Is.EqualTo(CandidateIntegrationStages.GateC));
            Assert.That(
                manifest.candidateId,
                Is.EqualTo("TrendMonitor_ThemeShapes_T1"));
            Assert.That(manifest.entries, Has.Length.EqualTo(3));
            Assert.That(
                manifest.entries[0].includedRevisions,
                Is.EqualTo(new[] { "P1", "P2", "ThemeShapes_T1" }));
            Assert.That(
                manifest.entries[2].revision,
                Is.EqualTo("ThemeShapes_T1"));
        }

        [Test]
        public void Load_AcceptsTrendMonitorTextureT1Manifest()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/TrendMonitor_Texture_T1.json");

            Assert.That(manifest.schemaVersion, Is.EqualTo(2));
            Assert.That(
                manifest.integrationStage,
                Is.EqualTo(CandidateIntegrationStages.GateC));
            Assert.That(manifest.candidateId,
                Is.EqualTo("TrendMonitor_Texture_T1"));
            Assert.That(manifest.entries, Has.Length.EqualTo(3));
            Assert.That(
                manifest.entries[0].includedRevisions,
                Is.EqualTo(new[]
                {
                    "P1", "P2", "ThemeShapes_T1", "Texture_T1"
                }));
            Assert.That(manifest.entries[2].revision,
                Is.EqualTo("Texture_T1"));
        }

        [Test]
        public void Load_AcceptsAudioModulesA1B1Manifest()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/AudioModules_A1_B1.json");

            Assert.That(manifest.schemaVersion, Is.EqualTo(2));
            Assert.That(manifest.candidateId, Is.EqualTo("AudioModules_A1_B1"));
            Assert.That(manifest.integrationStage,
                Is.EqualTo(CandidateIntegrationStages.GateC));
            Assert.That(manifest.entries, Has.Length.EqualTo(24));
        }

        [Test]
        public void Load_AcceptsSuperfineCandidateWithoutProductionRegistration()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/AudioModules_Superfine_S1.json");

            Assert.That(manifest.schemaVersion, Is.EqualTo(2));
            Assert.That(manifest.candidateId,
                Is.EqualTo("AudioModules_Superfine_S1"));
            Assert.That(manifest.integrationStage,
                Is.EqualTo(CandidateIntegrationStages.GateB));
            Assert.That(manifest.entries, Has.Length.EqualTo(6));
            Assert.That(manifest.entries.All(entry =>
                entry.theme == "Superfine"), Is.True);
        }

        [Test]
        public void Load_AcceptsSuperfineC2WithSequencerF1Replacement()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/AudioModules_Superfine_C2.json");

            Assert.That(manifest.integrationStage,
                Is.EqualTo(CandidateIntegrationStages.GateB));
            Assert.That(manifest.entries, Has.Length.EqualTo(6));
            var sequencer = manifest.entries.Single(entry =>
                entry.model == "AudioSequencer");
            Assert.That(sequencer.revision, Is.EqualTo("SFF1"));
            Assert.That(sequencer.includedRevisions,
                Is.EqualTo(new[] { "SFS1", "SFF1" }));
            Assert.That(sequencer.replacesCandidateId,
                Is.EqualTo("AudioModules_Superfine_S1"));
            Assert.That(sequencer.replacesRevision, Is.EqualTo("SFS1"));
        }

        [Test]
        public void Load_AcceptsSuperfineC3AudioS2Expansion()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/AudioModules_Superfine_C3.json");

            Assert.That(manifest.integrationStage,
                Is.EqualTo(CandidateIntegrationStages.GateB));
            Assert.That(manifest.entries, Has.Length.EqualTo(4));
            Assert.That(manifest.entries.Select(entry => entry.model),
                Is.EqualTo(new[]
                {
                    "AudioOscillator", "AudioNoise", "AudioDelay",
                    "AudioOutput"
                }));
            Assert.That(manifest.entries.All(entry =>
                entry.theme == "Superfine" &&
                entry.revision == "SFS2" &&
                entry.includedRevisions.SequenceEqual(new[] { "SFS2" }) &&
                entry.requiredRevisions.SequenceEqual(new[] { "SFS2" })),
                Is.True);
        }

        [Test]
        public void Load_AcceptsSuperfineNonAudioC4WithTwoF1Replacements()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/Superfine_NonAudio_C4.json");

            Assert.That(manifest.integrationStage,
                Is.EqualTo(CandidateIntegrationStages.GateB));
            Assert.That(manifest.candidateId,
                Is.EqualTo("Superfine_NonAudio_C4"));
            Assert.That(manifest.entries, Has.Length.EqualTo(14));
            Assert.That(manifest.entries.All(entry =>
                entry.theme == "Superfine"), Is.True);
            Assert.That(
                manifest.entries.Select(entry => entry.model).Distinct().Count(),
                Is.EqualTo(14));

            var replacements = manifest.entries.Where(entry =>
                entry.revision == "SFN2F1").ToArray();
            Assert.That(replacements.Select(entry => entry.model),
                Is.EquivalentTo(new[] { "WindowPanel", "Rotary" }));
            Assert.That(replacements.All(entry =>
                entry.includedRevisions.SequenceEqual(
                    new[] { "SFN2", "SFN2F1" }) &&
                entry.requiredRevisions.SequenceEqual(
                    new[] { "SFN2", "SFN2F1" })), Is.True);
        }

        [Test]
        public void Load_AcceptsAudioModuleExtensionManifestWithExplicitReplacements()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/AudioModules_Ext_A1_B1.json");

            Assert.That(manifest.schemaVersion, Is.EqualTo(2));
            Assert.That(manifest.candidateId,
                Is.EqualTo("AudioModules_Ext_A1_B1"));
            Assert.That(manifest.integrationStage,
                Is.EqualTo(CandidateIntegrationStages.GateC));
            Assert.That(manifest.entries, Has.Length.EqualTo(24));
            Assert.That(
                manifest.entries.Select(entry =>
                    $"{entry.theme}/{entry.model}").Distinct().Count(),
                Is.EqualTo(24));

            var replacements = manifest.entries.Where(entry =>
                !string.IsNullOrWhiteSpace(entry.replacesCandidateId)).ToArray();
            Assert.That(replacements, Has.Length.EqualTo(8));
            Assert.That(replacements.All(entry =>
                entry.model == "AudioLFO" ||
                entry.model == "AudioSequencer"), Is.True);
            Assert.That(replacements.All(entry =>
                entry.replacesCandidateId == "AudioModules_A1_B1"), Is.True);
        }

        [Test]
        public void CandidateManifestIds_AreUnique()
        {
            const string folder =
                "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests";
            var duplicates = AssetDatabase.FindAssets("t:TextAsset", new[] { folder })
                .Select(AssetDatabase.GUIDToAssetPath)
                .Where(path => path.EndsWith(
                    ".json", StringComparison.OrdinalIgnoreCase))
                .Select(path => JsonUtility.FromJson<CandidateStagingManifest>(
                    File.ReadAllText(path)))
                .Where(manifest => manifest != null &&
                                   !string.IsNullOrWhiteSpace(manifest.candidateId))
                .GroupBy(manifest => manifest.candidateId, StringComparer.Ordinal)
                .Where(group => group.Count() > 1)
                .Select(group => group.Key)
                .OrderBy(value => value, StringComparer.Ordinal)
                .ToArray();

            Assert.That(duplicates, Is.Empty);
        }

        [Test]
        public void ProductionAudioModuleModels_AreReadableForRuntimeUvRepair()
        {
            var manifest = CandidateStagingManifest.Load(
                "Assets/MatsuMotoMeterAR/Editor/" +
                "Opus5CandidateManifests/AudioModules_A1_B1.json");

            foreach (var entry in manifest.entries)
            {
                var path =
                    $"Assets/MatsuMotoMeterAR/Content/Themes/{entry.theme}/" +
                    $"Models/SM_{entry.model}_{entry.theme}.fbx";
                var importer = AssetImporter.GetAtPath(path) as ModelImporter;
                Assert.That(importer, Is.Not.Null, path);
                Assert.That(importer.isReadable, Is.True, path);
            }
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
        public void ValidateDefinition_RejectsPartialReplacementLineage()
        {
            var manifest = ValidSchema2Manifest(CandidateIntegrationStages.GateC);
            manifest.entries[0].replacesCandidateId = "AudioModules_A1_B1";

            AssertProblemsContain(
                manifest,
                "replacement lineage must provide both");
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

        [Test]
        public void GateCReadiness_AcceptsExplicitQuestDeferral()
        {
            var manifest = ValidSchema2Manifest(CandidateIntegrationStages.GateC);
            manifest.gateCEvidence = CompleteEvidence("present");
            manifest.gateCEvidence.quest48Gate = string.Empty;
            manifest.gateCEvidence.quest64Stress = string.Empty;
            manifest.gateCEvidence.questValidationDeferral = "deferred";

            var checks = CandidateGateCReadiness.Evaluate(
                manifest,
                path => path == "present" || path == "deferred" ||
                        path == SourceReport);

            Assert.That(checks, Has.All.Matches<CandidateGateCCheck>(
                check => check.Passed));
            Assert.That(
                checks,
                Has.Some.Matches<CandidateGateCCheck>(
                    check => check.Id == "quest-48-gate" &&
                             check.Detail == "DEFERRED: deferred"));
            Assert.That(
                CandidateGateCReadiness.BuildMarkdown(manifest, checks),
                Does.Contain("| quest-48-gate | DEFERRED |"));
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
        public void ValidateDefinition_AcceptsMachinedErgonomicsWindowPanel()
        {
            var manifest = ValidSchema2Manifest(CandidateIntegrationStages.GateB);
            manifest.entries[0].theme = "MachinedErgonomics";
            manifest.entries[0].model = "WindowPanel";
            manifest.entries[0].revision = "WP3";
            manifest.entries[0].includedRevisions = new[] { "WP3" };
            manifest.entries[0].requiredRevisions = new[] { "WP3" };

            Assert.That(manifest.ValidateDefinition(), Is.Empty);
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

        [Test]
        public void CrossCandidateDependencies_ReturnsOnlyOtherCandidateTrees()
        {
            const string current =
                "Assets/Root/CandidateStaging/Current";
            var result = RefinedModelReplacementValidator
                .CrossCandidateDependencies(
                    new[]
                    {
                        current + "/Resources/Current/Theme/Prefab.prefab",
                        current + "/Models/Theme/Model.fbx",
                        "Assets/Root/CandidateStaging/Old/Model.fbx",
                        "Assets/MatsuMotoMeterAR/Runtime/Audio/View.cs"
                    },
                    current);

            Assert.That(
                result,
                Is.EqualTo(new[]
                {
                    "Assets/Root/CandidateStaging/Old/Model.fbx"
                }));
        }

        [TestCase("AudioOscillator")]
        [TestCase("AudioNoise")]
        [TestCase("AudioLFO")]
        [TestCase("AudioSequencer")]
        [TestCase("AudioDelay")]
        [TestCase("AudioOutput")]
        [TestCase("AudioVca")]
        [TestCase("AudioMixer")]
        [TestCase("AudioFilter")]
        [TestCase("AudioEnvelope")]
        public void ProductionPromotion_ClassifiesEveryAudioModule(string model)
        {
            Assert.That(
                CandidateProductionPromoter.IsAudioModule(model),
                Is.True,
                "promotion classification");
            Assert.That(
                OrbitalAnalogUnityAssetBuilder.IsAudioModule(model),
                Is.True,
                "production prefab builder classification");
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
                questValidationDeferral = string.Empty,
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
