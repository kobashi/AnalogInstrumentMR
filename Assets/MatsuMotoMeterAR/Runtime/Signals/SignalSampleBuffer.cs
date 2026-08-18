using System;

namespace MatsuMotoMeterAR.Signals
{
    public sealed class SignalSampleBuffer
    {
        private readonly float[] samples;
        private int nextIndex;

        public SignalSampleBuffer(int capacity)
        {
            if (capacity < 2)
                throw new ArgumentOutOfRangeException(nameof(capacity));
            samples = new float[capacity];
        }

        public int Capacity => samples.Length;
        public int Count { get; private set; }

        public void Add(float value)
        {
            samples[nextIndex] = value;
            nextIndex = (nextIndex + 1) % samples.Length;
            if (Count < samples.Length)
                Count++;
        }

        public void Clear()
        {
            nextIndex = 0;
            Count = 0;
        }

        public float GetOldestFirst(int index)
        {
            if (index < 0 || index >= Count)
                throw new ArgumentOutOfRangeException(nameof(index));

            var oldest = Count == samples.Length ? nextIndex : 0;
            return samples[(oldest + index) % samples.Length];
        }
    }
}
