using System.Globalization;
using MatsuMotoMeterAR.Rendering;
using UnityEngine;

namespace MatsuMotoMeterAR.Signals
{
    public sealed class SignalMonitorView : MonoBehaviour
    {
        public const int ChannelCapacity = 4;
        public const int SampleCapacity = 32;
        public const float RefreshIntervalSeconds = 0.2f;

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

        private const float DisplayClearanceMeters = 0.002f;

        public static SignalMonitorView Create(
            Transform labelSocket,
            Transform displaySurface)
        {
            var monitorObject = new GameObject("TrendMonitorDisplay");
            monitorObject.transform.SetParent(labelSocket, false);
            if (displaySurface != null)
            {
                var normal = displaySurface.forward.normalized;
                var surfacePoint = displaySurface.position;
                var renderer = displaySurface.GetComponent<Renderer>();
                if (renderer != null)
                {
                    var extents = renderer.bounds.extents;
                    var projectedExtent =
                        Mathf.Abs(normal.x) * extents.x +
                        Mathf.Abs(normal.y) * extents.y +
                        Mathf.Abs(normal.z) * extents.z;
                    surfacePoint += normal * projectedExtent;
                }
                monitorObject.transform.SetPositionAndRotation(
                    surfacePoint + normal * DisplayClearanceMeters,
                    displaySurface.rotation *
                    Quaternion.Euler(0f, 180f, 0f));
            }
            else
            {
                monitorObject.transform.localPosition =
                    new Vector3(0f, 0f, 0.091f);
                monitorObject.transform.localRotation =
                    Quaternion.Euler(0f, 180f, 0f);
            }

            var monitor = monitorObject.AddComponent<SignalMonitorView>();
            monitor.Build();
            return monitor;
        }

        public void BeginRefresh()
        {
            for (var index = 0; index < channels.Length; index++)
                channels[index].Touched = false;
        }

        public bool AddSample(string connectionId, float value)
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
            }
            channel.Touched = true;

            if (float.IsNaN(value) || float.IsInfinity(value))
            {
                channel.Samples.Clear();
                channel.Label.text = $"{channelIndex + 1} INVALID";
                channel.Label.color = InvalidColor;
                channel.Line.enabled = false;
                return true;
            }

            var outOfRange = value < 0f || value > 1f;
            var displayValue = Mathf.Clamp01(value);
            channel.Samples.Add(displayValue);
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
                channel.Line.enabled = false;
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

            for (var index = 0; index < channels.Length; index++)
            {
                var labelObject = new GameObject($"Channel{index + 1}Value");
                labelObject.transform.SetParent(transform, false);
                labelObject.transform.localPosition = new Vector3(
                    0.12f - index * 0.08f,
                    0.068f,
                    0f);
                var label = labelObject.AddComponent<TextMesh>();
                label.anchor = TextAnchor.MiddleCenter;
                label.alignment = TextAlignment.Center;
                label.fontSize = 42;
                label.characterSize = 0.00145f;
                label.color = ChannelColors[index];
                labelObject.SetActive(false);

                var lineObject = new GameObject($"Channel{index + 1}Trend");
                lineObject.transform.SetParent(transform, false);
                var line = lineObject.AddComponent<LineRenderer>();
                line.useWorldSpace = false;
                line.loop = false;
                line.widthMultiplier = 0.0024f;
                line.numCapVertices = 0;
                line.numCornerVertices = 0;
                RuntimeMaterialUtility.ApplySharedUnlit(
                    line,
                    ChannelColors[index]);
                line.enabled = false;

                channels[index] = new Channel(label, line);
            }
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
            channel.Line.enabled = channel.Samples.Count >= 2;
            channel.Line.positionCount = channel.Samples.Count;
            if (channel.Samples.Count < 2)
            {
                RuntimeMaterialUtility.SetColor(
                    channel.Line,
                    outOfRange
                        ? InvalidColor
                        : ChannelColors[channelIndex]);
                return;
            }
            for (var index = 0; index < channel.Samples.Count; index++)
            {
                var ratio = index / (float)(channel.Samples.Count - 1);
                channel.Positions[index] = new Vector3(
                    0.16f - ratio * 0.32f,
                    channel.Samples.GetOldestFirst(index) * 0.11f - 0.06f,
                    0f);
            }
            channel.Line.SetPositions(channel.Positions);
            RuntimeMaterialUtility.SetColor(
                channel.Line,
                outOfRange ? InvalidColor : ChannelColors[channelIndex]);
        }

        private sealed class Channel
        {
            public Channel(TextMesh label, LineRenderer line)
            {
                Label = label;
                Line = line;
            }

            public readonly SignalSampleBuffer Samples =
                new(SampleCapacity);
            public readonly Vector3[] Positions =
                new Vector3[SampleCapacity];
            public readonly TextMesh Label;
            public readonly LineRenderer Line;
            public string ConnectionId;
            public bool Touched;
        }
    }
}
