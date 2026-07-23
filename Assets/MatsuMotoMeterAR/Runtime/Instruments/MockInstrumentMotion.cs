using MatsuMotoMeterAR.Rendering;
using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public sealed class MockInstrumentMotion : MonoBehaviour
    {
        public enum MotionKind
        {
            Meter,
            Lever,
            Toggle,
            Rotate,
            Press,
            Pulse
        }

        [SerializeField] private MotionKind motionKind;
        [SerializeField] private Transform movingPart;
        [SerializeField] private Vector3 localAxis = Vector3.forward;
        [SerializeField] private float amplitude = 45f;
        [SerializeField, Range(0f, 1f)] private float normalizedValue;
        [SerializeField] private Renderer indicatorRenderer;

        private Quaternion initialRotation;
        private Vector3 initialPosition;
        private Color indicatorColor = Color.white;
        private bool configured;

        public MotionKind Kind => motionKind;
        public Transform MovingPart => movingPart;
        public float NormalizedValue => normalizedValue;

        public void Configure(
            MotionKind kind,
            Transform part,
            Vector3 axis,
            float range,
            float frequency,
            Renderer indicator = null,
            Color? activeColor = null)
        {
            var preservedValue = normalizedValue;
            motionKind = kind;
            movingPart = part;
            localAxis = axis.normalized;
            amplitude = range;
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
                normalizedValue = Mathf.Clamp01(preservedValue);
            configured = true;
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
                case MotionKind.Toggle:
                case MotionKind.Pulse:
                    SetNormalizedValue(normalizedValue >= 0.5f ? 0f : 1f);
                    break;
                case MotionKind.Rotate:
                    SetNormalizedValue(Mathf.Repeat(normalizedValue + 0.125f, 1f));
                    break;
            }
        }

        public void SetNormalizedValue(float value)
        {
            normalizedValue = Mathf.Clamp01(value);
            ApplyState();
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
                    var angle = Mathf.Lerp(-amplitude, amplitude, normalizedValue);
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
            }
        }

        private static float DefaultValue(MotionKind kind)
        {
            return kind switch
            {
                MotionKind.Meter or MotionKind.Lever or MotionKind.Toggle => 0.5f,
                MotionKind.Pulse => 1f,
                _ => 0f
            };
        }
    }
}
