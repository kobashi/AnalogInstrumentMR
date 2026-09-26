using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    [DisallowMultipleComponent]
    public sealed class AudioModuleDisplayView : MonoBehaviour
    {
        public const int TextureWidth = 256;
        public const int TextureHeight = 96;
        public const float RefreshIntervalSeconds = 0.1f;

        private static readonly IReadOnlyDictionary<char, string[]> Glyphs =
            CreateGlyphs();
        [SerializeField] private Renderer displayRenderer;
        [SerializeField] private MockInstrumentKind instrumentKind;
        [SerializeField] private MockInstrumentTheme theme;

        private readonly Color32[] pixels =
            new Color32[TextureWidth * TextureHeight];
        private Texture2D texture;
        private Mesh generatedDisplayMesh;
        private ModularAudioModuleRuntime module;
        private float nextRefreshTime;

        public Renderer DisplayRenderer => displayRenderer;
        public Texture2D DisplayTexture => texture;
        public float DisplayedLfoPhase { get; private set; }
        public int DisplayedLfoMarkerColumn { get; private set; }

        public void Configure(
            MockInstrumentKind kind,
            MockInstrumentTheme visualTheme,
            Renderer renderer)
        {
            instrumentKind = kind;
            theme = MockInstrumentThemeCatalog.Normalize(visualTheme);
            displayRenderer = renderer;
            EnsureDisplayUv();
            EnsureTexture();
            RedrawNow();
        }

        public void Bind(ModularAudioModuleRuntime runtime)
        {
            module = runtime;
            RedrawNow();
        }

        public void RedrawNow()
        {
            if (displayRenderer == null)
                return;
            EnsureTexture();
            var foreground = ForegroundColor(theme);
            var dim = DimColor(foreground);
            Clear(new Color32(3, 9, 13, 255));
            DrawFrame(dim);
            DisplayedLfoPhase = 0f;
            DisplayedLfoMarkerColumn = 0;

            switch (instrumentKind)
            {
                case MockInstrumentKind.AudioOscillator:
                    DrawOscillator(foreground, dim);
                    break;
                case MockInstrumentKind.AudioNoise:
                    DrawNoise(foreground, dim);
                    break;
                case MockInstrumentKind.AudioLfo:
                    DrawLfo(foreground, dim);
                    break;
                case MockInstrumentKind.AudioSequencer:
                    DrawSequencer(foreground, dim);
                    break;
                case MockInstrumentKind.AudioDelay:
                    DrawDelay(foreground, dim);
                    break;
                case MockInstrumentKind.AudioVca:
                    DrawVca(foreground, dim);
                    break;
                case MockInstrumentKind.AudioMixer:
                    DrawMixer(foreground, dim);
                    break;
                case MockInstrumentKind.AudioFilter:
                    DrawFilter(foreground, dim);
                    break;
                case MockInstrumentKind.AudioEnvelope:
                    DrawEnvelope(foreground, dim);
                    break;
                default:
                    DrawOutput(foreground, dim);
                    break;
            }

            texture.SetPixels32(pixels);
            texture.Apply(false, false);
            ApplyTexture();
            nextRefreshTime = Time.unscaledTime + RefreshIntervalSeconds;
        }

        private void Update()
        {
            if (Time.unscaledTime >= nextRefreshTime)
                RedrawNow();
        }

        private void DrawOscillator(Color32 color, Color32 dim)
        {
            var oscillator = module?.Node as ModularOscillatorNode;
            var waveform = oscillator?.Waveform ?? ModularOscillatorWaveform.Sine;
            var frequency = oscillator?.Frequency ?? 220f;
            DrawText(9, 77, WaveformName(waveform), color, 2);
            DrawText(154, 77, $"{Mathf.RoundToInt(frequency)} HZ", color, 2);
            DrawWaveform(10, 15, 236, 47, waveform, 0f, color, dim);
            DrawHorizontalBar(10, 8, 236, NormalizedValue(), color, dim);
        }

        private void DrawNoise(Color32 color, Color32 dim)
        {
            var noise = module?.Node as ModularNoiseNode;
            var noiseColor = noise?.Color ?? ModularNoiseColor.White;
            var level = noise?.Level ?? Mathf.Lerp(0.02f, 0.35f, NormalizedValue());
            DrawText(9, 77, noiseColor.ToString().ToUpperInvariant(), color, 2);
            DrawText(183, 77, $"{Mathf.RoundToInt(level * 100f)}%", color, 2);
            for (var x = 10; x < 246; x += 3)
            {
                var hash = (x * 1103515245 + (int)noiseColor * 12345) & 0x7fffffff;
                var height = 4 + hash % 35;
                DrawLine(x, 13, x, 13 + height, (x / 3) % 3 == 0 ? color : dim);
            }
            DrawHorizontalBar(10, 8, 236,
                Mathf.InverseLerp(0.02f, 0.35f, level), color, dim);
        }

        private void DrawLfo(Color32 color, Color32 dim)
        {
            var lfo = module?.Node as ModularLfoNode;
            var waveform = lfo?.Waveform ?? ModularOscillatorWaveform.Sine;
            var frequency = lfo?.Frequency ?? 1f;
            DrawText(9, 77, WaveformName(waveform), color, 2);
            DrawText(158, 77, $"{frequency:0.00} HZ", color, 2);
            var phase = Mathf.Repeat(lfo?.Phase01 ?? 0f, 1f);
            DisplayedLfoPhase = phase;
            DrawWaveform(
                10,
                15,
                236,
                47,
                waveform,
                0f,
                color,
                dim,
                1f);
            var markerX = 10 + Mathf.RoundToInt(235f * phase);
            DisplayedLfoMarkerColumn = markerX;
            DrawLine(markerX, 12, markerX, 65, color);
        }

        private void DrawSequencer(Color32 color, Color32 dim)
        {
            var sequencer = module?.Node as ModularSequencerNode;
            var stepCount = sequencer?.StepCount ??
                (NormalizedValue() >= 0.5f ? 16 : 8);
            var tempo = sequencer?.TempoBpm ?? 120f;
            var current = sequencer?.CurrentStep ?? 0;
            var triggerStep = sequencer?.PlaybackMode ==
                              ModularSequencerPlaybackMode.StepTrigger;
            DrawText(9, 77, $"{stepCount} STEP", color, 2);
            DrawText(
                174,
                77,
                triggerStep ? "TRIG" : $"{Mathf.RoundToInt(tempo)}",
                color,
                2);
            for (var index = 0; index < 16; index++)
            {
                var column = index % 8;
                var row = index / 8;
                var x = 10 + column * 30;
                var y = 13 + (1 - row) * 27;
                var value = sequencer?.GetStepValue(index) ??
                    ModularAudioParameterPolicy.DefaultSequencerStepValue(index);
                var active = index < stepCount;
                DrawRect(x, y, 23, 20, active ? dim : new Color32(9, 18, 21, 255));
                var center = y + 10;
                var valueY = center + Mathf.RoundToInt(value * 8f);
                DrawLine(x + 2, center, x + 20, center, dim);
                DrawLine(x + 4, center, x + 4, valueY, active ? color : dim);
                if (index == current && active)
                    DrawOutline(x - 1, y - 1, 25, 22, color);
            }
        }

        private void DrawDelay(Color32 color, Color32 dim)
        {
            var delay = module?.Node as ModularDelayNode;
            var seconds = delay?.DelaySeconds ?? Mathf.Lerp(
                ModularDelayNode.MinimumDelaySeconds,
                ModularDelayNode.MaximumDelaySeconds,
                NormalizedValue());
            DrawText(9, 77, "DELAY", color, 2);
            DrawText(159, 77, $"{Mathf.RoundToInt(seconds * 1000f)} MS", color, 2);
            var spacing = Mathf.RoundToInt(Mathf.Lerp(22f, 67f,
                Mathf.InverseLerp(
                    ModularDelayNode.MinimumDelaySeconds,
                    ModularDelayNode.MaximumDelaySeconds,
                    seconds)));
            DrawLine(17, 18, 17, 58, color);
            for (var tap = 1; tap <= 3; tap++)
            {
                var x = Mathf.Min(239, 17 + spacing * tap);
                var height = 34 - tap * 7;
                DrawLine(x, 18, x, 18 + height, tap == 1 ? color : dim);
                DrawLine(x - 4, 18 + height, x + 4, 18 + height,
                    tap == 1 ? color : dim);
            }
            DrawHorizontalBar(10, 8, 236,
                Mathf.InverseLerp(
                    ModularDelayNode.MinimumDelaySeconds,
                    ModularDelayNode.MaximumDelaySeconds,
                    seconds), color, dim);
        }

        private void DrawOutput(Color32 color, Color32 dim)
        {
            var output = module?.Node as ModularAudioOutputNode;
            var gain = output?.Gain ?? NormalizedValue() * 2f;
            DrawText(9, 77, "OUTPUT", color, 2);
            DrawText(162, 77, $"{Mathf.RoundToInt(gain * 100f)}%", color, 2);
            var normalized = Mathf.Clamp01(gain * 0.5f);
            for (var band = 0; band < 12; band++)
            {
                var x = 12 + band * 19;
                var height = 6 + band * 3;
                var active = band / 11f <= normalized;
                DrawRect(x, 13, 13, height, active ? color : dim);
            }
            DrawHorizontalBar(10, 8, 236, normalized, color, dim);
        }

        private void DrawVca(Color32 color, Color32 dim)
        {
            var vca = module?.Node as ModularVcaNode;
            var controlDriven = vca?.IsControlDriven ?? false;
            var level = Mathf.Clamp01(
                controlDriven
                    ? vca?.CurrentLevel ?? 0f
                    : vca?.ManualLevel ?? NormalizedValue());
            DrawText(9, 77, "VCA", color, 2);
            DrawText(167, 77, controlDriven ? "CV" : "MAN", color, 2);
            for (var band = 0; band < 10; band++)
            {
                var x = 13 + band * 23;
                var height = 7 + band * 4;
                DrawRect(
                    x,
                    14,
                    14,
                    height,
                    band / 9f <= level ? color : dim);
            }
            DrawHorizontalBar(10, 8, 236, level, color, dim);
        }

        private void DrawMixer(Color32 color, Color32 dim)
        {
            var mixer = module?.Node as ModularMixerNode;
            var gain = mixer?.Gain ?? NormalizedValue() * 2f;
            DrawText(9, 77, "MIXER", color, 2);
            DrawText(158, 77, $"{gain:0.00} X", color, 2);
            for (var channel = 0; channel < 4; channel++)
            {
                var x = 18 + channel * 57;
                var height = 18 + channel * 8;
                DrawRect(x, 14, 18, height, channel % 2 == 0 ? color : dim);
                DrawLine(x - 3, 14 + height, x + 21, 14 + height, color);
            }
            DrawHorizontalBar(10, 8, 236, Mathf.Clamp01(gain * 0.5f), color, dim);
        }

        private void DrawFilter(Color32 color, Color32 dim)
        {
            var filter = module?.Node as ModularFilterNode;
            var cutoff = Mathf.Clamp(
                filter?.CurrentCutoff ?? filter?.Cutoff ?? 1200f,
                20f,
                18000f);
            var resonance = Mathf.Clamp01(filter?.Resonance ?? 0.2f);
            var normalizedCutoff = Mathf.Clamp01(
                Mathf.Log(cutoff / 20f) / Mathf.Log(18000f / 20f));
            DrawText(9, 77, "LOW PASS", color, 2);
            DrawText(151, 77, $"{Mathf.RoundToInt(cutoff)} HZ", color, 2);
            DrawLine(10, 17, 246, 17, dim);
            var previousX = 10;
            var previousY = 51;
            for (var x = 10; x <= 246; x++)
            {
                var position = (x - 10f) / 236f;
                var distance = position - normalizedCutoff;
                var rolloff = Mathf.Clamp01(0.5f + distance * 8f);
                var bump = Mathf.Exp(-distance * distance * 900f) *
                           resonance * 0.34f;
                var response = Mathf.Clamp01(1f - rolloff + bump);
                var y = 17 + Mathf.RoundToInt(response * 34f);
                if (x > 10)
                    DrawLine(previousX, previousY, x, y, color);
                previousX = x;
                previousY = y;
            }
            DrawHorizontalBar(10, 8, 236, normalizedCutoff, color, dim);
        }

        private void DrawEnvelope(Color32 color, Color32 dim)
        {
            var envelope = module?.Node as ModularEnvelopeNode;
            var attack = Mathf.Clamp(
                envelope?.AttackSeconds ?? 0.05f,
                0.001f,
                10f);
            var decay = Mathf.Clamp(
                envelope?.DecaySeconds ?? 0.2f,
                0.001f,
                10f);
            var sustain = Mathf.Clamp01(envelope?.SustainLevel ?? 0.7f);
            var release = Mathf.Clamp(
                envelope?.ReleaseSeconds ?? 0.35f,
                0.001f,
                10f);
            var level = Mathf.Clamp01(envelope?.CurrentLevel ?? 0f);
            var stage = envelope?.Stage ?? ModularEnvelopeStage.Idle;

            DrawText(9, 77, "ADSR", color, 2);
            DrawText(91, 77, stage.ToString().ToUpperInvariant(), color, 1);
            DrawText(201, 77, $"{Mathf.RoundToInt(level * 100f)}%", color, 1);

            var attackWeight = Mathf.Sqrt(attack);
            var decayWeight = Mathf.Sqrt(decay);
            var releaseWeight = Mathf.Sqrt(release);
            var weightTotal = attackWeight + decayWeight + releaseWeight;
            var attackWidth = 20 + Mathf.RoundToInt(
                120f * attackWeight / weightTotal);
            var decayWidth = 20 + Mathf.RoundToInt(
                120f * decayWeight / weightTotal);
            var releaseWidth = 20 + Mathf.RoundToInt(
                120f * releaseWeight / weightTotal);
            var attackX = 10 + attackWidth;
            var decayX = attackX + decayWidth;
            var releaseX = 246 - releaseWidth;
            var sustainY = 17 + Mathf.RoundToInt(34f * sustain);

            DrawLine(10, 17, attackX, 51, color);
            DrawLine(attackX, 51, decayX, sustainY, color);
            DrawLine(decayX, sustainY, releaseX, sustainY, dim);
            DrawLine(releaseX, sustainY, 246, 17, color);
            DrawHorizontalBar(10, 8, 236, level, color, dim);
        }

        private void DrawWaveform(
            int x,
            int y,
            int width,
            int height,
            ModularOscillatorWaveform waveform,
            float phaseOffset,
            Color32 color,
            Color32 dim,
            float cycleCount = 2f)
        {
            var center = y + height / 2;
            DrawLine(x, center, x + width, center, dim);
            var previousX = x;
            var previousY = center;
            for (var sample = 0; sample <= width; sample++)
            {
                var phase = Mathf.Repeat(
                    sample / (float)width * cycleCount + phaseOffset,
                    1f);
                var value = waveform switch
                {
                    ModularOscillatorWaveform.Triangle =>
                        1f - 4f * Mathf.Abs(phase - 0.5f),
                    ModularOscillatorWaveform.Saw => phase * 2f - 1f,
                    ModularOscillatorWaveform.Square => phase < 0.5f ? 1f : -1f,
                    _ => Mathf.Sin(phase * Mathf.PI * 2f)
                };
                var nextX = x + sample;
                var nextY = center + Mathf.RoundToInt(value * (height * 0.42f));
                if (sample > 0)
                    DrawLine(previousX, previousY, nextX, nextY, color);
                previousX = nextX;
                previousY = nextY;
            }
        }

        private float NormalizedValue()
        {
            return module?.Motion != null
                ? Mathf.Clamp01(module.Motion.NormalizedValue)
                : 0.5f;
        }

        private void EnsureTexture()
        {
            if (texture != null)
                return;
            texture = new Texture2D(
                TextureWidth,
                TextureHeight,
                TextureFormat.RGBA32,
                false)
            {
                name = $"AudioModuleDisplay_{GetInstanceID()}",
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0
            };
        }

        private void EnsureDisplayUv()
        {
            if (displayRenderer == null)
                return;
            var filter = displayRenderer.GetComponent<MeshFilter>();
            if (filter == null)
                return;
            var source = filter.sharedMesh;
            if (source == null || source.vertexCount == 0)
                return;
            var existing = source.uv;
            if (existing != null && existing.Length == source.vertexCount &&
                UvSpan(existing, horizontal: true) > 0.9f &&
                UvSpan(existing, horizontal: false) > 0.9f)
            {
                return;
            }

            var vertices = source.vertices;
            var bounds = source.bounds;
            var dimensions = new[]
            {
                (Axis: 0, Size: bounds.size.x),
                (Axis: 1, Size: bounds.size.y),
                (Axis: 2, Size: bounds.size.z)
            };
            Array.Sort(dimensions, (left, right) =>
                right.Size.CompareTo(left.Size));
            var widthAxis = dimensions[0].Axis;
            var heightAxis = dimensions[1].Axis;
            // The module faces local +Z. Viewed from that front side, screen
            // right is the module's local -X direction.
            var flipHorizontal = Vector3.Dot(
                displayRenderer.transform.TransformDirection(
                    AxisVector(widthAxis)),
                transform.right) > 0f;
            var flipVertical = Vector3.Dot(
                displayRenderer.transform.TransformDirection(
                    AxisVector(heightAxis)),
                transform.up) < 0f;
            var minimum = bounds.min;
            var size = bounds.size;
            var uv = new Vector2[vertices.Length];
            for (var index = 0; index < vertices.Length; index++)
            {
                var horizontal = NormalizeAxis(
                    vertices[index], minimum, size, widthAxis);
                var vertical = NormalizeAxis(
                    vertices[index], minimum, size, heightAxis);
                uv[index] = new Vector2(
                    flipHorizontal ? 1f - horizontal : horizontal,
                    flipVertical ? 1f - vertical : vertical);
            }

            generatedDisplayMesh = Instantiate(source);
            generatedDisplayMesh.name = $"{source.name}_RuntimeDisplayUv";
            generatedDisplayMesh.hideFlags = HideFlags.HideAndDontSave;
            generatedDisplayMesh.uv = uv;
            filter.sharedMesh = generatedDisplayMesh;
        }

        private static float UvSpan(IReadOnlyList<Vector2> uv, bool horizontal)
        {
            var minimum = float.PositiveInfinity;
            var maximum = float.NegativeInfinity;
            for (var index = 0; index < uv.Count; index++)
            {
                var value = horizontal ? uv[index].x : uv[index].y;
                minimum = Mathf.Min(minimum, value);
                maximum = Mathf.Max(maximum, value);
            }
            return maximum - minimum;
        }

        private static float NormalizeAxis(
            Vector3 value,
            Vector3 minimum,
            Vector3 size,
            int axis)
        {
            var denominator = Mathf.Max(size[axis], 0.000001f);
            return Mathf.Clamp01((value[axis] - minimum[axis]) / denominator);
        }

        private static Vector3 AxisVector(int axis)
        {
            return axis switch
            {
                0 => Vector3.right,
                1 => Vector3.up,
                _ => Vector3.forward
            };
        }

        private void ApplyTexture()
        {
            var block = new MaterialPropertyBlock();
            displayRenderer.GetPropertyBlock(block);
            block.SetTexture("_BaseMap", texture);
            block.SetTexture("_MainTex", texture);
            block.SetTexture("_EmissionMap", texture);
            block.SetColor("_BaseColor", Color.white);
            block.SetColor("_Color", Color.white);
            block.SetColor("_EmissionColor", Color.white);
            displayRenderer.SetPropertyBlock(block);
        }

        private void DrawFrame(Color32 color)
        {
            DrawOutline(3, 3, TextureWidth - 6, TextureHeight - 6, color);
            DrawLine(5, 70, TextureWidth - 6, 70, color);
        }

        private void DrawHorizontalBar(
            int x,
            int y,
            int width,
            float value,
            Color32 color,
            Color32 dim)
        {
            DrawRect(x, y, width, 3, dim);
            DrawRect(x, y, Mathf.RoundToInt(width * Mathf.Clamp01(value)), 3, color);
        }

        private void DrawText(
            int x,
            int top,
            string value,
            Color32 color,
            int scale)
        {
            if (string.IsNullOrEmpty(value))
                return;
            var cursor = x;
            foreach (var raw in value.ToUpperInvariant())
            {
                var character = Glyphs.ContainsKey(raw) ? raw : ' ';
                var glyph = Glyphs[character];
                for (var row = 0; row < glyph.Length; row++)
                {
                    for (var column = 0; column < glyph[row].Length; column++)
                    {
                        if (glyph[row][column] != '1')
                            continue;
                        DrawRect(
                            cursor + column * scale,
                            top - (row + 1) * scale,
                            scale,
                            scale,
                            color);
                    }
                }
                cursor += 4 * scale;
            }
        }

        private void DrawOutline(
            int x,
            int y,
            int width,
            int height,
            Color32 color)
        {
            DrawLine(x, y, x + width - 1, y, color);
            DrawLine(x, y + height - 1, x + width - 1, y + height - 1, color);
            DrawLine(x, y, x, y + height - 1, color);
            DrawLine(x + width - 1, y, x + width - 1, y + height - 1, color);
        }

        private void DrawRect(
            int x,
            int y,
            int width,
            int height,
            Color32 color)
        {
            for (var py = Mathf.Max(0, y);
                 py < Mathf.Min(TextureHeight, y + height);
                 py++)
            {
                var offset = py * TextureWidth;
                for (var px = Mathf.Max(0, x);
                     px < Mathf.Min(TextureWidth, x + width);
                     px++)
                {
                    pixels[offset + px] = color;
                }
            }
        }

        private void DrawLine(
            int x0,
            int y0,
            int x1,
            int y1,
            Color32 color)
        {
            var dx = Mathf.Abs(x1 - x0);
            var sx = x0 < x1 ? 1 : -1;
            var dy = -Mathf.Abs(y1 - y0);
            var sy = y0 < y1 ? 1 : -1;
            var error = dx + dy;
            while (true)
            {
                SetPixel(x0, y0, color);
                if (x0 == x1 && y0 == y1)
                    break;
                var twice = 2 * error;
                if (twice >= dy)
                {
                    error += dy;
                    x0 += sx;
                }
                if (twice <= dx)
                {
                    error += dx;
                    y0 += sy;
                }
            }
        }

        private void SetPixel(int x, int y, Color32 color)
        {
            if (x >= 0 && x < TextureWidth && y >= 0 && y < TextureHeight)
                pixels[y * TextureWidth + x] = color;
        }

        private void Clear(Color32 color)
        {
            Array.Fill(pixels, color);
        }

        private static string WaveformName(ModularOscillatorWaveform waveform)
        {
            return waveform switch
            {
                ModularOscillatorWaveform.Triangle => "TRI",
                ModularOscillatorWaveform.Saw => "SAW",
                ModularOscillatorWaveform.Square => "SQUARE",
                _ => "SINE"
            };
        }

        private static Color32 ForegroundColor(MockInstrumentTheme visualTheme)
        {
            return visualTheme switch
            {
                MockInstrumentTheme.ForgeBrass => new Color32(255, 170, 60, 255),
                MockInstrumentTheme.KineticSafety => new Color32(255, 104, 18, 255),
                MockInstrumentTheme.MachinedErgonomics => new Color32(92, 226, 255, 255),
                MockInstrumentTheme.Superfine => new Color32(42, 232, 255, 255),
                _ => new Color32(72, 230, 210, 255)
            };
        }

        private static Color32 DimColor(Color32 source)
        {
            return new Color32(
                (byte)(source.r / 4),
                (byte)(source.g / 4),
                (byte)(source.b / 4),
                255);
        }

        private static IReadOnlyDictionary<char, string[]> CreateGlyphs()
        {
            return new Dictionary<char, string[]>
            {
                [' '] = new[] { "000", "000", "000", "000", "000", "000", "000" },
                ['0'] = new[] { "111", "101", "101", "101", "101", "101", "111" },
                ['1'] = new[] { "010", "110", "010", "010", "010", "010", "111" },
                ['2'] = new[] { "111", "001", "001", "111", "100", "100", "111" },
                ['3'] = new[] { "111", "001", "001", "111", "001", "001", "111" },
                ['4'] = new[] { "101", "101", "101", "111", "001", "001", "001" },
                ['5'] = new[] { "111", "100", "100", "111", "001", "001", "111" },
                ['6'] = new[] { "111", "100", "100", "111", "101", "101", "111" },
                ['7'] = new[] { "111", "001", "001", "010", "010", "010", "010" },
                ['8'] = new[] { "111", "101", "101", "111", "101", "101", "111" },
                ['9'] = new[] { "111", "101", "101", "111", "001", "001", "111" },
                ['A'] = new[] { "010", "101", "101", "111", "101", "101", "101" },
                ['B'] = new[] { "110", "101", "101", "110", "101", "101", "110" },
                ['C'] = new[] { "111", "100", "100", "100", "100", "100", "111" },
                ['D'] = new[] { "110", "101", "101", "101", "101", "101", "110" },
                ['E'] = new[] { "111", "100", "100", "110", "100", "100", "111" },
                ['F'] = new[] { "111", "100", "100", "110", "100", "100", "100" },
                ['G'] = new[] { "111", "100", "100", "101", "101", "101", "111" },
                ['H'] = new[] { "101", "101", "101", "111", "101", "101", "101" },
                ['I'] = new[] { "111", "010", "010", "010", "010", "010", "111" },
                ['J'] = new[] { "001", "001", "001", "001", "101", "101", "111" },
                ['K'] = new[] { "101", "101", "110", "100", "110", "101", "101" },
                ['L'] = new[] { "100", "100", "100", "100", "100", "100", "111" },
                ['M'] = new[] { "101", "111", "111", "101", "101", "101", "101" },
                ['N'] = new[] { "101", "111", "111", "111", "111", "111", "101" },
                ['O'] = new[] { "111", "101", "101", "101", "101", "101", "111" },
                ['P'] = new[] { "111", "101", "101", "111", "100", "100", "100" },
                ['Q'] = new[] { "111", "101", "101", "101", "111", "001", "001" },
                ['R'] = new[] { "110", "101", "101", "110", "110", "101", "101" },
                ['S'] = new[] { "111", "100", "100", "111", "001", "001", "111" },
                ['T'] = new[] { "111", "010", "010", "010", "010", "010", "010" },
                ['U'] = new[] { "101", "101", "101", "101", "101", "101", "111" },
                ['V'] = new[] { "101", "101", "101", "101", "101", "101", "010" },
                ['W'] = new[] { "101", "101", "101", "101", "111", "111", "101" },
                ['X'] = new[] { "101", "101", "010", "010", "010", "101", "101" },
                ['Y'] = new[] { "101", "101", "101", "010", "010", "010", "010" },
                ['Z'] = new[] { "111", "001", "001", "010", "100", "100", "111" },
                ['.'] = new[] { "000", "000", "000", "000", "000", "010", "010" },
                ['-'] = new[] { "000", "000", "000", "111", "000", "000", "000" },
                ['%'] = new[] { "101", "001", "010", "010", "010", "100", "101" },
                ['/'] = new[] { "001", "001", "010", "010", "010", "100", "100" }
            };
        }

        private void OnDestroy()
        {
            DestroyRuntimeObject(texture);
            DestroyRuntimeObject(generatedDisplayMesh);
        }

        private static void DestroyRuntimeObject(UnityEngine.Object value)
        {
            if (value == null)
                return;
            if (Application.isPlaying)
                Destroy(value);
            else
                DestroyImmediate(value);
        }
    }
}
