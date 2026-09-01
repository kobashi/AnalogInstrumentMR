using System;
using UnityEngine;

namespace MatsuMotoMeterAR.Signals
{
    public enum WindowPanelGraphicPreset
    {
        Orbit = 0,
        Rose = 1,
        Lissajous = 2
    }

    public readonly struct WindowPanelGraphicInputs
    {
        public WindowPanelGraphicInputs(
            float energy,
            float balance,
            float phase,
            float detail,
            bool hasInvalidInput,
            int connectedCount)
        {
            Energy = energy;
            Balance = balance;
            Phase = phase;
            Detail = detail;
            HasInvalidInput = hasInvalidInput;
            ConnectedCount = connectedCount;
        }

        public float Energy { get; }
        public float Balance { get; }
        public float Phase { get; }
        public float Detail { get; }
        public bool HasInvalidInput { get; }
        public int ConnectedCount { get; }
    }

    public static class WindowPanelGraphicGeometry
    {
        public const int SlotCount = 4;
        public const int SampleCount = 64;
        public const int ContourCount = 2;
        public const int VertexCapacity =
            SampleCount * ContourCount * 2;
        public const int IndexCapacity =
            SampleCount * ContourCount * 6;
        public const float HalfWidth = 1f;
        public const float HalfHeight = 0.55f;

        private const float RibbonHalfWidth = 0.012f;
        private const float Tau = Mathf.PI * 2f;

        private static readonly float[] NeutralSlots =
        {
            0.5f, 0.5f, 0.5f, 0f
        };

        public static WindowPanelGraphicInputs ResolveInputs(
            float[] values,
            bool[] connected)
        {
            var resolved = new float[SlotCount];
            return ResolveInputs(values, connected, resolved);
        }

        public static WindowPanelGraphicInputs ResolveInputs(
            float[] values,
            bool[] connected,
            float[] resolved)
        {
            if (resolved == null || resolved.Length < SlotCount)
                throw new ArgumentException(
                    $"Resolved buffer must contain {SlotCount} values.",
                    nameof(resolved));

            var invalid = false;
            var connectedCount = 0;
            for (var slot = 0; slot < SlotCount; slot++)
            {
                var isConnected = connected != null &&
                                  slot < connected.Length &&
                                  connected[slot];
                if (!isConnected)
                {
                    resolved[slot] = NeutralSlots[slot];
                    continue;
                }

                connectedCount++;
                var value = values != null && slot < values.Length
                    ? values[slot]
                    : float.NaN;
                if (float.IsNaN(value) || float.IsInfinity(value))
                {
                    invalid = true;
                    resolved[slot] = NeutralSlots[slot];
                    continue;
                }
                resolved[slot] = Mathf.Clamp01(value);
            }

            return new WindowPanelGraphicInputs(
                Mathf.Lerp(0.45f, 0.95f, resolved[0]),
                Mathf.Lerp(0.60f, 1.40f, resolved[1]),
                Mathf.Lerp(-Mathf.PI, Mathf.PI, resolved[2]),
                resolved[3],
                invalid,
                connectedCount);
        }

