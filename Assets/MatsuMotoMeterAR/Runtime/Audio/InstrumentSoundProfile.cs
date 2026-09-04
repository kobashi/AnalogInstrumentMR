using MatsuMotoMeterAR.Instruments;

namespace MatsuMotoMeterAR.Audio
{
    public readonly struct InstrumentSoundProfile
    {
        public InstrumentSoundProfile(
            float pitch,
            float duration,
            float decay,
            float overtoneRatio,
            float bodyLevel,
            float overtoneLevel,
            float transientLevel)
        {
            Pitch = pitch;
            Duration = duration;
            Decay = decay;
            OvertoneRatio = overtoneRatio;
            BodyLevel = bodyLevel;
            OvertoneLevel = overtoneLevel;
            TransientLevel = transientLevel;
        }

        public float Pitch { get; }
        public float Duration { get; }
        public float Decay { get; }
        public float OvertoneRatio { get; }
        public float BodyLevel { get; }
        public float OvertoneLevel { get; }
        public float TransientLevel { get; }
    }

    public static class InstrumentSoundProfileCatalog
    {
        public static InstrumentSoundProfile Get(MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.ToggleSwitch =>
                    new InstrumentSoundProfile(
                        1.08f, 0.86f, 1.10f, 1.82f, 0.32f, 0.16f, 0.25f),
                MockInstrumentKind.Lever =>
                    new InstrumentSoundProfile(
                        0.72f, 1.16f, 0.82f, 2.05f, 0.40f, 0.12f, 0.16f),
                MockInstrumentKind.ThrottleLever =>
                    new InstrumentSoundProfile(
                        0.54f, 1.34f, 0.70f, 1.47f, 0.43f, 0.17f, 0.22f),
                MockInstrumentKind.PowerSlider =>
                    new InstrumentSoundProfile(
                        1.28f, 0.72f, 1.28f, 3.13f, 0.25f, 0.10f, 0.31f),
                MockInstrumentKind.RotaryKnob =>
                    new InstrumentSoundProfile(
                        1.43f, 0.64f, 1.42f, 2.71f, 0.24f, 0.13f, 0.29f),
                MockInstrumentKind.PushButton =>
                    new InstrumentSoundProfile(
                        0.88f, 0.92f, 1.02f, 1.63f, 0.36f, 0.11f, 0.21f),
                MockInstrumentKind.IndicatorLamp =>
                    new InstrumentSoundProfile(
                        0.96f, 1.08f, 0.86f, 2.22f, 0.31f, 0.22f, 0.14f),
                MockInstrumentKind.StatusIndicator =>
                    new InstrumentSoundProfile(
                        1.04f, 1.04f, 0.91f, 2.49f, 0.29f, 0.25f, 0.13f),
                _ =>
                    new InstrumentSoundProfile(
                        1f, 1f, 1f, 2.37f, 0.34f, 0.13f, 0.20f)
            };
        }
    }
}
