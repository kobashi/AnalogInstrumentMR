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
            if (kind == MockInstrumentKind.WindowMeter ||
                kind == MockInstrumentKind.WindowPanel ||
                kind == MockInstrumentKind.StatusIndicator)
            {
                return false;
            }

            var resourcePath =
                $"{ThemeFolder(theme)}/Prefabs/{PrefabName(kind, theme)}";
            var prefab = Resources.Load<GameObject>(resourcePath);
            if (prefab == null)
            {
                if (kind != MockInstrumentKind.ThrottleLever &&
                    kind != MockInstrumentKind.PowerSlider)
                {
                    Debug.LogWarning(
                        $"{theme} visual prefab is missing for {kind}; " +
                        "using the primitive fallback.");
                }
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

        public static bool HasVisualPrefab(
            MockInstrumentKind kind,
            MockInstrumentTheme theme)
        {
            var resourcePath =
                $"{ThemeFolder(theme)}/Prefabs/{PrefabName(kind, theme)}";
            return Resources.Load<GameObject>(resourcePath) != null;
        }

        private static void ConfigureMotion(
            MockInstrumentKind kind,
            MockInstrumentTheme theme,
            ThemeVisualManifest manifest,
            Transform logic)
        {
            var motionTarget = CreateRuntimeMotionTarget(
                manifest.MotionTarget,
                manifest.transform);
            switch (kind)
            {
                case MockInstrumentKind.RoundMeter:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Meter,
                        motionTarget,
                        Vector3.forward,
                        55f,
                        0.18f);
                    break;
                case MockInstrumentKind.Lever:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Lever,
                        motionTarget,
                        Vector3.right,
                        InstrumentGreyboxSpecification.LeverMaximumAngleDegrees,
                        0.14f,
                        -InstrumentGreyboxSpecification.LeverMaximumAngleDegrees);
                    break;
                case MockInstrumentKind.ToggleSwitch:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Toggle,
                        motionTarget,
                        Vector3.right,
                        28f,
                        0.2f,
                        -28f);
                    break;
                case MockInstrumentKind.RotaryKnob:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Rotate,
                        motionTarget,
                        Vector3.forward,
                        48f,
                        1f);
                    break;
                case MockInstrumentKind.PushButton:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Press,
                        motionTarget,
                        Vector3.back,
                        0.014f,
                        0.3f);
                    break;
                case MockInstrumentKind.IndicatorLamp:
                    var warning =
                        MockInstrumentThemeCatalog.GetPalette(theme).Warning;
                    GetOrAddMotion(logic).Configure(
                        MockInstrumentMotion.MotionKind.Pulse,
                        motionTarget,
                        Vector3.forward,
                        1f,
                        0.55f,
                        manifest.IndicatorRenderer,
                        warning);
                    break;
                case MockInstrumentKind.ThrottleLever:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Throttle,
                        motionTarget,
                        Vector3.right,
                        InstrumentGreyboxSpecification
                            .ThrottleMaximumAngleDegrees,
                        0f,
                        -InstrumentGreyboxSpecification
                            .ThrottleMaximumAngleDegrees);
                    break;
                case MockInstrumentKind.PowerSlider:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.PowerSlider,
                        motionTarget,
                        Vector3.up,
                        InstrumentGreyboxSpecification
                            .PowerSliderTravelMeters,
                        0f);
                    break;
            }
        }

        private static Transform CreateRuntimeMotionTarget(
            Transform source,
            Transform coordinateRoot)
        {
            var proxy = new GameObject(
                $"{source.name} Runtime Motion").transform;
            proxy.SetParent(coordinateRoot, false);
            proxy.position = source.position;
            proxy.rotation = coordinateRoot.rotation;
            proxy.localScale = Vector3.one;

            source.SetParent(proxy, true);
            return proxy;
        }

        private static void AddMotion(
            Transform logic,
            MockInstrumentMotion.MotionKind kind,
            Transform movingPart,
            Vector3 axis,
            float range,
            float frequency,
            float rotationOffset = 0f)
        {
            GetOrAddMotion(logic).Configure(
                kind,
                movingPart,
                axis,
                range,
                frequency,
                rotationOffset: rotationOffset);
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
                MockInstrumentKind.ThrottleLever => "Throttle",
                MockInstrumentKind.PowerSlider => "PowerSlider",
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
