using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;
using MatsuMotoMeterAR.Signals;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class SignalMonitorTests
    {
        [Test]
        public void SampleBuffer_WrapsAndReadsOldestFirst()
        {
            var buffer = new SignalSampleBuffer(3);
            buffer.Add(1f);
            buffer.Add(2f);
            buffer.Add(3f);
            buffer.Add(4f);

            Assert.That(buffer.Count, Is.EqualTo(3));
            Assert.That(buffer.GetOldestFirst(0), Is.EqualTo(2f));
            Assert.That(buffer.GetOldestFirst(1), Is.EqualTo(3f));
            Assert.That(buffer.GetOldestFirst(2), Is.EqualTo(4f));

            buffer.Clear();
            Assert.That(buffer.Count, Is.Zero);
            Assert.Throws<ArgumentOutOfRangeException>(
                () => buffer.GetOldestFirst(0));
        }

        [Test]
        public void Evaluator_ReportsOutputAndClearsDisconnectedState()
        {
            var sourceRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.Lever,
                Pose.identity);
            var targetRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.RoundMeter,
                Pose.identity);
            try
            {
                var source = sourceRoot
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                var target = targetRoot
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                source.SetNormalizedValue(0.75f);

                var instruments = new Dictionary<string, MockInstrumentInteraction>
                {
                    ["source"] = source,
                    ["target"] = target
                };
                var connections = new List<SignalConnectionRecord>
                {
                    new()
                    {
                        connectionId = "connection",
                        sourcePlacementId = "source",
                        targetPlacementId = "target",
                        transformKind = (int)SignalTransformKind.Direct
                    }
                };
                var evaluator = new SignalGraphEvaluator();

                evaluator.Evaluate(connections, instruments);

                Assert.That(
                    evaluator.TryGetOutput(
                        "target",
                        out var output,
                        out var inputCount),
                    Is.True);
                Assert.That(output, Is.EqualTo(0.75f).Within(0.0001f));
                Assert.That(inputCount, Is.EqualTo(1));
                Assert.That(target.NormalizedValue, Is.EqualTo(0.75f).Within(0.0001f));

                evaluator.Evaluate(Array.Empty<SignalConnectionRecord>(), instruments);
                Assert.That(
                    evaluator.TryGetOutput("target", out _, out _),
                    Is.False);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(sourceRoot);
                UnityEngine.Object.DestroyImmediate(targetRoot);
            }
        }

        [Test]
        public void Evaluator_UsesConnectionSpecificTransformParameters()
        {
            var sourceRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.Lever,
                Pose.identity);
            var targetRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.RoundMeter,
                Pose.identity);
            try
            {
                var source = sourceRoot
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                var target = targetRoot
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                source.SetNormalizedValue(0.5f);
                var instruments = new Dictionary<string, MockInstrumentInteraction>
                {
                    ["source"] = source,
                    ["target"] = target
                };
                var connections = new List<SignalConnectionRecord>
                {
                    new()
                    {
                        connectionId = "configured-range",
                        sourcePlacementId = "source",
                        targetPlacementId = "target",
                        transformKind = (int)SignalTransformKind.Range,
                        inputMinimum = 0f,
                        inputMaximum = 1f,
                        outputMinimum = 0.4f,
                        outputMaximum = 0.6f
                    }
                };

                new SignalGraphEvaluator().Evaluate(connections, instruments);

                Assert.That(
                    target.NormalizedValue,
                    Is.EqualTo(0.5f).Within(0.0001f));
                source.SetNormalizedValue(1f);
                new SignalGraphEvaluator().Evaluate(connections, instruments);
                Assert.That(
                    target.NormalizedValue,
                    Is.EqualTo(0.6f).Within(0.0001f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(sourceRoot);
                UnityEngine.Object.DestroyImmediate(targetRoot);
            }
        }

        [Test]
        public void Factory_AddsDisplayOnlyToTrendMonitor()
        {
            var monitor = MockInstrumentFactory.Create(
                MockInstrumentKind.TrendMonitor,
                Pose.identity);
            var meter = MockInstrumentFactory.Create(
                MockInstrumentKind.RoundMeter,
                Pose.identity);
            try
            {
                Assert.That(
                    monitor.GetComponentInChildren<SignalMonitorView>(true),
                    Is.Not.Null);
                Assert.That(
                    meter.GetComponentInChildren<SignalMonitorView>(true),
                    Is.Null);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(monitor);
                UnityEngine.Object.DestroyImmediate(meter);
            }
        }

        [Test]
        public void Factory_AlignsDisplayToVisualDisplaySurface()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.TrendMonitor,
                new Pose(
                    new Vector3(1f, 2f, 3f),
                    Quaternion.Euler(12f, 34f, 5f)));
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var displaySurface = contract.VisualSocket
                    .GetComponentInChildren<ThemeVisualManifest>(true)
                    .MotionTarget;
                var monitor = root.GetComponentInChildren<SignalMonitorView>(true);
                var outward = contract.LabelSocket.forward;
                var displayFrontDepth = FrontDepth(
                    displaySurface,
                    outward);
                var monitorDepth = Vector3.Dot(
                    monitor.transform.position,
                    outward);

                Assert.That(
                    monitorDepth - displayFrontDepth,
                    Is.EqualTo(0.0002f).Within(0.0001f));
                Assert.That(
                    Vector3.Dot(
                        monitor.transform.forward,
                        outward),
                    Is.LessThan(-0.999f));
                Assert.That(
                    Vector3.Dot(
                        monitor.transform.up,
                        contract.LabelSocket.up),
                    Is.GreaterThan(0.999f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void Factory_ReAlignsTrendDisplayAfterThemeChange()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.TrendMonitor,
                Pose.identity);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var monitor = root.GetComponentInChildren<SignalMonitorView>(true);
                foreach (var theme in new[]
                         {
                             MockInstrumentTheme.ForgeBrass,
                             MockInstrumentTheme.KineticSafety,
                             MockInstrumentTheme.OrbitalAnalog,
                             MockInstrumentTheme.MachinedErgonomics
                         })
                {
                    Assert.That(
                        MockInstrumentFactory.ApplyTheme(root, theme),
                        Is.True);
                    var displaySurface = contract.VisualSocket
                        .GetComponentInChildren<ThemeVisualManifest>(true)
                        .MotionTarget;
                    var normal = contract.LabelSocket.forward;
                    var monitorDepth = Vector3.Dot(
                        monitor.transform.position,
                        normal);
                    var frontDepth = FrontDepth(
                        displaySurface,
                        normal);

                    Assert.That(
                        monitorDepth - frontDepth,
                        Is.EqualTo(0.0002f).Within(0.0001f));
                    Assert.That(
                        Vector3.Dot(
                            monitor.transform.forward,
                            normal),
                        Is.LessThan(-0.999f));
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void View_UsesDisplayMeshPlaneWhenTransformForwardIsPerpendicular()
        {
            var socket = new GameObject("LabelSocket");
            var surface = new GameObject("display_surface");
            var mesh = new Mesh();
            try
            {
                surface.transform.SetParent(socket.transform, false);
                surface.transform.localRotation =
                    Quaternion.Euler(0f, 90f, 0f);
                mesh.vertices = new[]
                {
                    new Vector3(-0.001f, -0.09f, -0.18f),
                    new Vector3(-0.001f, -0.09f, 0.18f),
                    new Vector3(-0.001f, 0.09f, -0.18f),
                    new Vector3(-0.001f, 0.09f, 0.18f),
                    new Vector3(0.001f, -0.09f, -0.18f),
                    new Vector3(0.001f, -0.09f, 0.18f),
                    new Vector3(0.001f, 0.09f, -0.18f),
                    new Vector3(0.001f, 0.09f, 0.18f)
                };
                mesh.triangles = new[]
                {
                    0, 2, 1, 1, 2, 3,
                    4, 5, 6, 5, 7, 6
                };
                mesh.RecalculateBounds();
                surface.AddComponent<MeshFilter>().sharedMesh = mesh;
                surface.AddComponent<MeshRenderer>();

                var monitor = SignalMonitorView.Create(
                    socket.transform,
                    surface.transform);

                Assert.That(
                    Mathf.Abs(Vector3.Dot(
                        surface.transform.forward,
                        socket.transform.forward)),
                    Is.LessThan(0.001f));
                Assert.That(
                    Vector3.Dot(
                        monitor.transform.forward,
                        socket.transform.forward),
                    Is.LessThan(-0.999f));
                Assert.That(
                    Vector3.Dot(
                        monitor.transform.up,
                        socket.transform.up),
                    Is.GreaterThan(0.999f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(socket);
                UnityEngine.Object.DestroyImmediate(mesh);
            }
        }

        [Test]
        public void View_FitsRecessedDisplaySurfaceInsideFrontBezel()
        {
            var socket = new GameObject("LabelSocket");
            var visual = new GameObject("Visual");
            var surface = new GameObject("display_surface");
            var mesh = new Mesh();
            try
            {
                visual.transform.SetParent(socket.transform, false);
                surface.transform.SetParent(visual.transform, false);
                surface.transform.localRotation =
                    Quaternion.Euler(0f, 180f, 0f);
                mesh.vertices = new[]
                {
                    new Vector3(-0.18f, -0.09f, 0.04f),
                    new Vector3(0.18f, -0.09f, 0.04f),
                    new Vector3(-0.18f, 0.09f, 0.06f),
                    new Vector3(0.18f, 0.09f, 0.06f)
                };
                mesh.triangles = new[] { 0, 2, 1, 1, 2, 3 };
                mesh.RecalculateBounds();
                surface.AddComponent<MeshFilter>().sharedMesh = mesh;
                surface.AddComponent<MeshRenderer>();
                visual.AddComponent<ThemeVisualManifest>().Configure(
                    surface.transform);
                var bezel = GameObject.CreatePrimitive(PrimitiveType.Cube);
                bezel.name = "FrontBezel";
                bezel.transform.SetParent(visual.transform, false);
                bezel.transform.localPosition = new Vector3(0f, 0f, 0.08f);
                bezel.transform.localScale = new Vector3(0.4f, 0.25f, 0.02f);
                var bezelRenderer = bezel.GetComponent<Renderer>();

                var monitor = SignalMonitorView.Create(
                    socket.transform,
                    surface.transform);
                var outward = socket.transform.forward;
                var monitorDepth = Vector3.Dot(
                    monitor.transform.position,
                    outward);
                var visualFrontDepth = Vector3.Dot(
                    bezelRenderer.bounds.center,
                    outward) +
                    Mathf.Abs(outward.x) * bezelRenderer.bounds.extents.x +
                    Mathf.Abs(outward.y) * bezelRenderer.bounds.extents.y +
                    Mathf.Abs(outward.z) * bezelRenderer.bounds.extents.z;

                var displayFrontDepth = FrontDepth(
                    surface.transform,
                    outward);
                Assert.That(monitorDepth, Is.GreaterThan(displayFrontDepth));
                Assert.That(
                    monitorDepth - displayFrontDepth,
                    Is.EqualTo(0.0002f).Within(0.0001f));
                Assert.That(monitorDepth, Is.LessThan(visualFrontDepth));
                Assert.That(
                    Vector3.Dot(monitor.transform.forward, outward),
                    Is.LessThan(-0.999f));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(socket);
                UnityEngine.Object.DestroyImmediate(mesh);
            }
        }

        [Test]
        public void Policy_MetersAreObservableOnlyByTrendMonitor()
        {
            Assert.That(
                InstrumentSignalPolicy.CanConnect(
                    MockInstrumentKind.RoundMeter,
                    MockInstrumentKind.TrendMonitor),
                Is.True);
            Assert.That(
                InstrumentSignalPolicy.CanConnect(
                    MockInstrumentKind.RoundMeter,
                    MockInstrumentKind.WindowMeter),
                Is.False);
            Assert.That(
                InstrumentSignalPolicy.CanConnect(
                    MockInstrumentKind.Lever,
                    MockInstrumentKind.TrendMonitor),
                Is.True);
            Assert.That(
                InstrumentSignalPolicy.CanSource(
                    MockInstrumentKind.TrendMonitor),
                Is.False);
        }

        [Test]
        public void View_AcceptsFourStableChannelsAndRejectsFifth()
        {
            var socket = new GameObject("LabelSocket");
            try
            {
                var monitor = SignalMonitorView.Create(
                    socket.transform,
                    displaySurface: null);
                monitor.BeginRefresh();
                for (var index = 0;
                     index < SignalMonitorView.ChannelCapacity;
                     index++)
                {
                    Assert.That(
                        monitor.AddSample($"connection-{index}", index / 3f),
                        Is.True);
                }
                Assert.That(
                    monitor.AddSample("connection-overflow", 0.5f),
                    Is.False);
                monitor.EndRefresh();

                Assert.That(
                    monitor.ConnectedChannelCount,
                    Is.EqualTo(SignalMonitorView.ChannelCapacity));
                for (var index = 0;
                     index < SignalMonitorView.ChannelCapacity;
                     index++)
                {
                    Assert.That(
                        monitor.GetChannelSampleCount(index),
                        Is.EqualTo(1));
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(socket);
            }
        }

        [Test]
        public void View_DrawsSamplesFromOldestLeftToNewestRight()
        {
            var socket = new GameObject("LabelSocket");
            try
            {
                var monitor = SignalMonitorView.Create(
                    socket.transform,
                    displaySurface: null);
                monitor.BeginRefresh();
                Assert.That(
                    monitor.AddSample("connection", 0.25f, 0f),
                    Is.True);
                monitor.EndRefresh();
                monitor.BeginRefresh();
                Assert.That(
                    monitor.AddSample(
                        "connection",
                        0.75f,
                        SignalMonitorView.RefreshIntervalSeconds),
                    Is.True);
                monitor.EndRefresh();

                var graph = monitor.transform
                    .Find("Channel1Trend")
                    .GetComponent<LineRenderer>();
                Assert.That(graph.gameObject.activeSelf, Is.True);
                Assert.That(graph.transform.localPosition.z, Is.LessThan(0f));
                Assert.That(graph.useWorldSpace, Is.True);
                Assert.That(
                    graph.alignment,
                    Is.EqualTo(LineAlignment.TransformZ));
                Assert.That(graph.numCornerVertices, Is.EqualTo(8));
                Assert.That(graph.numCapVertices, Is.EqualTo(6));
                Assert.That(graph.forceRenderingOff, Is.False);
                Assert.That(graph.enabled, Is.True);
                Assert.That(graph.positionCount, Is.EqualTo(2));
                Assert.That(graph.startWidth, Is.EqualTo(0.0045f).Within(0.0001f));
                Assert.That(graph.endWidth, Is.EqualTo(0.0045f).Within(0.0001f));
                Assert.That(
                    graph.sharedMaterial.renderQueue,
                    Is.EqualTo((int)UnityEngine.Rendering.RenderQueue.Geometry));
                Assert.That(graph.transform.Find("BakedRibbon"), Is.Null);
                var firstPoint = graph.transform.InverseTransformPoint(
                    graph.GetPosition(0));
                var lastPoint = graph.transform.InverseTransformPoint(
                    graph.GetPosition(1));
                Assert.That(firstPoint.x, Is.LessThan(lastPoint.x));
                Assert.That(lastPoint.x, Is.EqualTo(0.145f).Within(0.0001f));
                Assert.That(
                    firstPoint.y,
                    Is.LessThan(lastPoint.y));

                monitor.BeginRefresh();
                Assert.That(
                    monitor.AddSample("connection", 0.10f, 0.21f),
                    Is.True);
                monitor.EndRefresh();
                Assert.That(monitor.GetChannelSampleCount(0), Is.EqualTo(2));
                Assert.That(graph.positionCount, Is.EqualTo(2));
                firstPoint = graph.transform.InverseTransformPoint(
                    graph.GetPosition(0));
                lastPoint = graph.transform.InverseTransformPoint(
                    graph.GetPosition(1));
                Assert.That(lastPoint.x, Is.EqualTo(0.145f).Within(0.0001f));
                Assert.That(
                    lastPoint.y,
                    Is.LessThan(firstPoint.y));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(socket);
            }
        }

        [Test]
        public void View_DistinguishesCoincidentChannels()
        {
            var socket = new GameObject("LabelSocket");
            try
            {
                var monitor = SignalMonitorView.Create(
                    socket.transform,
                    displaySurface: null);
                var sampleTime = 0f;
                foreach (var value in new[] { 0.25f, 0.75f })
                {
                    monitor.BeginRefresh();
                    Assert.That(
                        monitor.AddSample("lever", value, sampleTime),
                        Is.True);
                    Assert.That(
                        monitor.AddSample("meter", value, sampleTime),
                        Is.True);
                    monitor.EndRefresh();
                    sampleTime += SignalMonitorView.RefreshIntervalSeconds;
                }

                var leverGraph = monitor.transform
                    .Find("Channel1Trend")
                    .GetComponent<LineRenderer>();
                var meterGraph = monitor.transform
                    .Find("Channel2Trend")
                    .GetComponent<LineRenderer>();
                Assert.That(leverGraph.positionCount, Is.EqualTo(2));
                Assert.That(meterGraph.positionCount, Is.EqualTo(2));
                Assert.That(
                    leverGraph.transform.localPosition.y,
                    Is.Not.EqualTo(meterGraph.transform.localPosition.y));
                Assert.That(leverGraph.startColor, Is.Not.EqualTo(meterGraph.startColor));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(socket);
            }
        }

        [Test]
        public void View_UsesDepthTestedFrontFaceTextMaterial()
        {
            var socket = new GameObject("LabelSocket");
            try
            {
                var monitor = SignalMonitorView.Create(
                    socket.transform,
                    displaySurface: null);
                var text = monitor.transform
                    .Find("Status")
                    .GetComponent<TextMesh>();
                var material = text.GetComponent<MeshRenderer>()
                    .sharedMaterial;

                Assert.That(material, Is.Not.Null);
                Assert.That(
                    material.shader.name,
                    Is.EqualTo("MatsuMotoMeterAR/DepthTestedText"));
                Assert.That(
                    material.GetInt("_ZTest"),
                    Is.EqualTo((int)UnityEngine.Rendering.CompareFunction.LessEqual));
                Assert.That(
                    material.GetInt("_Cull"),
                    Is.EqualTo((int)UnityEngine.Rendering.CullMode.Back));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(socket);
            }
        }

        private static float FrontDepth(
            Transform surface,
            Vector3 normal)
        {
            var bounds = surface.GetComponent<MeshFilter>()
                .sharedMesh.bounds;
            var center = bounds.center;
            var extents = bounds.extents;
            var frontDepth = float.NegativeInfinity;
            for (var x = -1; x <= 1; x += 2)
            for (var y = -1; y <= 1; y += 2)
            for (var z = -1; z <= 1; z += 2)
            {
                var corner = surface.TransformPoint(
                    center + Vector3.Scale(
                        extents,
                        new Vector3(x, y, z)));
                frontDepth = Mathf.Max(
                    frontDepth,
                    Vector3.Dot(corner, normal));
            }
            return frontDepth;
        }
    }
}
