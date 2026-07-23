using MatsuMotoMeterAR.Instruments;
using UnityEngine;

namespace MatsuMotoMeterAR.PerformanceGate
{
    public static class PerformanceGateConfiguration
    {
        public const string CountExtra = "matsu_perf_count";
        public const string ThemeExtra = "matsu_perf_theme";
        public const string DurationExtra = "matsu_perf_duration";

        private static bool loaded;
        private static int instrumentCount;
        private static MockInstrumentTheme theme;
        private static int durationSeconds = 600;

        public static bool IsEnabled
        {
            get
            {
                EnsureLoaded();
                return instrumentCount > 0;
            }
        }

        public static int InstrumentCount
        {
            get
            {
                EnsureLoaded();
                return instrumentCount;
            }
        }

        public static MockInstrumentTheme Theme
        {
            get
            {
                EnsureLoaded();
                return theme;
            }
        }

        public static int DurationSeconds
        {
            get
            {
                EnsureLoaded();
                return durationSeconds;
            }
        }

        public static int NormalizeCount(int requestedCount)
        {
            return requestedCount == 12 || requestedCount == 24 || requestedCount == 40
                ? requestedCount
                : 0;
        }

        public static MockInstrumentTheme ParseTheme(string value)
        {
            if (!string.IsNullOrWhiteSpace(value) &&
                System.Enum.TryParse(value, true, out MockInstrumentTheme parsed))
            {
                return MockInstrumentThemeCatalog.Normalize(parsed);
            }

            return MockInstrumentThemeCatalog.DefaultTheme;
        }

        public static int NormalizeDuration(int requestedSeconds)
        {
            return requestedSeconds == 60 ? 60 : 600;
        }

        private static void EnsureLoaded()
        {
            if (loaded)
                return;

            loaded = true;
            instrumentCount = 0;
            theme = MockInstrumentThemeCatalog.DefaultTheme;
            durationSeconds = 600;

#if UNITY_ANDROID && !UNITY_EDITOR
            try
            {
                using var unityPlayer = new AndroidJavaClass("com.unity3d.player.UnityPlayer");
                using var activity = unityPlayer.GetStatic<AndroidJavaObject>("currentActivity");
                using var intent = activity?.Call<AndroidJavaObject>("getIntent");
                if (intent == null)
                    return;

                instrumentCount = NormalizeCount(
                    intent.Call<int>("getIntExtra", CountExtra, 0));
                theme = ParseTheme(intent.Call<string>("getStringExtra", ThemeExtra));
                durationSeconds = NormalizeDuration(
                    intent.Call<int>("getIntExtra", DurationExtra, 600));
            }
            catch (AndroidJavaException exception)
            {
                Debug.LogWarning($"[PerfGate] Could not read launch extras: {exception.Message}");
            }
#endif
        }
    }
}
