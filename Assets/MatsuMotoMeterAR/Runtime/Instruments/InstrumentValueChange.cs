namespace MatsuMotoMeterAR.Instruments
{
    public enum InstrumentValueChangeOrigin
    {
        Programmatic = 0,
        UserInteraction = 1,
        SignalGraph = 2,
        Restore = 3,
        ThemeChange = 4
    }

    public readonly struct InstrumentValueChange
    {
        public InstrumentValueChange(
            MockInstrumentMotion.MotionKind motionKind,
            float previousValue,
            float currentValue,
            int previousDetent,
            int currentDetent,
            InstrumentValueChangeOrigin origin)
        {
            MotionKind = motionKind;
            PreviousValue = previousValue;
            CurrentValue = currentValue;
            PreviousDetent = previousDetent;
            CurrentDetent = currentDetent;
            Origin = origin;
        }

        public MockInstrumentMotion.MotionKind MotionKind { get; }
        public float PreviousValue { get; }
        public float CurrentValue { get; }
        public int PreviousDetent { get; }
        public int CurrentDetent { get; }
        public InstrumentValueChangeOrigin Origin { get; }
    }
}
