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
        public const string RateInputPortId = "rate.in";
        public const string TimeInputPortId = "time.in";
        public const string LevelInputPortId = "level.in";
        public const string CutoffInputPortId = "cutoff.in";
        public const string GateInputPortId = "gate.in";
        public const string TriggerInputPortId = "trigger.in";
        public const string ResetInputPortId = "reset.in";
        public const string GateOutputPortId = "gate.out";
        public const string TriggerOutputPortId = "trigger.out";
        public const string ValueOutputPortId = "value.out";
        public const string SlopeOutputPortId = "slope.out";
        public const string SpreadOutputPortId = "spread.out";
        public const string EnergyOutputPortId = "energy.out";
        public const string BalanceOutputPortId = "balance.out";
        public const string PhaseOutputPortId = "phase.out";
        public const string DetailOutputPortId = "detail.out";
        public const float ObservableTriggerThreshold = 0.5f;

        private static readonly string[] MeterOutputs =
        {
            ValueOutputPortId,
            TriggerOutputPortId,
            AudioOutputPortId
        };

        private static readonly string[] TrendOutputs =
        {
            ValueOutputPortId,
            SlopeOutputPortId,
            SpreadOutputPortId,
            TriggerOutputPortId,
            AudioOutputPortId
        };

        private static readonly string[] PanelOutputs =
        {
            EnergyOutputPortId,
            BalanceOutputPortId,
            PhaseOutputPortId,
            DetailOutputPortId,
            TriggerOutputPortId,
            AudioOutputPortId
        };

        private static readonly string[] LfoOutputs =
        {
            ControlOutputPortId,
            ClockOutputPortId,
            GateOutputPortId,
            TriggerOutputPortId,
            AudioOutputPortId
        };

        private static readonly string[] SequencerOutputs =
        {
            ControlOutputPortId,
            GateOutputPortId,
            TriggerOutputPortId
        };

        private static readonly string[] ControlSourceOutputs =
        {
            ControlOutputPortId,
            GateOutputPortId,
            TriggerOutputPortId
        };

        public static bool CanSource(MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.AudioOscillator ||
                   kind == MockInstrumentKind.AudioNoise ||
                   kind == MockInstrumentKind.AudioLfo ||
                   kind == MockInstrumentKind.AudioSequencer ||
                   kind == MockInstrumentKind.AudioDelay ||
                   kind == MockInstrumentKind.AudioVca ||
                   kind == MockInstrumentKind.AudioMixer ||
                   kind == MockInstrumentKind.AudioFilter ||
                   kind == MockInstrumentKind.AudioEnvelope ||
                   IsInteractiveControlSource(kind) ||
                   IsObservableInstrument(kind);
        }

        public static bool CanTarget(MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.AudioOutput ||
                   kind == MockInstrumentKind.AudioOscillator ||
                   kind == MockInstrumentKind.AudioNoise ||
                   kind == MockInstrumentKind.AudioLfo ||
                   kind == MockInstrumentKind.AudioSequencer ||
                   kind == MockInstrumentKind.AudioDelay ||
                   kind == MockInstrumentKind.AudioVca ||
                   kind == MockInstrumentKind.AudioMixer ||
                   kind == MockInstrumentKind.AudioFilter ||
                   kind == MockInstrumentKind.AudioEnvelope;
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
                var sourcePort = IsInteractiveControlSource(source)
                    ? PreferredControlSourcePort(source, target)
                    : target == MockInstrumentKind.AudioSequencer
                        ? TriggerOutputPortId
                        : target == MockInstrumentKind.AudioOutput ||
                          target == MockInstrumentKind.AudioDelay ||
                          target == MockInstrumentKind.AudioMixer
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
            if (source == MockInstrumentKind.AudioEnvelope)
            {
                sourcePortId = ControlOutputPortId;
                return TryGetRouteFromPort(
                    source,
                    target,
                    sourcePortId,
                    out targetPortId,
                    out domain);
            }
            if (source == MockInstrumentKind.AudioLfo &&
                (target == MockInstrumentKind.AudioEnvelope ||
                 target == MockInstrumentKind.AudioNoise))
            {
                sourcePortId = GateOutputPortId;
                return TryGetRouteFromPort(
                    source,
                    target,
                    sourcePortId,
                    out targetPortId,
                    out domain);
            }
            if (source == MockInstrumentKind.AudioSequencer &&
                (target == MockInstrumentKind.AudioEnvelope ||
                 target == MockInstrumentKind.AudioNoise))
            {
                sourcePortId = GateOutputPortId;
                return TryGetRouteFromPort(
                    source,
                    target,
                    sourcePortId,
                    out targetPortId,
                    out domain);
            }
            if (source == MockInstrumentKind.AudioSequencer &&
                target == MockInstrumentKind.AudioLfo)
            {
                sourcePortId = TriggerOutputPortId;
                return TryGetRouteFromPort(
                    source,
                    target,
                    sourcePortId,
                    out targetPortId,
                    out domain);
            }
            if (source == MockInstrumentKind.AudioSequencer &&
                target == MockInstrumentKind.AudioSequencer)
            {
                sourcePortId = TriggerOutputPortId;
                return TryGetRouteFromPort(
                    source,
                    target,
                    sourcePortId,
                    out targetPortId,
                    out domain);
            }
            if (source == MockInstrumentKind.AudioLfo &&
                target == MockInstrumentKind.AudioVca)
            {
                sourcePortId = ControlOutputPortId;
                targetPortId = LevelInputPortId;
                domain = ModularAudioPortDomain.Control;
                return true;
            }
            if (source == MockInstrumentKind.AudioLfo &&
                target == MockInstrumentKind.AudioFilter)
            {
                sourcePortId = ControlOutputPortId;
                targetPortId = CutoffInputPortId;
                domain = ModularAudioPortDomain.Control;
                return true;
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

        public static int GetDefaultPatchOutputIndex(
            MockInstrumentKind kind)
        {
            var outputs = GetSelectableOutputs(kind);
            if (outputs == null || outputs.Length == 0)
                return 0;
            if (!SupportsSignalRole(kind))
                return 0;
            for (var index = 0; index < outputs.Length; index++)
            {
                if (TryGetOutputDomain(
                        kind,
                        outputs[index],
                        out var domain) &&
                    domain == ModularAudioPortDomain.Audio)
                {
                    return index;
                }
            }
            return 0;
        }

        public static int GetDefaultPatchOutputIndex(
            MockInstrumentKind kind,
            MockInstrumentKind target)
        {
            if (target == MockInstrumentKind.AudioSequencer)
            {
                var outputs = GetSelectableOutputs(kind);
                if (outputs != null)
                {
                    for (var index = 0; index < outputs.Length; index++)
                    {
                        if (outputs[index] == TriggerOutputPortId)
                            return index;
                    }
                }
            }
            return GetDefaultPatchOutputIndex(kind);
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
            else if (target == MockInstrumentKind.AudioVca)
            {
                targetPortId = domain switch
                {
                    ModularAudioPortDomain.Audio => AudioInputPortId,
                    ModularAudioPortDomain.Control => LevelInputPortId,
                    _ => null
                };
            }
            else if (target == MockInstrumentKind.AudioMixer &&
                     domain == ModularAudioPortDomain.Audio)
            {
                targetPortId = AudioInputPortId;
            }
            else if (target == MockInstrumentKind.AudioFilter)
            {
                targetPortId = domain switch
                {
                    ModularAudioPortDomain.Audio => AudioInputPortId,
                    ModularAudioPortDomain.Control => CutoffInputPortId,
                    _ => null
                };
            }
            else if (target == MockInstrumentKind.AudioEnvelope)
            {
                targetPortId = domain switch
                {
                    ModularAudioPortDomain.Gate => GateInputPortId,
                    ModularAudioPortDomain.Trigger => TriggerInputPortId,
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
                    ModularAudioPortDomain.Gate => GateInputPortId,
                    _ => null
                };
            }
            else if (target == MockInstrumentKind.AudioNoise &&
                     domain == ModularAudioPortDomain.Gate)
            {
                targetPortId = GateInputPortId;
            }
            else if (target == MockInstrumentKind.AudioLfo &&
                     (domain == ModularAudioPortDomain.Control ||
                      domain == ModularAudioPortDomain.Trigger))
            {
                targetPortId = domain == ModularAudioPortDomain.Trigger
                    ? ResetInputPortId
                    : RateInputPortId;
            }
            else if (target == MockInstrumentKind.AudioSequencer &&
                     (domain == ModularAudioPortDomain.Clock ||
                      domain == ModularAudioPortDomain.Trigger))
            {
                targetPortId = domain == ModularAudioPortDomain.Trigger
                    ? TriggerInputPortId
                    : ClockInputPortId;
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
                case MockInstrumentKind.AudioVca:
                    moduleKind = ModularAudioModuleKind.Vca;
                    return true;
                case MockInstrumentKind.AudioMixer:
                    moduleKind = ModularAudioModuleKind.Mixer;
                    return true;
                case MockInstrumentKind.AudioFilter:
                    moduleKind = ModularAudioModuleKind.Filter;
                    return true;
                case MockInstrumentKind.AudioEnvelope:
                    moduleKind = ModularAudioModuleKind.Envelope;
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
                case MockInstrumentKind.Lever:
                case MockInstrumentKind.ToggleSwitch:
                case MockInstrumentKind.RotaryKnob:
                case MockInstrumentKind.PushButton:
                case MockInstrumentKind.ThrottleLever:
                case MockInstrumentKind.PowerSlider:
                    moduleKind = ModularAudioModuleKind.ControlSource;
                    return true;
                default:
                    moduleKind = default;
                    return false;
            }
        }

        private static bool IsObservableInstrument(MockInstrumentKind kind)
        {
            return SupportsSignalRole(kind);
        }

        public static bool SupportsSignalRole(MockInstrumentKind kind)
        {
            return IsInteractiveControlSource(kind) ||
                   kind == MockInstrumentKind.RoundMeter ||
                   kind == MockInstrumentKind.RoundMeterMedium ||
                   kind == MockInstrumentKind.RoundMeterLarge ||
                   kind == MockInstrumentKind.WindowMeter ||
                   kind == MockInstrumentKind.TrendMonitor ||
                   kind == MockInstrumentKind.WindowPanel;
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
                MockInstrumentKind.Lever or
                MockInstrumentKind.ToggleSwitch or
                MockInstrumentKind.RotaryKnob or
                MockInstrumentKind.PushButton or
                MockInstrumentKind.ThrottleLever or
                MockInstrumentKind.PowerSlider => ControlSourceOutputs,
                MockInstrumentKind.AudioLfo => LfoOutputs,
                MockInstrumentKind.AudioSequencer => SequencerOutputs,
                _ => null
            };
        }

        private static bool IsInteractiveControlSource(
            MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.Lever ||
                   kind == MockInstrumentKind.ToggleSwitch ||
                   kind == MockInstrumentKind.RotaryKnob ||
                   kind == MockInstrumentKind.PushButton ||
                   kind == MockInstrumentKind.ThrottleLever ||
                   kind == MockInstrumentKind.PowerSlider;
        }

        private static string PreferredControlSourcePort(
            MockInstrumentKind source,
            MockInstrumentKind target)
        {
            if (target == MockInstrumentKind.AudioSequencer)
                return TriggerOutputPortId;
            if (target == MockInstrumentKind.AudioEnvelope ||
                target == MockInstrumentKind.AudioNoise)
            {
                return GateOutputPortId;
            }
            if (target == MockInstrumentKind.AudioLfo &&
                (source == MockInstrumentKind.PushButton ||
                 source == MockInstrumentKind.ToggleSwitch))
            {
                return TriggerOutputPortId;
            }
            return ControlOutputPortId;
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
