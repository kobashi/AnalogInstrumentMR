using System;
using System.Collections;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Signals;
using Unity.Profiling;
using UnityEngine;
using UnityEngine.Profiling;

namespace MatsuMotoMeterAR.PerformanceGate
{
    public sealed class PerformanceGateController : MonoBehaviour
    {
        private const float WarmupSeconds = 15f;
        // 30 minutes at 72 Hz is about 129,600 frames. Keep enough headroom so
        // the final percentile and delayed-frame result cover the full run.
        private const int MaximumSamples = 150000;
        private const double VsyncMilliseconds = 1000.0 / 72.0;
        private const string PerformanceInputA = "perf-a";
        private const string PerformanceInputB = "perf-b";

        private readonly FrameTiming[] latestTiming = new FrameTiming[1];
        private readonly double[] cpuSamples = new double[MaximumSamples];
        private readonly double[] gpuSamples = new double[MaximumSamples];
        private readonly double[] frameSamples = new double[MaximumSamples];
        private ProfilerRecorder gcAllocatedRecorder;
        private TextMesh statusLabel;
        private float measurementStartedAt;
        private int sampleCount;
        private int delayedFrameCount;
        private long maximumGcAllocatedBytes;
        private int initialCollectionCount;
        private bool measurementActive;
        private bool reportWritten;
        private bool frameTimingAvailable;
        private SignalMonitorView[] trendMonitors;
        private readonly SignalMonitorRefreshScheduler
            trendMonitorRefreshScheduler = new();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
            if (!PerformanceGateConfiguration.IsEnabled ||
                FindAnyObjectByType<PerformanceGateController>() != null)
            {
                return;
            }

            var host = new GameObject("[Performance Gate] Quest Scenario");
            DontDestroyOnLoad(host);
            host.AddComponent<PerformanceGateController>();
        }

        private IEnumerator Start()
        {
            CreateStatusHud();
            SetStatus("PERFORMANCE GATE\nPREPARING", Color.yellow);
            yield return new WaitForSecondsRealtime(2f);

            var camera = Camera.main;
            if (camera == null)
            {
                Debug.LogError("[PerfGate] Main camera was not found.");
                SetStatus("PERFORMANCE GATE\nNO CAMERA", Color.red);
                yield break;
            }

            CreateScenario(camera.transform);
            OVRPlugin.systemDisplayFrequency = 72f;
            yield return new WaitForSecondsRealtime(1f);
            var displayFrequency = OVRPlugin.systemDisplayFrequency;
            if (Mathf.Abs(displayFrequency - 72f) > 0.5f)
            {
                Debug.LogError(
                    $"[PerfGate] 72 Hz request failed; current={displayFrequency:0.00} Hz.");
                SetStatus(
                    $"PERFORMANCE GATE BLOCKED\nDISPLAY {displayFrequency:0.00} Hz",
                    Color.red);
                yield break;
            }

            frameTimingAvailable = FrameTimingManager.IsFeatureEnabled();
            Debug.Log(
                $"[PerfGate] Scenario ready: count={PerformanceGateConfiguration.InstrumentCount}, " +
                $"theme={PerformanceGateConfiguration.Theme}, display={displayFrequency:0.00}Hz, " +
                $"frameTiming={frameTimingAvailable}, " +
                $"distance={PerformanceGateConfiguration.DistanceMeters:0.00}m, " +
                $"kind={PerformanceGateConfiguration.InstrumentKind?.ToString() ?? "Baseline"}, " +
                $"profile={PerformanceGateConfiguration.DisplayMode}, " +
                $"duration={PerformanceGateConfiguration.DurationSeconds}s.");
            SetStatus(
                $"PERF WARMUP {WarmupSeconds:0}s\n" +
                $"{PerformanceGateConfiguration.InstrumentCount} OBJECTS | 72 Hz",
                Color.yellow);
            yield return new WaitForSecondsRealtime(WarmupSeconds);

            BeginMeasurement();
        }