        public static void BuildRibbon(
            WindowPanelGraphicPreset preset,
            WindowPanelGraphicInputs inputs,
            Vector3[] vertices,
            int[] indices,
            out int vertexCount,
            out int indexCount,
            out Bounds bounds)
        {
            if (vertices == null || vertices.Length < VertexCapacity)
                throw new ArgumentException(
                    $"Vertex buffer must contain {VertexCapacity} values.",
                    nameof(vertices));
            if (indices == null || indices.Length < IndexCapacity)
                throw new ArgumentException(
                    $"Index buffer must contain {IndexCapacity} values.",
                    nameof(indices));

            vertexCount = 0;
            indexCount = 0;
            var minimum = new Vector3(float.PositiveInfinity,
                float.PositiveInfinity, 0f);
            var maximum = new Vector3(float.NegativeInfinity,
                float.NegativeInfinity, 0f);

            for (var contour = 0; contour < ContourCount; contour++)
            {
                var contourBase = vertexCount;
                for (var sample = 0; sample < SampleCount; sample++)
                {
                    var t = sample / (float)SampleCount;
                    var previous = Evaluate(
                        preset,
                        inputs,
                        RepeatSample(sample - 1),
                        contour);
                    var current = Evaluate(
                        preset,
                        inputs,
                        t,
                        contour);
                    var next = Evaluate(
                        preset,
                        inputs,
                        RepeatSample(sample + 1),
                        contour);
                    var tangent = (next - previous).normalized;
                    if (tangent.sqrMagnitude < 0.000001f)
                        tangent = Vector2.right;
                    var normal = new Vector2(-tangent.y, tangent.x) *
                                 RibbonHalfWidth;
                    var left = current - normal;
                    var right = current + normal;
                    vertices[vertexCount++] = new Vector3(left.x, left.y, 0f);
                    vertices[vertexCount++] = new Vector3(right.x, right.y, 0f);
                    minimum.x = Mathf.Min(
                        minimum.x, Mathf.Min(left.x, right.x));
                    minimum.y = Mathf.Min(
                        minimum.y, Mathf.Min(left.y, right.y));
                    maximum.x = Mathf.Max(
                        maximum.x, Mathf.Max(left.x, right.x));
                    maximum.y = Mathf.Max(
                        maximum.y, Mathf.Max(left.y, right.y));
                }

                for (var sample = 0; sample < SampleCount; sample++)
                {
                    var next = (sample + 1) % SampleCount;
                    var a = contourBase + sample * 2;
                    var b = a + 1;
                    var c = contourBase + next * 2;
                    var d = c + 1;
                    indices[indexCount++] = a;
                    indices[indexCount++] = b;
                    indices[indexCount++] = c;
                    indices[indexCount++] = b;
                    indices[indexCount++] = d;
                    indices[indexCount++] = c;
                }
            }

            var size = maximum - minimum;
            bounds = new Bounds((minimum + maximum) * 0.5f, size);
        }

        public static Vector2 Evaluate(
            WindowPanelGraphicPreset preset,
            WindowPanelGraphicInputs inputs,
            float normalizedTime,
            int contour)
        {
            var theta = Repeat01(normalizedTime) * Tau;
            var balance = Mathf.Clamp(inputs.Balance, 0.60f, 1.40f);
            var xAspect = Mathf.Lerp(0.72f, 1f,
                Mathf.InverseLerp(0.60f, 1.40f, balance));
            var yAspect = Mathf.Lerp(1f, 0.72f,
                Mathf.InverseLerp(0.60f, 1.40f, balance));
            var energy = Mathf.Clamp(inputs.Energy, 0.45f, 0.95f);
            var phase = inputs.Phase;
            var detail = Mathf.Clamp01(inputs.Detail);
            var x = 0f;
            var y = 0f;

            switch (preset)
            {
                case WindowPanelGraphicPreset.Rose:
                    var rosePhase = phase + contour * 0.16f * detail;
                    var radius = 0.72f +
                                 (0.08f + 0.20f * detail) *
                                 Mathf.Cos(3f * theta + rosePhase);
                    x = Mathf.Cos(theta + phase * 0.20f) * radius;
                    y = Mathf.Sin(theta + phase * 0.20f) * radius;
                    break;
                case WindowPanelGraphicPreset.Lissajous:
                    var offset = contour * 0.10f * detail;
                    x = Mathf.Sin(2f * theta + phase + offset);
                    y = Mathf.Sin(3f * theta - offset);
                    break;
                default:
                    var separation = contour *
                                     (0.06f + 0.09f * detail);
                    var orbitX = Mathf.Cos(theta) * (1f - separation);
                    var orbitY = Mathf.Sin(theta) *
                                 (1f - separation * 0.75f);
                    var phaseCos = Mathf.Cos(phase);
                    var phaseSin = Mathf.Sin(phase);
                    x = orbitX * phaseCos - orbitY * phaseSin;
                    y = orbitX * phaseSin + orbitY * phaseCos;
                    break;
            }

            return new Vector2(
                x * 0.92f * energy * xAspect,
                y * 0.52f * energy * yAspect);
        }

        private static float RepeatSample(int sample)
        {
            return ((sample % SampleCount) + SampleCount) % SampleCount /
                   (float)SampleCount;
        }

        private static float Repeat01(float value)
        {
            return value - Mathf.Floor(value);
        }
    }
}
