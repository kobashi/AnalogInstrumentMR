using MatsuMotoMeterAR.Rendering;
using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public static class MockInstrumentFactory
    {
        private static readonly Color PreviewGreen = new(0.1f, 0.95f, 0.45f);

        public static GameObject Create(
            MockInstrumentKind kind,
            Pose pose,
            bool preview = false,
            MockInstrumentTheme theme = MockInstrumentThemeCatalog.DefaultTheme)
        {
            theme = MockInstrumentThemeCatalog.Normalize(theme);
            var root = new GameObject(
                preview
                    ? $"{MockInstrumentCatalog.GetDisplayName(kind)} Preview"
                    : MockInstrumentCatalog.GetDisplayName(kind));
            root.transform.SetPositionAndRotation(pose.position, pose.rotation);
            var mountOrigin = CreateSocket(root.transform, "MountOrigin");
            var logic = CreateSocket(root.transform, "Logic");
            var interaction = CreateSocket(root.transform, "Interaction");
            var visualSocket = CreateSocket(root.transform, "VisualSocket");
            var occlusionProxy = CreateSocket(root.transform, "OcclusionProxy");
            var labelSocket = CreateSocket(root.transform, "LabelSocket");
            var audioSocket = CreateSocket(root.transform, "AudioSocket");
            var vfxSocket = CreateSocket(root.transform, "VfxSocket");
            var colliderObject = new GameObject("InteractionCollider");
            colliderObject.transform.SetParent(interaction, false);
            var interactionCollider = colliderObject.AddComponent<BoxCollider>();
            var spec = InstrumentGreyboxSpecification.Get(kind);
            interactionCollider.center = spec.InteractionCenter;
            interactionCollider.size = spec.InteractionSize;
            BuildVisual(kind, theme, visualSocket, logic, preview);
            MockInstrumentInteraction instrumentInteraction = null;
            if (!preview)
            {
                var motion = logic.GetComponent<MockInstrumentMotion>();
                instrumentInteraction =
                    interaction.gameObject.AddComponent<MockInstrumentInteraction>();
                instrumentInteraction.Configure(motion, interactionCollider);
            }

            root.AddComponent<InstrumentGreyboxContract>().Configure(
                kind,
                theme,
                mountOrigin,
                logic,
                interaction,
                interactionCollider,
                instrumentInteraction,
                visualSocket,
                occlusionProxy,
                labelSocket,
                audioSocket,
                vfxSocket);

            if (preview)
                RemoveColliders(root);
            return root;
        }

        public static bool IsPlacementReady(
            MockInstrumentKind kind,
            MockInstrumentTheme theme)
        {
            return (kind != MockInstrumentKind.ThrottleLever &&
                    kind != MockInstrumentKind.PowerSlider) ||
                   InstrumentThemeVisualFactory.HasVisualPrefab(kind, theme);
        }

        public static bool ApplyTheme(
            GameObject instrument,
            MockInstrumentTheme theme,
            bool preview = false)
        {
            if (instrument == null)
                return false;

            var contract = instrument.GetComponent<InstrumentGreyboxContract>();
            if (contract == null ||
                contract.VisualSocket == null ||
                contract.Logic == null)
            {
                return false;
            }

            theme = MockInstrumentThemeCatalog.Normalize(theme);
            if (contract.Theme == theme)
                return true;

            for (var index = contract.VisualSocket.childCount - 1; index >= 0; index--)
            {
                var child = contract.VisualSocket.GetChild(index);
                child.gameObject.SetActive(false);
                child.SetParent(null, false);
                DestroyObject(child.gameObject);
            }

            BuildVisual(
                contract.Kind,
                theme,
                contract.VisualSocket,
                contract.Logic,
                preview);
            if (!preview && contract.InstrumentInteraction != null)
            {
                contract.InstrumentInteraction.Configure(
                    contract.Logic.GetComponent<MockInstrumentMotion>(),
                    contract.InteractionCollider);
            }
            contract.SetTheme(theme);
            return true;
        }

        public static void Destroy(GameObject instrument)
        {
            if (instrument == null)
                return;

            Object.Destroy(instrument);
        }

        private static void BuildVisual(
            MockInstrumentKind kind,
            MockInstrumentTheme theme,
            Transform visualSocket,
            Transform logic,
            bool preview)
        {
            if (InstrumentThemeVisualFactory.TryBuild(
                    kind,
                    theme,
                    visualSocket,
                    logic,
                    preview))
            {
                return;
            }

            var palette = MockInstrumentThemeCatalog.GetPalette(theme);
            switch (kind)
            {
                case MockInstrumentKind.Lever:
                    BuildLever(visualSocket, logic, preview, palette);
                    break;
                case MockInstrumentKind.ToggleSwitch:
                    BuildToggle(visualSocket, logic, preview, palette);
                    break;
                case MockInstrumentKind.RotaryKnob:
                    BuildRotary(visualSocket, logic, preview, palette);
                    break;
                case MockInstrumentKind.PushButton:
                    BuildPushButton(visualSocket, logic, preview, palette);
                    break;
                case MockInstrumentKind.IndicatorLamp:
                    BuildIndicatorLamp(visualSocket, logic, preview, palette);
                    break;
                case MockInstrumentKind.StatusIndicator:
                    BuildStatusIndicator(
                        visualSocket,
                        logic,
                        preview,
                        theme,
                        palette);
                    break;
                case MockInstrumentKind.ThrottleLever:
                    BuildThrottleCodeContract(
                        visualSocket,
                        logic,
                        preview,
                        theme);
                    break;
                case MockInstrumentKind.PowerSlider:
                    BuildPowerSliderCodeContract(
                        visualSocket,
                        logic,
                        preview,
                        theme);
                    break;
                case MockInstrumentKind.WindowMeter:
                    BuildWindowMeter(
                        visualSocket,
                        logic,
                        preview,
                        theme,
                        palette);
                    break;
                case MockInstrumentKind.WindowPanel:
                    BuildWindowPanel(
                        visualSocket,
                        logic,
                        preview,
                        theme,
                        palette);
                    break;
                default:
                    BuildRoundMeter(visualSocket, logic, preview, palette);
                    break;
            }
        }

        private static void DestroyObject(Object value)
        {
            if (Application.isPlaying)
                Object.Destroy(value);
            else
                Object.DestroyImmediate(value);
        }

        private static void BuildRoundMeter(
            Transform visual,
            Transform logic,
            bool preview,
            MockInstrumentThemeCatalog.Palette palette)
        {
            CreatePrimitive(
                PrimitiveType.Cylinder,
                "Backplate",
                visual,
                new Vector3(0f, 0f, 0.025f),
                new Vector3(0.14f, 0.018f, 0.14f),
                Quaternion.Euler(90f, 0f, 0f),
                ColorFor(preview, palette.Housing));

            CreatePrimitive(
                PrimitiveType.Cylinder,
                "Dial",
                visual,
                new Vector3(0f, 0f, 0.048f),
                new Vector3(0.115f, 0.006f, 0.115f),
                Quaternion.Euler(90f, 0f, 0f),
                ColorFor(preview, palette.Face));

            var pivot = CreatePivot(visual, "Needle Pivot", new Vector3(0f, 0f, 0.058f));
            CreatePrimitive(
                PrimitiveType.Cube,
                "Needle",
                pivot,
                new Vector3(0f, 0.052f, 0f),
                new Vector3(0.012f, 0.105f, 0.009f),
                Quaternion.identity,
                ColorFor(preview, palette.Primary));
            CreatePrimitive(
                PrimitiveType.Sphere,
                "Needle Hub",
                pivot,
                Vector3.zero,
                Vector3.one * 0.026f,
                Quaternion.identity,
                ColorFor(preview, palette.Dark));

            if (!preview)
            {
                GetOrAddMotion(logic).Configure(
                    MockInstrumentMotion.MotionKind.Meter,
                    pivot,
                    Vector3.forward,
                    55f,
                    0.18f);
            }
        }

        private static void BuildLever(
            Transform visual,
            Transform logic,
            bool preview,
            MockInstrumentThemeCatalog.Palette palette)
        {
            CreatePrimitive(
                PrimitiveType.Cube,
                "Base",
                visual,
                new Vector3(0f, 0f, 0.025f),
                new Vector3(0.18f, 0.14f, 0.05f),
                Quaternion.identity,
                ColorFor(preview, palette.Housing));
            var pivot = CreatePivot(visual, "Handle Pivot", new Vector3(0f, -0.025f, 0.065f));
            CreatePrimitive(
                PrimitiveType.Cylinder,
                "Handle",
                pivot,
                new Vector3(0f, 0.075f, 0f),
                new Vector3(0.018f, 0.075f, 0.018f),
                Quaternion.identity,
                ColorFor(preview, palette.Face));
            CreatePrimitive(
                PrimitiveType.Sphere,
                "Grip",
                pivot,
                new Vector3(0f, 0.16f, 0f),
                Vector3.one * 0.052f,
                Quaternion.identity,
                ColorFor(preview, palette.Primary));
            if (!preview)
            {
                GetOrAddMotion(logic).Configure(
                    MockInstrumentMotion.MotionKind.Lever,
                    pivot,
                    Vector3.right,
                    InstrumentGreyboxSpecification.LeverMaximumAngleDegrees,
                    0.14f,
                    rotationOffset:
                        -InstrumentGreyboxSpecification.LeverMaximumAngleDegrees);
            }
        }

        private static void BuildToggle(
            Transform visual,
            Transform logic,
            bool preview,
            MockInstrumentThemeCatalog.Palette palette)
        {
            CreatePrimitive(
                PrimitiveType.Cube,
                "Base",
                visual,
                new Vector3(0f, 0f, 0.018f),
                new Vector3(0.12f, 0.14f, 0.036f),
                Quaternion.identity,
                ColorFor(preview, palette.Housing));
            var pivot = CreatePivot(visual, "Toggle Pivot", new Vector3(0f, 0f, 0.05f));
            CreatePrimitive(
                PrimitiveType.Cylinder,
                "Toggle",
                pivot,
                new Vector3(0f, 0.045f, 0f),
                new Vector3(0.013f, 0.05f, 0.013f),
                Quaternion.identity,
                ColorFor(preview, palette.Face));
            if (!preview)
            {
                GetOrAddMotion(logic).Configure(
                    MockInstrumentMotion.MotionKind.Toggle,
                    pivot,
                    Vector3.right,
                    28f,
                    0.2f,
                    rotationOffset: -28f);
            }
        }

        private static void BuildRotary(
            Transform visual,
            Transform logic,
            bool preview,
            MockInstrumentThemeCatalog.Palette palette)
        {
            CreatePrimitive(
                PrimitiveType.Cube,
                "Base",
                visual,
                new Vector3(0f, 0f, 0.02f),
                new Vector3(0.15f, 0.15f, 0.04f),
                Quaternion.identity,
                ColorFor(preview, palette.Housing));
            var pivot = CreatePivot(visual, "Knob Pivot", new Vector3(0f, 0f, 0.065f));
            CreatePrimitive(
                PrimitiveType.Cylinder,
                "Knob",
                pivot,
                Vector3.zero,
                new Vector3(0.052f, 0.03f, 0.052f),
                Quaternion.Euler(90f, 0f, 0f),
                ColorFor(preview, palette.Dark));
            CreatePrimitive(
                PrimitiveType.Cube,
                "Index",
                pivot,
                new Vector3(0f, 0.026f, 0.033f),
                new Vector3(0.009f, 0.045f, 0.008f),
                Quaternion.identity,
                ColorFor(preview, palette.Face));
            if (!preview)
            {
                GetOrAddMotion(logic).Configure(
                    MockInstrumentMotion.MotionKind.Rotate,
                    pivot,
                    Vector3.forward,
                    48f,
                    1f);
            }
        }

        private static void BuildPushButton(
            Transform visual,
            Transform logic,
            bool preview,
            MockInstrumentThemeCatalog.Palette palette)
        {
            CreatePrimitive(
                PrimitiveType.Cube,
                "Base",
                visual,
                new Vector3(0f, 0f, 0.02f),
                new Vector3(0.13f, 0.13f, 0.04f),
                Quaternion.identity,
                ColorFor(preview, palette.Housing));
            var button = CreatePrimitive(
                PrimitiveType.Cylinder,
                "Button",
                visual,
                new Vector3(0f, 0f, 0.065f),
                new Vector3(0.043f, 0.025f, 0.043f),
                Quaternion.Euler(90f, 0f, 0f),
                ColorFor(preview, palette.Primary));
            if (!preview)
            {
                GetOrAddMotion(logic).Configure(
                    MockInstrumentMotion.MotionKind.Press,
                    button.transform,
                    Vector3.back,
                    0.014f,
                    0.3f);
            }
        }

        private static void BuildIndicatorLamp(
            Transform visual,
            Transform logic,
            bool preview,
            MockInstrumentThemeCatalog.Palette palette)
        {
            CreatePrimitive(
                PrimitiveType.Cube,
                "Base",
                visual,
                new Vector3(0f, 0f, 0.018f),
                new Vector3(0.14f, 0.11f, 0.036f),
                Quaternion.identity,
                ColorFor(preview, palette.Housing));
            var lens = CreatePrimitive(
                PrimitiveType.Sphere,
                "Lens",
                visual,
                new Vector3(0f, 0f, 0.062f),
                new Vector3(0.065f, 0.065f, 0.04f),
                Quaternion.identity,
                ColorFor(preview, palette.Warning));
            if (!preview)
            {
                GetOrAddMotion(logic).Configure(
                    MockInstrumentMotion.MotionKind.Pulse,
                    lens.transform,
                    Vector3.forward,
                    1f,
                    0.55f,
                    lens.GetComponent<Renderer>(),
                    palette.Warning);
            }
        }

        private static void BuildStatusIndicator(
            Transform visual,
            Transform logic,
            bool preview,
            MockInstrumentTheme theme,
            MockInstrumentThemeCatalog.Palette palette)
        {
            var visualRoot = new GameObject(
                $"PF_Visual_StatusIndicator_{RuntimeThemeName(theme)}");
            visualRoot.transform.SetParent(visual, false);
            var housingDepth = theme == MockInstrumentTheme.ForgeBrass
                ? 0.050f
                : 0.044f;
            var lensScale = theme switch
            {
                MockInstrumentTheme.ForgeBrass =>
                    new Vector3(0.068f, 0.068f, 0.038f),
                MockInstrumentTheme.KineticSafety =>
                    new Vector3(0.120f, 0.045f, 0.035f),
                _ => new Vector3(0.090f, 0.060f, 0.038f)
            };
            CreatePrimitive(
                PrimitiveType.Cube,
                "Status Housing",
                visualRoot.transform,
                new Vector3(0f, 0f, housingDepth * 0.5f),
                new Vector3(0.18f, 0.12f, housingDepth),
                Quaternion.identity,
                ColorFor(preview, palette.Housing));
            var lens = CreatePrimitive(
                PrimitiveType.Sphere,
                "RGB Status Lens",
                visualRoot.transform,
                new Vector3(0f, 0f, housingDepth + 0.006f),
                lensScale,
                Quaternion.identity,
                preview ? PreviewGreen : Color.black);
            var lensRenderer = lens.GetComponent<Renderer>();
            visualRoot.AddComponent<ThemeVisualManifest>().Configure(
                lens.transform,
                lensRenderer);

            if (!preview)
            {
                GetOrAddMotion(logic).ConfigureStatus(
                    lens.transform,
                    lensRenderer,
                    palette.Ready,
                    palette.Warning,
                    palette.Primary);
            }
        }

        private static void BuildThrottleCodeContract(
            Transform visual,
            Transform logic,
            bool preview,
            MockInstrumentTheme theme)
        {
            var visualRoot = new GameObject(
                $"PF_Visual_Throttle_{RuntimeThemeName(theme)}");
            visualRoot.transform.SetParent(visual, false);
            var pivot = CreatePivot(
                visualRoot.transform,
                "throttle_pivot",
                Vector3.zero);
            visualRoot.AddComponent<ThemeVisualManifest>().Configure(pivot);

            if (!preview)
            {
                GetOrAddMotion(logic).Configure(
                    MockInstrumentMotion.MotionKind.Throttle,
                    pivot,
                    Vector3.right,
                    InstrumentGreyboxSpecification
                        .ThrottleMaximumAngleDegrees,
                    0f,
                    rotationOffset:
                        -InstrumentGreyboxSpecification
                            .ThrottleMaximumAngleDegrees);
            }
        }

        private static void BuildPowerSliderCodeContract(
            Transform visual,
            Transform logic,
            bool preview,
            MockInstrumentTheme theme)
        {
            var visualRoot = new GameObject(
                $"PF_Visual_PowerSlider_{RuntimeThemeName(theme)}");
            visualRoot.transform.SetParent(visual, false);
            var travel = CreatePivot(
                visualRoot.transform,
                "slider_travel",
                Vector3.zero);
            visualRoot.AddComponent<ThemeVisualManifest>().Configure(travel);

            if (!preview)
            {
                GetOrAddMotion(logic).Configure(
                    MockInstrumentMotion.MotionKind.PowerSlider,
                    travel,
                    Vector3.up,
                    InstrumentGreyboxSpecification.PowerSliderTravelMeters,
                    0f);
            }
        }

        private static void BuildWindowMeter(
            Transform visual,
            Transform logic,
            bool preview,
            MockInstrumentTheme theme,
            MockInstrumentThemeCatalog.Palette palette)
        {
            var housingDepth = theme switch
            {
                MockInstrumentTheme.ForgeBrass => 0.11f,
                MockInstrumentTheme.KineticSafety => 0.10f,
                _ => 0.065f
            };
            CreatePrimitive(
                PrimitiveType.Cube,
                "Window Meter Housing",
                visual,
                new Vector3(0f, 0f, housingDepth * 0.5f),
                new Vector3(1.20f, 0.75f, housingDepth),
                Quaternion.identity,
                ColorFor(preview, palette.Housing));

            var dialDepth = 0.028f;
            var dialPosition = new Vector3(
                0f,
                0f,
                housingDepth + dialDepth * 0.5f);
            if (theme == MockInstrumentTheme.KineticSafety)
            {
                CreatePrimitive(
                    PrimitiveType.Cube,
                    "Guarded Dial Recess",
                    visual,
                    dialPosition,
                    new Vector3(0.72f, 0.58f, dialDepth),
                    Quaternion.identity,
                    ColorFor(preview, palette.Dark));
            }
            else
            {
                CreatePrimitive(
                    PrimitiveType.Cylinder,
                    "Deep Circular Dial",
                    visual,
                    dialPosition,
                    new Vector3(0.66f, dialDepth, 0.66f),
                    Quaternion.Euler(90f, 0f, 0f),
                    ColorFor(preview, palette.Dark));
            }

            var pivot = CreatePivot(
                visual,
                "Window Needle Pivot",
                new Vector3(0f, -0.08f, housingDepth + dialDepth + 0.008f));
            CreatePrimitive(
                PrimitiveType.Cube,
                "Window Needle",
                pivot,
                new Vector3(0f, 0.24f, 0f),
                new Vector3(0.026f, 0.48f, 0.014f),
                Quaternion.identity,
                ColorFor(
                    preview,
                    theme == MockInstrumentTheme.KineticSafety
                        ? palette.Warning
                        : palette.Primary));
            CreatePrimitive(
                PrimitiveType.Sphere,
                "Window Needle Hub",
                pivot,
                Vector3.zero,
                Vector3.one * 0.075f,
                Quaternion.identity,
                ColorFor(preview, palette.Face));

            if (!preview)
            {
                GetOrAddMotion(logic).Configure(
                    MockInstrumentMotion.MotionKind.Meter,
                    pivot,
                    Vector3.forward,
                    55f,
                    0.12f);
            }
        }

        private static void BuildWindowPanel(
            Transform visual,
            Transform logic,
            bool preview,
            MockInstrumentTheme theme,
            MockInstrumentThemeCatalog.Palette palette)
        {
            var housingDepth = theme switch
            {
                MockInstrumentTheme.ForgeBrass => 0.14f,
                MockInstrumentTheme.KineticSafety => 0.13f,
                _ => 0.08f
            };
            CreatePrimitive(
                PrimitiveType.Cube,
                "Recessed Hull Information Field",
                visual,
                new Vector3(0f, 0f, housingDepth * 0.5f),
                new Vector3(1.60f, 0.90f, housingDepth),
                Quaternion.identity,
                ColorFor(
                    preview,
                    theme == MockInstrumentTheme.OrbitalAnalog
                        ? palette.Dark
                        : palette.Housing));

            var guardColor = theme switch
            {
                MockInstrumentTheme.ForgeBrass => palette.Face,
                MockInstrumentTheme.KineticSafety => palette.Warning,
                _ => palette.Face
            };
            var guardWidth =
                theme == MockInstrumentTheme.OrbitalAnalog ? 0.035f : 0.075f;
            CreatePrimitive(
                PrimitiveType.Cube,
                "Left Frame Rail",
                visual,
                new Vector3(-0.70f, 0f, housingDepth + 0.045f),
                new Vector3(guardWidth, 0.72f, 0.05f),
                Quaternion.identity,
                ColorFor(preview, guardColor));
            CreatePrimitive(
                PrimitiveType.Cube,
                "Right Frame Rail",
                visual,
                new Vector3(0.70f, 0f, housingDepth + 0.045f),
                new Vector3(guardWidth, 0.72f, 0.05f),
                Quaternion.identity,
                ColorFor(preview, guardColor));

            var pivot = CreatePivot(
                visual,
                "Panel Vane Pivot",
                new Vector3(0f, -0.18f, housingDepth + 0.055f));
            CreatePrimitive(
                PrimitiveType.Cube,
                "Panel Status Vane",
                pivot,
                new Vector3(0f, 0.25f, 0f),
                new Vector3(0.035f, 0.50f, 0.018f),
                Quaternion.identity,
                ColorFor(
                    preview,
                    theme == MockInstrumentTheme.OrbitalAnalog
                        ? palette.Primary
                        : palette.Warning));

            if (!preview)
            {
                GetOrAddMotion(logic).Configure(
                    MockInstrumentMotion.MotionKind.Meter,
                    pivot,
                    Vector3.forward,
                    42f,
                    0.1f);
            }
        }

        private static Transform CreatePivot(Transform parent, string name, Vector3 position)
        {
            var pivot = new GameObject(name).transform;
            pivot.SetParent(parent, false);
            pivot.localPosition = position;
            return pivot;
        }

        private static string RuntimeThemeName(MockInstrumentTheme theme)
        {
            return theme switch
            {
                MockInstrumentTheme.ForgeBrass => "ForgeBrass",
                MockInstrumentTheme.KineticSafety => "KineticSafety",
                _ => "OrbitalAnalog"
            };
        }

        private static MockInstrumentMotion GetOrAddMotion(Transform logic)
        {
            var motion = logic.GetComponent<MockInstrumentMotion>();
            return motion != null
                ? motion
                : logic.gameObject.AddComponent<MockInstrumentMotion>();
        }

        private static Transform CreateSocket(Transform parent, string name)
        {
            var socket = new GameObject(name).transform;
            socket.SetParent(parent, false);
            return socket;
        }

        private static GameObject CreatePrimitive(
            PrimitiveType type,
            string name,
            Transform parent,
            Vector3 localPosition,
            Vector3 localScale,
            Quaternion localRotation,
            Color color)
        {
            var instance = GameObject.CreatePrimitive(type);
            instance.name = name;
            instance.transform.SetParent(parent, false);
            instance.transform.localPosition = localPosition;
            instance.transform.localRotation = localRotation;
            instance.transform.localScale = localScale;
            var primitiveCollider = instance.GetComponent<Collider>();
            if (primitiveCollider != null)
                DestroyComponent(primitiveCollider);
            RuntimeMaterialUtility.ApplySharedUnlit(instance.GetComponent<Renderer>(), color);
            return instance;
        }

        private static Color ColorFor(bool preview, Color normal)
        {
            return preview ? PreviewGreen : normal;
        }

        private static void RemoveColliders(GameObject root)
        {
            foreach (var collider in root.GetComponentsInChildren<Collider>())
            {
                collider.enabled = false;
                DestroyComponent(collider);
            }
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
