using System;

namespace MatsuMotoMeterAR.Signals
{
    public enum SignalCompositionKind
    {
        Average = 0,
        Sum = 1,
        Minimum = 2,
        Maximum = 3,
        Priority = 4
    }

    public struct SignalCompositionAccumulator
    {
        private readonly SignalCompositionKind kind;
        private float sum;
        private float minimum;
        private float maximum;
        private float priorityValue;
        private int priority;
        private string priorityStableId;

        public SignalCompositionAccumulator(SignalCompositionKind kind)
        {
            this.kind = Enum.IsDefined(typeof(SignalCompositionKind), kind)
                ? kind
                : SignalCompositionKind.Average;
            sum = 0f;
            minimum = 1f;
            maximum = 0f;
            priorityValue = 0f;
            priority = int.MinValue;
            priorityStableId = null;
            ValidCount = 0;
        }

        public int ValidCount { get; private set; }

        public bool Add(float value, int inputPriority, string stableId)
        {
            if (float.IsNaN(value) || float.IsInfinity(value))
                return false;

            value = Clamp01(value);
            sum += value;
            if (ValidCount == 0)
            {
                minimum = value;
                maximum = value;
            }
            else
            {
                if (value < minimum)
                    minimum = value;
                if (value > maximum)
                    maximum = value;
            }

            if (ValidCount == 0 ||
                inputPriority > priority ||
                inputPriority == priority &&
                CompareStableIds(stableId, priorityStableId) < 0)
            {
                priorityValue = value;
                priority = inputPriority;
                priorityStableId = stableId;
            }

            ValidCount++;
            return true;
        }

        public bool TryGetValue(out float value)
        {
            if (ValidCount == 0)
            {
                value = 0f;
                return false;
            }

            value = kind switch
            {
                SignalCompositionKind.Sum => Clamp01(sum),
                SignalCompositionKind.Minimum => minimum,
                SignalCompositionKind.Maximum => maximum,
                SignalCompositionKind.Priority => priorityValue,
                _ => sum / ValidCount
            };
            return true;
        }

        private static int CompareStableIds(string left, string right)
        {
            if (left == null)
                return right == null ? 0 : 1;
            if (right == null)
                return -1;
            return string.CompareOrdinal(left, right);
        }

        private static float Clamp01(float value)
        {
            if (value < 0f)
                return 0f;
            return value > 1f ? 1f : value;
        }
    }
}
