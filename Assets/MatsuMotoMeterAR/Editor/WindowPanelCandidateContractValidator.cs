using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class WindowPanelCandidateContractValidator
    {
        private const int TriangleBudget = 8000;
        private const float AxisTolerance = 0.999f;
        private const float PlaneTolerance = 0.00001f;

        private static readonly HashSet<string> ForbiddenLegacyNodes = new(
            new[]
            {
                "vane", "vane_pivot", "needle", "needle_pivot",
                "scale", "ticks", "tick_marks"
            },
            StringComparer.OrdinalIgnoreCase);

        public static IReadOnlyList<string> Evaluate(GameObject root)
        {
            var problems = new List<string>();
            if (root == null)
            {
                problems.Add("Window Panel candidate root is missing.");
                return problems;
            }

            var transforms = root.GetComponentsInChildren<Transform>(true);
            var displays = transforms
                .Where(item => item.name == "display_surface")
                .ToArray();
            if (displays.Length != 1)
            {
                problems.Add(
                    "Window Panel candidate must contain exactly one " +
                    $"display_surface; actual={displays.Length}.");
                return problems;
            }

            foreach (var transform in transforms)
            {
                if (ForbiddenLegacyNodes.Contains(transform.name))
                {
                    problems.Add(
                        $"Legacy analog node is forbidden: {transform.name}.");
                }
            }

            ValidateDisplay(root.transform, displays[0], problems);

            var triangles = root.GetComponentsInChildren<MeshFilter>(true)
                .Where(filter => filter.sharedMesh != null)
                .Sum(filter => filter.sharedMesh.triangles.Length / 3);
            if (triangles > TriangleBudget)
            {
                problems.Add(
                    $"Window Panel triangles {triangles} exceed budget " +
                    $"{TriangleBudget}.");
            }

            return problems;
        }

        private static void ValidateDisplay(
            Transform root,
            Transform display,
            ICollection<string> problems)
        {
            var filter = display.GetComponent<MeshFilter>();
            var renderer = display.GetComponent<MeshRenderer>();
            var mesh = filter?.sharedMesh;
            if (mesh == null || renderer == null)
            {
                problems.Add(
                    "display_surface must have one MeshFilter and " +
                    "MeshRenderer.");
                return;
            }

            var triangleCount = mesh.triangles.Length / 3;
            if (triangleCount != 2)
            {
                problems.Add(
                    "display_surface must be a 2-triangle plane; " +
                    $"actual={triangleCount}.");
            }

            var localSize = mesh.bounds.size;
            if (localSize.x <= PlaneTolerance ||
                localSize.y <= PlaneTolerance ||
                localSize.z > PlaneTolerance)
            {
                problems.Add(
                    "display_surface mesh data must lie in its local XY " +
                    "plane with non-zero X/Y and zero Z extent; " +
                    $"actual=({localSize.x:0.######}, " +
                    $"{localSize.y:0.######}, {localSize.z:0.######}).");
            }

            var rootUp = DisplayUvUpDirection(root, display, mesh);
            if (Vector3.Dot(rootUp, Vector3.up) < AxisTolerance)
            {
                problems.Add("display_surface up axis must be instrument local +Y.");
            }

            var vertices = mesh.vertices
                .Select(vertex => root.InverseTransformPoint(
                    display.TransformPoint(vertex)))
                .ToArray();
            if (vertices.Length == 0)
            {
                problems.Add("display_surface mesh has no vertices.");
                return;
            }
            if (vertices.Max(vertex => vertex.z) -
                vertices.Min(vertex => vertex.z) > PlaneTolerance)
            {
                problems.Add("display_surface vertices must be coplanar in local Z.");
            }

            var triangles = mesh.triangles;
            for (var index = 0; index + 2 < triangles.Length; index += 3)
            {
                var a = vertices[triangles[index]];
                var b = vertices[triangles[index + 1]];
                var c = vertices[triangles[index + 2]];
                var normal = Vector3.Cross(b - a, c - a).normalized;
                if (Vector3.Dot(normal, Vector3.forward) >= AxisTolerance)
                    continue;
                problems.Add(
                    "display_surface triangle normals must face instrument " +
                    "local +Z.");
                break;
            }
        }

        private static Vector3 DisplayUvUpDirection(
            Transform root,
            Transform display,
            Mesh mesh)
        {
            var vertices = mesh.vertices;
            var uv = mesh.uv;
            var triangles = mesh.triangles;
            for (var index = 0; index + 2 < triangles.Length; index += 3)
            {
                var first = triangles[index];
                var second = triangles[index + 1];
                var third = triangles[index + 2];
                if (first >= uv.Length || second >= uv.Length || third >= uv.Length)
                    continue;
                var edge1 = vertices[second] - vertices[first];
                var edge2 = vertices[third] - vertices[first];
                var delta1 = uv[second] - uv[first];
                var delta2 = uv[third] - uv[first];
                var determinant =
                    delta1.x * delta2.y - delta1.y * delta2.x;
                if (Mathf.Abs(determinant) < 0.000001f)
                    continue;
                var localUp =
                    (-delta2.x * edge1 + delta1.x * edge2) /
                    determinant;
                var worldUp = display.TransformDirection(localUp);
                if (worldUp.sqrMagnitude < 0.000001f)
                    continue;
                return root.InverseTransformDirection(worldUp).normalized;
            }
            return root.InverseTransformDirection(display.up).normalized;
        }
    }
}
