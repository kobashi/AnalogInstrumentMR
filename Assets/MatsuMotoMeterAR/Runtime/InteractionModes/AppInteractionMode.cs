namespace MatsuMotoMeterAR.InteractionModes
{
    public enum AppInteractionMode
    {
        Operation = 0,
        Edit = 1,
        Connect = 2
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

        public static bool AllowsConnecting(AppInteractionMode mode)
        {
            return mode == AppInteractionMode.Connect;
        }

        public static AppInteractionMode Toggle(AppInteractionMode mode)
        {
            return mode switch
            {
                AppInteractionMode.Operation => AppInteractionMode.Edit,
                AppInteractionMode.Edit => AppInteractionMode.Connect,
                _ => AppInteractionMode.Operation
            };
        }
    }
}
