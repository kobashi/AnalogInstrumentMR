using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Signals;
using System.Collections.Generic;
using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    [DisallowMultipleComponent]
    public sealed class ModularAudioModuleRuntime : MonoBehaviour
    {
        private MockInstrumentMotion motion;
        private MockInstrumentKind instrumentKind;
        private List<AdjustableParameterSetting> parameterSettings;
        private float previousTrendValue;
        private bool hasTrendValue;

        public ModularAudioModuleKind ModuleKind { get; private set; }
        public ModularAudioNode Node { get; private set; }
        public MockInstrumentMotion Motion => motion;
        public float PrimaryParameterValue => Node switch
        {
            ModularOscillatorNode oscillator => oscillator.Frequency,
            ModularNoiseNode noise => noise.Level,
            ModularLfoNode lfo => lfo.Frequency,
            ModularSequencerNode sequencer => sequencer.TempoBpm,
            ModularDelayNode delay => delay.DelaySeconds,
            ModularVcaNode vca => vca.ManualLevel,
            ModularMixerNode mixer => mixer.Gain,
            ModularFilterNode filter => filter.Cutoff,
            ModularEnvelopeNode envelope => envelope.ManualGate ? 1f : 0f,
            ModularAudioOutputNode output => output.Gain,
            _ => motion != null ? motion.NormalizedValue : 0f
        };

        public void Configure(
            MockInstrumentKind instrumentKind,
            MockInstrumentMotion instrumentMotion)
        {
            if (motion != null)
                motion.ValueChanged -= OnValueChanged;
            motion = instrumentMotion;
            this.instrumentKind = instrumentKind;
            ModuleKind = ToModuleKind(instrumentKind);
            Node = ModuleKind switch
            {
                ModularAudioModuleKind.Oscillator =>
                    new ModularOscillatorNode(),
                ModularAudioModuleKind.Noise =>
                    new ModularNoiseNode((uint)(GetInstanceID() | 1)),
                ModularAudioModuleKind.Lfo =>
                    new ModularLfoNode(),
                ModularAudioModuleKind.Sequencer =>
                    new ModularSequencerNode(),
                ModularAudioModuleKind.Delay =>
                    new ModularDelayNode(),
                ModularAudioModuleKind.Vca =>
                    new ModularVcaNode(),
                ModularAudioModuleKind.Mixer =>
                    new ModularMixerNode(),
                ModularAudioModuleKind.Filter =>
                    new ModularFilterNode(),
                ModularAudioModuleKind.Envelope =>
                    new ModularEnvelopeNode(),
                ModularAudioModuleKind.MeterSource =>
                    new ModularMeterSourceNode(),
                ModularAudioModuleKind.TrendSource =>
                    new ModularTrendSourceNode(),
                ModularAudioModuleKind.PanelSource =>
                    new ModularPanelSourceNode(),
                ModularAudioModuleKind.ControlSource =>
                    new ModularControlSourceNode(),
                _ => new ModularAudioOutputNode()
            };
            ApplyValue(motion != null ? motion.NormalizedValue : 0.5f);
            if (motion != null)
                motion.ValueChanged += OnValueChanged;
        }

        private void OnValueChanged(InstrumentValueChange change)
        {
            ApplyValue(change.CurrentValue);
        }

        private void ApplyValue(float value)
        {
            value = Mathf.Clamp01(value);
            if (Node is ModularControlSourceNode controlSource)
                controlSource.Value = value;
            if (Node is ModularSequencerNode configuredSequencer)
                configuredSequencer.StepCount = value >= 0.5f ? 16 : 8;
            if (parameterSettings != null && parameterSettings.Count > 0)
            {
                var parameterPosition = Node is ModularSequencerNode
                    ? value >= 0.5f
                        ? (value - 0.5f) * 2f
                        : value * 2f
                    : value;
                parameterSettings[0].value =
                    AdjustableParameterPolicy.MapNormalized(
                        parameterPosition,
                        parameterSettings[0]);
                ApplyNumericParameters(parameterSettings);
                return;
            }
            switch (Node)
            {
                case ModularOscillatorNode oscillator:
                    oscillator.Frequency = 55f * Mathf.Pow(2f, value * 5f);
                    oscillator.Level = 0.22f;
                    break;
                case ModularNoiseNode noise:
                    noise.Level = Mathf.Lerp(0.02f, 0.35f, value);
                    break;
                case ModularAudioOutputNode output:
                    output.Gain = value * 2f;
                    break;
                case ModularLfoNode lfo:
                    lfo.Frequency = 0.05f * Mathf.Pow(400f, value);
                    lfo.Depth = 0.8f;
                    break;
                case ModularSequencerNode sequencer:
                    var selectsSixteenSteps = value >= 0.5f;
                    var tempoPosition = selectsSixteenSteps
                        ? (value - 0.5f) * 2f
                        : value * 2f;
                    sequencer.StepCount = selectsSixteenSteps ? 16 : 8;
                    sequencer.TempoBpm = Mathf.Lerp(
                        40f,
                        240f,
                        tempoPosition);
                    break;
                case ModularDelayNode delay:
                    delay.DelaySeconds = Mathf.Lerp(
                        ModularDelayNode.MinimumDelaySeconds,
                        ModularDelayNode.MaximumDelaySeconds,
                        value);
                    delay.Feedback = 0.42f;
                    delay.Mix = 1f;
                    break;
                case ModularVcaNode vca:
                    vca.ManualLevel = value;
                    vca.Gain = 1f;
                    break;
                case ModularMixerNode mixer:
                    mixer.Gain = value * 2f;
                    mixer.Limit = 0.85f;
                    break;
                case ModularFilterNode filter:
                    filter.Cutoff = 80f * Mathf.Pow(150f, value);
                    filter.Resonance = 0.2f;
                    break;
                case ModularEnvelopeNode envelope:
                    envelope.ManualGate = value >= 0.5f;
                    break;
                case ModularMeterSourceNode meter:
                    meter.Value = value;
                    break;
                case ModularTrendSourceNode trend:
                    trend.Value = value;
                    break;
                case ModularPanelSourceNode panel:
                    panel.Energy = value;
                    break;
            }
        }

        public void SetTrendState(
            float composedValue,
            float spread,
            int validInputCount,
            bool hasValidInput)
        {
            if (Node is not ModularTrendSourceNode trend)
                return;

            var finiteValue = FiniteClamp(composedValue, 0f, 1f, 0f);
            var slope = hasTrendValue && hasValidInput
                ? (finiteValue - previousTrendValue) /
                  SignalMonitorView.RefreshIntervalSeconds
                : 0f;
            trend.Value = finiteValue;
            trend.Slope = FiniteClamp(slope, -1f, 1f, 0f);
            trend.Spread = FiniteClamp(spread, 0f, 1f, 0f);
            trend.ValidInputCount = Mathf.Clamp(validInputCount, 0, 4);
            trend.HasValidInput = hasValidInput && validInputCount > 0;
            if (trend.HasValidInput)
            {
                previousTrendValue = finiteValue;
                hasTrendValue = true;
            }
            else
            {
                hasTrendValue = false;
            }
        }

        public void SetWindowPanelState(WindowPanelGraphicInputs inputs)
        {
            if (Node is not ModularPanelSourceNode panel)
                return;

            panel.Energy = FiniteClamp(inputs.Energy, 0f, 1f, 0f);
            panel.Balance = FiniteClamp(inputs.Balance, 0f, 2f, 1f);
            panel.Phase = FiniteClamp(
                inputs.Phase,
                -Mathf.PI * 2f,
                Mathf.PI * 2f,
                0f);
            panel.Detail = FiniteClamp(inputs.Detail, 0f, 1f, 0f);
            panel.ConnectedCount = Mathf.Clamp(inputs.ConnectedCount, 0, 4);
            panel.HasValidInput = !inputs.HasInvalidInput &&
                                  inputs.ConnectedCount > 0;
        }

        public void ApplyPersistentParameters(
            int waveform,
            int noiseColor,
            IReadOnlyList<float> sequencerSteps,
            IReadOnlyList<AdjustableParameterSetting> numericParameters = null)
        {
            parameterSettings =
                AdjustableParameterPolicy.NormalizeSettings(
                    instrumentKind,
                    numericParameters,
                    motion != null ? motion.NormalizedValue : 0.5f);
            switch (Node)
            {
                case ModularOscillatorNode oscillator:
                    oscillator.Waveform = (ModularOscillatorWaveform)
                        ModularAudioParameterPolicy.NormalizeWaveform(
                            waveform);
                    break;
                case ModularLfoNode lfo:
                    lfo.Waveform = (ModularOscillatorWaveform)
                        ModularAudioParameterPolicy.NormalizeWaveform(
                            waveform);
                    break;
                case ModularNoiseNode noise:
                    noise.Color = (ModularNoiseColor)
                        ModularAudioParameterPolicy.NormalizeNoiseColor(
                            noiseColor);
                    break;
                case ModularSequencerNode sequencer:
                    sequencer.SetStepValues(
                        sequencerSteps,
                        AdjustableParameterPolicy.Find(
                            parameterSettings,
                            AdjustableParameterPolicy.SequencerStepValueId));
                    break;
            }
            ApplyNumericParameters(parameterSettings);
        }

        private void ApplyNumericParameters(
            IReadOnlyList<AdjustableParameterSetting> settings)
        {
            if (settings == null)
                return;
            switch (Node)
            {
                case ModularOscillatorNode oscillator:
                    oscillator.Frequency = Value(
                        settings,
                        AdjustableParameterPolicy.OscillatorFrequencyId,
                        oscillator.Frequency);
                    oscillator.Level = Value(
                        settings,
                        AdjustableParameterPolicy.OscillatorLevelId,
                        oscillator.Level);
                    break;
                case ModularNoiseNode noise:
                    noise.Level = Value(
                        settings,
                        AdjustableParameterPolicy.NoiseLevelId,
                        noise.Level);
                    break;
                case ModularLfoNode lfo:
                    lfo.Frequency = Value(
                        settings,
                        AdjustableParameterPolicy.LfoFrequencyId,
                        lfo.Frequency);
                    lfo.Depth = Value(
                        settings,
                        AdjustableParameterPolicy.LfoDepthId,
                        lfo.Depth);
                    lfo.GateLength = Value(
                        settings,
                        AdjustableParameterPolicy.LfoGateLengthId,
                        lfo.GateLength);
                    break;
                case ModularSequencerNode sequencer:
                    sequencer.TempoBpm = Value(
                        settings,
                        AdjustableParameterPolicy.SequencerTempoId,
                        sequencer.TempoBpm);
                    sequencer.GateLength = Value(
                        settings,
                        AdjustableParameterPolicy.SequencerGateLengthId,
                        sequencer.GateLength);
                    sequencer.PlaybackMode = Value(
                            settings,
                            AdjustableParameterPolicy
                                .SequencerPlaybackModeId,
                            0f) >= 0.5f
                        ? ModularSequencerPlaybackMode.StepTrigger
                        : ModularSequencerPlaybackMode.Clock;
                    break;
                case ModularDelayNode delay:
                    delay.DelaySeconds = Value(
                        settings,
                        AdjustableParameterPolicy.DelayTimeId,
                        delay.DelaySeconds);
                    delay.Feedback = Value(
                        settings,
                        AdjustableParameterPolicy.DelayFeedbackId,
                        delay.Feedback);
                    delay.Mix = Value(
                        settings,
                        AdjustableParameterPolicy.DelayMixId,
                        delay.Mix);
                    break;
                case ModularAudioOutputNode output:
                    output.Gain = Value(
                        settings,
                        AdjustableParameterPolicy.OutputGainId,
                        output.Gain);
                    output.Limit = Value(
                        settings,
                        AdjustableParameterPolicy.OutputLimitId,
                        output.Limit);
                    break;
                case ModularVcaNode vca:
                    vca.ManualLevel = Value(
                        settings,
                        AdjustableParameterPolicy.VcaLevelId,
                        vca.ManualLevel);
                    vca.Gain = Value(
                        settings,
                        AdjustableParameterPolicy.VcaGainId,
                        vca.Gain);
                    break;
                case ModularMixerNode mixer:
                    mixer.Gain = Value(
                        settings,
                        AdjustableParameterPolicy.MixerGainId,
                        mixer.Gain);
                    mixer.Limit = Value(
                        settings,
                        AdjustableParameterPolicy.MixerLimitId,
                        mixer.Limit);
                    break;
                case ModularFilterNode filter:
                    filter.Cutoff = Value(
                        settings,
                        AdjustableParameterPolicy.FilterCutoffId,
                        filter.Cutoff);
                    filter.Resonance = Value(
                        settings,
                        AdjustableParameterPolicy.FilterResonanceId,
                        filter.Resonance);
                    break;
                case ModularEnvelopeNode envelope:
                    envelope.ManualGate = Value(
                        settings,
                        AdjustableParameterPolicy.EnvelopeGateId,
                        envelope.ManualGate ? 1f : 0f) >= 0.5f;
                    envelope.AttackSeconds = Value(
                        settings,
                        AdjustableParameterPolicy.EnvelopeAttackId,
                        envelope.AttackSeconds);
                    envelope.DecaySeconds = Value(
                        settings,
                        AdjustableParameterPolicy.EnvelopeDecayId,
                        envelope.DecaySeconds);
                    envelope.SustainLevel = Value(
                        settings,
                        AdjustableParameterPolicy.EnvelopeSustainId,
                        envelope.SustainLevel);
                    envelope.ReleaseSeconds = Value(
                        settings,
                        AdjustableParameterPolicy.EnvelopeReleaseId,
                        envelope.ReleaseSeconds);
                    break;
            }
        }

        private static float Value(
            IReadOnlyList<AdjustableParameterSetting> settings,
            string parameterId,
            float fallback)
        {
            return AdjustableParameterPolicy.Find(settings, parameterId)?.value
                   ?? fallback;
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

        private static ModularAudioModuleKind ToModuleKind(
            MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.AudioOscillator =>
                    ModularAudioModuleKind.Oscillator,
                MockInstrumentKind.AudioNoise =>
                    ModularAudioModuleKind.Noise,
                MockInstrumentKind.AudioLfo =>
                    ModularAudioModuleKind.Lfo,
                MockInstrumentKind.AudioSequencer =>
                    ModularAudioModuleKind.Sequencer,
                MockInstrumentKind.AudioDelay =>
                    ModularAudioModuleKind.Delay,
                MockInstrumentKind.AudioVca =>
                    ModularAudioModuleKind.Vca,
                MockInstrumentKind.AudioMixer =>
                    ModularAudioModuleKind.Mixer,
                MockInstrumentKind.AudioFilter =>
                    ModularAudioModuleKind.Filter,
                MockInstrumentKind.AudioEnvelope =>
                    ModularAudioModuleKind.Envelope,
                MockInstrumentKind.RoundMeter or
                MockInstrumentKind.RoundMeterMedium or
                MockInstrumentKind.RoundMeterLarge or
                MockInstrumentKind.WindowMeter =>
                    ModularAudioModuleKind.MeterSource,
                MockInstrumentKind.TrendMonitor =>
                    ModularAudioModuleKind.TrendSource,
                MockInstrumentKind.WindowPanel =>
                    ModularAudioModuleKind.PanelSource,
                MockInstrumentKind.Lever or
                MockInstrumentKind.ToggleSwitch or
                MockInstrumentKind.RotaryKnob or
                MockInstrumentKind.PushButton or
                MockInstrumentKind.ThrottleLever or
                MockInstrumentKind.PowerSlider =>
                    ModularAudioModuleKind.ControlSource,
                _ => ModularAudioModuleKind.AudioOutput
            };
        }

        private void OnDestroy()
        {
            if (motion != null)
                motion.ValueChanged -= OnValueChanged;
        }
    }
}
