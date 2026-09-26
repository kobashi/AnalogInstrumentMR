using MatsuMotoMeterAR.Audio;
using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public sealed class MockInstrumentInteraction : MonoBehaviour
    {
        public MockInstrumentMotion Motion { get; private set; }
        public Collider InteractionCollider { get; private set; }
        public bool IsPressed { get; private set; }
        public float NormalizedValue => Motion != null ? Motion.NormalizedValue : 0f;
        public float OutputValue => Motion != null ? Motion.OutputValue : 0f;
        public int DetentCount => Motion != null ? Motion.DetentCount : 0;
        public int DetentIndex => Motion != null ? Motion.DetentIndex : -1;
        public string StateName => Motion != null ? Motion.StateName : string.Empty;

        public void Configure(
            MockInstrumentMotion motion,
            Collider interactionCollider)
        {
            Motion = motion;
            InteractionCollider = interactionCollider;
        }

        public void SetPressed(bool pressed)
        {
            if (IsPressed == pressed)
                return;

            IsPressed = pressed;
            Motion?.Actuate(
                pressed,
                InstrumentValueChangeOrigin.UserInteraction);
        }

        public void Step(int direction)
        {
            Motion?.Step(direction);
        }

        public void ResetSoundModuleValue(MockInstrumentKind kind)
        {
            if (!MockInstrumentCatalog.IsSoundModule(kind))
                return;
            SetNormalizedValue(
                MockInstrumentCatalog.DefaultSoundModuleValue(kind),
                InstrumentValueChangeOrigin.UserInteraction);
        }

        public void SetNormalizedValue(
            float value,
            InstrumentValueChangeOrigin origin =
                InstrumentValueChangeOrigin.Programmatic)
        {
            Motion?.SetNormalizedValue(value, origin);
        }

        public void SetStickControlledValue(float value)
        {
            Motion?.SetStickControlledValue(
                value,
                InstrumentValueChangeOrigin.UserInteraction);
        }

        public void EndStickControl()
        {
            Motion?.EndStickControl();
        }

        public void ConfigureParameterRange(
            AdjustableParameterSetting setting)
        {
            if (setting == null)
                return;
            Motion?.ConfigureParameterRange(
                setting.minimum,
                setting.maximum,
                setting.stepCount,
                (AdjustableParameterScale)setting.scaleKind);
        }

        public void SetOutputValue(
            float value,
            InstrumentValueChangeOrigin origin =
                InstrumentValueChangeOrigin.Programmatic)
        {
            Motion?.SetOutputValue(value, origin);
        }

        public void SetLeverDetentIndex(int detentIndex)
        {
            Motion?.SetLeverDetentIndex(detentIndex);
        }

        public void SetThrottleDetentIndex(int detentIndex)
        {
            Motion?.SetThrottleDetentIndex(detentIndex);
        }

        public void SetPowerSliderDetentIndex(int detentIndex)
        {
            Motion?.SetPowerSliderDetentIndex(detentIndex);
        }
    }
}
