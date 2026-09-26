using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Audio;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class AdjustableParameterTests
    {
        [Test]
        public void ControlDefaults_PreserveLegacyDetentCounts()
        {
            Assert.That(First(MockInstrumentKind.Lever).stepCount, Is.EqualTo(5));
            Assert.That(
                First(MockInstrumentKind.ThrottleLever).stepCount,
                Is.EqualTo(6));
            Assert.That(
                First(MockInstrumentKind.PowerSlider).stepCount,
                Is.EqualTo(11));
            Assert.That(
                First(MockInstrumentKind.RotaryKnob).stepCount,
                Is.EqualTo(0));
            Assert.That(
                First(MockInstrumentKind.ToggleSwitch).stepCount,
                Is.EqualTo(2));
            Assert.That(
                First(MockInstrumentKind.PushButton).stepCount,
                Is.EqualTo(2));
        }

        [Test]
        public void AudioDefaults_PreserveLegacyPrimaryMappings()
        {
            Assert.That(
                First(MockInstrumentKind.AudioNoise, 0.35f).value,
                Is.EqualTo(0.1355f).Within(0.0001f));
            Assert.That(
                First(MockInstrumentKind.AudioSequencer, 0.25f).value,
                Is.EqualTo(140f).Within(0.001f));
            Assert.That(
                First(MockInstrumentKind.AudioSequencer, 0.75f).value,
                Is.EqualTo(140f).Within(0.001f));
            Assert.That(
                First(MockInstrumentKind.AudioDelay, 0.5f).value,
                Is.EqualTo(0.385f).Within(0.0001f));
            Assert.That(
                First(MockInstrumentKind.AudioVca, 0.5f).value,
                Is.EqualTo(0.5f).Within(0.0001f));
            Assert.That(
                First(MockInstrumentKind.AudioMixer, 0.5f).value,
                Is.EqualTo(1f).Within(0.0001f));
            Assert.That(
                First(MockInstrumentKind.AudioFilter, 0.5f).value,
                Is.EqualTo(Mathf.Sqrt(80f * 12000f)).Within(0.001f));
            Assert.That(
                First(MockInstrumentKind.AudioEnvelope, 0.5f).value,
                Is.EqualTo(1f));
        }

        [Test]
        public void LogarithmicRange_UsesGeometricMidpoint()
        {
            var setting = new AdjustableParameterSetting
            {
                parameterId = "test",
                minimum = 20f,
                maximum = 2000f,
                stepCount = 0,
                scaleKind = (int)AdjustableParameterScale.Logarithmic
            };

            var value = AdjustableParameterPolicy.MapNormalized(0.5f, setting);

            Assert.That(value, Is.EqualTo(200f).Within(0.001f));
            Assert.That(
                AdjustableParameterPolicy.InverseMap(value, setting),
                Is.EqualTo(0.5f).Within(0.0001f));
        }

        [Test]
        public void SteppedRange_IncludesBothEndpoints()
        {
            var setting = new AdjustableParameterSetting
            {
                parameterId = "test",
                minimum = 0f,
                maximum = 1f,
                stepCount = 5
            };

            Assert.That(
                AdjustableParameterPolicy.MapNormalized(0.37f, setting),
                Is.EqualTo(0.25f).Within(0.0001f));
            Assert.That(
                AdjustableParameterPolicy.MapNormalized(1f, setting),
                Is.EqualTo(1f).Within(0.0001f));
        }

        [Test]
        public void SequencerStepRange_ControlsBoundsAndQuantization()
        {
            var settings = AdjustableParameterPolicy.NormalizeSettings(
                MockInstrumentKind.AudioSequencer,
                null,
                0.25f);
            var range = AdjustableParameterPolicy.Find(
                settings,
                AdjustableParameterPolicy.SequencerStepValueId);
            range.minimum = -0.5f;
            range.maximum = 0.5f;
            range.stepCount = 5;

            var values = ModularAudioParameterPolicy.NormalizeSequencerSteps(
                new[] { -1f, -0.12f, 0.38f, 1f },
                range);

            Assert.That(values[0], Is.EqualTo(-0.5f).Within(0.0001f));
            Assert.That(values[1], Is.EqualTo(0f).Within(0.0001f));
            Assert.That(values[2], Is.EqualTo(0.5f).Within(0.0001f));
            Assert.That(values[3], Is.EqualTo(0.5f).Within(0.0001f));
        }

        [Test]
        public void MotionRange_ChangesOutputAndDetentCount()
        {
            var root = new GameObject("MotionRangeTest");
            var part = new GameObject("Part").transform;
            part.SetParent(root.transform);
            try
            {
                var motion = root.AddComponent<MockInstrumentMotion>();
                motion.Configure(
                    MockInstrumentMotion.MotionKind.Lever,
                    part,
                    Vector3.forward,
                    45f,
                    0f);
                motion.ConfigureParameterRange(
                    0.2f,
                    0.8f,
                    4,
                    AdjustableParameterScale.Linear);
                motion.SetNormalizedValue(0.62f);

                Assert.That(motion.DetentCount, Is.EqualTo(4));
                Assert.That(motion.DetentIndex, Is.EqualTo(2));
                Assert.That(motion.OutputValue, Is.EqualTo(0.6f).Within(0.0001f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void AudioRuntime_AppliesPersistentNumericParameters()
        {
            var root = new GameObject("AudioParameterTest");
            var part = new GameObject("Part").transform;
            part.SetParent(root.transform);
            try
            {
                var motion = root.AddComponent<MockInstrumentMotion>();
                motion.Configure(
                    MockInstrumentMotion.MotionKind.Rotate,
                    part,
                    Vector3.forward,
                    360f,
                    0f);
                var runtime = root.AddComponent<ModularAudioModuleRuntime>();
                runtime.Configure(MockInstrumentKind.AudioDelay, motion);
                var settings = AdjustableParameterPolicy.NormalizeSettings(
                    MockInstrumentKind.AudioDelay,
                    null,
                    0.5f);
                var time = AdjustableParameterPolicy.Find(
                    settings,
                    AdjustableParameterPolicy.DelayTimeId);
                var feedback = AdjustableParameterPolicy.Find(
                    settings,
                    AdjustableParameterPolicy.DelayFeedbackId);
                var mix = AdjustableParameterPolicy.Find(
                    settings,
                    AdjustableParameterPolicy.DelayMixId);
                time.stepCount = 0;
                feedback.stepCount = 0;
                mix.stepCount = 0;
                time.value = 0.12f;
                feedback.value = 0.7f;
                mix.value = 0.4f;

                runtime.ApplyPersistentParameters(0, 0, null, settings);

                var delay = (ModularDelayNode)runtime.Node;
                Assert.That(delay.DelaySeconds, Is.EqualTo(0.12f).Within(0.0001f));
                Assert.That(delay.Feedback, Is.EqualTo(0.7f).Within(0.0001f));
                Assert.That(delay.Mix, Is.EqualTo(0.4f).Within(0.0001f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void VcaMixerFilterAndEnvelope_ApplyPersistentNumericParameters()
        {
            var vcaRoot = new GameObject("VcaParameterTest");
            var mixerRoot = new GameObject("MixerParameterTest");
            var filterRoot = new GameObject("FilterParameterTest");
            var envelopeRoot = new GameObject("EnvelopeParameterTest");
            try
            {
                var vca = vcaRoot.AddComponent<ModularAudioModuleRuntime>();
                vca.Configure(MockInstrumentKind.AudioVca, null);
                var vcaSettings = AdjustableParameterPolicy.NormalizeSettings(
                    MockInstrumentKind.AudioVca,
                    null,
                    0.5f);
                AdjustableParameterPolicy.Find(
                    vcaSettings,
                    AdjustableParameterPolicy.VcaLevelId).value = 0.25f;
                AdjustableParameterPolicy.Find(
                    vcaSettings,
                    AdjustableParameterPolicy.VcaGainId).value = 1.4f;
                vca.ApplyPersistentParameters(0, 0, null, vcaSettings);

                var vcaNode = (ModularVcaNode)vca.Node;
                Assert.That(vcaNode.ManualLevel,
                    Is.EqualTo(0.25f).Within(0.0001f));
                Assert.That(vcaNode.Gain,
                    Is.EqualTo(1.4f).Within(0.0001f));

                var mixer = mixerRoot.AddComponent<ModularAudioModuleRuntime>();
                mixer.Configure(MockInstrumentKind.AudioMixer, null);
                var mixerSettings = AdjustableParameterPolicy.NormalizeSettings(
                    MockInstrumentKind.AudioMixer,
                    null,
                    0.5f);
                AdjustableParameterPolicy.Find(
                    mixerSettings,
                    AdjustableParameterPolicy.MixerGainId).value = 1.25f;
                AdjustableParameterPolicy.Find(
                    mixerSettings,
                    AdjustableParameterPolicy.MixerLimitId).value = 0.7f;
                mixer.ApplyPersistentParameters(0, 0, null, mixerSettings);

                var mixerNode = (ModularMixerNode)mixer.Node;
                Assert.That(mixerNode.Gain,
                    Is.EqualTo(1.25f).Within(0.0001f));
                Assert.That(mixerNode.Limit,
                    Is.EqualTo(0.7f).Within(0.0001f));

                var filter = filterRoot.AddComponent<
                    ModularAudioModuleRuntime>();
                filter.Configure(MockInstrumentKind.AudioFilter, null);
                var filterSettings = AdjustableParameterPolicy
                    .NormalizeSettings(
                        MockInstrumentKind.AudioFilter,
                        null,
                        0.5f);
                AdjustableParameterPolicy.Find(
                    filterSettings,
                    AdjustableParameterPolicy.FilterCutoffId).value = 2400f;
                AdjustableParameterPolicy.Find(
                    filterSettings,
                    AdjustableParameterPolicy.FilterResonanceId).value = 0.65f;
                filter.ApplyPersistentParameters(0, 0, null, filterSettings);

                var filterNode = (ModularFilterNode)filter.Node;
                Assert.That(filterNode.Cutoff,
                    Is.EqualTo(2400f).Within(0.001f));
                Assert.That(filterNode.Resonance,
                    Is.EqualTo(0.65f).Within(0.0001f));

                var envelope = envelopeRoot.AddComponent<
                    ModularAudioModuleRuntime>();
                envelope.Configure(MockInstrumentKind.AudioEnvelope, null);
                var envelopeSettings = AdjustableParameterPolicy
                    .NormalizeSettings(
                        MockInstrumentKind.AudioEnvelope,
                        null,
                        0.5f);
                AdjustableParameterPolicy.Find(
                    envelopeSettings,
                    AdjustableParameterPolicy.EnvelopeGateId).value = 0f;
                AdjustableParameterPolicy.Find(
                    envelopeSettings,
                    AdjustableParameterPolicy.EnvelopeAttackId).value = 0.1f;
                AdjustableParameterPolicy.Find(
                    envelopeSettings,
                    AdjustableParameterPolicy.EnvelopeDecayId).value = 0.2f;
                AdjustableParameterPolicy.Find(
                    envelopeSettings,
                    AdjustableParameterPolicy.EnvelopeSustainId).value = 0.55f;
                AdjustableParameterPolicy.Find(
                    envelopeSettings,
                    AdjustableParameterPolicy.EnvelopeReleaseId).value = 0.4f;
                envelope.ApplyPersistentParameters(
                    0,
                    0,
                    null,
                    envelopeSettings);

                var envelopeNode = (ModularEnvelopeNode)envelope.Node;
                Assert.That(envelopeNode.ManualGate, Is.False);
                Assert.That(envelopeNode.AttackSeconds,
                    Is.EqualTo(0.1f).Within(0.0001f));
                Assert.That(envelopeNode.DecaySeconds,
                    Is.EqualTo(0.2f).Within(0.0001f));
                Assert.That(envelopeNode.SustainLevel,
                    Is.EqualTo(0.55f).Within(0.0001f));
                Assert.That(envelopeNode.ReleaseSeconds,
                    Is.EqualTo(0.4f).Within(0.0001f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(vcaRoot);
                UnityEngine.Object.DestroyImmediate(mixerRoot);
                UnityEngine.Object.DestroyImmediate(filterRoot);
                UnityEngine.Object.DestroyImmediate(envelopeRoot);
            }
        }

        [Test]
        public void LfoAndSequencer_ApplyPersistentGateLengths()
        {
            var lfoRoot = new GameObject("LfoGateLengthTest");
            var sequencerRoot = new GameObject("SequencerGateLengthTest");
            try
            {
                var lfo = lfoRoot.AddComponent<ModularAudioModuleRuntime>();
                lfo.Configure(MockInstrumentKind.AudioLfo, null);
                var lfoSettings = AdjustableParameterPolicy.NormalizeSettings(
                    MockInstrumentKind.AudioLfo,
                    null,
                    0.5f);
                AdjustableParameterPolicy.Find(
                    lfoSettings,
                    AdjustableParameterPolicy.LfoGateLengthId).value = 0.35f;
                lfo.ApplyPersistentParameters(0, 0, null, lfoSettings);

                var sequencer = sequencerRoot.AddComponent<
                    ModularAudioModuleRuntime>();
                sequencer.Configure(MockInstrumentKind.AudioSequencer, null);
                var sequencerSettings =
                    AdjustableParameterPolicy.NormalizeSettings(
                        MockInstrumentKind.AudioSequencer,
                        null,
                        0.25f);
                AdjustableParameterPolicy.Find(
                    sequencerSettings,
                    AdjustableParameterPolicy.SequencerGateLengthId).value =
                    0.65f;
                AdjustableParameterPolicy.Find(
                    sequencerSettings,
                    AdjustableParameterPolicy.SequencerPlaybackModeId).value =
                    1f;
                sequencer.ApplyPersistentParameters(
                    0,
                    0,
                    null,
                    sequencerSettings);

                Assert.That(((ModularLfoNode)lfo.Node).GateLength,
                    Is.EqualTo(0.35f).Within(0.0001f));
                Assert.That(((ModularSequencerNode)sequencer.Node).GateLength,
                    Is.EqualTo(0.65f).Within(0.0001f));
                Assert.That(
                    ((ModularSequencerNode)sequencer.Node).PlaybackMode,
                    Is.EqualTo(
                        ModularSequencerPlaybackMode.StepTrigger));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(lfoRoot);
                UnityEngine.Object.DestroyImmediate(sequencerRoot);
            }
        }

        [Test]
        public void SchemaNineMigration_CreatesParameterDefaultsFromPosition()
        {
            var placementId = Guid.NewGuid().ToString("D");
            var document = new PlacementDocument
            {
                schemaVersion = 9,
                placements = new List<PlacementRecord>
                {
                    new()
                    {
                        placementId = placementId,
                        anchorId = Guid.NewGuid().ToString("D"),
                        instrumentTypeId = "control.power_slider",
                        localOffset = SerializablePose.Identity,
                        normalizedValue = 0.7f
                    }
                }
            };

            var normalized = PlacementJsonCodec.Normalize(document);
            var record = normalized.placements[0];

            Assert.That(
                normalized.schemaVersion,
                Is.EqualTo(PlacementDocument.CurrentSchemaVersion));
            Assert.That(record.parameterSettings, Has.Count.EqualTo(1));
            Assert.That(record.parameterSettings[0].stepCount, Is.EqualTo(11));
            Assert.That(record.parameterSettings[0].value,
                Is.EqualTo(0.7f).Within(0.0001f));
        }

        private static AdjustableParameterSetting First(
            MockInstrumentKind kind,
            float normalizedValue = 0f)
        {
            return AdjustableParameterPolicy.NormalizeSettings(
                kind,
                null,
                normalizedValue)[0];
        }
    }
}
