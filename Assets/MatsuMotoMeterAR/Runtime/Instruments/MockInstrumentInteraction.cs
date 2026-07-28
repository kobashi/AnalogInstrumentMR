using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public sealed class MockInstrumentInteraction : MonoBehaviour
    {
        public MockInstrumentMotion Motion { get; private set; }
        public Collider InteractionCollider { get; private set; }
        public bool IsPressed { get; private set; }
        public float NormalizedValue => Motion != null ? Motion.NormalizedValue : 0f;
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
            Motion?.Actuate(pressed);
        }

        public void SetNormalizedValue(float value)
        {
            Motion?.SetNormalizedValue(value);
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
