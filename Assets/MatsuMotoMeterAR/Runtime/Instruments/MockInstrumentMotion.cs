using System;
using MatsuMotoMeterAR.Audio;
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
            PowerSlider,
            Display
        }

        [SerializeField] private MotionKind motionKind;
        [SerializeField] private Transform movingPart;
        [SerializeField] private Vector3 localAxis = Vector3.forward;
        [SerializeField] private float amplitude = 45f;
        [SerializeField] private float frequencyHz;
        [SerializeField] private float rotationOffsetDegrees;
        [SerializeField, Range(0f, 1f)] private float normalizedValue;
        [SerializeField] private Renderer indicatorRenderer;
        [SerializeField] private Renderer[] statusRenderers;
        [SerializeField] private float outputMinimum;
        [SerializeField] private float outputMaximum = 1f;
        [SerializeField] private int configuredStepCount;
        [SerializeField] private AdjustableParameterScale outputScale;

        private Quaternion initialRotation;
        private Vector3 initialPosition;
        private Color indicatorColor = Color.white;
        private Color statusSafeColor = Color.green;
        private Color statusWarningColor = Color.yellow;
        private Color statusDangerColor = Color.red;
        private float meterPhase;
        private bool ambientAnimationEnabled;
        private bool configured;
        private bool parameterRangeConfigured;
        private int leverDirection = 1;
        private int throttleDirection = 1;
        private int powerSliderDirection = 1;
        private float stickVisualValue;
        private float stickVisualTarget;
        private float stickVisualVelocity;
        private bool stickVisualActive;

        private const float StickVisualSmoothTime = 0.08f;

        public event Action<InstrumentValueChange> ValueChanged;

        public MotionKind Kind => motionKind;
        public Transform MovingPart => movingPart;
        public float NormalizedValue => normalizedValue;
        public float StickVisualTarget => stickVisualActive
            ? stickVisualTarget
            : normalizedValue;
        public float OutputValue => MapOutputValue(normalizedValue);
        public float DefaultNormalizedValue => DefaultValue(motionKind);
        public int DetentCount => motionKind switch
        {
            MotionKind.Lever => parameterRangeConfigured
                ? configuredStepCount
                : LeverDetentCount,
            MotionKind.Toggle or MotionKind.Press => parameterRangeConfigured
                ? configuredStepCount
                : 0,
            MotionKind.Status => StatusIndicatorStateCount,
            MotionKind.Throttle => parameterRangeConfigured
                ? configuredStepCount
                : ThrottleDetentCount,
            MotionKind.PowerSlider => parameterRangeConfigured
                ? configuredStepCount
                : PowerSliderDetentCount,
            MotionKind.Rotate => parameterRangeConfigured
                ? configuredStepCount
                : 0,
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
            MotionKind.Throttle => DetentCount == ThrottleDetentCount
                ? DetentIndex switch
                {
                    1 => "IDLE",
                    2 => "LOW",
                    3 => "CRUISE",
                    4 => "HIGH",
                    5 => "FULL",
                    _ => "CUTOFF"
                }
                : DetentIndex switch
                {
                    <= 0 => "CUTOFF",
                    var index when index == DetentCount - 1 => "FULL",
                    _ => $"{Mathf.RoundToInt(DetentIndex * 100f / Mathf.Max(1, DetentCount - 1))}%"
                },
            MotionKind.PowerSlider => DetentIndex switch
            {
                0 => "OFF",
                var index when index == DetentCount - 1 => "MAX",
                _ => $"{Mathf.RoundToInt(DetentIndex * 100f / Mathf.Max(1, DetentCount - 1))}%"
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
            frequencyHz = frequency;
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
                normalizedValue = NormalizeValue(preservedValue);
            configured = true;
            stickVisualValue = normalizedValue;
            stickVisualTarget = normalizedValue;
            stickVisualVelocity = 0f;
            stickVisualActive = false;
            meterPhase = Mathf.Repeat(
                movingPart != null
                    ? movingPart.GetInstanceID() * 0.173f
                    : 0f,
                Mathf.PI * 2f);
            ApplyState();
        }

        public void ConfigureParameterRange(
            float minimum,
            float maximum,
            int stepCount,
            AdjustableParameterScale scale)
        {
            if (float.IsNaN(minimum) || float.IsInfinity(minimum) ||
                float.IsNaN(maximum) || float.IsInfinity(maximum))
            {
                minimum = 0f;
                maximum = 1f;
            }
            if (minimum > maximum)
                (minimum, maximum) = (maximum, minimum);
            if (Mathf.Approximately(minimum, maximum))
                maximum = minimum + 0.0001f;

            outputMinimum = minimum;
            outputMaximum = maximum;
            configuredStepCount = stepCount >= 2
                ? Mathf.Clamp(
                    stepCount,
                    2,
                    AdjustableParameterPolicy.MaximumStepCount)
                : 0;
            outputScale = scale == AdjustableParameterScale.Logarithmic &&
                          minimum > 0f
                ? AdjustableParameterScale.Logarithmic
                : AdjustableParameterScale.Linear;
            parameterRangeConfigured = true;
            SetNormalizedValue(normalizedValue);
        }

        public void SetOutputValue(
            float value,
            InstrumentValueChangeOrigin origin =
                InstrumentValueChangeOrigin.Programmatic)
        {
            if (!parameterRangeConfigured)
            {
                SetNormalizedValue(value, origin);
                return;
            }
            value = Mathf.Clamp(value, outputMinimum, outputMaximum);
            var normalized = outputScale ==
                                 AdjustableParameterScale.Logarithmic &&
                             outputMinimum > 0f && value > 0f
                ? Mathf.Log(value / outputMinimum) /
                  Mathf.Log(outputMaximum / outputMinimum)
                : Mathf.InverseLerp(outputMinimum, outputMaximum, value);
            SetNormalizedValue(normalized, origin);
        }

        public void SetAmbientAnimationEnabled(bool enabled)
        {
            if (ambientAnimationEnabled == enabled)
                return;

            ambientAnimationEnabled = enabled;
            ApplyState();
        }

        public void ConfigureStatus(
            Transform part,
            Renderer indicator,
            Color safeColor,
            Color warningColor,
            Color dangerColor,
            Renderer[] segmentedRenderers = null)
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
            statusRenderers = segmentedRenderers;
            ApplyState();
        }

        public void Actuate(
            bool pressed,
            InstrumentValueChangeOrigin origin =
                InstrumentValueChangeOrigin.Programmatic)
        {
            if (!configured)
                return;

            if (motionKind == MotionKind.Press)
            {
                SetNormalizedValue(pressed ? 1f : 0f, origin);
                return;
            }

            if (!pressed)
                return;

            switch (motionKind)
            {
                case MotionKind.Meter:
                    // Meters are read-only in operation mode.
                    break;
                case MotionKind.Lever:
                    AdvanceLeverDetent(origin);
                    break;
                case MotionKind.Toggle:
                case MotionKind.Pulse:
                    SetNormalizedValue(
                        normalizedValue >= 0.5f ? 0f : 1f,
                        origin);
                    break;
                case MotionKind.Rotate:
                    if (DetentCount >= 2)
                    {
                        SetNormalizedValue(
                            DetentIndex >= DetentCount - 1
                                ? 0f
                                : (DetentIndex + 1) /
                                  (float)(DetentCount - 1),
                            origin);
                    }
                    else
                    {
                        SetNormalizedValue(
                            Mathf.Repeat(normalizedValue + 0.125f, 1f),
                            origin);
                    }
                    break;
                case MotionKind.Status:
                    SetNormalizedValue(
                        (DetentIndex + 1) %
                        DetentCount /
                        (float)(DetentCount - 1),
                        origin);
                    break;
                case MotionKind.Throttle:
                    AdvanceThrottleDetent(origin);
                    break;
                case MotionKind.PowerSlider:
                    AdvancePowerSliderDetent(origin);
                    break;
            }
        }

        public void Step(
            int direction,
            InstrumentValueChangeOrigin origin =
                InstrumentValueChangeOrigin.UserInteraction)
        {
            if (!configured || direction == 0)
                return;

            direction = direction > 0 ? 1 : -1;
            switch (motionKind)
            {
                case MotionKind.Lever:
                case MotionKind.Throttle:
                case MotionKind.PowerSlider:
                case MotionKind.Status:
                case MotionKind.Rotate when DetentCount >= 2:
                    SetNormalizedValue(
                        (Mathf.Clamp(DetentIndex + direction, 0, DetentCount - 1)) /
                        (float)(DetentCount - 1),
                        origin);
                    break;
                case MotionKind.Rotate:
                    SetNormalizedValue(normalizedValue + direction * 0.125f, origin);
                    break;
                case MotionKind.Toggle:
                case MotionKind.Pulse:
                    SetNormalizedValue(direction > 0 ? 1f : 0f, origin);
                    break;
            }
        }

        public void SetNormalizedValue(
            float value,
            InstrumentValueChangeOrigin origin =
                InstrumentValueChangeOrigin.Programmatic)
        {
            SetNormalizedValueInternal(value, origin, true);
        }

        public void SetStickControlledValue(
            float value,
            InstrumentValueChangeOrigin origin =
                InstrumentValueChangeOrigin.UserInteraction)
        {
            if (!configured)
                return;

            if (!stickVisualActive)
            {
                stickVisualValue = normalizedValue;
                stickVisualVelocity = 0f;
            }
            stickVisualActive = true;
            stickVisualTarget = Mathf.Clamp01(value);
            SetNormalizedValueInternal(value, origin, false);
        }

        public void EndStickControl()
        {
            if (!stickVisualActive)
                return;
            stickVisualTarget = normalizedValue;
        }

        private void SetNormalizedValueInternal(
            float value,
            InstrumentValueChangeOrigin origin,
            bool applyVisualImmediately)
        {
            var previousValue = normalizedValue;
            var previousDetent = DetentIndexFor(previousValue);
            var nextValue = NormalizeValue(value);
            if (applyVisualImmediately)
            {
                stickVisualActive = false;
                stickVisualValue = nextValue;
                stickVisualTarget = nextValue;
                stickVisualVelocity = 0f;
            }
            if (Mathf.Abs(previousValue - nextValue) <= 0.000001f)
            {
                if (applyVisualImmediately)
                    ApplyState();
                return;
            }

            normalizedValue = nextValue;
            if (motionKind == MotionKind.Lever)
            {
                if (DetentIndex <= 0)
                    leverDirection = 1;
                else if (DetentIndex >= DetentCount - 1)
                    leverDirection = -1;
            }
            else if (motionKind == MotionKind.Throttle)
            {
                if (DetentIndex <= 0)
                    throttleDirection = 1;
                else if (DetentIndex >= DetentCount - 1)
                    throttleDirection = -1;
            }
            else if (motionKind == MotionKind.PowerSlider)
            {
                if (DetentIndex <= 0)
                    powerSliderDirection = 1;
                else if (DetentIndex >= DetentCount - 1)
                    powerSliderDirection = -1;
            }
            if (applyVisualImmediately)
                ApplyState();
            ValueChanged?.Invoke(new InstrumentValueChange(
                motionKind,
                previousValue,
                normalizedValue,
                previousDetent,
                DetentIndexFor(normalizedValue),
                origin));
        }

        public void SetLeverDetentIndex(
            int detentIndex,
            InstrumentValueChangeOrigin origin =
                InstrumentValueChangeOrigin.Programmatic)
        {
            if (motionKind != MotionKind.Lever)
                return;
            if (DetentCount < 2)
                return;

            var clampedIndex = Mathf.Clamp(
                detentIndex,
                0,
                DetentCount - 1);
            SetNormalizedValue(
                clampedIndex / (float)(DetentCount - 1),
                origin);
        }

        public void SetThrottleDetentIndex(
            int detentIndex,
            InstrumentValueChangeOrigin origin =
                InstrumentValueChangeOrigin.Programmatic)
        {
            if (motionKind != MotionKind.Throttle)
                return;
            if (DetentCount < 2)
                return;

            var clampedIndex = Mathf.Clamp(
                detentIndex,
                0,
                DetentCount - 1);
            SetNormalizedValue(
                clampedIndex / (float)(DetentCount - 1),
                origin);
        }

        public void SetPowerSliderDetentIndex(
            int detentIndex,
            InstrumentValueChangeOrigin origin =
                InstrumentValueChangeOrigin.Programmatic)
        {
            if (motionKind != MotionKind.PowerSlider)
                return;
            if (DetentCount < 2)
                return;

            var clampedIndex = Mathf.Clamp(
                detentIndex,
                0,
                DetentCount - 1);
            SetNormalizedValue(
                clampedIndex / (float)(DetentCount - 1),
                origin);
        }

        private void AdvanceLeverDetent(InstrumentValueChangeOrigin origin)
        {
            if (DetentCount < 2)
            {
                AdvanceContinuous(origin, ref leverDirection);
                return;
            }
            var currentIndex = DetentIndex;
            if (currentIndex >= DetentCount - 1)
                leverDirection = -1;
            else if (currentIndex <= 0)
                leverDirection = 1;

            SetLeverDetentIndex(currentIndex + leverDirection, origin);
        }

        private void AdvanceThrottleDetent(InstrumentValueChangeOrigin origin)
        {
            if (DetentCount < 2)
            {
                AdvanceContinuous(origin, ref throttleDirection);
                return;
            }
            var currentIndex = DetentIndex;
            if (currentIndex >= DetentCount - 1)
                throttleDirection = -1;
            else if (currentIndex <= 0)
                throttleDirection = 1;

            SetThrottleDetentIndex(currentIndex + throttleDirection, origin);
        }

        private void AdvancePowerSliderDetent(InstrumentValueChangeOrigin origin)
        {
            if (DetentCount < 2)
            {
                AdvanceContinuous(origin, ref powerSliderDirection);
                return;
            }
            var currentIndex = DetentIndex;
            if (currentIndex >= DetentCount - 1)
                powerSliderDirection = -1;
            else if (currentIndex <= 0)
                powerSliderDirection = 1;

            SetPowerSliderDetentIndex(
                currentIndex + powerSliderDirection,
                origin);
        }

        private void AdvanceContinuous(
            InstrumentValueChangeOrigin origin,
            ref int direction)
        {
            if (normalizedValue >= 1f)
                direction = -1;
            else if (normalizedValue <= 0f)
                direction = 1;
            SetNormalizedValue(
                normalizedValue + direction * 0.125f,
                origin);
        }

        private void ApplyState()
        {
            ApplyState(normalizedValue);
        }

        private void ApplyState(float visualValue)
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
                        Mathf.Lerp(-amplitude, amplitude, visualValue) +
                        rotationOffsetDegrees;
                    movingPart.localRotation =
                        initialRotation * Quaternion.AngleAxis(angle, localAxis);
                    break;
                case MotionKind.Rotate:
                    movingPart.localRotation =
                        initialRotation *
                        Quaternion.AngleAxis(visualValue * 360f, localAxis);
                    break;
                case MotionKind.Press:
                    movingPart.localPosition =
                        initialPosition + localAxis * (visualValue * amplitude);
                    break;
                case MotionKind.Pulse:
                    var intensity = Mathf.Lerp(0.12f, 1f, visualValue);
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
                    ApplySegmentedStatus();
                    break;
                case MotionKind.PowerSlider:
                    movingPart.localPosition =
                        initialPosition +
                        localAxis *
                        Mathf.Lerp(
                            -amplitude * 0.5f,
                            amplitude * 0.5f,
                            visualValue);
                    break;
            }
        }

        private void ApplySegmentedStatus()
        {
            if (statusRenderers == null || statusRenderers.Length == 0)
                return;

            var activeIndex = DetentIndex - 1;
            for (var index = 0;
                 index < statusRenderers.Length;
                 index++)
            {
                var active =
                    index == activeIndex &&
                    index < 3;
                var color = active
                    ? StatusColor(index)
                    : Color.black;
                RuntimeMaterialUtility.SetColor(
                    statusRenderers[index],
                    color);
                RuntimeMaterialUtility.SetEmissionColor(
                    statusRenderers[index],
                    color * (active ? 1.5f : 0f));
            }
        }

        private Color StatusColor(int index)
        {
            return index switch
            {
                0 => statusSafeColor,
                1 => statusWarningColor,
                2 => statusDangerColor,
                _ => Color.black
            };
        }

        private void Update()
        {
            if (configured && stickVisualActive && movingPart != null)
            {
                stickVisualValue = Mathf.SmoothDamp(
                    stickVisualValue,
                    stickVisualTarget,
                    ref stickVisualVelocity,
                    StickVisualSmoothTime,
                    Mathf.Infinity,
                    Time.unscaledDeltaTime);
                ApplyState(stickVisualValue);
                if (Mathf.Abs(stickVisualValue - stickVisualTarget) < 0.0001f &&
                    Mathf.Approximately(stickVisualTarget, normalizedValue))
                {
                    stickVisualValue = normalizedValue;
                    stickVisualActive = false;
                    ApplyState();
                }
            }

            if (!configured ||
                !ambientAnimationEnabled ||
                motionKind != MotionKind.Meter ||
                movingPart == null)
            {
                return;
            }

            var baseAngle =
                Mathf.Lerp(-amplitude, amplitude, normalizedValue) +
                rotationOffsetDegrees;
            var time = Time.unscaledTime * Mathf.PI * 2f;
            var primary =
                Mathf.Sin(time * Mathf.Max(0.05f, frequencyHz) + meterPhase);
            var secondary =
                Mathf.Sin(
                    time * Mathf.Max(0.08f, frequencyHz * 1.73f) +
                    meterPhase * 0.43f);
            var microAngle = primary * 1.4f + secondary * 0.45f;
            movingPart.localRotation =
                initialRotation *
                Quaternion.AngleAxis(
                    baseAngle + microAngle,
                    localAxis);
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

        private float NormalizeValue(float value)
        {
            var clamped = Mathf.Clamp01(value);
            var stepCount = DetentCount;
            if (stepCount == 0)
                return clamped;

            var detentIndex = Mathf.RoundToInt(
                clamped * (stepCount - 1));
            return detentIndex / (float)(stepCount - 1);
        }

        private int DetentIndexFor(float value)
        {
            var count = DetentCount;
            return count > 0
                ? Mathf.RoundToInt(Mathf.Clamp01(value) * (count - 1))
                : -1;
        }

        private float MapOutputValue(float value)
        {
            var t = Mathf.Clamp01(value);
            if (!parameterRangeConfigured)
                return t;
            return outputScale == AdjustableParameterScale.Logarithmic &&
                   outputMinimum > 0f
                ? outputMinimum * Mathf.Pow(
                    outputMaximum / outputMinimum,
                    t)
                : Mathf.Lerp(outputMinimum, outputMaximum, t);
        }
    }
}
