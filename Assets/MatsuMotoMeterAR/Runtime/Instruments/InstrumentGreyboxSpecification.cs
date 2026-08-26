using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public readonly struct InstrumentGreyboxSpec
    {
        public InstrumentGreyboxSpec(
            Vector3 boundsSize,
            Vector3 interactionCenter,
            Vector3 interactionSize,
            int rendererBudget)
        {
            BoundsSize = boundsSize;
            InteractionCenter = interactionCenter;
            InteractionSize = interactionSize;
            RendererBudget = rendererBudget;
        }

        public Vector3 BoundsSize { get; }
        public Vector3 InteractionCenter { get; }
        public Vector3 InteractionSize { get; }
        public int RendererBudget { get; }
    }

    public static class InstrumentGreyboxSpecification
    {
        public const int TriangleBudgetPerInstrument = 5000;
        public const int LargeInstrumentTriangleBudget = 25000;
        public const int SharedMaterialBudgetPerInstrument = 2;
        public const int SignalMonitorRendererBudget = 9;
        public const int SignalMonitorMaterialBudget = 2;
        public const int GuaranteedInstrumentsPerRoom = 24;
        public const int StressTestInstrumentsPerRoom = 40;
        public const float MeterSweepDegrees = 115f;
        public const float LeverMaximumAngleDegrees = 24f;
        public const float ThrottleMaximumAngleDegrees = 35f;
        public const float PowerSliderTravelMeters = 0.18f;
        public static readonly Vector3 ThrottleGripCenterFromPivot =
            new(0f, 0.225f, 0.002f);
        public static readonly Vector3 ThrottleGripInteractionSize =
            new(0.16f, 0.075f, 0.085f);

        public static InstrumentGreyboxSpec Get(MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.Lever => new InstrumentGreyboxSpec(
                    new Vector3(0.18f, 0.256f, 0.18f),
                    new Vector3(0f, 0.058f, 0.05f),
                    new Vector3(0.24f, 0.256f, 0.10f),
                    3),
                MockInstrumentKind.ToggleSwitch => new InstrumentGreyboxSpec(
                    new Vector3(0.125f, 0.17f, 0.13f),
                    new Vector3(0f, 0.015f, 0.032f),
                    new Vector3(0.12f, 0.17f, 0.064f),
                    2),
                MockInstrumentKind.RotaryKnob => new InstrumentGreyboxSpec(
                    new Vector3(0.153f, 0.153f, 0.112f),
                    new Vector3(0f, 0f, 0.051f),
                    new Vector3(0.15f, 0.15f, 0.102f),
                    3),
                MockInstrumentKind.PushButton => new InstrumentGreyboxSpec(
                    new Vector3(0.137f, 0.137f, 0.096f),
                    new Vector3(0f, 0f, 0.045f),
                    new Vector3(0.13f, 0.13f, 0.09f),
                    2),
                MockInstrumentKind.IndicatorLamp => new InstrumentGreyboxSpec(
                    new Vector3(0.143f, 0.119f, 0.115f),
                    new Vector3(0f, 0f, 0.041f),
                    new Vector3(0.14f, 0.11f, 0.082f),
                    2),
                MockInstrumentKind.StatusIndicator => new InstrumentGreyboxSpec(
                    new Vector3(0.185f, 0.125f, 0.100f),
                    new Vector3(0f, 0f, 0.0375f),
                    new Vector3(0.18f, 0.12f, 0.075f),
                    4),
                MockInstrumentKind.ThrottleLever => new InstrumentGreyboxSpec(
                    new Vector3(0.24f, 0.34f, 0.16f),
                    new Vector3(0f, 0.04f, 0.08f),
                    new Vector3(0.28f, 0.38f, 0.18f),
                    3),
                MockInstrumentKind.PowerSlider => new InstrumentGreyboxSpec(
                    new Vector3(0.17f, 0.34f, 0.195f),
                    new Vector3(0f, 0f, 0.045f),
                    new Vector3(0.20f, 0.38f, 0.12f),
                    3),
                MockInstrumentKind.RoundMeterMedium =>
                    new InstrumentGreyboxSpec(
                        new Vector3(0.36f, 0.36f, 0.145f),
                        new Vector3(0f, 0f, 0.066f),
                        new Vector3(0.36f, 0.36f, 0.132f),
                        4),
                MockInstrumentKind.RoundMeterLarge =>
                    new InstrumentGreyboxSpec(
                        new Vector3(0.55f, 0.55f, 0.205f),
                        new Vector3(0f, 0f, 0.096f),
                        new Vector3(0.55f, 0.55f, 0.192f),
                        4),
                MockInstrumentKind.WindowMeter => new InstrumentGreyboxSpec(
                    new Vector3(1.20f, 0.75f, 0.202f),
                    new Vector3(0f, 0f, 0.095f),
                    new Vector3(1.20f, 0.75f, 0.19f),
                    4),
                MockInstrumentKind.WindowPanel => new InstrumentGreyboxSpec(
                    new Vector3(1.60f, 0.90f, 0.22f),
                    new Vector3(0f, 0f, 0.11f),
                    new Vector3(1.60f, 0.90f, 0.22f),
                    4),
                MockInstrumentKind.TrendMonitor => new InstrumentGreyboxSpec(
                    new Vector3(0.44f, 0.28f, 0.10f),
                    new Vector3(0f, 0f, 0.05f),
                    new Vector3(0.44f, 0.28f, 0.10f),
                    3),
                _ => new InstrumentGreyboxSpec(
                    new Vector3(0.17f, 0.17f, 0.082f),
                    new Vector3(0f, 0f, 0.032f),
                    new Vector3(0.14f, 0.14f, 0.064f),
                    4)
            };
        }

        public static int GetTriangleBudget(MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.RoundMeterMedium ||
                   kind == MockInstrumentKind.RoundMeterLarge ||
                   kind == MockInstrumentKind.WindowMeter ||
                   kind == MockInstrumentKind.WindowPanel ||
                   kind == MockInstrumentKind.TrendMonitor
                ? LargeInstrumentTriangleBudget
                : TriangleBudgetPerInstrument;
        }
    }
}
