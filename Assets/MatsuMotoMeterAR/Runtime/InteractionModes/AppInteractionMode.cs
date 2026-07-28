namespace MatsuMotoMeterAR.InteractionModes
{
    public enum AppInteractionMode
    {
        Operation = 0,
        Edit = 1
    }

    public static class AppInteractionModePolicy
    {
        public static AppInteractionMode DefaultMode => AppInteractionMode.Operation;

        public static bool AllowsEditing(AppInteractionMode mode)
        {
            return mode == AppInteractionMode.Edit;
        }

        public static bool AllowsInstrumentOperation(AppInteractionMode mode)
        {
            return mode == AppInteractionMode.Operation;
        }

        public static AppInteractionMode Toggle(AppInteractionMode mode)
        {
            return mode == AppInteractionMode.Edit
                ? AppInteractionMode.Operation
                : AppInteractionMode.Edit;
        }
    }
}
