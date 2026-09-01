using System.Linq;
using MatsuMotoMeterAR.Editor;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class WindowPanelCandidateContractValidatorTests
    {
        [Test]
        public void Evaluate_AcceptsTwoTriangleForwardDisplay()
        {
            var root = BuildCandidate();
            try
            {
                Assert.That(
                    WindowPanelCandidateContractValidator.Evaluate(root),
                    Is.Empty);
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void Evaluate_RejectsLegacyVaneAndBackwardDisplay()
        {
            var root = BuildCandidate(backward: true);
            new GameObject("vane_pivot").transform.SetParent(
                root.transform,
                false);
            try
            {
                var problems =
                    WindowPanelCandidateContractValidator.Evaluate(root);
                Assert.That(
                    problems.Any(problem => problem.Contains("vane_pivot")),
                    Is.True);
                Assert.That(
                    problems.Any(problem => problem.Contains("local +Z")),
                    Is.True);
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void Evaluate_RejectsDuplicateDisplaySurface()
        {
            var root = BuildCandidate();
            new GameObject("display_surface").transform.SetParent(
                root.transform,
                false);
            try
            {
                Assert.That(
                    WindowPanelCandidateContractValidator.Evaluate(root),
                    Has.Some.Contains("exactly one"));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        private static GameObject BuildCandidate(bool backward = false)
        {
            var root = new GameObject("WindowPanelCandidate");
            var display = new GameObject(
                "display_surface",
                typeof(MeshFilter),
                typeof(MeshRenderer));
            display.transform.SetParent(root.transform, false);

            var mesh = new Mesh { name = "display_surface" };
            mesh.vertices = new[]
            {
                new Vector3(-1f, -0.55f, 0f),
                new Vector3(1f, -0.55f, 0f),
                new Vector3(1f, 0.55f, 0f),
                new Vector3(-1f, 0.55f, 0f)
            };
            mesh.triangles = backward
                ? new[] { 0, 2, 1, 0, 3, 2 }
                : new[] { 0, 1, 2, 0, 2, 3 };
            mesh.RecalculateNormals();
            display.GetComponent<MeshFilter>().sharedMesh = mesh;
            return root;
        }
    }
}
