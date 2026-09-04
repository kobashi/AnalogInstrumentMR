using System;

namespace MatsuMotoMeterAR.Audio
{
    public sealed class ModularAudioGraph
    {
        public const int MaximumNodes = 32;
        public const int MaximumConnections = 64;
        public const int MaximumBlockFrames = 1024;

        private readonly ModularAudioNode[] nodes =
            new ModularAudioNode[MaximumNodes];
        private readonly float[][] nodeBuffers = new float[MaximumNodes][];
        private readonly AudioConnection[] connections =
            new AudioConnection[MaximumConnections];
        private readonly int[] renderOrder = new int[MaximumNodes];
        private readonly int[] indegree = new int[MaximumNodes];
        private readonly bool[] scheduled = new bool[MaximumNodes];
        private readonly bool[] delayedConnections =
            new bool[MaximumConnections];
        private readonly float[] previousSamples = new float[MaximumNodes];
        private readonly float[] controlBlockValues =
            new float[MaximumConnections];
        private readonly float[] inputScratch =
            new float[MaximumBlockFrames];
        private readonly float[] clockScratch =
            new float[MaximumBlockFrames];
        private int nodeCount;
        private int connectionCount;
        private int outputNodeIndex = -1;
        private bool compiled;
        private bool sampleBySample;

        public int NodeCount => nodeCount;
        public int ConnectionCount => connectionCount;
        public bool IsCompiled => compiled;

        public int AddNode(ModularAudioNode node)
        {
            if (node == null)
                throw new ArgumentNullException(nameof(node));
            if (nodeCount >= MaximumNodes)
                return -1;
            var index = nodeCount++;
            nodes[index] = node;
            nodeBuffers[index] = new float[MaximumBlockFrames];
            compiled = false;
            return index;
        }

        public bool ConnectAudio(int sourceNodeIndex, int targetNodeIndex)
        {
            return Connect(
                sourceNodeIndex,
                targetNodeIndex,
                ModularAudioPortDomain.Audio,
                ModularAudioPatchPolicy.AudioOutputPortId,
                ModularAudioPatchPolicy.AudioInputPortId);
        }

        public bool Connect(
            int sourceNodeIndex,
            int targetNodeIndex,
            ModularAudioPortDomain domain,
            string sourcePortId,
            string targetPortId)
        {
            if (!IsNodeIndex(sourceNodeIndex) ||
                !IsNodeIndex(targetNodeIndex) ||
                (sourceNodeIndex == targetNodeIndex &&
                 nodes[targetNodeIndex] is not ModularDelayNode) ||
                (domain != ModularAudioPortDomain.Audio &&
                 domain != ModularAudioPortDomain.Control &&
                 domain != ModularAudioPortDomain.Clock) ||
                connectionCount >= MaximumConnections)
            {
                return false;
            }
            for (var index = 0; index < connectionCount; index++)
            {
                if (connections[index].Source == sourceNodeIndex &&
                    connections[index].Target == targetNodeIndex &&
                    connections[index].Domain == domain &&
                    connections[index].SourcePortId == sourcePortId &&
                    connections[index].TargetPortId == targetPortId)
                    return false;
            }
            connections[connectionCount++] = new AudioConnection(
                sourceNodeIndex,
                targetNodeIndex,
                domain,
                sourcePortId,
                targetPortId);
            compiled = false;
            return true;
        }

        public bool SetOutputNode(int nodeIndex)
        {
            if (!IsNodeIndex(nodeIndex) ||
                nodes[nodeIndex] is not ModularAudioOutputNode)
            {
                return false;
            }
            outputNodeIndex = nodeIndex;
            compiled = false;
            return true;
        }

        public bool Compile()
        {
            if (outputNodeIndex < 0)
                return compiled = false;
            Array.Clear(delayedConnections, 0, connectionCount);
            Array.Clear(previousSamples, 0, nodeCount);
            sampleBySample = false;
            if (TryBuildRenderOrder())
                return compiled = true;

            var hasDelayBoundary = false;
            for (var index = 0; index < connectionCount; index++)
            {
                if (nodes[connections[index].Target] is not ModularDelayNode)
                    continue;
                delayedConnections[index] = true;
                hasDelayBoundary = true;
            }
            if (!hasDelayBoundary || !TryBuildRenderOrder())
                return compiled = false;
            sampleBySample = true;
            return compiled = true;
        }

        private bool TryBuildRenderOrder()
        {
            Array.Clear(indegree, 0, nodeCount);
            Array.Clear(scheduled, 0, nodeCount);
            for (var index = 0; index < connectionCount; index++)
            {
                if (!delayedConnections[index])
                    indegree[connections[index].Target]++;
            }

            var orderCount = 0;
            while (orderCount < nodeCount)
            {
                var next = -1;
                for (var nodeIndex = 0;
                     nodeIndex < nodeCount;
                     nodeIndex++)
                {
                    if (!scheduled[nodeIndex] && indegree[nodeIndex] == 0)
                    {
                        next = nodeIndex;
                        break;
                    }
                }
                if (next < 0)
                    return false;

                scheduled[next] = true;
                renderOrder[orderCount++] = next;
                for (var index = 0; index < connectionCount; index++)
                {
                    if (!delayedConnections[index] &&
                        connections[index].Source == next)
                        indegree[connections[index].Target]--;
                }
            }
            return true;
        }

