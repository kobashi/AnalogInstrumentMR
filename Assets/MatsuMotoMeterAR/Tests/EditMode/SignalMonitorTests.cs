using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;
using MatsuMotoMeterAR.Signals;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class SignalMonitorTests
    {
        [Test]
        public void SampleBuffer_WrapsAndReadsOldestFirst()
        {
            var buffer = new SignalSampleBuffer(3);
            buffer.Add(1f);
            buffer.Add(2f);
            buffer.Add(3f);
            buffer.Add(4f);

            Assert.That(buffer.Count, Is.EqualTo(3));
            Assert.That(buffer.GetOldestFirst(0), Is.EqualTo(2f));
            Assert.That(buffer.GetOldestFirst(1), Is.EqualTo(3f));
            Assert.That(buffer.GetOldestFirst(2), Is.EqualTo(4f));

            buffer.Clear();
            Assert.That(buffer.Count, Is.Zero);
            Assert.Throws<ArgumentOutOfRangeException>(
                () => buffer.GetOldestFirst(0));
        }

        [Test]
        public void Evaluator_ReportsOutputAndClearsDisconnectedState()
        {
            var sourceRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.Lever,
                Pose.identity);
            var targetRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.RoundMeter,
                Pose.identity);
            try
            {
                var source = sourceRoot
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                var target = targetRoot
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                source.SetNormalizedValue(0.75f);

                var instruments = new Dictionary<string, MockInstrumentInteraction>
                {
                    ["source"] = source,
                    ["target"] = target
                };
                var connections = new List<SignalConnectionRecord>
                {
                    new()
                    {
                        connectionId = "connection",
                        sourcePlacementId = "source",
                        targetPlacementId = "target",
                        transformKind = (int)SignalTransformKind.Direct
                    }
                };
                var evaluator = new SignalGraphEvaluator();

                evaluator.Evaluate(connections, instruments);

                Assert.That(
                    evaluator.TryGetOutput(
                        "target",
                        out var output,
                        out var inputCount),
                    Is.True);
                Assert.That(output, Is.EqualTo(0.75f).Within(0.0001f));
                Assert.That(inputCount, Is.EqualTo(1));
                Assert.That(target.NormalizedValue, Is.EqualTo(0.75f).Within(0.0001f));

                evaluator.Evaluate(Array.Empty<SignalConnectionRecord>(), instruments);
                Assert.That(
                    evaluator.TryGetOutput("target", out _, out _),
                    Is.False);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(sourceRoot);
                UnityEngine.Object.DestroyImmediate(targetRoot);
            }
        }

        [Test]
        public void Factory_AddsMonitorOnlyToSignalTargets()
        {
            var target = MockInstrumentFactory.Create(
                MockInstrumentKind.RoundMeter,
                Pose.identity);
            var source = MockInstrumentFactory.Create(
                MockInstrumentKind.Lever,
                Pose.identity);
            try
            {
                Assert.That(
                    target.GetComponentInChildren<SignalMonitorView>(true),
                    Is.Not.Null);
                Assert.That(
                    source.GetComponentInChildren<SignalMonitorView>(true),
                    Is.Null);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(target);
                UnityEngine.Object.DestroyImmediate(source);
            }
        }
    }
}
