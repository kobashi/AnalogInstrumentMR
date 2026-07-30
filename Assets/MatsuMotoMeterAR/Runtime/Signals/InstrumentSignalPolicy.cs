using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;
using UnityEngine;

namespace MatsuMotoMeterAR.Signals
{
    public enum SignalTransformKind
    {
        Direct = 0,
        Invert = 1,
        Range = 2,
        Threshold = 3
    }

    public static class InstrumentSignalPolicy
    {
        public const float RangeMinimum = 0.2f;
        public const float RangeMaximum = 0.8f;
        public const float Threshold = 0.5f;

        public static bool CanSource(MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.Lever ||
                   kind == MockInstrumentKind.ToggleSwitch ||
                   kind == MockInstrumentKind.RotaryKnob ||
                   kind == MockInstrumentKind.PushButton ||
                   kind == MockInstrumentKind.ThrottleLever ||
                   kind == MockInstrumentKind.PowerSlider;
        }

        public static bool CanTarget(MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.RoundMeter ||
                   kind == MockInstrumentKind.RoundMeterMedium ||
                   kind == MockInstrumentKind.RoundMeterLarge ||
                   kind == MockInstrumentKind.IndicatorLamp ||
                   kind == MockInstrumentKind.WindowMeter ||
                   kind == MockInstrumentKind.WindowPanel ||
                   kind == MockInstrumentKind.StatusIndicator;
        }

        public static float Transform(
            float value,
            SignalTransformKind transform)
        {
            value = Mathf.Clamp01(value);
            return transform switch
            {
                SignalTransformKind.Invert => 1f - value,
                SignalTransformKind.Range => Mathf.Lerp(
                    RangeMinimum,
                    RangeMaximum,
                    value),
                SignalTransformKind.Threshold =>
                    value >= Threshold ? 1f : 0f,
                _ => value
            };
        }

        public static SignalTransformKind Cycle(
            SignalTransformKind current,
            int direction)
        {
            const int count = 4;
            var offset = direction < 0 ? -1 : 1;
            return (SignalTransformKind)
                (((int)current + offset + count) % count);
        }
    }

    public static class SignalConnectionSelectionPolicy
    {
        public static bool TouchesPlacement(
            SignalConnectionRecord connection,
            string placementId)
        {
            return connection != null &&
                   !string.IsNullOrEmpty(placementId) &&
                   (connection.sourcePlacementId == placementId ||
                    connection.targetPlacementId == placementId);
        }

        public static int CountForPlacement(
            IReadOnlyList<SignalConnectionRecord> connections,
            string placementId)
        {
            if (connections == null ||
                string.IsNullOrEmpty(placementId))
            {
                return 0;
            }

            var count = 0;
            foreach (var connection in connections)
            {
                if (TouchesPlacement(connection, placementId))
                    count++;
            }
            return count;
        }

        public static SignalConnectionRecord SelectNext(
            IReadOnlyList<SignalConnectionRecord> connections,
            string placementId,
            string currentConnectionId)
        {
            if (connections == null ||
                string.IsNullOrEmpty(placementId))
            {
                return null;
            }

            SignalConnectionRecord first = null;
            var returnNext =
                string.IsNullOrEmpty(currentConnectionId);
            foreach (var connection in connections)
            {
                if (!TouchesPlacement(connection, placementId))
                    continue;

                first ??= connection;
                if (returnNext)
                    return connection;
                if (string.Equals(
                        connection.connectionId,
                        currentConnectionId,
                        StringComparison.Ordinal))
                {
                    returnNext = true;
                }
            }
            return first;
        }
    }
}