        public bool Render(float[] output, int frameCount, int sampleRate)
        {
            if (!compiled || output == null || frameCount < 0 ||
                frameCount > MaximumBlockFrames ||
                output.Length < frameCount || sampleRate < 8000)
            {
                return false;
            }

            if (sampleBySample)
                return RenderWithDelayBoundaries(
                    output,
                    frameCount,
                    sampleRate);

            for (var orderIndex = 0;
                 orderIndex < nodeCount;
                 orderIndex++)
            {
                var nodeIndex = renderOrder[orderIndex];
                Array.Clear(inputScratch, 0, frameCount);
                Array.Clear(clockScratch, 0, frameCount);
                Array.Clear(nodeBuffers[nodeIndex], 0, frameCount);
                var controlInput = 0f;
                var hasClockInput = false;
                for (var connectionIndex = 0;
                     connectionIndex < connectionCount;
                     connectionIndex++)
                {
                    var connection = connections[connectionIndex];
                    if (connection.Target != nodeIndex)
                        continue;
                    var source = nodeBuffers[connection.Source];
                    if (connection.Domain == ModularAudioPortDomain.Control)
                    {
                        controlInput += nodes[connection.Source].ReadOutput(
                            connection.SourcePortId,
                            source,
                            0);
                    }
                    else if (connection.Domain == ModularAudioPortDomain.Clock)
                    {
                        hasClockInput = true;
                        for (var frame = 0; frame < frameCount; frame++)
                            clockScratch[frame] +=
                                nodes[connection.Source].ReadOutput(
                                    connection.SourcePortId,
                                    source,
                                    frame);
                    }
                    else
                    {
                        for (var frame = 0; frame < frameCount; frame++)
                            inputScratch[frame] +=
                                nodes[connection.Source].ReadOutput(
                                    connection.SourcePortId,
                                    source,
                                    frame);
                    }
                }
                nodes[nodeIndex].Process(
                    inputScratch,
                    controlInput,
                    clockScratch,
                    hasClockInput,
                    nodeBuffers[nodeIndex],
                    frameCount,
                    sampleRate);
            }

            Array.Copy(
                nodeBuffers[outputNodeIndex],
                output,
                frameCount);
            return true;
        }

        private bool RenderWithDelayBoundaries(
            float[] output,
            int frameCount,
            int sampleRate)
        {
            Array.Clear(controlBlockValues, 0, connectionCount);
            for (var frame = 0; frame < frameCount; frame++)
            {
                for (var orderIndex = 0;
                     orderIndex < nodeCount;
                     orderIndex++)
                {
                    var nodeIndex = renderOrder[orderIndex];
                    inputScratch[0] = 0f;
                    clockScratch[0] = 0f;
                    var controlInput = 0f;
                    var hasClockInput = false;
                    for (var connectionIndex = 0;
                         connectionIndex < connectionCount;
                         connectionIndex++)
                    {
                        var connection = connections[connectionIndex];
                        if (connection.Target != nodeIndex)
                            continue;
                        var sourceValue = delayedConnections[connectionIndex]
                            ? previousSamples[connection.Source]
                            : nodes[connection.Source].ReadOutput(
                                connection.SourcePortId,
                                nodeBuffers[connection.Source],
                                0);
                        if (connection.Domain ==
                            ModularAudioPortDomain.Control)
                        {
                            if (frame == 0)
                                controlBlockValues[connectionIndex] =
                                    sourceValue;
                            controlInput +=
                                controlBlockValues[connectionIndex];
                        }
                        else if (connection.Domain ==
                                 ModularAudioPortDomain.Clock)
                        {
                            hasClockInput = true;
                            clockScratch[0] += sourceValue;
                        }
                        else
                        {
                            inputScratch[0] += sourceValue;
                        }
                    }
                    nodes[nodeIndex].Process(
                        inputScratch,
                        controlInput,
                        clockScratch,
                        hasClockInput,
                        nodeBuffers[nodeIndex],
                        1,
                        sampleRate);
                }
                output[frame] = nodeBuffers[outputNodeIndex][0];
                for (var nodeIndex = 0;
                     nodeIndex < nodeCount;
                     nodeIndex++)
                {
                    previousSamples[nodeIndex] = nodeBuffers[nodeIndex][0];
                }
            }
            return true;
        }

        private bool IsNodeIndex(int index)
        {
            return index >= 0 && index < nodeCount && nodes[index] != null;
        }

        private readonly struct AudioConnection
        {
            public AudioConnection(
                int source,
                int target,
                ModularAudioPortDomain domain,
                string sourcePortId,
                string targetPortId)
            {
                Source = source;
                Target = target;
                Domain = domain;
                SourcePortId = sourcePortId;
                TargetPortId = targetPortId;
            }

            public int Source { get; }
            public int Target { get; }
            public ModularAudioPortDomain Domain { get; }
            public string SourcePortId { get; }
            public string TargetPortId { get; }
        }
    }
}
