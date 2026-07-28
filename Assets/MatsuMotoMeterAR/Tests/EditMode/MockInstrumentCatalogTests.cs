using System.Collections.Generic;
using MatsuMotoMeterAR.Anchors;
using MatsuMotoMeterAR.Instruments;
using NUnit.Framework;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class MockInstrumentCatalogTests
    {
        [Test]
        public void TypeIds_AreStableAndUnique()
        {
            var ids = new HashSet<string>();
            for (var index = 0; index < MockInstrumentCatalog.Count; index++)
            {
                var kind = (MockInstrumentKind)index;
                var typeId = MockInstrumentCatalog.GetTypeId(kind);
                Assert.That(typeId, Is.Not.Empty);
                Assert.That(ids.Add(typeId), Is.True, $"Duplicate type ID: {typeId}");
                Assert.That(MockInstrumentCatalog.FromTypeId(typeId), Is.EqualTo(kind));
            }
        }

        [TestCase(MockInstrumentKind.RoundMeter, "meter.round")]
        [TestCase(MockInstrumentKind.Lever, "control.lever")]
        [TestCase(MockInstrumentKind.ToggleSwitch, "control.toggle")]
        [TestCase(MockInstrumentKind.RotaryKnob, "control.rotary")]
        [TestCase(MockInstrumentKind.PushButton, "control.button")]
        [TestCase(MockInstrumentKind.IndicatorLamp, "indicator.lamp")]
        [TestCase(MockInstrumentKind.WindowMeter, "meter.window")]
        [TestCase(MockInstrumentKind.WindowPanel, "panel.window")]
        [TestCase(MockInstrumentKind.StatusIndicator, "indicator.status")]
        [TestCase(MockInstrumentKind.ThrottleLever, "control.throttle")]
        [TestCase(MockInstrumentKind.PowerSlider, "control.power_slider")]
        public void TypeIds_PreservePlacementDataContract(
            MockInstrumentKind kind,
            string expectedTypeId)
        {
            Assert.That(MockInstrumentCatalog.GetTypeId(kind), Is.EqualTo(expectedTypeId));
        }

        [Test]
        public void LegacyRoundMeterFactory_PreservesTypeId()
        {
            Assert.That(
                MockRoundMeterFactory.InstrumentTypeId,
                Is.EqualTo(MockInstrumentCatalog.GetTypeId(MockInstrumentKind.RoundMeter)));
        }

        [Test]
        public void UnknownTypeId_FallsBackToRoundMeter()
        {
            Assert.That(
                MockInstrumentCatalog.FromTypeId("unknown"),
                Is.EqualTo(MockInstrumentKind.RoundMeter));
        }

        [Test]
        public void Cycle_WrapsInBothDirections()
        {
            Assert.That(
                MockInstrumentCatalog.Cycle(MockInstrumentKind.PowerSlider, 1),
                Is.EqualTo(MockInstrumentKind.RoundMeter));
            Assert.That(
                MockInstrumentCatalog.Cycle(MockInstrumentKind.RoundMeter, -1),
                Is.EqualTo(MockInstrumentKind.PowerSlider));
        }

        [TestCase(MockInstrumentKind.Lever)]
        [TestCase(MockInstrumentKind.RotaryKnob)]
        [TestCase(MockInstrumentKind.ThrottleLever)]
        [TestCase(MockInstrumentKind.PowerSlider)]
        public void ManualControls_AreRejectedOnCeiling(MockInstrumentKind kind)
        {
            Assert.That(
                MockInstrumentCatalog.SupportsSurface(kind, SurfaceKind.Wall),
                Is.True);
            Assert.That(
                MockInstrumentCatalog.SupportsSurface(kind, SurfaceKind.Floor),
                Is.True);
            Assert.That(
                MockInstrumentCatalog.SupportsSurface(kind, SurfaceKind.Ceiling),
                Is.False);
        }

        [Test]
        public void CodeOnlyControls_WaitForAuthoredModels()
        {
            Assert.That(
                MockInstrumentFactory.IsPlacementReady(
                    MockInstrumentKind.ThrottleLever,
                    MockInstrumentTheme.OrbitalAnalog),
                Is.False);
            Assert.That(
                MockInstrumentFactory.IsPlacementReady(
                    MockInstrumentKind.PowerSlider,
                    MockInstrumentTheme.OrbitalAnalog),
                Is.False);
            Assert.That(
                MockInstrumentFactory.IsPlacementReady(
                    MockInstrumentKind.Lever,
                    MockInstrumentTheme.OrbitalAnalog),
                Is.True);
        }

        [TestCase(MockInstrumentKind.RoundMeter)]
        [TestCase(MockInstrumentKind.ToggleSwitch)]
        [TestCase(MockInstrumentKind.PushButton)]
        [TestCase(MockInstrumentKind.IndicatorLamp)]
        [TestCase(MockInstrumentKind.WindowMeter)]
        [TestCase(MockInstrumentKind.WindowPanel)]
        [TestCase(MockInstrumentKind.StatusIndicator)]
        public void DisplayAndCompactControls_SupportAllSurfaces(MockInstrumentKind kind)
        {
            Assert.That(
                MockInstrumentCatalog.SupportsSurface(kind, SurfaceKind.Wall),
                Is.True);
            Assert.That(
                MockInstrumentCatalog.SupportsSurface(kind, SurfaceKind.Floor),
                Is.True);
            Assert.That(
                MockInstrumentCatalog.SupportsSurface(kind, SurfaceKind.Ceiling),
                Is.True);
        }
    }
}
