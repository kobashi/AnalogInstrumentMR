using System;
using System.Reflection;
using MatsuMotoMeterAR.Signals;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class WindowPanelGraphicPrototypeTests
    {
        [TestCase(WindowPanelGraphicPreset.Orbit)]
        [TestCase(WindowPanelGraphicPreset.Rose)]
        [TestCase(WindowPanelGraphicPreset.Lissajous)]
        public void Geometry_StaysFiniteClosedAndWithinDisplay(
            WindowPanelGraphicPreset preset)
        {
            foreach (var value in new[] { 0f, 0.5f, 1f })
            {
                var inputs = Resolve(value, value, value, value);
                for (var contour = 0; contour < 2; contour++)
                {
                    var first = WindowPanelGraphicGeometry.Evaluate(
                        preset, inputs, 0f, contour);
                    var closed = WindowPanelGraphicGeometry.Evaluate(
                        preset, inputs, 1f, contour);
                    Assert.That(Vector2.Distance(first, closed),
                        Is.LessThan(0.00001f));
                    for (var sample = 0; sample < 64; sample++)
                    {
                        var point = WindowPanelGraphicGeometry.Evaluate(
                            preset,
                            inputs,
                            sample / 64f,
                            contour);
                        Assert.That(float.IsFinite(point.x), Is.True);
                        Assert.That(float.IsFinite(point.y), Is.True);
                        Assert.That(Mathf.Abs(point.x), Is.LessThanOrEqualTo(1f));
                        Assert.That(Mathf.Abs(point.y), Is.LessThanOrEqualTo(0.55f));
                    }
                }
            }
        }

        [Test]
        public void Ribbon_UsesFixedQuestBudget()
        {
            var vertices = new Vector3[
                WindowPanelGraphicGeometry.VertexCapacity];
            var indices = new int[
                WindowPanelGraphicGeometry.IndexCapacity];

            WindowPanelGraphicGeometry.BuildRibbon(
                WindowPanelGraphicPreset.Rose,
                Resolve(1f, 1f, 1f, 1f),
                vertices,
                indices,
                out var vertexCount,
                out var indexCount,
                out var bounds);

            Assert.That(vertexCount, Is.EqualTo(256));
            Assert.That(indexCount, Is.EqualTo(768));
            Assert.That(bounds.min.x, Is.GreaterThanOrEqualTo(-1f));
            Assert.That(bounds.max.x, Is.LessThanOrEqualTo(1f));
            Assert.That(bounds.min.y, Is.GreaterThanOrEqualTo(-0.55f));
            Assert.That(bounds.max.y, Is.LessThanOrEqualTo(0.55f));
        }

        [Test]
        public void Ribbon_UsesUnityFrontFaceWindingForPositiveZDisplay()
        {
            var vertices = new Vector3[
                WindowPanelGraphicGeometry.VertexCapacity];
            var indices = new int[
                WindowPanelGraphicGeometry.IndexCapacity];

            WindowPanelGraphicGeometry.BuildRibbon(
                WindowPanelGraphicPreset.Orbit,
                Resolve(0.8f, 0.5f, 0.62f, 0.45f),
                vertices,
                indices,
                out _,
                out var indexCount,
                out _);

            for (var index = 0; index < indexCount; index += 3)
            {
                var a = vertices[indices[index]];
                var b = vertices[indices[index + 1]];
                var c = vertices[indices[index + 2]];
                var signedArea = Vector3.Cross(b - a, c - a).z;
                // Unity renders clockwise triangles as front faces. From
                // instrument local +Z this corresponds to a negative signed
                // XY area for this display-space mesh.
                Assert.That(signedArea, Is.LessThan(0f),
                    $"Triangle {index / 3} must face the local +Z viewer.");
            }
        }

        [Test]
        public void Orbit_PhaseRotationNeverCollapsesToLine()
        {
            var vertices = new Vector3[256];
            var indices = new int[768];
            foreach (var phase in new[] { 0f, 0.25f, 0.5f, 0.75f, 1f })
            {
                WindowPanelGraphicGeometry.BuildRibbon(
                    WindowPanelGraphicPreset.Orbit,
                    Resolve(0.8f, 0.5f, phase, 0.8f),
                    vertices,
                    indices,
                    out _, out _, out var bounds);
                Assert.That(bounds.size.x, Is.GreaterThan(0.25f));
                Assert.That(bounds.size.y, Is.GreaterThan(0.20f));
            }
        }

        [Test]
        public void Inputs_UseNeutralForMissingAndInvalidSlots()
        {
            var values = new[] { 1f, float.NaN, 1f, 1f };
            var connected = new[] { true, true, false, false };
            var resolved = new float[4];

            var inputs = WindowPanelGraphicGeometry.ResolveInputs(
                values, connected, resolved);

            Assert.That(inputs.ConnectedCount, Is.EqualTo(2));
            Assert.That(inputs.HasInvalidInput, Is.True);
            Assert.That(inputs.Energy, Is.EqualTo(0.95f).Within(0.0001f));
            Assert.That(inputs.Balance, Is.EqualTo(1f).Within(0.0001f));
            Assert.That(inputs.Phase, Is.Zero.Within(0.0001f));
            Assert.That(inputs.Detail, Is.Zero.Within(0.0001f));
        }

        [Test]
        public void GeometryBuild_DoesNotAllocateAfterWarmup()
        {
            var vertices = new Vector3[256];
            var indices = new int[768];
            var inputs = Resolve(0.7f, 0.2f, 0.8f, 0.6f);
            WindowPanelGraphicGeometry.BuildRibbon(
                WindowPanelGraphicPreset.Lissajous,
                inputs,
                vertices,
                indices,
                out _, out _, out _);

            var before = GC.GetAllocatedBytesForCurrentThread();
            for (var index = 0; index < 100; index++)
            {
                WindowPanelGraphicGeometry.BuildRibbon(
                    WindowPanelGraphicPreset.Lissajous,
                    inputs,
                    vertices,
                    indices,
                    out _, out _, out _);
            }
            var after = GC.GetAllocatedBytesForCurrentThread();

            Assert.That(after - before, Is.Zero);
        }

        [Test]
        public void PrototypeView_UsesOneRendererAndOneSharedMaterial()
        {
            var root = new GameObject("WP1 Test Root");
            try
            {
                var view = WindowPanelGraphicsPrototypeView.Create(
                    root.transform);
                view.SetPreset(WindowPanelGraphicPreset.Rose);
                for (var slot = 0; slot < 4; slot++)
                    view.SetSlot(slot, 0.5f, true);
                view.ApplyNow();

                var renderers = root.GetComponentsInChildren<MeshRenderer>(true);
                Assert.That(renderers, Has.Length.EqualTo(1));
                Assert.That(renderers[0].sharedMaterials,
                    Has.Length.EqualTo(1));
                Assert.That(renderers[0].sharedMaterial, Is.Not.Null);
                Assert.That(view.RuntimeMesh.vertexCount, Is.EqualTo(256));
                Assert.That(view.RuntimeMesh.GetIndexCount(0),
                    Is.EqualTo(768));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void CandidateDisplayAttachment_FitsInsideSurfaceAndFacesFront()
        {
            var root = new GameObject("Window Panel Candidate Root");
            var display = new GameObject("display_surface");
            var mesh = new Mesh();
            try
            {
                display.transform.SetParent(root.transform, false);
                display.transform.localPosition =
                    new Vector3(0f, 0f, 0.06f);
                mesh.vertices = new[]
                {
                    new Vector3(-0.65f, -0.30f, 0f),
                    new Vector3(0.65f, -0.30f, 0f),
                    new Vector3(-0.65f, 0.30f, 0f),
                    new Vector3(0.65f, 0.30f, 0f)
                };
                mesh.triangles = new[] { 0, 1, 2, 1, 3, 2 };
                mesh.RecalculateBounds();
                display.AddComponent<MeshFilter>().sharedMesh = mesh;
                display.AddComponent<MeshRenderer>();

                var factoryType = typeof(WindowPanelGraphicGeometry).Assembly
                    .GetType(
                        "MatsuMotoMeterAR.Instruments." +
                        "InstrumentThemeVisualFactory",
                        throwOnError: true);
                var attach = factoryType.GetMethod(
                    "AttachWindowPanelGraphic",
                    BindingFlags.Static | BindingFlags.NonPublic);
                Assert.That(attach, Is.Not.Null);
                var view = (WindowPanelGraphicsPrototypeView)attach.Invoke(
                    null,
                    new object[] { root.transform, display.transform });

                Assert.That(view, Is.Not.Null);
                Assert.That(
                    Vector3.Dot(
                        view.transform.position - display.transform.position,
                        root.transform.forward),
                    Is.EqualTo(0.002f).Within(0.00001f));
                Assert.That(
                    Vector3.Dot(view.transform.forward, root.transform.forward),
                    Is.LessThan(-0.999f));
                var graphicBounds = view.GetComponent<MeshRenderer>().bounds;
                Assert.That(graphicBounds.size.x, Is.LessThan(1.30f * 0.95f));
                Assert.That(graphicBounds.size.y, Is.LessThan(0.60f * 0.95f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
                UnityEngine.Object.DestroyImmediate(mesh);
            }
        }

        private static WindowPanelGraphicInputs Resolve(
            float energy,
            float balance,
            float phase,
            float detail)
        {
            return WindowPanelGraphicGeometry.ResolveInputs(
                new[] { energy, balance, phase, detail },
                new[] { true, true, true, true },
                new float[4]);
        }
    }
}
