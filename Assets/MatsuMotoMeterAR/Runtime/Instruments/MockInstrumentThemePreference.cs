using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public static class MockInstrumentThemePreference
    {
        public const string PlayerPrefsKey = "settings.instrument.themeId";

        public static MockInstrumentTheme Load()
        {
            return MockInstrumentThemeCatalog.FromThemeId(
                PlayerPrefs.GetString(
                    PlayerPrefsKey,
                    MockInstrumentThemeCatalog.GetThemeId(
                        MockInstrumentThemeCatalog.DefaultTheme)));
        }

        public static void Save(MockInstrumentTheme theme)
        {
            var normalized = MockInstrumentThemeCatalog.Normalize(theme);
            PlayerPrefs.SetString(
                PlayerPrefsKey,
                MockInstrumentThemeCatalog.GetThemeId(normalized));
            PlayerPrefs.Save();
        }
    }
}
