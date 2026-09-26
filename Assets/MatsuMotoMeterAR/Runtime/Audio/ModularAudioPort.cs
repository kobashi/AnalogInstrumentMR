using System.Collections.Generic;

namespace MatsuMotoMeterAR.Audio
{
    public enum ModularAudioModuleKind
    {
        Oscillator = 0,
        Noise = 1,
        AudioOutput = 2,
        Lfo = 3,
        Sequencer = 4,
        Delay = 5,
        MeterSource = 6,
        TrendSource = 7,
        PanelSource = 8,
        Vca = 9,
        Mixer = 10,
        Filter = 11,
        Envelope = 12,
        ControlSource = 13
    }

    public enum ModularAudioPortDomain
    {
        Control = 0,
        Gate = 1,
        Trigger = 2,
        Clock = 3,
        Audio = 4
    }

    public enum ModularAudioPortDirection
    {
        Input = 0,
        Output = 1
    }

    public enum ModularAudioPortCompatibility
    {
        Compatible = 0,
        SourceMustBeOutput = 1,
        TargetMustBeInput = 2,
        DomainMismatch = 3
    }

    public readonly struct ModularAudioPort
    {
        public ModularAudioPort(
            string id,
            ModularAudioPortDomain domain,
            ModularAudioPortDirection direction)
        {
            Id = id;
            Domain = domain;
            Direction = direction;
        }

        public string Id { get; }
        public ModularAudioPortDomain Domain { get; }
        public ModularAudioPortDirection Direction { get; }

        public static ModularAudioPortCompatibility CheckConnection(
            ModularAudioPort source,
            ModularAudioPort target)
        {
            if (source.Direction != ModularAudioPortDirection.Output)
                return ModularAudioPortCompatibility.SourceMustBeOutput;
            if (target.Direction != ModularAudioPortDirection.Input)
                return ModularAudioPortCompatibility.TargetMustBeInput;
            return source.Domain == target.Domain
                ? ModularAudioPortCompatibility.Compatible
                : ModularAudioPortCompatibility.DomainMismatch;
        }
    }

    public static class ModularAudioPortCatalog
    {
        private static readonly ModularAudioPort[] OscillatorPorts =
        {
            new("pitch.in", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Input),
            new("gate.in", ModularAudioPortDomain.Gate,
                ModularAudioPortDirection.Input),
            new("fm.in", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Input),
            new("audio.out", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] NoisePorts =
        {
            new("gate.in", ModularAudioPortDomain.Gate,
                ModularAudioPortDirection.Input),
            new("audio.out", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] AudioOutputPorts =
        {
            new("audio.in", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Input)
        };

        private static readonly ModularAudioPort[] LfoPorts =
        {
            new("rate.in", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Input),
            new("reset.in", ModularAudioPortDomain.Trigger,
                ModularAudioPortDirection.Input),
            new("control.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output),
            new("clock.out", ModularAudioPortDomain.Clock,
                ModularAudioPortDirection.Output),
            new("gate.out", ModularAudioPortDomain.Gate,
                ModularAudioPortDirection.Output),
            new("trigger.out", ModularAudioPortDomain.Trigger,
                ModularAudioPortDirection.Output),
            new("audio.out", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] SequencerPorts =
        {
            new("clock.in", ModularAudioPortDomain.Clock,
                ModularAudioPortDirection.Input),
            new("trigger.in", ModularAudioPortDomain.Trigger,
                ModularAudioPortDirection.Input),
            new("control.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output),
            new("gate.out", ModularAudioPortDomain.Gate,
                ModularAudioPortDirection.Output),
            new("trigger.out", ModularAudioPortDomain.Trigger,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] DelayPorts =
        {
            new("audio.in", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Input),
            new("time.in", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Input),
            new("audio.out", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] VcaPorts =
        {
            new("audio.in", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Input),
            new("level.in", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Input),
            new("audio.out", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] MixerPorts =
        {
            new("audio.in", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Input),
            new("audio.out", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] FilterPorts =
        {
            new("audio.in", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Input),
            new("cutoff.in", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Input),
            new("audio.out", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] EnvelopePorts =
        {
            new("gate.in", ModularAudioPortDomain.Gate,
                ModularAudioPortDirection.Input),
            new("trigger.in", ModularAudioPortDomain.Trigger,
                ModularAudioPortDirection.Input),
            new("control.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] MeterSourcePorts =
        {
            new("value.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output),
            new("trigger.out", ModularAudioPortDomain.Trigger,
                ModularAudioPortDirection.Output),
            new("audio.out", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] TrendSourcePorts =
        {
            new("value.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output),
            new("slope.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output),
            new("spread.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output),
            new("trigger.out", ModularAudioPortDomain.Trigger,
                ModularAudioPortDirection.Output),
            new("audio.out", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] PanelSourcePorts =
        {
            new("energy.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output),
            new("balance.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output),
            new("phase.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output),
            new("detail.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output),
            new("trigger.out", ModularAudioPortDomain.Trigger,
                ModularAudioPortDirection.Output),
            new("audio.out", ModularAudioPortDomain.Audio,
                ModularAudioPortDirection.Output)
        };

        private static readonly ModularAudioPort[] ControlSourcePorts =
        {
            new("control.out", ModularAudioPortDomain.Control,
                ModularAudioPortDirection.Output),
            new("gate.out", ModularAudioPortDomain.Gate,
                ModularAudioPortDirection.Output),
            new("trigger.out", ModularAudioPortDomain.Trigger,
                ModularAudioPortDirection.Output)
        };

        public static IReadOnlyList<ModularAudioPort> GetPorts(
            ModularAudioModuleKind kind)
        {
            return kind switch
            {
                ModularAudioModuleKind.Oscillator => OscillatorPorts,
                ModularAudioModuleKind.Noise => NoisePorts,
                ModularAudioModuleKind.Lfo => LfoPorts,
                ModularAudioModuleKind.Sequencer => SequencerPorts,
                ModularAudioModuleKind.Delay => DelayPorts,
                ModularAudioModuleKind.Vca => VcaPorts,
                ModularAudioModuleKind.Mixer => MixerPorts,
                ModularAudioModuleKind.Filter => FilterPorts,
                ModularAudioModuleKind.Envelope => EnvelopePorts,
                ModularAudioModuleKind.MeterSource => MeterSourcePorts,
                ModularAudioModuleKind.TrendSource => TrendSourcePorts,
                ModularAudioModuleKind.PanelSource => PanelSourcePorts,
                ModularAudioModuleKind.ControlSource => ControlSourcePorts,
                _ => AudioOutputPorts
            };
        }

        public static bool TryGetPort(
            ModularAudioModuleKind kind,
            string portId,
            out ModularAudioPort port)
        {
            var ports = GetPorts(kind);
            for (var index = 0; index < ports.Count; index++)
            {
                if (ports[index].Id != portId)
                    continue;
                port = ports[index];
                return true;
            }
            port = default;
            return false;
        }
    }
}
