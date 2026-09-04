using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    public enum InstrumentContinuousAudioMode
    {
        None = 0,
        Meter = 1,
        TrendMonitor = 2,
        WindowPanel = 3
    }

    public sealed class InstrumentContinuousAudioSynth
    {
        private const float TwoPi = Mathf.PI * 2f;
        private readonly InstrumentContinuousAudioMode mode;
        private volatile float targetValue;
        private volatile float targetSpread;
        private volatile float targetSlope;
        private volatile float targetEnergy;
        private volatile float targetBalance = 1f;
        private volatile float targetPhase;
        private volatile float targetDetail;
        private volatile int targetInputCount;
        private volatile int targetPreset;
        private volatile int targetActive;
        private float smoothedValue;
        private float smoothedGain;
        private float smoothedPreset;
        private float oscillatorPhase;
        private float modulationPhase;
        private uint noiseState = 0x6d2b79f5u;

        public InstrumentContinuousAudioSynth(
            InstrumentContinuousAudioMode synthesisMode)
        {
            mode = synthesisMode;
        }

        public InstrumentContinuousAudioMode Mode => mode;
        public float SmoothedValue => smoothedValue;
        public float SmoothedGain => smoothedGain;

        public static InstrumentContinuousAudioMode ModeFor(
            Instruments.MockInstrumentKind kind)
        {
            return kind switch
            {
                Instruments.MockInstrumentKind.RoundMeter or
                Instruments.MockInstrumentKind.RoundMeterMedium or
                Instruments.MockInstrumentKind.RoundMeterLarge or
                Instruments.MockInstrumentKind.WindowMeter =>
                    InstrumentContinuousAudioMode.Meter,
                Instruments.MockInstrumentKind.TrendMonitor =>
                    InstrumentContinuousAudioMode.TrendMonitor,
                Instruments.MockInstrumentKind.WindowPanel =>
                    InstrumentContinuousAudioMode.WindowPanel,
                _ => InstrumentContinuousAudioMode.None
            };
        }

        public static float MeterFrequency(float value)
        {
            return Mathf.Lerp(42f, 228f, Mathf.Clamp01(value));
        }

        public void SetMeter(float value)
        {
            targetValue = Finite01(value);
            targetActive = 1;
        }

        public void SetTrend(
            float composedValue,
            float slope,
            float spread,
            int validInputCount,
            bool hasValidInput)
        {
            targetValue = Finite01(composedValue);
            targetSlope = Finite01(Mathf.Abs(slope));
            targetSpread = Finite01(spread);
            targetInputCount = Mathf.Clamp(validInputCount, 0, 4);
            targetActive = hasValidInput && targetInputCount > 0 ? 1 : 0;
        }

        public void SetWindowPanel(
            float energy,
            float balance,
            float phase,
            float detail,
            int connectedCount,
            int preset,
            bool hasValidInput)
        {
            targetEnergy = Finite01(Mathf.InverseLerp(0.45f, 0.95f, energy));
            targetBalance = Finite(
                Mathf.Clamp(balance, 0.6f, 1.4f),
                1f);
            targetPhase = Finite(
                Mathf.Clamp(phase, -Mathf.PI, Mathf.PI),
                0f);
            targetDetail = Finite01(detail);
            targetInputCount = Mathf.Clamp(connectedCount, 0, 4);
            targetPreset = Mathf.Clamp(preset, 0, 2);
            targetActive = hasValidInput && targetInputCount > 0 ? 1 : 0;
        }

        public void Fill(float[] data, int channels, int sampleRate)
        {
            if (data == null || data.Length == 0 || channels <= 0)
                return;

            sampleRate = Mathf.Max(8000, sampleRate);
            var valueBlend = 1f - Mathf.Exp(-1f / (0.075f * sampleRate));
            var gainBlend = 1f - Mathf.Exp(-1f / (0.12f * sampleRate));
            var presetBlend = 1f - Mathf.Exp(-1f / (0.16f * sampleRate));
            for (var frame = 0; frame < data.Length; frame += channels)
            {
                smoothedValue += (TargetPrimaryValue() - smoothedValue) * valueBlend;
                smoothedGain += (TargetGain() - smoothedGain) * gainBlend;
                smoothedPreset += (targetPreset - smoothedPreset) * presetBlend;
                var sample = RenderSample(sampleRate) * smoothedGain;
                sample = Mathf.Clamp(sample, -0.18f, 0.18f);
                for (var channel = 0;
                     channel < channels && frame + channel < data.Length;
                     channel++)
                {
                    data[frame + channel] = sample;
                }
            }
        }

        private float TargetPrimaryValue()
        {
            return mode == InstrumentContinuousAudioMode.WindowPanel
                ? targetEnergy
                : targetValue;
        }

        private float TargetGain()
        {
            if (targetActive == 0)
                return 0f;
            return mode switch
            {
                InstrumentContinuousAudioMode.Meter =>
                    Mathf.Lerp(0.006f, 0.024f, targetValue),
                InstrumentContinuousAudioMode.TrendMonitor =>
                    Mathf.Lerp(0.012f, 0.038f, targetValue),
                InstrumentContinuousAudioMode.WindowPanel =>
                    Mathf.Lerp(0.010f, 0.042f, targetEnergy),
                _ => 0f
            };
        }

        private float RenderSample(int sampleRate)
        {
            return mode switch
            {
                InstrumentContinuousAudioMode.Meter => RenderMeter(sampleRate),
                InstrumentContinuousAudioMode.TrendMonitor => RenderTrend(sampleRate),
                InstrumentContinuousAudioMode.WindowPanel => RenderPanel(sampleRate),
                _ => 0f
            };
        }

        private float RenderMeter(int sampleRate)
        {
            var frequency = MeterFrequency(smoothedValue);
            AdvancePhase(ref oscillatorPhase, frequency, sampleRate);
            AdvancePhase(ref modulationPhase, frequency * 0.137f, sampleRate);
            var fundamental = Mathf.Sin(oscillatorPhase);
            var rotation = Mathf.Sin(
                oscillatorPhase * 2f + Mathf.Sin(modulationPhase) * 0.18f);
            return fundamental * 0.72f + rotation * 0.28f;
        }

        private float RenderTrend(int sampleRate)
        {
            var frequency = Mathf.Lerp(34f, 142f, smoothedValue);
            var modulation = 0.4f + targetSlope * 7f;
            AdvancePhase(ref oscillatorPhase, frequency, sampleRate);
            AdvancePhase(ref modulationPhase, modulation, sampleRate);
            var harmonicDensity = Mathf.Clamp(targetInputCount, 1, 4);
            var tonal = Mathf.Sin(
                oscillatorPhase + Mathf.Sin(modulationPhase) * targetSlope);
            tonal += Mathf.Sin(oscillatorPhase * 2.01f) *
                     (0.12f * harmonicDensity);
            tonal += Mathf.Sin(oscillatorPhase * 3.97f) *
                     (0.05f * (harmonicDensity - 1));
            var roughness = NextNoise() * targetSpread * 0.32f;
            return tonal * 0.52f + roughness;
        }

        private float RenderPanel(int sampleRate)
        {
            var presetFrequency = smoothedPreset <= 1f
                ? Mathf.Lerp(1f, 0.86f, smoothedPreset)
                : Mathf.Lerp(0.86f, 1.17f, smoothedPreset - 1f);
            var frequency = Mathf.Lerp(29f, 118f, smoothedValue) *
                            presetFrequency;
            var modulationRate = 0.25f + Mathf.Abs(targetPhase) * 0.42f;
            AdvancePhase(ref oscillatorPhase, frequency, sampleRate);
            AdvancePhase(ref modulationPhase, modulationRate, sampleRate);
            var phaseModulation = Mathf.Sin(modulationPhase + targetPhase);
            var first = Mathf.Sin(
                oscillatorPhase + phaseModulation * (0.25f + targetDetail));
            var secondRatio = smoothedPreset <= 1f
                ? 2.003f
                : Mathf.Lerp(2.003f, 1.501f, smoothedPreset - 1f);
            var second = Mathf.Sin(
                oscillatorPhase * secondRatio - targetPhase) *
                Mathf.Lerp(0.12f, 0.38f, targetBalance - 0.6f);
            var noise = NextNoise() * targetDetail * 0.18f;
            return first * 0.56f + second + noise;
        }

        private static void AdvancePhase(
            ref float phase,
            float frequency,
            int sampleRate)
        {
            phase += TwoPi * Mathf.Max(0f, frequency) / sampleRate;
            if (phase >= TwoPi)
                phase -= TwoPi;
        }

        private float NextNoise()
        {
            noiseState ^= noiseState << 13;
            noiseState ^= noiseState >> 17;
            noiseState ^= noiseState << 5;
            return (noiseState / (float)uint.MaxValue) * 2f - 1f;
        }

        private static float Finite01(float value)
        {
            return Mathf.Clamp01(Finite(value, 0f));
        }

        private static float Finite(float value, float fallback)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? fallback
                : value;
        }
    }
}
