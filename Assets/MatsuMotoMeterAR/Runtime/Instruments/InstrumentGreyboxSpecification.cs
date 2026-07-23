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
        public const int GreyboxTriangleBudgetPerInstrument = 1500;
        public const int TriangleBudgetPerInstrument = 5000;
        public const int SharedMaterialBudgetPerInstrument = 2;
        public const int GuaranteedInstrumentsPerRoom = 24;
        public const int StressTestInstrumentsPerRoom = 40;

        public static InstrumentGreyboxSpec Get(MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.Lever => new InstrumentGreyboxSpec(
                    new Vector3(0.18f, 0.256f, 0.10f),
                    new Vector3(0f, 0.058f, 0.05f),
                    new Vector3(0.18f, 0.256f, 0.10f),
                    3),
                MockInstrumentKind.ToggleSwitch => new InstrumentGreyboxSpec(
                    new Vector3(0.12f, 0.17f, 0.064f),
                    new Vector3(0f, 0.015f, 0.032f),
                    new Vector3(0.12f, 0.17f, 0.064f),
                    2),
                MockInstrumentKind.RotaryKnob => new InstrumentGreyboxSpec(
                    new Vector3(0.15f, 0.15f, 0.102f),
                    new Vector3(0f, 0f, 0.051f),
                    new Vector3(0.15f, 0.15f, 0.102f),
                    3),
                MockInstrumentKind.PushButton => new InstrumentGreyboxSpec(
                    new Vector3(0.13f, 0.13f, 0.09f),
                    new Vector3(0f, 0f, 0.045f),
                    new Vector3(0.13f, 0.13f, 0.09f),
                    2),
                MockInstrumentKind.IndicatorLamp => new InstrumentGreyboxSpec(
                    new Vector3(0.14f, 0.11f, 0.082f),
                    new Vector3(0f, 0f, 0.041f),
                    new Vector3(0.14f, 0.11f, 0.082f),
                    2),
                _ => new InstrumentGreyboxSpec(
                    new Vector3(0.14f, 0.14f, 0.064f),
                    new Vector3(0f, 0f, 0.032f),
                    new Vector3(0.14f, 0.14f, 0.064f),
                    4)
            };
        }
    }
}
