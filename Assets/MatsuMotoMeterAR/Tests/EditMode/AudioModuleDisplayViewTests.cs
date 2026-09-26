using System.Collections.Generic;
using MatsuMotoMeterAR.Audio;
using MatsuMotoMeterAR.Instruments;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class AudioModuleDisplayViewTests
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
        public void RedrawNow_AssignsTextureAndDrawsDistinctModuleDisplays()
        {
            var signatures = new HashSet<int>();
            foreach (var kind in AudioKinds)
            {
                var root = new GameObject($"DisplayTest_{kind}");
                try
                {
                    var filter = root.AddComponent<MeshFilter>();
                    filter.sharedMesh = BuildDisplayQuad();
                    var renderer = root.AddComponent<MeshRenderer>();
                    var module = root.AddComponent<ModularAudioModuleRuntime>();
                    module.Configure(kind, null);
                    var view = root.AddComponent<AudioModuleDisplayView>();
                    view.Configure(
                        kind,
                        MockInstrumentTheme.OrbitalAnalog,
                        renderer);
                    view.Bind(module);
                    view.RedrawNow();

                    Assert.That(view.DisplayTexture, Is.Not.Null, kind.ToString());
                    Assert.That(
                        view.DisplayTexture.width,
                        Is.EqualTo(AudioModuleDisplayView.TextureWidth));
                    Assert.That(
                        view.DisplayTexture.height,
                        Is.EqualTo(AudioModuleDisplayView.TextureHeight));
                    var block = new MaterialPropertyBlock();
                    renderer.GetPropertyBlock(block);
                    Assert.That(
                        block.GetTexture("_BaseMap"),
                        Is.SameAs(view.DisplayTexture),
                        kind.ToString());
                    Assert.That(
                        block.GetTexture("_EmissionMap"),
                        Is.SameAs(view.DisplayTexture),
                        $"{kind} emission must show the runtime display");
                    Assert.That(
                        block.GetColor("_EmissionColor"),
                        Is.EqualTo(Color.white),
                        $"{kind} authored cyan emission must not mask content");
                    Assert.That(filter.sharedMesh.uv, Has.Length.EqualTo(4));
                    Assert.That(filter.sharedMesh.uv[0], Is.Not.EqualTo(
                        filter.sharedMesh.uv[2]));

                    signatures.Add(Signature(view.DisplayTexture.GetPixels32()));
                }
                finally
                {
                    Object.DestroyImmediate(root);
                }
            }

            Assert.That(signatures, Has.Count.EqualTo(AudioKinds.Length));
        }

        [Test]
        public void Configure_UsesThemeSpecificForegroundColor()
        {
            var signatures = new HashSet<int>();
            foreach (MockInstrumentTheme theme in
                     System.Enum.GetValues(typeof(MockInstrumentTheme)))
            {
                var root = new GameObject($"ThemeDisplayTest_{theme}");
                try
                {
                    var renderer = root.AddComponent<MeshRenderer>();
                    var view = root.AddComponent<AudioModuleDisplayView>();
                    view.Configure(
                        MockInstrumentKind.AudioOscillator,
                        theme,
                        renderer);
                    signatures.Add(Signature(view.DisplayTexture.GetPixels32()));
                }
                finally
                {
                    Object.DestroyImmediate(root);
                }
            }

            Assert.That(
                signatures,
                Has.Count.EqualTo(MockInstrumentThemeCatalog.Count));
        }

        [Test]
        public void ProductionFactory_BindsDisplayForEveryThemeAndAudioKind()
        {
            foreach (var kind in AudioKinds)
            {
                foreach (MockInstrumentTheme theme in
                         System.Enum.GetValues(typeof(MockInstrumentTheme)))
                {
                    var root = MockInstrumentFactory.Create(
                        kind,
                        Pose.identity,
                        theme: theme);
                    try
                    {
                        var view = root.GetComponentInChildren<
                            AudioModuleDisplayView>(true);
                        Assert.That(view, Is.Not.Null, $"{theme}/{kind}");
                        Assert.That(view.DisplayRenderer, Is.Not.Null,
                            $"{theme}/{kind}");
                        Assert.That(view.DisplayTexture, Is.Not.Null,
                            $"{theme}/{kind}");
                        Assert.That(
                            root.GetComponent<InstrumentGreyboxContract>()
                                .VisualSocket.childCount,
                            Is.EqualTo(1),
                            $"{theme}/{kind}");
                    }
                    finally
                    {
                        Object.DestroyImmediate(root);
                    }
                }
            }
        }

        [Test]
        public void LfoDisplay_UsesRenderedDspPhaseForHairline()
        {
            var root = new GameObject("LfoPhaseDisplayTest");
            try
            {
                var filter = root.AddComponent<MeshFilter>();
                filter.sharedMesh = BuildDisplayQuad();
                var renderer = root.AddComponent<MeshRenderer>();
                var module = root.AddComponent<ModularAudioModuleRuntime>();
                module.Configure(MockInstrumentKind.AudioLfo, null);
                var lfoNode = (ModularLfoNode)module.Node;
                lfoNode.Frequency = 1f;

                var graph = new ModularAudioGraph();
                var lfo = graph.AddNode(lfoNode);
                var outputNode = graph.AddNode(
                    new ModularAudioOutputNode());
                Assert.That(graph.ConnectAudio(lfo, outputNode), Is.True);
                Assert.That(graph.SetOutputNode(outputNode), Is.True);
                Assert.That(graph.Compile(), Is.True);
                var output = new float[800];
                Assert.That(
                    graph.Render(output, output.Length, 8000),
                    Is.True);

                var view = root.AddComponent<AudioModuleDisplayView>();
                view.Configure(
                    MockInstrumentKind.AudioLfo,
                    MockInstrumentTheme.OrbitalAnalog,
                    renderer);
                view.Bind(module);
                view.RedrawNow();

                Assert.That(
                    view.DisplayedLfoPhase,
                    Is.EqualTo(lfoNode.Phase01).Within(0.0001f));
                Assert.That(
                    view.DisplayedLfoMarkerColumn,
                    Is.EqualTo(10 + Mathf.RoundToInt(
                        235f * lfoNode.Phase01)));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        private static int Signature(IReadOnlyList<Color32> pixels)
        {
            unchecked
            {
                var hash = 17;
                for (var index = 0; index < pixels.Count; index += 7)
                {
                    var pixel = pixels[index];
                    hash = hash * 31 + pixel.r;
                    hash = hash * 31 + pixel.g;
                    hash = hash * 31 + pixel.b;
                }
                return hash;
            }
        }

        private static Mesh BuildDisplayQuad()
        {
            var mesh = new Mesh { name = "DisplayWithoutUv" };
            mesh.vertices = new[]
            {
                new Vector3(-1f, -0.5f, 0f),
                new Vector3(1f, -0.5f, 0f),
                new Vector3(1f, 0.5f, 0f),
                new Vector3(-1f, 0.5f, 0f)
            };
            mesh.triangles = new[] { 0, 1, 2, 0, 2, 3 };
            mesh.RecalculateNormals();
            return mesh;
        }
    }
}
