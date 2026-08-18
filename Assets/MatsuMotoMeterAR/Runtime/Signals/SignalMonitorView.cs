using System.Globalization;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Rendering;
using UnityEngine;

namespace MatsuMotoMeterAR.Signals
{
    public sealed class SignalMonitorView : MonoBehaviour
    {
        public const int SampleCapacity = 32;
        public const float RefreshIntervalSeconds = 0.2f;

        private static readonly Color ConnectedColor =
            new(0.20f, 0.95f, 1f, 1f);
        private static readonly Color DisconnectedColor =
            new(0.65f, 0.68f, 0.70f, 1f);
        private static readonly Color InvalidColor =
            new(1f, 0.30f, 0.12f, 1f);

        private readonly SignalSampleBuffer samples =
            new(SampleCapacity);
        private readonly Vector3[] graphPositions =
            new Vector3[SampleCapacity];

        private TextMesh valueLabel;
        private LineRenderer graph;
        private bool connected;
        private float graphWidth;

        public bool IsConnected => connected;
        public int SampleCount => samples.Count;

        public static SignalMonitorView Create(
            Transform labelSocket,
            MockInstrumentKind kind)
        {
            var monitorObject = new GameObject("SignalMonitor");
            monitorObject.transform.SetParent(labelSocket, false);

            var spec = InstrumentGreyboxSpecification.Get(kind);
            monitorObject.transform.localPosition = new Vector3(
                0f,
                -spec.BoundsSize.y * 0.5f - 0.035f,
                spec.BoundsSize.z * 0.5f + 0.008f);

            var monitor = monitorObject.AddComponent<SignalMonitorView>();
            monitor.Build(Mathf.Clamp(spec.BoundsSize.x * 0.72f, 0.10f, 0.30f));
            return monitor;
        }

        public void SetSignalState(bool hasConnection, float value, int inputCount)
        {
            RefreshDisplay(hasConnection, value, inputCount);
        }

        private void Build(float graphWidth)
        {
            var labelObject = new GameObject("Value");
            labelObject.transform.SetParent(transform, false);
            labelObject.transform.localPosition = new Vector3(0f, 0.017f, 0f);
            valueLabel = labelObject.AddComponent<TextMesh>();
            valueLabel.anchor = TextAnchor.MiddleCenter;
            valueLabel.alignment = TextAlignment.Center;
            valueLabel.fontSize = 48;
            valueLabel.characterSize = 0.0022f;

            var graphObject = new GameObject("Trend");
            graphObject.transform.SetParent(transform, false);
            graph = graphObject.AddComponent<LineRenderer>();
            graph.useWorldSpace = false;
            graph.loop = false;
            graph.widthMultiplier = 0.002f;
            graph.numCapVertices = 0;
            graph.numCornerVertices = 0;
            RuntimeMaterialUtility.ApplySharedUnlit(graph, ConnectedColor);

            this.graphWidth = graphWidth;

            ApplyDisconnected();
        }

        private void RefreshDisplay(bool hasConnection, float value, int inputCount)
        {
            if (!hasConnection)
            {
                ApplyDisconnected();
                return;
            }

            connected = true;
            if (float.IsNaN(value) || float.IsInfinity(value))
            {
                valueLabel.text = "INVALID | 0—100 %";
                valueLabel.color = InvalidColor;
                graph.enabled = false;
                samples.Clear();
                return;
            }

            var outOfRange = value < 0f || value > 1f;
            var displayValue = Mathf.Clamp01(value);
            samples.Add(displayValue);
            valueLabel.text = string.Format(
                CultureInfo.InvariantCulture,
                inputCount > 1 ? "{0:0.0} % | {1} IN | 0—100" : "{0:0.0} % | 0—100",
                displayValue * 100f,
                inputCount);
            valueLabel.color = outOfRange ? InvalidColor : ConnectedColor;

            graph.enabled = samples.Count >= 2;
            graph.positionCount = samples.Count;
            for (var index = 0; index < samples.Count; index++)
            {
                var ratio = index / (float)(samples.Count - 1);
                graphPositions[index] = new Vector3(
                    (ratio - 0.5f) * graphWidth,
                    samples.GetOldestFirst(index) * 0.025f - 0.0125f,
                    0f);
            }
            graph.SetPositions(graphPositions);
            RuntimeMaterialUtility.SetColor(
                graph,
                outOfRange ? InvalidColor : ConnectedColor);
        }

        private void ApplyDisconnected()
        {
            connected = false;
            valueLabel.text = "NO SIGNAL | 0—100 %";
            valueLabel.color = DisconnectedColor;
            graph.enabled = false;
            samples.Clear();
        }
    }
}
