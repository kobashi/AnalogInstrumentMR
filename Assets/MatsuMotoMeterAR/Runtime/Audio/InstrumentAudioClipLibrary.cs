using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    public static class InstrumentAudioClipLibrary
    {
        private const int SampleRate = 24000;
        private static readonly Dictionary<int, AudioClip> Clips = new();

        public static AudioClip Get(
            MockInstrumentTheme theme,
            InstrumentAudioCue cue)
        {
            return Get(
                theme,
                MockInstrumentKind.ToggleSwitch,
                cue,
                0);
        }

        public static AudioClip Get(
            MockInstrumentTheme theme,
            MockInstrumentKind kind,
            InstrumentAudioCue cue,
            int state = 0)
        {
            theme = MockInstrumentThemeCatalog.Normalize(theme);
            state = Mathf.Clamp(state, 0, 7);
            var key = (int)theme * 100000 +
                      (int)kind * 1000 +
                      (int)cue * 10 +
                      state;
            if (Clips.TryGetValue(key, out var clip) && clip != null)
                return clip;

            clip = Build(theme, kind, cue, state);
            Clips[key] = clip;
            return clip;
        }

        private static AudioClip Build(
            MockInstrumentTheme theme,
            MockInstrumentKind kind,
            InstrumentAudioCue cue,
            int state)
        {
            var profile = InstrumentSoundProfileCatalog.Get(kind);
            var baseDuration = IsRelay(cue) ? 0.065f : 0.045f;
            var duration = Mathf.Clamp(
                baseDuration * profile.Duration,
                0.025f,
                0.075f);
            var sampleCount = Mathf.CeilToInt(SampleRate * duration);
            var samples = new float[sampleCount];
            var random = new System.Random(
                1709 +
                (int)theme * 131 +
                (int)kind * 557 +
                (int)cue * 977 +
                state * 199);
            var frequency = ThemeFrequency(theme) *
                            CuePitch(cue) *
                            profile.Pitch;
            var decay = (IsRelay(cue) ? 47f : 72f) * profile.Decay;

            for (var index = 0; index < sampleCount; index++)
            {
                var time = index / (float)SampleRate;
                var attack = 1f - Mathf.Exp(-time * 900f);
                var envelope = attack * Mathf.Exp(-time * decay);
                var body = Mathf.Sin(Mathf.PI * 2f * frequency * time);
                var overtone = Mathf.Sin(
                    Mathf.PI * 2f * frequency *
                    profile.OvertoneRatio * time + 0.31f);
                var noise = (float)(random.NextDouble() * 2.0 - 1.0);
                var transient = noise * Mathf.Exp(-time * 260f);
                samples[index] = Mathf.Clamp(
                    envelope *
                    (body * profile.BodyLevel +
                     overtone * profile.OvertoneLevel) +
                    transient * profile.TransientLevel,
                    -0.72f,
                    0.72f);
            }

            var clip = AudioClip.Create(
                $"Generated_{theme}_{kind}_{cue}_{state}",
                sampleCount,
                1,
                SampleRate,
                false);
            clip.SetData(samples, 0);
            return clip;
        }

        private static float ThemeFrequency(MockInstrumentTheme theme)
        {
            return theme switch
            {
                MockInstrumentTheme.ForgeBrass => 470f,
                MockInstrumentTheme.KineticSafety => 930f,
                MockInstrumentTheme.MachinedErgonomics => 690f,
                MockInstrumentTheme.Superfine => 1180f,
                _ => 790f
            };
        }

        private static float CuePitch(InstrumentAudioCue cue)
        {
            return cue switch
            {
                InstrumentAudioCue.SwitchOff or
                InstrumentAudioCue.DetentDown or
                InstrumentAudioCue.ButtonUp or
                InstrumentAudioCue.LampOff or
                InstrumentAudioCue.StatusOff => 0.78f,
                InstrumentAudioCue.StatusWarning => 1.10f,
                InstrumentAudioCue.StatusDanger => 1.32f,
                InstrumentAudioCue.LampLow => 0.84f,
                InstrumentAudioCue.LampMedium => 1.0f,
                InstrumentAudioCue.LampHigh => 1.19f,
                InstrumentAudioCue.SwitchOn or
                InstrumentAudioCue.DetentUp or
                InstrumentAudioCue.ButtonDown or
                InstrumentAudioCue.LampOn or
                InstrumentAudioCue.StatusSafe => 1.0f,
                InstrumentAudioCue.RotaryStep => 1.18f,
                _ => 1f
            };
        }

        private static bool IsRelay(InstrumentAudioCue cue)
        {
            return cue == InstrumentAudioCue.LampOn ||
                   cue == InstrumentAudioCue.LampOff ||
                   cue == InstrumentAudioCue.StatusSafe ||
                   cue == InstrumentAudioCue.StatusWarning ||
                   cue == InstrumentAudioCue.StatusDanger ||
                   cue == InstrumentAudioCue.StatusOff ||
                   cue == InstrumentAudioCue.LampLow ||
                   cue == InstrumentAudioCue.LampMedium ||
                   cue == InstrumentAudioCue.LampHigh;
        }
    }
}
