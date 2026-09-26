using System;
using System.Collections.Generic;
using System.Linq;
using MatsuMotoMeterAR.Instruments;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class AudioModuleCandidateContractValidator
    {
        private const float DirectionTolerance = 0.995f;
        private static readonly string[] CommonNodes =
        {
            "housing",
            "faceplate",
            "display_bezel",
            "display_surface",
            "parameter_knob_pivot",
            "parameter_knob",
            "parameter_index"
        };

        internal static IReadOnlyList<string> Evaluate(
            GameObject root,
            MockInstrumentKind kind,
            bool requireSignalSurface = false)
        {
            var problems = new List<string>();
            if (root == null)
            {
                problems.Add("Audio module root is missing.");
                return problems;
            }

            // Unity absorbs the authored FBX scene root (`audio_module_root`)
            // into the imported model asset. The staging prefab wrapper is the
            // runtime-equivalent root, and must contain exactly one imported
            // model hierarchy.
            if (root.transform.childCount != 1)
            {
                problems.Add(
                    "Audio module staging root must contain exactly one " +
                    $"imported model root; actual={root.transform.childCount}.");
            }

            foreach (var node in CommonNodes)
                RequireExactlyOne(root.transform, node, problems);
            foreach (var port in ExpectedPorts(kind))
                RequireExactlyOne(root.transform, port, problems);

            var expectedPorts = new HashSet<string>(
                ExpectedPorts(kind),
                StringComparer.Ordinal);
            var actualPorts = root.GetComponentsInChildren<Transform>(true)
                .Where(item => item.name.StartsWith(
                    "port_",
                    StringComparison.Ordinal))
                .Select(item => item.name)
                .ToArray();
            foreach (var unexpected in actualPorts.Where(
                         item => !expectedPorts.Contains(item)))
            {
                problems.Add($"Unexpected audio port transform {unexpected}.");
            }

            var display = Find(root.transform, "display_surface");
            ValidateDisplay(display, root.transform, problems);
            var signalSurfaces = root.GetComponentsInChildren<Transform>(true)
                .Where(item => item.name == "signal_surface")
                .ToArray();
            if (requireSignalSurface && signalSurfaces.Length != 1)
            {
                problems.Add(
                    "Expected exactly one signal_surface; actual=" +
                    $"{signalSurfaces.Length}.");
            }
            if (signalSurfaces.Length == 1)
            {
                ValidateSignalSurface(
                    signalSurfaces[0],
                    display,
                    root.transform,
                    problems);
            }
            var pivot = Find(root.transform, "parameter_knob_pivot");
            var knob = Find(root.transform, "parameter_knob");
            var index = Find(root.transform, "parameter_index");
            if (pivot != null && knob != null && !knob.IsChildOf(pivot))
                problems.Add("parameter_knob must be below parameter_knob_pivot.");
            if (pivot != null && index != null && !index.IsChildOf(pivot))
                problems.Add("parameter_index must be below parameter_knob_pivot.");

            return problems;
        }

        private static void ValidateSignalSurface(
            Transform signal,
            Transform display,
            Transform root,
            ICollection<string> problems)
        {
            var filter = signal.GetComponent<MeshFilter>();
            var renderer = signal.GetComponent<Renderer>();
            var mesh = filter?.sharedMesh;
            if (mesh == null || renderer == null)
            {
                problems.Add(
                    "signal_surface must have one MeshFilter and Renderer.");
                return;
            }

            var displayRenderer = display?.GetComponent<Renderer>();
            if (displayRenderer == renderer)
            {
                problems.Add(
                    "signal_surface must use a Renderer separate from " +
                    "display_surface.");
            }
            if (renderer.sharedMaterial == null)
                problems.Add("signal_surface material is missing.");
            else if (displayRenderer?.sharedMaterial != renderer.sharedMaterial)
            {
                problems.Add(
                    "signal_surface and display_surface must share the " +
                    "EmissionDisplay material role.");
            }

            var vertices = mesh.vertices;
            var triangles = mesh.triangles;
            var usableTriangles = 0;
            var backFacingTriangles = 0;
            var minimumFacingDot = 1f;
            for (var index = 0; index + 2 < triangles.Length; index += 3)
            {
                var a = root.InverseTransformPoint(
                    signal.TransformPoint(vertices[triangles[index]]));
                var b = root.InverseTransformPoint(
                    signal.TransformPoint(vertices[triangles[index + 1]]));
                var c = root.InverseTransformPoint(
                    signal.TransformPoint(vertices[triangles[index + 2]]));
                var normal = Vector3.Cross(b - a, c - a);
                if (normal.sqrMagnitude <= 0.000000000001f)
                    continue;
                usableTriangles++;
                var facingDot = Vector3.Dot(
                    normal.normalized,
                    Vector3.forward);
                minimumFacingDot = Mathf.Min(minimumFacingDot, facingDot);
                if (facingDot < DirectionTolerance)
                    backFacingTriangles++;
            }
            if (usableTriangles == 0)
                problems.Add("signal_surface has no usable triangles.");
            else if (backFacingTriangles > 0)
            {
                problems.Add(
                    "signal_surface triangles must face module local +Z; " +
                    $"nonconforming={backFacingTriangles}/{usableTriangles}, " +
                    $"minimum dot={minimumFacingDot:0.####}.");
            }

            var uv = mesh.uv;
            if (uv == null || uv.Length != mesh.vertexCount)
            {
                problems.Add(
                    "signal_surface must provide finite UV0 for every vertex.");
                return;
            }
            var minimum = new Vector2(
                float.PositiveInfinity,
                float.PositiveInfinity);
            var maximum = new Vector2(
                float.NegativeInfinity,
                float.NegativeInfinity);
            foreach (var value in uv)
            {
                if (float.IsNaN(value.x) || float.IsInfinity(value.x) ||
                    float.IsNaN(value.y) || float.IsInfinity(value.y))
                {
                    problems.Add("signal_surface UV0 contains a non-finite value.");
                    return;
                }
                minimum = Vector2.Min(minimum, value);
                maximum = Vector2.Max(maximum, value);
            }
            var span = maximum - minimum;
            if (span.x < 0.9f || span.y < 0.9f)
            {
                problems.Add(
                    "signal_surface UV0 must span approximately 0..1 in U/V; " +
                    $"actual span=({span.x:0.###}, {span.y:0.###}).");
            }
        }

        private static void ValidateDisplay(
            Transform display,
            Transform root,
            ICollection<string> problems)
        {
            var filter = display?.GetComponent<MeshFilter>();
            var renderer = display?.GetComponent<Renderer>();
            var mesh = filter?.sharedMesh;
            if (mesh == null || renderer == null)
            {
                problems.Add(
                    "display_surface must have one MeshFilter and Renderer.");
                return;
            }
            if (mesh.triangles.Length != 6)
            {
                problems.Add(
                    $"display_surface must contain 2 triangles; actual=" +
                    $"{mesh.triangles.Length / 3}.");
            }
            if (renderer.sharedMaterial == null)
                problems.Add("display_surface material is missing.");
            var uv = mesh.uv;
            var hasRuntimeReadyUv = uv != null &&
                                    uv.Length == mesh.vertexCount &&
                                    UvSpan(uv, horizontal: true) > 0.9f &&
                                    UvSpan(uv, horizontal: false) > 0.9f;
            if (!hasRuntimeReadyUv && !mesh.isReadable)
            {
                problems.Add(
                    "display_surface without full UV0 must be readable for " +
                    "runtime UV generation.");
            }
            if (mesh.normals == null || mesh.normals.Length == 0)
            {
                problems.Add("display_surface normals are missing.");
                return;
            }
            foreach (var normal in mesh.normals)
            {
                var world = display.TransformDirection(normal).normalized;
                if (Vector3.Dot(world, root.forward) >= DirectionTolerance)
                    continue;
                problems.Add("display_surface normals must face module local +Z.");
                break;
            }
            var vertices = mesh.vertices;
            if (vertices == null || vertices.Length < 3)
            {
                problems.Add("display_surface vertices are missing.");
                return;
            }
            var first = display.TransformPoint(vertices[0]);
            for (var index = 1; index < vertices.Length; index++)
            {
                var local = root.InverseTransformPoint(
                    display.TransformPoint(vertices[index]));
                var reference = root.InverseTransformPoint(first);
                if (Mathf.Abs(local.z - reference.z) <= 0.00001f)
                    continue;
                problems.Add("display_surface must be coplanar in module Z.");
                break;
            }
        }

        private static float UvSpan(IReadOnlyList<Vector2> uv, bool horizontal)
        {
            var minimum = float.PositiveInfinity;
            var maximum = float.NegativeInfinity;
            foreach (var value in uv)
            {
                var coordinate = horizontal ? value.x : value.y;
                minimum = Mathf.Min(minimum, coordinate);
                maximum = Mathf.Max(maximum, coordinate);
            }
            return maximum - minimum;
        }

        private static void RequireExactlyOne(
            Transform root,
            string name,
            ICollection<string> problems)
        {
            var count = root.GetComponentsInChildren<Transform>(true)
                .Count(item => item.name == name);
            if (count != 1)
                problems.Add($"Expected exactly one {name}; actual={count}.");
        }

        private static Transform Find(Transform root, string name)
        {
            return root.GetComponentsInChildren<Transform>(true)
                .FirstOrDefault(item => item.name == name);
        }

        private static IReadOnlyList<string> ExpectedPorts(
            MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.AudioOscillator => new[]
                {
                    "port_pitch_in", "port_gate_in", "port_fm_in",
                    "port_audio_out"
                },
                MockInstrumentKind.AudioNoise => new[]
                {
                    "port_gate_in", "port_audio_out"
                },
                MockInstrumentKind.AudioLfo => new[]
                {
                    "port_rate_in", "port_reset_in", "port_control_out",
                    "port_clock_out", "port_gate_out", "port_trigger_out",
                    "port_audio_out"
                },
                MockInstrumentKind.AudioSequencer => new[]
                {
                    "port_clock_in", "port_trigger_in", "port_control_out",
                    "port_gate_out", "port_trigger_out"
                },
                MockInstrumentKind.AudioDelay => new[]
                {
                    "port_audio_in", "port_time_in", "port_audio_out"
                },
                MockInstrumentKind.AudioOutput => new[] { "port_audio_in" },
                MockInstrumentKind.AudioVca => new[]
                {
                    "port_audio_in", "port_level_in", "port_audio_out"
                },
                MockInstrumentKind.AudioMixer => new[]
                {
                    "port_audio_in", "port_audio_out"
                },
                MockInstrumentKind.AudioFilter => new[]
                {
                    "port_audio_in", "port_cutoff_in", "port_audio_out"
                },
                MockInstrumentKind.AudioEnvelope => new[]
                {
                    "port_gate_in", "port_trigger_in", "port_control_out"
                },
                _ => Array.Empty<string>()
            };
        }
    }
}
