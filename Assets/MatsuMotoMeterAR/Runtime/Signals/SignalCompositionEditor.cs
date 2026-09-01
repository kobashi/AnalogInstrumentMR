using System;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;

namespace MatsuMotoMeterAR.Signals
{
    public static class SignalCompositionEditor
    {
        private const int KindCount = 5;

        public static bool CanConfigureTarget(MockInstrumentKind kind)
        {
            return InstrumentSignalPolicy.CanTarget(kind) &&
                   kind != MockInstrumentKind.WindowPanel;
        }

        public static SignalCompositionKind NormalizeKind(int value)
        {
            return Enum.IsDefined(typeof(SignalCompositionKind), value)
                ? (SignalCompositionKind)value
                : SignalCompositionKind.Average;
        }

        public static SignalCompositionKind CycleKind(
            int current,
            int direction)
        {
            var normalized = (int)NormalizeKind(current);
            var offset = direction < 0 ? -1 : 1;
            return (SignalCompositionKind)
                ((normalized + offset + KindCount) % KindCount);
        }

        public static int CyclePriority(int current, int direction)
        {
            var normalized = Math.Max(
                SignalConnectionRecord.MinimumCompositionPriority,
                Math.Min(
                    SignalConnectionRecord.MaximumCompositionPriority,
                    current));
            var count =
                SignalConnectionRecord.MaximumCompositionPriority -
                SignalConnectionRecord.MinimumCompositionPriority + 1;
            var offset = direction < 0 ? -1 : 1;
            return SignalConnectionRecord.MinimumCompositionPriority +
                   (normalized -
                    SignalConnectionRecord.MinimumCompositionPriority +
                    offset + count) % count;
        }
    }
}
