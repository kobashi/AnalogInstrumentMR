using MatsuMotoMeterAR.Rendering;
using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public sealed class MockInstrumentMotion : MonoBehaviour
    {
        public const int LeverDetentCount = 5;
        public const int StatusIndicatorStateCount = 4;
        public const int ThrottleDetentCount = 6;
        public const int PowerSliderDetentCount = 11;

        public enum MotionKind
        {
            Meter,
            Lever,
            Toggle,
            Rotate,
            Press,
            Pulse,
            Status,
            Throttle,
            PowerSlider
        }

        [SerializeField] private MotionKind motionKind;
        [SerializeField] private Transform movingPart;
        [SerializeField] private Vector3 localAxis = Vector3.forward;
        [SerializeField] private float amplitude = 45f;
        [SerializeField] private float rotationOffsetDegrees;
        [SerializeField, Range(0f, 1f)] private float normalizedValue;
        [SerializeField] private Renderer indicatorRenderer;

        private Quaternion initialRotation;
        private Vector3 initialPosition;
        private Color indicatorColor = Color.white;
        private Color statusSafeColor = Color.green;
        private Color statusWarningColor = Color.yellow;
        private Color statusDangerColor = Color.red;
        private bool configured;
        private int leverDirection = 1;
        private int throttleDirection = 1;
        private int powerSliderDirection = 1;

        public MotionKind Kind => motionKind;
        public Transform MovingPart => movingPart;
        public float NormalizedValue => normalizedValue;
        public int DetentCount => motionKind switch
        {
            MotionKind.Lever => LeverDetentCount,
            MotionKind.Status => StatusIndicatorStateCount,
            MotionKind.Throttle => ThrottleDetentCount,
            MotionKind.PowerSlider => PowerSliderDetentCount,
            _ => 0
        };
        public int DetentIndex =>
            DetentCount > 0
                ? Mathf.RoundToInt(normalizedValue * (DetentCount - 1))
                : -1;
        public string StateName => motionKind switch
        {
            MotionKind.Status => DetentIndex switch
            {
                1 => "SAFE",
                2 => "WARN",
                3 => "DANGER",
                _ => "OFF"
            },
            MotionKind.Throttle => DetentIndex switch
            {
                1 => "IDLE",
                2 => "LOW",
                3 => "CRUISE",
                4 => "HIGH",
                5 => "FULL",
                _ => "CUTOFF"
            },
            MotionKind.PowerSlider => DetentIndex switch
            {
                0 => "OFF",
                PowerSliderDetentCount - 1 => "MAX",
                _ => $"{DetentIndex * 10}%"
            },
            _ => string.Empty
        };

        public void Configure(
            MotionKind kind,
            Transform part,
            Vector3 axis,
            float range,
            float frequency,
            Renderer indicator = null,
            Color? activeColor = null,
            float rotationOffset = 0f)
        {
            var preservedValue = normalizedValue;
            motionKind = kind;
            movingPart = part;
            localAxis = axis.normalized;
            amplitude = range;
            rotationOffsetDegrees = rotationOffset;
            indicatorRenderer = indicator;
            indicatorColor = activeColor ?? Color.white;
            initialRotation = movingPart != null
                ? movingPart.localRotation
                : Quaternion.identity;
            initialPosition = movingPart != null
                ? movingPart.localPosition
                : Vector3.zero;

            if (!configured)
                normalizedValue = DefaultValue(kind);
            else
                normalizedValue = NormalizeValue(kind, preservedValue);
            configured = true;
            ApplyState();
        }

        public void ConfigureStatus(
            Transform part,
            Renderer indicator,
            Color safeColor,
            Color warningColor,
            Color dangerColor)
        {
            Configure(
                MotionKind.Status,
                part,
                Vector3.forward,
                1f,
                0f,
                indicator,
                safeColor);
            statusSafeColor = safeColor;
            statusWarningColor = warningColor;
            statusDangerColor = dangerColor;
            ApplyState();
        }

        public void Actuate(bool pressed)
        {
            if (!configured)
                return;

            if (motionKind == MotionKind.Press)
            {
                SetNormalizedValue(pressed ? 1f : 0f);
                return;
            }

            if (!pressed)
                return;

            switch (motionKind)
            {
                case MotionKind.Meter:
                    SetNormalizedValue(
                        normalizedValue >= 0.999f
                            ? 0f
                            : normalizedValue + 0.25f);
                    break;
                case MotionKind.Lever:
                    AdvanceLeverDetent();
                    break;
                case MotionKind.Toggle:
                case MotionKind.Pulse:
                    SetNormalizedValue(normalizedValue >= 0.5f ? 0f : 1f);
                    break;
                case MotionKind.Rotate:
                    SetNormalizedValue(Mathf.Repeat(normalizedValue + 0.125f, 1f));
                    break;
                case MotionKind.Status:
                    SetNormalizedValue(
                        (DetentIndex + 1) %
                        StatusIndicatorStateCount /
                        (float)(StatusIndicatorStateCount - 1));
                    break;
                case MotionKind.Throttle:
                    AdvanceThrottleDetent();
                    break;
                case MotionKind.PowerSlider:
                    AdvancePowerSliderDetent();
                    break;
            }
        }

        public void SetNormalizedValue(float value)
        {
            normalizedValue = NormalizeValue(motionKind, value);
            if (motionKind == MotionKind.Lever)
            {
                if (DetentIndex <= 0)
                    leverDirection = 1;
                else if (DetentIndex >= LeverDetentCount - 1)
                    leverDirection = -1;
            }
            else if (motionKind == MotionKind.Throttle)
            {
                if (DetentIndex <= 0)
                    throttleDirection = 1;
                else if (DetentIndex >= ThrottleDetentCount - 1)
                    throttleDirection = -1;
            }
            else if (motionKind == MotionKind.PowerSlider)
            {
                if (DetentIndex <= 0)
                    powerSliderDirection = 1;
                else if (DetentIndex >= PowerSliderDetentCount - 1)
                    powerSliderDirection = -1;
            }
            ApplyState();
        }

        public void SetLeverDetentIndex(int detentIndex)
        {
            if (motionKind != MotionKind.Lever)
                return;

            var clampedIndex = Mathf.Clamp(
                detentIndex,
                0,
                LeverDetentCount - 1);
            SetNormalizedValue(
                clampedIndex / (float)(LeverDetentCount - 1));
        }

        public void SetThrottleDetentIndex(int detentIndex)
        {
            if (motionKind != MotionKind.Throttle)
                return;

            var clampedIndex = Mathf.Clamp(
                detentIndex,
                0,
                ThrottleDetentCount - 1);
            SetNormalizedValue(
                clampedIndex / (float)(ThrottleDetentCount - 1));
        }

        public void SetPowerSliderDetentIndex(int detentIndex)
        {
            if (motionKind != MotionKind.PowerSlider)
                return;

            var clampedIndex = Mathf.Clamp(
                detentIndex,
                0,
                PowerSliderDetentCount - 1);
            SetNormalizedValue(
                clampedIndex / (float)(PowerSliderDetentCount - 1));
        }

        private void AdvanceLeverDetent()
        {
            var currentIndex = DetentIndex;
            if (currentIndex >= LeverDetentCount - 1)
                leverDirection = -1;
            else if (currentIndex <= 0)
                leverDirection = 1;

            SetLeverDetentIndex(currentIndex + leverDirection);
        }

        private void AdvanceThrottleDetent()
        {
            var currentIndex = DetentIndex;
            if (currentIndex >= ThrottleDetentCount - 1)
                throttleDirection = -1;
            else if (currentIndex <= 0)
                throttleDirection = 1;

            SetThrottleDetentIndex(currentIndex + throttleDirection);
        }

        private void AdvancePowerSliderDetent()
        {
            var currentIndex = DetentIndex;
            if (currentIndex >= PowerSliderDetentCount - 1)
                powerSliderDirection = -1;
            else if (currentIndex <= 0)
                powerSliderDirection = 1;

            SetPowerSliderDetentIndex(
                currentIndex + powerSliderDirection);
        }

        private void ApplyState()
        {
            if (movingPart == null)
                return;

            switch (motionKind)
            {
                case MotionKind.Meter:
                case MotionKind.Lever:
                case MotionKind.Toggle:
                case MotionKind.Throttle:
                    var angle =
                        Mathf.Lerp(-amplitude, amplitude, normalizedValue) +
                        rotationOffsetDegrees;
                    movingPart.localRotation =
                        initialRotation * Quaternion.AngleAxis(angle, localAxis);
                    break;
                case MotionKind.Rotate:
                    movingPart.localRotation =
                        initialRotation *
                        Quaternion.AngleAxis(normalizedValue * 360f, localAxis);
                    break;
                case MotionKind.Press:
                    movingPart.localPosition =
                        initialPosition + localAxis * (normalizedValue * amplitude);
                    break;
                case MotionKind.Pulse:
                    var intensity = Mathf.Lerp(0.12f, 1f, normalizedValue);
                    var color = Color.Lerp(Color.black, indicatorColor, intensity);
                    RuntimeMaterialUtility.SetColor(indicatorRenderer, color);
                    RuntimeMaterialUtility.SetEmissionColor(
                        indicatorRenderer,
                        color * 1.5f);
                    break;
                case MotionKind.Status:
                    var statusColor = DetentIndex switch
                    {
                        1 => statusSafeColor,
                        2 => statusWarningColor,
                        3 => statusDangerColor,
                        _ => Color.black
                    };
                    RuntimeMaterialUtility.SetColor(
                        indicatorRenderer,
                        statusColor);
                    RuntimeMaterialUtility.SetEmissionColor(
                        indicatorRenderer,
                        statusColor * (DetentIndex == 0 ? 0f : 1.5f));
                    break;
                case MotionKind.PowerSlider:
                    movingPart.localPosition =
                        initialPosition +
                        localAxis *
                        Mathf.Lerp(
                            -amplitude * 0.5f,
                            amplitude * 0.5f,
                            normalizedValue);
                    break;
            }
        }

        private static float DefaultValue(MotionKind kind)
        {
            return kind switch
            {
                MotionKind.Meter or MotionKind.Lever or MotionKind.Toggle => 0.5f,
                MotionKind.Pulse => 1f,
                MotionKind.Status => 0f,
                MotionKind.Throttle => 0f,
                MotionKind.PowerSlider => 0f,
                _ => 0f
            };
        }

        private static float NormalizeValue(MotionKind kind, float value)
        {
            var clamped = Mathf.Clamp01(value);
            var stepCount = kind switch
            {
                MotionKind.Lever => LeverDetentCount,
                MotionKind.Status => StatusIndicatorStateCount,
                MotionKind.Throttle => ThrottleDetentCount,
                MotionKind.PowerSlider => PowerSliderDetentCount,
                _ => 0
            };
            if (stepCount == 0)
                return clamped;

            var detentIndex = Mathf.RoundToInt(
                clamped * (stepCount - 1));
            return detentIndex / (float)(stepCount - 1);
        }
    }
}
