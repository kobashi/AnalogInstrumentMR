using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;

namespace MatsuMotoMeterAR.Audio
{
    public static class ModularAudioPatchPolicy
    {
        public const string AudioOutputPortId = "audio.out";
        public const string AudioInputPortId = "audio.in";
        public const string ControlOutputPortId = "control.out";
        public const string PitchInputPortId = "pitch.in";
        public const string FrequencyModulationInputPortId = "fm.in";
        public const string ClockOutputPortId = "clock.out";
        public const string ClockInputPortId = "clock.in";
        public const string TimeInputPortId = "time.in";
        public const string ValueOutputPortId = "value.out";
        public const string SlopeOutputPortId = "slope.out";
        public const string SpreadOutputPortId = "spread.out";
        public const string EnergyOutputPortId = "energy.out";
        public const string BalanceOutputPortId = "balance.out";
        public const string PhaseOutputPortId = "phase.out";
        public const string DetailOutputPortId = "detail.out";

        private static readonly string[] MeterOutputs =
        {
            ValueOutputPortId,
            AudioOutputPortId
        };

        private static readonly string[] TrendOutputs =
        {
            ValueOutputPortId,
            SlopeOutputPortId,
            SpreadOutputPortId,
            AudioOutputPortId
        };

        private static readonly string[] PanelOutputs =
        {
            EnergyOutputPortId,
            BalanceOutputPortId,
            PhaseOutputPortId,
            DetailOutputPortId,
            AudioOutputPortId
        };

        public static bool CanSource(MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.AudioOscillator ||
                   kind == MockInstrumentKind.AudioNoise ||
                   kind == MockInstrumentKind.AudioLfo ||
                   kind == MockInstrumentKind.AudioSequencer ||
                   kind == MockInstrumentKind.AudioDelay ||
                   IsObservableInstrument(kind);
        }

        public static bool CanTarget(MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.AudioOutput ||
                   kind == MockInstrumentKind.AudioOscillator ||
                   kind == MockInstrumentKind.AudioSequencer ||
                   kind == MockInstrumentKind.AudioDelay;
        }

        public static bool PrefersTargetWhenUnconnected(
            MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.AudioOutput;
        }

        public static bool TryGetDefaultRoute(
            MockInstrumentKind source,
            MockInstrumentKind target,
            out string sourcePortId,
            out string targetPortId,
            out ModularAudioPortDomain domain)
        {
            return TryGetRoute(
                source,
                target,
                ModularAudioPortDomain.Control,
                out sourcePortId,
                out targetPortId,
                out domain);
        }

        public static bool TryGetRoute(
            MockInstrumentKind source,
            MockInstrumentKind target,
            ModularAudioPortDomain preferredLfoDomain,
            out string sourcePortId,
            out string targetPortId,
            out ModularAudioPortDomain domain)
        {
            if (IsObservableInstrument(source))
            {
                var sourcePort = target == MockInstrumentKind.AudioOutput ||
                                 target == MockInstrumentKind.AudioDelay
                    ? AudioOutputPortId
                    : GetSelectableOutputPortId(source, 0);
                sourcePortId = sourcePort;
                return TryGetRouteFromPort(
                    source,
                    target,
                    sourcePort,
                    out targetPortId,
                    out domain);
            }
            if (source == MockInstrumentKind.AudioLfo &&
                target == MockInstrumentKind.AudioDelay)
            {
                var audioRate = preferredLfoDomain ==
                                ModularAudioPortDomain.Audio;
                sourcePortId = audioRate
                    ? AudioOutputPortId
                    : ControlOutputPortId;
                targetPortId = audioRate
                    ? AudioInputPortId
                    : TimeInputPortId;
                domain = audioRate
                    ? ModularAudioPortDomain.Audio
                    : ModularAudioPortDomain.Control;
                return true;
            }
            if (source == MockInstrumentKind.AudioLfo &&
                target == MockInstrumentKind.AudioSequencer)
            {
                sourcePortId = ClockOutputPortId;
                targetPortId = ClockInputPortId;
                domain = ModularAudioPortDomain.Clock;
                return true;
            }
            if (source == MockInstrumentKind.AudioSequencer &&
                target == MockInstrumentKind.AudioOscillator)
            {
                sourcePortId = ControlOutputPortId;
                targetPortId = PitchInputPortId;
                domain = ModularAudioPortDomain.Control;
                return true;
            }
            if (source == MockInstrumentKind.AudioLfo &&
                target == MockInstrumentKind.AudioOscillator)
            {
                var audioRate = preferredLfoDomain ==
                                ModularAudioPortDomain.Audio;
                sourcePortId = audioRate
                    ? AudioOutputPortId
                    : ControlOutputPortId;
                targetPortId = audioRate
                    ? FrequencyModulationInputPortId
                    : PitchInputPortId;
                domain = audioRate
                    ? ModularAudioPortDomain.Audio
                    : ModularAudioPortDomain.Control;
                return true;
            }
            sourcePortId = AudioOutputPortId;
            targetPortId = AudioInputPortId;
            domain = ModularAudioPortDomain.Audio;
            return CanConnect(
                source,
                target,
                sourcePortId,
                targetPortId,
                domain);
        }

