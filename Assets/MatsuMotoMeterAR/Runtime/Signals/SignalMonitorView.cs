using System.Globalization;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Rendering;
using UnityEngine;

namespace MatsuMotoMeterAR.Signals
{
    public sealed class SignalMonitorView : MonoBehaviour
    {
        public const int ChannelCapacity = 4;
        public const int SampleCapacity = 32;
        public const float RefreshIntervalSeconds = 0.2f;
        private const int GraphPointCapacity = 24;
        private const float ValueReadoutY = 0.068f;
        private const float GraphLeft = -0.145f;
        private const float GraphRight = 0.145f;
        private const float GraphBottom = -0.045f;
        private const float GraphTop = 0.045f;
        private const float GraphWidth = 0.0045f;
        private const int GraphCornerVertices = 8;
        private const int GraphCapVertices = 6;

        private static readonly Color[] ChannelColors =
        {
            new(0.20f, 0.95f, 1f, 1f),
            new(1f, 0.72f, 0.18f, 1f),
            new(0.42f, 1f, 0.34f, 1f),
            new(0.94f, 0.35f, 1f, 1f)
        };

        private static readonly Color DisconnectedColor =
            new(0.65f, 0.68f, 0.70f, 1f);
        private static readonly Color InvalidColor =
            new(1f, 0.30f, 0.12f, 1f);

        private readonly Channel[] channels = new Channel[ChannelCapacity];
        private TextMesh statusLabel;

        public int ConnectedChannelCount { get; private set; }

        private const float DisplayClearanceMeters = 0.0002f;

        public static SignalMonitorView Create(
            Transform labelSocket,
            Transform displaySurface)
        {
            var monitorObject = new GameObject("TrendMonitorDisplay");
            monitorObject.transform.SetParent(labelSocket, false);
            var monitor = monitorObject.AddComponent<SignalMonitorView>();
            if (displaySurface != null)
            {
                monitor.AlignToDisplay(displaySurface);
            }
            else
            {
                monitorObject.transform.localPosition =
                    new Vector3(0f, 0f, 0.091f);
                monitorObject.transform.localRotation = Quaternion.identity;
            }

            monitor.Build();
            return monitor;
        }

        public void AlignToDisplay(Transform displaySurface)
        {
            if (displaySurface == null)
                return;

            var normal = ResolveOutwardNormal(
                displaySurface,
                transform.parent);
            var surfacePoint = ResolveSurfaceFrontPoint(
                displaySurface,
                normal);
            transform.SetPositionAndRotation(
                surfacePoint + normal * DisplayClearanceMeters,
                DisplayRotation(transform.parent, displaySurface, normal));
            RefreshGraphPositions();
        }

        private static Vector3 ResolveSurfaceFrontPoint(
            Transform displaySurface,
            Vector3 normal)
        {
            var surfacePoint = displaySurface.position;
            var filter = displaySurface.GetComponent<MeshFilter>();
            var mesh = filter != null ? filter.sharedMesh : null;
            if (mesh == null)
                return surfacePoint;

            var bounds = mesh.bounds;
            var center = bounds.center;
            var extents = bounds.extents;
            var frontDistance = float.NegativeInfinity;
            for (var x = -1; x <= 1; x += 2)
            for (var y = -1; y <= 1; y += 2)
            for (var z = -1; z <= 1; z += 2)
            {
                var localCorner = center + Vector3.Scale(
                    extents,
                    new Vector3(x, y, z));
                var worldCorner = displaySurface.TransformPoint(localCorner);
                frontDistance = Mathf.Max(
                    frontDistance,
                    Vector3.Dot(worldCorner, normal));
            }

            return surfacePoint + normal *
                (frontDistance - Vector3.Dot(surfacePoint, normal));
        }

        private static Vector3 ResolveOutwardNormal(
            Transform displaySurface,
            Transform labelSocket)
        {
            // Every instrument is mounted with local +Z facing the room.
            // The FBX display mesh may use arbitrary object axes, so the
            // placement socket—not displaySurface.forward—is authoritative.
            return labelSocket != null
                ? labelSocket.forward.normalized
                : displaySurface.forward.normalized;
        }

        public void BeginRefresh()
        {
            for (var index = 0; index < channels.Length; index++)
                channels[index].Touched = false;
        }

        public bool AddSample(string connectionId, float value)
        {
            return AddSample(connectionId, value, Time.unscaledTime);
        }

