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
            if (connections == null || instruments == null)
                return;

            sums.Clear();
            counts.Clear();
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
                    (SignalTransformKind)connection.transformKind);
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
    }
}
