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

    public enum ModularEnvelopeStage
    {
        Idle = 0,
        Attack = 1,
        Decay = 2,
        Sustain = 3,
        Release = 4
    }

    public enum ModularSequencerPlaybackMode
    {
        Clock = 0,
        StepTrigger = 1
    }

    public abstract class ModularAudioNode
    {
        private float[] gateInput;
        private float[] triggerInput;

        protected bool HasGateInput { get; private set; }
        protected bool HasTriggerInput { get; private set; }

        internal void SetDiscreteInputs(
            float[] gateValues,
            bool hasGateInput,
            float[] triggerValues,
            bool hasTriggerInput)
        {
            gateInput = gateValues;
            triggerInput = triggerValues;
            HasGateInput = hasGateInput;
            HasTriggerInput = hasTriggerInput;
        }

        protected float GateInput(int frame)
        {
            return HasGateInput && gateInput != null
                ? gateInput[frame]
                : 0f;
        }

        protected float TriggerInput(int frame)
        {
            return HasTriggerInput && triggerInput != null
                ? triggerInput[frame]
                : 0f;
        }

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
            bool hasControlInput,
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
            bool hasControlInput,
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
            var level = FiniteClamp(Level, 0f, 1f, 0f);
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
                var gateOpen = HasGateInput
                    ? GateInput(frame) > 0f
                    : Gate;
                output[frame] = sample * (gateOpen ? level : 0f);
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
        private const float PinkNormalizationGain = 2.7f;
        private const float BrownNormalizationGain = 3.6f;

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
            bool hasControlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var level = !float.IsNaN(Level) && !float.IsInfinity(Level)
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
                    ModularNoiseColor.Pink =>
                        pinkState * PinkNormalizationGain,
                    ModularNoiseColor.Brown =>
                        brownState * BrownNormalizationGain,
                    _ => white
                };
                var gateOpen = HasGateInput
                    ? GateInput(frame) > 0f
                    : Gate;
                output[frame] = gateOpen
                    ? Mathf.Clamp(sample, -1f, 1f) * level
                    : 0f;
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
            bool hasControlInput,
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
        private readonly float[] gateOutput =
            new float[ModularAudioGraph.MaximumBlockFrames];
        private readonly float[] triggerOutput =
            new float[ModularAudioGraph.MaximumBlockFrames];
        private float phase;
        private float previousTrigger;
        private bool previousGateOutput;

        public ModularOscillatorWaveform Waveform { get; set; }
        public float Frequency { get; set; } = 1f;
        public float Depth { get; set; } = 0.8f;
        public float GateLength { get; set; } = 0.5f;
        public float Phase01 => phase / TwoPi;

        internal override float ReadOutput(
            string portId,
            float[] output,
            int frame)
        {
            return portId switch
            {
                ModularAudioPatchPolicy.GateOutputPortId => gateOutput[frame],
                ModularAudioPatchPolicy.TriggerOutputPortId =>
                    triggerOutput[frame],
                _ => base.ReadOutput(portId, output, frame)
            };
        }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            bool hasControlInput,
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
            var gateLength = FiniteClamp(GateLength, 0.01f, 0.99f, 0.5f);
            var rateScale = Mathf.Pow(
                2f,
                FiniteClamp(controlInput, -1f, 1f, 0f) * 2f);
            var phaseStep = TwoPi * frequency * rateScale / sampleRate;
            for (var frame = 0; frame < frameCount; frame++)
            {
                var trigger = HasTriggerInput
                    ? TriggerInput(frame)
                    : 0f;
                if (trigger > 0f && previousTrigger <= 0f)
                {
                    phase = 0f;
                    previousGateOutput = false;
                }
                previousTrigger = trigger;
                var normalizedPhase = phase / TwoPi;
                var gateOpen = normalizedPhase < gateLength;
                gateOutput[frame] = gateOpen ? 1f : 0f;
                triggerOutput[frame] = gateOpen && !previousGateOutput
                    ? 1f
                    : 0f;
                previousGateOutput = gateOpen;
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
        private readonly float[] gateOutput =
            new float[ModularAudioGraph.MaximumBlockFrames];
        private readonly float[] triggerOutput =
            new float[ModularAudioGraph.MaximumBlockFrames];
        private double internalPhase;
        private float previousClock;
        private float previousStepTrigger;
        private int currentStep;
        private bool emitInitialTrigger = true;
        private ModularSequencerPlaybackMode playbackMode;

        public int StepCount { get; set; } = 8;
        public float TempoBpm { get; set; } = 120f;
        public float GateLength { get; set; } = 0.5f;
        public int CurrentStep => currentStep;
        public bool UsesExternalClock { get; private set; }
        public bool UsesTriggerStep { get; private set; }
        public ModularSequencerPlaybackMode PlaybackMode
        {
            get => playbackMode;
            set
            {
                var normalized = value ==
                                 ModularSequencerPlaybackMode.StepTrigger
                    ? ModularSequencerPlaybackMode.StepTrigger
                    : ModularSequencerPlaybackMode.Clock;
                if (playbackMode == normalized)
                    return;
                playbackMode = normalized;
                previousClock = 0f;
                previousStepTrigger = 0f;
            }
        }

        internal override float ReadOutput(
            string portId,
            float[] output,
            int frame)
        {
            return portId switch
            {
                ModularAudioPatchPolicy.GateOutputPortId => gateOutput[frame],
                ModularAudioPatchPolicy.TriggerOutputPortId =>
                    triggerOutput[frame],
                _ => base.ReadOutput(portId, output, frame)
            };
        }

        public float GetStepValue(int index)
        {
            return steps[Mathf.Clamp(
                index,
                0,
                ModularAudioParameterPolicy.SequencerStepCapacity - 1)];
        }

        public void SetStepValue(int index, float value)
        {
            SetStepValue(index, value, null);
        }

        public void SetStepValue(
            int index,
            float value,
            AdjustableParameterSetting range)
        {
            if (index < 0 ||
                index >= ModularAudioParameterPolicy.SequencerStepCapacity)
                return;
            steps[index] = range == null
                ? ModularAudioParameterPolicy.NormalizeStepValue(value)
                : AdjustableParameterPolicy.Quantize(value, range);
        }

        public void SetStepValues(IReadOnlyList<float> values)
        {
            SetStepValues(values, null);
        }

        public void SetStepValues(
            IReadOnlyList<float> values,
            AdjustableParameterSetting range)
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
                            .DefaultSequencerStepValue(index),
                    range);
            }
        }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            bool hasControlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var stepCount = StepCount <= 8 ? 8 : 16;
            currentStep %= stepCount;
            var triggerStepMode = PlaybackMode ==
                                  ModularSequencerPlaybackMode.StepTrigger;
            UsesExternalClock = !triggerStepMode && hasClockInput;
            UsesTriggerStep = triggerStepMode && HasTriggerInput;
            var tempo = float.IsNaN(TempoBpm) ||
                        float.IsInfinity(TempoBpm)
                ? 120f
                : Mathf.Clamp(TempoBpm, 20f, 300f);
            var internalStepRate = tempo / 15f;
            var gateLength = float.IsNaN(GateLength) ||
                             float.IsInfinity(GateLength)
                ? 0.5f
                : Mathf.Clamp(GateLength, 0.01f, 0.99f);
            for (var frame = 0; frame < frameCount; frame++)
            {
                var stepAdvanced = !triggerStepMode && emitInitialTrigger;
                emitInitialTrigger = false;
                if (triggerStepMode)
                {
                    var trigger = HasTriggerInput
                        ? Mathf.Clamp(TriggerInput(frame), 0f, 1f)
                        : 0f;
                    if (trigger > 0f && previousStepTrigger <= 0f)
                    {
                        currentStep = (currentStep + 1) % stepCount;
                        stepAdvanced = true;
                    }
                    previousStepTrigger = trigger;
                    previousClock = 0f;
                    internalPhase = 0.0;
                    gateOutput[frame] = trigger > 0f ? 1f : 0f;
                }
                else if (hasClockInput)
                {
                    var clock = Mathf.Clamp(
                        clockInput[frame],
                        -1f,
                        1f);
                    if (clock > 0f && previousClock <= 0f)
                    {
                        currentStep = (currentStep + 1) % stepCount;
                        stepAdvanced = true;
                    }
                    previousClock = clock;
                    gateOutput[frame] = clock > 0f ? 1f : 0f;
                }
                else
                {
                    internalPhase += internalStepRate / sampleRate;
                    while (internalPhase >= 1.0)
                    {
                        internalPhase -= 1.0;
                        currentStep = (currentStep + 1) % stepCount;
                        stepAdvanced = true;
                    }
                    previousClock = 0f;
                    gateOutput[frame] = internalPhase < gateLength ? 1f : 0f;
                }
                if (!triggerStepMode)
                    previousStepTrigger = 0f;
                triggerOutput[frame] = stepAdvanced ? 1f : 0f;
                output[frame] = steps[currentStep];
            }
        }
    }

    public sealed class ModularEnvelopeNode : ModularAudioNode
    {
        private float previousGate;
        private float previousTrigger;
        private float attackStep;
        private float releaseStep;
        private bool triggerOnly;

        public float AttackSeconds { get; set; } = 0.05f;
        public float DecaySeconds { get; set; } = 0.2f;
        public float SustainLevel { get; set; } = 0.7f;
        public float ReleaseSeconds { get; set; } = 0.35f;
        public bool ManualGate { get; set; } = true;
        public float CurrentLevel { get; private set; }
        public float LastBlockPeak { get; private set; }
        public ModularEnvelopeStage Stage { get; private set; }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            bool hasControlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var attack = FiniteClamp(
                AttackSeconds,
                0.001f,
                10f,
                0.05f);
            var decay = FiniteClamp(
                DecaySeconds,
                0.001f,
                10f,
                0.2f);
            var sustain = FiniteClamp(SustainLevel, 0f, 1f, 0.7f);
            var release = FiniteClamp(
                ReleaseSeconds,
                0.001f,
                10f,
                0.35f);
            LastBlockPeak = 0f;

            for (var frame = 0; frame < frameCount; frame++)
            {
                var gate = HasGateInput
                    ? (GateInput(frame) > 0f ? 1f : 0f)
                    : (ManualGate ? 1f : 0f);
                var trigger = HasTriggerInput
                    ? (TriggerInput(frame) > 0f ? 1f : 0f)
                    : 0f;
                var gateRose = gate > 0f && previousGate <= 0f;
                var gateFell = gate <= 0f && previousGate > 0f;
                var triggerRose = trigger > 0f && previousTrigger <= 0f;

                if (gateRose)
                {
                    triggerOnly = false;
                    BeginAttack(attack, sampleRate);
                }
                if (triggerRose)
                {
                    triggerOnly = gate <= 0f;
                    BeginAttack(attack, sampleRate);
                }
                if (gateFell && !triggerOnly)
                    BeginRelease(release, sampleRate);

                switch (Stage)
                {
                    case ModularEnvelopeStage.Attack:
                        CurrentLevel += attackStep;
                        if (CurrentLevel >= 1f)
                        {
                            CurrentLevel = 1f;
                            Stage = ModularEnvelopeStage.Decay;
                        }
                        break;
                    case ModularEnvelopeStage.Decay:
                        CurrentLevel -=
                            (1f - sustain) / (decay * sampleRate);
                        if (CurrentLevel <= sustain)
                        {
                            CurrentLevel = sustain;
                            if (gate > 0f && !triggerOnly)
                                Stage = ModularEnvelopeStage.Sustain;
                            else
                                BeginRelease(release, sampleRate);
                        }
                        break;
                    case ModularEnvelopeStage.Sustain:
                        CurrentLevel = sustain;
                        if (gate <= 0f)
                            BeginRelease(release, sampleRate);
                        break;
                    case ModularEnvelopeStage.Release:
                        CurrentLevel -= releaseStep;
                        if (CurrentLevel <= 0f)
                        {
                            CurrentLevel = 0f;
                            Stage = ModularEnvelopeStage.Idle;
                            triggerOnly = false;
                        }
                        break;
                    default:
                        CurrentLevel = 0f;
                        break;
                }

                CurrentLevel = Mathf.Clamp01(CurrentLevel);
                LastBlockPeak = Mathf.Max(LastBlockPeak, CurrentLevel);
                output[frame] = CurrentLevel;
                previousGate = gate;
                previousTrigger = trigger;
            }
        }

        private void BeginAttack(float attackSeconds, int sampleRate)
        {
            attackStep = Mathf.Max(
                (1f - CurrentLevel) / (attackSeconds * sampleRate),
                0.0000001f);
            Stage = ModularEnvelopeStage.Attack;
        }

        private void BeginRelease(float releaseSeconds, int sampleRate)
        {
            releaseStep = Mathf.Max(
                CurrentLevel / (releaseSeconds * sampleRate),
                0.0000001f);
            Stage = ModularEnvelopeStage.Release;
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
            bool hasControlInput,
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

    public sealed class ModularVcaNode : ModularAudioNode
    {
        private const float LevelSmoothingSeconds = 0.005f;
        private float smoothedLevel;
        private bool hasSmoothedLevel;

        public float ManualLevel { get; set; } = 0.5f;
        public float Gain { get; set; } = 1f;
        public bool IsControlDriven { get; private set; }
        public float CurrentLevel => smoothedLevel;

        internal override void Process(
            float[] audioInput,
            float controlInput,
            bool hasControlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            IsControlDriven = hasControlInput;
            var targetLevel = hasControlInput
                ? FiniteClamp(controlInput, 0f, 1f, 0f)
                : FiniteClamp(ManualLevel, 0f, 1f, 0f);
            var gain = FiniteClamp(Gain, 0f, 4f, 1f);
            if (!hasSmoothedLevel)
            {
                smoothedLevel = targetLevel;
                hasSmoothedLevel = true;
            }
            var smoothing = 1f - Mathf.Exp(
                -1f / (LevelSmoothingSeconds * sampleRate));
            for (var frame = 0; frame < frameCount; frame++)
            {
                smoothedLevel += (targetLevel - smoothedLevel) * smoothing;
                output[frame] = Mathf.Clamp(
                    audioInput[frame] * smoothedLevel * gain,
                    -1f,
                    1f);
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

    public sealed class ModularFilterNode : ModularAudioNode
    {
        private const float MinimumCutoff = 20f;
        private const float MaximumCutoff = 18000f;
        private const float CoefficientSmoothingSeconds = 0.005f;

        private float integratorOne;
        private float integratorTwo;
        private float smoothedCoefficient;
        private bool hasSmoothedCoefficient;

        public float Cutoff { get; set; } = 1200f;
        public float Resonance { get; set; } = 0.2f;
        public float CurrentCutoff { get; private set; } = 1200f;

        internal override void Process(
            float[] audioInput,
            float controlInput,
            bool hasControlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var nyquistLimit = Mathf.Min(MaximumCutoff, sampleRate * 0.45f);
            var cutoff = FiniteClamp(
                Cutoff,
                MinimumCutoff,
                nyquistLimit,
                1200f);
            if (hasControlInput)
            {
                cutoff *= Mathf.Pow(
                    2f,
                    FiniteClamp(controlInput, -1f, 1f, 0f) * 4f);
                cutoff = Mathf.Clamp(cutoff, MinimumCutoff, nyquistLimit);
            }
            CurrentCutoff = cutoff;

            var resonance = FiniteClamp(Resonance, 0f, 1f, 0.2f);
            var quality = Mathf.Lerp(0.5f, 12f, resonance * resonance);
            var damping = 1f / quality;
            var targetCoefficient = Mathf.Tan(
                Mathf.PI * cutoff / sampleRate);
            if (!hasSmoothedCoefficient)
            {
                smoothedCoefficient = targetCoefficient;
                hasSmoothedCoefficient = true;
            }
            var smoothing = 1f - Mathf.Exp(
                -1f / (CoefficientSmoothingSeconds * sampleRate));

            for (var frame = 0; frame < frameCount; frame++)
            {
                smoothedCoefficient +=
                    (targetCoefficient - smoothedCoefficient) * smoothing;
                var coefficient = Mathf.Clamp(
                    smoothedCoefficient,
                    0.0001f,
                    8f);
                var denominator = 1f +
                                  coefficient *
                                  (coefficient + damping);
                var a1 = 1f / denominator;
                var a2 = coefficient * a1;
                var a3 = coefficient * a2;
                var input = FiniteClamp(
                    audioInput[frame],
                    -1f,
                    1f,
                    0f);
                var v3 = input - integratorTwo;
                var v1 = a1 * integratorOne + a2 * v3;
                var low = integratorTwo +
                          a2 * integratorOne +
                          a3 * v3;
                integratorOne = Mathf.Clamp(
                    2f * v1 - integratorOne,
                    -4f,
                    4f);
                integratorTwo = Mathf.Clamp(
                    2f * low - integratorTwo,
                    -4f,
                    4f);
                if (!IsFinite(integratorOne) || !IsFinite(integratorTwo))
                {
                    integratorOne = 0f;
                    integratorTwo = 0f;
                    low = 0f;
                }
                output[frame] = Mathf.Clamp(low, -1f, 1f);
            }
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static float FiniteClamp(
            float value,
            float minimum,
            float maximum,
            float fallback)
        {
            return IsFinite(value)
                ? Mathf.Clamp(value, minimum, maximum)
                : fallback;
        }
    }

    public sealed class ModularMixerNode : ModularAudioNode
    {
        public float Gain { get; set; } = 1f;
        public float Limit { get; set; } = 0.85f;

        internal override void Process(
            float[] audioInput,
            float controlInput,
            bool hasControlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            var gain = FiniteClamp(Gain, 0f, 4f, 1f);
            var limit = FiniteClamp(Limit, 0.05f, 1f, 0.85f);
            for (var frame = 0; frame < frameCount; frame++)
            {
                output[frame] = Mathf.Clamp(
                    audioInput[frame] * gain,
                    -limit,
                    limit);
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
            var value = FiniteClamp01(Value, 0f);
            return portId switch
            {
                "value.out" => value,
                "trigger.out" => value >= ModularAudioPatchPolicy
                    .ObservableTriggerThreshold ? 1f : 0f,
                _ => base.ReadOutput(portId, output, frame)
            };
        }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            bool hasControlInput,
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

    public sealed class ModularControlSourceNode : ModularAudioNode
    {
        public float Value { get; set; }

        internal override float ReadOutput(
            string portId,
            float[] output,
            int frame)
        {
            var value = FiniteClamp01(Value);
            return portId switch
            {
                "control.out" => value,
                "gate.out" or "trigger.out" =>
                    value >= ModularAudioPatchPolicy
                        .ObservableTriggerThreshold ? 1f : 0f,
                _ => base.ReadOutput(portId, output, frame)
            };
        }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            bool hasControlInput,
            float[] clockInput,
            bool hasClockInput,
            float[] output,
            int frameCount,
            int sampleRate)
        {
            for (var frame = 0; frame < frameCount; frame++)
                output[frame] = 0f;
        }

        private static float FiniteClamp01(float value)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? 0f
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
            var value = HasValidInput && ValidInputCount > 0
                ? FiniteClamp(Value, 0f, 1f, 0f)
                : 0f;
            return portId switch
            {
                "value.out" => value,
                "slope.out" => FiniteClamp(Slope, -1f, 1f, 0f),
                "spread.out" => FiniteClamp(Spread, 0f, 1f, 0f),
                "trigger.out" => value >= ModularAudioPatchPolicy
                    .ObservableTriggerThreshold ? 1f : 0f,
                _ => base.ReadOutput(portId, output, frame)
            };
        }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            bool hasControlInput,
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
            var energy = HasValidInput && ConnectedCount > 0
                ? FiniteClamp(Energy, 0f, 1f, 0f)
                : 0f;
            return portId switch
            {
                "energy.out" => energy,
                "balance.out" => FiniteClamp(Balance, 0f, 2f, 1f),
                "phase.out" => FiniteClamp(Phase, -Mathf.PI * 2f,
                    Mathf.PI * 2f, 0f),
                "detail.out" => FiniteClamp(Detail, 0f, 1f, 0f),
                "trigger.out" => energy >= ModularAudioPatchPolicy
                    .ObservableTriggerThreshold ? 1f : 0f,
                _ => base.ReadOutput(portId, output, frame)
            };
        }

        internal override void Process(
            float[] audioInput,
            float controlInput,
            bool hasControlInput,
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
