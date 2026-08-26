using MatsuMotoMeterAR.Anchors;

namespace MatsuMotoMeterAR.Instruments
{
    public enum MockInstrumentCategory
    {
        Meters = 0,
        Indicators = 1,
        Switches = 2,
        MotionControls = 3
    }

    public static class MockInstrumentCatalog
    {
        public const int PerformanceBaselineCount = 6;
        public const int Count = 14;
        public const int CategoryCount = 4;

        private static readonly MockInstrumentKind[] OrderedKinds =
        {
            MockInstrumentKind.RoundMeter,
            MockInstrumentKind.RoundMeterMedium,
            MockInstrumentKind.RoundMeterLarge,
            MockInstrumentKind.WindowMeter,
            MockInstrumentKind.TrendMonitor,
            MockInstrumentKind.IndicatorLamp,
            MockInstrumentKind.StatusIndicator,
            MockInstrumentKind.WindowPanel,
            MockInstrumentKind.ToggleSwitch,
            MockInstrumentKind.PushButton,
            MockInstrumentKind.RotaryKnob,
            MockInstrumentKind.Lever,
            MockInstrumentKind.ThrottleLever,
            MockInstrumentKind.PowerSlider
        };

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
                MockInstrumentKind.RoundMeterMedium => "meter.round.medium",
                MockInstrumentKind.RoundMeterLarge => "meter.round.large",
                MockInstrumentKind.TrendMonitor => "monitor.trend",
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
                MockInstrumentKind.RoundMeterMedium => "ROUND METER M",
                MockInstrumentKind.RoundMeterLarge => "ROUND METER L",
                MockInstrumentKind.TrendMonitor => "TREND MONITOR",
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
                "meter.round.medium" => MockInstrumentKind.RoundMeterMedium,
                "meter.round.large" => MockInstrumentKind.RoundMeterLarge,
                "monitor.trend" => MockInstrumentKind.TrendMonitor,
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
                   typeId == "control.power_slider" ||
                   typeId == "meter.round.medium" ||
                   typeId == "meter.round.large" ||
                   typeId == "monitor.trend";
        }

        public static MockInstrumentKind Cycle(MockInstrumentKind current, int direction)
        {
            var index = OrderedIndex(current);
            index = (index + (direction < 0 ? -1 : 1) + Count) % Count;
            return OrderedKinds[index];
        }

        public static MockInstrumentCategory GetCategory(
            MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.RoundMeter =>
                    MockInstrumentCategory.Meters,
                MockInstrumentKind.RoundMeterMedium =>
                    MockInstrumentCategory.Meters,
                MockInstrumentKind.RoundMeterLarge =>
                    MockInstrumentCategory.Meters,
                MockInstrumentKind.WindowMeter =>
                    MockInstrumentCategory.Meters,
                MockInstrumentKind.TrendMonitor =>
                    MockInstrumentCategory.Meters,
                MockInstrumentKind.IndicatorLamp =>
                    MockInstrumentCategory.Indicators,
                MockInstrumentKind.StatusIndicator =>
                    MockInstrumentCategory.Indicators,
                MockInstrumentKind.WindowPanel =>
                    MockInstrumentCategory.Indicators,
                MockInstrumentKind.ToggleSwitch =>
                    MockInstrumentCategory.Switches,
                MockInstrumentKind.PushButton =>
                    MockInstrumentCategory.Switches,
                MockInstrumentKind.RotaryKnob =>
                    MockInstrumentCategory.Switches,
                _ => MockInstrumentCategory.MotionControls
            };
        }

        public static string GetCategoryDisplayName(
            MockInstrumentKind kind)
        {
            return GetCategory(kind) switch
            {
                MockInstrumentCategory.Meters => "METERS",
                MockInstrumentCategory.Indicators => "INDICATORS",
                MockInstrumentCategory.Switches => "SWITCHES",
                _ => "MOTION"
            };
        }

        public static MockInstrumentKind JumpCategory(
            MockInstrumentKind current,
            int direction)
        {
            var category = (int)GetCategory(current);
            category =
                (category +
                 (direction < 0 ? -1 : 1) +
                 CategoryCount) %
                CategoryCount;
            return category switch
            {
                (int)MockInstrumentCategory.Meters =>
                    MockInstrumentKind.RoundMeter,
                (int)MockInstrumentCategory.Indicators =>
                    MockInstrumentKind.IndicatorLamp,
                (int)MockInstrumentCategory.Switches =>
                    MockInstrumentKind.ToggleSwitch,
                _ => MockInstrumentKind.Lever
            };
        }

        private static int OrderedIndex(MockInstrumentKind kind)
        {
            for (var index = 0; index < OrderedKinds.Length; index++)
            {
                if (OrderedKinds[index] == kind)
                    return index;
            }
            return 0;
        }

        public static bool SupportsSurface(MockInstrumentKind kind, SurfaceKind surface)
        {
            return surface == SurfaceKind.Plane ||
                   surface == SurfaceKind.Volume ||
                   surface == SurfaceKind.Wall ||
                   surface == SurfaceKind.Floor ||
                   surface == SurfaceKind.Ceiling;
        }

        public static bool IsReadOnlyMeter(MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.RoundMeter ||
                   kind == MockInstrumentKind.RoundMeterMedium ||
                   kind == MockInstrumentKind.RoundMeterLarge ||
                   kind == MockInstrumentKind.WindowMeter ||
                   kind == MockInstrumentKind.WindowPanel;
        }

        public static bool SupportsGripMotion(MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.Lever ||
                   kind == MockInstrumentKind.ThrottleLever ||
                   kind == MockInstrumentKind.PowerSlider;
        }

        public static bool UsesContactPress(MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.PushButton;
        }

    }
}
