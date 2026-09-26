using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    public static class GlobalAudioSettings
    {
        public const float DefaultEffectsVolume = 0.5f;
        public const float MaximumEffectsGain = 2f;
        private const int CurrentVolumeScaleVersion = 2;
        private const string EffectsVolumeKey =
            "AnalogInstrumentMR.Audio.EffectsVolume";
        private const string EffectsEnabledKey =
            "AnalogInstrumentMR.Audio.EffectsEnabled";
        private const string ModularAudioEnabledKey =
            "AnalogInstrumentMR.Audio.ModularEnabled";
        private const string VolumeScaleVersionKey =
            "AnalogInstrumentMR.Audio.EffectsVolumeScaleVersion";

        private static volatile float effectsVolume = LoadVolume();
        private static volatile bool effectsEnabled =
            PlayerPrefs.GetInt(EffectsEnabledKey, 1) != 0;
        private static volatile bool modularAudioEnabled =
            PlayerPrefs.GetInt(ModularAudioEnabledKey, 1) != 0;

        public static float EffectsVolume
        {
            get => effectsVolume;
            set
            {
                effectsVolume = Mathf.Clamp01(value);
                PlayerPrefs.SetFloat(EffectsVolumeKey, effectsVolume);
                PlayerPrefs.SetInt(
                    VolumeScaleVersionKey,
                    CurrentVolumeScaleVersion);
            }
        }

        public static float EffectsGain =>
            effectsVolume * MaximumEffectsGain;

        public static bool EffectsEnabled
        {
            get => effectsEnabled;
            set
            {
                effectsEnabled = value;
                PlayerPrefs.SetInt(EffectsEnabledKey, value ? 1 : 0);
            }
        }

        public static bool ModularAudioEnabled
        {
            get => modularAudioEnabled;
            set
            {
                modularAudioEnabled = value;
                PlayerPrefs.SetInt(ModularAudioEnabledKey, value ? 1 : 0);
            }
        }

        public static void ResetEffectsVolume()
        {
            EffectsVolume = DefaultEffectsVolume;
        }

        public static void Persist()
        {
            PlayerPrefs.Save();
        }

        private static float LoadVolume()
        {
            var scaleVersion = PlayerPrefs.GetInt(VolumeScaleVersionKey, 1);
            var stored = PlayerPrefs.GetFloat(EffectsVolumeKey, 1f);
            if (scaleVersion < CurrentVolumeScaleVersion)
            {
                stored *= 0.5f;
                PlayerPrefs.SetFloat(EffectsVolumeKey, stored);
                PlayerPrefs.SetInt(
                    VolumeScaleVersionKey,
                    CurrentVolumeScaleVersion);
                PlayerPrefs.Save();
            }
            return Mathf.Clamp01(stored);
        }
    }
}
