using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;

namespace MatsuMotoMeterAR.Signals
{
    public sealed class SignalGraphEvaluator
    {
        private readonly Dictionary<string, float> sums = new();
        private readonly Dictionary<string, int> counts = new();

        public void Evaluate(
            IReadOnlyList<SignalConnectionRecord> connections,
            IReadOnlyDictionary<string, MockInstrumentInteraction> instruments)
        {
            sums.Clear();
            counts.Clear();
            if (connections == null || instruments == null)
                return;

            foreach (var connection in connections)
            {
                if (connection == null ||
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
                sums.TryGetValue(connection.targetPlacementId, out var sum);
                counts.TryGetValue(connection.targetPlacementId, out var count);
                sums[connection.targetPlacementId] = sum + transformed;
                counts[connection.targetPlacementId] = count + 1;
            }

            foreach (var pair in sums)
            {
                if (!instruments.TryGetValue(pair.Key, out var target))
                    continue;
                target.SetNormalizedValue(pair.Value / counts[pair.Key]);
            }
        }

        public bool TryGetOutput(
            string targetPlacementId,
            out float value,
            out int inputCount)
        {
            if (!string.IsNullOrEmpty(targetPlacementId) &&
                sums.TryGetValue(targetPlacementId, out var sum) &&
                counts.TryGetValue(targetPlacementId, out inputCount) &&
                inputCount > 0)
            {
                value = sum / inputCount;
                return true;
            }

            value = 0f;
            inputCount = 0;
            return false;
        }
    }
}