        public bool AddSample(
            string connectionId,
            float value,
            float sampleTime)
        {
            if (string.IsNullOrEmpty(connectionId))
                return false;

            var channelIndex = FindChannel(connectionId);
            if (channelIndex < 0)
                channelIndex = FindAvailableChannel();
            if (channelIndex < 0)
                return false;

            var channel = channels[channelIndex];
            if (channel.ConnectionId != connectionId)
            {
                channel.ConnectionId = connectionId;
                channel.Samples.Clear();
                channel.NextSampleTime = sampleTime;
                channel.DiagnosticLogged = false;
            }
            channel.Touched = true;

            if (float.IsNaN(value) || float.IsInfinity(value))
            {
                channel.Samples.Clear();
                channel.Label.text = $"{channelIndex + 1} INVALID";
                channel.Label.color = InvalidColor;
                channel.Graph.gameObject.SetActive(false);
                return true;
            }

            var outOfRange = value < 0f || value > 1f;
            var displayValue = Mathf.Clamp01(value);
            if (channel.Samples.Count == 0 ||
                sampleTime >= channel.NextSampleTime)
            {
                channel.Samples.Add(displayValue);
                channel.NextSampleTime =
                    sampleTime + RefreshIntervalSeconds;
            }
            else
            {
                // Keep the current time bucket synchronized with the live
                // instrument output instead of waiting for the next sample.
                channel.Samples.SetNewest(displayValue);
            }
            channel.Label.text = string.Format(
                CultureInfo.InvariantCulture,
                "{0} {1:0.0}%",
                channelIndex + 1,
                displayValue * 100f);
            channel.Label.color =
                outOfRange ? InvalidColor : ChannelColors[channelIndex];
            UpdateLine(channelIndex, outOfRange);
            return true;
        }

        public void EndRefresh()
        {
            ConnectedChannelCount = 0;
            for (var index = 0; index < channels.Length; index++)
            {
                var channel = channels[index];
                if (channel.Touched)
                {
                    ConnectedChannelCount++;
                    channel.Label.gameObject.SetActive(true);
                    continue;
                }

                channel.ConnectionId = null;
                channel.Samples.Clear();
                channel.Label.gameObject.SetActive(false);
                channel.Graph.gameObject.SetActive(false);
            }

            statusLabel.gameObject.SetActive(ConnectedChannelCount == 0);
        }

        public int GetChannelSampleCount(int channelIndex)
        {
            return channelIndex >= 0 && channelIndex < channels.Length
                ? channels[channelIndex].Samples.Count
                : 0;
        }

        private void Build()
        {
            var statusObject = new GameObject("Status");
            statusObject.transform.SetParent(transform, false);
            statusLabel = statusObject.AddComponent<TextMesh>();
            statusLabel.anchor = TextAnchor.MiddleCenter;
            statusLabel.alignment = TextAlignment.Center;
            statusLabel.fontSize = 48;
            statusLabel.characterSize = 0.0024f;
            statusLabel.color = DisconnectedColor;
            statusLabel.text = "NO SIGNAL\n0—100 %";
            RuntimeMaterialUtility.ApplyDepthTestedText(statusLabel);
            statusObject.GetComponent<MeshRenderer>().sortingOrder = 21;

            for (var index = 0; index < channels.Length; index++)
            {
                var labelObject = new GameObject($"Channel{index + 1}Value");
                labelObject.transform.SetParent(transform, false);
                labelObject.transform.localPosition = new Vector3(
                    0.12f - index * 0.08f,
                    ValueReadoutY,
                    0f);
                var label = labelObject.AddComponent<TextMesh>();
                label.anchor = TextAnchor.MiddleCenter;
                label.alignment = TextAlignment.Center;
                label.fontSize = 42;
                label.characterSize = 0.00145f;
                label.color = ChannelColors[index];
                RuntimeMaterialUtility.ApplyDepthTestedText(label);
                labelObject.GetComponent<MeshRenderer>().sortingOrder = 21;
                labelObject.SetActive(false);

                var lineObject = new GameObject($"Channel{index + 1}Trend");
                lineObject.transform.SetParent(transform, false);
                var graph = lineObject.AddComponent<LineRenderer>();
                graph.useWorldSpace = true;
                graph.alignment = LineAlignment.TransformZ;
                graph.startWidth = GraphWidth;
                graph.endWidth = GraphWidth;
                graph.numCapVertices = GraphCapVertices;
                graph.numCornerVertices = GraphCornerVertices;
                graph.loop = false;
                graph.forceRenderingOff = false;
                RuntimeMaterialUtility.ApplySharedUnlit(
                    graph,
                    ChannelColors[index]);
                graph.startColor = ChannelColors[index];
                graph.endColor = ChannelColors[index];
                graph.shadowCastingMode =
                    UnityEngine.Rendering.ShadowCastingMode.Off;
                graph.receiveShadows = false;
                lineObject.transform.localPosition =
                    new Vector3(
                        0f,
                        (index - 1.5f) * 0.002f,
                        -0.0001f - index * 0.00005f);
                graph.sortingOrder = 20;
                lineObject.SetActive(false);

                channels[index] = new Channel(label, graph);
            }
        }

