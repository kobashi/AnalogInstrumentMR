using System;
using System.Collections.Generic;
using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public sealed class InstrumentGreyboxContract : MonoBehaviour
    {
        private readonly Dictionary<string, Transform> portAnchors =
            new(StringComparer.Ordinal);
        private readonly HashSet<string> missingPortAnchors =
            new(StringComparer.Ordinal);
        private int visualSignature = int.MinValue;

        public MockInstrumentKind Kind { get; private set; }
        public MockInstrumentTheme Theme { get; private set; }
        public Transform MountOrigin { get; private set; }
        public Transform Logic { get; private set; }
        public Transform Interaction { get; private set; }
        public Collider InteractionCollider { get; private set; }
        public MockInstrumentInteraction InstrumentInteraction { get; private set; }
        public Transform VisualSocket { get; private set; }
        public Transform OcclusionProxy { get; private set; }
        public Transform LabelSocket { get; private set; }
        public Transform AudioSocket { get; private set; }
        public Transform VfxSocket { get; private set; }

        public void Configure(
            MockInstrumentKind kind,
            MockInstrumentTheme theme,
            Transform mountOrigin,
            Transform logic,
            Transform interaction,
            Collider interactionCollider,
            MockInstrumentInteraction instrumentInteraction,
            Transform visualSocket,
            Transform occlusionProxy,
            Transform labelSocket,
            Transform audioSocket,
            Transform vfxSocket)
        {
            Kind = kind;
            Theme = theme;
            MountOrigin = mountOrigin;
            Logic = logic;
            Interaction = interaction;
            InteractionCollider = interactionCollider;
            InstrumentInteraction = instrumentInteraction;
            VisualSocket = visualSocket;
            OcclusionProxy = occlusionProxy;
            LabelSocket = labelSocket;
            AudioSocket = audioSocket;
            VfxSocket = vfxSocket;
            InvalidatePortAnchorCache();
        }

        public void SetTheme(MockInstrumentTheme theme)
        {
            Theme = MockInstrumentThemeCatalog.Normalize(theme);
            InvalidatePortAnchorCache();
        }

        public Transform ResolvePortAnchor(string portId)
        {
            if (string.IsNullOrWhiteSpace(portId) || VisualSocket == null)
                return transform;

            RefreshPortAnchorCacheIfVisualChanged();
            var nodeName = PortNodeName(portId);
            if (portAnchors.TryGetValue(nodeName, out var cached) &&
                cached != null)
            {
                return cached;
            }
            if (missingPortAnchors.Contains(nodeName))
                return transform;

            foreach (var candidate in
                     VisualSocket.GetComponentsInChildren<Transform>(true))
            {
                if (!string.Equals(
                        candidate.name,
                        nodeName,
                        StringComparison.Ordinal))
                {
                    continue;
                }

                portAnchors[nodeName] = candidate;
                return candidate;
            }

            missingPortAnchors.Add(nodeName);
            return transform;
        }

        public static string PortNodeName(string portId)
        {
            if (string.IsNullOrWhiteSpace(portId))
                return string.Empty;

            var normalized = portId.Trim()
                .ToLowerInvariant()
                .Replace('.', '_')
                .Replace('-', '_');
            return normalized.StartsWith(
                "port_",
                StringComparison.Ordinal)
                ? normalized
                : $"port_{normalized}";
        }

        private void RefreshPortAnchorCacheIfVisualChanged()
        {
            var nextSignature = 17;
            unchecked
            {
                nextSignature = nextSignature * 31 + VisualSocket.childCount;
                for (var index = 0; index < VisualSocket.childCount; index++)
                {
                    nextSignature = nextSignature * 31 +
                                    VisualSocket.GetChild(index).GetInstanceID();
                }
            }
            if (nextSignature == visualSignature)
                return;

            visualSignature = nextSignature;
            portAnchors.Clear();
            missingPortAnchors.Clear();
        }

        private void InvalidatePortAnchorCache()
        {
            visualSignature = int.MinValue;
            portAnchors.Clear();
            missingPortAnchors.Clear();
        }
    }
}
