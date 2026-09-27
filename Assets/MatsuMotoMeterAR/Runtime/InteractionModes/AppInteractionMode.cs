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

        public static bool AllowsConnecting(
            AppInteractionMode mode,
            bool connectionEditing)
        {
            return mode == AppInteractionMode.Edit && connectionEditing;
        }

        public static bool CanToggleConnectionVisuals(
            AppInteractionMode mode,
            bool modeSwitchLocked)
        {
            return mode == AppInteractionMode.Operation && modeSwitchLocked;
        }

        public static bool CanRequestApplicationExit(
            AppInteractionMode mode,
            bool globalSettingsVisible)
        {
            return mode == AppInteractionMode.Operation &&
                   globalSettingsVisible;
        }

        public static bool ShowsConnectionVisuals(
            AppInteractionMode mode,
            bool operationConnectionVisualsVisible,
            bool connectionEditing)
        {
            return AllowsConnecting(mode, connectionEditing) ||
                   (mode == AppInteractionMode.Operation &&
                    operationConnectionVisualsVisible);
        }

        public static AppInteractionMode Toggle(AppInteractionMode mode)
        {
            return mode == AppInteractionMode.Operation
                ? AppInteractionMode.Edit
                : AppInteractionMode.Operation;
        }
    }
}
