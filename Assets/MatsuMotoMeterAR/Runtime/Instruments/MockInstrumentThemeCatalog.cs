using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public static class MockInstrumentThemeCatalog
    {
        public const int Count = 4;
        public const MockInstrumentTheme DefaultTheme = MockInstrumentTheme.OrbitalAnalog;

        public readonly struct Palette
        {
            public Palette(
                Color housing,
                Color face,
                Color dark,
                Color primary,
                Color warning,
                Color ready)
            {
                Housing = housing;
                Face = face;
                Dark = dark;
                Primary = primary;
                Warning = warning;
                Ready = ready;
            }

            public Color Housing { get; }
            public Color Face { get; }
            public Color Dark { get; }
            public Color Primary { get; }
            public Color Warning { get; }
            public Color Ready { get; }
        }

        public static string GetThemeId(MockInstrumentTheme theme)
        {
            theme = Normalize(theme);
            return theme switch
            {
                MockInstrumentTheme.ForgeBrass => "forge-brass",
                MockInstrumentTheme.KineticSafety => "kinetic-safety",
                MockInstrumentTheme.MachinedErgonomics => "machined-ergonomics",
                _ => "orbital-analog"
            };
        }

        public static string GetDisplayName(MockInstrumentTheme theme)
        {
            theme = Normalize(theme);
            return theme switch
            {
                MockInstrumentTheme.ForgeBrass => "FORGE BRASS",
                MockInstrumentTheme.KineticSafety => "KINETIC SAFETY",
                MockInstrumentTheme.MachinedErgonomics =>
                    "MACHINED ERGONOMICS",
                _ => "ORBITAL ANALOG"
            };
        }

        public static MockInstrumentTheme FromThemeId(string themeId)
        {
            return themeId switch
            {
                "forge-brass" => MockInstrumentTheme.ForgeBrass,
                "kinetic-safety" => MockInstrumentTheme.KineticSafety,
                "machined-ergonomics" =>
                    MockInstrumentTheme.MachinedErgonomics,
                _ => DefaultTheme
            };
        }

        public static MockInstrumentTheme Normalize(MockInstrumentTheme theme)
        {
            return (int)theme >= 0 && (int)theme < Count
                ? theme
                : DefaultTheme;
        }

        public static MockInstrumentTheme Cycle(
            MockInstrumentTheme current,
            int direction)
        {
            var normalized = (int)Normalize(current);
            var offset = direction < 0 ? Count - 1 : 1;
            return (MockInstrumentTheme)((normalized + offset) % Count);
        }

        public static Palette GetPalette(MockInstrumentTheme theme)
        {
            theme = Normalize(theme);
            return theme switch
            {
                MockInstrumentTheme.ForgeBrass => new Palette(
                    new Color(0.25f, 0.16f, 0.08f),
                    new Color(0.82f, 0.68f, 0.38f),
                    new Color(0.07f, 0.055f, 0.04f),
                    new Color(0.76f, 0.24f, 0.08f),
                    new Color(1f, 0.55f, 0.08f),
                    new Color(0.32f, 0.88f, 0.48f)),
                MockInstrumentTheme.KineticSafety => new Palette(
                    new Color(0.08f, 0.11f, 0.14f),
                    new Color(0.62f, 0.69f, 0.72f),
                    new Color(0.025f, 0.035f, 0.045f),
                    new Color(1f, 0.25f, 0.035f),
                    new Color(1f, 0.72f, 0.04f),
                    new Color(0.08f, 1f, 0.58f)),
                MockInstrumentTheme.MachinedErgonomics => new Palette(
                    new Color(0.72f, 0.75f, 0.78f),
                    new Color(0.18f, 0.24f, 0.28f),
                    new Color(0.012f, 0.020f, 0.028f),
                    new Color(0.05f, 0.88f, 0.92f),
                    new Color(1f, 0.52f, 0.08f),
                    new Color(0.18f, 1f, 0.58f)),
                _ => new Palette(
                    new Color(0.12f, 0.14f, 0.16f),
                    new Color(0.72f, 0.75f, 0.7f),
                    new Color(0.06f, 0.07f, 0.08f),
                    new Color(0.9f, 0.12f, 0.06f),
                    new Color(1f, 0.48f, 0.04f),
                    new Color(0.1f, 0.95f, 0.45f))
            };
        }
    }
}
