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
        public void Factory_AddsDisplayOnlyToTrendMonitor()
        {
            var monitor = MockInstrumentFactory.Create(
                MockInstrumentKind.TrendMonitor,
                Pose.identity);
            var meter = MockInstrumentFactory.Create(
                MockInstrumentKind.RoundMeter,
                Pose.identity);
            try
            {
                Assert.That(
                    monitor.GetComponentInChildren<SignalMonitorView>(true),
                    Is.Not.Null);
                Assert.That(
                    meter.GetComponentInChildren<SignalMonitorView>(true),
                    Is.Null);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(monitor);
                UnityEngine.Object.DestroyImmediate(meter);
            }
        }

        [Test]
        public void Factory_AlignsDisplayToVisualDisplaySurface()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.TrendMonitor,
                new Pose(
                    new Vector3(1f, 2f, 3f),
                    Quaternion.Euler(12f, 34f, 5f)));
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var displaySurface = contract.VisualSocket
                    .GetComponentInChildren<ThemeVisualManifest>(true)
                    .MotionTarget;
                var monitor = root.GetComponentInChildren<SignalMonitorView>(true);
                var outwardOffset = Vector3.Dot(
                    monitor.transform.position - displaySurface.position,
                    displaySurface.forward);

                Assert.That(outwardOffset, Is.GreaterThan(0f));
                Assert.That(
                    Vector3.Dot(
                        monitor.transform.forward,
                        displaySurface.forward),
                    Is.LessThan(-0.999f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void Policy_MetersAreObservableOnlyByTrendMonitor()
        {
            Assert.That(
                InstrumentSignalPolicy.CanConnect(
                    MockInstrumentKind.RoundMeter,
                    MockInstrumentKind.TrendMonitor),
                Is.True);
            Assert.That(
                InstrumentSignalPolicy.CanConnect(
                    MockInstrumentKind.RoundMeter,
                    MockInstrumentKind.WindowMeter),
                Is.False);
            Assert.That(
                InstrumentSignalPolicy.CanConnect(
                    MockInstrumentKind.Lever,
                    MockInstrumentKind.TrendMonitor),
                Is.True);
            Assert.That(
                InstrumentSignalPolicy.CanSource(
                    MockInstrumentKind.TrendMonitor),
                Is.False);
        }

        [Test]
        public void View_AcceptsFourStableChannelsAndRejectsFifth()
        {
            var socket = new GameObject("LabelSocket");
            try
            {
                var monitor = SignalMonitorView.Create(
                    socket.transform,
                    displaySurface: null);
                monitor.BeginRefresh();
                for (var index = 0;
                     index < SignalMonitorView.ChannelCapacity;
                     index++)
                {
                    Assert.That(
                        monitor.AddSample($"connection-{index}", index / 3f),
                        Is.True);
                }
                Assert.That(
                    monitor.AddSample("connection-overflow", 0.5f),
                    Is.False);
                monitor.EndRefresh();

                Assert.That(
                    monitor.ConnectedChannelCount,
                    Is.EqualTo(SignalMonitorView.ChannelCapacity));
                for (var index = 0;
                     index < SignalMonitorView.ChannelCapacity;
                     index++)
                {
                    Assert.That(
                        monitor.GetChannelSampleCount(index),
                        Is.EqualTo(1));
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(socket);
            }
        }
    }
}
