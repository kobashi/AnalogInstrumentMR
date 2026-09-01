using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;
using MatsuMotoMeterAR.Signals;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class SignalGraphCompositionTests
    {
        [TestCase(SignalCompositionKind.Average, 0.5f)]
        [TestCase(SignalCompositionKind.Sum, 1f)]
        [TestCase(SignalCompositionKind.Minimum, 0.25f)]
        [TestCase(SignalCompositionKind.Maximum, 0.75f)]
        public void Evaluator_AppliesTargetCompositionKind(
            SignalCompositionKind kind,
            float expected)
        {
            var roots = CreateInstruments(out var instruments);
            try
            {
                SetSourceValues(instruments, 0.25f, 0.5f, 0.75f);
                var evaluator = new SignalGraphEvaluator();

                evaluator.Evaluate(
                    Connections(),
                    instruments,
                    compositionKinds: new Dictionary<
                        string, SignalCompositionKind>
                    {
                        ["target"] = kind
                    });

                Assert.That(
                    instruments["target"].NormalizedValue,
                    Is.EqualTo(expected).Within(0.0001f));
                Assert.That(
                    evaluator.TryGetOutput(
                        "target",
                        out var output,
                        out var inputCount),
                    Is.True);
                Assert.That(output, Is.EqualTo(expected).Within(0.0001f));
                Assert.That(inputCount, Is.EqualTo(3));
            }
            finally
            {
                Destroy(roots);
            }
        }

        [Test]
        public void Evaluator_PriorityUsesRankThenStableConnectionId()
        {
            var roots = CreateInstruments(out var instruments);
            try
            {
                SetSourceValues(instruments, 0.25f, 0.5f, 0.75f);
                var connections = Connections();
                connections[0].compositionPriority = 1;
                connections[1].compositionPriority = 3;
                connections[2].compositionPriority = 3;
                connections[1].connectionId = "a-high";
                connections[2].connectionId = "z-high";

                new SignalGraphEvaluator().Evaluate(
                    connections,
                    instruments,
                    compositionKinds: new Dictionary<
                        string, SignalCompositionKind>
                    {
                        ["target"] = SignalCompositionKind.Priority
                    });

                Assert.That(
                    instruments["target"].NormalizedValue,
                    Is.EqualTo(0.5f).Within(0.0001f));
            }
            finally
            {
                Destroy(roots);
            }
        }

        private static GameObject[] CreateInstruments(
            out Dictionary<string, MockInstrumentInteraction> instruments)
        {
            var roots = new[]
            {
                MockInstrumentFactory.Create(
                    MockInstrumentKind.Lever,
                    Pose.identity),
                MockInstrumentFactory.Create(
                    MockInstrumentKind.ToggleSwitch,
                    Pose.identity),
                MockInstrumentFactory.Create(
                    MockInstrumentKind.RotaryKnob,
                    Pose.identity),
                MockInstrumentFactory.Create(
                    MockInstrumentKind.RoundMeter,
                    Pose.identity)
            };
            instruments = new Dictionary<string, MockInstrumentInteraction>
            {
                ["source-a"] = Interaction(roots[0]),
                ["source-b"] = Interaction(roots[1]),
                ["source-c"] = Interaction(roots[2]),
                ["target"] = Interaction(roots[3])
            };
            return roots;
        }

        private static void SetSourceValues(
            IReadOnlyDictionary<string, MockInstrumentInteraction> instruments,
            float first,
            float second,
            float third)
        {
            instruments["source-a"].SetNormalizedValue(first);
            instruments["source-b"].SetNormalizedValue(second);
            instruments["source-c"].SetNormalizedValue(third);
        }

        private static List<SignalConnectionRecord> Connections()
        {
            return new List<SignalConnectionRecord>
            {
                Connection("connection-a", "source-a"),
                Connection("connection-b", "source-b"),
                Connection("connection-c", "source-c")
            };
        }

        private static SignalConnectionRecord Connection(
            string connectionId,
            string sourcePlacementId)
        {
            return new SignalConnectionRecord
            {
                connectionId = connectionId,
                sourcePlacementId = sourcePlacementId,
                targetPlacementId = "target"
            };
        }

        private static MockInstrumentInteraction Interaction(GameObject root)
        {
            return root.GetComponent<InstrumentGreyboxContract>()
                .InstrumentInteraction;
        }

        private static void Destroy(IEnumerable<GameObject> roots)
        {
            foreach (var root in roots)
                Object.DestroyImmediate(root);
        }
    }
}
