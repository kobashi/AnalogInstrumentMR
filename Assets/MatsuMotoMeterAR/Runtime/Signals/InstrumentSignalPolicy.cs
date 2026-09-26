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

    public enum SignalThresholdComparison
    {
        Above = 0,
        Below = 1
    }

    public static class InstrumentSignalPolicy
    {
        public const float RangeMinimum = 0.2f;
        public const float RangeMaximum = 0.8f;
        public const float Threshold = 0.5f;
        public const int MaximumTrendMonitorInputs = 4;
        public const int MaximumWindowPanelInputs =
            WindowPanelGraphicGeometry.SlotCount;

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
                   kind == MockInstrumentKind.StatusIndicator ||
                   kind == MockInstrumentKind.TrendMonitor;
        }

        public static bool CanObserve(MockInstrumentKind kind)
        {
            return CanSource(kind) ||
                   MockInstrumentCatalog.IsReadOnlyMeter(kind);
        }

        public static bool CanConnect(
            MockInstrumentKind source,
            MockInstrumentKind target)
        {
            if (!CanTarget(target))
                return false;
            if (target == MockInstrumentKind.TrendMonitor)
                return CanObserve(source);
            if (target == MockInstrumentKind.WindowPanel)
            {
                return source != MockInstrumentKind.WindowPanel &&
                       CanObserve(source);
            }
            return CanSource(source);
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

        public static float Transform(
            float value,
            SignalConnectionRecord connection)
        {
            if (connection == null)
                return Mathf.Clamp01(value);

            value = Mathf.Clamp01(value);
            var transform = Enum.IsDefined(
                typeof(SignalTransformKind),
                connection.transformKind)
                ? (SignalTransformKind)connection.transformKind
                : SignalTransformKind.Direct;
            switch (transform)
            {
                case SignalTransformKind.Invert:
                    return 1f - value;
                case SignalTransformKind.Range:
                    var input = Mathf.InverseLerp(
                        connection.inputMinimum,
                        connection.inputMaximum,
                        value);
                    return Mathf.Lerp(
                        connection.outputMinimum,
                        connection.outputMaximum,
                        input);
                case SignalTransformKind.Threshold:
                    var comparison = Enum.IsDefined(
                        typeof(SignalThresholdComparison),
                        connection.thresholdComparison)
                        ? (SignalThresholdComparison)connection.thresholdComparison
                        : SignalThresholdComparison.Above;
                    return comparison == SignalThresholdComparison.Below
                        ? value <= connection.thresholdValue ? 1f : 0f
                        : value >= connection.thresholdValue ? 1f : 0f;
                default:
                    return value;
            }
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

    public static class MixedConnectionSelectionPolicy
    {
        public static bool TrySelectNext(
            IReadOnlyList<SignalConnectionRecord> signalConnections,
            IReadOnlyList<AudioPatchConnectionRecord> audioPatches,
            string placementId,
            string currentSignalConnectionId,
            string currentAudioPatchId,
            out SignalConnectionRecord selectedSignal,
            out AudioPatchConnectionRecord selectedAudioPatch)
        {
            selectedSignal = null;
            selectedAudioPatch = null;
            if (string.IsNullOrEmpty(placementId))
                return false;

            if (!string.IsNullOrEmpty(currentSignalConnectionId))
            {
                selectedSignal = SelectSignalAfterCurrent(
                    signalConnections,
                    placementId,
                    currentSignalConnectionId);
                if (selectedSignal != null)
                    return true;
                selectedAudioPatch = SelectFirstAudioPatch(
                    audioPatches,
                    placementId);
                if (selectedAudioPatch != null)
                    return true;
                selectedSignal = SignalConnectionSelectionPolicy.SelectNext(
                    signalConnections,
                    placementId,
                    null);
                return selectedSignal != null;
            }

            if (!string.IsNullOrEmpty(currentAudioPatchId))
            {
                selectedAudioPatch = SelectAudioPatchAfterCurrent(
                    audioPatches,
                    placementId,
                    currentAudioPatchId);
                if (selectedAudioPatch != null)
                    return true;
                selectedSignal = SignalConnectionSelectionPolicy.SelectNext(
                    signalConnections,
                    placementId,
                    null);
                if (selectedSignal != null)
                    return true;
                selectedAudioPatch = SelectFirstAudioPatch(
                    audioPatches,
                    placementId);
                return selectedAudioPatch != null;
            }

            selectedSignal = SignalConnectionSelectionPolicy.SelectNext(
                signalConnections,
                placementId,
                null);
            if (selectedSignal != null)
                return true;
            selectedAudioPatch = SelectFirstAudioPatch(
                audioPatches,
                placementId);
            return selectedAudioPatch != null;
        }

        private static SignalConnectionRecord SelectSignalAfterCurrent(
            IReadOnlyList<SignalConnectionRecord> connections,
            string placementId,
            string currentConnectionId)
        {
            if (connections == null)
                return null;
            var foundCurrent = false;
            foreach (var connection in connections)
            {
                if (!SignalConnectionSelectionPolicy.TouchesPlacement(
                        connection,
                        placementId))
                {
                    continue;
                }
                if (foundCurrent)
                    return connection;
                if (string.Equals(
                        connection.connectionId,
                        currentConnectionId,
                        StringComparison.Ordinal))
                {
                    foundCurrent = true;
                }
            }
            return null;
        }

        private static AudioPatchConnectionRecord SelectAudioPatchAfterCurrent(
            IReadOnlyList<AudioPatchConnectionRecord> connections,
            string placementId,
            string currentConnectionId)
        {
            if (connections == null)
                return null;
            var foundCurrent = false;
            foreach (var connection in connections)
            {
                if (!TouchesPlacement(connection, placementId))
                    continue;
                if (foundCurrent)
                    return connection;
                if (string.Equals(
                        connection.connectionId,
                        currentConnectionId,
                        StringComparison.Ordinal))
                {
                    foundCurrent = true;
                }
            }
            return null;
        }

        private static AudioPatchConnectionRecord SelectFirstAudioPatch(
            IReadOnlyList<AudioPatchConnectionRecord> connections,
            string placementId)
        {
            if (connections == null)
                return null;
            foreach (var connection in connections)
                if (TouchesPlacement(connection, placementId))
                    return connection;
            return null;
        }

        private static bool TouchesPlacement(
            AudioPatchConnectionRecord connection,
            string placementId)
        {
            return connection != null &&
                   (connection.sourcePlacementId == placementId ||
                    connection.targetPlacementId == placementId);
        }
    }
}
