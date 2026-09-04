using System.Collections.Generic;
using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    public enum ModularOscillatorWaveform
    {
        Sine = 0,
        Triangle = 1,
        Saw = 2,
        Square = 3
    }

    public enum ModularNoiseColor
    {
        White = 0,
        Pink = 1,
        Brown = 2
    }

    public abstract class ModularAudioNode
    {
        internal virtual float ReadOutput(
            string portId,
            float[] output,
            int frame)
        {
            return output[frame];
        }

        internal abstract void Process(
            float[] audioInput,
            float controlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate);
    }

    public sealed class ModularOscillatorNode : ModularAudioNode
    {
        private const float TwoPi = Mathf.PI * 2f;
        private float phase;

        public ModularOscillatorWaveform Waveform { get; set; }
        public float Frequency { get; set; } = 220f;
        public float Level { get; set; } = 0.2f;
        public bool Gate { get; set; } = true;

        internal override void Process(
            float[] audioInput,
            float controlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var baseFrequency = FiniteClamp(
                Frequency,
                0f,
                Mathf.Min(12000f, sampleRate * 0.45f),
                0f);
            var level = Gate
                ? FiniteClamp(Level, 0f, 1f, 0f)
                : 0f;
            var controlOctaves = FiniteClamp(
                controlInput,
                -1f,
                1f,
                0f) * 2f;
            for (var frame = 0; frame < frameCount; frame++)
            {
                var fmOctaves = FiniteClamp(
                    audioInput[frame],
                    -1f,
                    1f,
                    0f) * 2f;
                var frequency = Mathf.Clamp(
                    baseFrequency * Mathf.Pow(
                        2f,
                        controlOctaves + fmOctaves),
                    0f,
                    Mathf.Min(12000f, sampleRate * 0.45f));
                var phaseStep = TwoPi * frequency / sampleRate;
                var normalizedPhase = phase / TwoPi;
                var sample = Waveform switch
                {
                    ModularOscillatorWaveform.Triangle =>
                        1f - 4f * Mathf.Abs(normalizedPhase - 0.5f),
                    ModularOscillatorWaveform.Saw =>
                        normalizedPhase * 2f - 1f,
                    ModularOscillatorWaveform.Square =>
                        normalizedPhase < 0.5f ? 1f : -1f,
                    _ => Mathf.Sin(phase)
                };
                output[frame] = sample * level;
                phase += phaseStep;
                if (phase >= TwoPi)
                    phase -= TwoPi * Mathf.Floor(phase / TwoPi);
            }
        }

        private static float FiniteClamp(
            float value,
            float minimum,
            float maximum,
            float fallback)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? fallback
                : Mathf.Clamp(value, minimum, maximum);
        }
    }

    public sealed class ModularNoiseNode : ModularAudioNode
    {
        private uint state;
        private float pinkState;
        private float brownState;

        public ModularNoiseNode(uint seed = 0x51f15e5du)
        {
            state = seed == 0u ? 1u : seed;
        }

        public ModularNoiseColor Color { get; set; }
        public float Level { get; set; } = 0.15f;
        public bool Gate { get; set; } = true;

        internal override void Process(
            float[] audioInput,
            float controlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var level = Gate && !float.IsNaN(Level) &&
                        !float.IsInfinity(Level)
                ? Mathf.Clamp01(Level)
                : 0f;
            for (var frame = 0; frame < frameCount; frame++)
            {
                var white = NextWhite();
                pinkState = pinkState * 0.94f + white * 0.06f;
                brownState = Mathf.Clamp(
                    brownState * 0.997f + white * 0.018f,
                    -1f,
                    1f);
                var sample = Color switch
                {
                    ModularNoiseColor.Pink => pinkState * 2.7f,
                    ModularNoiseColor.Brown => brownState,
                    _ => white
                };
                output[frame] = Mathf.Clamp(sample, -1f, 1f) * level;
            }
        }

        private float NextWhite()
        {
            state ^= state << 13;
            state ^= state >> 17;
            state ^= state << 5;
            return state / (float)uint.MaxValue * 2f - 1f;
        }
    }

    public sealed class ModularAudioOutputNode : ModularAudioNode
    {
        public float Gain { get; set; } = 1f;
        public float Limit { get; set; } = 0.85f;
        public bool Muted { get; set; }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var gain = !Muted && !float.IsNaN(Gain) &&
                       !float.IsInfinity(Gain)
                ? Mathf.Clamp(Gain, 0f, 4f)
                : 0f;
            var limit = !float.IsNaN(Limit) &&
                        !float.IsInfinity(Limit)
                ? Mathf.Clamp(Limit, 0.05f, 1f)
                : 0.85f;
            for (var frame = 0; frame < frameCount; frame++)
                output[frame] = Mathf.Clamp(
                    audioInput[frame] * gain,
                    -limit,
                    limit);
        }
    }

    public sealed class ModularLfoNode : ModularAudioNode
    {
        private const float TwoPi = Mathf.PI * 2f;
        private float phase;

        public ModularOscillatorWaveform Waveform { get; set; }
        public float Frequency { get; set; } = 1f;
        public float Depth { get; set; } = 0.8f;

        internal override void Process(
            float[] audioInput,
            float controlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var frequency = FiniteClamp(
                Frequency,
                0.01f,
                40f,
                1f);
            var depth = FiniteClamp(Depth, 0f, 1f, 0f);
            var rateScale = Mathf.Pow(
                2f,
                FiniteClamp(controlInput, -1f, 1f, 0f) * 2f);
            var phaseStep = TwoPi * frequency * rateScale / sampleRate;
            for (var frame = 0; frame < frameCount; frame++)
            {
                var normalizedPhase = phase / TwoPi;
                var sample = Waveform switch
                {
                    ModularOscillatorWaveform.Triangle =>
                        1f - 4f * Mathf.Abs(normalizedPhase - 0.5f),
                    ModularOscillatorWaveform.Saw =>
                        normalizedPhase * 2f - 1f,
                    ModularOscillatorWaveform.Square =>
                        normalizedPhase < 0.5f ? 1f : -1f,
                    _ => Mathf.Sin(phase)
                };
                output[frame] = sample * depth;
                phase += phaseStep;
                if (phase >= TwoPi)
                    phase -= TwoPi * Mathf.Floor(phase / TwoPi);
            }
        }

        private static float FiniteClamp(
            float value,
            float minimum,
            float maximum,
            float fallback)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? fallback
                : Mathf.Clamp(value, minimum, maximum);
        }
    }

    public sealed class ModularSequencerNode : ModularAudioNode
    {
        private readonly float[] steps =
            ModularAudioParameterPolicy.CreateDefaultSequencerSteps();
        private double internalPhase;
        private float previousClock;
        private int currentStep;

        public int StepCount { get; set; } = 8;
        public float TempoBpm { get; set; } = 120f;
        public int CurrentStep => currentStep;
        public bool UsesExternalClock { get; private set; }

        public float GetStepValue(int index)
        {
            return steps[Mathf.Clamp(
                index,
                0,
                ModularAudioParameterPolicy.SequencerStepCapacity - 1)];
        }

        public void SetStepValue(int index, float value)
        {
            if (index < 0 ||
                index >= ModularAudioParameterPolicy.SequencerStepCapacity)
                return;
            steps[index] =
                ModularAudioParameterPolicy.NormalizeStepValue(value);
        }

        public void SetStepValues(IReadOnlyList<float> values)
        {
            for (var index = 0;
                 index < ModularAudioParameterPolicy.SequencerStepCapacity;
                 index++)
            {
                SetStepValue(
                    index,
                    values != null && index < values.Count
                        ? values[index]
                        : ModularAudioParameterPolicy
                            .DefaultSequencerStepValue(index));
            }
        }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var stepCount = StepCount <= 8 ? 8 : 16;
            currentStep %= stepCount;
            UsesExternalClock = hasClockInput;
            var tempo = float.IsNaN(TempoBpm) ||
                        float.IsInfinity(TempoBpm)
                ? 120f
                : Mathf.Clamp(TempoBpm, 20f, 300f);
            var internalStepRate = tempo / 15f;
            for (var frame = 0; frame < frameCount; frame++)
            {
                if (hasClockInput)
                {
                    var clock = Mathf.Clamp(
                        clockInput[frame],
                        -1f,
                        1f);
                    if (clock > 0f && previousClock <= 0f)
                        currentStep = (currentStep + 1) % stepCount;
                    previousClock = clock;
                }
                else
                {
                    internalPhase += internalStepRate / sampleRate;
                    while (internalPhase >= 1.0)
                    {
                        internalPhase -= 1.0;
                        currentStep = (currentStep + 1) % stepCount;
                    }
                    previousClock = 0f;
                }
                output[frame] = steps[currentStep];
            }
        }
    }

    public sealed class ModularDelayNode : ModularAudioNode
    {
        public const float MinimumDelaySeconds = 0.02f;
        public const float MaximumDelaySeconds = 0.75f;
        public const float MaximumFeedback = 0.92f;
        private const int DelayBufferCapacity = 96000;

        private readonly float[] delayBuffer =
            new float[DelayBufferCapacity];
        private int writeIndex;

        public float DelaySeconds { get; set; } = 0.25f;
        public float Feedback { get; set; } = 0.42f;
        public float Mix { get; set; } = 1f;

        internal override void Process(
            float[] audioInput,
            float controlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var delaySeconds = FiniteClamp(
                DelaySeconds,
                MinimumDelaySeconds,
                MaximumDelaySeconds,
                0.25f);
            var timeModulation = FiniteClamp(
                controlInput,
                -1f,
                1f,
                0f) * 0.2f;
            delaySeconds = Mathf.Clamp(
                delaySeconds + timeModulation,
                MinimumDelaySeconds,
                MaximumDelaySeconds);
            var delaySamples = Mathf.Clamp(
                Mathf.RoundToInt(delaySeconds * sampleRate),
                1,
                DelayBufferCapacity - 1);
            var feedback = FiniteClamp(
                Feedback,
                0f,
                MaximumFeedback,
                0f);
            var mix = FiniteClamp(Mix, 0f, 1f, 1f);
            for (var frame = 0; frame < frameCount; frame++)
            {
                var input = FiniteClamp(
                    audioInput[frame],
                    -1f,
                    1f,
                    0f);
                var readIndex = writeIndex - delaySamples;
                if (readIndex < 0)
                    readIndex += DelayBufferCapacity;
                var delayed = delayBuffer[readIndex];
                delayBuffer[writeIndex] = Mathf.Clamp(
                    input + delayed * feedback,
                    -1f,
                    1f);
                output[frame] = Mathf.Clamp(
                    Mathf.Lerp(input, delayed, mix),
                    -1f,
                    1f);
                writeIndex++;
                if (writeIndex >= DelayBufferCapacity)
                    writeIndex = 0;
            }
        }

        private static float FiniteClamp(
            float value,
            float minimum,
            float maximum,
            float fallback)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? fallback
                : Mathf.Clamp(value, minimum, maximum);
        }
    }

    public sealed class ModularMeterSourceNode : ModularAudioNode
    {
        private const float TwoPi = Mathf.PI * 2f;
        private float phase;

        public float Value { get; set; } = 0.5f;

        internal override float ReadOutput(
            string portId,
            float[] output,
            int frame)
        {
            return portId == "value.out"
                ? FiniteClamp01(Value, 0f)
                : base.ReadOutput(portId, output, frame);
        }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var value = FiniteClamp01(Value, 0f);
            var frequency = Mathf.Lerp(42f, 520f, value * value);
            var level = Mathf.Lerp(0.025f, 0.11f, value);
            var phaseStep = TwoPi * frequency / sampleRate;
            for (var frame = 0; frame < frameCount; frame++)
            {
                var motor = Mathf.Sin(phase) * 0.72f +
                            Mathf.Sin(phase * 2.03f) * 0.20f +
                            Mathf.Sin(phase * 4.11f) * 0.08f;
                output[frame] = Mathf.Clamp(motor * level, -1f, 1f);
                phase += phaseStep;
                if (phase >= TwoPi)
                    phase -= TwoPi * Mathf.Floor(phase / TwoPi);
            }
        }

        private static float FiniteClamp01(float value, float fallback)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? fallback
                : Mathf.Clamp01(value);
        }
    }

    public sealed class ModularTrendSourceNode : ModularAudioNode
    {
        private const float TwoPi = Mathf.PI * 2f;
        private float phase;
        private uint noiseState = 0x7f4a7c15u;

        public float Value { get; set; } = 0.5f;
        public float Slope { get; set; }
        public float Spread { get; set; }
        public int ValidInputCount { get; set; }
        public bool HasValidInput { get; set; }

        internal override float ReadOutput(
            string portId,
            float[] output,
            int frame)
        {
            return portId switch
            {
                "value.out" => FiniteClamp(Value, 0f, 1f, 0f),
                "slope.out" => FiniteClamp(Slope, -1f, 1f, 0f),
                "spread.out" => FiniteClamp(Spread, 0f, 1f, 0f),
                _ => base.ReadOutput(portId, output, frame)
            };
        }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            if (!HasValidInput || ValidInputCount <= 0)
            {
                for (var frame = 0; frame < frameCount; frame++)
                    output[frame] = 0f;
                return;
            }

            var value = FiniteClamp(Value, 0f, 1f, 0f);
            var slope = FiniteClamp(Slope, -1f, 1f, 0f);
            var spread = FiniteClamp(Spread, 0f, 1f, 0f);
            var frequency = Mathf.Lerp(72f, 690f, value) *
                            Mathf.Pow(2f, slope * 0.35f);
            var phaseStep = TwoPi * frequency / sampleRate;
            var level = Mathf.Lerp(0.045f, 0.12f, spread);
            for (var frame = 0; frame < frameCount; frame++)
            {
                var tonal = Mathf.Sin(phase + Mathf.Sin(phase * 0.13f) *
                    slope * 0.8f);
                var noise = NextWhite() * spread * 0.34f;
                output[frame] = Mathf.Clamp(
                    (tonal * (1f - spread * 0.25f) + noise) * level,
                    -1f,
                    1f);
                phase += phaseStep;
                if (phase >= TwoPi)
                    phase -= TwoPi * Mathf.Floor(phase / TwoPi);
            }
        }

        private float NextWhite()
        {
            noiseState ^= noiseState << 13;
            noiseState ^= noiseState >> 17;
            noiseState ^= noiseState << 5;
            return noiseState / (float)uint.MaxValue * 2f - 1f;
        }

        private static float FiniteClamp(
            float value,
            float minimum,
            float maximum,
            float fallback)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? fallback
                : Mathf.Clamp(value, minimum, maximum);
        }
    }

    public sealed class ModularPanelSourceNode : ModularAudioNode
    {
        private const float TwoPi = Mathf.PI * 2f;
        private float phase;
        private float modulationPhase;
        private uint noiseState = 0xc2b2ae35u;

        public float Energy { get; set; } = 0.5f;
        public float Balance { get; set; } = 1f;
        public float Phase { get; set; }
        public float Detail { get; set; }
        public int ConnectedCount { get; set; }
        public bool HasValidInput { get; set; }

        internal override float ReadOutput(
            string portId,
            float[] output,
            int frame)
        {
            return portId switch
            {
                "energy.out" => FiniteClamp(Energy, 0f, 1f, 0f),
                "balance.out" => FiniteClamp(Balance, 0f, 2f, 1f),
                "phase.out" => FiniteClamp(Phase, -Mathf.PI * 2f,
                    Mathf.PI * 2f, 0f),
                "detail.out" => FiniteClamp(Detail, 0f, 1f, 0f),
                _ => base.ReadOutput(portId, output, frame)
            };
        }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            if (!HasValidInput || ConnectedCount <= 0)
            {
                for (var frame = 0; frame < frameCount; frame++)
                    output[frame] = 0f;
                return;
            }

            var energy = FiniteClamp(Energy, 0f, 1f, 0f);
            var balance = FiniteClamp(Balance, 0.6f, 1.4f, 1f);
            var panelPhase = FiniteClamp(
                Phase,
                -Mathf.PI * 2f,
                Mathf.PI * 2f,
                0f);
            var detail = FiniteClamp(Detail, 0f, 1f, 0f);
            var frequency = Mathf.Lerp(52f, 360f, energy) * balance;
            var modulationRate = 0.18f + Mathf.Abs(panelPhase) * 0.12f;
            var phaseStep = TwoPi * frequency / sampleRate;
            var modulationStep = TwoPi * modulationRate / sampleRate;
            var level = Mathf.Lerp(0.04f, 0.13f, energy);
            for (var frame = 0; frame < frameCount; frame++)
            {
                var modulation = Mathf.Sin(
                    modulationPhase + panelPhase) *
                    (0.15f + detail * 0.65f);
                var tonal = Mathf.Sin(phase + modulation);
                tonal += Mathf.Sin(phase * (1.5f + balance * 0.5f) -
                    panelPhase) * Mathf.Lerp(0.08f, 0.30f, detail);
                var noise = NextWhite() * detail * 0.18f;
                output[frame] = Mathf.Clamp(
                    (tonal * 0.72f + noise) * level,
                    -1f,
                    1f);
                phase += phaseStep;
                modulationPhase += modulationStep;
                if (phase >= TwoPi)
                    phase -= TwoPi * Mathf.Floor(phase / TwoPi);
                if (modulationPhase >= TwoPi)
                    modulationPhase -= TwoPi;
            }
        }

        private float NextWhite()
        {
            noiseState ^= noiseState << 13;
            noiseState ^= noiseState >> 17;
            noiseState ^= noiseState << 5;
            return noiseState / (float)uint.MaxValue * 2f - 1f;
        }

        private static float FiniteClamp(
            float value,
            float minimum,
            float maximum,
            float fallback)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? fallback
                : Mathf.Clamp(value, minimum, maximum);
        }
    }
}
