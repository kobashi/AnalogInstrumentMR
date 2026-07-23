using MatsuMotoMeterAR.Anchors;

namespace MatsuMotoMeterAR.Instruments
{
    public static class MockInstrumentCatalog
    {
        public const int Count = 6;

        public static string GetTypeId(MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.RoundMeter => "meter.round",
                MockInstrumentKind.Lever => "control.lever",
                MockInstrumentKind.ToggleSwitch => "control.toggle",
                MockInstrumentKind.RotaryKnob => "control.rotary",
                MockInstrumentKind.PushButton => "control.button",
                MockInstrumentKind.IndicatorLamp => "indicator.lamp",
                _ => "meter.round"
            };
        }

        public static string GetDisplayName(MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.RoundMeter => "ROUND METER",
                MockInstrumentKind.Lever => "LEVER",
                MockInstrumentKind.ToggleSwitch => "TOGGLE",
                MockInstrumentKind.RotaryKnob => "ROTARY KNOB",
                MockInstrumentKind.PushButton => "PUSH BUTTON",
                MockInstrumentKind.IndicatorLamp => "STATUS LAMP",
                _ => "ROUND METER"
            };
        }

        public static MockInstrumentKind FromTypeId(string typeId)
        {
            return typeId switch
            {
                "control.lever" => MockInstrumentKind.Lever,
                "control.toggle" => MockInstrumentKind.ToggleSwitch,
                "control.rotary" => MockInstrumentKind.RotaryKnob,
                "control.button" => MockInstrumentKind.PushButton,
                "indicator.lamp" => MockInstrumentKind.IndicatorLamp,
                _ => MockInstrumentKind.RoundMeter
            };
        }

        public static bool IsKnownTypeId(string typeId)
        {
            return typeId == "meter.round" ||
                   typeId == "control.lever" ||
                   typeId == "control.toggle" ||
                   typeId == "control.rotary" ||
                   typeId == "control.button" ||
                   typeId == "indicator.lamp";
        }

        public static MockInstrumentKind Cycle(MockInstrumentKind current, int direction)
        {
            var index = ((int)current + (direction < 0 ? -1 : 1) + Count) % Count;
            return (MockInstrumentKind)index;
        }

        public static bool SupportsSurface(MockInstrumentKind kind, SurfaceKind surface)
        {
            if (surface != SurfaceKind.Ceiling)
                return true;

            return kind != MockInstrumentKind.Lever &&
                   kind != MockInstrumentKind.RotaryKnob;
        }
    }
}
