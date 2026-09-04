using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    public static class ModularAudioParameterPolicy
    {
        public const int SequencerStepCapacity = 16;
        public const float SequencerStepIncrement = 0.05f;

        private static readonly float[] DefaultSequencerSteps =
        {
            -0.50f, 0.00f, 0.45f, -0.15f,
            0.65f, 0.20f, -0.35f, 0.35f,
            -0.60f, -0.05f, 0.55f, 0.10f,
            0.75f, 0.30f, -0.25f, 0.50f
        };

        public static bool SupportsEditing(MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.AudioOscillator ||
                   kind == MockInstrumentKind.AudioNoise ||
                   kind == MockInstrumentKind.AudioLfo ||
                   kind == MockInstrumentKind.AudioSequencer;
        }

        public static int NormalizeWaveform(int value)
        {
            return value >= (int)ModularOscillatorWaveform.Sine &&
                   value <= (int)ModularOscillatorWaveform.Square
                ? value
                : (int)ModularOscillatorWaveform.Sine;
        }

        public static int NormalizeNoiseColor(int value)
        {
            return value >= (int)ModularNoiseColor.White &&
                   value <= (int)ModularNoiseColor.Brown
                ? value
                : (int)ModularNoiseColor.White;
        }

        public static int CycleWaveform(int current, int direction)
        {
            const int count = 4;
            current = NormalizeWaveform(current);
            return (current + (direction < 0 ? count - 1 : 1)) % count;
        }

        public static int CycleNoiseColor(int current, int direction)
        {
            const int count = 3;
            current = NormalizeNoiseColor(current);
            return (current + (direction < 0 ? count - 1 : 1)) % count;
        }

        public static int CycleStepIndex(
            int current,
            int stepCount,
            int direction)
        {
            stepCount = stepCount <= 8 ? 8 : SequencerStepCapacity;
            current = Mathf.Clamp(current, 0, stepCount - 1);
            return (current + (direction < 0 ? stepCount - 1 : 1)) %
                   stepCount;
        }

        public static float AdjustStepValue(float value, int direction)
        {
            value = NormalizeStepValue(value);
            return NormalizeStepValue(
                value + (direction < 0
                    ? -SequencerStepIncrement
                    : SequencerStepIncrement));
        }

        public static float NormalizeStepValue(float value)
        {
            if (float.IsNaN(value) || float.IsInfinity(value))
                return 0f;
            var quantized = Mathf.Round(
                value / SequencerStepIncrement) *
                SequencerStepIncrement;
            return Mathf.Clamp(quantized, -1f, 1f);
        }

        public static float DefaultSequencerStepValue(int index)
        {
            return DefaultSequencerSteps[
                Mathf.Clamp(index, 0, SequencerStepCapacity - 1)];
        }

        public static float[] CreateDefaultSequencerSteps()
        {
            return (float[])DefaultSequencerSteps.Clone();
        }

        public static float[] NormalizeSequencerSteps(
            IReadOnlyList<float> source)
        {
            var normalized = CreateDefaultSequencerSteps();
            if (source == null)
                return normalized;
            var count = Mathf.Min(source.Count, SequencerStepCapacity);
            for (var index = 0; index < count; index++)
                normalized[index] = NormalizeStepValue(source[index]);
            return normalized;
        }
    }
}
