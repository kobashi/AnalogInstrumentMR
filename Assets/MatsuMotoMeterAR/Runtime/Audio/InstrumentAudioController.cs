using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Signals;
using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    [DisallowMultipleComponent]
    public sealed class InstrumentAudioController : MonoBehaviour
    {
        public const float MinimumDistance = 0.25f;
        public const float MaximumDistance = 4f;
        public const float OneShotVolume = 0.34f;

        private MockInstrumentKind instrumentKind;
        private MockInstrumentTheme theme;
        private MockInstrumentMotion motion;
        private AudioSource oneShotSource;
        private AudioSource continuousSource;
        private AudioClip continuousClip;
        private InstrumentContinuousAudioSynth continuousSynth;
        private int continuousSampleRate = 48000;
        private int lampStage;
        private bool hasTrendValue;
        private float previousTrendValue;

        public MockInstrumentKind InstrumentKind => instrumentKind;
        public MockInstrumentTheme Theme => theme;
        public MockInstrumentMotion Motion => motion;
        public AudioSource OneShotSource => oneShotSource;
        public AudioSource ContinuousSource => continuousSource;
        public InstrumentContinuousAudioSynth ContinuousSynth => continuousSynth;
        public bool ContinuousSelected { get; private set; }
        public InstrumentAudioCue LastCue { get; private set; }
        public int LampStage => lampStage;
        public int CueCount { get; private set; }

        public void Configure(
            MockInstrumentKind kind,
            MockInstrumentTheme instrumentTheme,
            MockInstrumentMotion instrumentMotion)
        {
            if (motion != null)
                motion.ValueChanged -= OnValueChanged;

            instrumentKind = kind;
            theme = MockInstrumentThemeCatalog.Normalize(instrumentTheme);
            motion = instrumentMotion;
            oneShotSource = GetComponent<AudioSource>();
            if (oneShotSource == null)
                oneShotSource = gameObject.AddComponent<AudioSource>();
            ConfigureSource(oneShotSource);
            ConfigureContinuous(kind);
            lampStage = motion != null
                ? InstrumentAudioPolicy.InitialLampStage(
                    motion.NormalizedValue)
                : 0;
            LastCue = InstrumentAudioCue.None;
            CueCount = 0;

            if (motion != null)
                motion.ValueChanged += OnValueChanged;
        }

        public void SetTheme(MockInstrumentTheme instrumentTheme)
        {
            theme = MockInstrumentThemeCatalog.Normalize(instrumentTheme);
        }

        public void SetTrendState(
            float composedValue,
            float spread,
            int validInputCount,
            bool hasValidInput)
        {
            if (continuousSynth == null ||
                continuousSynth.Mode !=
                InstrumentContinuousAudioMode.TrendMonitor)
            {
                return;
            }

            var slope = hasTrendValue
                ? Mathf.Abs(composedValue - previousTrendValue) /
                  SignalMonitorView.RefreshIntervalSeconds
                : 0f;
            if (hasValidInput)
            {
                previousTrendValue = composedValue;
                hasTrendValue = true;
            }
            else
            {
                hasTrendValue = false;
            }
            continuousSynth.SetTrend(
                composedValue,
                slope,
                spread,
                validInputCount,
                hasValidInput);
        }

        public void SetWindowPanelState(
            WindowPanelGraphicInputs inputs,
            WindowPanelGraphicPreset preset)
        {
            if (continuousSynth == null ||
                continuousSynth.Mode !=
                InstrumentContinuousAudioMode.WindowPanel)
            {
                return;
            }

            continuousSynth.SetWindowPanel(
                inputs.Energy,
                inputs.Balance,
                inputs.Phase,
                inputs.Detail,
                inputs.ConnectedCount,
                (int)preset,
                !inputs.HasInvalidInput && inputs.ConnectedCount > 0);
        }

        private static void ConfigureSource(AudioSource source)
        {
            source.playOnAwake = false;
            source.loop = false;
            source.spatialBlend = 1f;
            source.dopplerLevel = 0f;
            source.rolloffMode = AudioRolloffMode.Logarithmic;
            source.minDistance = MinimumDistance;
            source.maxDistance = MaximumDistance;
            source.volume = OneShotVolume;
            source.priority = 32;
        }

        private void ConfigureContinuous(MockInstrumentKind kind)
        {
            var mode = InstrumentContinuousAudioSynth.ModeFor(kind);
            continuousSynth = mode == InstrumentContinuousAudioMode.None
                ? null
                : new InstrumentContinuousAudioSynth(mode);
            if (continuousSynth == null)
                return;

            continuousSource = gameObject.AddComponent<AudioSource>();
            ConfigureSource(continuousSource);
            continuousSource.loop = true;
            continuousSource.volume = 0f;
            continuousSource.priority = 160;
            continuousSource.mute = true;
            if (mode == InstrumentContinuousAudioMode.Meter && motion != null)
                continuousSynth.SetMeter(motion.NormalizedValue);
            InstrumentAudioVoiceBudget.Register(this);
        }

        private void Start()
        {
            if (continuousSynth == null || continuousSource == null)
                return;

            continuousSampleRate = Mathf.Max(
                8000,
                AudioSettings.outputSampleRate);
            continuousClip = AudioClip.Create(
                $"Generated_{instrumentKind}_Continuous",
                continuousSampleRate,
                1,
                continuousSampleRate,
                true,
                OnContinuousAudioRead);
            continuousSource.clip = continuousClip;
            continuousSource.Play();
        }

        private void Update()
        {
            if (continuousSource == null)
                return;

            InstrumentAudioVoiceBudget.RefreshIfDue();
            if (ContinuousSelected)
                continuousSource.mute = false;
            continuousSource.volume = Mathf.MoveTowards(
                continuousSource.volume,
                ContinuousSelected ? 1f : 0f,
                Time.unscaledDeltaTime * 6f);
            if (!ContinuousSelected && continuousSource.volume <= 0f)
                continuousSource.mute = true;
        }

        public void SetContinuousSelected(bool selected)
        {
            ContinuousSelected = selected;
        }

        private void OnContinuousAudioRead(float[] data)
        {
            continuousSynth?.Fill(
                data,
                1,
                continuousSampleRate);
        }

        private void OnValueChanged(InstrumentValueChange change)
        {
            var cue = InstrumentAudioPolicy.ResolveOneShot(
                instrumentKind,
                change,
                ref lampStage);
            if (continuousSynth != null &&
                continuousSynth.Mode == InstrumentContinuousAudioMode.Meter)
            {
                continuousSynth.SetMeter(change.CurrentValue);
            }
            if (cue == InstrumentAudioCue.None ||
                InstrumentAudioPolicy.IsOneShotSuppressed(change.Origin))
            {
                return;
            }

            LastCue = cue;
            CueCount++;
            if (!Application.isPlaying || oneShotSource == null)
                return;

            oneShotSource.PlayOneShot(
                InstrumentAudioClipLibrary.Get(
                    theme,
                    instrumentKind,
                    cue,
                    lampStage));
        }

        private void OnDestroy()
        {
            if (motion != null)
                motion.ValueChanged -= OnValueChanged;
            InstrumentAudioVoiceBudget.Unregister(this);
            if (continuousClip != null)
                Destroy(continuousClip);
        }
    }
}
