using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using MatsuMotoMeterAR.Audio;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Signals;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class SuperfineDisplayGeometryAudit
    {
        private const string ReportPath =
            "Builds/Reports/superfine-display-geometry-audit.md";

        private static readonly MockInstrumentKind[] Kinds =
        {
            MockInstrumentKind.WindowPanel,
            MockInstrumentKind.AudioOscillator,
            MockInstrumentKind.AudioNoise,
            MockInstrumentKind.AudioLfo,
            MockInstrumentKind.AudioSequencer,
            MockInstrumentKind.AudioDelay,
            MockInstrumentKind.AudioVca,
            MockInstrumentKind.AudioMixer,
            MockInstrumentKind.AudioFilter,
            MockInstrumentKind.AudioEnvelope,
            MockInstrumentKind.AudioOutput
        };

        public static void Run()
        {
            var lines = new List<string>
            {
                "# Superfine display geometry audit",
                "",
                "Generated from production Resources prefabs. Coordinates " +
                "are prefab-root local metres; +Z is the contracted front.",
                "",
                "| Theme / Kind | plane Z | size XY | mesh local XYZ | " +
                "node rotation XYZ | triangle front dot | UV span | " +
                "determinant | material | overlapping geometry in front |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---|---|"
            };

            foreach (var theme in new[]
                     {
                         MockInstrumentTheme.ForgeBrass,
                         MockInstrumentTheme.Superfine
                     })
            {
                foreach (var kind in Kinds)
                    Append(lines, theme, kind);
            }

            lines.Add("");
            lines.Add("## Runtime Window Panel attachment");
            lines.Add("");
            lines.Add("| Theme | display center | graphic position | " +
                      "graphic scale | graphic bounds | forward dot | material |");
            lines.Add("|---|---:|---:|---:|---:|---:|---|");
            AppendWindowRuntime(lines, MockInstrumentTheme.ForgeBrass);
            AppendWindowRuntime(lines, MockInstrumentTheme.Superfine);

            Directory.CreateDirectory(Path.GetDirectoryName(ReportPath));
            File.WriteAllLines(ReportPath, lines);
            AssetDatabase.Refresh();
            Debug.Log($"Superfine display audit written: {ReportPath}");
        }

        private static void AppendWindowRuntime(
            ICollection<string> lines,
            MockInstrumentTheme theme)
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.WindowPanel,
                Pose.identity,
                theme: theme);
            try
            {
                var visual = root.GetComponent<InstrumentGreyboxContract>()
                    .VisualSocket.GetChild(0);
                var manifest = visual.GetComponent<ThemeVisualManifest>();
                var display = manifest.MotionTarget;
                var displayMesh = display.GetComponent<MeshFilter>().sharedMesh;
                var displayCenter = display.TransformPoint(
                    displayMesh.bounds.center);
                var view = visual.GetComponentInChildren<
                    WindowPanelGraphicsPrototypeView>(true);
                var renderer = view.GetComponent<MeshRenderer>();
                var bounds = renderer.bounds;
                lines.Add(
                    $"| {theme} | {Vector(displayCenter)} | " +
                    $"{Vector(view.transform.position)} | " +
                    $"{Vector(view.transform.lossyScale)} | " +
                    $"{Vector(bounds.size)} | " +
                    $"{F(Vector3.Dot(view.transform.forward, visual.forward))} | " +
                    $"{renderer.sharedMaterial?.name ?? "missing"} |");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        public static void RenderRuntimeComparison()
        {
            Directory.CreateDirectory("Builds/Reports");
            foreach (var theme in new[]
                     {
                         MockInstrumentTheme.ForgeBrass,
                         MockInstrumentTheme.Superfine
                     })
            {
                foreach (var kind in new[]
                         {
                             MockInstrumentKind.WindowPanel,
                             MockInstrumentKind.AudioVca
                         })
                {
                    Render(theme, kind);
                }
            }
            foreach (var kind in new[]
                     {
                         MockInstrumentKind.WindowPanel,
                         MockInstrumentKind.AudioVca
                     })
            {
                RenderThemeSwitch(kind);
            }
            Debug.Log("Superfine runtime display comparisons rendered.");
        }

        private static void RenderThemeSwitch(MockInstrumentKind kind)
        {
            Render(
                MockInstrumentTheme.ForgeBrass,
                kind,
                switchTo: MockInstrumentTheme.Superfine);
        }

        private static void Render(
            MockInstrumentTheme theme,
            MockInstrumentKind kind,
            MockInstrumentTheme? switchTo = null)
        {
            var root = MockInstrumentFactory.Create(
                kind,
                Pose.identity,
                theme: theme);
            var cameraObject = new GameObject("Display Audit Camera");
            var lightObject = new GameObject("Display Audit Light");
            var target = new RenderTexture(640, 480, 24,
                RenderTextureFormat.ARGB32);
            var previous = RenderTexture.active;
            try
            {
                if (switchTo.HasValue)
                {
                    MockInstrumentFactory.ApplyTheme(
                        root,
                        switchTo.Value);
                }
                root.GetComponentInChildren<AudioModuleDisplayView>(true)
                    ?.RedrawNow();
                root.GetComponentInChildren<WindowPanelGraphicsPrototypeView>(true)
                    ?.ApplyNow();

                var bounds = CombinedBounds(root);
                var camera = cameraObject.AddComponent<Camera>();
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = new Color(0.02f, 0.02f, 0.025f, 1f);
                camera.orthographic = true;
                camera.orthographicSize = Mathf.Max(
                    bounds.extents.y * 1.25f,
                    bounds.extents.x * 1.25f * 480f / 640f);
                camera.nearClipPlane = 0.01f;
                camera.farClipPlane = 10f;
                camera.transform.position = bounds.center +
                                            Vector3.forward * 2f;
                camera.transform.rotation = Quaternion.Euler(0f, 180f, 0f);
                camera.targetTexture = target;

                var light = lightObject.AddComponent<Light>();
                light.type = LightType.Directional;
                light.intensity = 1.2f;
                light.transform.rotation = Quaternion.Euler(25f, 155f, 0f);

                camera.Render();
                RenderTexture.active = target;
                var texture = new Texture2D(
                    target.width,
                    target.height,
                    TextureFormat.RGBA32,
                    false);
                texture.ReadPixels(
                    new Rect(0f, 0f, target.width, target.height),
                    0,
                    0);
                texture.Apply();
                var themeLabel = switchTo.HasValue
                    ? $"{theme}-to-{switchTo.Value}"
                    : theme.ToString();
                var path = $"Builds/Reports/superfine-display-runtime-" +
                           $"{themeLabel}-{kind}.png";
                File.WriteAllBytes(path, texture.EncodeToPNG());
                UnityEngine.Object.DestroyImmediate(texture);
            }
            finally
            {
                RenderTexture.active = previous;
                target.Release();
                UnityEngine.Object.DestroyImmediate(target);
                UnityEngine.Object.DestroyImmediate(cameraObject);
                UnityEngine.Object.DestroyImmediate(lightObject);
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static Bounds CombinedBounds(GameObject root)
        {
            var renderers = root.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0)
                return new Bounds(Vector3.zero, Vector3.one);
            var bounds = renderers[0].bounds;
            for (var index = 1; index < renderers.Length; index++)
                bounds.Encapsulate(renderers[index].bounds);
            return bounds;
        }

        private static void Append(
            ICollection<string> lines,
            MockInstrumentTheme theme,
            MockInstrumentKind kind)
        {
            var key = PrefabKey(kind);
            var path = $"{ThemeFolder(theme)}/Prefabs/" +
                       $"PF_Visual_{key}_{ThemeFolder(theme)}";
            var prefab = Resources.Load<GameObject>(path);
            if (prefab == null)
            {
                lines.Add($"| {theme} / {kind} | N/A | N/A | N/A | N/A | " +
                          $"N/A | N/A | N/A | missing prefab | N/A |");
                return;
            }

            var instance = UnityEngine.Object.Instantiate(prefab);
            try
            {
                var root = instance.transform;
                var display = Find(root, "display_surface");
                var filter = display?.GetComponent<MeshFilter>();
                var renderer = display?.GetComponent<Renderer>();
                var mesh = filter?.sharedMesh;
                if (display == null || mesh == null || renderer == null)
                {
                    lines.Add($"| {theme} / {kind} | N/A | N/A | N/A | N/A | " +
                              $"N/A | N/A | N/A | missing display_surface | N/A |");
                    return;
                }

                var vertices = mesh.vertices
                    .Select(vertex => root.InverseTransformPoint(
                        display.TransformPoint(vertex)))
                    .ToArray();
                var minimum = vertices.Aggregate(Vector3.Min);
                var maximum = vertices.Aggregate(Vector3.Max);
                var centerZ = (minimum.z + maximum.z) * 0.5f;
                var triangles = mesh.triangles;
                var minimumFrontDot = 1f;
                for (var index = 0; index + 2 < triangles.Length; index += 3)
                {
                    var a = vertices[triangles[index]];
                    var b = vertices[triangles[index + 1]];
                    var c = vertices[triangles[index + 2]];
                    var normal = Vector3.Cross(b - a, c - a).normalized;
                    minimumFrontDot = Mathf.Min(
                        minimumFrontDot,
                        Vector3.Dot(normal, Vector3.forward));
                }

                var uv = mesh.uv;
                var uvText = uv != null && uv.Length == mesh.vertexCount
                    ? $"{Span(uv, true):0.###} × {Span(uv, false):0.###}"
                    : $"missing ({uv?.Length ?? 0}/{mesh.vertexCount})";
                var right = root.InverseTransformVector(
                    display.TransformVector(Vector3.right));
                var up = root.InverseTransformVector(
                    display.TransformVector(Vector3.up));
                var forward = root.InverseTransformVector(
                    display.TransformVector(Vector3.forward));
                var determinant = Vector3.Dot(Vector3.Cross(right, up), forward);
                var material = renderer.sharedMaterial;
                var materialText = material == null
                    ? "missing"
                    : $"{material.name} / {material.shader?.name ?? "no shader"}";
                var blockers = FindPotentialBlockers(
                    root,
                    display,
                    minimum,
                    maximum,
                    centerZ);

                lines.Add(
                    $"| {theme} / {kind} | {F(centerZ)} | " +
                    $"{F(maximum.x - minimum.x)} × {F(maximum.y - minimum.y)} | " +
                    $"{Vector(mesh.bounds.size)} | " +
                    $"{Vector(display.localEulerAngles)} | " +
                    $"{F(minimumFrontDot)} | {uvText} | {F(determinant)} | " +
                    $"{materialText} | {blockers} |");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static string FindPotentialBlockers(
            Transform root,
            Transform display,
            Vector3 displayMinimum,
            Vector3 displayMaximum,
            float displayZ)
        {
            var blockers = new List<string>();
            var samples = new List<Vector2>();
            foreach (var horizontal in new[] { 0.2f, 0.5f, 0.8f })
            {
                foreach (var vertical in new[] { 0.2f, 0.5f, 0.8f })
                {
                    samples.Add(new Vector2(
                        Mathf.Lerp(displayMinimum.x, displayMaximum.x, horizontal),
                        Mathf.Lerp(displayMinimum.y, displayMaximum.y, vertical)));
                }
            }
            foreach (var filter in root.GetComponentsInChildren<MeshFilter>(true))
            {
                if (filter.transform == display || filter.sharedMesh == null)
                    continue;
                var vertices = filter.sharedMesh.vertices;
                if (vertices == null || vertices.Length == 0)
                    continue;
                var localVertices = new Vector3[vertices.Length];
                for (var index = 0; index < vertices.Length; index++)
                {
                    localVertices[index] = root.InverseTransformPoint(
                        filter.transform.TransformPoint(vertices[index]));
                }
                var covered = 0;
                var maximumDepth = 0f;
                foreach (var sample in samples)
                {
                    if (!TryFindFrontDepth(
                            localVertices,
                            filter.sharedMesh.triangles,
                            sample,
                            displayZ,
                            out var depth))
                    {
                        continue;
                    }
                    covered++;
                    maximumDepth = Mathf.Max(maximumDepth, depth);
                }
                if (covered > 0)
                    blockers.Add(
                        $"{filter.name}: {covered}/{samples.Count} samples, " +
                        $"+{F(maximumDepth)} m");
            }
            return blockers.Count == 0
                ? "none"
                : string.Join("; ", blockers);
        }

        private static bool TryFindFrontDepth(
            IReadOnlyList<Vector3> vertices,
            IReadOnlyList<int> triangles,
            Vector2 point,
            float displayZ,
            out float maximumDepth)
        {
            maximumDepth = 0f;
            var hit = false;
            for (var index = 0; index + 2 < triangles.Count; index += 3)
            {
                var a = vertices[triangles[index]];
                var b = vertices[triangles[index + 1]];
                var c = vertices[triangles[index + 2]];
                var denominator =
                    (b.y - c.y) * (a.x - c.x) +
                    (c.x - b.x) * (a.y - c.y);
                if (Mathf.Abs(denominator) <= 0.0000001f)
                    continue;
                var first =
                    ((b.y - c.y) * (point.x - c.x) +
                     (c.x - b.x) * (point.y - c.y)) / denominator;
                var second =
                    ((c.y - a.y) * (point.x - c.x) +
                     (a.x - c.x) * (point.y - c.y)) / denominator;
                var third = 1f - first - second;
                if (first < -0.0001f || second < -0.0001f ||
                    third < -0.0001f)
                {
                    continue;
                }
                var z = first * a.z + second * b.z + third * c.z;
                var depth = z - displayZ;
                if (depth <= 0.0001f)
                    continue;
                hit = true;
                maximumDepth = Mathf.Max(maximumDepth, depth);
            }
            return hit;
        }

        private static Transform Find(Transform root, string name)
        {
            foreach (var candidate in root.GetComponentsInChildren<Transform>(true))
            {
                if (candidate.name == name)
                    return candidate;
            }
            return null;
        }

        private static float Span(IReadOnlyList<Vector2> uv, bool horizontal)
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

        private static string F(float value) =>
            value.ToString("0.######", CultureInfo.InvariantCulture);

        private static string Vector(Vector3 value) =>
            $"({F(value.x)}, {F(value.y)}, {F(value.z)})";

        private static string ThemeFolder(MockInstrumentTheme theme) =>
            theme == MockInstrumentTheme.ForgeBrass
                ? "ForgeBrass"
                : "Superfine";

        private static string PrefabKey(MockInstrumentKind kind) => kind switch
        {
            MockInstrumentKind.WindowPanel => "WindowPanel",
            MockInstrumentKind.AudioOscillator => "AudioOscillator",
            MockInstrumentKind.AudioNoise => "AudioNoise",
            MockInstrumentKind.AudioLfo => "AudioLFO",
            MockInstrumentKind.AudioSequencer => "AudioSequencer",
            MockInstrumentKind.AudioDelay => "AudioDelay",
            MockInstrumentKind.AudioVca => "AudioVca",
            MockInstrumentKind.AudioMixer => "AudioMixer",
            MockInstrumentKind.AudioFilter => "AudioFilter",
            MockInstrumentKind.AudioEnvelope => "AudioEnvelope",
            MockInstrumentKind.AudioOutput => "AudioOutput",
            _ => throw new ArgumentOutOfRangeException(nameof(kind), kind, null)
        };
    }
}
