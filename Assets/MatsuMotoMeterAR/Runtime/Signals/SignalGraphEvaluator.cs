using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;

namespace MatsuMotoMeterAR.Signals
{
    public sealed class SignalGraphEvaluator
    {
        private readonly Dictionary<string, SignalCompositionAccumulator>
            outputs = new();

        public void Evaluate(
            IReadOnlyList<SignalConnectionRecord> connections,
            IReadOnlyDictionary<string, MockInstrumentInteraction> instruments,
            ISet<string> independentTargets = null,
            IReadOnlyDictionary<string, SignalCompositionKind>
                compositionKinds = null)
        {
            outputs.Clear();
            if (connections == null || instruments == null)
                return;

            foreach (var connection in connections)
            {
                if (connection == null ||
                    (independentTargets != null &&
                     independentTargets.Contains(connection.targetPlacementId)) ||
                    !instruments.TryGetValue(
                        connection.sourcePlacementId,
                        out var source) ||
                    !instruments.ContainsKey(connection.targetPlacementId))
                {
                    continue;
                }

                var transformed = InstrumentSignalPolicy.Transform(
                    source.NormalizedValue,
                    connection);
                if (!outputs.TryGetValue(
                        connection.targetPlacementId,
                        out var accumulator))
                {
                    var kind = SignalCompositionKind.Average;
                    compositionKinds?.TryGetValue(
                        connection.targetPlacementId,
                        out kind);
                    accumulator = new SignalCompositionAccumulator(
                        kind);
                }
                accumulator.Add(
                    transformed,
                    connection.compositionPriority,
                    connection.connectionId);
                outputs[connection.targetPlacementId] = accumulator;
            }

            foreach (var pair in outputs)
            {
                if (!instruments.TryGetValue(pair.Key, out var target))
                    continue;
                if (pair.Value.TryGetValue(out var value))
                    target.SetNormalizedValue(value);
            }
        }

        public bool TryGetOutput(
            string targetPlacementId,
            out float value,
            out int inputCount)
        {
            if (!string.IsNullOrEmpty(targetPlacementId) &&
                outputs.TryGetValue(targetPlacementId, out var accumulator) &&
                accumulator.TryGetValue(out value))
            {
                inputCount = accumulator.ValidCount;
                return true;
            }

            value = 0f;
            inputCount = 0;
            return false;
        }
    }
}
