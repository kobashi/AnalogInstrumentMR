using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    public enum AdjustableParameterScale
    {
        Linear = 0,
        Logarithmic = 1
    }

    public enum AdjustableParameterField
    {
        Value = 0,
        Minimum = 1,
        Maximum = 2,
        StepCount = 3
    }

    [Serializable]
    public sealed class AdjustableParameterSetting
    {
        public string parameterId;
        public float value;
        public float minimum;
        public float maximum = 1f;
        public int stepCount;
        public int scaleKind = (int)AdjustableParameterScale.Linear;

        public AdjustableParameterSetting Clone()
        {
            return new AdjustableParameterSetting
            {
                parameterId = parameterId,
                value = value,
                minimum = minimum,
                maximum = maximum,
                stepCount = stepCount,
                scaleKind = scaleKind
            };
        }
    }

    public readonly struct AdjustableParameterDescriptor
    {
        public AdjustableParameterDescriptor(
            string id,
            string label,
            string unit,
            float hardMinimum,
            float hardMaximum,
            float defaultMinimum,
            float defaultMaximum,
            float defaultValue,
            int defaultStepCount,
            AdjustableParameterScale scale,
            float editIncrement,
            bool stepCountEditable = true)
        {
            Id = id;
            Label = label;
            Unit = unit;
            HardMinimum = hardMinimum;
            HardMaximum = hardMaximum;
            DefaultMinimum = defaultMinimum;
            DefaultMaximum = defaultMaximum;
            DefaultValue = defaultValue;
            DefaultStepCount = defaultStepCount;
            Scale = scale;
            EditIncrement = editIncrement;
            StepCountEditable = stepCountEditable;
        }

        public string Id { get; }
        public string Label { get; }
        public string Unit { get; }
        public float HardMinimum { get; }
        public float HardMaximum { get; }
        public float DefaultMinimum { get; }
        public float DefaultMaximum { get; }
        public float DefaultValue { get; }
        public int DefaultStepCount { get; }
        public AdjustableParameterScale Scale { get; }
        public float EditIncrement { get; }
        public bool StepCountEditable { get; }
    }

    public static class AdjustableParameterPolicy
    {
        public const string ControlValueId = "control.value";
        public const string OscillatorFrequencyId = "osc.frequency";
        public const string OscillatorLevelId = "osc.level";
        public const string NoiseLevelId = "noise.level";
        public const string LfoFrequencyId = "lfo.frequency";
        public const string LfoDepthId = "lfo.depth";
        public const string LfoGateLengthId = "lfo.gate_length";
        public const string SequencerTempoId = "sequencer.tempo";
        public const string SequencerGateLengthId = "sequencer.gate_length";
        public const string SequencerStepValueId = "sequencer.step_value";
        public const string SequencerPlaybackModeId =
            "sequencer.playback_mode";
        public const string DelayTimeId = "delay.time";
        public const string DelayFeedbackId = "delay.feedback";
        public const string DelayMixId = "delay.mix";
        public const string OutputGainId = "output.gain";
        public const string OutputLimitId = "output.limit";
        public const string VcaLevelId = "vca.level";
        public const string VcaGainId = "vca.gain";
        public const string MixerGainId = "mixer.gain";
        public const string MixerLimitId = "mixer.limit";
        public const string FilterCutoffId = "filter.cutoff";
        public const string FilterResonanceId = "filter.resonance";
        public const string EnvelopeGateId = "envelope.gate";
        public const string EnvelopeAttackId = "envelope.attack";
        public const string EnvelopeDecayId = "envelope.decay";
        public const string EnvelopeSustainId = "envelope.sustain";
        public const string EnvelopeReleaseId = "envelope.release";
        public const int MaximumStepCount = 128;

        private static readonly AdjustableParameterDescriptor[] Empty = { };
        private static readonly AdjustableParameterDescriptor[] Lever =
        {
            Control("VALUE", 5)
        };
        private static readonly AdjustableParameterDescriptor[] Rotary =
        {
            Control("VALUE", 0)
        };
        private static readonly AdjustableParameterDescriptor[] Binary =
        {
            Control("VALUE", 2, false)
        };
        private static readonly AdjustableParameterDescriptor[] Throttle =
        {
            Control("VALUE", 6)
        };
        private static readonly AdjustableParameterDescriptor[] Slider =
        {
            Control("VALUE", 11)
        };
        private static readonly AdjustableParameterDescriptor[] Oscillator =
        {
            new(OscillatorFrequencyId, "FREQUENCY", "HZ", 20f, 12000f,
                55f, 1760f, 311.12698f, 0,
                AdjustableParameterScale.Logarithmic, 5f),
            Unit(OscillatorLevelId, "LEVEL", 0.22f, 101)
        };
        private static readonly AdjustableParameterDescriptor[] Noise =
        {
            new(NoiseLevelId, "LEVEL", string.Empty, 0f, 1f,
                0.02f, 0.35f, 0.1355f, 101,
                AdjustableParameterScale.Linear, 0.005f)
        };
        private static readonly AdjustableParameterDescriptor[] Lfo =
        {
            new(LfoFrequencyId, "RATE", "HZ", 0.01f, 40f,
                0.05f, 20f, 1f, 0,
                AdjustableParameterScale.Logarithmic, 0.01f),
            Unit(LfoDepthId, "DEPTH", 0.8f, 101),
            new(LfoGateLengthId, "GATE LENGTH", string.Empty, 0.01f, 0.99f,
                0.05f, 0.95f, 0.5f, 91,
                AdjustableParameterScale.Linear, 0.01f)
        };
        private static readonly AdjustableParameterDescriptor[] Sequencer =
        {
            new(SequencerTempoId, "TEMPO", "BPM", 20f, 300f,
                40f, 240f, 140f, 101,
                AdjustableParameterScale.Linear, 1f),
            new(SequencerGateLengthId, "GATE LENGTH", string.Empty, 0.01f, 0.99f,
                0.05f, 0.95f, 0.5f, 91,
                AdjustableParameterScale.Linear, 0.01f),
            new(SequencerStepValueId, "STEP VALUE", string.Empty, -1f, 1f,
                -1f, 1f, 0f, 41,
                AdjustableParameterScale.Linear, 0.05f),
            new(SequencerPlaybackModeId, "PLAY MODE", string.Empty, 0f, 1f,
                0f, 1f, 0f, 2,
                AdjustableParameterScale.Linear, 1f, false)
        };
        private static readonly AdjustableParameterDescriptor[] Delay =
        {
            new(DelayTimeId, "TIME", "S", 0.02f, 0.75f,
                0.02f, 0.75f, 0.385f, 0,
                AdjustableParameterScale.Linear, 0.01f),
            Unit(DelayFeedbackId, "FEEDBACK", 0.42f, 101),
            Unit(DelayMixId, "MIX", 1f, 101)
        };
        private static readonly AdjustableParameterDescriptor[] Output =
        {
            new(OutputGainId, "GAIN", "X", 0f, 4f,
                0f, 2f, 1f, 81,
                AdjustableParameterScale.Linear, 0.05f),
            new(OutputLimitId, "LIMIT", string.Empty, 0.05f, 1f,
                0.05f, 1f, 0.85f, 96,
                AdjustableParameterScale.Linear, 0.01f)
        };
        private static readonly AdjustableParameterDescriptor[] Vca =
        {
            Unit(VcaLevelId, "MANUAL LEVEL", 0.5f, 101),
            new(VcaGainId, "GAIN", "X", 0f, 4f,
                0f, 2f, 1f, 81,
                AdjustableParameterScale.Linear, 0.05f)
        };
        private static readonly AdjustableParameterDescriptor[] Mixer =
        {
            new(MixerGainId, "GAIN", "X", 0f, 4f,
                0f, 2f, 1f, 81,
                AdjustableParameterScale.Linear, 0.05f),
            new(MixerLimitId, "LIMIT", string.Empty, 0.05f, 1f,
                0.05f, 1f, 0.85f, 96,
                AdjustableParameterScale.Linear, 0.01f)
        };
        private static readonly AdjustableParameterDescriptor[] Filter =
        {
            new(FilterCutoffId, "CUTOFF", "HZ", 20f, 18000f,
                80f, 12000f, 1200f, 0,
                AdjustableParameterScale.Logarithmic, 10f),
            Unit(FilterResonanceId, "RESONANCE", 0.2f, 101)
        };
        private static readonly AdjustableParameterDescriptor[] Envelope =
        {
            new(EnvelopeGateId, "MANUAL GATE", string.Empty, 0f, 1f,
                0f, 1f, 1f, 2,
                AdjustableParameterScale.Linear, 1f, false),
            new(EnvelopeAttackId, "ATTACK", "S", 0.001f, 10f,
                0.005f, 5f, 0.05f, 0,
                AdjustableParameterScale.Logarithmic, 0.01f),
            new(EnvelopeDecayId, "DECAY", "S", 0.001f, 10f,
                0.005f, 5f, 0.2f, 0,
                AdjustableParameterScale.Logarithmic, 0.01f),
            Unit(EnvelopeSustainId, "SUSTAIN", 0.7f, 101),
            new(EnvelopeReleaseId, "RELEASE", "S", 0.001f, 10f,
                0.005f, 5f, 0.35f, 0,
                AdjustableParameterScale.Logarithmic, 0.01f)
        };

        public static IReadOnlyList<AdjustableParameterDescriptor> Descriptors(
            MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.Lever => Lever,
                MockInstrumentKind.ToggleSwitch => Binary,
                MockInstrumentKind.RotaryKnob => Rotary,
                MockInstrumentKind.PushButton => Binary,
                MockInstrumentKind.ThrottleLever => Throttle,
                MockInstrumentKind.PowerSlider => Slider,
                MockInstrumentKind.AudioOscillator => Oscillator,
                MockInstrumentKind.AudioNoise => Noise,
                MockInstrumentKind.AudioLfo => Lfo,
                MockInstrumentKind.AudioSequencer => Sequencer,
                MockInstrumentKind.AudioDelay => Delay,
                MockInstrumentKind.AudioVca => Vca,
                MockInstrumentKind.AudioMixer => Mixer,
                MockInstrumentKind.AudioFilter => Filter,
                MockInstrumentKind.AudioEnvelope => Envelope,
                MockInstrumentKind.AudioOutput => Output,
                _ => Empty
            };
        }

        public static bool SupportsEditing(MockInstrumentKind kind)
        {
            return Descriptors(kind).Count > 0;
        }

        public static List<AdjustableParameterSetting> NormalizeSettings(
            MockInstrumentKind kind,
            IReadOnlyList<AdjustableParameterSetting> source,
            float normalizedValue)
        {
            var descriptors = Descriptors(kind);
            var result = new List<AdjustableParameterSetting>(descriptors.Count);
            for (var index = 0; index < descriptors.Count; index++)
            {
                var descriptor = descriptors[index];
                var candidate = Find(source, descriptor.Id);
                var setting = candidate?.Clone() ?? CreateDefault(descriptor);
                if (candidate == null && index == 0)
                {
                    setting.value = DefaultPrimaryValue(
                        kind,
                        normalizedValue,
                        setting);
                }
                Normalize(setting, descriptor);
                result.Add(setting);
            }
            return result;
        }

        public static AdjustableParameterSetting Find(
            IReadOnlyList<AdjustableParameterSetting> settings,
            string parameterId)
        {
            if (settings == null || string.IsNullOrEmpty(parameterId))
                return null;
            for (var index = 0; index < settings.Count; index++)
            {
                var setting = settings[index];
                if (setting != null && setting.parameterId == parameterId)
                    return setting;
            }
            return null;
        }

        public static float MapNormalized(
            float normalizedValue,
            AdjustableParameterSetting setting)
        {
            if (setting == null)
                return Mathf.Clamp01(normalizedValue);
            var t = Mathf.Clamp01(normalizedValue);
            var scale = NormalizeScale(setting);
            var value = scale == AdjustableParameterScale.Logarithmic &&
                        setting.minimum > 0f
                ? setting.minimum * Mathf.Pow(
                    setting.maximum / setting.minimum,
                    t)
                : Mathf.Lerp(setting.minimum, setting.maximum, t);
            return Quantize(value, setting);
        }

        public static float InverseMap(
            float value,
            AdjustableParameterSetting setting)
        {
            if (setting == null)
                return Mathf.Clamp01(value);
            value = Mathf.Clamp(value, setting.minimum, setting.maximum);
            if (NormalizeScale(setting) ==
                    AdjustableParameterScale.Logarithmic &&
                setting.minimum > 0f && value > 0f)
            {
                return Mathf.Clamp01(
                    Mathf.Log(value / setting.minimum) /
                    Mathf.Log(setting.maximum / setting.minimum));
            }
            return Mathf.InverseLerp(setting.minimum, setting.maximum, value);
        }

        public static void Adjust(
            AdjustableParameterSetting setting,
            AdjustableParameterDescriptor descriptor,
            AdjustableParameterField field,
            int direction)
        {
            if (setting == null || direction == 0)
                return;
            direction = direction < 0 ? -1 : 1;
            switch (field)
            {
                case AdjustableParameterField.Minimum:
                    setting.minimum += descriptor.EditIncrement * direction;
                    break;
                case AdjustableParameterField.Maximum:
                    setting.maximum += descriptor.EditIncrement * direction;
                    break;
                case AdjustableParameterField.StepCount:
                    if (!descriptor.StepCountEditable)
                        break;
                    if (direction < 0)
                        setting.stepCount = setting.stepCount <= 2
                            ? 0
                            : setting.stepCount - 1;
                    else
                        setting.stepCount = setting.stepCount == 0
                            ? 2
                            : setting.stepCount + 1;
                    break;
                default:
                    if (setting.stepCount >= 2)
                    {
                        var step = (setting.maximum - setting.minimum) /
                                   (setting.stepCount - 1);
                        setting.value += step * direction;
                    }
                    else if (NormalizeScale(setting) ==
                             AdjustableParameterScale.Logarithmic &&
                             setting.minimum > 0f)
                    {
                        var factor = Mathf.Pow(
                            setting.maximum / setting.minimum,
                            1f / 64f);
                        setting.value *= direction < 0 ? 1f / factor : factor;
                    }
                    else
                    {
                        setting.value += descriptor.EditIncrement * direction;
                    }
                    break;
            }
            Normalize(setting, descriptor);
        }

        public static AdjustableParameterField CycleField(
            AdjustableParameterField field,
            int direction)
        {
            const int count = 4;
            return (AdjustableParameterField)
                (((int)field + (direction < 0 ? count - 1 : 1)) % count);
        }

        public static float Quantize(
            float value,
            AdjustableParameterSetting setting)
        {
            value = Mathf.Clamp(value, setting.minimum, setting.maximum);
            if (setting.stepCount < 2)
                return value;
            var t = InverseMapWithoutQuantization(value, setting);
            var index = Mathf.Round(t * (setting.stepCount - 1));
            var quantizedT = index / (float)(setting.stepCount - 1);
            return NormalizeScale(setting) ==
                       AdjustableParameterScale.Logarithmic &&
                   setting.minimum > 0f
                ? setting.minimum * Mathf.Pow(
                    setting.maximum / setting.minimum,
                    quantizedT)
                : Mathf.Lerp(setting.minimum, setting.maximum, quantizedT);
        }

        private static AdjustableParameterSetting CreateDefault(
            AdjustableParameterDescriptor descriptor)
        {
            var setting = new AdjustableParameterSetting
            {
                parameterId = descriptor.Id,
                minimum = descriptor.DefaultMinimum,
                maximum = descriptor.DefaultMaximum,
                value = descriptor.DefaultValue,
                stepCount = descriptor.DefaultStepCount,
                scaleKind = (int)descriptor.Scale
            };
            return setting;
        }

        private static float DefaultPrimaryValue(
            MockInstrumentKind kind,
            float normalizedValue,
            AdjustableParameterSetting setting)
        {
            var value = Mathf.Clamp01(normalizedValue);
            if (kind == MockInstrumentKind.AudioSequencer)
            {
                value = value >= 0.5f
                    ? (value - 0.5f) * 2f
                    : value * 2f;
            }
            if (kind == MockInstrumentKind.AudioEnvelope)
            {
                return value >= 0.5f
                    ? setting.maximum
                    : setting.minimum;
            }
            return MapNormalized(value, setting);
        }

        private static void Normalize(
            AdjustableParameterSetting setting,
            AdjustableParameterDescriptor descriptor)
        {
            setting.parameterId = descriptor.Id;
            setting.scaleKind = (int)descriptor.Scale;
            setting.minimum = FiniteOr(
                setting.minimum,
                descriptor.DefaultMinimum);
            setting.maximum = FiniteOr(
                setting.maximum,
                descriptor.DefaultMaximum);
            setting.minimum = Mathf.Clamp(
                setting.minimum,
                descriptor.HardMinimum,
                descriptor.HardMaximum);
            setting.maximum = Mathf.Clamp(
                setting.maximum,
                descriptor.HardMinimum,
                descriptor.HardMaximum);
            if (setting.minimum > setting.maximum)
                (setting.minimum, setting.maximum) =
                    (setting.maximum, setting.minimum);
            if (Mathf.Approximately(setting.minimum, setting.maximum))
            {
                setting.minimum = descriptor.DefaultMinimum;
                setting.maximum = descriptor.DefaultMaximum;
            }
            setting.stepCount = setting.stepCount == 0
                ? 0
                : Mathf.Clamp(setting.stepCount, 2, MaximumStepCount);
            if (!descriptor.StepCountEditable)
                setting.stepCount = descriptor.DefaultStepCount;
            setting.value = Quantize(
                FiniteOr(setting.value, descriptor.DefaultValue),
                setting);
        }

        private static float InverseMapWithoutQuantization(
            float value,
            AdjustableParameterSetting setting)
        {
            if (NormalizeScale(setting) ==
                    AdjustableParameterScale.Logarithmic &&
                setting.minimum > 0f && value > 0f)
            {
                return Mathf.Clamp01(
                    Mathf.Log(value / setting.minimum) /
                    Mathf.Log(setting.maximum / setting.minimum));
            }
            return Mathf.InverseLerp(setting.minimum, setting.maximum, value);
        }

        private static AdjustableParameterScale NormalizeScale(
            AdjustableParameterSetting setting)
        {
            return setting.scaleKind ==
                   (int)AdjustableParameterScale.Logarithmic
                ? AdjustableParameterScale.Logarithmic
                : AdjustableParameterScale.Linear;
        }

        private static float FiniteOr(float value, float fallback)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? fallback
                : value;
        }

        private static AdjustableParameterDescriptor Control(
            string label,
            int steps,
            bool stepCountEditable = true)
        {
            return new AdjustableParameterDescriptor(
                ControlValueId, label, string.Empty,
                0f, 1f, 0f, 1f, 0.5f, steps,
                AdjustableParameterScale.Linear, 0.01f,
                stepCountEditable);
        }

        private static AdjustableParameterDescriptor Unit(
            string id,
            string label,
            float value,
            int steps)
        {
            return new AdjustableParameterDescriptor(
                id, label, string.Empty,
                0f, 1f, 0f, 1f, value, steps,
                AdjustableParameterScale.Linear, 0.01f);
        }
    }
}
