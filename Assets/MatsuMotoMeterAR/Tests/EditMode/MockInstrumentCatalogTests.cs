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
                MockInstrumentCatalog.Cycle(MockInstrumentKind.IndicatorLamp, 1),
                Is.EqualTo(MockInstrumentKind.RoundMeter));
            Assert.That(
                MockInstrumentCatalog.Cycle(MockInstrumentKind.RoundMeter, -1),
                Is.EqualTo(MockInstrumentKind.IndicatorLamp));
        }

        [TestCase(MockInstrumentKind.Lever)]
        [TestCase(MockInstrumentKind.RotaryKnob)]
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

        [TestCase(MockInstrumentKind.RoundMeter)]
        [TestCase(MockInstrumentKind.ToggleSwitch)]
        [TestCase(MockInstrumentKind.PushButton)]
        [TestCase(MockInstrumentKind.IndicatorLamp)]
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