        private void Update()
        {
            UpdateTrendMonitorDisplays();

            if (!measurementActive || reportWritten)
                return;

            FrameTimingManager.CaptureFrameTimings();
            var count = FrameTimingManager.GetLatestTimings(1, latestTiming);
            var frameMilliseconds = Time.unscaledDeltaTime * 1000.0;
            var cpuMilliseconds = count > 0 ? latestTiming[0].cpuFrameTime : 0.0;
            var gpuMilliseconds = count > 0 ? latestTiming[0].gpuFrameTime : 0.0;

            if (sampleCount < MaximumSamples)
            {
                cpuSamples[sampleCount] = cpuMilliseconds;
                gpuSamples[sampleCount] = gpuMilliseconds;
                frameSamples[sampleCount] = frameMilliseconds;
                sampleCount++;
                if (frameMilliseconds > VsyncMilliseconds * 1.5)
                    delayedFrameCount++;
            }
            if (gcAllocatedRecorder.Valid)
            {
                maximumGcAllocatedBytes = Math.Max(
                    maximumGcAllocatedBytes,
                    gcAllocatedRecorder.LastValue);
            }

            var elapsed = Time.realtimeSinceStartup - measurementStartedAt;
            if (elapsed >= PerformanceGateConfiguration.DurationSeconds)
                WriteFinalReport(elapsed);
        }

        private void OnDestroy()
        {
            gcAllocatedRecorder.Dispose();
        }

        private void CreateScenario(Transform cameraTransform)
        {
            var count = PerformanceGateConfiguration.InstrumentCount;
            if (PerformanceGateConfiguration.InstrumentKind ==
                    MockInstrumentKind.TrendMonitor &&
                PerformanceGateConfiguration.DisplayMode ==
                    PerformanceGateDisplayMode.Graph)
            {
                trendMonitors = new SignalMonitorView[count];
            }
            var forward = Vector3.ProjectOnPlane(cameraTransform.forward, Vector3.up).normalized;
            if (forward.sqrMagnitude < 0.001f)
                forward = Vector3.forward;
            var right = Vector3.Cross(Vector3.up, forward).normalized;
            var origin = cameraTransform.position +
                         forward * PerformanceGateConfiguration.DistanceMeters;
            var normal = -forward;

            for (var index = 0; index < count; index++)
            {
                var pose = PerformanceGateLayout.GetPose(
                    index,
                    count,
                    origin,
                    right,
                    Vector3.up,
                    normal);
                var instrument = MockInstrumentFactory.Create(
                    PerformanceGateConfiguration.InstrumentKind ??
                    (MockInstrumentKind)(
                        index % MockInstrumentCatalog.PerformanceBaselineCount),
                    pose,
                    theme: PerformanceGateConfiguration.Theme);
                instrument.name = $"[PerfGate {index + 1:00}] {instrument.name}";

                ConfigureTrendMonitor(instrument, index);
            }
        }

        private void ConfigureTrendMonitor(GameObject instrument, int index)
        {
            if (PerformanceGateConfiguration.InstrumentKind !=
                MockInstrumentKind.TrendMonitor)
            {
                return;
            }

            var monitor = instrument.GetComponentInChildren<SignalMonitorView>(true);
            if (monitor == null)
            {
                Debug.LogError(
                    $"[PerfGate] TrendMonitor display was not found at index {index}.");
                return;
            }

            switch (PerformanceGateConfiguration.DisplayMode)
            {
                case PerformanceGateDisplayMode.None:
                    monitor.gameObject.SetActive(false);
                    break;
                case PerformanceGateDisplayMode.Numeric:
                    monitor.BeginRefresh();
                    monitor.AddSample(PerformanceInputA, 0.5f, 0f);
                    monitor.EndRefresh();
                    break;
                case PerformanceGateDisplayMode.Graph:
                    trendMonitors[index] = monitor;
                    break;
            }
        }

        private void UpdateTrendMonitorDisplays()
        {
            if (trendMonitors == null || trendMonitors.Length == 0)
                return;

            var sampleTime = Time.unscaledTime;
            var refreshCount = trendMonitorRefreshScheduler.Accumulate(
                trendMonitors.Length,
                Time.unscaledDeltaTime);

            for (var refresh = 0; refresh < refreshCount; refresh++)
            {
                var index = trendMonitorRefreshScheduler.TakeNextIndex(
                    trendMonitors.Length);
                var monitor = trendMonitors[index];
                if (monitor == null)
                    continue;

                var phase = sampleTime * 0.8f + index * 0.17f;
                var inputA = 0.5f + Mathf.Sin(phase) * 0.42f;
                var inputB = 0.5f + Mathf.Cos(phase * 0.61f) * 0.35f;
                monitor.BeginRefresh();
                monitor.AddSample(PerformanceInputA, inputA, sampleTime);
                monitor.AddSample(PerformanceInputB, inputB, sampleTime);
                monitor.AddComposedSample(
                    SignalCompositionKind.Average,
                    (inputA + inputB) * 0.5f,
                    2,
                    sampleTime);
                monitor.EndRefresh();
            }
        }

