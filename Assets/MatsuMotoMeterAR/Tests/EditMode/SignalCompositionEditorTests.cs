using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Signals;
using NUnit.Framework;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class SignalCompositionEditorTests
    {
        [Test]
        public void CycleKind_WrapsBothDirectionsAndRepairsUnknown()
        {
            Assert.That(
                SignalCompositionEditor.CycleKind(
                    (int)SignalCompositionKind.Priority,
                    1),
                Is.EqualTo(SignalCompositionKind.Average));
            Assert.That(
                SignalCompositionEditor.CycleKind(
                    (int)SignalCompositionKind.Average,
                    -1),
                Is.EqualTo(SignalCompositionKind.Priority));
            Assert.That(
                SignalCompositionEditor.CycleKind(999, 1),
                Is.EqualTo(SignalCompositionKind.Sum));
        }

        [Test]
        public void CyclePriority_ClampsThenWrapsZeroToThree()
        {
            Assert.That(
                SignalCompositionEditor.CyclePriority(3, 1),
                Is.Zero);
            Assert.That(
                SignalCompositionEditor.CyclePriority(0, -1),
                Is.EqualTo(3));
            Assert.That(
                SignalCompositionEditor.CyclePriority(99, -1),
                Is.EqualTo(2));
        }

        [Test]
        public void CanConfigureTarget_ExcludesWindowPanelSlotSemantics()
        {
            Assert.That(
                SignalCompositionEditor.CanConfigureTarget(
                    MockInstrumentKind.RoundMeter),
                Is.True);
            Assert.That(
                SignalCompositionEditor.CanConfigureTarget(
                    MockInstrumentKind.TrendMonitor),
                Is.True);
            Assert.That(
                SignalCompositionEditor.CanConfigureTarget(
                    MockInstrumentKind.WindowPanel),
                Is.False);
            Assert.That(
                SignalCompositionEditor.CanConfigureTarget(
                    MockInstrumentKind.Lever),
                Is.False);
        }
    }
}
