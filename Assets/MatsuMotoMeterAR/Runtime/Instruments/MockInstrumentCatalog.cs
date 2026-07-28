using MatsuMotoMeterAR.Anchors;

namespace MatsuMotoMeterAR.Instruments
{
    public static class MockInstrumentCatalog
    {
        public const int PerformanceBaselineCount = 6;
        public const int Count = 11;

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
                MockInstrumentKind.WindowMeter => "meter.window",
                MockInstrumentKind.WindowPanel => "panel.window",
                MockInstrumentKind.StatusIndicator => "indicator.status",
                MockInstrumentKind.ThrottleLever => "control.throttle",
                MockInstrumentKind.PowerSlider => "control.power_slider",
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
                MockInstrumentKind.WindowMeter => "WINDOW METER",
                MockInstrumentKind.WindowPanel => "WINDOW PANEL",
                MockInstrumentKind.StatusIndicator => "STATUS INDICATOR",
                MockInstrumentKind.ThrottleLever => "THROTTLE LEVER",
                MockInstrumentKind.PowerSlider => "POWER SLIDER",
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
                "meter.window" => MockInstrumentKind.WindowMeter,
                "panel.window" => MockInstrumentKind.WindowPanel,
                "indicator.status" => MockInstrumentKind.StatusIndicator,
                "control.throttle" => MockInstrumentKind.ThrottleLever,
                "control.power_slider" => MockInstrumentKind.PowerSlider,
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
                   typeId == "indicator.lamp" ||
                   typeId == "meter.window" ||
                   typeId == "panel.window" ||
                   typeId == "indicator.status" ||
                   typeId == "control.throttle" ||
                   typeId == "control.power_slider";
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
                   kind != MockInstrumentKind.RotaryKnob &&
                   kind != MockInstrumentKind.ThrottleLever &&
                   kind != MockInstrumentKind.PowerSlider;
        }

    }
}
