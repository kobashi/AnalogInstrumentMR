using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public static class MockRoundMeterFactory
    {
        public const string InstrumentTypeId = "meter.round";

        public static GameObject Create(Pose pose, bool preview = false)
        {
            return MockInstrumentFactory.Create(
                MockInstrumentKind.RoundMeter,
                pose,
                preview);
        }
    }
}
