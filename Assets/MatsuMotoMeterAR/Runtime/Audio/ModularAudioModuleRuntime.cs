using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Signals;
using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    [DisallowMultipleComponent]
    public sealed class ModularAudioModuleRuntime : MonoBehaviour
    {
        private MockInstrumentMotion motion;
        private float previousTrendValue;
        private bool hasTrendValue;

        public ModularAudioModuleKind ModuleKind { get; private set; }
        public ModularAudioNode Node { get; private set; }
        public MockInstrumentMotion Motion => motion;

        public void Configure(
            MockInstrumentKind instrumentKind,
            MockInstrumentMotion instrumentMotion)
        {
            if (motion != null)
                motion.ValueChanged -= OnValueChanged;
            motion = instrumentMotion;
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
                ModularAudioModuleKind.MeterSource =>
                    new ModularMeterSourceNode(),
                ModularAudioModuleKind.TrendSource =>
                    new ModularTrendSourceNode(),
                ModularAudioModuleKind.PanelSource =>
                    new ModularPanelSourceNode(),
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
            System.Collections.Generic.IReadOnlyList<float> sequencerSteps)
        {
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
                    sequencer.SetStepValues(sequencerSteps);
                    break;
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
                MockInstrumentKind.RoundMeter or
                MockInstrumentKind.RoundMeterMedium or
                MockInstrumentKind.RoundMeterLarge or
                MockInstrumentKind.WindowMeter =>
                    ModularAudioModuleKind.MeterSource,
                MockInstrumentKind.TrendMonitor =>
                    ModularAudioModuleKind.TrendSource,
                MockInstrumentKind.WindowPanel =>
                    ModularAudioModuleKind.PanelSource,
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
