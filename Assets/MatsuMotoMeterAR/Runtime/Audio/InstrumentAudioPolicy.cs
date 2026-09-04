using MatsuMotoMeterAR.Instruments;

namespace MatsuMotoMeterAR.Audio
{
    public static class InstrumentAudioPolicy
    {
        public const int IndicatorLampStageCount = 4;
        private static readonly float[] LampUpThresholds =
            { 0.18f, 0.48f, 0.78f };
        private static readonly float[] LampDownThresholds =
            { 0.12f, 0.42f, 0.72f };

        public static bool IsOneShotSuppressed(
            InstrumentValueChangeOrigin origin)
        {
            return origin == InstrumentValueChangeOrigin.Restore ||
                   origin == InstrumentValueChangeOrigin.ThemeChange;
        }

        public static InstrumentAudioCue ResolveOneShot(
            MockInstrumentKind instrumentKind,
            InstrumentValueChange change,
            ref int lampStage)
        {
            if (instrumentKind == MockInstrumentKind.IndicatorLamp)
                return ResolveLamp(change.CurrentValue, ref lampStage);

            if (change.MotionKind == MockInstrumentMotion.MotionKind.Toggle)
            {
                return change.CurrentValue >= 0.5f
                    ? InstrumentAudioCue.SwitchOn
                    : InstrumentAudioCue.SwitchOff;
            }

            if (change.MotionKind == MockInstrumentMotion.MotionKind.Lever ||
                change.MotionKind == MockInstrumentMotion.MotionKind.Throttle ||
                change.MotionKind == MockInstrumentMotion.MotionKind.PowerSlider)
            {
                if (change.PreviousDetent == change.CurrentDetent)
                    return InstrumentAudioCue.None;
                return change.CurrentDetent > change.PreviousDetent
                    ? InstrumentAudioCue.DetentUp
                    : InstrumentAudioCue.DetentDown;
            }

            if (change.MotionKind == MockInstrumentMotion.MotionKind.Rotate)
                return InstrumentAudioCue.RotaryStep;

            if (change.MotionKind == MockInstrumentMotion.MotionKind.Press)
            {
                return change.CurrentValue >= 0.5f
                    ? InstrumentAudioCue.ButtonDown
                    : InstrumentAudioCue.ButtonUp;
            }

            if (change.MotionKind == MockInstrumentMotion.MotionKind.Status)
            {
                return change.CurrentDetent switch
                {
                    1 => InstrumentAudioCue.StatusSafe,
                    2 => InstrumentAudioCue.StatusWarning,
                    3 => InstrumentAudioCue.StatusDanger,
                    _ => InstrumentAudioCue.StatusOff
                };
            }

            return InstrumentAudioCue.None;
        }

        public static int InitialLampStage(float value)
        {
            value = ClampFinite01(value);
            if (value < 0.15f)
                return 0;
            if (value < 0.45f)
                return 1;
            if (value < 0.75f)
                return 2;
            return 3;
        }

        private static InstrumentAudioCue ResolveLamp(
            float value,
            ref int lampStage)
        {
            value = ClampFinite01(value);
            var nextStage = lampStage;
            while (nextStage < IndicatorLampStageCount - 1 &&
                   value >= LampUpThresholds[nextStage])
                nextStage++;
            while (nextStage > 0 &&
                   value <= LampDownThresholds[nextStage - 1])
                nextStage--;

            if (nextStage == lampStage)
                return InstrumentAudioCue.None;

            lampStage = nextStage;
            return nextStage switch
            {
                1 => InstrumentAudioCue.LampLow,
                2 => InstrumentAudioCue.LampMedium,
                3 => InstrumentAudioCue.LampHigh,
                _ => InstrumentAudioCue.LampOff
            };
        }

        private static float ClampFinite01(float value)
        {
            if (float.IsNaN(value) || float.IsInfinity(value))
                return 0f;
            return UnityEngine.Mathf.Clamp01(value);
        }
    }
}