        public static int GetSelectableOutputCount(MockInstrumentKind kind)
        {
            return GetSelectableOutputs(kind)?.Length ?? 0;
        }

        public static string GetSelectableOutputPortId(
            MockInstrumentKind kind,
            int index)
        {
            var outputs = GetSelectableOutputs(kind);
            if (outputs == null || outputs.Length == 0)
                return null;
            index = index < 0
                ? 0
                : index >= outputs.Length
                    ? outputs.Length - 1
                    : index;
            return outputs[index];
        }

        public static int CycleSelectableOutput(
            MockInstrumentKind kind,
            int currentIndex,
            int direction)
        {
            var count = GetSelectableOutputCount(kind);
            if (count <= 1)
                return 0;
            currentIndex = currentIndex < 0
                ? 0
                : currentIndex >= count
                    ? count - 1
                    : currentIndex;
            return (currentIndex + (direction < 0 ? count - 1 : 1)) % count;
        }

        public static bool TryGetOutputDomain(
            MockInstrumentKind kind,
            string portId,
            out ModularAudioPortDomain domain)
        {
            if (TryGetModuleKind(kind, out var moduleKind) &&
                ModularAudioPortCatalog.TryGetPort(
                    moduleKind,
                    portId,
                    out var port) &&
                port.Direction == ModularAudioPortDirection.Output)
            {
                domain = port.Domain;
                return true;
            }
            domain = default;
            return false;
        }

        public static bool TryGetRouteFromPort(
            MockInstrumentKind source,
            MockInstrumentKind target,
            string sourcePortId,
            out string targetPortId,
            out ModularAudioPortDomain domain)
        {
            targetPortId = null;
            if (!TryGetOutputDomain(source, sourcePortId, out domain))
                return false;

            if (domain == ModularAudioPortDomain.Audio &&
                target == MockInstrumentKind.AudioOutput)
            {
                targetPortId = AudioInputPortId;
            }
            else if (target == MockInstrumentKind.AudioDelay)
            {
                targetPortId = domain switch
                {
                    ModularAudioPortDomain.Audio => AudioInputPortId,
                    ModularAudioPortDomain.Control => TimeInputPortId,
                    _ => null
                };
            }
            else if (target == MockInstrumentKind.AudioOscillator)
            {
                targetPortId = domain switch
                {
                    ModularAudioPortDomain.Audio =>
                        FrequencyModulationInputPortId,
                    ModularAudioPortDomain.Control => PitchInputPortId,
                    _ => null
                };
            }
            else if (target == MockInstrumentKind.AudioSequencer &&
                     domain == ModularAudioPortDomain.Clock)
            {
                targetPortId = ClockInputPortId;
            }

            return targetPortId != null && CanConnect(
                source,
                target,
                sourcePortId,
                targetPortId,
                domain);
        }

        public static bool CanConnect(
            MockInstrumentKind source,
            MockInstrumentKind target,
            string sourcePortId,
            string targetPortId,
            ModularAudioPortDomain domain)
        {
            if (!TryGetModuleKind(source, out var sourceModule) ||
                !TryGetModuleKind(target, out var targetModule))
                return false;
            return CanConnect(
                sourceModule,
                targetModule,
                sourcePortId,
                targetPortId,
                domain);
        }

