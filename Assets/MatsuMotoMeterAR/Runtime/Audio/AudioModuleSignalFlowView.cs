using MatsuMotoMeterAR.Instruments;
using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    [DisallowMultipleComponent]
    public sealed class AudioModuleSignalFlowView : MonoBehaviour
    {
        public const float RefreshIntervalSeconds = 0.05f;
        public const int TextureSize = 64;

        private const int BandCount = 8;
        private const int BandHeight = TextureSize / BandCount;
        private static Texture2D sharedTexture;

        [SerializeField] private Renderer signalRenderer;
        [SerializeField] private MockInstrumentKind instrumentKind;
        [SerializeField] private MockInstrumentTheme theme;

        private MaterialPropertyBlock propertyBlock;
        private ModularAudioModuleRuntime module;
        private float nextRefreshTime;

        public Renderer SignalRenderer => signalRenderer;
        public Texture2D SharedSignalTexture => SharedTexture();
        public Vector4 CurrentTextureTransform { get; private set; }
        public Color CurrentColor { get; private set; }

        public void Configure(
            MockInstrumentKind kind,
            MockInstrumentTheme visualTheme,
            Renderer renderer)
        {
            instrumentKind = kind;
            theme = MockInstrumentThemeCatalog.Normalize(visualTheme);
            signalRenderer = renderer;
            ApplyNow(Time.unscaledTime);
            nextRefreshTime = Time.unscaledTime +
                              RefreshIntervalSeconds * InitialPhase();
        }

        public void Bind(ModularAudioModuleRuntime runtime)
        {
            module = runtime;
            ApplyNow(Time.unscaledTime);
        }

        public void ApplyNow(float timeSeconds)
        {
            if (signalRenderer == null)
                return;

            var values = Evaluate(timeSeconds);
            var bandOffset = (values.Band * BandHeight + 1f) / TextureSize;
            var bandScale = (BandHeight - 2f) / TextureSize;
            CurrentTextureTransform = new Vector4(
                values.Density,
                bandScale,
                values.Offset,
                bandOffset);
            CurrentColor = ThemeColor(theme) * values.Intensity;
            CurrentColor = new Color(
                CurrentColor.r,
                CurrentColor.g,
                CurrentColor.b,
                1f);

            propertyBlock ??= new MaterialPropertyBlock();
            signalRenderer.GetPropertyBlock(propertyBlock);
            propertyBlock.SetTexture("_BaseMap", SharedTexture());
            propertyBlock.SetTexture("_MainTex", SharedTexture());
            propertyBlock.SetVector("_BaseMap_ST", CurrentTextureTransform);
            propertyBlock.SetVector("_MainTex_ST", CurrentTextureTransform);
            propertyBlock.SetColor("_BaseColor", CurrentColor);
            propertyBlock.SetColor("_Color", CurrentColor);
            signalRenderer.SetPropertyBlock(propertyBlock);
        }

        private void Update()
        {
            var now = Time.unscaledTime;
            if (now < nextRefreshTime)
                return;
            ApplyNow(now);
            nextRefreshTime = now + RefreshIntervalSeconds;
        }

        private SignalValues Evaluate(float timeSeconds)
        {
            switch (module?.Node)
            {
                case ModularOscillatorNode oscillator:
                {
                    var normalized = Mathf.InverseLerp(
                        55f,
                        1760f,
                        Finite(oscillator.Frequency, 220f));
                    var active = oscillator.Gate ? 1f : 0.08f;
                    return new SignalValues(
                        Mathf.Clamp((int)oscillator.Waveform, 0, 3),
                        Mathf.Lerp(1.5f, 5f, normalized),
                        Mathf.Repeat(-timeSeconds *
                                     Mathf.Lerp(0.22f, 1.8f, normalized), 1f),
                        active * Mathf.Lerp(0.65f, 1.15f, normalized));
                }
                case ModularNoiseNode noise:
                {
                    var level = Mathf.Clamp01(Finite(noise.Level, 0.15f));
                    var colorBias = Mathf.Clamp((int)noise.Color, 0, 2);
                    return new SignalValues(
                        4,
                        Mathf.Lerp(2.5f, 8f, level),
                        Mathf.Repeat(-timeSeconds * (0.65f + colorBias * 0.17f), 1f),
                        noise.Gate ? Mathf.Lerp(0.35f, 1.2f, level) : 0.06f);
                }
                case ModularLfoNode lfo:
                {
                    var normalized = Mathf.InverseLerp(
                        0.05f,
                        20f,
                        Finite(lfo.Frequency, 1f));
                    var depth = Mathf.Clamp01(Finite(lfo.Depth, 0.8f));
                    return new SignalValues(
                        Mathf.Clamp((int)lfo.Waveform, 0, 3),
                        Mathf.Lerp(1f, 3f, normalized),
                        Mathf.Repeat(-timeSeconds *
                                     Mathf.Lerp(0.05f, 0.9f, normalized), 1f),
                        Mathf.Lerp(0.25f, 1.15f, depth));
                }
                case ModularSequencerNode sequencer:
                {
                    var steps = sequencer.StepCount <= 8 ? 8 : 16;
                    var tempo = Mathf.Clamp(Finite(sequencer.TempoBpm, 120f), 20f, 300f);
                    var stepPhase = sequencer.PlaybackMode ==
                                    ModularSequencerPlaybackMode.StepTrigger
                        ? sequencer.CurrentStep / (float)steps
                        : Mathf.Repeat(
                            sequencer.CurrentStep / (float)steps +
                            timeSeconds * tempo / 240f,
                            1f);
                    var stepValue = Mathf.Clamp01(
                        (sequencer.GetStepValue(sequencer.CurrentStep) + 1f) * 0.5f);
                    return new SignalValues(
                        5,
                        steps,
                        -stepPhase,
                        Mathf.Lerp(0.45f, 1.2f, stepValue));
                }
                case ModularDelayNode delay:
                {
                    var normalized = Mathf.InverseLerp(
                        ModularDelayNode.MinimumDelaySeconds,
                        ModularDelayNode.MaximumDelaySeconds,
                        Finite(delay.DelaySeconds, 0.25f));
                    return new SignalValues(
                        6,
                        Mathf.Lerp(7f, 2f, normalized),
                        Mathf.Repeat(-timeSeconds * Mathf.Lerp(1.2f, 0.25f, normalized), 1f),
                        Mathf.Lerp(0.7f, 1.15f,
                            Mathf.Clamp01(Finite(delay.Feedback, 0.42f))));
                }
                case ModularVcaNode vca:
                {
                    var level = Mathf.Clamp01(Finite(vca.ManualLevel, 0.5f));
                    return new SignalValues(
                        3,
                        Mathf.Lerp(1.5f, 5f, level),
                        Mathf.Repeat(-timeSeconds * Mathf.Lerp(0.12f, 0.75f, level), 1f),
                        Mathf.Lerp(0.15f, 1.2f, level));
                }
                case ModularMixerNode mixer:
                {
                    var gain = Mathf.Clamp01(Finite(mixer.Gain, 1f) * 0.5f);
                    return new SignalValues(
                        5,
                        Mathf.Lerp(2f, 7f, gain),
                        Mathf.Repeat(-timeSeconds * Mathf.Lerp(0.2f, 0.9f, gain), 1f),
                        Mathf.Lerp(0.25f, 1.2f, gain));
                }
                case ModularFilterNode filter:
                {
                    var cutoff = Mathf.Clamp(
                        Finite(filter.CurrentCutoff, 1200f),
                        20f,
                        18000f);
                    var normalized = Mathf.Clamp01(
                        Mathf.Log(cutoff / 20f) /
                        Mathf.Log(18000f / 20f));
                    return new SignalValues(
                        6,
                        Mathf.Lerp(1.5f, 7f, normalized),
                        Mathf.Repeat(-timeSeconds * Mathf.Lerp(0.15f, 1.1f, normalized), 1f),
                        Mathf.Lerp(0.35f, 1.2f, normalized));
                }
                case ModularEnvelopeNode envelope:
                {
                    var level = Mathf.Clamp01(Finite(
                        envelope.CurrentLevel,
                        0f));
                    return new SignalValues(
                        4,
                        Mathf.Lerp(1f, 6f, level),
                        Mathf.Repeat(-timeSeconds * Mathf.Lerp(0.1f, 0.8f, level), 1f),
                        Mathf.Lerp(0.08f, 1.2f, level));
                }
                case ModularAudioOutputNode output:
                {
                    var gain = Mathf.Clamp01(Finite(output.Gain, 1f) * 0.5f);
                    return new SignalValues(
                        7,
                        Mathf.Lerp(2f, 5f, gain),
                        Mathf.Repeat(-timeSeconds * Mathf.Lerp(0.15f, 0.8f, gain), 1f),
                        output.Muted ? 0.05f : Mathf.Lerp(0.25f, 1.25f, gain));
                }
                default:
                    return Defaults(timeSeconds);
            }
        }

        private SignalValues Defaults(float timeSeconds)
        {
            return instrumentKind switch
            {
                MockInstrumentKind.AudioNoise => new SignalValues(
                    4, 4f, Mathf.Repeat(-timeSeconds * 0.65f, 1f), 0.65f),
                MockInstrumentKind.AudioSequencer => new SignalValues(
                    5, 8f, Mathf.Repeat(-timeSeconds * 0.5f, 1f), 0.75f),
                MockInstrumentKind.AudioDelay => new SignalValues(
                    6, 4f, Mathf.Repeat(-timeSeconds * 0.5f, 1f), 0.75f),
                MockInstrumentKind.AudioVca => new SignalValues(
                    3, 3f, Mathf.Repeat(-timeSeconds * 0.35f, 1f), 0.65f),
                MockInstrumentKind.AudioMixer => new SignalValues(
                    5, 4f, Mathf.Repeat(-timeSeconds * 0.5f, 1f), 0.75f),
                MockInstrumentKind.AudioFilter => new SignalValues(
                    6, 4f, Mathf.Repeat(-timeSeconds * 0.45f, 1f), 0.75f),
                MockInstrumentKind.AudioEnvelope => new SignalValues(
                    4, 3f, Mathf.Repeat(-timeSeconds * 0.35f, 1f), 0.65f),
                MockInstrumentKind.AudioOutput => new SignalValues(
                    7, 3f, Mathf.Repeat(-timeSeconds * 0.4f, 1f), 0.75f),
                _ => new SignalValues(
                    0, 2f, Mathf.Repeat(-timeSeconds * 0.35f, 1f), 0.75f)
            };
        }

        private float InitialPhase()
        {
            return Mathf.Repeat(Mathf.Abs(GetInstanceID()) * 0.61803398875f, 1f);
        }

        private static Texture2D SharedTexture()
        {
            if (sharedTexture != null)
                return sharedTexture;

            var pixels = new Color32[TextureSize * TextureSize];
            var dark = new Color32(14, 14, 14, 255);
            for (var index = 0; index < pixels.Length; index++)
                pixels[index] = dark;

            for (var band = 0; band < BandCount; band++)
            {
                for (var y = 1; y < BandHeight - 1; y++)
                {
                    var py = band * BandHeight + y;
                    for (var x = 0; x < TextureSize; x++)
                    {
                        var u = x / (float)TextureSize;
                        var v = (y - 1f) / (BandHeight - 3f);
                        var strength = Pattern(band, u, v);
                        var value = (byte)Mathf.RoundToInt(
                            Mathf.Lerp(20f, 255f, Mathf.Clamp01(strength)));
                        pixels[py * TextureSize + x] =
                            new Color32(value, value, value, 255);
                    }
                }
            }

            sharedTexture = new Texture2D(
                TextureSize,
                TextureSize,
                TextureFormat.RGBA32,
                false)
            {
                name = "AudioModuleSignalFlow_Shared",
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Repeat,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave
            };
            sharedTexture.SetPixels32(pixels);
            sharedTexture.Apply(false, true);
            return sharedTexture;
        }

        private static float Pattern(int band, float u, float v)
        {
            var center = 1f - Mathf.Abs(v * 2f - 1f);
            return band switch
            {
                0 => center * (0.45f + 0.55f * Mathf.Sin(u * Mathf.PI * 2f)),
                1 => center * (1f - Mathf.Abs(Mathf.Repeat(u * 2f, 1f) * 2f - 1f)),
                2 => center * Mathf.Repeat(u * 1.9f, 1f),
                3 => center * (Mathf.Repeat(u * 2f, 1f) < 0.5f ? 1f : 0.18f),
                4 => Hash01(Mathf.FloorToInt(u * 32f), Mathf.FloorToInt(v * 5f)),
                5 => center * (Mathf.Repeat(u * 8f, 1f) < 0.34f ? 1f : 0.14f),
                6 => center * Mathf.Pow(
                    Mathf.Clamp01(1f - Mathf.Repeat(u * 4f, 1f) * 1.5f), 2f),
                _ => center * Mathf.Lerp(0.25f, 1f, u)
            };
        }

        private static float Hash01(int x, int y)
        {
            unchecked
            {
                var hash = x * 374761393 + y * 668265263;
                hash = (hash ^ (hash >> 13)) * 1274126177;
                return (hash & 0x7fffffff) / (float)int.MaxValue;
            }
        }

        private static float Finite(float value, float fallback)
        {
            return float.IsNaN(value) || float.IsInfinity(value)
                ? fallback
                : value;
        }

        private static Color ThemeColor(MockInstrumentTheme visualTheme)
        {
            return visualTheme switch
            {
                MockInstrumentTheme.ForgeBrass => new Color(1f, 0.55f, 0.16f, 1f),
                MockInstrumentTheme.KineticSafety => new Color(1f, 0.25f, 0.04f, 1f),
                MockInstrumentTheme.MachinedErgonomics => new Color(0.22f, 0.82f, 1f, 1f),
                MockInstrumentTheme.Superfine => new Color(0.05f, 0.90f, 1f, 1f),
                _ => new Color(0.12f, 0.95f, 0.84f, 1f)
            };
        }

        private readonly struct SignalValues
        {
            public SignalValues(int band, float density, float offset, float intensity)
            {
                Band = band;
                Density = density;
                Offset = offset;
                Intensity = intensity;
            }

            public int Band { get; }
            public float Density { get; }
            public float Offset { get; }
            public float Intensity { get; }
        }
    }
}
