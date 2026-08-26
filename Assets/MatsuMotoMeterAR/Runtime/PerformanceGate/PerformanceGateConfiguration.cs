using MatsuMotoMeterAR.Instruments;
using UnityEngine;

namespace MatsuMotoMeterAR.PerformanceGate
{
    public static class PerformanceGateConfiguration
    {
        public const string CountExtra = "matsu_perf_count";
        public const string ThemeExtra = "matsu_perf_theme";
        public const string DurationExtra = "matsu_perf_duration";
        public const string DistanceExtra = "matsu_perf_distance";
        public const string KindExtra = "matsu_perf_kind";
        public const float DefaultDistanceMeters = 1.35f;

        private static bool loaded;
        private static int instrumentCount;
        private static MockInstrumentTheme theme;
        private static int durationSeconds = 600;
        private static float distanceMeters = DefaultDistanceMeters;
        private static MockInstrumentKind? instrumentKind;

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

        public static float DistanceMeters
        {
            get
            {
                EnsureLoaded();
                return distanceMeters;
            }
        }

        public static MockInstrumentKind? InstrumentKind
        {
            get
            {
                EnsureLoaded();
                return instrumentKind;
            }
        }

        public static int NormalizeCount(int requestedCount)
        {
            return requestedCount == 1 ||
                   requestedCount == 12 ||
                   requestedCount == 24 ||
                   requestedCount == 40 ||
                   requestedCount == 48 ||
                   requestedCount == 64
                ? requestedCount
                : 0;
        }

        public static MockInstrumentTheme ParseTheme(string value)
        {
            var byId = MockInstrumentThemeCatalog.FromThemeId(value);
            if (!string.IsNullOrWhiteSpace(value) &&
                string.Equals(
                    MockInstrumentThemeCatalog.GetThemeId(byId),
                    value,
                    System.StringComparison.OrdinalIgnoreCase))
            {
                return byId;
            }
            if (!string.IsNullOrWhiteSpace(value) &&
                System.Enum.TryParse(value, true, out MockInstrumentTheme parsed))
            {
                return MockInstrumentThemeCatalog.Normalize(parsed);
            }

            return MockInstrumentThemeCatalog.DefaultTheme;
        }

        public static int NormalizeDuration(int requestedSeconds)
        {
            return requestedSeconds == 60 ||
                   requestedSeconds == 600 ||
                   requestedSeconds == 1800
                ? requestedSeconds
                : 600;
        }

        public static float NormalizeDistance(float requestedMeters)
        {
            return !float.IsNaN(requestedMeters) &&
                   !float.IsInfinity(requestedMeters) &&
                   requestedMeters >= 0.5f &&
                   requestedMeters <= 5f
                ? requestedMeters
                : DefaultDistanceMeters;
        }

        public static MockInstrumentKind? ParseKind(string value)
        {
            if (!string.IsNullOrWhiteSpace(value) &&
                System.Enum.TryParse(
                    value,
                    true,
                    out MockInstrumentKind parsed) &&
                System.Enum.IsDefined(typeof(MockInstrumentKind), parsed))
            {
                return parsed;
            }
            return null;
        }

        private static void EnsureLoaded()
        {
            if (loaded)
                return;

            loaded = true;
            instrumentCount = 0;
            theme = MockInstrumentThemeCatalog.DefaultTheme;
            durationSeconds = 600;
            distanceMeters = DefaultDistanceMeters;
            instrumentKind = null;

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
                distanceMeters = NormalizeDistance(
                    intent.Call<float>(
                        "getFloatExtra",
                        DistanceExtra,
                        DefaultDistanceMeters));
                instrumentKind = ParseKind(
                    intent.Call<string>("getStringExtra", KindExtra));
            }
            catch (AndroidJavaException exception)
            {
                Debug.LogWarning($"[PerfGate] Could not read launch extras: {exception.Message}");
            }
#endif
        }
    }
}
