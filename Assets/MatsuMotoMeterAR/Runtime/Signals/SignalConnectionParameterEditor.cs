using MatsuMotoMeterAR.PlacementPersistence;
using UnityEngine;

namespace MatsuMotoMeterAR.Signals
{
    public enum SignalConnectionParameterField
    {
        InputMinimum,
        InputMaximum,
        OutputMinimum,
        OutputMaximum,
        ThresholdValue,
        ThresholdComparison
    }

    public static class SignalConnectionParameterEditor
    {
        public const float Step = 0.05f;
        public const float MinimumSpan = 0.05f;

        public static bool Supports(SignalTransformKind transform)
        {
            return transform == SignalTransformKind.Range ||
                   transform == SignalTransformKind.Threshold;
        }

        public static SignalConnectionParameterField FirstField(
            SignalTransformKind transform)
        {
            return transform == SignalTransformKind.Threshold
                ? SignalConnectionParameterField.ThresholdValue
                : SignalConnectionParameterField.InputMinimum;
        }

        public static SignalConnectionParameterField CycleField(
            SignalTransformKind transform,
            SignalConnectionParameterField current,
            int direction)
        {
            if (transform == SignalTransformKind.Threshold)
            {
                if (current != SignalConnectionParameterField.ThresholdValue &&
                    current != SignalConnectionParameterField.ThresholdComparison)
                {
                    return SignalConnectionParameterField.ThresholdValue;
                }
                return current == SignalConnectionParameterField.ThresholdValue
                    ? SignalConnectionParameterField.ThresholdComparison
                    : SignalConnectionParameterField.ThresholdValue;
            }

            var index = current switch
            {
                SignalConnectionParameterField.InputMinimum => 0,
                SignalConnectionParameterField.InputMaximum => 1,
                SignalConnectionParameterField.OutputMinimum => 2,
                SignalConnectionParameterField.OutputMaximum => 3,
                _ => 0
            };
            index = (index + (direction < 0 ? -1 : 1) + 4) % 4;
            return (SignalConnectionParameterField)index;
        }

        public static void Adjust(
            SignalConnectionRecord draft,
            SignalConnectionParameterField field,
            int direction)
        {
            if (draft == null || direction == 0)
                return;

            var delta = direction < 0 ? -Step : Step;
            switch (field)
            {
                case SignalConnectionParameterField.InputMinimum:
                    draft.inputMinimum = Mathf.Clamp(
                        draft.inputMinimum + delta,
                        0f,
                        draft.inputMaximum - MinimumSpan);
                    break;
                case SignalConnectionParameterField.InputMaximum:
                    draft.inputMaximum = Mathf.Clamp(
                        draft.inputMaximum + delta,
                        draft.inputMinimum + MinimumSpan,
                        1f);
                    break;
                case SignalConnectionParameterField.OutputMinimum:
                    draft.outputMinimum = Mathf.Clamp(
                        draft.outputMinimum + delta,
                        0f,
                        draft.outputMaximum - MinimumSpan);
                    break;
                case SignalConnectionParameterField.OutputMaximum:
                    draft.outputMaximum = Mathf.Clamp(
                        draft.outputMaximum + delta,
                        draft.outputMinimum + MinimumSpan,
                        1f);
                    break;
                case SignalConnectionParameterField.ThresholdValue:
                    draft.thresholdValue = Mathf.Clamp01(
                        draft.thresholdValue + delta);
                    break;
                case SignalConnectionParameterField.ThresholdComparison:
                    draft.thresholdComparison = direction < 0
                        ? (int)SignalThresholdComparison.Below
                        : (int)SignalThresholdComparison.Above;
                    break;
            }
        }

        public static string Label(SignalConnectionParameterField field)
        {
            return field switch
            {
                SignalConnectionParameterField.InputMinimum => "INPUT MIN",
                SignalConnectionParameterField.InputMaximum => "INPUT MAX",
                SignalConnectionParameterField.OutputMinimum => "OUTPUT MIN",
                SignalConnectionParameterField.OutputMaximum => "OUTPUT MAX",
                SignalConnectionParameterField.ThresholdValue => "THRESHOLD",
                SignalConnectionParameterField.ThresholdComparison => "COMPARE",
                _ => "PARAMETER"
            };
        }

        public static string Value(
            SignalConnectionRecord draft,
            SignalConnectionParameterField field)
        {
            if (draft == null)
                return "--";
            return field switch
            {
                SignalConnectionParameterField.InputMinimum =>
                    draft.inputMinimum.ToString("0.00"),
                SignalConnectionParameterField.InputMaximum =>
                    draft.inputMaximum.ToString("0.00"),
                SignalConnectionParameterField.OutputMinimum =>
                    draft.outputMinimum.ToString("0.00"),
                SignalConnectionParameterField.OutputMaximum =>
                    draft.outputMaximum.ToString("0.00"),
                SignalConnectionParameterField.ThresholdValue =>
                    draft.thresholdValue.ToString("0.00"),
                SignalConnectionParameterField.ThresholdComparison =>
                    draft.thresholdComparison ==
                        (int)SignalThresholdComparison.Below
                            ? "BELOW"
                            : "ABOVE",
                _ => "--"
            };
        }
    }
}
