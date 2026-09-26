using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Audio;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;
using MatsuMotoMeterAR.Signals;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class ModularAudioGraphTests
    {
        [Test]
        public void PatchPolicy_AcceptsInitialAudioRoutesOnly()
        {
            Assert.That(ModularAudioPatchPolicy.CanConnect(
                    MockInstrumentKind.AudioOscillator,
                    MockInstrumentKind.AudioOutput,
                    "audio.out",
                    "audio.in",
                    ModularAudioPortDomain.Audio),
                Is.True);
            Assert.That(ModularAudioPatchPolicy.CanConnect(
                    MockInstrumentKind.AudioNoise,
                    MockInstrumentKind.AudioOutput,
                    "audio.out",
                    "audio.in",
                    ModularAudioPortDomain.Audio),
                Is.True);
            Assert.That(ModularAudioPatchPolicy.CanConnect(
                    MockInstrumentKind.AudioOscillator,
                    MockInstrumentKind.RoundMeter,
                    "audio.out",
                    "audio.in",
                    ModularAudioPortDomain.Audio),
                Is.False);
            Assert.That(ModularAudioPatchPolicy.CanConnect(
                    MockInstrumentKind.AudioLfo,
                    MockInstrumentKind.AudioOscillator,
                    "control.out",
                    "pitch.in",
                    ModularAudioPortDomain.Control),
                Is.True);
            Assert.That(ModularAudioPatchPolicy.CanConnect(
                    MockInstrumentKind.AudioLfo,
                    MockInstrumentKind.AudioOscillator,
                    "audio.out",
                    "fm.in",
                    ModularAudioPortDomain.Audio),
                Is.True);
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioLfo,
                    MockInstrumentKind.AudioOscillator,
                    out var sourcePort,
                    out var targetPort,
                    out var domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("control.out"));
            Assert.That(targetPort, Is.EqualTo("pitch.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Control));
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioOscillator,
                    MockInstrumentKind.AudioDelay,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("audio.out"));
            Assert.That(targetPort, Is.EqualTo("audio.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Audio));
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioDelay,
                    MockInstrumentKind.AudioOutput,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioLfo,
                    MockInstrumentKind.AudioDelay,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("control.out"));
            Assert.That(targetPort, Is.EqualTo("time.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Control));
            Assert.That(ModularAudioPatchPolicy.TryGetRoute(
                    MockInstrumentKind.AudioLfo,
                    MockInstrumentKind.AudioOscillator,
                    ModularAudioPortDomain.Audio,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("audio.out"));
            Assert.That(targetPort, Is.EqualTo("fm.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Audio));
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioLfo,
                    MockInstrumentKind.AudioSequencer,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("clock.out"));
            Assert.That(targetPort, Is.EqualTo("clock.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Clock));
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioSequencer,
                    MockInstrumentKind.AudioOscillator,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("control.out"));
            Assert.That(targetPort, Is.EqualTo("pitch.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Control));
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioLfo,
                    MockInstrumentKind.AudioEnvelope,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("gate.out"));
            Assert.That(targetPort, Is.EqualTo("gate.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Gate));
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioSequencer,
                    MockInstrumentKind.AudioLfo,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("trigger.out"));
            Assert.That(targetPort, Is.EqualTo("reset.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Trigger));
            Assert.That(ModularAudioPatchPolicy.CanConnect(
                    MockInstrumentKind.AudioOscillator,
                    MockInstrumentKind.AudioOutput,
                    "audio.out",
                    "audio.in",
                    ModularAudioPortDomain.Control),
                Is.False);
        }

        [Test]
        public void PatchPolicy_RoutesVcaMixerAndFilterDomains()
        {
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioOscillator,
                    MockInstrumentKind.AudioVca,
                    out var sourcePort,
                    out var targetPort,
                    out var domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("audio.out"));
            Assert.That(targetPort, Is.EqualTo("audio.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Audio));

            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioLfo,
                    MockInstrumentKind.AudioVca,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("control.out"));
            Assert.That(targetPort, Is.EqualTo("level.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Control));

            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioVca,
                    MockInstrumentKind.AudioMixer,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("audio.out"));
            Assert.That(targetPort, Is.EqualTo("audio.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Audio));

            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioMixer,
                    MockInstrumentKind.AudioOutput,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);

            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioOscillator,
                    MockInstrumentKind.AudioFilter,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("audio.out"));
            Assert.That(targetPort, Is.EqualTo("audio.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Audio));

            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioLfo,
                    MockInstrumentKind.AudioFilter,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("control.out"));
            Assert.That(targetPort, Is.EqualTo("cutoff.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Control));

            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioFilter,
                    MockInstrumentKind.AudioOutput,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("audio.out"));
            Assert.That(targetPort, Is.EqualTo("audio.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Audio));

            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioEnvelope,
                    MockInstrumentKind.AudioVca,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sourcePort, Is.EqualTo("control.out"));
            Assert.That(targetPort, Is.EqualTo("level.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Control));

            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioEnvelope,
                    MockInstrumentKind.AudioFilter,
                    out sourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(targetPort, Is.EqualTo("cutoff.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Control));
        }

        [Test]
        public void Vca_UsesManualLevelWithoutCvAndControlLevelWithCv()
        {
            var manualGraph = new ModularAudioGraph();
            var manualOscillator = manualGraph.AddNode(
                new ModularOscillatorNode
                {
                    Frequency = 440f,
                    Level = 0.2f
                });
            var manualVca = manualGraph.AddNode(new ModularVcaNode
            {
                ManualLevel = 0.4f,
                Gain = 1.5f
            });
            var manualOutput = manualGraph.AddNode(
                new ModularAudioOutputNode { Gain = 1f, Limit = 1f });
            Assert.That(manualGraph.ConnectAudio(
                manualOscillator, manualVca), Is.True);
            Assert.That(manualGraph.ConnectAudio(
                manualVca, manualOutput), Is.True);
            Assert.That(manualGraph.SetOutputNode(manualOutput), Is.True);
            Assert.That(manualGraph.Compile(), Is.True);
            var manualSamples = new float[480];
            Assert.That(manualGraph.Render(
                manualSamples, manualSamples.Length, 48000), Is.True);

            var sequencerNode = new ModularSequencerNode();
            for (var index = 0;
                 index < ModularAudioParameterPolicy.SequencerStepCapacity;
                 index++)
                sequencerNode.SetStepValue(index, 0.2f);
            var cvGraph = new ModularAudioGraph();
            var cvOscillator = cvGraph.AddNode(
                new ModularOscillatorNode
                {
                    Frequency = 440f,
                    Level = 0.2f
                });
            var sequencer = cvGraph.AddNode(sequencerNode);
            var cvNode = new ModularVcaNode
            {
                ManualLevel = 0.9f,
                Gain = 1.5f
            };
            var cvVca = cvGraph.AddNode(cvNode);
            var cvOutput = cvGraph.AddNode(
                new ModularAudioOutputNode { Gain = 1f, Limit = 1f });
            Assert.That(cvGraph.ConnectAudio(cvOscillator, cvVca), Is.True);
            Assert.That(cvGraph.Connect(
                sequencer,
                cvVca,
                ModularAudioPortDomain.Control,
                "control.out",
                "level.in"), Is.True);
            Assert.That(cvGraph.ConnectAudio(cvVca, cvOutput), Is.True);
            Assert.That(cvGraph.SetOutputNode(cvOutput), Is.True);
            Assert.That(cvGraph.Compile(), Is.True);
            var cvSamples = new float[480];
            Assert.That(cvGraph.Render(
                cvSamples, cvSamples.Length, 48000), Is.True);

            Assert.That(MaximumAbsolute(manualSamples),
                Is.EqualTo(0.12f).Within(0.002f));
            Assert.That(MaximumAbsolute(cvSamples),
                Is.EqualTo(0.06f).Within(0.002f));
            Assert.That(cvNode.IsControlDriven, Is.True);
        }

        [Test]
        public void Mixer_AppliesGainAndBoundsSummedInput()
        {
            var graph = new ModularAudioGraph();
            var first = graph.AddNode(new ModularOscillatorNode
            {
                Frequency = 440f,
                Level = 0.6f
            });
            var second = graph.AddNode(new ModularOscillatorNode
            {
                Frequency = 440f,
                Level = 0.6f
            });
            var mixer = graph.AddNode(new ModularMixerNode
            {
                Gain = 1f,
                Limit = 0.5f
            });
            var output = graph.AddNode(
                new ModularAudioOutputNode { Gain = 1f, Limit = 1f });
            Assert.That(graph.ConnectAudio(first, mixer), Is.True);
            Assert.That(graph.ConnectAudio(second, mixer), Is.True);
            Assert.That(graph.ConnectAudio(mixer, output), Is.True);
            Assert.That(graph.SetOutputNode(output), Is.True);
            Assert.That(graph.Compile(), Is.True);
            var samples = new float[480];
            Assert.That(graph.Render(
                samples, samples.Length, 48000), Is.True);

            Assert.That(MaximumAbsolute(samples),
                Is.EqualTo(0.5f).Within(0.0001f));
        }

        [Test]
        public void Filter_AttenuatesHighToneAndTracksCutoffControl()
        {
            var closedRms = MeasureFilteredToneRms(300f, 0f);
            var openRms = MeasureFilteredToneRms(10000f, 0f);
            Assert.That(openRms, Is.GreaterThan(0.05f));
            Assert.That(closedRms, Is.LessThan(openRms * 0.35f));

            var graph = new ModularAudioGraph();
            var oscillator = graph.AddNode(new ModularOscillatorNode
            {
                Frequency = 440f,
                Level = 0.2f
            });
            var sequencerNode = new ModularSequencerNode();
            for (var index = 0;
                 index < ModularAudioParameterPolicy.SequencerStepCapacity;
                 index++)
                sequencerNode.SetStepValue(index, 0.5f);
            var sequencer = graph.AddNode(sequencerNode);
            var filterNode = new ModularFilterNode
            {
                Cutoff = 1000f,
                Resonance = 0.35f
            };
            var filter = graph.AddNode(filterNode);
            var output = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.ConnectAudio(oscillator, filter), Is.True);
            Assert.That(graph.Connect(
                sequencer,
                filter,
                ModularAudioPortDomain.Control,
                "control.out",
                "cutoff.in"), Is.True);
            Assert.That(graph.ConnectAudio(filter, output), Is.True);
            Assert.That(graph.SetOutputNode(output), Is.True);
            Assert.That(graph.Compile(), Is.True);
            var samples = new float[512];
            Assert.That(graph.Render(samples, samples.Length, 48000), Is.True);

            Assert.That(filterNode.CurrentCutoff,
                Is.EqualTo(4000f).Within(0.01f));
            AssertFiniteBoundedAndNonSilent(samples, 0.851f);
        }

        [Test]
        public void Envelope_GateAndTriggerUseSampleAccurateAdsrSemantics()
        {
            var gateGraph = new ModularAudioGraph();
            var gateSource = gateGraph.AddNode(new ModularLfoNode
            {
                Waveform = ModularOscillatorWaveform.Square,
                Frequency = 20f,
                Depth = 1f
            });
            var gateEnvelopeNode = FastEnvelope();
            var gateEnvelope = gateGraph.AddNode(gateEnvelopeNode);
            var gateOutput = gateGraph.AddNode(new ModularAudioOutputNode());
            Assert.That(gateGraph.Connect(
                gateSource,
                gateEnvelope,
                ModularAudioPortDomain.Gate,
                "gate.out",
                "gate.in"), Is.True);
            Assert.That(gateGraph.Connect(
                gateEnvelope,
                gateOutput,
                ModularAudioPortDomain.Audio,
                "control.out",
                "audio.in"), Is.True);
            Assert.That(gateGraph.SetOutputNode(gateOutput), Is.True);
            Assert.That(gateGraph.Compile(), Is.True);
            var samples = new float[1024];
            Assert.That(gateGraph.Render(samples, samples.Length, 48000), Is.True);
            Assert.That(gateEnvelopeNode.LastBlockPeak,
                Is.GreaterThan(0.99f));
            Assert.That(gateEnvelopeNode.CurrentLevel,
                Is.EqualTo(0.6f).Within(0.001f));
            Assert.That(gateEnvelopeNode.Stage,
                Is.EqualTo(ModularEnvelopeStage.Sustain));

            Assert.That(gateGraph.Render(samples, samples.Length, 48000), Is.True);
            Assert.That(gateEnvelopeNode.CurrentLevel, Is.Zero);
            Assert.That(gateEnvelopeNode.Stage,
                Is.EqualTo(ModularEnvelopeStage.Idle));

            var triggerGraph = new ModularAudioGraph();
            var triggerSource = triggerGraph.AddNode(new ModularLfoNode
            {
                Waveform = ModularOscillatorWaveform.Square,
                Frequency = 20f,
                Depth = 1f
            });
            var triggerEnvelopeNode = FastEnvelope();
            var triggerEnvelope = triggerGraph.AddNode(triggerEnvelopeNode);
            var triggerOutput = triggerGraph.AddNode(
                new ModularAudioOutputNode());
            Assert.That(triggerGraph.Connect(
                triggerSource,
                triggerEnvelope,
                ModularAudioPortDomain.Trigger,
                "trigger.out",
                "trigger.in"), Is.True);
            Assert.That(triggerGraph.Connect(
                triggerEnvelope,
                triggerOutput,
                ModularAudioPortDomain.Audio,
                "control.out",
                "audio.in"), Is.True);
            Assert.That(triggerGraph.SetOutputNode(triggerOutput), Is.True);
            Assert.That(triggerGraph.Compile(), Is.True);
            Assert.That(triggerGraph.Render(
                samples,
                samples.Length,
                48000), Is.True);
            Assert.That(triggerEnvelopeNode.LastBlockPeak,
                Is.GreaterThan(0.99f));
            Assert.That(triggerEnvelopeNode.CurrentLevel, Is.Zero);
            Assert.That(triggerEnvelopeNode.Stage,
                Is.EqualTo(ModularEnvelopeStage.Idle));
        }

        [Test]
        public void Sequencer_GateAndTriggerOutputsDriveDiscreteInputs()
        {
            var gateGraph = new ModularAudioGraph();
            var sequencer = gateGraph.AddNode(new ModularSequencerNode
            {
                TempoBpm = 300f,
                GateLength = 0.25f
            });
            var envelopeNode = FastEnvelope();
            var envelope = gateGraph.AddNode(envelopeNode);
            var output = gateGraph.AddNode(new ModularAudioOutputNode());
            Assert.That(gateGraph.Connect(
                sequencer,
                envelope,
                ModularAudioPortDomain.Gate,
                ModularAudioPatchPolicy.GateOutputPortId,
                ModularAudioPatchPolicy.GateInputPortId), Is.True);
            Assert.That(gateGraph.Connect(
                envelope,
                output,
                ModularAudioPortDomain.Audio,
                ModularAudioPatchPolicy.ControlOutputPortId,
                ModularAudioPatchPolicy.AudioInputPortId), Is.True);
            Assert.That(gateGraph.SetOutputNode(output), Is.True);
            Assert.That(gateGraph.Compile(), Is.True);

            var samples = new float[1024];
            Assert.That(gateGraph.Render(samples, samples.Length, 48000),
                Is.True);
            Assert.That(envelopeNode.LastBlockPeak, Is.GreaterThan(0.99f));
            Assert.That(envelopeNode.CurrentLevel, Is.Zero);
            Assert.That(envelopeNode.Stage,
                Is.EqualTo(ModularEnvelopeStage.Idle));

            Assert.That(ModularAudioPatchPolicy.TryGetRouteFromPort(
                    MockInstrumentKind.AudioSequencer,
                    MockInstrumentKind.AudioEnvelope,
                    ModularAudioPatchPolicy.TriggerOutputPortId,
                    out var targetPort,
                    out var domain),
                Is.True);
            Assert.That(targetPort,
                Is.EqualTo(ModularAudioPatchPolicy.TriggerInputPortId));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Trigger));
        }

        [Test]
        public void PatchPolicy_SelectsAndCyclesPatchesForOnePlacement()
        {
            var first = AudioPatch("first", "osc", "out-a");
            var unrelated = AudioPatch("other", "noise", "out-b");
            var second = AudioPatch("second", "noise", "out-a");
            var connections = new List<AudioPatchConnectionRecord>
            {
                null,
                first,
                unrelated,
                second
            };

            Assert.That(ModularAudioPatchPolicy.SelectNext(
                connections, "out-a", null), Is.SameAs(first));
            Assert.That(ModularAudioPatchPolicy.SelectNext(
                connections, "out-a", "first"), Is.SameAs(second));
            Assert.That(ModularAudioPatchPolicy.SelectNext(
                connections, "out-a", "second"), Is.SameAs(first));
            Assert.That(ModularAudioPatchPolicy.SelectNext(
                connections, "out-a", "missing"), Is.SameAs(first));
        }

        [Test]
        public void PatchPolicy_CountsSourceAndTargetPatches()
        {
            var connections = new List<AudioPatchConnectionRecord>
            {
                AudioPatch("first", "osc", "out"),
                AudioPatch("second", "noise", "out"),
                AudioPatch("third", "osc", "other")
            };

            Assert.That(ModularAudioPatchPolicy.CountForPlacement(
                connections, "osc"), Is.EqualTo(2));
            Assert.That(ModularAudioPatchPolicy.CountForPlacement(
                connections, "out"), Is.EqualTo(2));
            Assert.That(ModularAudioPatchPolicy.CountForPlacement(
                connections, "missing"), Is.Zero);
        }

        [Test]
        public void PatchPolicy_DefaultsObservableSourceToAudioOutput()
        {
            var kinds = new[]
            {
                MockInstrumentKind.RoundMeter,
                MockInstrumentKind.TrendMonitor,
                MockInstrumentKind.WindowPanel
            };

            foreach (var kind in kinds)
            {
                var index = ModularAudioPatchPolicy
                    .GetDefaultPatchOutputIndex(kind);
                Assert.That(
                    ModularAudioPatchPolicy.GetSelectableOutputPortId(
                        kind,
                        index),
                    Is.EqualTo(ModularAudioPatchPolicy.AudioOutputPortId));
            }
        }

        [Test]
        public void PatchPolicy_ExposesAndRoutesObservableInstrumentOutputs()
        {
            Assert.That(ModularAudioPatchPolicy.GetSelectableOutputCount(
                MockInstrumentKind.RoundMeter), Is.EqualTo(3));
            Assert.That(ModularAudioPatchPolicy.GetSelectableOutputCount(
                MockInstrumentKind.TrendMonitor), Is.EqualTo(5));
            Assert.That(ModularAudioPatchPolicy.GetSelectableOutputCount(
                MockInstrumentKind.WindowPanel), Is.EqualTo(6));
            Assert.That(ModularAudioPatchPolicy.CycleSelectableOutput(
                MockInstrumentKind.TrendMonitor, 4, 1), Is.Zero);
            Assert.That(ModularAudioPatchPolicy.GetSelectableOutputCount(
                MockInstrumentKind.AudioLfo), Is.EqualTo(5));
            Assert.That(ModularAudioPatchPolicy.GetSelectableOutputCount(
                MockInstrumentKind.AudioSequencer), Is.EqualTo(3));
            Assert.That(ModularAudioPatchPolicy.GetSelectableOutputCount(
                MockInstrumentKind.PushButton), Is.EqualTo(3));
            Assert.That(ModularAudioPatchPolicy.GetSelectableOutputPortId(
                    MockInstrumentKind.AudioLfo,
                    ModularAudioPatchPolicy.CycleSelectableOutput(
                        MockInstrumentKind.AudioLfo, 1, 1)),
                Is.EqualTo(ModularAudioPatchPolicy.GateOutputPortId));
            Assert.That(ModularAudioPatchPolicy.SupportsSignalRole(
                MockInstrumentKind.AudioLfo), Is.False);
            Assert.That(ModularAudioPatchPolicy.SupportsSignalRole(
                MockInstrumentKind.TrendMonitor), Is.True);
            Assert.That(ModularAudioPatchPolicy.SupportsSignalRole(
                MockInstrumentKind.PushButton), Is.True);

            Assert.That(ModularAudioPatchPolicy.TryGetRouteFromPort(
                    MockInstrumentKind.TrendMonitor,
                    MockInstrumentKind.AudioOscillator,
                    "slope.out",
                    out var targetPort,
                    out var domain),
                Is.True);
            Assert.That(targetPort, Is.EqualTo("pitch.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Control));

            Assert.That(ModularAudioPatchPolicy.TryGetRouteFromPort(
                    MockInstrumentKind.WindowPanel,
                    MockInstrumentKind.AudioOutput,
                    "audio.out",
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(targetPort, Is.EqualTo("audio.in"));
            Assert.That(domain, Is.EqualTo(ModularAudioPortDomain.Audio));
            Assert.That(ModularAudioPatchPolicy.TryGetRouteFromPort(
                    MockInstrumentKind.WindowPanel,
                    MockInstrumentKind.AudioOutput,
                    "energy.out",
                    out _,
                    out _),
                Is.False);

            Assert.That(ModularAudioPatchPolicy.TryGetRouteFromPort(
                    MockInstrumentKind.AudioLfo,
                    MockInstrumentKind.AudioSequencer,
                    "trigger.out",
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(targetPort, Is.EqualTo("trigger.in"));
            Assert.That(domain,
                Is.EqualTo(ModularAudioPortDomain.Trigger));
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.PushButton,
                    MockInstrumentKind.AudioSequencer,
                    out var buttonSourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(buttonSourcePort, Is.EqualTo("trigger.out"));
            Assert.That(targetPort, Is.EqualTo("trigger.in"));
            Assert.That(domain,
                Is.EqualTo(ModularAudioPortDomain.Trigger));
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.Lever,
                    MockInstrumentKind.AudioOscillator,
                    out var leverSourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(leverSourcePort, Is.EqualTo("control.out"));
            Assert.That(targetPort, Is.EqualTo("pitch.in"));
            Assert.That(domain,
                Is.EqualTo(ModularAudioPortDomain.Control));
            Assert.That(ModularAudioPatchPolicy.TryGetRouteFromPort(
                    MockInstrumentKind.RotaryKnob,
                    MockInstrumentKind.AudioLfo,
                    "control.out",
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(targetPort, Is.EqualTo("rate.in"));
            Assert.That(domain,
                Is.EqualTo(ModularAudioPortDomain.Control));
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.WindowPanel,
                    MockInstrumentKind.AudioSequencer,
                    out var panelSourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(panelSourcePort, Is.EqualTo("trigger.out"));
            Assert.That(targetPort, Is.EqualTo("trigger.in"));
            Assert.That(domain,
                Is.EqualTo(ModularAudioPortDomain.Trigger));
            Assert.That(ModularAudioPatchPolicy.GetDefaultPatchOutputIndex(
                    MockInstrumentKind.WindowPanel,
                    MockInstrumentKind.AudioSequencer),
                Is.EqualTo(4));
            foreach (var uiKind in new[]
                     {
                         MockInstrumentKind.RoundMeter,
                         MockInstrumentKind.TrendMonitor,
                         MockInstrumentKind.WindowPanel
                     })
            {
                Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                        uiKind,
                        MockInstrumentKind.AudioSequencer,
                        out var uiSourcePort,
                        out var uiTargetPort,
                        out var uiDomain),
                    Is.True);
                Assert.That(uiSourcePort, Is.EqualTo("trigger.out"));
                Assert.That(uiTargetPort, Is.EqualTo("trigger.in"));
                Assert.That(uiDomain,
                    Is.EqualTo(ModularAudioPortDomain.Trigger));
            }
            Assert.That(ModularAudioPatchPolicy.TryGetDefaultRoute(
                    MockInstrumentKind.AudioSequencer,
                    MockInstrumentKind.AudioSequencer,
                    out var sequencerSourcePort,
                    out targetPort,
                    out domain),
                Is.True);
            Assert.That(sequencerSourcePort, Is.EqualTo("trigger.out"));
            Assert.That(targetPort, Is.EqualTo("trigger.in"));
            Assert.That(domain,
                Is.EqualTo(ModularAudioPortDomain.Trigger));
        }

        [Test]
        public void ParameterPolicy_NormalizesAndCyclesEditableValues()
        {
            Assert.That(ModularAudioParameterPolicy.SupportsEditing(
                MockInstrumentKind.AudioOscillator), Is.True);
            Assert.That(ModularAudioParameterPolicy.SupportsEditing(
                MockInstrumentKind.AudioSequencer), Is.True);
            Assert.That(ModularAudioParameterPolicy.SupportsEditing(
                MockInstrumentKind.AudioDelay), Is.True);
            Assert.That(ModularAudioParameterPolicy.SupportsEditing(
                MockInstrumentKind.AudioOutput), Is.True);
            Assert.That(ModularAudioParameterPolicy.CycleWaveform(
                    (int)ModularOscillatorWaveform.Square,
                    1),
                Is.EqualTo((int)ModularOscillatorWaveform.Sine));
            Assert.That(ModularAudioParameterPolicy.CycleNoiseColor(
                    (int)ModularNoiseColor.White,
                    -1),
                Is.EqualTo((int)ModularNoiseColor.Brown));
            Assert.That(ModularAudioParameterPolicy.CycleStepIndex(
                7, 8, 1), Is.Zero);
            Assert.That(ModularAudioParameterPolicy.AdjustStepValue(
                0.98f, 1), Is.EqualTo(1f));
            Assert.That(ModularAudioParameterPolicy.NormalizeStepValue(
                0.26f), Is.EqualTo(0.25f).Within(0.0001f));
        }

        [Test]
        public void PatchRuntime_RebuildsOutputOnlyWhenTopologyChanges()
        {
            var oscillatorRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOscillator,
                Pose.identity);
            var noiseRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioNoise,
                Pose.identity);
            var outputRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOutput,
                Pose.identity);
            try
            {
                var oscillator = oscillatorRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var noise = noiseRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var output = outputRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var player = outputRoot.GetComponentInChildren<
                    ModularAudioGraphPlayer>(true);
                var modules = new Dictionary<string, ModularAudioModuleRuntime>
                {
                    ["osc"] = oscillator,
                    ["noise"] = noise,
                    ["out"] = output
                };
                var outputs = new Dictionary<string, ModularAudioGraphPlayer>
                {
                    ["out"] = player
                };
                var connections = new List<AudioPatchConnectionRecord>
                {
                    new()
                    {
                        connectionId = "osc-out",
                        sourcePlacementId = "osc",
                        targetPlacementId = "out"
                    },
                    new()
                    {
                        connectionId = "noise-out",
                        sourcePlacementId = "noise",
                        targetPlacementId = "out"
                    }
                };
                var runtime = new ModularAudioPatchRuntime();
                Assert.That(runtime.Refresh(connections, modules, outputs),
                    Is.True);
                Assert.That(runtime.AppliedConnectionCount, Is.EqualTo(2));
                var appliedGraph = player.Graph;
                Assert.That(runtime.Refresh(connections, modules, outputs),
                    Is.False);
                Assert.That(player.Graph, Is.SameAs(appliedGraph));

                var samples = new float[512];
                Assert.That(player.RenderForValidation(
                    samples,
                    samples.Length), Is.True);
                AssertFiniteBoundedAndNonSilent(samples, 0.851f);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(oscillatorRoot);
                UnityEngine.Object.DestroyImmediate(noiseRoot);
                UnityEngine.Object.DestroyImmediate(outputRoot);
            }
        }

        [TestCase(
            ModularAudioPortDomain.Control,
            "control.out",
            "pitch.in")]
        [TestCase(
            ModularAudioPortDomain.Audio,
            "audio.out",
            "fm.in")]
        public void PatchRuntime_BuildsLfoChainIntoAudioOutput(
            ModularAudioPortDomain modulationDomain,
            string sourcePortId,
            string targetPortId)
        {
            var lfoRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioLfo,
                Pose.identity);
            var oscillatorRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOscillator,
                Pose.identity);
            var outputRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOutput,
                Pose.identity);
            try
            {
                var lfo = lfoRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var oscillator = oscillatorRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var output = outputRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var player = outputRoot.GetComponentInChildren<
                    ModularAudioGraphPlayer>(true);
                var modules = new Dictionary<string, ModularAudioModuleRuntime>
                {
                    ["lfo"] = lfo,
                    ["osc"] = oscillator,
                    ["out"] = output
                };
                var outputs = new Dictionary<string, ModularAudioGraphPlayer>
                {
                    ["out"] = player
                };
                var connections = new List<AudioPatchConnectionRecord>
                {
                    new()
                    {
                        connectionId = "lfo-osc",
                        sourcePlacementId = "lfo",
                        targetPlacementId = "osc",
                        sourcePortId = sourcePortId,
                        targetPortId = targetPortId,
                        portDomain = (int)modulationDomain
                    },
                    AudioPatch("osc-out", "osc", "out")
                };

                var runtime = new ModularAudioPatchRuntime();
                Assert.That(runtime.Refresh(connections, modules, outputs),
                    Is.True);
                Assert.That(runtime.AppliedConnectionCount, Is.EqualTo(2));
                Assert.That(player.Graph.NodeCount, Is.EqualTo(3));
                Assert.That(player.Graph.ConnectionCount, Is.EqualTo(2));
                Assert.That(player.Graph.IsCompiled, Is.True);
                var samples = new float[512];
                Assert.That(player.RenderForValidation(
                    samples,
                    samples.Length), Is.True);
                AssertFiniteBoundedAndNonSilent(samples, 0.851f);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(lfoRoot);
                UnityEngine.Object.DestroyImmediate(oscillatorRoot);
                UnityEngine.Object.DestroyImmediate(outputRoot);
            }
        }

        [Test]
        public void PatchRuntime_BuildsExternalClockSequencerChain()
        {
            var lfoRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioLfo,
                Pose.identity);
            var sequencerRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioSequencer,
                Pose.identity);
            var oscillatorRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOscillator,
                Pose.identity);
            var outputRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOutput,
                Pose.identity);
            try
            {
                var lfo = lfoRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var sequencer = sequencerRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var oscillator = oscillatorRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var output = outputRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                ((ModularLfoNode)lfo.Node).Waveform =
                    ModularOscillatorWaveform.Square;
                ((ModularLfoNode)lfo.Node).Frequency = 20f;
                var player = outputRoot.GetComponentInChildren<
                    ModularAudioGraphPlayer>(true);
                var modules = new Dictionary<string, ModularAudioModuleRuntime>
                {
                    ["lfo"] = lfo,
                    ["seq"] = sequencer,
                    ["osc"] = oscillator,
                    ["out"] = output
                };
                var outputs = new Dictionary<string, ModularAudioGraphPlayer>
                {
                    ["out"] = player
                };
                var connections = new List<AudioPatchConnectionRecord>
                {
                    Patch(
                        "lfo-seq",
                        "lfo",
                        "seq",
                        "clock.out",
                        "clock.in",
                        ModularAudioPortDomain.Clock),
                    Patch(
                        "seq-osc",
                        "seq",
                        "osc",
                        "control.out",
                        "pitch.in",
                        ModularAudioPortDomain.Control),
                    AudioPatch("osc-out", "osc", "out")
                };

                var runtime = new ModularAudioPatchRuntime();
                Assert.That(runtime.Refresh(connections, modules, outputs),
                    Is.True);
                Assert.That(runtime.AppliedConnectionCount, Is.EqualTo(3));
                Assert.That(player.Graph.NodeCount, Is.EqualTo(4));
                Assert.That(player.Graph.ConnectionCount, Is.EqualTo(3));
                Assert.That(player.Graph.IsCompiled, Is.True);
                var samples = new float[1024];
                for (var index = 0; index < 4; index++)
                {
                    Assert.That(player.RenderForValidation(
                        samples,
                        samples.Length), Is.True);
                }
                var sequencerNode = (ModularSequencerNode)sequencer.Node;
                Assert.That(sequencerNode.UsesExternalClock, Is.True);
                Assert.That(sequencerNode.CurrentStep, Is.GreaterThan(0));
                AssertFiniteBoundedAndNonSilent(samples, 0.851f);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(lfoRoot);
                UnityEngine.Object.DestroyImmediate(sequencerRoot);
                UnityEngine.Object.DestroyImmediate(oscillatorRoot);
                UnityEngine.Object.DestroyImmediate(outputRoot);
            }
        }

        [Test]
        public void Factory_CreatesPlacementReadyModuleKindsInEveryTheme()
        {
            var kinds = new[]
            {
                MockInstrumentKind.AudioOscillator,
                MockInstrumentKind.AudioNoise,
                MockInstrumentKind.AudioLfo,
                MockInstrumentKind.AudioSequencer,
                MockInstrumentKind.AudioDelay,
                MockInstrumentKind.AudioVca,
                MockInstrumentKind.AudioMixer,
                MockInstrumentKind.AudioFilter,
                MockInstrumentKind.AudioEnvelope,
                MockInstrumentKind.AudioOutput,
                MockInstrumentKind.RoundMeter,
                MockInstrumentKind.RoundMeterMedium,
                MockInstrumentKind.RoundMeterLarge,
                MockInstrumentKind.WindowMeter,
                MockInstrumentKind.TrendMonitor,
                MockInstrumentKind.WindowPanel,
                MockInstrumentKind.Lever,
                MockInstrumentKind.ToggleSwitch,
                MockInstrumentKind.RotaryKnob,
                MockInstrumentKind.PushButton,
                MockInstrumentKind.ThrottleLever,
                MockInstrumentKind.PowerSlider
            };
            foreach (var kind in kinds)
            {
                for (var themeIndex = 0;
                     themeIndex < MockInstrumentThemeCatalog.Count;
                     themeIndex++)
                {
                    var root = MockInstrumentFactory.Create(
                        kind,
                        Pose.identity,
                        theme: (MockInstrumentTheme)themeIndex);
                    try
                    {
                        var contract = root
                            .GetComponent<InstrumentGreyboxContract>();
                        var module = contract.Logic
                            .GetComponent<ModularAudioModuleRuntime>();
                        Assert.That(module, Is.Not.Null, $"{themeIndex}/{kind}");
                        Assert.That(module.Motion,
                            Is.SameAs(contract.InstrumentInteraction.Motion));
                        Assert.That(module.Node, Is.Not.Null);
                        var player = contract.AudioSocket
                            .GetComponent<ModularAudioGraphPlayer>();
                        Assert.That(player != null,
                            Is.EqualTo(kind == MockInstrumentKind.AudioOutput));
                        if (player != null)
                        {
                            Assert.That(player.Source.spatialBlend, Is.EqualTo(1f));
                            Assert.That(player.Source.dopplerLevel, Is.Zero);
                            Assert.That(player.Graph.IsCompiled, Is.True);
                        }
                    }
                    finally
                    {
                        UnityEngine.Object.DestroyImmediate(root);
                    }
                }
            }
        }

        [Test]
        public void ModulePreview_HasNoRuntimeOrAudioSource()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOutput,
                Pose.identity,
                preview: true);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                Assert.That(contract.Logic
                    .GetComponent<ModularAudioModuleRuntime>(), Is.Null);
                Assert.That(contract.AudioSocket
                    .GetComponent<ModularAudioGraphPlayer>(), Is.Null);
                Assert.That(contract.AudioSocket
                    .GetComponent<AudioSource>(), Is.Null);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void OutputPlacement_CanRenderPatchedOscillatorThrough3DPlayer()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOutput,
                Pose.identity);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var player = contract.AudioSocket
                    .GetComponent<ModularAudioGraphPlayer>();
                var oscillator = player.Graph.AddNode(
                    new ModularOscillatorNode
                    {
                        Frequency = 440f,
                        Level = 0.25f
                    });
                Assert.That(player.Graph.ConnectAudio(oscillator, 0), Is.True);
                Assert.That(player.Graph.Compile(), Is.True);
                var samples = new float[512];
                Assert.That(
                    player.RenderForValidation(samples, samples.Length),
                    Is.True);
                AssertFiniteBoundedAndNonSilent(samples, 0.851f);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void GlobalAudioOff_SkipsGraphAndClearsOutputBuffer()
        {
            var previous = GlobalAudioSettings.ModularAudioEnabled;
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOutput,
                Pose.identity);
            try
            {
                var player = root.GetComponent<InstrumentGreyboxContract>()
                    .AudioSocket.GetComponent<ModularAudioGraphPlayer>();
                var oscillator = player.Graph.AddNode(
                    new ModularOscillatorNode
                    {
                        Frequency = 440f,
                        Level = 0.25f
                    });
                Assert.That(player.Graph.ConnectAudio(oscillator, 0), Is.True);
                Assert.That(player.Graph.Compile(), Is.True);

                GlobalAudioSettings.ModularAudioEnabled = false;
                var samples = new float[256];
                for (var index = 0; index < samples.Length; index++)
                    samples[index] = 1f;

                Assert.That(
                    player.RenderForValidation(samples, samples.Length),
                    Is.False);
                Assert.That(samples, Is.All.EqualTo(0f));
            }
            finally
            {
                GlobalAudioSettings.ModularAudioEnabled = previous;
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void ModuleParameterSurvivesThemeRebinding()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOscillator,
                Pose.identity);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                contract.InstrumentInteraction.SetNormalizedValue(0.75f);
                Assert.That(
                    MockInstrumentFactory.ApplyTheme(
                        root,
                        MockInstrumentTheme.ForgeBrass),
                    Is.True);
                Assert.That(contract.InstrumentInteraction.NormalizedValue,
                    Is.EqualTo(0.75f));
                var oscillator = (ModularOscillatorNode)contract.Logic
                    .GetComponent<ModularAudioModuleRuntime>().Node;
                Assert.That(oscillator.Frequency,
                    Is.EqualTo(55f * Mathf.Pow(2f, 3.75f)).Within(0.001f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void TypedPorts_RequireOutputToInputInTheSameDomain()
        {
            var audioOutput = new ModularAudioPort(
                "audio.out",
                ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Output);
            var audioInput = new ModularAudioPort(
                "audio.in",
                ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Input);
            var controlInput = new ModularAudioPort(
                "pitch.in",
                ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Input);

            Assert.That(
                ModularAudioPort.CheckConnection(audioOutput, audioInput),
                Is.EqualTo(ModularAudioPortCompatibility.Compatible));
            Assert.That(
                ModularAudioPort.CheckConnection(audioOutput, controlInput),
                Is.EqualTo(ModularAudioPortCompatibility.DomainMismatch));
            Assert.That(
                ModularAudioPort.CheckConnection(audioInput, audioInput),
                Is.EqualTo(ModularAudioPortCompatibility.SourceMustBeOutput));
        }

        [Test]
        public void PortCatalog_DefinesTypedPortsForInitialModules()
        {
            var oscillator = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.Oscillator);
            Assert.That(oscillator.Count, Is.EqualTo(4));
            Assert.That(oscillator[0].Id, Is.EqualTo("pitch.in"));
            Assert.That(oscillator[0].Domain,
                Is.EqualTo(ModularAudioPortDomain.Control));
            Assert.That(oscillator[2].Id, Is.EqualTo("fm.in"));
            Assert.That(oscillator[2].Domain,
                Is.EqualTo(ModularAudioPortDomain.Audio));
            Assert.That(oscillator[3].Direction,
                Is.EqualTo(ModularAudioPortDirection.Output));

            var noise = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.Noise);
            Assert.That(noise.Count, Is.EqualTo(2));
            var output = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.AudioOutput);
            Assert.That(output.Count, Is.EqualTo(1));
            Assert.That(output[0].Id, Is.EqualTo("audio.in"));

            var lfo = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.Lfo);
            Assert.That(lfo.Count, Is.EqualTo(7));
            Assert.That(lfo[2].Id, Is.EqualTo("control.out"));
            Assert.That(lfo[2].Domain,
                Is.EqualTo(ModularAudioPortDomain.Control));
            Assert.That(lfo[3].Id, Is.EqualTo("clock.out"));
            Assert.That(lfo[3].Domain,
                Is.EqualTo(ModularAudioPortDomain.Clock));
            Assert.That(lfo[4].Id, Is.EqualTo("gate.out"));
            Assert.That(lfo[4].Domain,
                Is.EqualTo(ModularAudioPortDomain.Gate));
            Assert.That(lfo[5].Id, Is.EqualTo("trigger.out"));
            Assert.That(lfo[5].Domain,
                Is.EqualTo(ModularAudioPortDomain.Trigger));
            Assert.That(lfo[6].Id, Is.EqualTo("audio.out"));
            Assert.That(lfo[6].Domain,
                Is.EqualTo(ModularAudioPortDomain.Audio));

            var sequencer = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.Sequencer);
            Assert.That(sequencer.Count, Is.EqualTo(5));
            Assert.That(sequencer[0].Id, Is.EqualTo("clock.in"));
            Assert.That(sequencer[0].Domain,
                Is.EqualTo(ModularAudioPortDomain.Clock));
            Assert.That(sequencer[1].Id, Is.EqualTo("trigger.in"));
            Assert.That(sequencer[1].Domain,
                Is.EqualTo(ModularAudioPortDomain.Trigger));
            Assert.That(sequencer[2].Id, Is.EqualTo("control.out"));
            Assert.That(sequencer[3].Id, Is.EqualTo("gate.out"));
            Assert.That(sequencer[3].Domain,
                Is.EqualTo(ModularAudioPortDomain.Gate));
            Assert.That(sequencer[4].Id, Is.EqualTo("trigger.out"));
            Assert.That(sequencer[4].Domain,
                Is.EqualTo(ModularAudioPortDomain.Trigger));

            var delay = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.Delay);
            Assert.That(delay.Count, Is.EqualTo(3));
            Assert.That(delay[0].Id, Is.EqualTo("audio.in"));
            Assert.That(delay[1].Id, Is.EqualTo("time.in"));
            Assert.That(delay[2].Id, Is.EqualTo("audio.out"));

            var filter = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.Filter);
            Assert.That(filter.Count, Is.EqualTo(3));
            Assert.That(filter[0].Id, Is.EqualTo("audio.in"));
            Assert.That(filter[1].Id, Is.EqualTo("cutoff.in"));
            Assert.That(filter[1].Domain,
                Is.EqualTo(ModularAudioPortDomain.Control));
            Assert.That(filter[2].Id, Is.EqualTo("audio.out"));

            var envelope = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.Envelope);
            Assert.That(envelope.Count, Is.EqualTo(3));
            Assert.That(envelope[0].Id, Is.EqualTo("gate.in"));
            Assert.That(envelope[0].Domain,
                Is.EqualTo(ModularAudioPortDomain.Gate));
            Assert.That(envelope[1].Id, Is.EqualTo("trigger.in"));
            Assert.That(envelope[1].Domain,
                Is.EqualTo(ModularAudioPortDomain.Trigger));
            Assert.That(envelope[2].Id, Is.EqualTo("control.out"));

            var meter = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.MeterSource);
            Assert.That(meter.Count, Is.EqualTo(3));
            Assert.That(meter[0].Id, Is.EqualTo("value.out"));
            Assert.That(meter[0].Domain,
                Is.EqualTo(ModularAudioPortDomain.Control));
            Assert.That(meter[1].Id, Is.EqualTo("trigger.out"));
            Assert.That(meter[1].Domain,
                Is.EqualTo(ModularAudioPortDomain.Trigger));
            Assert.That(meter[2].Domain,
                Is.EqualTo(ModularAudioPortDomain.Audio));

            var trend = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.TrendSource);
            Assert.That(trend.Count, Is.EqualTo(5));
            Assert.That(trend[1].Id, Is.EqualTo("slope.out"));
            Assert.That(trend[2].Id, Is.EqualTo("spread.out"));
            Assert.That(trend[3].Id, Is.EqualTo("trigger.out"));

            var panel = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.PanelSource);
            Assert.That(panel.Count, Is.EqualTo(6));
            Assert.That(panel[0].Id, Is.EqualTo("energy.out"));
            Assert.That(panel[3].Id, Is.EqualTo("detail.out"));
            Assert.That(panel[4].Id, Is.EqualTo("trigger.out"));
            Assert.That(panel[5].Id, Is.EqualTo("audio.out"));

            var controlSource = ModularAudioPortCatalog.GetPorts(
                ModularAudioModuleKind.ControlSource);
            Assert.That(controlSource.Count, Is.EqualTo(3));
            Assert.That(controlSource[0].Id, Is.EqualTo("control.out"));
            Assert.That(controlSource[0].Domain,
                Is.EqualTo(ModularAudioPortDomain.Control));
            Assert.That(controlSource[1].Id, Is.EqualTo("gate.out"));
            Assert.That(controlSource[1].Domain,
                Is.EqualTo(ModularAudioPortDomain.Gate));
            Assert.That(controlSource[2].Id, Is.EqualTo("trigger.out"));
            Assert.That(controlSource[2].Domain,
                Is.EqualTo(ModularAudioPortDomain.Trigger));
        }

        [Test]
        public void ObservableSources_RenderFiniteBoundedTextures()
        {
            var sources = new ModularAudioNode[]
            {
                new ModularMeterSourceNode { Value = 0.8f },
                new ModularTrendSourceNode
                {
                    Value = 0.65f,
                    Slope = -0.3f,
                    Spread = 0.4f,
                    ValidInputCount = 2,
                    HasValidInput = true
                },
                new ModularPanelSourceNode
                {
                    Energy = 0.72f,
                    Balance = 1.1f,
                    Phase = 0.4f,
                    Detail = 0.6f,
                    ConnectedCount = 4,
                    HasValidInput = true
                }
            };

            foreach (var sourceNode in sources)
            {
                var graph = new ModularAudioGraph();
                var source = graph.AddNode(sourceNode);
                var outputNode = graph.AddNode(new ModularAudioOutputNode());
                Assert.That(graph.ConnectAudio(source, outputNode), Is.True);
                Assert.That(graph.SetOutputNode(outputNode), Is.True);
                Assert.That(graph.Compile(), Is.True);
                var output = new float[512];
                Assert.That(graph.Render(output, output.Length, 48000), Is.True);
                AssertFiniteBoundedAndNonSilent(output, 0.851f);
            }
        }

        [Test]
        public void TrendAndPanelRuntimeState_UpdatesTypedSourceNodes()
        {
            var trendRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.TrendMonitor,
                Pose.identity);
            var panelRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.WindowPanel,
                Pose.identity);
            try
            {
                var trendRuntime = trendRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                trendRuntime.SetTrendState(0.2f, 0.15f, 2, true);
                trendRuntime.SetTrendState(0.5f, 0.25f, 3, true);
                var trend = (ModularTrendSourceNode)trendRuntime.Node;
                Assert.That(trend.Value, Is.EqualTo(0.5f));
                Assert.That(trend.Slope, Is.EqualTo(1f));
                Assert.That(trend.Spread, Is.EqualTo(0.25f));
                Assert.That(trend.ValidInputCount, Is.EqualTo(3));
                Assert.That(trend.HasValidInput, Is.True);

                var panelRuntime = panelRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                panelRuntime.SetWindowPanelState(
                    new WindowPanelGraphicInputs(
                        0.76f,
                        1.18f,
                        -0.4f,
                        0.55f,
                        false,
                        4));
                var panel = (ModularPanelSourceNode)panelRuntime.Node;
                Assert.That(panel.Energy, Is.EqualTo(0.76f));
                Assert.That(panel.Balance, Is.EqualTo(1.18f));
                Assert.That(panel.Phase, Is.EqualTo(-0.4f));
                Assert.That(panel.Detail, Is.EqualTo(0.55f));
                Assert.That(panel.ConnectedCount, Is.EqualTo(4));
                Assert.That(panel.HasValidInput, Is.True);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(trendRoot);
                UnityEngine.Object.DestroyImmediate(panelRoot);
            }
        }

        [Test]
        public void ModuleRuntime_AppliesPersistentWaveformColorAndSteps()
        {
            var oscillatorRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOscillator,
                Pose.identity);
            var noiseRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioNoise,
                Pose.identity);
            var lfoRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioLfo,
                Pose.identity);
            var sequencerRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioSequencer,
                Pose.identity);
            try
            {
                var steps =
                    ModularAudioParameterPolicy.CreateDefaultSequencerSteps();
                steps[3] = 0.85f;
                oscillatorRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true)
                    .ApplyPersistentParameters(
                        (int)ModularOscillatorWaveform.Saw,
                        0,
                        null);
                noiseRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true)
                    .ApplyPersistentParameters(
                        0,
                        (int)ModularNoiseColor.Pink,
                        null);
                lfoRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true)
                    .ApplyPersistentParameters(
                        (int)ModularOscillatorWaveform.Square,
                        0,
                        null);
                sequencerRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true)
                    .ApplyPersistentParameters(0, 0, steps);

                Assert.That(((ModularOscillatorNode)oscillatorRoot
                        .GetComponentInChildren<ModularAudioModuleRuntime>(true)
                        .Node).Waveform,
                    Is.EqualTo(ModularOscillatorWaveform.Saw));
                Assert.That(((ModularNoiseNode)noiseRoot
                        .GetComponentInChildren<ModularAudioModuleRuntime>(true)
                        .Node).Color,
                    Is.EqualTo(ModularNoiseColor.Pink));
                Assert.That(((ModularLfoNode)lfoRoot
                        .GetComponentInChildren<ModularAudioModuleRuntime>(true)
                        .Node).Waveform,
                    Is.EqualTo(ModularOscillatorWaveform.Square));
                Assert.That(((ModularSequencerNode)sequencerRoot
                        .GetComponentInChildren<ModularAudioModuleRuntime>(true)
                        .Node).GetStepValue(3),
                    Is.EqualTo(0.85f).Within(0.0001f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(oscillatorRoot);
                UnityEngine.Object.DestroyImmediate(noiseRoot);
                UnityEngine.Object.DestroyImmediate(lfoRoot);
                UnityEngine.Object.DestroyImmediate(sequencerRoot);
            }
        }

        [Test]
        public void PatchRuntime_BuildsMeterValueControlledOscillatorChain()
        {
            var meterRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.RoundMeter,
                Pose.identity);
            var oscillatorRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOscillator,
                Pose.identity);
            var outputRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOutput,
                Pose.identity);
            try
            {
                var meter = meterRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var oscillator = oscillatorRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var output = outputRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var player = outputRoot.GetComponentInChildren<
                    ModularAudioGraphPlayer>(true);
                var modules = new Dictionary<string, ModularAudioModuleRuntime>
                {
                    ["meter"] = meter,
                    ["osc"] = oscillator,
                    ["out"] = output
                };
                var outputs = new Dictionary<string, ModularAudioGraphPlayer>
                {
                    ["out"] = player
                };
                var connections = new List<AudioPatchConnectionRecord>
                {
                    Patch(
                        "meter-osc",
                        "meter",
                        "osc",
                        "value.out",
                        "pitch.in",
                        ModularAudioPortDomain.Control),
                    AudioPatch("osc-out", "osc", "out")
                };

                var runtime = new ModularAudioPatchRuntime();
                Assert.That(runtime.Refresh(connections, modules, outputs),
                    Is.True);
                Assert.That(runtime.AppliedConnectionCount, Is.EqualTo(2));
                var samples = new float[512];
                Assert.That(player.RenderForValidation(
                    samples,
                    samples.Length), Is.True);
                AssertFiniteBoundedAndNonSilent(samples, 0.851f);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(meterRoot);
                UnityEngine.Object.DestroyImmediate(oscillatorRoot);
                UnityEngine.Object.DestroyImmediate(outputRoot);
            }
        }

        [TestCase(8)]
        [TestCase(16)]
        public void Sequencer_InternalClockAdvancesSelectedStepCount(
            int stepCount)
        {
            var graph = new ModularAudioGraph();
            var sequencerNode = new ModularSequencerNode
            {
                StepCount = stepCount,
                TempoBpm = 300f
            };
            var sequencer = graph.AddNode(sequencerNode);
            var oscillator = graph.AddNode(new ModularOscillatorNode());
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.Connect(
                sequencer,
                oscillator,
                ModularAudioPortDomain.Control,
                "control.out",
                "pitch.in"), Is.True);
            Assert.That(graph.ConnectAudio(oscillator, outputNode), Is.True);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.True);
            var output = new float[1024];
            for (var index = 0; index < 4; index++)
                Assert.That(graph.Render(output, output.Length, 48000), Is.True);
            Assert.That(sequencerNode.UsesExternalClock, Is.False);
            Assert.That(sequencerNode.CurrentStep, Is.GreaterThan(0));
            Assert.That(sequencerNode.CurrentStep, Is.LessThan(stepCount));
            AssertFiniteBoundedAndNonSilent(output, 0.851f);
        }

        [Test]
        public void Sequencer_StepTriggerAdvancesOncePerRisingEdge()
        {
            var graph = new ModularAudioGraph();
            var lfo = graph.AddNode(new ModularLfoNode
            {
                Frequency = 10f,
                GateLength = 0.5f
            });
            var sequencerNode = new ModularSequencerNode
            {
                PlaybackMode =
                    ModularSequencerPlaybackMode.StepTrigger,
                StepCount = 8
            };
            var sequencer = graph.AddNode(sequencerNode);
            var oscillator = graph.AddNode(new ModularOscillatorNode());
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.Connect(
                lfo,
                sequencer,
                ModularAudioPortDomain.Trigger,
                "trigger.out",
                "trigger.in"), Is.True);
            Assert.That(graph.Connect(
                sequencer,
                oscillator,
                ModularAudioPortDomain.Control,
                "control.out",
                "pitch.in"), Is.True);
            Assert.That(graph.ConnectAudio(oscillator, outputNode), Is.True);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.True);

            var output = new float[256];
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(sequencerNode.CurrentStep, Is.EqualTo(1));
            Assert.That(sequencerNode.UsesTriggerStep, Is.True);
            Assert.That(sequencerNode.UsesExternalClock, Is.False);

            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(sequencerNode.CurrentStep, Is.EqualTo(1),
                "Without a new rising edge, the sequencer must not advance.");

            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(sequencerNode.CurrentStep, Is.EqualTo(2));
            AssertFiniteBoundedAndNonSilent(output, 0.851f);
        }

        [Test]
        public void ObservableTrigger_AdvancesSequencerOnThresholdCrossing()
        {
            var graph = new ModularAudioGraph();
            var meterNode = new ModularMeterSourceNode { Value = 0.4f };
            var meter = graph.AddNode(meterNode);
            var sequencerNode = new ModularSequencerNode
            {
                PlaybackMode =
                    ModularSequencerPlaybackMode.StepTrigger,
                StepCount = 8
            };
            var sequencer = graph.AddNode(sequencerNode);
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.Connect(
                meter,
                sequencer,
                ModularAudioPortDomain.Trigger,
                "trigger.out",
                "trigger.in"), Is.True);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.True);

            var output = new float[64];
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(sequencerNode.CurrentStep, Is.Zero);

            meterNode.Value = 0.5f;
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(sequencerNode.CurrentStep, Is.EqualTo(1));

            meterNode.Value = 0.8f;
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(sequencerNode.CurrentStep, Is.EqualTo(1),
                "Remaining above the threshold must not retrigger.");

            meterNode.Value = 0.4f;
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            meterNode.Value = 0.6f;
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(sequencerNode.CurrentStep, Is.EqualTo(2));
        }

        [Test]
        public void PushButtonTrigger_AdvancesSequencerOnPressOnly()
        {
            var graph = new ModularAudioGraph();
            var buttonNode = new ModularControlSourceNode();
            var button = graph.AddNode(buttonNode);
            var sequencerNode = new ModularSequencerNode
            {
                PlaybackMode =
                    ModularSequencerPlaybackMode.StepTrigger,
                StepCount = 8
            };
            var sequencer = graph.AddNode(sequencerNode);
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.Connect(
                button,
                sequencer,
                ModularAudioPortDomain.Trigger,
                "trigger.out",
                "trigger.in"), Is.True);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.True);

            var output = new float[64];
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(sequencerNode.CurrentStep, Is.Zero);

            buttonNode.Value = 1f;
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(sequencerNode.CurrentStep, Is.EqualTo(1));
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(sequencerNode.CurrentStep, Is.EqualTo(1),
                "Holding the button must not retrigger.");

            buttonNode.Value = 0f;
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            buttonNode.Value = 1f;
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(sequencerNode.CurrentStep, Is.EqualTo(2));
        }

        [Test]
        public void PushButtonRuntime_TracksInteractionAsControlSource()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.PushButton,
                Pose.identity);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var runtime = contract.Logic.GetComponent<
                    ModularAudioModuleRuntime>();
                Assert.That(runtime.ModuleKind,
                    Is.EqualTo(ModularAudioModuleKind.ControlSource));
                var source = (ModularControlSourceNode)runtime.Node;
                Assert.That(source.Value, Is.Zero);
                runtime.ApplyPersistentParameters(0, 0, null);

                contract.InstrumentInteraction.SetPressed(true);
                Assert.That(source.Value, Is.EqualTo(1f));
                contract.InstrumentInteraction.SetPressed(false);
                Assert.That(source.Value, Is.Zero);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void InvalidMonitorAndPanelTrigger_RemainsLowUntilInputValid()
        {
            var trend = new ModularTrendSourceNode
            {
                Value = 0.8f,
                ValidInputCount = 1,
                HasValidInput = false
            };
            var panel = new ModularPanelSourceNode
            {
                Energy = 0.8f,
                ConnectedCount = 1,
                HasValidInput = false
            };
            var cases = new (ModularAudioNode Node, Action Enable)[]
            {
                (trend, () => trend.HasValidInput = true),
                (panel, () => panel.HasValidInput = true)
            };

            foreach (var sourceCase in cases)
            {
                var graph = new ModularAudioGraph();
                var source = graph.AddNode(sourceCase.Node);
                var sequencerNode = new ModularSequencerNode
                {
                    PlaybackMode =
                        ModularSequencerPlaybackMode.StepTrigger,
                    StepCount = 8
                };
                var sequencer = graph.AddNode(sequencerNode);
                var outputNode = graph.AddNode(new ModularAudioOutputNode());
                Assert.That(graph.Connect(
                    source,
                    sequencer,
                    ModularAudioPortDomain.Trigger,
                    "trigger.out",
                    "trigger.in"), Is.True);
                Assert.That(graph.SetOutputNode(outputNode), Is.True);
                Assert.That(graph.Compile(), Is.True);

                var output = new float[64];
                Assert.That(graph.Render(
                    output, output.Length, 8000), Is.True);
                Assert.That(sequencerNode.CurrentStep, Is.Zero);

                sourceCase.Enable();
                Assert.That(graph.Render(
                    output, output.Length, 8000), Is.True);
                Assert.That(sequencerNode.CurrentStep, Is.EqualTo(1));
            }
        }

        [Test]
        public void SequencerPlacementValue_SelectsLengthAndTempo()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioSequencer,
                Pose.identity);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var sequencer = (ModularSequencerNode)contract.Logic
                    .GetComponent<ModularAudioModuleRuntime>().Node;
                Assert.That(sequencer.StepCount, Is.EqualTo(8));
                Assert.That(sequencer.TempoBpm, Is.EqualTo(140f).Within(0.001f));
                contract.InstrumentInteraction.SetNormalizedValue(0.75f);
                Assert.That(sequencer.StepCount, Is.EqualTo(16));
                Assert.That(sequencer.TempoBpm, Is.EqualTo(140f).Within(0.001f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void Delay_WetOutputStartsAfterConfiguredTimeAndStaysBounded()
        {
            var graph = new ModularAudioGraph();
            var oscillator = graph.AddNode(new ModularOscillatorNode
            {
                Frequency = 440f,
                Level = 0.3f
            });
            var delay = graph.AddNode(new ModularDelayNode
            {
                DelaySeconds = 0.02f,
                Feedback = 5f,
                Mix = 1f
            });
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.ConnectAudio(oscillator, delay), Is.True);
            Assert.That(graph.ConnectAudio(delay, outputNode), Is.True);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.True);

            var output = new float[1024];
            Assert.That(graph.Render(output, output.Length, 48000), Is.True);
            for (var index = 0; index < 960; index++)
                Assert.That(output[index], Is.Zero);
            var delayedMaximum = 0f;
            for (var index = 960; index < output.Length; index++)
                delayedMaximum = Mathf.Max(
                    delayedMaximum,
                    Mathf.Abs(output[index]));
            Assert.That(delayedMaximum, Is.GreaterThan(0.001f));
            for (var block = 0; block < 64; block++)
                Assert.That(graph.Render(output, output.Length, 48000), Is.True);
            AssertFiniteBoundedAndNonSilent(output, 0.851f);
        }

        [Test]
        public void Compile_AllowsFeedbackCycleOnlyWhenDelayBreaksIt()
        {
            var graph = new ModularAudioGraph();
            var oscillator = graph.AddNode(new ModularOscillatorNode
            {
                Frequency = 220f,
                Level = 0.15f
            });
            var delay = graph.AddNode(new ModularDelayNode
            {
                DelaySeconds = 0.02f,
                Feedback = 0.5f,
                Mix = 1f
            });
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.ConnectAudio(oscillator, delay), Is.True);
            Assert.That(graph.Connect(
                delay,
                oscillator,
                ModularAudioPortDomain.Audio,
                "audio.out",
                "fm.in"), Is.True);
            Assert.That(graph.ConnectAudio(oscillator, outputNode), Is.True);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.True);
            var output = new float[1024];
            Assert.That(graph.Render(output, output.Length, 48000), Is.True);
            AssertFiniteBoundedAndNonSilent(output, 0.851f);
        }

        [Test]
        public void PatchRuntime_BuildsOscillatorDelayOutputChain()
        {
            var lfoRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioLfo,
                Pose.identity);
            var oscillatorRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOscillator,
                Pose.identity);
            var delayRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioDelay,
                Pose.identity);
            var outputRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioOutput,
                Pose.identity);
            try
            {
                var lfo = lfoRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var oscillator = oscillatorRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var delay = delayRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var output = outputRoot.GetComponentInChildren<
                    ModularAudioModuleRuntime>(true);
                var player = outputRoot.GetComponentInChildren<
                    ModularAudioGraphPlayer>(true);
                var modules = new Dictionary<string, ModularAudioModuleRuntime>
                {
                    ["lfo"] = lfo,
                    ["osc"] = oscillator,
                    ["delay"] = delay,
                    ["out"] = output
                };
                var outputs = new Dictionary<string, ModularAudioGraphPlayer>
                {
                    ["out"] = player
                };
                var connections = new List<AudioPatchConnectionRecord>
                {
                    Patch(
                        "lfo-delay-time",
                        "lfo",
                        "delay",
                        "control.out",
                        "time.in",
                        ModularAudioPortDomain.Control),
                    AudioPatch("osc-delay", "osc", "delay"),
                    AudioPatch("delay-out", "delay", "out")
                };
                var runtime = new ModularAudioPatchRuntime();
                Assert.That(runtime.Refresh(connections, modules, outputs),
                    Is.True);
                Assert.That(runtime.AppliedConnectionCount, Is.EqualTo(3));
                Assert.That(player.Graph.NodeCount, Is.EqualTo(4));
                Assert.That(player.Graph.ConnectionCount, Is.EqualTo(3));
                Assert.That(player.Graph.IsCompiled, Is.True);
                var samples = new float[1024];
                Assert.That(player.RenderForValidation(
                    samples,
                    samples.Length), Is.True);
                Assert.That(MaximumAbsolute(samples), Is.Zero);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(lfoRoot);
                UnityEngine.Object.DestroyImmediate(oscillatorRoot);
                UnityEngine.Object.DestroyImmediate(delayRoot);
                UnityEngine.Object.DestroyImmediate(outputRoot);
            }
        }

        [TestCase(ModularOscillatorWaveform.Sine)]
        [TestCase(ModularOscillatorWaveform.Triangle)]
        [TestCase(ModularOscillatorWaveform.Saw)]
        [TestCase(ModularOscillatorWaveform.Square)]
        public void Lfo_RendersFiniteBipolarWaveform(
            ModularOscillatorWaveform waveform)
        {
            var graph = new ModularAudioGraph();
            var lfo = graph.AddNode(new ModularLfoNode
            {
                Waveform = waveform,
                Frequency = 20f,
                Depth = 0.7f
            });
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.ConnectAudio(lfo, outputNode), Is.True);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.True);
            var output = new float[1024];
            Assert.That(graph.Render(output, output.Length, 48000), Is.True);
            AssertFiniteBoundedAndNonSilent(output, 0.701f);
        }

        [TestCase(ModularOscillatorWaveform.Sine)]
        [TestCase(ModularOscillatorWaveform.Triangle)]
        [TestCase(ModularOscillatorWaveform.Saw)]
        [TestCase(ModularOscillatorWaveform.Square)]
        public void OscillatorToOutput_RendersFiniteBoundedAudio(
            ModularOscillatorWaveform waveform)
        {
            var graph = new ModularAudioGraph();
            var oscillator = graph.AddNode(new ModularOscillatorNode
            {
                Waveform = waveform,
                Frequency = 330f,
                Level = 0.4f
            });
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.ConnectAudio(oscillator, outputNode), Is.True);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.True);

            var output = new float[512];
            Assert.That(graph.Render(output, output.Length, 48000), Is.True);
            AssertFiniteBoundedAndNonSilent(output, 0.851f);
        }

        [Test]
        public void Noise_IsDeterministicForEqualSeedsAndColorsDiffer()
        {
            var first = RenderNoise(ModularNoiseColor.White, 123u);
            var second = RenderNoise(ModularNoiseColor.White, 123u);
            var pink = RenderNoise(ModularNoiseColor.Pink, 123u);
            var brown = RenderNoise(ModularNoiseColor.Brown, 123u);
            CollectionAssert.AreEqual(first, second);
            Assert.That(SampleDifference(first, pink), Is.GreaterThan(1f));
            Assert.That(SampleDifference(first, brown), Is.GreaterThan(1f));
            AssertFiniteBoundedAndNonSilent(pink, 0.851f);
            AssertFiniteBoundedAndNonSilent(brown, 0.851f);
        }

        [Test]
        public void BrownNoise_NormalizationKeepsPowerNearWhiteNoise()
        {
            var whiteRms = MeasureNoiseRms(
                ModularNoiseColor.White,
                123u);
            var brownRms = MeasureNoiseRms(
                ModularNoiseColor.Brown,
                123u);

            Assert.That(brownRms / whiteRms,
                Is.InRange(0.75f, 1.05f));
        }

        [Test]
        public void Lfo_ExposesPhaseAdvancedByAudioRendering()
        {
            var graph = new ModularAudioGraph();
            var lfoNode = new ModularLfoNode
            {
                Frequency = 1f,
                Depth = 0.8f
            };
            var lfo = graph.AddNode(lfoNode);
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.ConnectAudio(lfo, outputNode), Is.True);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.True);

            var output = new float[800];
            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(lfoNode.Phase01, Is.EqualTo(0.1f).Within(0.001f));

            Assert.That(graph.Render(output, output.Length, 8000), Is.True);
            Assert.That(lfoNode.Phase01, Is.EqualTo(0.2f).Within(0.001f));
        }

        [Test]
        public void Output_MixesSourcesAndAppliesLimiter()
        {
            var graph = new ModularAudioGraph();
            var first = graph.AddNode(new ModularOscillatorNode
            {
                Waveform = ModularOscillatorWaveform.Square,
                Frequency = 110f,
                Level = 1f
            });
            var second = graph.AddNode(new ModularOscillatorNode
            {
                Waveform = ModularOscillatorWaveform.Square,
                Frequency = 220f,
                Level = 1f
            });
            var outputNode = graph.AddNode(new ModularAudioOutputNode
            {
                Gain = 4f,
                Limit = 0.2f
            });
            Assert.That(graph.ConnectAudio(first, outputNode), Is.True);
            Assert.That(graph.ConnectAudio(second, outputNode), Is.True);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.True);
            var output = new float[512];
            Assert.That(graph.Render(output, output.Length, 48000), Is.True);
            AssertFiniteBoundedAndNonSilent(output, 0.20001f);
            Assert.That(MaximumAbsolute(output), Is.EqualTo(0.2f).Within(0.00001f));
        }

        [Test]
        public void Compile_RejectsZeroDelayAudioCycle()
        {
            var graph = new ModularAudioGraph();
            var oscillator = graph.AddNode(new ModularOscillatorNode());
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.ConnectAudio(oscillator, outputNode), Is.True);
            Assert.That(graph.ConnectAudio(outputNode, oscillator), Is.True);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.False);
            Assert.That(graph.IsCompiled, Is.False);
        }

        [Test]
        public void Render_AfterWarmupAllocatesNoManagedMemory()
        {
            var graph = new ModularAudioGraph();
            var oscillator = graph.AddNode(new ModularOscillatorNode());
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            graph.ConnectAudio(oscillator, outputNode);
            graph.SetOutputNode(outputNode);
            Assert.That(graph.Compile(), Is.True);
            var output = new float[ModularAudioGraph.MaximumBlockFrames];
            graph.Render(output, output.Length, 48000);

            var before = GC.GetAllocatedBytesForCurrentThread();
            for (var index = 0; index < 32; index++)
                graph.Render(output, output.Length, 48000);
            var after = GC.GetAllocatedBytesForCurrentThread();
            Assert.That(after - before, Is.Zero);
        }

        [Test]
        public void Graph_EnforcesNodeBlockAndDuplicateConnectionBounds()
        {
            var graph = new ModularAudioGraph();
            var oscillator = graph.AddNode(new ModularOscillatorNode());
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            Assert.That(graph.ConnectAudio(oscillator, outputNode), Is.True);
            Assert.That(graph.ConnectAudio(oscillator, outputNode), Is.False);
            Assert.That(graph.SetOutputNode(outputNode), Is.True);
            Assert.That(graph.Compile(), Is.True);
            Assert.That(
                graph.Render(
                    new float[ModularAudioGraph.MaximumBlockFrames + 1],
                    ModularAudioGraph.MaximumBlockFrames + 1,
                    48000),
                Is.False);
        }

        private static float[] RenderNoise(
            ModularNoiseColor color,
            uint seed)
        {
            var graph = new ModularAudioGraph();
            var noise = graph.AddNode(new ModularNoiseNode(seed)
            {
                Color = color,
                Level = 0.35f
            });
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            graph.ConnectAudio(noise, outputNode);
            graph.SetOutputNode(outputNode);
            Assert.That(graph.Compile(), Is.True);
            var output = new float[512];
            Assert.That(graph.Render(output, output.Length, 48000), Is.True);
            return output;
        }

        private static float MeasureNoiseRms(
            ModularNoiseColor color,
            uint seed)
        {
            var graph = new ModularAudioGraph();
            var noise = graph.AddNode(new ModularNoiseNode(seed)
            {
                Color = color,
                Level = 0.35f
            });
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            graph.ConnectAudio(noise, outputNode);
            graph.SetOutputNode(outputNode);
            Assert.That(graph.Compile(), Is.True);

            var output = new float[ModularAudioGraph.MaximumBlockFrames];
            double sumSquares = 0.0;
            var sampleCount = 0;
            for (var block = 0; block < 48; block++)
            {
                Assert.That(
                    graph.Render(output, output.Length, 48000),
                    Is.True);
                if (block < 16)
                    continue;
                for (var sample = 0; sample < output.Length; sample++)
                {
                    sumSquares += output[sample] * output[sample];
                    sampleCount++;
                }
            }
            return Mathf.Sqrt((float)(sumSquares / sampleCount));
        }

        private static float MeasureFilteredToneRms(
            float cutoff,
            float resonance)
        {
            var graph = new ModularAudioGraph();
            var oscillator = graph.AddNode(new ModularOscillatorNode
            {
                Frequency = 4000f,
                Level = 0.2f
            });
            var filter = graph.AddNode(new ModularFilterNode
            {
                Cutoff = cutoff,
                Resonance = resonance
            });
            var outputNode = graph.AddNode(new ModularAudioOutputNode());
            graph.ConnectAudio(oscillator, filter);
            graph.ConnectAudio(filter, outputNode);
            graph.SetOutputNode(outputNode);
            Assert.That(graph.Compile(), Is.True);

            var output = new float[ModularAudioGraph.MaximumBlockFrames];
            double sumSquares = 0.0;
            var sampleCount = 0;
            for (var block = 0; block < 24; block++)
            {
                Assert.That(
                    graph.Render(output, output.Length, 48000),
                    Is.True);
                if (block < 8)
                    continue;
                for (var sample = 0; sample < output.Length; sample++)
                {
                    sumSquares += output[sample] * output[sample];
                    sampleCount++;
                }
            }
            return Mathf.Sqrt((float)(sumSquares / sampleCount));
        }

        private static ModularEnvelopeNode FastEnvelope()
        {
            return new ModularEnvelopeNode
            {
                AttackSeconds = 0.005f,
                DecaySeconds = 0.005f,
                SustainLevel = 0.6f,
                ReleaseSeconds = 0.005f,
                ManualGate = false
            };
        }

        private static AudioPatchConnectionRecord AudioPatch(
            string id,
            string source,
            string target)
        {
            return new AudioPatchConnectionRecord
            {
                connectionId = id,
                sourcePlacementId = source,
                targetPlacementId = target
            };
        }

        private static AudioPatchConnectionRecord Patch(
            string id,
            string source,
            string target,
            string sourcePort,
            string targetPort,
            ModularAudioPortDomain domain)
        {
            return new AudioPatchConnectionRecord
            {
                connectionId = id,
                sourcePlacementId = source,
                targetPlacementId = target,
                sourcePortId = sourcePort,
                targetPortId = targetPort,
                portDomain = (int)domain
            };
        }

        private static void AssertFiniteBoundedAndNonSilent(
            float[] samples,
            float maximum)
        {
            foreach (var sample in samples)
            {
                Assert.That(float.IsNaN(sample), Is.False);
                Assert.That(float.IsInfinity(sample), Is.False);
                Assert.That(Mathf.Abs(sample), Is.LessThanOrEqualTo(maximum));
            }
            Assert.That(MaximumAbsolute(samples), Is.GreaterThan(0.001f));
        }

        private static float MaximumAbsolute(float[] samples)
        {
            var maximum = 0f;
            foreach (var sample in samples)
                maximum = Mathf.Max(maximum, Mathf.Abs(sample));
            return maximum;
        }

        private static float SampleDifference(float[] first, float[] second)
        {
            var difference = 0f;
            for (var index = 0; index < first.Length; index++)
                difference += Mathf.Abs(first[index] - second[index]);
            return difference;
        }
    }
}
