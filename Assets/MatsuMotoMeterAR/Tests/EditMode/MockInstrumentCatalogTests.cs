using System.Collections.Generic;
using MatsuMotoMeterAR.Anchors;
using MatsuMotoMeterAR.Instruments;
using NUnit.Framework;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class MockInstrumentCatalogTests
    {
        [Test]
        public void MeterSweep_CoversFullDialScale()
        {
            Assert.That(
                InstrumentGreyboxSpecification.MeterSweepDegrees,
                Is.EqualTo(115f));
        }

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
        [TestCase(MockInstrumentKind.RoundMeterMedium, "meter.round.medium")]
        [TestCase(MockInstrumentKind.RoundMeterLarge, "meter.round.large")]
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

        [Test]
        public void Cycle_UsesFunctionalObjectOrder()
        {
            Assert.That(
                MockInstrumentCatalog.Cycle(MockInstrumentKind.RoundMeter, 1),
                Is.EqualTo(MockInstrumentKind.RoundMeterMedium));
            Assert.That(
                MockInstrumentCatalog.Cycle(
                    MockInstrumentKind.WindowMeter,
                    1),
                Is.EqualTo(MockInstrumentKind.IndicatorLamp));
            Assert.That(
                MockInstrumentCatalog.Cycle(
                    MockInstrumentKind.WindowPanel,
                    1),
                Is.EqualTo(MockInstrumentKind.ToggleSwitch));
            Assert.That(
                MockInstrumentCatalog.Cycle(
                    MockInstrumentKind.RotaryKnob,
                    1),
                Is.EqualTo(MockInstrumentKind.Lever));
        }

        [Test]
        public void CategoryJump_MovesToAdjacentCategoryStart()
        {
            Assert.That(
                MockInstrumentCatalog.JumpCategory(
                    MockInstrumentKind.RoundMeterLarge,
                    1),
                Is.EqualTo(MockInstrumentKind.IndicatorLamp));
            Assert.That(
                MockInstrumentCatalog.JumpCategory(
                    MockInstrumentKind.StatusIndicator,
                    1),
                Is.EqualTo(MockInstrumentKind.ToggleSwitch));
            Assert.That(
                MockInstrumentCatalog.JumpCategory(
                    MockInstrumentKind.ToggleSwitch,
                    -1),
                Is.EqualTo(MockInstrumentKind.IndicatorLamp));
            Assert.That(
                MockInstrumentCatalog.JumpCategory(
                    MockInstrumentKind.RoundMeter,
                    -1),
                Is.EqualTo(MockInstrumentKind.Lever));
        }

        [TestCase(MockInstrumentKind.Lever)]
        [TestCase(MockInstrumentKind.RotaryKnob)]
        [TestCase(MockInstrumentKind.ThrottleLever)]
        [TestCase(MockInstrumentKind.PowerSlider)]
        public void ManualControls_SupportEveryPlacementSurface(
            MockInstrumentKind kind)
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
            Assert.That(
                MockInstrumentCatalog.SupportsSurface(kind, SurfaceKind.Plane),
                Is.True);
            Assert.That(
                MockInstrumentCatalog.SupportsSurface(kind, SurfaceKind.Volume),
                Is.True);
        }

        [Test]
        public void AuthoredMotionControls_ArePlacementReadyInEveryTheme()
        {
            for (var themeIndex = 0;
                 themeIndex < MockInstrumentThemeCatalog.Count;
                 themeIndex++)
            {
                var theme = (MockInstrumentTheme)themeIndex;
                Assert.That(
                    MockInstrumentFactory.IsPlacementReady(
                        MockInstrumentKind.ThrottleLever,
                        theme),
                    Is.True);
                Assert.That(
                    MockInstrumentFactory.IsPlacementReady(
                        MockInstrumentKind.PowerSlider,
                        theme),
                    Is.True);
                Assert.That(
                    MockInstrumentFactory.IsPlacementReady(
                        MockInstrumentKind.Lever,
                        theme),
                    Is.True);
            }
        }

        [TestCase(MockInstrumentKind.RoundMeter)]
        [TestCase(MockInstrumentKind.RoundMeterMedium)]
        [TestCase(MockInstrumentKind.RoundMeterLarge)]
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
            Assert.That(
                MockInstrumentCatalog.SupportsSurface(kind, SurfaceKind.Plane),
                Is.True);
            Assert.That(
                MockInstrumentCatalog.SupportsSurface(kind, SurfaceKind.Volume),
                Is.True);
        }
    }
}
