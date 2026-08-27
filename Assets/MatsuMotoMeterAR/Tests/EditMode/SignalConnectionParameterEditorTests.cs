using MatsuMotoMeterAR.PlacementPersistence;
using MatsuMotoMeterAR.Signals;
using NUnit.Framework;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class SignalConnectionParameterEditorTests
    {
        [Test]
        public void RangeFields_CycleInBothDirections()
        {
            Assert.That(
                SignalConnectionParameterEditor.CycleField(
                    SignalTransformKind.Range,
                    SignalConnectionParameterField.InputMinimum,
                    -1),
                Is.EqualTo(
                    SignalConnectionParameterField.OutputMaximum));
            Assert.That(
                SignalConnectionParameterEditor.CycleField(
                    SignalTransformKind.Range,
                    SignalConnectionParameterField.OutputMaximum,
                    1),
                Is.EqualTo(
                    SignalConnectionParameterField.InputMinimum));
        }

        [Test]
        public void RangeAdjustment_PreservesMinimumSpan()
        {
            var draft = new SignalConnectionRecord
            {
                inputMinimum = 0.45f,
                inputMaximum = 0.5f,
                outputMinimum = 0.4f,
                outputMaximum = 0.45f
            };

            SignalConnectionParameterEditor.Adjust(
                draft,
                SignalConnectionParameterField.InputMinimum,
                1);
            SignalConnectionParameterEditor.Adjust(
                draft,
                SignalConnectionParameterField.OutputMaximum,
                -1);

            Assert.That(draft.inputMinimum, Is.EqualTo(0.45f).Within(0.0001f));
            Assert.That(draft.outputMaximum, Is.EqualTo(0.45f).Within(0.0001f));
        }

        [Test]
        public void ThresholdFields_CycleWithoutRangeFields()
        {
            Assert.That(
                SignalConnectionParameterEditor.CycleField(
                    SignalTransformKind.Threshold,
                    SignalConnectionParameterField.ThresholdValue,
                    1),
                Is.EqualTo(
                    SignalConnectionParameterField.ThresholdComparison));
            Assert.That(
                SignalConnectionParameterEditor.CycleField(
                    SignalTransformKind.Threshold,
                    SignalConnectionParameterField.ThresholdComparison,
                    1),
                Is.EqualTo(
                    SignalConnectionParameterField.ThresholdValue));
        }

        [Test]
        public void ThresholdComparison_AdjustsExplicitDirection()
        {
            var draft = new SignalConnectionRecord();

            SignalConnectionParameterEditor.Adjust(
                draft,
                SignalConnectionParameterField.ThresholdComparison,
                -1);
            Assert.That(
                draft.thresholdComparison,
                Is.EqualTo((int)SignalThresholdComparison.Below));

            SignalConnectionParameterEditor.Adjust(
                draft,
                SignalConnectionParameterField.ThresholdComparison,
                1);
            Assert.That(
                draft.thresholdComparison,
                Is.EqualTo((int)SignalThresholdComparison.Above));
        }
    }
}
