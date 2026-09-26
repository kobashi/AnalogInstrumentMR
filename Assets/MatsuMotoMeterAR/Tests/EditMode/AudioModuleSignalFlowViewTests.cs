using System.Collections.Generic;
using MatsuMotoMeterAR.Audio;
using MatsuMotoMeterAR.Instruments;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class AudioModuleSignalFlowViewTests
    {
        private static readonly MockInstrumentKind[] AudioKinds =
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
            MockInstrumentKind.AudioOutput
        };

        [Test]
        public void Configure_AllModulesShareOneTextureAndUseRendererPropertyBlocks()
        {
            Texture2D shared = null;
            foreach (var kind in AudioKinds)
            {
                var root = new GameObject($"SignalFlow_{kind}");
                try
                {
                    var renderer = root.AddComponent<MeshRenderer>();
                    var runtime = root.AddComponent<ModularAudioModuleRuntime>();
                    runtime.Configure(kind, null);
                    var view = root.AddComponent<AudioModuleSignalFlowView>();
                    view.Configure(
                        kind,
                        MockInstrumentTheme.OrbitalAnalog,
                        renderer);
                    view.Bind(runtime);
                    view.ApplyNow(1.25f);

                    shared ??= view.SharedSignalTexture;
                    Assert.That(
                        view.SharedSignalTexture,
                        Is.SameAs(shared),
                        kind.ToString());
                    Assert.That(
                        view.SharedSignalTexture.width,
                        Is.EqualTo(AudioModuleSignalFlowView.TextureSize));
                    var block = new MaterialPropertyBlock();
                    renderer.GetPropertyBlock(block);
                    Assert.That(
                        block.GetTexture("_BaseMap"),
                        Is.SameAs(shared),
                        kind.ToString());
                    Assert.That(
                        block.GetVector("_BaseMap_ST"),
                        Is.EqualTo(view.CurrentTextureTransform));
                }
                finally
                {
                    Object.DestroyImmediate(root);
                }
            }
        }

        [Test]
        public void OscillatorParameters_ControlDensitySpeedAndGateBrightness()
        {
            var root = new GameObject("SignalFlow_OscillatorParameters");
            try
            {
                var renderer = root.AddComponent<MeshRenderer>();
                var runtime = root.AddComponent<ModularAudioModuleRuntime>();
                runtime.Configure(MockInstrumentKind.AudioOscillator, null);
                var oscillator = (ModularOscillatorNode)runtime.Node;
                var view = root.AddComponent<AudioModuleSignalFlowView>();
                view.Configure(
                    MockInstrumentKind.AudioOscillator,
                    MockInstrumentTheme.OrbitalAnalog,
                    renderer);
                view.Bind(runtime);

                oscillator.Frequency = 55f;
                view.ApplyNow(0f);
                var lowDensity = view.CurrentTextureTransform.x;
                var activeBrightness = Brightness(view.CurrentColor);

                oscillator.Frequency = 1760f;
                view.ApplyNow(1f);
                Assert.That(
                    view.CurrentTextureTransform.x,
                    Is.GreaterThan(lowDensity));
                Assert.That(
                    view.CurrentTextureTransform.z,
                    Is.Not.EqualTo(0f));

                oscillator.Gate = false;
                view.ApplyNow(1f);
                Assert.That(
                    Brightness(view.CurrentColor),
                    Is.LessThan(activeBrightness * 0.2f));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void ModuleKinds_SelectPurposeSpecificTextureBands()
        {
            var offsets = new Dictionary<MockInstrumentKind, float>();
            foreach (var kind in AudioKinds)
            {
                var root = new GameObject($"SignalBand_{kind}");
                try
                {
                    var renderer = root.AddComponent<MeshRenderer>();
                    var runtime = root.AddComponent<ModularAudioModuleRuntime>();
                    runtime.Configure(kind, null);
                    var view = root.AddComponent<AudioModuleSignalFlowView>();
                    view.Configure(
                        kind,
                        MockInstrumentTheme.OrbitalAnalog,
                        renderer);
                    view.Bind(runtime);
                    view.ApplyNow(0f);
                    offsets[kind] = view.CurrentTextureTransform.w;
                }
                finally
                {
                    Object.DestroyImmediate(root);
                }
            }

            Assert.That(
                offsets[MockInstrumentKind.AudioNoise],
                Is.Not.EqualTo(offsets[MockInstrumentKind.AudioOscillator]));
            Assert.That(
                offsets[MockInstrumentKind.AudioSequencer],
                Is.Not.EqualTo(offsets[MockInstrumentKind.AudioDelay]));
            Assert.That(
                offsets[MockInstrumentKind.AudioOutput],
                Is.Not.EqualTo(offsets[MockInstrumentKind.AudioDelay]));
        }

        private static float Brightness(Color value)
        {
            return Mathf.Max(value.r, Mathf.Max(value.g, value.b));
        }
    }
}
