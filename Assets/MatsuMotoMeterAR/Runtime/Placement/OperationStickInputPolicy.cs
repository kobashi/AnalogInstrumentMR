using MatsuMotoMeterAR.Instruments;
using UnityEngine;

namespace MatsuMotoMeterAR.Placement
{
    public static class OperationStickInputPolicy
    {
        public static float ApplyVerticalDelta(
            MockInstrumentKind kind,
            float currentValue,
            float stickY,
            float speed,
            float deltaTime)
        {
            var direction = UsesInvertedVerticalDirection(kind) ? -1f : 1f;
            return Mathf.Clamp01(
                currentValue +
                stickY * direction *
                Mathf.Max(0f, speed) * Mathf.Max(0f, deltaTime));
        }

        public static bool UsesInvertedVerticalDirection(
            MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.Lever ||
                   kind == MockInstrumentKind.ThrottleLever;
        }
    }
}