        private static Quaternion DisplayRotation(
            Transform labelSocket,
            Transform displaySurface,
            Vector3 normal)
        {
            var up = Vector3.ProjectOnPlane(labelSocket.up, normal);
            if (up.sqrMagnitude < 0.000001f)
                up = Vector3.ProjectOnPlane(displaySurface.up, normal);
            if (up.sqrMagnitude < 0.000001f)
                up = Vector3.ProjectOnPlane(Vector3.up, normal);
            // TextMesh faces its local -Z side. Keep the display positioned
            // along the outward normal, but point local +Z into the housing.
            return Quaternion.LookRotation(-normal, up.normalized);
        }

        private int FindChannel(string connectionId)
        {
            for (var index = 0; index < channels.Length; index++)
            {
                if (channels[index].ConnectionId == connectionId)
                    return index;
            }
            return -1;
        }

        private int FindAvailableChannel()
        {
            for (var index = 0; index < channels.Length; index++)
            {
                if (string.IsNullOrEmpty(channels[index].ConnectionId))
                    return index;
            }
            for (var index = 0; index < channels.Length; index++)
            {
                if (!channels[index].Touched)
                    return index;
            }
            return -1;
        }

        private void UpdateLine(int channelIndex, bool outOfRange)
        {
            var channel = channels[channelIndex];
            channel.Graph.gameObject.SetActive(channel.Samples.Count >= 2);
            if (channel.Samples.Count < 2)
            {
                SetLineColor(
                    channel.Graph,
                    outOfRange
                    ? InvalidColor
                    : ChannelColors[channelIndex]);
                return;
            }
            BuildLine(channel.Graph, channel.Samples);
            SetLineColor(
                channel.Graph,
                outOfRange
                ? InvalidColor
                : ChannelColors[channelIndex]);
            if (!channel.DiagnosticLogged)
            {
                channel.DiagnosticLogged = true;
                var material = channel.Graph.sharedMaterial;
                Debug.Log(
                    $"[TrendMonitorLine] channel={channelIndex + 1}, " +
                    $"points={channel.Graph.positionCount}, " +
                    $"enabled={channel.Graph.enabled}, " +
                    $"active={channel.Graph.gameObject.activeInHierarchy}, " +
                    $"width={channel.Graph.startWidth:F4}/{channel.Graph.endWidth:F4}, " +
                    $"widthCurveKeys={channel.Graph.widthCurve.length}, " +
                    $"forceRenderingOff={channel.Graph.forceRenderingOff}, " +
                    $"material={(material == null ? "null" : material.name)}, " +
                    $"shader={(material == null ? "null" : material.shader.name)}, " +
                    $"bounds={channel.Graph.bounds}, " +
                    $"first={channel.Graph.GetPosition(0)}, " +
                    $"last={channel.Graph.GetPosition(channel.Graph.positionCount - 1)}, " +
                    $"world={channel.Graph.transform.position}.");
            }
        }

        private static void BuildLine(
            LineRenderer graph,
            SignalSampleBuffer samples)
        {
            var visibleSampleCount = Mathf.Min(
                samples.Count,
                GraphPointCapacity);
            var firstColumn = GraphPointCapacity - visibleSampleCount;
            var firstSample = samples.Count - visibleSampleCount;
            graph.positionCount = visibleSampleCount;
            for (var visibleIndex = 0;
                 visibleIndex < visibleSampleCount;
                 visibleIndex++)
            {
                var column = firstColumn + visibleIndex;
                var value = samples.GetOldestFirst(
                    firstSample + visibleIndex);
                graph.SetPosition(
                    visibleIndex,
                    graph.transform.TransformPoint(new Vector3(
                        Mathf.Lerp(
                            GraphLeft,
                            GraphRight,
                            column / (float)(GraphPointCapacity - 1)),
                        Mathf.Lerp(GraphBottom, GraphTop, value),
                        0f)));
            }
        }

        private static void SetLineColor(
            LineRenderer graph,
            Color color)
        {
            graph.startColor = color;
            graph.endColor = color;
            RuntimeMaterialUtility.SetColor(graph, color);
        }

        private void RefreshGraphPositions()
        {
            for (var index = 0; index < channels.Length; index++)
            {
                var channel = channels[index];
                if (channel != null && channel.Samples.Count >= 2)
                    BuildLine(channel.Graph, channel.Samples);
            }
        }

        private sealed class Channel
        {
            public Channel(TextMesh label, LineRenderer graph)
            {
                Label = label;
                Graph = graph;
            }

            public readonly SignalSampleBuffer Samples =
                new(SampleCapacity);
            public readonly TextMesh Label;
            public readonly LineRenderer Graph;
            public string ConnectionId;
            public bool Touched;
            public float NextSampleTime;
            public bool DiagnosticLogged;
        }
    }
}
