using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.PlacementPersistence;

namespace MatsuMotoMeterAR.Audio
{
    public sealed class ModularAudioPatchRuntime
    {
        private int appliedSignature = int.MinValue;

        public int AppliedConnectionCount { get; private set; }

        public bool Refresh(
            IReadOnlyList<AudioPatchConnectionRecord> connections,
            IReadOnlyDictionary<string, ModularAudioModuleRuntime> modules,
            IReadOnlyDictionary<string, ModularAudioGraphPlayer> outputs)
        {
            var signature = ComputeSignature(connections, modules, outputs);
            if (signature == appliedSignature)
                return false;
            appliedSignature = signature;
            AppliedConnectionCount = 0;

            foreach (var pair in outputs)
            {
                if (pair.Value == null ||
                    !modules.TryGetValue(pair.Key, out var outputModule) ||
                    outputModule?.Node is not ModularAudioOutputNode)
                    continue;
                var graph = new ModularAudioGraph();
                var outputIndex = graph.AddNode(outputModule.Node);
                graph.SetOutputNode(outputIndex);
                var nodeIndexes = new Dictionary<string, int>(
                    StringComparer.Ordinal)
                {
                    [pair.Key] = outputIndex
                };
                var appliedConnections = new HashSet<string>(
                    StringComparer.Ordinal);
                AddUpstreamConnections(
                    graph,
                    connections,
                    modules,
                    nodeIndexes,
                    appliedConnections);
                AppliedConnectionCount += appliedConnections.Count;
                graph.Compile();
                pair.Value.Configure(graph);
            }
            return true;
        }

        private static void AddUpstreamConnections(
            ModularAudioGraph graph,
            IReadOnlyList<AudioPatchConnectionRecord> connections,
            IReadOnlyDictionary<string, ModularAudioModuleRuntime> modules,
            IDictionary<string, int> nodeIndexes,
            ISet<string> appliedConnections)
        {
            if (connections == null)
                return;
            var changed = true;
            while (changed)
            {
                changed = false;
                foreach (var connection in connections)
                {
                    if (connection == null ||
                        appliedConnections.Contains(connection.connectionId) ||
                        !nodeIndexes.TryGetValue(
                            connection.targetPlacementId,
                            out var targetIndex) ||
                        !modules.TryGetValue(
                            connection.sourcePlacementId,
                            out var source) ||
                        source?.Node == null ||
                        !modules.TryGetValue(
                            connection.targetPlacementId,
                            out var target) ||
                        target?.Node == null ||
                        !Enum.IsDefined(
                            typeof(ModularAudioPortDomain),
                            connection.portDomain))
                    {
                        continue;
                    }
                    var domain =
                        (ModularAudioPortDomain)connection.portDomain;
                    if (!ModularAudioPatchPolicy.CanConnect(
                            source.ModuleKind,
                            target.ModuleKind,
                            connection.sourcePortId,
                            connection.targetPortId,
                            domain))
                    {
                        continue;
                    }
                    if (!nodeIndexes.TryGetValue(
                            connection.sourcePlacementId,
                            out var sourceIndex))
                    {
                        sourceIndex = graph.AddNode(source.Node);
                        if (sourceIndex < 0)
                            continue;
                        nodeIndexes[connection.sourcePlacementId] = sourceIndex;
                    }
                    if (!graph.Connect(
                            sourceIndex,
                            targetIndex,
                            domain,
                            connection.sourcePortId,
                            connection.targetPortId))
                    {
                        continue;
                    }
                    appliedConnections.Add(connection.connectionId);
                    changed = true;
                }
            }
        }

        public void Invalidate()
        {
            appliedSignature = int.MinValue;
        }

        private static int ComputeSignature(
            IReadOnlyList<AudioPatchConnectionRecord> connections,
            IReadOnlyDictionary<string, ModularAudioModuleRuntime> modules,
            IReadOnlyDictionary<string, ModularAudioGraphPlayer> outputs)
        {
            unchecked
            {
                var hash = 17;
                hash = hash * 31 + (connections?.Count ?? 0);
                if (connections != null)
                {
                    foreach (var connection in connections)
                    {
                        if (connection == null)
                            continue;
                        hash = hash * 31 + StableHash(connection.connectionId);
                        hash = hash * 31 + StableHash(
                            connection.sourcePlacementId);
                        hash = hash * 31 + StableHash(
                            connection.targetPlacementId);
                        hash = hash * 31 + StableHash(
                            connection.sourcePortId);
                        hash = hash * 31 + StableHash(
                            connection.targetPortId);
                        hash = hash * 31 + connection.portDomain;
                    }
                }
                foreach (var pair in modules)
                    hash ^= StableHash(pair.Key) * 397 ^
                            (pair.Value != null
                                ? pair.Value.GetInstanceID()
                                : 0);
                foreach (var pair in outputs)
                    hash ^= StableHash(pair.Key) * 733 ^
                            (pair.Value != null
                                ? pair.Value.GetInstanceID()
                                : 0);
                return hash;
            }
        }

        private static int StableHash(string value)
        {
            unchecked
            {
                var hash = 23;
                if (value == null)
                    return hash;
                for (var index = 0; index < value.Length; index++)
                    hash = hash * 31 + value[index];
                return hash;
            }
        }
    }
}
