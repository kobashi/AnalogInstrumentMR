using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PerformanceGate;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class PerformanceGateTests
    {
        [TestCase(12, 12)]
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
        [TestCase("invalid", MockInstrumentTheme.OrbitalAnalog)]
        public void ParseTheme_UsesKnownThemeOrDefault(string value, MockInstrumentTheme expected)
        {
            Assert.That(PerformanceGateConfiguration.ParseTheme(value), Is.EqualTo(expected));
        }

        [TestCase(60, 60)]
        [TestCase(600, 600)]
        [TestCase(0, 600)]
        [TestCase(120, 600)]
        public void NormalizeDuration_AllowsSmokeOrFullGate(int requested, int expected)
        {
            Assert.That(
                PerformanceGateConfiguration.NormalizeDuration(requested),
                Is.EqualTo(expected));
        }

    }
}