        private void BeginMeasurement()
        {
            gcAllocatedRecorder = ProfilerRecorder.StartNew(
                ProfilerCategory.Memory,
                "GC Allocated In Frame",
                1);
            initialCollectionCount = GC.CollectionCount(0) +
                                     GC.CollectionCount(1) +
                                     GC.CollectionCount(2);
            measurementStartedAt = Time.realtimeSinceStartup;
            measurementActive = true;
            Debug.Log("[PerfGate] Measurement started after 15s warmup.");
            if (statusLabel != null)
                statusLabel.gameObject.SetActive(false);
        }

        private void WriteFinalReport(float elapsed)
        {
            reportWritten = true;
            measurementActive = false;
            var memoryBytes = Profiler.GetTotalAllocatedMemoryLong();
            var collections = GC.CollectionCount(0) + GC.CollectionCount(1) +
                              GC.CollectionCount(2) - initialCollectionCount;
            var cpuP95 = Percentile95(cpuSamples, sampleCount, ignoreZeros: true);
            var gpuP95 = Percentile95(gpuSamples, sampleCount, ignoreZeros: true);
            var frameP95 = Percentile95(frameSamples, sampleCount, ignoreZeros: false);
            var delayedPercent = sampleCount > 0
                ? delayedFrameCount * 100.0 / sampleCount
                : 0.0;
            var timingDiagnosticOk = frameTimingAvailable &&
                                     cpuP95 > 0.0 && gpuP95 > 0.0 &&
                                     cpuP95 <= 11.0 && gpuP95 <= 11.0 &&
                                     delayedPercent < 1.0;
            var diagnostic = !frameTimingAvailable
                ? "UNAVAILABLE"
                : timingDiagnosticOk ? "TIMING_OK" : "REVIEW";

            gcAllocatedRecorder.Dispose();

            Debug.Log(
                $"[PerfGate] FINAL diagnostic={diagnostic}, externalVerdict=PENDING, " +
                $"count={PerformanceGateConfiguration.InstrumentCount}, " +
                $"theme={PerformanceGateConfiguration.Theme}, " +
                $"profile={PerformanceGateConfiguration.DisplayMode}, " +
                $"elapsed={elapsed:0.0}s, " +
                $"samples={sampleCount}, cpuP95={cpuP95:0.000}ms, " +
                $"gpuP95={gpuP95:0.000}ms, frameP95={frameP95:0.000}ms, " +
                $"delayed={delayedPercent:0.000}%, gcCollections={collections}, " +
                $"maxGcAllocatedInFrame={maximumGcAllocatedBytes}B, " +
                $"memory={memoryBytes}B.");
            if (statusLabel != null)
                statusLabel.gameObject.SetActive(true);
            SetStatus(
                $"{diagnostic}\nEXTERNAL VERDICT PENDING",
                timingDiagnosticOk ? Color.green : Color.yellow);
        }

        public static double Percentile95(double[] values, int count, bool ignoreZeros)
        {
            if (values == null || count <= 0)
                return 0.0;

            var filtered = new double[Math.Min(count, values.Length)];
            var filteredCount = 0;
            for (var index = 0; index < filtered.Length; index++)
            {
                if (ignoreZeros && values[index] <= 0.0)
                    continue;
                filtered[filteredCount++] = values[index];
            }
            if (filteredCount == 0)
                return 0.0;

            Array.Sort(filtered, 0, filteredCount);
            var percentileIndex = Mathf.CeilToInt(filteredCount * 0.95f) - 1;
            return filtered[Mathf.Clamp(percentileIndex, 0, filteredCount - 1)];
        }

        private void CreateStatusHud()
        {
            var camera = Camera.main;
            if (camera == null)
                return;

            var statusObject = new GameObject("Performance Gate Status");
            statusObject.transform.SetParent(camera.transform, false);
            statusObject.transform.localPosition = new Vector3(0f, 0.28f, 0.8f);
            statusLabel = statusObject.AddComponent<TextMesh>();
            statusLabel.anchor = TextAnchor.MiddleCenter;
            statusLabel.alignment = TextAlignment.Center;
            statusLabel.characterSize = 0.011f;
            statusLabel.fontSize = 64;
        }

        private void SetStatus(string value, Color color)
        {
            if (statusLabel == null)
                return;
            statusLabel.text = value;
            statusLabel.color = color;
        }
    }
}
