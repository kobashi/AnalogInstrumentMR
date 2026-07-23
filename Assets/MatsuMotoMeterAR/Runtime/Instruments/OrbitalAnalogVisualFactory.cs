using MatsuMotoMeterAR.Rendering;
using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    internal static class InstrumentThemeVisualFactory
    {
        private static readonly Color PreviewGreen = new(0.1f, 0.95f, 0.45f);

        public static bool TryBuild(
            MockInstrumentKind kind,
            MockInstrumentTheme theme,
            Transform visualSocket,
            Transform logic,
            bool preview)
        {
            var resourcePath =
                $"{ThemeFolder(theme)}/Prefabs/{PrefabName(kind, theme)}";
            var prefab = Resources.Load<GameObject>(resourcePath);
            if (prefab == null)
            {
                Debug.LogWarning(
                    $"{theme} visual prefab is missing for {kind}; " +
                    "using the primitive fallback.");
                return false;
            }

            var visual = Object.Instantiate(prefab, visualSocket, false);
            visual.name = prefab.name;
            var manifest = visual.GetComponent<ThemeVisualManifest>();
            if (manifest == null || manifest.MotionTarget == null)
            {
                Object.DestroyImmediate(visual);
                throw new MissingReferenceException(
                    $"{theme} prefab {prefab.name} has no valid visual manifest.");
            }
            foreach (var collider in visual.GetComponentsInChildren<Collider>(true))
                DestroyComponent(collider);

            if (preview)
            {
                foreach (var renderer in visual.GetComponentsInChildren<Renderer>(true))
                {
                    RuntimeMaterialUtility.SetColor(renderer, PreviewGreen);
                    RuntimeMaterialUtility.SetEmissionColor(renderer, PreviewGreen);
                }
                return true;
            }

            ConfigureMotion(kind, theme, manifest, logic);
            return true;
        }

        private static void ConfigureMotion(
            MockInstrumentKind kind,
            MockInstrumentTheme theme,
            ThemeVisualManifest manifest,
            Transform logic)
        {
            switch (kind)
            {
                case MockInstrumentKind.RoundMeter:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Meter,
                        manifest.MotionTarget,
                        Vector3.up,
                        55f,
                        0.18f);
                    break;
                case MockInstrumentKind.Lever:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Lever,
                        manifest.MotionTarget,
                        Vector3.right,
                        32f,
                        0.14f);
                    break;
                case MockInstrumentKind.ToggleSwitch:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Toggle,
                        manifest.MotionTarget,
                        Vector3.right,
                        28f,
                        0.2f);
                    break;
                case MockInstrumentKind.RotaryKnob:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Rotate,
                        manifest.MotionTarget,
                        Vector3.up,
                        48f,
                        1f);
                    break;
                case MockInstrumentKind.PushButton:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Press,
                        manifest.MotionTarget,
                        Vector3.up,
                        0.014f,
                        0.3f);
                    break;
                case MockInstrumentKind.IndicatorLamp:
                    var warning =
                        MockInstrumentThemeCatalog.GetPalette(theme).Warning;
                    GetOrAddMotion(logic).Configure(
                        MockInstrumentMotion.MotionKind.Pulse,
                        manifest.MotionTarget,
                        Vector3.forward,
                        1f,
                        0.55f,
                        manifest.IndicatorRenderer,
                        warning);
                    break;
            }
        }

        private static void AddMotion(
            Transform logic,
            MockInstrumentMotion.MotionKind kind,
            Transform movingPart,
            Vector3 axis,
            float range,
            float frequency)
        {
            GetOrAddMotion(logic).Configure(
                kind,
                movingPart,
                axis,
                range,
                frequency);
        }

        private static MockInstrumentMotion GetOrAddMotion(Transform logic)
        {
            var motion = logic.GetComponent<MockInstrumentMotion>();
            return motion != null
                ? motion
                : logic.gameObject.AddComponent<MockInstrumentMotion>();
        }

        private static string PrefabName(
            MockInstrumentKind kind,
            MockInstrumentTheme theme)
        {
            var key = kind switch
            {
                MockInstrumentKind.Lever => "Lever",
                MockInstrumentKind.ToggleSwitch => "Toggle",
                MockInstrumentKind.RotaryKnob => "Rotary",
                MockInstrumentKind.PushButton => "Button",
                MockInstrumentKind.IndicatorLamp => "Lamp",
                _ => "MeterRound"
            };
            return $"PF_Visual_{key}_{ThemeFolder(theme)}";
        }

        private static string ThemeFolder(MockInstrumentTheme theme)
        {
            return theme switch
            {
                MockInstrumentTheme.ForgeBrass => "ForgeBrass",
                MockInstrumentTheme.KineticSafety => "KineticSafety",
                _ => "OrbitalAnalog"
            };
        }

        private static void DestroyComponent(Component component)
        {
            if (Application.isPlaying)
                Object.Destroy(component);
            else
                Object.DestroyImmediate(component);
        }
    }
}