        public static bool CanConnect(
            ModularAudioModuleKind source,
            ModularAudioModuleKind target,
            string sourcePortId,
            string targetPortId,
            ModularAudioPortDomain domain)
        {
            if (!ModularAudioPortCatalog.TryGetPort(
                    source,
                    sourcePortId,
                    out var sourcePort) ||
                !ModularAudioPortCatalog.TryGetPort(
                    target,
                    targetPortId,
                    out var targetPort) ||
                sourcePort.Domain != domain ||
                targetPort.Domain != domain)
            {
                return false;
            }
            return ModularAudioPort.CheckConnection(sourcePort, targetPort) ==
                   ModularAudioPortCompatibility.Compatible;
        }

        private static bool TryGetModuleKind(
            MockInstrumentKind kind,
            out ModularAudioModuleKind moduleKind)
        {
            switch (kind)
            {
                case MockInstrumentKind.AudioOscillator:
                    moduleKind = ModularAudioModuleKind.Oscillator;
                    return true;
                case MockInstrumentKind.AudioNoise:
                    moduleKind = ModularAudioModuleKind.Noise;
                    return true;
                case MockInstrumentKind.AudioOutput:
                    moduleKind = ModularAudioModuleKind.AudioOutput;
                    return true;
                case MockInstrumentKind.AudioLfo:
                    moduleKind = ModularAudioModuleKind.Lfo;
                    return true;
                case MockInstrumentKind.AudioSequencer:
                    moduleKind = ModularAudioModuleKind.Sequencer;
                    return true;
                case MockInstrumentKind.AudioDelay:
                    moduleKind = ModularAudioModuleKind.Delay;
                    return true;
                case MockInstrumentKind.RoundMeter:
                case MockInstrumentKind.RoundMeterMedium:
                case MockInstrumentKind.RoundMeterLarge:
                case MockInstrumentKind.WindowMeter:
                    moduleKind = ModularAudioModuleKind.MeterSource;
                    return true;
                case MockInstrumentKind.TrendMonitor:
                    moduleKind = ModularAudioModuleKind.TrendSource;
                    return true;
                case MockInstrumentKind.WindowPanel:
                    moduleKind = ModularAudioModuleKind.PanelSource;
                    return true;
                default:
                    moduleKind = default;
                    return false;
            }
        }

        private static bool IsObservableInstrument(MockInstrumentKind kind)
        {
            return GetSelectableOutputs(kind) != null;
        }

        private static string[] GetSelectableOutputs(MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.RoundMeter or
                MockInstrumentKind.RoundMeterMedium or
                MockInstrumentKind.RoundMeterLarge or
                MockInstrumentKind.WindowMeter => MeterOutputs,
                MockInstrumentKind.TrendMonitor => TrendOutputs,
                MockInstrumentKind.WindowPanel => PanelOutputs,
                _ => null
            };
        }

        public static bool TouchesPlacement(
            AudioPatchConnectionRecord connection,
            string placementId)
        {
            return connection != null &&
                   !string.IsNullOrEmpty(placementId) &&
                   (connection.sourcePlacementId == placementId ||
                    connection.targetPlacementId == placementId);
        }

        public static int CountForPlacement(
            IReadOnlyList<AudioPatchConnectionRecord> connections,
            string placementId)
        {
            if (connections == null || string.IsNullOrEmpty(placementId))
                return 0;
            var count = 0;
            for (var index = 0; index < connections.Count; index++)
                if (TouchesPlacement(connections[index], placementId))
                    count++;
            return count;
        }

        public static AudioPatchConnectionRecord SelectNext(
            IReadOnlyList<AudioPatchConnectionRecord> connections,
            string placementId,
            string currentConnectionId)
        {
            if (connections == null || string.IsNullOrEmpty(placementId))
                return null;

            AudioPatchConnectionRecord first = null;
            var returnNext = string.IsNullOrEmpty(currentConnectionId);
            for (var index = 0; index < connections.Count; index++)
            {
                var connection = connections[index];
                if (!TouchesPlacement(connection, placementId))
                    continue;
                first ??= connection;
                if (returnNext)
                    return connection;
                if (string.Equals(
                        connection.connectionId,
                        currentConnectionId,
                        StringComparison.Ordinal))
                    returnNext = true;
            }
            return first;
        }
    }
}
