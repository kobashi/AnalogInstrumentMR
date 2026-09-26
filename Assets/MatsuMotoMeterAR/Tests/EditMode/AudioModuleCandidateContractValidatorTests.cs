using System.Linq;
using MatsuMotoMeterAR.Editor;
using MatsuMotoMeterAR.Instruments;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class AudioModuleCandidateContractValidatorTests
    {
        [Test]
        public void R2A4Contract_AcceptsSeparateSignalSurfaceWithSharedMaterial()
        {
            var fixture = BuildFixture(includeSignal: true);
            try
            {
                var problems = AudioModuleCandidateContractValidator.Evaluate(
                    fixture.Root,
                    MockInstrumentKind.AudioNoise,
                    requireSignalSurface: true);

                Assert.That(problems, Is.Empty);
            }
            finally
            {
                fixture.Destroy();
            }
        }

        [Test]
        public void R2A4Contract_RejectsMissingSignalSurface()
        {
            var fixture = BuildFixture(includeSignal: false);
            try
            {
                var problems = AudioModuleCandidateContractValidator.Evaluate(
                    fixture.Root,
                    MockInstrumentKind.AudioNoise,
                    requireSignalSurface: true);

                Assert.That(
                    problems.Any(problem => problem.Contains(
                        "Expected exactly one signal_surface")),
                    Is.True);
            }
            finally
            {
                fixture.Destroy();
            }
        }

        [TestCase(MockInstrumentKind.AudioVca)]
        [TestCase(MockInstrumentKind.AudioMixer)]
        [TestCase(MockInstrumentKind.AudioFilter)]
        [TestCase(MockInstrumentKind.AudioEnvelope)]
        [TestCase(MockInstrumentKind.AudioLfo)]
        [TestCase(MockInstrumentKind.AudioSequencer)]
        public void ExtensionContract_AcceptsCurrentTypedPortSet(
            MockInstrumentKind kind)
        {
            var fixture = BuildFixture(
                includeSignal: true,
                ports: ExpectedPorts(kind));
            try
            {
                var problems = AudioModuleCandidateContractValidator.Evaluate(
                    fixture.Root,
                    kind,
                    requireSignalSurface: true);

                Assert.That(problems, Is.Empty);
            }
            finally
            {
                fixture.Destroy();
            }
        }

        private static Fixture BuildFixture(
            bool includeSignal,
            string[] ports = null)
        {
            var root = new GameObject("CandidateRoot");
            var imported = new GameObject("ImportedModel");
            imported.transform.SetParent(root.transform, false);
            var material = new Material(
                Shader.Find("Universal Render Pipeline/Unlit") ??
                Shader.Find("Unlit/Color"));

            AddNode(imported.transform, "housing");
            AddNode(imported.transform, "faceplate");
            AddNode(imported.transform, "display_bezel");
            AddSurface(
                imported.transform,
                "display_surface",
                material);
            if (includeSignal)
                AddSurface(imported.transform, "signal_surface", material);
            var pivot = AddNode(imported.transform, "parameter_knob_pivot");
            AddNode(pivot, "parameter_knob");
            AddNode(pivot, "parameter_index");
            foreach (var port in ports ?? new[]
                     {
                         "port_gate_in", "port_audio_out"
                     })
            {
                AddNode(imported.transform, port);
            }

            return new Fixture(root, material);
        }

        private static string[] ExpectedPorts(MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.AudioVca => new[]
                {
                    "port_audio_in", "port_level_in", "port_audio_out"
                },
                MockInstrumentKind.AudioMixer => new[]
                {
                    "port_audio_in", "port_audio_out"
                },
                MockInstrumentKind.AudioFilter => new[]
                {
                    "port_audio_in", "port_cutoff_in", "port_audio_out"
                },
                MockInstrumentKind.AudioEnvelope => new[]
                {
                    "port_gate_in", "port_trigger_in", "port_control_out"
                },
                MockInstrumentKind.AudioLfo => new[]
                {
                    "port_rate_in", "port_reset_in", "port_control_out",
                    "port_clock_out", "port_gate_out", "port_trigger_out",
                    "port_audio_out"
                },
                MockInstrumentKind.AudioSequencer => new[]
                {
                    "port_clock_in", "port_trigger_in", "port_control_out",
                    "port_gate_out", "port_trigger_out"
                },
                _ => System.Array.Empty<string>()
            };
        }

        private static Transform AddNode(Transform parent, string name)
        {
            var node = new GameObject(name).transform;
            node.SetParent(parent, false);
            return node;
        }

        private static MeshFilter AddSurface(
            Transform parent,
            string name,
            Material material)
        {
            var node = AddNode(parent, name).gameObject;
            var mesh = new Mesh { name = name + "_mesh" };
            mesh.vertices = new[]
            {
                new Vector3(-1f, -0.5f, 0f),
                new Vector3(1f, -0.5f, 0f),
                new Vector3(1f, 0.5f, 0f),
                new Vector3(-1f, 0.5f, 0f)
            };
            mesh.triangles = new[] { 0, 1, 2, 0, 2, 3 };
            mesh.uv = new[]
            {
                new Vector2(0f, 0f),
                new Vector2(1f, 0f),
                new Vector2(1f, 1f),
                new Vector2(0f, 1f)
            };
            mesh.RecalculateNormals();
            var filter = node.AddComponent<MeshFilter>();
            filter.sharedMesh = mesh;
            node.AddComponent<MeshRenderer>().sharedMaterial = material;
            return filter;
        }

        private sealed class Fixture
        {
            private readonly Material material;

            public Fixture(GameObject root, Material material)
            {
                Root = root;
                this.material = material;
            }

            public GameObject Root { get; }

            public void Destroy()
            {
                var meshes = Root.GetComponentsInChildren<MeshFilter>(true)
                    .Select(filter => filter.sharedMesh)
                    .Distinct()
                    .ToArray();
                Object.DestroyImmediate(Root);
                foreach (var mesh in meshes)
                    Object.DestroyImmediate(mesh);
                Object.DestroyImmediate(material);
            }
        }
    }
}
