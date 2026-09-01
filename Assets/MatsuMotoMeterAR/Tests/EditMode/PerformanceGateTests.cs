using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PerformanceGate;
using MatsuMotoMeterAR.Signals;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class PerformanceGateTests
    {
        [TestCase(12, 12)]
        [TestCase(1, 1)]
        [TestCase(24, 24)]
        [TestCase(40, 40)]
        [TestCase(48, 48)]
        [TestCase(64, 64)]
        [TestCase(0, 0)]
        [TestCase(23, 0)]
        public void NormalizeCount_AllowsOnlyDefinedScenarios(int requested, int expected)
        {
            Assert.That(PerformanceGateConfiguration.NormalizeCount(requested), Is.EqualTo(expected));
        }

        [Test]
        public void Layout_UsesSixColumnsAndUniquePositions()
        {
            var positions = new System.Collections.Generic.HashSet<Vector3>();
            for (var index = 0; index < 24; index++)
            {
                var pose = PerformanceGateLayout.GetPose(
                    index,
                    24,
                    Vector3.zero,
                    Vector3.right,
                    Vector3.up,
                    Vector3.back);
                positions.Add(pose.position);
            }

            Assert.That(positions, Has.Count.EqualTo(24));
        }

        [Test]
        public void Percentile95_IgnoresUnavailableFrameTimings()
        {
            var values = new[] { 0.0, 1.0, 2.0, 3.0, 4.0, 100.0 };
            Assert.That(
                PerformanceGateController.Percentile95(values, values.Length, true),
                Is.EqualTo(100.0));
        }

        [TestCase("OrbitalAnalog", MockInstrumentTheme.OrbitalAnalog)]
        [TestCase("forgebrass", MockInstrumentTheme.ForgeBrass)]
        [TestCase("MachinedErgonomics", MockInstrumentTheme.MachinedErgonomics)]
        [TestCase("machined-ergonomics", MockInstrumentTheme.MachinedErgonomics)]
        [TestCase("invalid", MockInstrumentTheme.OrbitalAnalog)]
        public void ParseTheme_UsesKnownThemeOrDefault(string value, MockInstrumentTheme expected)
        {
            Assert.That(PerformanceGateConfiguration.ParseTheme(value), Is.EqualTo(expected));
        }

        [TestCase(60, 60)]
        [TestCase(600, 600)]
        [TestCase(1800, 1800)]
        [TestCase(0, 600)]
        [TestCase(120, 600)]
        public void NormalizeDuration_AllowsSmokeFullOrLongGate(int requested, int expected)
        {
            Assert.That(
                PerformanceGateConfiguration.NormalizeDuration(requested),
                Is.EqualTo(expected));
        }

        [TestCase(0.5f, 0.5f)]
        [TestCase(1.0f, 1.0f)]
        [TestCase(3.0f, 3.0f)]
        [TestCase(5.0f, 5.0f)]
        [TestCase(0.49f, PerformanceGateConfiguration.DefaultDistanceMeters)]
        [TestCase(5.01f, PerformanceGateConfiguration.DefaultDistanceMeters)]
        public void NormalizeDistance_AllowsSafeReviewRange(
            float requested,
            float expected)
        {
            Assert.That(
                PerformanceGateConfiguration.NormalizeDistance(requested),
                Is.EqualTo(expected).Within(0.001f));
        }

        [TestCase("RoundMeterLarge", MockInstrumentKind.RoundMeterLarge)]
        [TestCase("windowmeter", MockInstrumentKind.WindowMeter)]
        [TestCase("WindowPanel", MockInstrumentKind.WindowPanel)]
        public void ParseKind_UsesDefinedInstrumentKind(
            string value,
            MockInstrumentKind expected)
        {
            Assert.That(
                PerformanceGateConfiguration.ParseKind(value),
                Is.EqualTo(expected));
        }

        [TestCase("")]
        [TestCase("NotAKind")]
        [TestCase("99")]
        public void ParseKind_RejectsUnknownInstrumentKind(string value)
        {
            Assert.That(
                PerformanceGateConfiguration.ParseKind(value),
                Is.Null);
        }

        [TestCase("None", PerformanceGateDisplayMode.None)]
        [TestCase("numeric", PerformanceGateDisplayMode.Numeric)]
        [TestCase("GRAPH", PerformanceGateDisplayMode.Graph)]
        [TestCase("invalid", PerformanceGateDisplayMode.None)]
        [TestCase("", PerformanceGateDisplayMode.None)]
        public void ParseDisplayMode_UsesKnownProfileOrNone(
            string value,
            PerformanceGateDisplayMode expected)
        {
            Assert.That(
                PerformanceGateConfiguration.ParseDisplayMode(value),
                Is.EqualTo(expected));
        }

        [TestCase(PerformanceGateDisplayMode.None, MockInstrumentKind.TrendMonitor,
            PerformanceGateDisplayMode.None)]
        [TestCase(PerformanceGateDisplayMode.Numeric, MockInstrumentKind.TrendMonitor,
            PerformanceGateDisplayMode.Numeric)]
        [TestCase(PerformanceGateDisplayMode.Graph, MockInstrumentKind.TrendMonitor,
            PerformanceGateDisplayMode.Graph)]
        [TestCase(PerformanceGateDisplayMode.Graph, MockInstrumentKind.RoundMeter,
            PerformanceGateDisplayMode.None)]
        public void ResolveDisplayMode_OnlyEnablesTrendMonitorProfiles(
            PerformanceGateDisplayMode requested,
            MockInstrumentKind kind,
            PerformanceGateDisplayMode expected)
        {
            Assert.That(
                PerformanceGateConfiguration.ResolveDisplayMode(requested, kind),
                Is.EqualTo(expected));
        }

        [Test]
        public void MonitorRefreshScheduler_SpreadsFiveHertzAcrossFrames()
        {
            var scheduler = new SignalMonitorRefreshScheduler();
            var refreshes = 0;
            for (var frame = 0; frame < 72; frame++)
                refreshes += scheduler.Accumulate(48, 1f / 72f);

            Assert.That(refreshes, Is.InRange(239, 240));
        }

        [Test]
        public void MonitorRefreshScheduler_WrapsStableIndices()
        {
            var scheduler = new SignalMonitorRefreshScheduler();
            Assert.That(scheduler.TakeNextIndex(3), Is.EqualTo(0));
            Assert.That(scheduler.TakeNextIndex(3), Is.EqualTo(1));
            Assert.That(scheduler.TakeNextIndex(3), Is.EqualTo(2));
            Assert.That(scheduler.TakeNextIndex(3), Is.EqualTo(0));
        }

    }
}
