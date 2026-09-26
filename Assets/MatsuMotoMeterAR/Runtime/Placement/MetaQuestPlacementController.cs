using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using MatsuMotoMeterAR.Anchors;
using MatsuMotoMeterAR.Audio;
using MatsuMotoMeterAR.Development;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.InteractionModes;
using MatsuMotoMeterAR.PlacementPersistence;
using MatsuMotoMeterAR.Rendering;
using MatsuMotoMeterAR.Signals;
using Meta.XR.MRUtilityKit;
using UnityEngine;
using UnityEngine.InputSystem;

namespace MatsuMotoMeterAR.Placement
{
    public sealed class MetaQuestPlacementController : MonoBehaviour
    {
        private const float MaxPlacementDistance = 10f;
        private const float MaxInteractionDistance = 5f;
        private const float SurfaceOffset = 0.015f;
        private const float SelectionThreshold = 0.65f;
        private const float SelectionReleaseThreshold = 0.3f;
        private const float TriggerPressThreshold = 0.65f;
        private const float TriggerReleaseThreshold = 0.35f;
        private const float DirectTipOffset = 0.06f;
        private const float DirectContactRadius = 0.05f;
        private const float ThrottleGripContactPadding = 0.045f;
        private const float LeverGripContactPadding = 0.04f;
        private const float PowerSliderGripContactPadding = 0.035f;
        private const float HapticDuration = 0.06f;
        private const float PlacementSpacing = 0.012f;
        private const float CollisionMargin = 0.002f;
        private const float SelectionMarkerPadding = 0.012f;
        private const int AutoPlacementMaximumRing = 4;
        private const float CoplanarDistanceTolerance = 0.15f;
        private const float CoplanarNormalDotThreshold = 0.95f;
        private const float PlacementGridSpacing = 0.10f;
        private const float AutoAlignSearchRadius = 1.0f;
        private const float OperationGripPressThreshold = 0.65f;
        private const float OperationGripReleaseThreshold = 0.35f;
        private const float OperationChordWindowSeconds = 0.12f;
        private const float LeverGripTravelMeters = 0.24f;
        private const float RotaryGripTravelDegrees = 180f;
        private const float SharedAnchorCoverageRadius = 2.75f;
        private const int MaximumEditHistory = 32;
        private const float ControllerBeamStartOffset = 0.035f;
        private const float ControllerBeamWidth = 0.004f;
        private const float ExitHoldSeconds = 2f;
        private const float ModeLockHoldSeconds = 2f;
        private const float OperationFaceButtonHoldSeconds = 1f;
        private const float OperationStickDeadZone = 0.18f;
        private const float OperationStickSnapThreshold = 0.72f;
        private const float OperationStickSpeed = 0.55f;
        private const float MoveTargetWidth = 0.008f;
        private const float SurfaceWireframeWidth = 0.006f;
        private const float SurfaceSwitchImmediateAdvantage = 0.12f;
        private const int SurfaceSwitchConfirmationFrames = 4;
        private const int SurfaceMissToleranceFrames = 3;
        private const float CurrentRoomPollSeconds = 0.5f;
        private const float CurrentRoomSwitchDebounceSeconds = 1f;

        private static readonly Color EditBeamColor =
            new(1f, 0.65f, 0.05f, 1f);
        private static readonly Color OperationBeamColor =
            new(0.05f, 0.9f, 1f, 1f);
        private static readonly Color ConnectBeamColor =
            new(0.2f, 1f, 0.55f, 1f);
        private static readonly Color ConnectSourceColor =
            new(0.05f, 0.9f, 1f, 1f);
        private static readonly Color ConnectTargetColor =
            new(0.15f, 1f, 0.45f, 1f);
        private static readonly Color DirectConnectionColor =
            new(0.08f, 0.78f, 1f, 0.95f);
        private static readonly Color InvertConnectionColor =
            new(0.95f, 0.20f, 1f, 0.95f);
        private static readonly Color RangeConnectionColor =
            new(0.16f, 1f, 0.38f, 0.95f);
        private static readonly Color ThresholdConnectionColor =
            new(1f, 0.38f, 0.06f, 0.95f);
        private static readonly Color ConnectionLineColor =
            DirectConnectionColor;
        private static readonly Color ConnectionEditObjectColor =
            new(1f, 0.55f, 0.12f, 1f);
        private static readonly Color AudioPatchColor =
            new(0.15f, 1f, 0.78f, 0.95f);
        private static readonly Color ControlPatchColor =
            new(1f, 0.76f, 0.12f, 0.95f);
        private static readonly Color ClockPatchColor =
            new(0.67f, 0.38f, 1f, 0.95f);
        private static readonly Color GatePatchColor =
            new(0.24f, 1f, 0.42f, 0.95f);
        private static readonly Color TriggerPatchColor =
            new(1f, 0.42f, 0.10f, 0.95f);
        private static readonly Color SelectedAudioPatchColor =
            new(1f, 0.30f, 0.85f, 1f);

        private static readonly LabelFilter PlacementPlaneFilter = new(
            componentTypes: MRUKAnchor.ComponentType.Plane);
        private static readonly LabelFilter PlacementVolumeFilter = new(
            componentTypes: MRUKAnchor.ComponentType.Volume);

        private Transform rightControllerAnchor;
        private Transform leftControllerAnchor;
        private Transform rightAimAnchor;
        private Transform leftAimAnchor;
        private Transform trackingSpace;
        private TextMesh statusLabel;
        private GameObject globalAudioPanel;
        private TextMesh globalAudioPanelLabel;
        private LineRenderer controllerBeam;
        private LineRenderer leftControllerBeam;
        private MRUKRoom currentRoom;
        private MRUKRoom pendingCurrentRoom;
        private GameObject preview;
        private readonly List<GameObject> moveTargetMarkers = new();
        private readonly List<GameObject> surfaceWireframes = new();
        private readonly List<RuntimePlacement> placements = new();
        private readonly List<MockInstrumentInteraction> interactionCandidates = new();
        private readonly List<RuntimePlacement> groupMoveSelection = new();
        private readonly List<Pose> layoutSourcePoses = new();
        private readonly List<Pose> pendingLayoutTargetPoses = new();
        private readonly Dictionary<RuntimePlacement, GameObject> selectionMarkers = new();
        private readonly Dictionary<string, LineRenderer> connectionLines =
            new(StringComparer.Ordinal);
        private readonly HashSet<string> activeConnectionLineIds =
            new(StringComparer.Ordinal);
        private readonly List<string> staleConnectionLineIds = new();
        private readonly Dictionary<string, MockInstrumentInteraction>
            signalInteractions = new(StringComparer.Ordinal);
        private readonly Dictionary<string, SignalCompositionKind>
            signalCompositionKinds = new(StringComparer.Ordinal);
        private readonly Dictionary<string, ModularAudioModuleRuntime>
            modularAudioModules = new(StringComparer.Ordinal);
        private readonly Dictionary<string, ModularAudioGraphPlayer>
            modularAudioOutputs = new(StringComparer.Ordinal);
        private readonly ModularAudioPatchRuntime modularAudioPatchRuntime =
            new();
        private readonly List<RuntimePlacement> signalMonitorRefreshQueue = new();
        private readonly SignalMonitorRefreshScheduler
            signalMonitorRefreshScheduler = new();
        private readonly HashSet<string> windowPanelTargetIds =
            new(StringComparer.Ordinal);
        private readonly SignalGraphEvaluator signalGraphEvaluator = new();
        private readonly Stack<EditCommand> undoHistory = new();
        private readonly Stack<EditCommand> redoHistory = new();
        private IPlacementStore placementStore;
        private IAnchorService anchorService;
        private PlacementDocument placementDocument;
        private Pose currentPlacementPose;
        private SurfaceKind currentSurface;
        private MockInstrumentKind selectedKind = MockInstrumentKind.RoundMeter;
        private MockInstrumentTheme selectedTheme =
            MockInstrumentThemeCatalog.DefaultTheme;
        private AppInteractionMode interactionMode =
            AppInteractionModePolicy.DefaultMode;
        private RuntimePlacement activePlacement;
        private RuntimePlacement connectSource;
        private RuntimePlacement connectTarget;
        private RuntimePlacement connectEditPlacement;
        private GameObject connectSourceMarker;
        private GameObject connectTargetMarker;
        private GameObject connectEditMarker;
        private SignalConnectionRecord selectedConnectionForRemoval;
        private AudioPatchConnectionRecord selectedAudioPatchForRemoval;
        private SignalTransformKind pendingSignalTransform =
            SignalTransformKind.Direct;
        private SignalTransformKind selectedConnectionPendingTransform =
            SignalTransformKind.Direct;
        private int selectedConnectionPendingSlot =
            SignalConnectionRecord.AutomaticTargetInputSlot;
        private int selectedConnectionPendingPriority =
            SignalConnectionRecord.DefaultCompositionPriority;
        private SignalConnectionRecord connectionParameterDraft;
        private SignalConnectionParameterField connectionParameterField;
        private RuntimePlacement audioParameterEditPlacement;
        private PlacementRecord audioParameterOriginal;
        private int audioParameterEntryIndex;
        private int audioParameterStepIndex;
        private AdjustableParameterField audioParameterSettingField;
        private RuntimePlacement groupMovePivot;
        private RuntimePlacement lastAlignmentReference;
        private AlignmentAnchorMode nextAlignmentAnchorMode =
            AlignmentAnchorMode.Leading;
        private string lastAlignmentGroupSignature;
        private int lastAlignmentOriginalReferenceIndex;
        private float hapticStopTime;
        private float leftHapticStopTime;
        private float operationStepNoticeUntil;
        private float exitHoldTime;
        private float modeLockHoldTime;
        private float operationYHoldTime;
        private float connectStatusHoldUntil;
        private float nextCurrentRoomPollTime;
        private float pendingCurrentRoomSince;
        private PlacementSurfaceHit stablePlacementSurfaceHit;
        private PlacementSurfaceHit pendingPlacementSurfaceHit;
        private bool hasAlignmentCycle;
        private bool lastAlignmentVertical;
        private bool hasPlacementPose;
        private bool placementPoseWasAdjusted;
        private bool isAimingAtPlacedObject;
        private bool previousAButton;
        private bool previousBButton;
        private bool previousXButton;
        private bool previousYButton;
        private bool previousGroupMoveChord;
        private bool previousThumbstickButton;
        private bool previousLeftThumbstickButton;
        private bool previousEditTrigger;
        private bool previousLeftEditTrigger;
        private bool previousLeftEditGrip;
        private bool previousRightEditGrip;
        private bool operationYHoldLatched;
        private bool leftStickShortClickPending;
        private bool globalAudioPanelVisible;
        private bool audioMenuTriggerEngaged;
        private bool audioMenuGripEngaged;
        private bool pendingLeftSelection;
        private bool pendingMoveUndo;
        private bool pendingRightCancel;
        private float pendingLeftSelectionUntil;
        private float pendingMoveUndoUntil;
        private float pendingRightCancelUntil;
        private bool editMoveChordActive;
        private bool editMoveCancelledUntilChordRelease;
        private bool editPlacementModifierChordActive;
        private MovePlacementModifier editMoveModifier;
        private bool moveModifierAxisEngaged;
        private bool moveModifierApplied;
        private bool connectionEditing;
        private bool connectRightTriggerEngaged;
        private bool connectLeftTriggerEngaged;
        private bool connectAxisEngaged;
        private bool connectParameterFieldAxisEngaged;
        private bool connectSlotAxisEngaged;
        private bool connectTargetSettingAxisEngaged;
        private bool audioParameterFieldAxisEngaged;
        private bool audioParameterValueAxisEngaged;
        private bool pendingLfoAudioRate;
        private bool pendingObservableAudioSource;
        private int pendingObservableOutputIndex;
        private bool groupMoveArmed;
        private bool selectionAxisEngaged;
        private bool themeAxisEngaged;
        private bool alignmentAxisEngaged;
        private bool rotationAxisEngaged;
        private bool hasStablePlacementSurfaceHit;
        private bool hasPendingPlacementSurfaceHit;
        private PendingLayout pendingLayout;
        private bool operationInProgress;
        private bool isExiting;
        private bool modeSwitchLocked;
        private bool operationConnectionVisualsVisible;
        private bool modeLockHoldLatched;
        private bool roomSwitchInProgress;
        private int controllerPoseResyncFrames;
        private int stableSurfaceMissFrames;
        private int pendingSurfaceFrames;
        private InputAction rightPrimaryButtonAction;
        private InputAction rightSecondaryButtonAction;
        private InputAction leftPrimaryButtonAction;
        private InputAction leftSecondaryButtonAction;
        private InputAction rightThumbstickButtonAction;
        private InputAction leftThumbstickButtonAction;
        private InputAction rightThumbstickAction;
        private InputAction leftThumbstickAction;
        private InputAction rightTriggerAction;
        private InputAction leftTriggerAction;
        private InputAction rightGripAction;
        private InputAction leftGripAction;
        private InputAction rightPositionAction;
        private InputAction rightRotationAction;
        private InputAction leftPositionAction;
        private InputAction leftRotationAction;
        private InputAction rightPointerPositionAction;
        private InputAction rightPointerRotationAction;
        private InputAction leftPointerPositionAction;
        private InputAction leftPointerRotationAction;
        private readonly HandOperationState rightOperationHand = new(
            OVRInput.Controller.RTouch,
            "RIGHT");
        private readonly HandOperationState leftOperationHand = new(
            OVRInput.Controller.LTouch,
            "LEFT");

        private sealed class RuntimePlacement
        {
            public PlacementRecord Record;
            public AnchorRecord Anchor;
            public GameObject AnchorRoot;
            public GameObject Root;
            public InstrumentGreyboxContract Contract;
            public MockInstrumentInteraction Interaction;
            public InstrumentAudioController Audio;
            public ModularAudioModuleRuntime AudioModule;
            public ModularAudioGraphPlayer AudioGraphPlayer;
            public SignalMonitorView SignalMonitor;
            public WindowPanelSignalRuntime WindowPanelSignal;
            public WindowPanelGraphicsPrototypeView WindowPanelGraphic;
        }

        private sealed class HandOperationState
        {
            public readonly OVRInput.Controller Controller;
            public readonly string Label;
            public MockInstrumentInteraction GripInteraction;
            public MockInstrumentInteraction ContactButton;
            public MockInstrumentInteraction BeamButton;
            public RuntimePlacement GripPlacement;
            public Vector3 GripStartPosition;
            public Vector3 GripStartDirection;
            public float GripStartValue;
            public int GripLastDetent;
            public int PendingStepDirection;
            public float PendingStepDeadline;
            public bool ResetChordEngaged;
            public bool TriggerEngaged;
            public bool BeamTriggerEngaged;
            public bool GripEngaged;
            public bool StickXEngaged;
            public MockInstrumentInteraction StickInteraction;
            public float StickTargetValue;
            public bool StickTargetInitialized;

            public HandOperationState(
                OVRInput.Controller controller,
                string label)
            {
                Controller = controller;
                Label = label;
            }
        }

        private enum AlignmentAnchorMode
        {
            Leading,
            Trailing,
            Centered,
            OriginalOrder
        }

        private enum PendingLayout
        {
            None,
            HorizontalAlign,
            VerticalAlign,
            HorizontalDistribute,
            VerticalDistribute
        }

        private enum MovePlacementModifier
        {
            None,
            AutoAlign,
            GridSnap
        }

        private enum OperationResolveMode
        {
            Any,
            DirectionalStep,
            StickControl,
            GripMotion,
            ContactButton,
            BeamButton
        }

        private sealed class PlacementEditState
        {
            public string PlacementId;
            public Pose WorldPose;
            public int SurfaceKind;
        }

        private sealed class EditCommand
        {
            public List<PlacementEditState> Before;
            public List<PlacementEditState> After;
            public bool IsMove;
        }

        private sealed class PlacementRuntimeState
        {
            public RuntimePlacement Placement;
            public AnchorRecord Anchor;
            public GameObject AnchorRoot;
            public string AnchorId;
            public Pose LocalPose;
            public int SurfaceKind;
        }

        private sealed class AnchorTarget
        {
            public AnchorRecord Anchor;
            public GameObject Root;
            public bool Created;
        }

        private readonly struct PlacementSurfaceHit
        {
            public PlacementSurfaceHit(
                Vector3 point,
                Vector3 normal,
                float distance,
                SurfaceKind surface,
                MRUKAnchor sceneAnchor = null)
            {
                Point = point;
                Normal = normal;
                Distance = distance;
                Surface = surface;
                SceneAnchor = sceneAnchor;
            }

            public Vector3 Point { get; }
            public Vector3 Normal { get; }
            public float Distance { get; }
            public SurfaceKind Surface { get; }
            public MRUKAnchor SceneAnchor { get; }
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
#if UNITY_ANDROID || UNITY_EDITOR
            if (PerformanceGate.PerformanceGateConfiguration.IsEnabled)
                return;

            if (FindAnyObjectByType<MetaQuestPlacementController>() != null)
                return;

            var host = new GameObject("[App] Meta Quest Placement");
            DontDestroyOnLoad(host);
            host.AddComponent<MetaQuestPlacementController>();
#endif
        }

        private async void Start()
        {
            try
            {
                selectedTheme = MockInstrumentThemePreference.Load();
                CreateStatusHud();
                placementStore = new PlayerPrefsPlacementStore();
                anchorService = new MetaQuestAnchorService();
                var placementLoad = LegacyPlacementMigration.LoadOrMigrate(
                    placementStore,
                    new PlayerPrefsLegacyPlacementSource());
                if (placementLoad.Status == PlacementLoadStatus.UnsupportedVersion)
                {
                    Debug.LogError($"[Placement] {placementLoad.Message}");
                    SetStatus("PLACEMENT DATA IS FROM A NEWER VERSION", Color.red);
                    return;
                }
                if (placementLoad.Status == PlacementLoadStatus.Corrupt ||
                    placementLoad.Status == PlacementLoadStatus.SaveFailed)
                {
                    Debug.LogError(
                        $"[Placement] Placement data requires recovery: " +
                        placementLoad.Message);
                    SetStatus("PLACEMENT DATA RECOVERY REQUIRED", Color.red);
                    return;
                }
                placementDocument = placementLoad.Document ?? new PlacementDocument();
                if (placementDocument.placements.Count > 0)
                {
                    Debug.Log(
                        $"[Placement] Loaded schema {placementDocument.schemaVersion}, " +
                        $"revision {placementDocument.revision}, " +
                        $"{placementDocument.placements.Count} record(s).");
                }
                SetStatus("ROOM: WAITING FOR PERMISSION");

#if UNITY_ANDROID && !UNITY_EDITOR
                for (var attempt = 0;
                     attempt < 180 && !UnityEngine.Android.Permission.HasUserAuthorizedPermission(
                         OVRPermissionsRequester.ScenePermission);
                     attempt++)
                {
                    await Task.Delay(500);
                }

                if (!UnityEngine.Android.Permission.HasUserAuthorizedPermission(
                        OVRPermissionsRequester.ScenePermission))
                {
                    SetStatus("SCENE PERMISSION REQUIRED", Color.yellow);
                    return;
                }
#endif

                // Allow the OpenXR session and tracking space to settle before
                // fetching room anchors. Loading during the first session frames
                // can leave every returned scene anchor unlocatable on Quest.
                await Task.Delay(1500);
                SetStatus("ROOM: LOADING");
                Debug.Log("[Placement] MRUK V1 room load started.");

                var mruk = MRUK.Instance;
                if (mruk == null)
                {
                    var mrukObject = new GameObject("[App] MRUK");
                    mrukObject.SetActive(false);
                    mruk = mrukObject.AddComponent<MRUK>();
                    mruk.SceneSettings = new MRUK.MRUKSettings
                    {
                        DataSource = MRUK.SceneDataSource.Device,
                        LoadSceneOnStartup = false,
                        EnableHighFidelityScene = false
                    };
                    mrukObject.SetActive(true);
                    DontDestroyOnLoad(mrukObject);
                }

                var roomLoadTask = mruk.LoadSceneFromDevice(
                    requestSceneCaptureIfNoDataFound: false,
                    sceneModel: MRUK.SceneModel.V1);
                MRUK.LoadDeviceResult? loadResult = null;
                if (await Task.WhenAny(roomLoadTask, Task.Delay(20000)) != roomLoadTask)
                {
                    Debug.LogWarning(
                        "[Placement] MRUK room load timed out because saved room anchors could not be localized.");
                    SetStatus(
                        "ROOM TRACKING LOST\nRUN SPACE SETUP",
                        Color.yellow);
                    return;
                }
                else
                {
                    loadResult = await roomLoadTask;
                    Debug.Log(
                        $"[Placement] MRUK room load completed: " +
                        $"{loadResult.Value}.");
                    if (loadResult.Value == MRUK.LoadDeviceResult.Success)
                        currentRoom = mruk.GetCurrentRoom();
                }

                if (currentRoom == null)
                {
                    SetStatus(
                        loadResult == MRUK.LoadDeviceResult.NoRoomsFound
                            ? "NO ROOM DATA\nRUN SPACE SETUP"
                            : $"ROOM ERROR: {loadResult?.ToString() ?? "TIMEOUT"}",
                        Color.yellow);
                    return;
                }

                BuildSurfaceWireframes();
                SetStatus("ROOM READY - AIM AT PLANE OR VOLUME");
                operationInProgress = true;
                try
                {
                    await RestorePlacedInstrumentsAsync();
                }
                finally
                {
                    operationInProgress = false;
                }
                SetModeStatus();
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                SetStatus("PLACEMENT START FAILED", Color.red);
            }
        }

        private void OnEnable()
        {
            Application.onBeforeRender += OnBeforeRender;
            rightPrimaryButtonAction = CreateAction(
                "Right Primary",
                InputActionType.Button,
                "<XRController>{RightHand}/primaryButton");
            rightSecondaryButtonAction = CreateAction(
                "Right Secondary",
                InputActionType.Button,
                "<XRController>{RightHand}/secondaryButton");
            leftPrimaryButtonAction = CreateAction(
                "Left Primary",
                InputActionType.Button,
                "<XRController>{LeftHand}/primaryButton");
            leftSecondaryButtonAction = CreateAction(
                "Left Secondary",
                InputActionType.Button,
                "<XRController>{LeftHand}/secondaryButton");
            rightThumbstickButtonAction = CreateAction(
                "Right Stick Click",
                InputActionType.Button,
                "<XRController>{RightHand}/thumbstickClicked");
            leftThumbstickButtonAction = CreateAction(
                "Left Stick Click",
                InputActionType.Button,
                "<XRController>{LeftHand}/thumbstickClicked");
            rightThumbstickAction = CreateAction(
                "Right Stick",
                InputActionType.Value,
                "<XRController>{RightHand}/thumbstick");
            leftThumbstickAction = CreateAction(
                "Left Stick",
                InputActionType.Value,
                "<XRController>{LeftHand}/thumbstick");
            rightTriggerAction = CreateAction(
                "Right Trigger",
                InputActionType.Value,
                "<XRController>{RightHand}/trigger");
            leftTriggerAction = CreateAction(
                "Left Trigger",
                InputActionType.Value,
                "<XRController>{LeftHand}/trigger");
            rightGripAction = CreateAction(
                "Right Grip",
                InputActionType.Value,
                "<XRController>{RightHand}/grip");
            leftGripAction = CreateAction(
                "Left Grip",
                InputActionType.Value,
                "<XRController>{LeftHand}/grip");
            rightPositionAction = CreateAction(
                "Right Controller Position",
                InputActionType.Value,
                "<XRController>{RightHand}/devicePosition");
            rightRotationAction = CreateAction(
                "Right Controller Rotation",
                InputActionType.Value,
                "<XRController>{RightHand}/deviceRotation");
            leftPositionAction = CreateAction(
                "Left Controller Position",
                InputActionType.Value,
                "<XRController>{LeftHand}/devicePosition");
            leftRotationAction = CreateAction(
                "Left Controller Rotation",
                InputActionType.Value,
                "<XRController>{LeftHand}/deviceRotation");
            rightPointerPositionAction = CreateAction(
                "Right Aim Position",
                InputActionType.Value,
                "<XRController>{RightHand}/pointerPosition");
            rightPointerRotationAction = CreateAction(
                "Right Aim Rotation",
                InputActionType.Value,
                "<XRController>{RightHand}/pointerRotation");
            leftPointerPositionAction = CreateAction(
                "Left Aim Position",
                InputActionType.Value,
                "<XRController>{LeftHand}/pointerPosition");
            leftPointerRotationAction = CreateAction(
                "Left Aim Rotation",
                InputActionType.Value,
                "<XRController>{LeftHand}/pointerRotation");
        }

        private void OnDisable()
        {
            Application.onBeforeRender -= OnBeforeRender;
            DisposeAction(ref rightPrimaryButtonAction);
            DisposeAction(ref rightSecondaryButtonAction);
            DisposeAction(ref leftPrimaryButtonAction);
            DisposeAction(ref leftSecondaryButtonAction);
            DisposeAction(ref rightThumbstickButtonAction);
            DisposeAction(ref leftThumbstickButtonAction);
            DisposeAction(ref rightThumbstickAction);
            DisposeAction(ref leftThumbstickAction);
            DisposeAction(ref rightTriggerAction);
            DisposeAction(ref leftTriggerAction);
            DisposeAction(ref rightGripAction);
            DisposeAction(ref leftGripAction);
            DisposeAction(ref rightPositionAction);
            DisposeAction(ref rightRotationAction);
            DisposeAction(ref leftPositionAction);
            DisposeAction(ref leftRotationAction);
            DisposeAction(ref rightPointerPositionAction);
            DisposeAction(ref rightPointerRotationAction);
            DisposeAction(ref leftPointerPositionAction);
            DisposeAction(ref leftPointerRotationAction);
            ReleaseOperationInteractions();
            ClearConnectSelection();
            ClearConnectionVisuals();
            ClearMoveTargetMarkers();
            ClearSurfaceWireframes();
        }

        private void Update()
        {
            EnsureControllerAnchor();
            UpdateOpenXrControllerPose();
            UpdateCurrentRoomTracking();
            UpdatePlacementPreview();
            UpdateControllerBeam();
            UpdateInput();
            UpdateSignalGraph();
            UpdateConnectionVisuals();
        }

        private void OnBeforeRender()
        {
            EnsureControllerAnchor();
            UpdateOpenXrControllerPose();
            UpdateControllerBeam();
        }

        private void UpdateCurrentRoomTracking()
        {
            if (currentRoom == null ||
                roomSwitchInProgress ||
                operationInProgress ||
                Time.unscaledTime < nextCurrentRoomPollTime)
            {
                return;
            }

            nextCurrentRoomPollTime =
                Time.unscaledTime + CurrentRoomPollSeconds;
            var detectedRoom = MRUK.Instance?.GetCurrentRoom();
            if (detectedRoom == null ||
                AreSameRoom(detectedRoom, currentRoom))
            {
                pendingCurrentRoom = null;
                pendingCurrentRoomSince = 0f;
                return;
            }

            if (!AreSameRoom(detectedRoom, pendingCurrentRoom))
            {
                pendingCurrentRoom = detectedRoom;
                pendingCurrentRoomSince = Time.unscaledTime;
                SetStatus("ROOM CHANGE DETECTED\nCONFIRMING POSITION", Color.yellow);
                return;
            }

            if (Time.unscaledTime - pendingCurrentRoomSince <
                CurrentRoomSwitchDebounceSeconds)
            {
                return;
            }

            pendingCurrentRoom = null;
            pendingCurrentRoomSince = 0f;
            SwitchCurrentRoomAsync(detectedRoom);
        }

        private async void SwitchCurrentRoomAsync(MRUKRoom nextRoom)
        {
            if (nextRoom == null ||
                AreSameRoom(nextRoom, currentRoom) ||
                roomSwitchInProgress)
            {
                return;
            }

            roomSwitchInProgress = true;
            operationInProgress = true;
            try
            {
                ReleaseActiveInteraction();
                ClearGroupMoveSelection();
                ClearConnectSelection();
                SetPreviewVisible(false);
                ClearSurfaceWireframes();
                UnloadRuntimePlacements();

                currentRoom = nextRoom;
                BuildSurfaceWireframes();
                SetStatus(
                    "ROOM SWITCHED\nLOCALIZING SPATIAL ANCHORS",
                    new Color(0.2f, 0.9f, 1f));
                await RestorePlacedInstrumentsAsync();
                Debug.Log(
                    $"[Placement] Current room switched to " +
                    $"{GetRoomId(currentRoom)}.");
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                SetStatus("ROOM SWITCH FAILED", Color.red);
            }
            finally
            {
                operationInProgress = false;
                roomSwitchInProgress = false;
                nextCurrentRoomPollTime =
                    Time.unscaledTime + CurrentRoomPollSeconds;
                SetModeStatus();
            }
        }

        private void UnloadRuntimePlacements()
        {
            var anchorRoots = new HashSet<GameObject>();
            foreach (var placement in placements)
            {
                if (placement?.AnchorRoot != null)
                    anchorRoots.Add(placement.AnchorRoot);
            }

            placements.Clear();
            activePlacement = null;
            interactionCandidates.Clear();
            signalInteractions.Clear();
            ClearConnectionVisuals();
            foreach (var anchorRoot in anchorRoots)
                Destroy(anchorRoot);
        }

        private static string GetRoomId(MRUKRoom room)
        {
            return room != null && room.Anchor != OVRAnchor.Null
                ? room.Anchor.Uuid.ToString("D")
                : string.Empty;
        }

        private static bool AreSameRoom(MRUKRoom left, MRUKRoom right)
        {
            if (ReferenceEquals(left, right))
                return true;
            if (left == null || right == null)
                return false;

            var leftId = GetRoomId(left);
            return !string.IsNullOrEmpty(leftId) &&
                   string.Equals(
                       leftId,
                       GetRoomId(right),
                       StringComparison.OrdinalIgnoreCase);
        }

        private void OnApplicationPause(bool isPaused)
        {
            if (isPaused)
            {
                if (controllerBeam != null)
                    controllerBeam.enabled = false;
                if (leftControllerBeam != null)
                    leftControllerBeam.enabled = false;
                return;
            }

            QueueControllerPoseResync();
        }

        private void OnApplicationFocus(bool hasFocus)
        {
            if (hasFocus)
                QueueControllerPoseResync();
        }

        private void QueueControllerPoseResync()
        {
            controllerPoseResyncFrames = 3;
            RefreshAction(rightPositionAction);
            RefreshAction(rightRotationAction);
            RefreshAction(leftPositionAction);
            RefreshAction(leftRotationAction);
            RefreshAction(rightPointerPositionAction);
            RefreshAction(rightPointerRotationAction);
            RefreshAction(leftPointerPositionAction);
            RefreshAction(leftPointerRotationAction);
            Debug.Log("[Input] Refreshing both controller poses after XR focus restore.");
        }

        private static void RefreshAction(InputAction action)
        {
            if (action == null)
                return;

            action.Disable();
            action.Enable();
        }

        private static InputAction CreateAction(
            string actionName,
            InputActionType actionType,
            string binding)
        {
            var action = new InputAction(actionName, actionType, binding);
            action.Enable();
            return action;
        }

        private static void DisposeAction(ref InputAction action)
        {
            action?.Dispose();
            action = null;
        }

        private void CreateStatusHud()
        {
            var camera = Camera.main;
            if (camera == null)
                return;

            var statusObject = new GameObject("Placement Status");
            statusObject.transform.SetParent(camera.transform, false);
            statusObject.transform.localPosition = new Vector3(0f, 0.15f, 0.75f);
            statusLabel = statusObject.AddComponent<TextMesh>();
            statusLabel.anchor = TextAnchor.MiddleCenter;
            statusLabel.alignment = TextAlignment.Center;
            statusLabel.characterSize = 0.0055f;
            statusLabel.fontSize = 64;
            statusLabel.color = Color.white;
        }

        private void EnsureGlobalAudioPanel()
        {
            if (globalAudioPanel != null)
                return;
            var camera = Camera.main;
            if (camera == null)
                return;

            globalAudioPanel = new GameObject("Global Audio Settings Panel");
            globalAudioPanel.transform.SetParent(camera.transform, false);
            globalAudioPanel.transform.localPosition =
                new Vector3(0f, -0.02f, 0.68f);

            var background = GameObject.CreatePrimitive(PrimitiveType.Quad);
            background.name = "Audio Settings Background";
            background.transform.SetParent(globalAudioPanel.transform, false);
            background.transform.localScale = new Vector3(0.62f, 0.32f, 1f);
            var collider = background.GetComponent<Collider>();
            if (collider != null)
                Destroy(collider);
            RuntimeMaterialUtility.ApplySharedUnlit(
                background.GetComponent<Renderer>(),
                new Color(0.012f, 0.025f, 0.035f, 0.96f));

            var labelObject = new GameObject("Audio Settings Text");
            labelObject.transform.SetParent(globalAudioPanel.transform, false);
            labelObject.transform.localPosition = new Vector3(0f, 0f, -0.004f);
            globalAudioPanelLabel = labelObject.AddComponent<TextMesh>();
            globalAudioPanelLabel.anchor = TextAnchor.MiddleCenter;
            globalAudioPanelLabel.alignment = TextAlignment.Center;
            globalAudioPanelLabel.characterSize = 0.0045f;
            globalAudioPanelLabel.fontSize = 64;
            globalAudioPanelLabel.color = new Color(0.25f, 0.95f, 1f);
            globalAudioPanel.SetActive(false);
        }

        private void SetGlobalAudioPanelVisible(bool visible)
        {
            EnsureGlobalAudioPanel();
            globalAudioPanelVisible = visible && globalAudioPanel != null;
            if (globalAudioPanel != null)
                globalAudioPanel.SetActive(globalAudioPanelVisible);
            if (!globalAudioPanelVisible)
            {
                GlobalAudioSettings.Persist();
                audioMenuTriggerEngaged = false;
                audioMenuGripEngaged = false;
                SetModeStatus();
                return;
            }
            ReleaseOperationInteractions();
            RefreshGlobalAudioPanel();
        }

        private void RefreshGlobalAudioPanel()
        {
            if (globalAudioPanelLabel == null)
                return;
            globalAudioPanelLabel.text =
                "GLOBAL AUDIO\n\n" +
                $"INSTRUMENT SE  {(GlobalAudioSettings.EffectsEnabled ? "ON" : "OFF")}\n" +
                $"SE VOLUME       {GlobalAudioSettings.EffectsVolume:P0}\n" +
                $"AUDIO MODULES   {(GlobalAudioSettings.ModularAudioEnabled ? "ON" : "OFF")}\n\n" +
                "TRIGGER +5%  |  GRIP -5%\n" +
                "STICK Y: FINE  |  CLICK: DEFAULT 50%\n" +
                "X: SE ON/OFF  |  Y: MODULE ON/OFF\n" +
                "A: CLOSE";
        }

        private void AdjustGlobalEffectsVolume(float delta)
        {
            GlobalAudioSettings.EffectsVolume += delta;
            RefreshGlobalAudioPanel();
        }

        private void EnsureControllerAnchor()
        {
            if (rightControllerAnchor != null &&
                leftControllerAnchor != null &&
                rightAimAnchor != null &&
                leftAimAnchor != null &&
                trackingSpace != null)
            {
                return;
            }

            if (rightControllerAnchor == null)
            {
                var anchorObject = GameObject.Find("RightControllerAnchor");
                if (anchorObject != null)
                    rightControllerAnchor = anchorObject.transform;
            }

            if (leftControllerAnchor == null)
            {
                var anchorObject = GameObject.Find("LeftControllerAnchor");
                if (anchorObject != null)
                    leftControllerAnchor = anchorObject.transform;
            }

            if (rightAimAnchor == null)
            {
                var aimObject = new GameObject("[Input] Right Aim Pose");
                aimObject.transform.SetParent(transform, false);
                rightAimAnchor = aimObject.transform;
            }
            if (leftAimAnchor == null)
            {
                var aimObject = new GameObject("[Input] Left Aim Pose");
                aimObject.transform.SetParent(transform, false);
                leftAimAnchor = aimObject.transform;
            }

            if (trackingSpace == null)
            {
                var trackingSpaceObject = GameObject.Find("TrackingSpace");
                if (trackingSpaceObject != null)
                    trackingSpace = trackingSpaceObject.transform;
            }
        }

        private void UpdateOpenXrControllerPose()
        {
            if (trackingSpace == null)
            {
                return;
            }

            var rightUpdated = TryUpdateOpenXrControllerPose(
                rightControllerAnchor,
                rightPositionAction,
                rightRotationAction);
            var leftUpdated = TryUpdateOpenXrControllerPose(
                leftControllerAnchor,
                leftPositionAction,
                leftRotationAction);
            var rightAimUpdated = TryUpdateOpenXrControllerPose(
                rightAimAnchor,
                rightPointerPositionAction,
                rightPointerRotationAction);
            var leftAimUpdated = TryUpdateOpenXrControllerPose(
                leftAimAnchor,
                leftPointerPositionAction,
                leftPointerRotationAction);
            if (!rightAimUpdated && rightControllerAnchor != null)
            {
                rightAimAnchor.SetPositionAndRotation(
                    rightControllerAnchor.position,
                    rightControllerAnchor.rotation);
            }
            if (!leftAimUpdated && leftControllerAnchor != null)
            {
                leftAimAnchor.SetPositionAndRotation(
                    leftControllerAnchor.position,
                    leftControllerAnchor.rotation);
            }
            if (controllerPoseResyncFrames > 0 &&
                (rightUpdated ||
                 leftUpdated ||
                 rightAimUpdated ||
                 leftAimUpdated))
            {
                controllerPoseResyncFrames--;
            }
        }

        private bool TryUpdateOpenXrControllerPose(
            Transform controllerAnchor,
            InputAction positionAction,
            InputAction rotationAction)
        {
            if (controllerAnchor == null ||
                positionAction?.activeControl == null ||
                rotationAction?.activeControl == null)
            {
                return false;
            }

            var localPosition = positionAction.ReadValue<Vector3>();
            var localRotation = rotationAction.ReadValue<Quaternion>();
            var rotationMagnitude =
                localRotation.x * localRotation.x +
                localRotation.y * localRotation.y +
                localRotation.z * localRotation.z +
                localRotation.w * localRotation.w;
            if (!IsFinite(localPosition) ||
                float.IsNaN(rotationMagnitude) ||
                float.IsInfinity(rotationMagnitude) ||
                rotationMagnitude < 0.5f)
            {
                return false;
            }

            controllerAnchor.SetPositionAndRotation(
                trackingSpace.TransformPoint(localPosition),
                trackingSpace.rotation * localRotation);
            return true;
        }

        private static bool IsFinite(Vector3 value)
        {
            return !float.IsNaN(value.x) &&
                   !float.IsNaN(value.y) &&
                   !float.IsNaN(value.z) &&
                   !float.IsInfinity(value.x) &&
                   !float.IsInfinity(value.y) &&
                   !float.IsInfinity(value.z);
        }

        private void EnsureControllerBeam()
        {
            if (controllerBeam == null && rightAimAnchor != null)
            {
                controllerBeam = CreateControllerBeam(
                    "[Interaction] Right Controller Beam");
            }
            if (leftControllerBeam == null && leftAimAnchor != null)
            {
                leftControllerBeam = CreateControllerBeam(
                    "[Interaction] Left Controller Beam");
            }
        }

        private LineRenderer CreateControllerBeam(string objectName)
        {
            var beamObject = new GameObject(objectName);
            beamObject.transform.SetParent(transform, false);
            var beam = beamObject.AddComponent<LineRenderer>();
            beam.useWorldSpace = true;
            beam.positionCount = 2;
            beam.startWidth = ControllerBeamWidth;
            beam.endWidth = ControllerBeamWidth * 0.5f;
            beam.numCapVertices = 4;
            beam.shadowCastingMode =
                UnityEngine.Rendering.ShadowCastingMode.Off;
            beam.receiveShadows = false;
            RuntimeMaterialUtility.ApplySharedUnlit(beam, EditBeamColor);
            return beam;
        }

        private void UpdateControllerBeam()
        {
            EnsureControllerBeam();
            UpdateControllerBeam(controllerBeam, rightAimAnchor, true);
            UpdateControllerBeam(
                leftControllerBeam,
                leftAimAnchor,
                false);
        }

        private void UpdateControllerBeam(
            LineRenderer beam,
            Transform controllerAnchor,
            bool rightController)
        {
            if (beam == null || controllerAnchor == null)
                return;
            if (controllerPoseResyncFrames > 0)
            {
                beam.enabled = false;
                return;
            }

            var direction = controllerAnchor.forward.normalized;
            if (direction.sqrMagnitude < 0.0001f)
            {
                beam.enabled = false;
                return;
            }

            beam.enabled = true;
            var maximumDistance =
                AppInteractionModePolicy.AllowsEditing(interactionMode)
                    ? MaxPlacementDistance
                    : MaxInteractionDistance;
            var ray = new Ray(controllerAnchor.position, direction);
            var beamDistance = maximumDistance;

            if (AppInteractionModePolicy.AllowsEditing(interactionMode) &&
                !rightController)
            {
                if (TryRaycastPlacementSurface(
                        ray,
                        maximumDistance,
                        out var surfaceHit))
                {
                    beamDistance =
                        hasPlacementPose &&
                        hasStablePlacementSurfaceHit
                            ? Vector3.Distance(
                                ray.origin,
                                stablePlacementSurfaceHit.Point)
                            : surfaceHit.Distance;
                }
            }
            else if (TryGetNearestInstrumentHitDistance(
                         ray,
                         maximumDistance,
                         out var instrumentDistance))
            {
                beamDistance = instrumentDistance;
            }

            beam.SetPosition(
                0,
                ray.origin + direction * ControllerBeamStartOffset);
            beam.SetPosition(
                1,
                ray.origin + direction * Mathf.Max(
                    beamDistance,
                    ControllerBeamStartOffset));
            RuntimeMaterialUtility.SetColor(
                beam,
                AppInteractionModePolicy.AllowsEditing(interactionMode)
                    ? rightController ? ConnectBeamColor : EditBeamColor
                    : OperationBeamColor);
        }

        private bool TryGetNearestInstrumentHitDistance(
            Ray ray,
            float maximumDistance,
            out float distance)
        {
            distance = float.PositiveInfinity;
            foreach (var placement in placements)
            {
                var interaction = placement?.Interaction;
                var collider = interaction != null
                    ? interaction.InteractionCollider
                    : null;
                if (collider == null ||
                    !collider.enabled ||
                    !collider.gameObject.activeInHierarchy ||
                    !collider.Raycast(ray, out var hit, maximumDistance) ||
                    hit.distance >= distance)
                {
                    continue;
                }

                distance = hit.distance;
            }
            return !float.IsPositiveInfinity(distance);
        }

        private void UpdatePlacementPreview()
        {
            hasPlacementPose = false;
            placementPoseWasAdjusted = false;
            moveModifierApplied = false;
            isAimingAtPlacedObject = false;
            SetMoveTargetMarkersVisible(false);
            if (!AppInteractionModePolicy.AllowsEditing(interactionMode) ||
                connectionEditing ||
                currentRoom == null ||
                leftAimAnchor == null ||
                operationInProgress)
            {
                hasStablePlacementSurfaceHit = false;
                hasPendingPlacementSurfaceHit = false;
                SetPreviewVisible(false);
                return;
            }

            if (!editMoveChordActive &&
                pendingLayout == PendingLayout.None &&
                groupMoveSelection.Count > 0)
            {
                SetPreviewVisible(false);
                SetStatus(
                    $"{groupMoveSelection.Count} SELECTED | " +
                    "CYAN = FIRST ANCHOR\n" +
                    "L-TRIGGER TO CHANGE | L-TRIGGER+GRIP MOVE\n" +
                    "MOVE+L-STICK: UP AUTO | DOWN GRID\n" +
                    "R-STICK: ROTATE | L-GRIP CANCEL",
                    new Color(1f, 0.75f, 0.15f));
                return;
            }

            if (pendingLayout != PendingLayout.None)
            {
                SetPreviewVisible(false);
                var targetIsValid =
                    UpdateMoveTargetMarkers(out var invalidReason);
                SetStatus(
                    targetIsValid
                        ? $"{PendingLayoutLabel(pendingLayout)} PREVIEW\n" +
                          "A CONFIRM | R-STICK ROTATE | B CANCEL"
                        : $"LAYOUT BLOCKED: {invalidReason}\n" +
                          "CHOOSE ANOTHER L-STICK DIRECTION",
                    targetIsValid ? Color.green : Color.red);
                return;
            }

            if (!groupMoveArmed &&
                TryResolvePlacedInteraction(out _, out _))
            {
                hasStablePlacementSurfaceHit = false;
                hasPendingPlacementSurfaceHit = false;
                isAimingAtPlacedObject = true;
                SetPreviewVisible(false);
                SetStatus(
                    "EXISTING OBJECT AIMED\n" +
                    "L-TRIGGER SELECT | B DELETE\n" +
                    "R-CLICK RE-PLACE",
                    Color.white);
                return;
            }

            var ray = new Ray(
                leftAimAnchor.position,
                leftAimAnchor.forward);
            if (!TryRaycastStablePlacementSurface(
                    ray,
                    MaxPlacementDistance,
                    out var hit))
            {
                SetPreviewVisible(false);
                SetStatus("ROOM READY - AIM AT A SURFACE");
                return;
            }

            currentSurface = hit.Surface;
            var cameraForward = Camera.main != null ? Camera.main.transform.forward : Vector3.forward;
            currentPlacementPose = PlacementPoseUtility.FromSurface(
                hit.Point + hit.Normal.normalized * SurfaceOffset,
                hit.Normal,
                cameraForward);
            if (editMoveChordActive ||
                editPlacementModifierChordActive ||
                (!groupMoveArmed &&
                 editMoveModifier != MovePlacementModifier.None))
                ApplyMovePlacementModifier(ref currentPlacementPose);
            hasPlacementPose = true;

            if (groupMoveArmed)
            {
                SetPreviewVisible(false);
                var targetIsValid =
                    UpdateMoveTargetMarkers(out var invalidReason);
                SetStatus(
                    targetIsValid
                        ? $"GROUP MOVE: {groupMoveSelection.Count} INSTRUMENT(S)\n" +
                          $"TARGET: {currentSurface.ToString().ToUpperInvariant()} | RELEASE TO CONFIRM\n" +
                          MoveModifierStatus() +
                          "L-STICK UP AUTO | DOWN GRID"
                        : $"MOVE BLOCKED: {invalidReason}\n" +
                          MoveModifierStatus() +
                          $"TARGET: {currentSurface.ToString().ToUpperInvariant()}",
                    targetIsValid
                        ? new Color(0.1f, 1f, 0.65f)
                        : Color.red);
                return;
            }

            if (!MockInstrumentFactory.IsPlacementReady(
                    selectedKind,
                    selectedTheme))
            {
                hasPlacementPose = false;
                SetPreviewVisible(false);
                SetStatus(
                    $"{MockInstrumentCatalog.GetDisplayName(selectedKind)}\n" +
                    "3D MODEL PENDING | PLACEMENT DISABLED",
                    Color.yellow);
                return;
            }

            if (!MockInstrumentCatalog.SupportsSurface(selectedKind, currentSurface))
            {
                SetPreviewVisible(false);
                SetStatus(
                    $"{MockInstrumentCatalog.GetDisplayName(selectedKind)}\n" +
                    $"NOT ALLOWED ON {currentSurface.ToString().ToUpperInvariant()}",
                    Color.yellow);
                return;
            }

            var desiredPose = currentPlacementPose;
            if (!TryResolveNonOverlappingPose(
                    desiredPose,
                    selectedKind,
                    out currentPlacementPose))
            {
                hasPlacementPose = false;
                SetPreviewVisible(false);
                SetStatus(
                    "NO FREE SPACE NEAR AIM POINT\n" +
                    "AIM AT ANOTHER AREA",
                    Color.yellow);
                return;
            }
            placementPoseWasAdjusted =
                Vector3.SqrMagnitude(
                    currentPlacementPose.position - desiredPose.position) >
                0.000001f;

            if (preview == null)
                preview = MockInstrumentFactory.Create(
                    selectedKind,
                    currentPlacementPose,
                    preview: true,
                    theme: selectedTheme);
            else
                preview.transform.SetPositionAndRotation(
                    currentPlacementPose.position,
                    currentPlacementPose.rotation);

            SetPreviewVisible(true);
            SetStatus(
                $"[{MockInstrumentCatalog.GetCategoryDisplayName(selectedKind)}] " +
                $"{MockInstrumentCatalog.GetDisplayName(selectedKind)} | " +
                $"{MockInstrumentThemeCatalog.GetDisplayName(selectedTheme)}\n" +
                $"{currentSurface.ToString().ToUpperInvariant()} | " +
                $"{CurrentRoomPlacementCount():00}/" +
                $"{PlacementDocument.MaximumActivePlacements:00}\n" +
                (placementPoseWasAdjusted ? "AUTO OFFSET: OVERLAP AVOIDED\n" : string.Empty) +
                MoveModifierStatus() +
                "R \u2190/\u2192 OBJECT | R \u2191/\u2193 CATEGORY\n" +
                "L \u2190/\u2192 THEME\n" +
                "L-TRIGGER SELECT | A PLACE | B DELETE\n" +
                "L-TRIGGER+GRIP + L-STICK UP AUTO/DOWN GRID\n" +
                "R-TRIGGER CONNECT | X OPERATE");
        }

        private void ApplyMovePlacementModifier(ref Pose pose)
        {
            switch (editMoveModifier)
            {
                case MovePlacementModifier.AutoAlign:
                    moveModifierApplied = TryAutoAlignMovePose(ref pose);
                    break;
                case MovePlacementModifier.GridSnap:
                    pose = PlacementPoseUtility.SnapToGrid(
                        pose,
                        PlacementGridSpacing);
                    moveModifierApplied = true;
                    break;
            }
        }

        private bool TryAutoAlignMovePose(ref Pose pose)
        {
            RuntimePlacement nearest = null;
            var nearestDistanceSquared =
                AutoAlignSearchRadius * AutoAlignSearchRadius;
            foreach (var placement in placements)
            {
                if (placement?.Root == null ||
                    groupMoveSelection.Contains(placement))
                {
                    continue;
                }

                var target = placement.Root.transform;
                if (Vector3.Dot(
                        target.forward,
                        pose.rotation * Vector3.forward) <
                    CoplanarNormalDotThreshold)
                {
                    continue;
                }

                var distanceSquared =
                    (target.position - pose.position).sqrMagnitude;
                if (distanceSquared >= nearestDistanceSquared)
                    continue;
                nearestDistanceSquared = distanceSquared;
                nearest = placement;
            }
            if (nearest?.Root == null)
                return false;

            var reference = nearest.Root.transform;
            pose = PlacementPoseUtility.AlignNearestAxis(
                pose,
                new Pose(reference.position, reference.rotation));
            return true;
        }

        private string MoveModifierStatus()
        {
            return editMoveModifier switch
            {
                MovePlacementModifier.AutoAlign =>
                    moveModifierApplied
                        ? "AUTO ALIGNED TO NEARBY OBJECT\n"
                        : "AUTO ALIGN: NO NEARBY MATCH\n",
                MovePlacementModifier.GridSnap => "GRID SNAP 10 CM\n",
                _ => string.Empty
            };
        }

        private void UpdateInput()
        {
            var aButton =
                OVRInput.Get(OVRInput.RawButton.A, OVRInput.Controller.RTouch) ||
                IsPressed(rightPrimaryButtonAction);
            var bButton =
                OVRInput.Get(OVRInput.RawButton.B, OVRInput.Controller.RTouch) ||
                IsPressed(rightSecondaryButtonAction);
            var xButton =
                OVRInput.Get(OVRInput.RawButton.X, OVRInput.Controller.LTouch) ||
                IsPressed(leftPrimaryButtonAction);
            var yButton =
                OVRInput.Get(OVRInput.RawButton.Y, OVRInput.Controller.LTouch) ||
                IsPressed(leftSecondaryButtonAction);
            var thumbstickButton =
                OVRInput.Get(
                    OVRInput.RawButton.RThumbstick,
                    OVRInput.Controller.RTouch) ||
                IsPressed(rightThumbstickButtonAction);
            var leftThumbstickButton =
                OVRInput.Get(
                    OVRInput.RawButton.LThumbstick,
                    OVRInput.Controller.LTouch) ||
                IsPressed(leftThumbstickButtonAction);
            var ovrThumbstick = OVRInput.Get(
                OVRInput.RawAxis2D.RThumbstick,
                OVRInput.Controller.RTouch);
            var inputSystemThumbstick = ReadVector2(rightThumbstickAction);
            var thumbstick = ovrThumbstick.sqrMagnitude >=
                             inputSystemThumbstick.sqrMagnitude
                ? ovrThumbstick
                : inputSystemThumbstick;
            var ovrLeftThumbstick = OVRInput.Get(
                OVRInput.RawAxis2D.LThumbstick,
                OVRInput.Controller.LTouch);
            var inputSystemLeftThumbstick =
                ReadVector2(leftThumbstickAction);
            var leftThumbstick =
                ovrLeftThumbstick.sqrMagnitude >=
                inputSystemLeftThumbstick.sqrMagnitude
                    ? ovrLeftThumbstick
                    : inputSystemLeftThumbstick;
            var trigger = Mathf.Max(
                OVRInput.Get(
                    OVRInput.RawAxis1D.RIndexTrigger,
                    OVRInput.Controller.RTouch),
                ReadFloat(rightTriggerAction));
            var leftTrigger = Mathf.Max(
                OVRInput.Get(
                    OVRInput.RawAxis1D.LIndexTrigger,
                    OVRInput.Controller.LTouch),
                ReadFloat(leftTriggerAction));
            var rightGrip = Mathf.Max(
                OVRInput.Get(
                    OVRInput.RawAxis1D.RHandTrigger,
                    OVRInput.Controller.RTouch),
                ReadFloat(rightGripAction));
            var leftGrip = Mathf.Max(
                OVRInput.Get(
                    OVRInput.RawAxis1D.LHandTrigger,
                    OVRInput.Controller.LTouch),
                ReadFloat(leftGripAction));
            var editTrigger = trigger >= TriggerPressThreshold;
            var modeToggled = false;
            var editing =
                AppInteractionModePolicy.AllowsEditing(interactionMode);
            var exitInputConsumed =
                UpdateLeftStickHold(
                    leftThumbstickButton,
                    editing && !connectionEditing,
                    AppInteractionModePolicy.AllowsInstrumentOperation(
                        interactionMode) && !globalAudioPanelVisible);

            if (!exitInputConsumed &&
                !operationInProgress &&
                editing &&
                xButton &&
                !previousXButton)
            {
                if (modeSwitchLocked)
                {
                    SetStatus(
                        "MODE SWITCH LOCKED\n" +
                        "HOLD L-STICK 2s TO UNLOCK",
                        new Color(1f, 0.65f, 0.1f));
                    PulseHaptics(OVRInput.Controller.LTouch);
                }
                else
                {
                    ToggleInteractionMode(trigger, leftTrigger);
                }
                modeToggled = true;
            }

            if (!editing && !exitInputConsumed && !operationInProgress)
            {
                modeToggled = UpdateOperationGlobalInput(
                    aButton,
                    bButton,
                    xButton,
                    yButton,
                    thumbstickButton,
                    leftThumbstickButton,
                    thumbstick,
                    leftThumbstick,
                    trigger,
                    leftTrigger,
                    rightGrip,
                    leftGrip) || modeToggled;
            }

            if (!exitInputConsumed && !modeToggled && editing)
            {
                if (!operationInProgress)
                    UpdateEditHandInput(
                        leftTrigger,
                        leftGrip,
                        trigger,
                        rightGrip,
                        leftThumbstick);

                if (connectionEditing)
                {
                    UpdateSelection(Vector2.zero, Vector2.zero);
                    UpdateConnectInput(
                        trigger,
                        0f,
                        leftThumbstick,
                        thumbstick,
                        yButton && !previousYButton,
                        leftThumbstickButton &&
                        !previousLeftThumbstickButton,
                        aButton && !previousAButton,
                        bButton && !previousBButton);
                }
                else
                {
                    if (groupMoveSelection.Count == 0 &&
                        !thumbstickButton)
                    {
                        UpdateSelection(
                            thumbstick,
                            leftThumbstick);
                    }

                    var editActionConsumed = false;
                    // Y is reserved for a future placement action.
                    if (!editActionConsumed &&
                        !operationInProgress &&
                        !editMoveChordActive &&
                        groupMoveSelection.Count >= 2)
                    {
                        editActionConsumed =
                            HandleSelectionRotationStick(thumbstick);
                    }
                    if (!editActionConsumed &&
                        !operationInProgress &&
                        !editMoveChordActive &&
                        groupMoveSelection.Count >= 2)
                    {
                        editActionConsumed =
                            HandleAlignmentStick(leftThumbstick);
                    }
                    if (!editActionConsumed &&
                        !operationInProgress &&
                        !editMoveChordActive &&
                        pendingLayout != PendingLayout.None &&
                        aButton &&
                        !previousAButton)
                    {
                        ConfirmPendingLayout();
                        editActionConsumed = true;
                    }
                    if (!editActionConsumed &&
                        !operationInProgress &&
                        !editMoveChordActive &&
                        bButton &&
                        !previousBButton)
                    {
                        ClearPendingLayout(clearSource: true);
                        if (groupMoveSelection.Count > 0)
                        {
                            ClearGroupMoveSelection();
                            SetStatus("SELECTION CLEARED", Color.white);
                            PulseHaptics();
                        }
                        else
                            DeleteAimedInstrument();
                        editActionConsumed = true;
                    }
                    if (!editActionConsumed &&
                        !operationInProgress &&
                        !groupMoveArmed &&
                        groupMoveSelection.Count == 0 &&
                        !isAimingAtPlacedObject &&
                        hasPlacementPose &&
                        aButton &&
                        !previousAButton)
                    {
                        PlaceInstrument();
                        editPlacementModifierChordActive = false;
                        editMoveModifier = MovePlacementModifier.None;
                        moveModifierAxisEngaged = false;
                        editActionConsumed = true;
                    }
                    if (!editActionConsumed &&
                        !operationInProgress &&
                        thumbstickButton &&
                        !previousThumbstickButton)
                    {
                        ReplaceAimedInstrument();
                    }
                }
            }
            else
            {
                UpdateSelection(
                    Vector2.zero,
                    Vector2.zero);
                if (!globalAudioPanelVisible &&
                    !exitInputConsumed && !modeToggled &&
                    !operationInProgress &&
                    AppInteractionModePolicy.CanToggleConnectionVisuals(
                        interactionMode,
                        modeSwitchLocked) &&
                    aButton && !previousAButton)
                {
                    operationConnectionVisualsVisible =
                        !operationConnectionVisualsVisible;
                    operationStepNoticeUntil = Time.unscaledTime + 1f;
                    SetStatus(
                        operationConnectionVisualsVisible
                            ? "CONNECTIONS VISIBLE | A: HIDE"
                            : "CONNECTIONS HIDDEN | A: SHOW",
                        operationConnectionVisualsVisible
                            ? ConnectBeamColor
                            : Color.white);
                    PulseHaptics(OVRInput.Controller.RTouch);
                }
            }

            var rightStickClick =
                thumbstickButton && !previousThumbstickButton;
            var leftStickClick = leftStickShortClickPending;
            leftStickShortClickPending = false;
            previousAButton = aButton;
            previousBButton = bButton;
            previousXButton = xButton;
            previousYButton = yButton;
            previousGroupMoveChord = false;
            previousThumbstickButton = thumbstickButton;
            previousLeftThumbstickButton = leftThumbstickButton;
            previousEditTrigger = editTrigger;
            previousLeftEditTrigger =
                leftTrigger >= TriggerPressThreshold;
            previousLeftEditGrip =
                leftGrip >= TriggerPressThreshold;
            previousRightEditGrip =
                rightGrip >= TriggerPressThreshold;
            UpdateInstrumentInteractions(
                trigger,
                leftTrigger,
                rightGrip,
                leftGrip,
                thumbstick,
                leftThumbstick,
                rightStickClick,
                leftStickClick);
            UpdateHaptics();
        }

        private bool UpdateOperationGlobalInput(
            bool aButton,
            bool bButton,
            bool xButton,
            bool yButton,
            bool rightStickButton,
            bool leftStickButton,
            Vector2 rightStick,
            Vector2 leftStick,
            float rightTrigger,
            float leftTrigger,
            float rightGrip,
            float leftGrip)
        {
            if (!globalAudioPanelVisible &&
                bButton && !previousBButton)
            {
                SetSelectedTheme(
                    MockInstrumentThemeCatalog.Cycle(selectedTheme, 1));
                PulseHaptics(OVRInput.Controller.RTouch);
            }

            if (!modeSwitchLocked)
            {
                operationYHoldTime = 0f;
                operationYHoldLatched = false;
                if (xButton && !previousXButton)
                {
                    ToggleInteractionMode(rightTrigger, leftTrigger);
                    return true;
                }
                return false;
            }

            if (xButton && !previousXButton)
            {
                GlobalAudioSettings.EffectsEnabled =
                    !GlobalAudioSettings.EffectsEnabled;
                GlobalAudioSettings.Persist();
                SetStatus(
                    GlobalAudioSettings.EffectsEnabled
                        ? "INSTRUMENT SE: ON"
                        : "INSTRUMENT SE: OFF",
                    GlobalAudioSettings.EffectsEnabled
                        ? Color.green
                        : Color.yellow);
                RefreshGlobalAudioPanel();
                PulseHaptics(OVRInput.Controller.LTouch);
            }

            if (yButton)
            {
                operationYHoldTime += Time.unscaledDeltaTime;
                if (!operationYHoldLatched &&
                    operationYHoldTime >= OperationFaceButtonHoldSeconds)
                {
                    operationYHoldLatched = true;
                    SetGlobalAudioPanelVisible(!globalAudioPanelVisible);
                    PulseHaptics(OVRInput.Controller.LTouch);
                }
            }
            else
            {
                if (previousYButton && !operationYHoldLatched)
                {
                    GlobalAudioSettings.ModularAudioEnabled =
                        !GlobalAudioSettings.ModularAudioEnabled;
                    GlobalAudioSettings.Persist();
                    SetStatus(
                        GlobalAudioSettings.ModularAudioEnabled
                            ? "AUDIO MODULES: ON"
                            : "AUDIO MODULES: OFF | PROCESSING STOPPED",
                        GlobalAudioSettings.ModularAudioEnabled
                            ? Color.green
                            : Color.yellow);
                    RefreshGlobalAudioPanel();
                    PulseHaptics(OVRInput.Controller.LTouch);
                }
                operationYHoldTime = 0f;
                operationYHoldLatched = false;
            }

            if (!globalAudioPanelVisible)
                return false;

            if (aButton && !previousAButton)
            {
                SetGlobalAudioPanelVisible(false);
                PulseHaptics(OVRInput.Controller.RTouch);
                return false;
            }

            var triggerDown = Mathf.Max(rightTrigger, leftTrigger) >=
                              TriggerPressThreshold;
            var gripDown = Mathf.Max(rightGrip, leftGrip) >=
                           OperationGripPressThreshold;
            if (triggerDown && !audioMenuTriggerEngaged)
            {
                AdjustGlobalEffectsVolume(0.05f);
                PulseHaptics();
            }
            if (gripDown && !audioMenuGripEngaged)
            {
                AdjustGlobalEffectsVolume(-0.05f);
                PulseHaptics();
            }
            audioMenuTriggerEngaged = triggerDown;
            audioMenuGripEngaged = gripDown;

            var stickY = Mathf.Abs(rightStick.y) >= Mathf.Abs(leftStick.y)
                ? rightStick.y
                : leftStick.y;
            if (Mathf.Abs(stickY) >= OperationStickDeadZone)
            {
                AdjustGlobalEffectsVolume(
                    stickY * 0.35f * Time.unscaledDeltaTime);
            }
            if ((rightStickButton && !previousThumbstickButton) ||
                (leftStickButton && !previousLeftThumbstickButton))
            {
                GlobalAudioSettings.ResetEffectsVolume();
                RefreshGlobalAudioPanel();
                PulseHaptics();
            }
            return false;
        }

        private void UpdateEditHandInput(
            float leftTrigger,
            float leftGrip,
            float rightTrigger,
            float rightGrip,
            Vector2 leftThumbstick)
        {
            var leftTriggerDown = leftTrigger >= TriggerPressThreshold;
            var leftGripDown = leftGrip >= TriggerPressThreshold;
            var rightTriggerDown = rightTrigger >= TriggerPressThreshold;
            var rightGripDown = rightGrip >= TriggerPressThreshold;

            if (rightGripDown && !previousRightEditGrip)
            {
                pendingRightCancel = true;
                pendingRightCancelUntil =
                    Time.unscaledTime + OperationChordWindowSeconds;
            }
            if (rightTriggerDown && rightGripDown)
                pendingRightCancel = false;
            else if (pendingRightCancel &&
                     (!rightGripDown ||
                      Time.unscaledTime >= pendingRightCancelUntil))
            {
                pendingRightCancel = false;
                CancelEditSelection();
            }

            if (rightTriggerDown && !previousEditTrigger &&
                !connectionEditing)
            {
                ClearGroupMoveSelection();
                SetPreviewVisible(false);
                pendingLeftSelection = false;
                pendingMoveUndo = false;
                editMoveChordActive = false;
                connectionEditing = true;
                connectRightTriggerEngaged = false;
                SetModeStatus();
            }

            if (leftTriggerDown && !previousLeftEditTrigger)
            {
                if (connectionEditing)
                {
                    ClearConnectSelection();
                    connectionEditing = false;
                    SetModeStatus();
                }
                pendingLeftSelection = true;
                pendingLeftSelectionUntil =
                    Time.unscaledTime + OperationChordWindowSeconds;
            }
            if (leftGripDown && !previousLeftEditGrip &&
                !connectionEditing)
            {
                pendingMoveUndo = true;
                pendingMoveUndoUntil =
                    Time.unscaledTime + OperationChordWindowSeconds;
            }

            if (leftTriggerDown && leftGripDown && !connectionEditing)
            {
                pendingLeftSelection = false;
                pendingMoveUndo = false;
                if (editMoveCancelledUntilChordRelease)
                    return;
                if (!editMoveChordActive)
                {
                    if (groupMoveSelection.Count == 0)
                    {
                        if (!editPlacementModifierChordActive)
                        {
                            editPlacementModifierChordActive = true;
                            editMoveModifier = MovePlacementModifier.None;
                            moveModifierAxisEngaged = false;
                        }
                    }
                    else
                    {
                        ClearPendingLayout(clearSource: false);
                        editMoveChordActive = true;
                        editMoveModifier = MovePlacementModifier.None;
                        moveModifierAxisEngaged = false;
                        PulseHaptics(OVRInput.Controller.LTouch);
                    }
                }
                if (editMoveChordActive ||
                    editPlacementModifierChordActive)
                    UpdateMoveModifierStick(leftThumbstick);
                return;
            }

            if (editMoveCancelledUntilChordRelease)
                editMoveCancelledUntilChordRelease = false;

            if (editPlacementModifierChordActive)
            {
                editPlacementModifierChordActive = false;
                pendingLeftSelection = false;
                pendingMoveUndo = false;
                moveModifierAxisEngaged = false;
                return;
            }

            if (editMoveChordActive)
            {
                editMoveChordActive = false;
                pendingLeftSelection = false;
                pendingMoveUndo = false;
                HandleGroupMoveAction();
                editMoveModifier = MovePlacementModifier.None;
                moveModifierAxisEngaged = false;
                return;
            }

            if (pendingLeftSelection &&
                (!leftTriggerDown ||
                 Time.unscaledTime >= pendingLeftSelectionUntil))
            {
                pendingLeftSelection = false;
                ToggleAimedSelection();
            }
            if (pendingMoveUndo &&
                (!leftGripDown ||
                 Time.unscaledTime >= pendingMoveUndoUntil))
            {
                pendingMoveUndo = false;
                CancelOrUndoMove();
            }
        }

        private void CancelEditSelection()
        {
            pendingLeftSelection = false;
            pendingMoveUndo = false;
            if (connectionEditing)
            {
                ClearConnectSelection();
                SetStatus("CONNECTION SELECTION CANCELLED", Color.white);
                PulseHaptics(OVRInput.Controller.RTouch);
                return;
            }

            var hadSelection = groupMoveSelection.Count > 0 ||
                               pendingLayout != PendingLayout.None ||
                               editMoveChordActive ||
                               editPlacementModifierChordActive;
            if (editMoveChordActive)
                editMoveCancelledUntilChordRelease = true;
            editMoveChordActive = false;
            editPlacementModifierChordActive = false;
            editMoveModifier = MovePlacementModifier.None;
            moveModifierAxisEngaged = false;
            ClearGroupMoveSelection();
            SetStatus(
                hadSelection
                    ? "EDIT SELECTION CANCELLED"
                    : "NOTHING TO CANCEL",
                hadSelection ? Color.white : Color.yellow);
            PulseHaptics(OVRInput.Controller.RTouch);
        }

        private void UpdateMoveModifierStick(Vector2 axis)
        {
            if (Mathf.Abs(axis.y) <= SelectionReleaseThreshold)
            {
                moveModifierAxisEngaged = false;
                return;
            }
            if (moveModifierAxisEngaged ||
                Mathf.Abs(axis.y) < SelectionThreshold ||
                Mathf.Abs(axis.y) <= Mathf.Abs(axis.x))
            {
                return;
            }

            moveModifierAxisEngaged = true;
            editMoveModifier = axis.y > 0f
                ? MovePlacementModifier.AutoAlign
                : MovePlacementModifier.GridSnap;
            PulseHaptics(OVRInput.Controller.LTouch);
        }

        private void CancelOrUndoMove()
        {
            if (groupMoveSelection.Count > 0)
            {
                ClearGroupMoveSelection();
                SetStatus("MOVE CANCELLED | SELECTION CLEARED", Color.white);
                PulseHaptics(OVRInput.Controller.LTouch);
                return;
            }
            if (undoHistory.Count == 0 || !undoHistory.Peek().IsMove)
            {
                SetStatus("NO MOVE TO UNDO", Color.yellow);
                return;
            }
            UndoLastEdit();
        }

        private bool UpdateLeftStickHold(
            bool isPressed,
            bool editing,
            bool operating)
        {
            if (editing)
            {
                modeLockHoldTime = 0f;
                modeLockHoldLatched = false;
                return UpdateSafeExit(isPressed, editing: true);
            }

            exitHoldTime = 0f;
            if (!operating)
            {
                modeLockHoldTime = 0f;
                modeLockHoldLatched = false;
                return false;
            }

            if (!isPressed)
            {
                if (modeLockHoldTime > 0f &&
                    !modeLockHoldLatched)
                {
                    leftStickShortClickPending = true;
                }
                modeLockHoldTime = 0f;
                modeLockHoldLatched = false;
                return false;
            }

            if (modeLockHoldLatched)
                return true;

            modeLockHoldTime += Time.unscaledDeltaTime;
            SetStatus(
                $"{(modeSwitchLocked ? "UNLOCK" : "LOCK")} MODE SWITCH: " +
                $"HOLD L-STICK " +
                $"{Mathf.Clamp01(modeLockHoldTime / ModeLockHoldSeconds):P0}",
                modeSwitchLocked
                    ? new Color(0.2f, 1f, 0.65f)
                    : new Color(1f, 0.75f, 0.15f));
            if (modeLockHoldTime < ModeLockHoldSeconds)
                return true;

            modeSwitchLocked = !modeSwitchLocked;
            modeLockHoldLatched = true;
            PulseHaptics(OVRInput.Controller.LTouch);
            SetModeStatus();
            Debug.Log(
                $"[InteractionMode] X mode switch " +
                $"{(modeSwitchLocked ? "locked" : "unlocked")}.");
            return true;
        }

        private bool UpdateSafeExit(bool isPressed, bool editing)
        {
            if (isExiting)
                return true;

            if (!editing)
            {
                exitHoldTime = 0f;
                return false;
            }

            if (operationInProgress)
            {
                exitHoldTime = 0f;
                if (isPressed)
                    SetStatus("WAIT FOR SAVE BEFORE EXIT", Color.yellow);
                return isPressed;
            }

            if (!isPressed)
            {
                if (exitHoldTime > 0f)
                {
                    exitHoldTime = 0f;
                    SetModeStatus();
                    return true;
                }
                return false;
            }

            exitHoldTime += Time.unscaledDeltaTime;
            SetStatus(
                $"SAFE EXIT: HOLD L-STICK " +
                $"{Mathf.Clamp01(exitHoldTime / ExitHoldSeconds):P0}",
                new Color(1f, 0.35f, 0.1f));
            if (exitHoldTime < ExitHoldSeconds)
                return true;

            isExiting = true;
            SetPreviewVisible(false);
            SetMoveTargetMarkersVisible(false);
            if (controllerBeam != null)
                controllerBeam.enabled = false;
            if (leftControllerBeam != null)
                leftControllerBeam.enabled = false;
            SetStatus("EXITING SAFELY", Color.green);
            Debug.Log(
                "[Application] Safe exit requested by left stick hold in Edit mode.");

#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#elif UNITY_ANDROID
            try
            {
                using var unityPlayer =
                    new AndroidJavaClass("com.unity3d.player.UnityPlayer");
                using var activity =
                    unityPlayer.GetStatic<AndroidJavaObject>("currentActivity");
                activity?.Call("finishAndRemoveTask");
            }
            catch (AndroidJavaException exception)
            {
                Debug.LogWarning(
                    $"Could not finish Android activity: {exception.Message}");
            }
            Application.Quit();
#else
            Application.Quit();
#endif
            return true;
        }

        private static bool IsPressed(InputAction action)
        {
            return action != null && action.IsPressed();
        }

        private static float ReadFloat(InputAction action)
        {
            return action?.activeControl != null
                ? action.ReadValue<float>()
                : 0f;
        }

        private static Vector2 ReadVector2(InputAction action)
        {
            return action?.activeControl != null
                ? action.ReadValue<Vector2>()
                : Vector2.zero;
        }

        private void UpdateInstrumentInteractions(
            float rightTrigger,
            float leftTrigger,
            float rightGrip,
            float leftGrip,
            Vector2 rightStick,
            Vector2 leftStick,
            bool rightStickClick,
            bool leftStickClick)
        {
            var operationAllowed =
                AppInteractionModePolicy.AllowsInstrumentOperation(
                    interactionMode) &&
                !globalAudioPanelVisible &&
                !DevelopmentExitController.IsTriggerReserved &&
                !operationInProgress;
            if (!operationAllowed)
            {
                ReleaseOperationInteractions();
                rightOperationHand.TriggerEngaged =
                    rightTrigger > TriggerReleaseThreshold;
                leftOperationHand.TriggerEngaged =
                    leftTrigger > TriggerReleaseThreshold;
                rightOperationHand.GripEngaged =
                    rightGrip > OperationGripReleaseThreshold;
                leftOperationHand.GripEngaged =
                    leftGrip > OperationGripReleaseThreshold;
                return;
            }

            UpdateContactButtons();
            UpdateBeamButton(
                rightOperationHand,
                leftOperationHand,
                rightAimAnchor,
                rightTrigger);
            UpdateBeamButton(
                leftOperationHand,
                rightOperationHand,
                leftAimAnchor,
                leftTrigger);
            UpdateGripInteraction(
                rightOperationHand,
                leftOperationHand,
                rightControllerAnchor,
                rightTrigger,
                rightGrip);
            UpdateGripInteraction(
                leftOperationHand,
                rightOperationHand,
                leftControllerAnchor,
                leftTrigger,
                leftGrip);
            UpdateDirectionalStep(
                rightOperationHand,
                leftOperationHand,
                rightAimAnchor,
                rightTrigger,
                rightGrip);
            UpdateDirectionalStep(
                leftOperationHand,
                rightOperationHand,
                leftAimAnchor,
                leftTrigger,
                leftGrip);
            UpdateStickInteraction(
                rightOperationHand,
                leftOperationHand,
                rightAimAnchor,
                leftAimAnchor,
                rightStick,
                rightStickClick);
            UpdateStickInteraction(
                leftOperationHand,
                rightOperationHand,
                leftAimAnchor,
                rightAimAnchor,
                leftStick,
                leftStickClick);

            if (!HasActiveOperationInteraction() &&
                Time.unscaledTime >= operationStepNoticeUntil)
                UpdateOperationHoverStatus();
        }

        private void UpdateStickInteraction(
            HandOperationState hand,
            HandOperationState otherHand,
            Transform aimAnchor,
            Transform fallbackAimAnchor,
            Vector2 stick,
            bool resetPressed)
        {
            if (Mathf.Abs(stick.x) <= SelectionReleaseThreshold)
                hand.StickXEngaged = false;

            if (Mathf.Abs(stick.y) < OperationStickDeadZone &&
                hand.StickInteraction != null)
            {
                hand.StickInteraction.EndStickControl();
                SaveInteractionState(hand.StickInteraction);
                hand.StickInteraction = null;
                hand.StickTargetInitialized = false;
            }

            if (hand.GripInteraction != null ||
                hand.ContactButton != null ||
                hand.BeamButton != null)
                return;

            if (resetPressed &&
                TryResolveStickInteraction(
                    aimAnchor,
                    fallbackAimAnchor,
                    out var resetInteraction,
                    out var resetPlacement,
                    out var resetReach) &&
                !IsInteractionHeldByOtherHand(resetInteraction, otherHand))
            {
                var kind = GetPlacementKind(resetPlacement);
                if (hand.StickInteraction != null &&
                    !ReferenceEquals(
                        hand.StickInteraction,
                        resetInteraction))
                {
                    hand.StickInteraction.EndStickControl();
                    SaveInteractionState(hand.StickInteraction);
                }
                resetInteraction.SetNormalizedValue(
                    DefaultNormalizedValue(kind, resetPlacement),
                    InstrumentValueChangeOrigin.UserInteraction);
                hand.StickInteraction = resetInteraction;
                hand.StickTargetValue = resetInteraction.NormalizedValue;
                hand.StickTargetInitialized = true;
                SaveInteractionState(resetInteraction);
                PulseHaptics(hand.Controller);
                operationStepNoticeUntil = Time.unscaledTime + 0.6f;
                SetStatus(
                    $"{hand.Label} {resetReach.ToString().ToUpperInvariant()} " +
                    $"STICK CLICK: DEFAULT | " +
                    $"{MockInstrumentCatalog.GetDisplayName(kind)}\n" +
                    FormatOperationState(resetInteraction),
                    Color.green);
                return;
            }

            if (Mathf.Abs(stick.x) >= OperationStickSnapThreshold &&
                !hand.StickXEngaged &&
                TryResolveStickInteraction(
                    aimAnchor,
                    fallbackAimAnchor,
                    out var snapInteraction,
                    out var snapPlacement,
                    out var snapReach) &&
                !IsInteractionHeldByOtherHand(snapInteraction, otherHand))
            {
                hand.StickXEngaged = true;
                if (hand.StickInteraction != null &&
                    !ReferenceEquals(
                        hand.StickInteraction,
                        snapInteraction))
                {
                    hand.StickInteraction.EndStickControl();
                    SaveInteractionState(hand.StickInteraction);
                }
                snapInteraction.SetNormalizedValue(
                    stick.x < 0f ? 0f : 1f,
                    InstrumentValueChangeOrigin.UserInteraction);
                hand.StickInteraction = snapInteraction;
                hand.StickTargetValue = snapInteraction.NormalizedValue;
                hand.StickTargetInitialized = true;
                SaveInteractionState(snapInteraction);
                PulseHaptics(hand.Controller);
                operationStepNoticeUntil = Time.unscaledTime + 0.6f;
                SetStatus(
                    $"{hand.Label} {snapReach.ToString().ToUpperInvariant()} " +
                    $"STICK X: {(stick.x < 0f ? "MIN" : "MAX")} | " +
                    $"{MockInstrumentCatalog.GetDisplayName(GetPlacementKind(snapPlacement))}\n" +
                    FormatOperationState(snapInteraction),
                    Color.green);
                return;
            }

            if (Mathf.Abs(stick.y) < OperationStickDeadZone ||
                !TryResolveStickInteraction(
                    aimAnchor,
                    fallbackAimAnchor,
                    out var interaction,
                    out var placement,
                    out var reach) ||
                IsInteractionHeldByOtherHand(interaction, otherHand))
            {
                return;
            }

            if (!ReferenceEquals(hand.StickInteraction, interaction) ||
                !hand.StickTargetInitialized)
            {
                if (hand.StickInteraction != null &&
                    !ReferenceEquals(hand.StickInteraction, interaction))
                {
                    hand.StickInteraction.EndStickControl();
                    SaveInteractionState(hand.StickInteraction);
                }
                hand.StickInteraction = interaction;
                hand.StickTargetValue = interaction.NormalizedValue;
                hand.StickTargetInitialized = true;
            }
            var interactionKind = GetPlacementKind(placement);
            hand.StickTargetValue =
                OperationStickInputPolicy.ApplyVerticalDelta(
                    interactionKind,
                    hand.StickTargetValue,
                    stick.y,
                    OperationStickSpeed,
                    Time.unscaledDeltaTime);
            if (OperationStickInputPolicy.UsesInvertedVerticalDirection(
                    interactionKind))
            {
                interaction.SetStickControlledValue(hand.StickTargetValue);
            }
            else
            {
                interaction.SetNormalizedValue(
                    hand.StickTargetValue,
                    InstrumentValueChangeOrigin.UserInteraction);
            }
            operationStepNoticeUntil = Time.unscaledTime + 0.25f;
            SetStatus(
                $"{hand.Label} {reach.ToString().ToUpperInvariant()} " +
                $"STICK Y: ANALOG | " +
                $"{MockInstrumentCatalog.GetDisplayName(interactionKind)}\n" +
                FormatOperationState(interaction),
                Color.green);
        }

        private bool TryResolveStickInteraction(
            Transform primaryAimAnchor,
            Transform fallbackAimAnchor,
            out MockInstrumentInteraction interaction,
            out RuntimePlacement placement,
            out InstrumentInteractionHitTest.Reach reach)
        {
            if (TryResolveOperationInteraction(
                    primaryAimAnchor,
                    OperationResolveMode.StickControl,
                    out interaction,
                    out placement,
                    out reach))
            {
                return true;
            }
            return TryResolveOperationInteraction(
                fallbackAimAnchor,
                OperationResolveMode.StickControl,
                out interaction,
                out placement,
                out reach);
        }

        private static float DefaultNormalizedValue(
            MockInstrumentKind kind,
            RuntimePlacement placement)
        {
            var descriptors = AdjustableParameterPolicy.Descriptors(kind);
            if (descriptors.Count == 0)
            {
                return placement?.Interaction?.Motion != null
                    ? placement.Interaction.Motion.DefaultNormalizedValue
                    : 0.5f;
            }
            var settings = AdjustableParameterPolicy.NormalizeSettings(
                kind,
                placement?.Record?.parameterSettings,
                placement?.Interaction?.NormalizedValue ?? 0.5f);
            if (settings.Count == 0)
                return 0.5f;
            var parameterPosition = AdjustableParameterPolicy.InverseMap(
                descriptors[0].DefaultValue,
                settings[0]);
            if (kind == MockInstrumentKind.AudioSequencer)
                return parameterPosition * 0.5f;
            if (kind == MockInstrumentKind.AudioEnvelope)
            {
                return descriptors[0].DefaultValue >
                       (settings[0].minimum + settings[0].maximum) * 0.5f
                    ? 1f
                    : 0f;
            }
            return parameterPosition;
        }

        private void UpdateDirectionalStep(
            HandOperationState hand,
            HandOperationState otherHand,
            Transform controllerAnchor,
            float triggerValue,
            float gripValue)
        {
            if (triggerValue <= TriggerReleaseThreshold &&
                gripValue <= OperationGripReleaseThreshold)
            {
                hand.ResetChordEngaged = false;
            }

            if (hand.ContactButton != null || hand.BeamButton != null)
            {
                hand.PendingStepDirection = 0;
                hand.TriggerEngaged = triggerValue > TriggerReleaseThreshold;
                hand.GripEngaged = gripValue > OperationGripReleaseThreshold;
                return;
            }

            var triggerDown = triggerValue >= TriggerPressThreshold;
            var gripDown = gripValue >= OperationGripPressThreshold;
            if (triggerDown && gripDown &&
                hand.GripInteraction == null &&
                !hand.ResetChordEngaged &&
                TryResetSoundModuleValue(hand, otherHand, controllerAnchor))
            {
                hand.ResetChordEngaged = true;
            }
            if ((triggerValue > TriggerReleaseThreshold && gripDown) ||
                (gripValue > OperationGripReleaseThreshold && triggerDown) ||
                hand.GripInteraction != null)
            {
                hand.PendingStepDirection = 0;
                hand.TriggerEngaged = true;
                hand.GripEngaged = true;
                return;
            }

            if (hand.PendingStepDirection != 0)
            {
                var released = hand.PendingStepDirection > 0
                    ? triggerValue <= TriggerReleaseThreshold
                    : gripValue <= OperationGripReleaseThreshold;
                if (released || Time.unscaledTime >= hand.PendingStepDeadline)
                {
                    TryApplyDirectionalStep(
                        hand,
                        otherHand,
                        controllerAnchor,
                        hand.PendingStepDirection);
                    hand.PendingStepDirection = 0;
                }
            }

            if (triggerValue <= TriggerReleaseThreshold)
                hand.TriggerEngaged = false;
            if (gripValue <= OperationGripReleaseThreshold)
                hand.GripEngaged = false;

            if (triggerDown && !hand.TriggerEngaged && !gripDown)
            {
                hand.TriggerEngaged = true;
                hand.PendingStepDirection = 1;
                hand.PendingStepDeadline =
                    Time.unscaledTime + OperationChordWindowSeconds;
            }
            else if (gripDown && !hand.GripEngaged && !triggerDown)
            {
                hand.GripEngaged = true;
                hand.PendingStepDirection = -1;
                hand.PendingStepDeadline =
                    Time.unscaledTime + OperationChordWindowSeconds;
            }
        }

        private bool TryResetSoundModuleValue(
            HandOperationState hand,
            HandOperationState otherHand,
            Transform controllerAnchor)
        {
            if (!TryResolveOperationInteraction(
                    controllerAnchor,
                    OperationResolveMode.Any,
                    out var interaction,
                    out var placement,
                    out var reach) ||
                !MockInstrumentCatalog.IsSoundModule(
                    GetPlacementKind(placement)) ||
                IsInteractionHeldByOtherHand(interaction, otherHand))
            {
                return false;
            }

            var kind = GetPlacementKind(placement);
            interaction.SetNormalizedValue(
                DefaultNormalizedValue(kind, placement),
                InstrumentValueChangeOrigin.UserInteraction);
            SaveInteractionState(interaction);
            PulseHaptics(hand.Controller);
            operationStepNoticeUntil = Time.unscaledTime + 0.5f;
            SetStatus(
                $"{hand.Label} {reach.ToString().ToUpperInvariant()} " +
                $"TRIGGER + GRIP RESET | " +
                $"{MockInstrumentCatalog.GetDisplayName(kind)}\n" +
                FormatOperationState(interaction),
                Color.green);
            return true;
        }

        private void TryApplyDirectionalStep(
            HandOperationState hand,
            HandOperationState otherHand,
            Transform controllerAnchor,
            int direction)
        {
            if (!TryResolveOperationInteraction(
                    controllerAnchor,
                    OperationResolveMode.DirectionalStep,
                    out var interaction,
                    out var placement,
                    out var reach) ||
                IsInteractionHeldByOtherHand(interaction, otherHand))
            {
                return;
            }

            interaction.Step(direction);
            SaveInteractionState(interaction);
            PulseHaptics(hand.Controller);
            operationStepNoticeUntil = Time.unscaledTime + 0.5f;
            var kind = GetPlacementKind(placement);
            SetStatus(
                $"{hand.Label} {reach.ToString().ToUpperInvariant()} " +
                (direction > 0 ? "TRIGGER + | " : "GRIP - | ") +
                $"{MockInstrumentCatalog.GetDisplayName(kind)}\n" +
                FormatOperationState(interaction),
                Color.green);
        }

        private void UpdateGripInteraction(
            HandOperationState hand,
            HandOperationState otherHand,
            Transform controllerAnchor,
            float triggerValue,
            float gripValue)
        {
            if (hand.GripInteraction != null)
            {
                if (triggerValue <= TriggerReleaseThreshold ||
                    gripValue <= OperationGripReleaseThreshold ||
                    controllerAnchor == null ||
                    hand.GripPlacement?.Root == null)
                {
                    ReleaseGripInteraction(hand);
                    return;
                }

                var kind = GetPlacementKind(hand.GripPlacement);
                float normalizedValue;
                if (hand.GripInteraction.Motion.Kind ==
                        MockInstrumentMotion.MotionKind.Rotate ||
                    kind == MockInstrumentKind.ThrottleLever ||
                    kind == MockInstrumentKind.Lever)
                {
                    var rotationAxis =
                        hand.GripInteraction.Motion.Kind ==
                            MockInstrumentMotion.MotionKind.Rotate
                            ? hand.GripPlacement.Root.transform.forward
                            : hand.GripPlacement.Root.transform.right;
                    var pivot =
                        hand.GripInteraction.Motion.MovingPart != null
                            ? hand.GripInteraction.Motion.MovingPart.position
                            : hand.GripPlacement.Root.transform.position;
                    var currentDirection = Vector3.ProjectOnPlane(
                        controllerAnchor.position - pivot,
                        rotationAxis);
                    var arcDegrees = currentDirection.sqrMagnitude > 0.0001f
                        ? Vector3.SignedAngle(
                            hand.GripStartDirection,
                            currentDirection.normalized,
                            rotationAxis)
                        : 0f;
                    var maximumAngle =
                        hand.GripInteraction.Motion.Kind ==
                            MockInstrumentMotion.MotionKind.Rotate
                            ? RotaryGripTravelDegrees * 0.5f
                        : kind == MockInstrumentKind.ThrottleLever
                            ? InstrumentGreyboxSpecification
                                .ThrottleMaximumAngleDegrees
                            : InstrumentGreyboxSpecification
                                .LeverMaximumAngleDegrees;
                    normalizedValue =
                        hand.GripStartValue +
                        arcDegrees / (maximumAngle * 2f);
                }
                else
                {
                    var travel = GripMotionTravel(kind);
                    var movement = Vector3.Dot(
                        controllerAnchor.position -
                        hand.GripStartPosition,
                        hand.GripPlacement.Root.transform.up);
                    normalizedValue =
                        hand.GripStartValue + movement / travel;
                }
                hand.GripInteraction.SetNormalizedValue(
                    normalizedValue,
                    InstrumentValueChangeOrigin.UserInteraction);
                if (hand.GripLastDetent !=
                    hand.GripInteraction.DetentIndex)
                {
                    hand.GripLastDetent =
                        hand.GripInteraction.DetentIndex;
                    PulseHaptics(hand.Controller);
                }
                SetStatus(
                    $"{hand.Label} TRIGGER + GRIP + CONTACT | " +
                    $"{MockInstrumentCatalog.GetDisplayName(kind)}\n" +
                    FormatOperationState(hand.GripInteraction),
                    Color.green);
                return;
            }

            if (triggerValue < TriggerPressThreshold ||
                gripValue < OperationGripPressThreshold ||
                controllerAnchor == null)
            {
                return;
            }

            if (!TryResolveOperationInteraction(
                    controllerAnchor,
                    OperationResolveMode.GripMotion,
                    out var interaction,
                    out var placement,
                    out var reach) ||
                reach != InstrumentInteractionHitTest.Reach.Direct ||
                IsInteractionHeldByOtherHand(interaction, otherHand))
            {
                return;
            }

            hand.GripInteraction = interaction;
            hand.PendingStepDirection = 0;
            hand.GripPlacement = placement;
            hand.GripStartPosition = controllerAnchor.position;
            var captureAxis = interaction.Motion.Kind ==
                              MockInstrumentMotion.MotionKind.Rotate
                ? placement.Root.transform.forward
                : placement.Root.transform.right;
            var capturePivot = interaction.Motion.MovingPart != null
                ? interaction.Motion.MovingPart.position
                : placement.Root.transform.position;
            var startDirection = Vector3.ProjectOnPlane(
                controllerAnchor.position - capturePivot,
                captureAxis);
            hand.GripStartDirection = startDirection.sqrMagnitude > 0.0001f
                ? startDirection.normalized
                : placement.Root.transform.up;
            hand.GripStartValue = interaction.NormalizedValue;
            hand.GripLastDetent = interaction.DetentIndex;
            PulseHaptics(hand.Controller);
            var displayName = MockInstrumentCatalog.GetDisplayName(
                GetPlacementKind(placement));
            var moveInstruction = interaction.Motion.Kind ==
                                  MockInstrumentMotion.MotionKind.Rotate
                ? "ROTATE AROUND KNOB"
                : GetPlacementKind(placement) switch
                {
                    MockInstrumentKind.ThrottleLever =>
                        "MOVE THROUGH THROTTLE ARC",
                    MockInstrumentKind.Lever =>
                        "MOVE THROUGH LEVER ARC",
                    _ => "MOVE UP / DOWN"
                };
            SetStatus(
                $"{hand.Label} TRIGGER + GRIP CONTACT | " +
                $"{displayName}\n" +
                moveInstruction,
                Color.green);
        }

        private static float GripMotionTravel(MockInstrumentKind kind)
        {
            return kind switch
            {
                MockInstrumentKind.PowerSlider =>
                    InstrumentGreyboxSpecification.PowerSliderTravelMeters,
                _ => LeverGripTravelMeters
            };
        }

        private static bool IsInteractionHeldByOtherHand(
            MockInstrumentInteraction interaction,
            HandOperationState otherHand)
        {
            return ReferenceEquals(interaction, otherHand.GripInteraction) ||
                   ReferenceEquals(interaction, otherHand.StickInteraction) ||
                   ReferenceEquals(interaction, otherHand.ContactButton) ||
                   ReferenceEquals(interaction, otherHand.BeamButton);
        }

        private bool HasActiveOperationInteraction()
        {
            return rightOperationHand.GripInteraction != null ||
                   leftOperationHand.GripInteraction != null ||
                   rightOperationHand.StickInteraction != null ||
                   leftOperationHand.StickInteraction != null ||
                   rightOperationHand.ContactButton != null ||
                   leftOperationHand.ContactButton != null ||
                   rightOperationHand.BeamButton != null ||
                   leftOperationHand.BeamButton != null;
        }

        private void UpdateOperationHoverStatus()
        {
            if (TrySetOperationHoverStatus(
                    rightOperationHand,
                    rightAimAnchor))
            {
                return;
            }
            TrySetOperationHoverStatus(
                leftOperationHand,
                leftAimAnchor);
        }

        private bool TrySetOperationHoverStatus(
            HandOperationState hand,
            Transform controllerAnchor)
        {
            if (!TryResolveOperationInteraction(
                    controllerAnchor,
                    OperationResolveMode.Any,
                    out var interaction,
                    out var placement,
                    out var reach))
            {
                return false;
            }

            var kind = GetPlacementKind(placement);
            string instruction;
            if (MockInstrumentCatalog.IsReadOnlyMeter(kind) ||
                kind == MockInstrumentKind.TrendMonitor)
            {
                instruction = "READ ONLY | AMBIENT MOTION";
            }
            else if (MockInstrumentCatalog.UsesContactPress(kind))
            {
                instruction = reach == InstrumentInteractionHitTest.Reach.Direct
                    ? "CONTACT PRESS"
                    : "TRIGGER: BEAM PRESS | CONTACT: PRESS";
            }
            else if (MockInstrumentCatalog.IsSoundModule(kind))
            {
                instruction = "TRIGGER + | GRIP - | BOTH: RESET";
            }
            else if (MockInstrumentCatalog.SupportsDirectionalStep(kind))
            {
                instruction = reach == InstrumentInteractionHitTest.Reach.Direct
                    ? "TRIGGER + | GRIP - | BOTH + MOVE"
                    : "TRIGGER + | GRIP - | TOUCH + BOTH TO MOVE";
            }
            else
            {
                instruction = "READ ONLY";
            }

            SetStatus(
                $"{hand.Label} {reach.ToString().ToUpperInvariant()} READY | " +
                $"{MockInstrumentCatalog.GetDisplayName(kind)}\n" +
                instruction,
                Color.white);
            return true;
        }

        private static string FormatOperationState(
            MockInstrumentInteraction interaction)
        {
            if (!string.IsNullOrEmpty(interaction.StateName))
            {
                return
                    $"STATE {interaction.StateName} | " +
                    $"{interaction.DetentIndex + 1}/{interaction.DetentCount}\n" +
                    $"VALUE {interaction.NormalizedValue:0.000}";
            }
            if (interaction.DetentCount > 0)
            {
                var signedPosition =
                    interaction.DetentIndex -
                    (interaction.DetentCount - 1) / 2;
                return
                    $"DETENT {interaction.DetentIndex + 1}/" +
                    $"{interaction.DetentCount} | " +
                    $"POSITION {signedPosition:+0;-0;0}\n" +
                    $"VALUE {interaction.NormalizedValue:0.000}";
            }
            return $"VALUE {interaction.NormalizedValue:0.000}";
        }

        private void ToggleInteractionMode(
            float rightTriggerValue,
            float leftTriggerValue)
        {
            ReleaseActiveInteraction();
            ClearGroupMoveSelection();
            ClearConnectSelection();
            connectionEditing = false;
            editMoveChordActive = false;
            editPlacementModifierChordActive = false;
            pendingLeftSelection = false;
            pendingMoveUndo = false;
            pendingRightCancel = false;
            editMoveCancelledUntilChordRelease = false;
            interactionMode = AppInteractionModePolicy.Toggle(interactionMode);
            rightOperationHand.TriggerEngaged =
                rightTriggerValue > TriggerReleaseThreshold;
            leftOperationHand.TriggerEngaged =
                leftTriggerValue > TriggerReleaseThreshold;
            connectRightTriggerEngaged =
                rightTriggerValue > TriggerReleaseThreshold;
            connectLeftTriggerEngaged =
                leftTriggerValue > TriggerReleaseThreshold;
            connectAxisEngaged = false;
            selectionAxisEngaged = false;
            themeAxisEngaged = false;
            SetPreviewVisible(false);
            SetSurfaceWireframesVisible(
                AppInteractionModePolicy.AllowsEditing(interactionMode));
            PulseHaptics();
            SetModeStatus();
            Debug.Log($"[InteractionMode] Switched to {interactionMode} mode.");
        }

        private void SetModeStatus()
        {
            var roomPrefix = CurrentRoomStatusPrefix();
            SetSurfaceWireframesVisible(
                AppInteractionModePolicy.AllowsEditing(interactionMode));
            SetAmbientMeterAnimationState(
                AppInteractionModePolicy.AllowsInstrumentOperation(
                    interactionMode));
            if (AppInteractionModePolicy.AllowsEditing(interactionMode))
            {
                SetStatus(
                    connectionEditing
                        ? roomPrefix + "EDIT: CONNECTIONS | X: OPERATE\n" +
                          "R-TRIGGER: SELECT ENDPOINTS | A: CONFIRM\n" +
                          "L-TRIGGER: PLACEMENT | Y: PARAMETERS\n" +
                          "R-GRIP: CANCEL | B: DELETE/CANCEL\n" +
                          "L-STICK PRESS: APPLY"
                        : roomPrefix + "EDIT: PLACEMENT | X: OPERATE\n" +
                          "L-TRIGGER: SELECT | A: PLACE\n" +
                          "L-TRIGGER+GRIP: MOVE; RELEASE: SAVE\n" +
                          "CHORD+L-STICK: UP AUTO | DOWN GRID\n" +
                          "L-GRIP: CANCEL/UNDO | R-GRIP: CANCEL\n" +
                          "R-TRIGGER: CONNECT\n" +
                          "HOLD L-STICK 2s TO EXIT",
                    connectionEditing
                        ? ConnectBeamColor
                        : new Color(1f, 0.75f, 0.15f));
                return;
            }

            SetStatus(
                modeSwitchLocked
                    ? roomPrefix +
                      "OPERATION MODE | MODE SWITCH LOCKED\n" +
                      $"A: CONNECTIONS {(operationConnectionVisualsVisible ? "ON" : "OFF")} | B: THEME\n" +
                      "X: SE | Y: AUDIO | HOLD Y: AUDIO MENU\n" +
                      "STICK Y: ADJUST | X: MIN/MAX | CLICK: RESET\n" +
                      "HOLD L-STICK 2s: UNLOCK"
                    : roomPrefix + "OPERATION MODE | X: EDIT\n" +
                      "B: NEXT THEME | HOLD L-STICK 2s: LOCK\n" +
                      "STICK Y: ADJUST | X: MIN/MAX | CLICK: RESET\n" +
                      "TRIGGER + | GRIP - | BOTH + CONTACT: MOVE\n" +
                      "BUTTON/TOGGLE: TOUCH | METERS: READ ONLY",
                modeSwitchLocked
                    ? new Color(1f, 0.65f, 0.1f)
                    : new Color(0.2f, 0.9f, 1f));
        }

        private string CurrentRoomStatusPrefix()
        {
            var rooms = MRUK.Instance?.Rooms;
            if (currentRoom == null ||
                rooms == null ||
                rooms.Count <= 1)
            {
                return string.Empty;
            }

            var index = rooms.IndexOf(currentRoom);
            return index >= 0
                ? $"ROOM {index + 1}/{rooms.Count} | "
                : "ROOM ? | ";
        }

        private void UpdateConnectInput(
            float rightTrigger,
            float leftTrigger,
            Vector2 transformAxis,
            Vector2 parameterAxis,
            bool parameterEditPressed,
            bool transformConfirmPressed,
            bool confirmPressed,
            bool cancelPressed)
        {
            if (audioParameterEditPlacement != null)
            {
                UpdateAudioParameterInput(
                    transformAxis,
                    parameterAxis,
                    transformConfirmPressed || confirmPressed,
                    cancelPressed);
                return;
            }
            if (connectionParameterDraft != null)
            {
                UpdateConnectionParameterInput(
                    transformAxis,
                    parameterAxis,
                    parameterEditPressed,
                    transformConfirmPressed,
                    cancelPressed);
                return;
            }

            if (parameterEditPressed)
            {
                if (selectedConnectionForRemoval != null)
                {
                    BeginConnectionParameterEdit();
                }
                else if (connectSource != null && connectTarget == null &&
                         ModularAudioParameterPolicy.SupportsEditing(
                             GetPlacementKind(connectSource)))
                {
                    BeginAudioParameterEdit();
                }
                else
                {
                    SetConnectNotice(
                        "SELECT AN EDITABLE MODULE SOURCE FIRST",
                        Color.yellow);
                }
                return;
            }

            UpdateConnectTargetSettings(parameterAxis);

            var axisMagnitude = Mathf.Abs(transformAxis.x);
            if (axisMagnitude <= SelectionReleaseThreshold)
            {
                connectAxisEngaged = false;
            }
            else if (!connectAxisEngaged &&
                     axisMagnitude >= SelectionThreshold &&
                     selectedAudioPatchForRemoval == null &&
                     (selectedConnectionForRemoval != null ||
                      connectSource != null))
            {
                connectAxisEngaged = true;
                var direction = transformAxis.x < 0f ? -1 : 1;
                if (selectedConnectionForRemoval != null)
                {
                    selectedConnectionPendingTransform =
                        InstrumentSignalPolicy.Cycle(
                            selectedConnectionPendingTransform,
                            direction);
                    PulseHaptics();
                    UpdateConnectStatus();
                }
                else if (ModularAudioPatchPolicy.GetSelectableOutputCount(
                             GetPlacementKind(connectSource)) > 1 &&
                         (!ModularAudioPatchPolicy.SupportsSignalRole(
                              GetPlacementKind(connectSource)) ||
                          pendingObservableAudioSource))
                {
                    pendingObservableOutputIndex =
                        ModularAudioPatchPolicy.CycleSelectableOutput(
                            GetPlacementKind(connectSource),
                            pendingObservableOutputIndex,
                            direction);
                    PulseHaptics();
                    UpdateConnectStatus();
                }
                else if (!ModularAudioPatchPolicy.CanSource(
                             GetPlacementKind(connectSource)))
                {
                    pendingSignalTransform =
                        InstrumentSignalPolicy.Cycle(
                            pendingSignalTransform,
                            direction);
                    PulseHaptics();
                    UpdateConnectStatus();
                }
            }

            if (transformConfirmPressed &&
                selectedConnectionForRemoval != null)
            {
                ConfirmSelectedConnectionTransform();
                return;
            }

            var endpointAction = UpdateConnectTrigger(
                ref connectRightTriggerEngaged,
                rightTrigger,
                rightAimAnchor);
            endpointAction |= UpdateConnectTrigger(
                ref connectLeftTriggerEngaged,
                leftTrigger,
                leftAimAnchor);

            if (confirmPressed)
            {
                if (connectSource != null && connectTarget != null)
                    ConfirmPendingConnection();
                else
                    SelectNextConnectionForRemoval();
                return;
            }

            if (cancelPressed)
            {
                if (selectedConnectionForRemoval != null ||
                    selectedAudioPatchForRemoval != null)
                {
                    DeleteSelectedConnection();
                }
                else if (connectSource != null ||
                         connectTarget != null ||
                         connectEditPlacement != null)
                {
                    ClearConnectSelection();
                    SetModeStatus();
                    PulseHaptics();
                }
                else
                {
                    SetConnectNotice(
                        "SELECT ONE OBJECT + TRIGGER\n" +
                        "A: SELECT CONNECTION | B: DELETE",
                        Color.yellow);
                }
                return;
            }

            if (!endpointAction)
                UpdateConnectStatus();
        }

        private void UpdateConnectTargetSettings(Vector2 axis)
        {
            var selectedTarget = selectedConnectionForRemoval == null
                ? null
                : FindPlacementById(
                    selectedConnectionForRemoval.targetPlacementId);
            var editsWindowPanelSlot = selectedTarget != null &&
                                       GetPlacementKind(selectedTarget) ==
                                       MockInstrumentKind.WindowPanel;
            var editsPriority = selectedTarget?.Record != null &&
                                SignalCompositionEditor.NormalizeKind(
                                    selectedTarget.Record
                                        .signalCompositionKind) ==
                                SignalCompositionKind.Priority;
            var slotMagnitude = Mathf.Abs(axis.x);
            if (slotMagnitude <= SelectionReleaseThreshold)
            {
                connectSlotAxisEngaged = false;
            }
            else if ((editsWindowPanelSlot || editsPriority) &&
                     !connectSlotAxisEngaged &&
                     slotMagnitude >= SelectionThreshold)
            {
                connectSlotAxisEngaged = true;
                if (editsWindowPanelSlot)
                {
                    selectedConnectionPendingSlot =
                        WindowPanelInputSlotPolicy.CycleAvailable(
                            placementDocument?.connections,
                            selectedConnectionForRemoval.targetPlacementId,
                            selectedConnectionForRemoval.connectionId,
                            selectedConnectionPendingSlot,
                            axis.x < 0f ? -1 : 1);
                }
                else
                {
                    selectedConnectionPendingPriority =
                        SignalCompositionEditor.CyclePriority(
                            selectedConnectionPendingPriority,
                            axis.x < 0f ? -1 : 1);
                }
                PulseHaptics();
                UpdateConnectStatus();
            }

            var targetPlacement = connectEditPlacement ?? connectTarget;
            var editsTargetSetting =
                selectedConnectionForRemoval == null &&
                targetPlacement?.Record != null;
            var targetKind = editsTargetSetting
                ? GetPlacementKind(targetPlacement)
                : MockInstrumentKind.RoundMeter;
            var editsPreset = editsTargetSetting &&
                              targetKind == MockInstrumentKind.WindowPanel;
            var editsComposition = editsTargetSetting &&
                                   SignalCompositionEditor
                                       .CanConfigureTarget(targetKind);
            var settingMagnitude = Mathf.Abs(axis.y);
            if (settingMagnitude <= SelectionReleaseThreshold)
            {
                connectTargetSettingAxisEngaged = false;
            }
            else if ((editsPreset || editsComposition) &&
                     !connectTargetSettingAxisEngaged &&
                     settingMagnitude >= SelectionThreshold)
            {
                connectTargetSettingAxisEngaged = true;
                var direction = axis.y < 0f ? 1 : -1;
                if (editsPreset)
                    CycleWindowPanelPreset(direction);
                else
                    CycleSignalComposition(targetPlacement, direction);
            }
        }

        private void CycleSignalComposition(
            RuntimePlacement placement,
            int direction)
        {
            var record = placement?.Record;
            if (record == null ||
                !SignalCompositionEditor.CanConfigureTarget(
                    GetPlacementKind(placement)))
            {
                return;
            }

            var previous = record.signalCompositionKind;
            var next = SignalCompositionEditor.CycleKind(
                previous,
                direction);
            record.signalCompositionKind = (int)next;
            if (!SavePlacementDocument())
            {
                record.signalCompositionKind = previous;
                SetConnectNotice("COMPOSITION SAVE FAILED", Color.red);
                return;
            }

            UpdateSignalGraph();
            SetConnectNotice(
                $"COMPOSITION: {next.ToString().ToUpperInvariant()} | " +
                $"OUTPUT {placement.Interaction?.NormalizedValue ?? 0f:0.00}",
                ConnectionEditObjectColor,
                0.6f);
            PulseHaptics();
        }

        private void CycleWindowPanelPreset(int direction)
        {
            var record = (connectEditPlacement ?? connectTarget)?.Record;
            if (record == null)
                return;
            var previous = record.windowPanelPreset;
            const int presetCount = 3;
            record.windowPanelPreset =
                (previous + (direction < 0 ? -1 : 1) + presetCount) %
                presetCount;
            if (!SavePlacementDocument())
            {
                record.windowPanelPreset = previous;
                SetConnectNotice("WINDOW PANEL PRESET SAVE FAILED", Color.red);
                return;
            }
            SetConnectNotice(
                $"WINDOW PANEL PRESET: " +
                $"{((WindowPanelGraphicPreset)record.windowPanelPreset).ToString().ToUpperInvariant()}",
                ConnectionEditObjectColor,
                0.6f);
            PulseHaptics();
        }

        private void BeginConnectionParameterEdit()
        {
            if (selectedConnectionForRemoval == null)
                return;
            if (!SignalConnectionParameterEditor.Supports(
                    selectedConnectionPendingTransform))
            {
                SetConnectNotice(
                    "PARAMETERS APPLY TO RANGE / THRESHOLD",
                    Color.yellow);
                return;
            }

            connectionParameterDraft =
                selectedConnectionForRemoval.Clone();
            connectionParameterDraft.transformKind =
                (int)selectedConnectionPendingTransform;
            connectionParameterDraft.targetInputSlot =
                selectedConnectionPendingSlot;
            connectionParameterDraft.compositionPriority =
                selectedConnectionPendingPriority;
            connectionParameterField =
                SignalConnectionParameterEditor.FirstField(
                    selectedConnectionPendingTransform);
            connectAxisEngaged = false;
            connectParameterFieldAxisEngaged = false;
            connectStatusHoldUntil = 0f;
            PulseHaptics();
            UpdateConnectStatus();
        }

        private void UpdateConnectionParameterInput(
            Vector2 adjustmentAxis,
            Vector2 fieldAxis,
            bool parameterEditPressed,
            bool confirmPressed,
            bool cancelPressed)
        {
            if (connectionParameterDraft == null ||
                selectedConnectionForRemoval == null)
            {
                CancelConnectionParameterEdit();
                return;
            }

            var fieldMagnitude = Mathf.Abs(fieldAxis.y);
            if (fieldMagnitude <= SelectionReleaseThreshold)
            {
                connectParameterFieldAxisEngaged = false;
            }
            else if (!connectParameterFieldAxisEngaged &&
                     fieldMagnitude >= SelectionThreshold)
            {
                connectParameterFieldAxisEngaged = true;
                connectionParameterField =
                    SignalConnectionParameterEditor.CycleField(
                        selectedConnectionPendingTransform,
                        connectionParameterField,
                        fieldAxis.y < 0f ? 1 : -1);
                PulseHaptics();
            }

            var adjustmentMagnitude = Mathf.Abs(adjustmentAxis.x);
            if (adjustmentMagnitude <= SelectionReleaseThreshold)
            {
                connectAxisEngaged = false;
            }
            else if (!connectAxisEngaged &&
                     adjustmentMagnitude >= SelectionThreshold)
            {
                connectAxisEngaged = true;
                SignalConnectionParameterEditor.Adjust(
                    connectionParameterDraft,
                    connectionParameterField,
                    adjustmentAxis.x < 0f ? -1 : 1);
                PulseHaptics();
            }

            if (confirmPressed)
            {
                ConfirmConnectionParameterEdit();
                return;
            }
            if (cancelPressed || parameterEditPressed)
            {
                CancelConnectionParameterEdit();
                SetConnectNotice(
                    "PARAMETER EDIT CANCELLED",
                    Color.yellow);
                return;
            }
            UpdateConnectStatus();
        }

        private void ConfirmConnectionParameterEdit()
        {
            if (selectedConnectionForRemoval == null ||
                connectionParameterDraft == null ||
                placementDocument?.connections == null ||
                !placementDocument.connections.Contains(
                    selectedConnectionForRemoval))
            {
                CancelConnectionParameterEdit();
                SetConnectNotice("CONNECTION NO LONGER EXISTS", Color.red);
                return;
            }

            var connection = selectedConnectionForRemoval;
            var previous = connection.Clone();
            CopyConnectionState(connectionParameterDraft, connection);
            if (!SavePlacementDocument())
            {
                CopyConnectionState(previous, connection);
                SetConnectNotice("PARAMETER SAVE FAILED", Color.red);
                return;
            }

            var confirmedTransform =
                (SignalTransformKind)connection.transformKind;
            connectionParameterDraft = null;
            selectedConnectionForRemoval = null;
            selectedConnectionPendingTransform =
                SignalTransformKind.Direct;
            connectAxisEngaged = false;
            connectParameterFieldAxisEngaged = false;
            SetConnectNotice(
                $"{confirmedTransform.ToString().ToUpperInvariant()} " +
                "PARAMETERS APPLIED\nOBJECT REMAINS SELECTED | A: NEXT",
                ConnectionColor(confirmedTransform));
            PulseHaptics();
        }

        private void CancelConnectionParameterEdit()
        {
            connectionParameterDraft = null;
            connectAxisEngaged = false;
            connectParameterFieldAxisEngaged = false;
            connectStatusHoldUntil = 0f;
        }

        private static void CopyConnectionState(
            SignalConnectionRecord source,
            SignalConnectionRecord destination)
        {
            destination.transformKind = source.transformKind;
            destination.inputMinimum = source.inputMinimum;
            destination.inputMaximum = source.inputMaximum;
            destination.outputMinimum = source.outputMinimum;
            destination.outputMaximum = source.outputMaximum;
            destination.thresholdValue = source.thresholdValue;
            destination.thresholdComparison = source.thresholdComparison;
            destination.targetInputSlot = source.targetInputSlot;
            destination.compositionPriority = source.compositionPriority;
        }

        private void BeginAudioParameterEdit()
        {
            if (connectSource?.Record == null ||
                !ModularAudioParameterPolicy.SupportsEditing(
                    GetPlacementKind(connectSource)))
            {
                return;
            }

            audioParameterEditPlacement = connectSource;
            audioParameterOriginal = connectSource.Record.Clone();
            ApplyAudioParameters(connectSource);
            audioParameterEntryIndex = 0;
            audioParameterStepIndex =
                connectSource.AudioModule?.Node is
                    ModularSequencerNode sequencer
                    ? Mathf.Clamp(
                        sequencer.CurrentStep,
                        0,
                        sequencer.StepCount - 1)
                    : 0;
            audioParameterSettingField = AdjustableParameterField.Value;
            audioParameterFieldAxisEngaged = false;
            audioParameterValueAxisEngaged = false;
            connectStatusHoldUntil = 0f;
            PulseHaptics();
            UpdateAudioParameterEditStatus();
        }

        private void UpdateAudioParameterInput(
            Vector2 fieldAxis,
            Vector2 valueAxis,
            bool confirmPressed,
            bool cancelPressed)
        {
            var placement = audioParameterEditPlacement;
            if (placement?.Record == null)
            {
                CancelAudioParameterEdit(true);
                SetConnectNotice("MODULE NO LONGER EXISTS", Color.red);
                return;
            }

            var kind = GetPlacementKind(placement);
            var fieldMagnitude = Mathf.Max(
                Mathf.Abs(fieldAxis.x),
                Mathf.Abs(fieldAxis.y));
            if (fieldMagnitude <= SelectionReleaseThreshold)
            {
                audioParameterFieldAxisEngaged = false;
            }
            else if (!audioParameterFieldAxisEngaged &&
                     fieldMagnitude >= SelectionThreshold)
            {
                audioParameterFieldAxisEngaged = true;
                var horizontal = Mathf.Abs(fieldAxis.x) >=
                                 Mathf.Abs(fieldAxis.y);
                var direction = horizontal
                    ? fieldAxis.x < 0f ? -1 : 1
                    : fieldAxis.y < 0f ? -1 : 1;
                var descriptors = AdjustableParameterPolicy.Descriptors(kind);
                if (horizontal)
                {
                    var entryCount = descriptors.Count +
                                     SpecialParameterEntryCount(kind);
                    audioParameterEntryIndex = entryCount > 0
                        ? (audioParameterEntryIndex +
                           (direction < 0 ? entryCount - 1 : 1)) %
                          entryCount
                        : 0;
                }
                else if (audioParameterEntryIndex < descriptors.Count)
                {
                    var descriptor =
                        descriptors[audioParameterEntryIndex];
                    audioParameterSettingField = descriptor.Id ==
                        AdjustableParameterPolicy.SequencerPlaybackModeId
                            ? AdjustableParameterField.Value
                            : AdjustableParameterPolicy.CycleField(
                                audioParameterSettingField,
                                direction);
                }
                else if (kind == MockInstrumentKind.AudioSequencer)
                {
                    var stepCount =
                        (placement.AudioModule?.Node as
                            ModularSequencerNode)?.StepCount ?? 8;
                    audioParameterStepIndex =
                        ModularAudioParameterPolicy.CycleStepIndex(
                            audioParameterStepIndex,
                            stepCount,
                            direction);
                }
                PulseHaptics();
            }

            var valueMagnitude = Mathf.Abs(valueAxis.y);
            if (valueMagnitude <= SelectionReleaseThreshold)
            {
                audioParameterValueAxisEngaged = false;
            }
            else if (!audioParameterValueAxisEngaged &&
                     valueMagnitude >= SelectionThreshold)
            {
                audioParameterValueAxisEngaged = true;
                var direction = valueAxis.y < 0f ? -1 : 1;
                var descriptors = AdjustableParameterPolicy.Descriptors(kind);
                if (audioParameterEntryIndex < descriptors.Count)
                {
                    placement.Record.parameterSettings =
                        AdjustableParameterPolicy.NormalizeSettings(
                            kind,
                            placement.Record.parameterSettings,
                            placement.Record.normalizedValue);
                    var setting = placement.Record.parameterSettings[
                        audioParameterEntryIndex];
                    var descriptor = descriptors[audioParameterEntryIndex];
                    var editsSequenceValue = descriptor.Id ==
                                             AdjustableParameterPolicy
                                                 .SequencerStepValueId;
                    if (editsSequenceValue &&
                        audioParameterSettingField ==
                        AdjustableParameterField.Value)
                    {
                        EnsureSequencerParameterArray(placement.Record);
                        setting.value = placement.Record.audioSequencerSteps[
                            audioParameterStepIndex];
                    }
                    AdjustableParameterPolicy.Adjust(
                        setting,
                        descriptor,
                        audioParameterSettingField,
                        direction);
                    if (editsSequenceValue)
                    {
                        if (audioParameterSettingField ==
                            AdjustableParameterField.Value)
                        {
                            placement.Record.audioSequencerSteps[
                                audioParameterStepIndex] = setting.value;
                        }
                        else
                        {
                            placement.Record.audioSequencerSteps =
                                ModularAudioParameterPolicy
                                    .NormalizeSequencerSteps(
                                        placement.Record.audioSequencerSteps,
                                        setting);
                        }
                    }
                }
                else
                {
                    AdjustSpecialAudioParameter(
                        placement,
                        kind,
                        direction);
                }
                ApplyAudioParameters(placement);
                PulseHaptics();
            }

            if (confirmPressed)
            {
                ConfirmAudioParameterEdit();
                return;
            }
            if (cancelPressed)
            {
                CancelAudioParameterEdit(true);
                SetConnectNotice("MODULE EDIT CANCELLED", Color.yellow);
                return;
            }
            UpdateAudioParameterEditStatus();
        }

        private void ConfirmAudioParameterEdit()
        {
            var placement = audioParameterEditPlacement;
            if (placement?.Record == null || audioParameterOriginal == null)
            {
                CancelAudioParameterEdit(true);
                return;
            }
            if (!SavePlacementDocument())
            {
                CopyAudioParameterState(
                    audioParameterOriginal,
                    placement.Record);
                ApplyAudioParameters(placement);
                ClearAudioParameterEditState();
                SetConnectNotice("MODULE PARAMETER SAVE FAILED", Color.red);
                return;
            }

            var kind = GetPlacementKind(placement);
            ClearAudioParameterEditState();
            SetConnectNotice(
                $"{MockInstrumentCatalog.GetDisplayName(kind)} " +
                "PARAMETERS APPLIED\nY: EDIT AGAIN",
                ModuleSourceColor(kind));
            PulseHaptics();
        }

        private void CancelAudioParameterEdit(bool restore)
        {
            var placement = audioParameterEditPlacement;
            if (restore && placement?.Record != null &&
                audioParameterOriginal != null)
            {
                CopyAudioParameterState(
                    audioParameterOriginal,
                    placement.Record);
                ApplyAudioParameters(placement);
            }
            ClearAudioParameterEditState();
        }

        private void ClearAudioParameterEditState()
        {
            audioParameterEditPlacement = null;
            audioParameterOriginal = null;
            audioParameterEntryIndex = 0;
            audioParameterStepIndex = 0;
            audioParameterSettingField = AdjustableParameterField.Value;
            audioParameterFieldAxisEngaged = false;
            audioParameterValueAxisEngaged = false;
            connectStatusHoldUntil = 0f;
        }

        private void UpdateAudioParameterEditStatus()
        {
            var placement = audioParameterEditPlacement;
            if (placement?.Record == null)
                return;
            var kind = GetPlacementKind(placement);
            placement.Record.parameterSettings =
                AdjustableParameterPolicy.NormalizeSettings(
                    kind,
                    placement.Record.parameterSettings,
                    placement.Record.normalizedValue);
            var descriptors = AdjustableParameterPolicy.Descriptors(kind);
            var entryCount = descriptors.Count +
                             SpecialParameterEntryCount(kind);
            audioParameterEntryIndex = Mathf.Clamp(
                audioParameterEntryIndex,
                0,
                Mathf.Max(0, entryCount - 1));
            string parameter;
            if (audioParameterEntryIndex < descriptors.Count)
            {
                var descriptor = descriptors[audioParameterEntryIndex];
                var setting = placement.Record.parameterSettings[
                    audioParameterEntryIndex];
                if (descriptor.Id ==
                    AdjustableParameterPolicy.SequencerPlaybackModeId)
                {
                    audioParameterSettingField =
                        AdjustableParameterField.Value;
                }
                if (descriptor.Id ==
                    AdjustableParameterPolicy.SequencerStepValueId)
                {
                    EnsureSequencerParameterArray(placement.Record);
                    setting.value = placement.Record.audioSequencerSteps[
                        audioParameterStepIndex];
                }
                var selectedValue = audioParameterSettingField switch
                {
                    AdjustableParameterField.Minimum => setting.minimum,
                    AdjustableParameterField.Maximum => setting.maximum,
                    AdjustableParameterField.StepCount => setting.stepCount,
                    _ => setting.value
                };
                var formatted = descriptor.Id ==
                                AdjustableParameterPolicy
                                    .SequencerPlaybackModeId
                    ? setting.value >= 0.5f
                        ? "STEP TRIGGER"
                        : "CLOCK"
                    : audioParameterSettingField ==
                      AdjustableParameterField.StepCount
                    ? !descriptor.StepCountEditable
                        ? $"FIXED {setting.stepCount}"
                        : setting.stepCount == 0
                            ? "CONTINUOUS"
                            : setting.stepCount.ToString()
                    : FormatParameterValue(selectedValue, descriptor.Unit);
                parameter = descriptor.Id ==
                            AdjustableParameterPolicy.SequencerPlaybackModeId
                    ? $"{descriptor.Label} " +
                      $"[{audioParameterEntryIndex + 1}/{entryCount}]\n" +
                      $"> VALUE: {formatted}\n" +
                      "CLOCK: INTERNAL/EXTERNAL CLOCK | " +
                      "STEP TRIGGER: 0->1 ADVANCES"
                    : $"{descriptor.Label} " +
                      $"[{audioParameterEntryIndex + 1}/{entryCount}]\n" +
                      $"> {audioParameterSettingField.ToString().ToUpperInvariant()}: {formatted}\n" +
                      $"RANGE {FormatParameterValue(setting.minimum, descriptor.Unit)} .. " +
                      $"{FormatParameterValue(setting.maximum, descriptor.Unit)} | " +
                      $"STEPS {(!descriptor.StepCountEditable ? $"FIXED {setting.stepCount}" : setting.stepCount == 0 ? "CONT" : setting.stepCount.ToString())}";
            }
            else
            {
                switch (kind)
                {
                    case MockInstrumentKind.AudioOscillator:
                    case MockInstrumentKind.AudioLfo:
                        parameter =
                            $"WAVEFORM [{entryCount}/{entryCount}]: " +
                            $"{((ModularOscillatorWaveform)ModularAudioParameterPolicy.NormalizeWaveform(placement.Record.audioWaveform)).ToString().ToUpperInvariant()}";
                        break;
                    case MockInstrumentKind.AudioNoise:
                        parameter =
                            $"COLOR [{entryCount}/{entryCount}]: " +
                            $"{((ModularNoiseColor)ModularAudioParameterPolicy.NormalizeNoiseColor(placement.Record.audioNoiseColor)).ToString().ToUpperInvariant()}";
                        break;
                    case MockInstrumentKind.AudioSequencer:
                        EnsureSequencerParameterArray(placement.Record);
                        var sequencer = placement.AudioModule?.Node as
                            ModularSequencerNode;
                        var stepCount = sequencer?.StepCount ?? 8;
                        audioParameterStepIndex = Mathf.Clamp(
                            audioParameterStepIndex,
                            0,
                            stepCount - 1);
                        var stepValue = placement.Record.audioSequencerSteps[
                            audioParameterStepIndex];
                        parameter =
                            $"SEQUENCE [{entryCount}/{entryCount}] | " +
                            $"STEP {audioParameterStepIndex + 1}/{stepCount}: " +
                            $"{stepValue:+0.00;-0.00;0.00}";
                        break;
                    default:
                        parameter = "NO EDITABLE PARAMETER";
                        break;
                }
            }
            SetStatus(
                $"PARAMETER EDIT: {MockInstrumentCatalog.GetDisplayName(kind)}\n" +
                parameter +
                "\nL STICK L/R: PARAM | U/D: FIELD/STEP" +
                "\nR STICK U/D: ADJUST | A: APPLY | B: CANCEL",
                ModuleSourceColor(kind));
        }

        private static int SpecialParameterEntryCount(
            MockInstrumentKind kind)
        {
            return kind == MockInstrumentKind.AudioOscillator ||
                   kind == MockInstrumentKind.AudioNoise ||
                   kind == MockInstrumentKind.AudioLfo ||
                   kind == MockInstrumentKind.AudioSequencer
                ? 1
                : 0;
        }

        private void AdjustSpecialAudioParameter(
            RuntimePlacement placement,
            MockInstrumentKind kind,
            int direction)
        {
            switch (kind)
            {
                case MockInstrumentKind.AudioOscillator:
                case MockInstrumentKind.AudioLfo:
                    placement.Record.audioWaveform =
                        ModularAudioParameterPolicy.CycleWaveform(
                            placement.Record.audioWaveform,
                            direction);
                    break;
                case MockInstrumentKind.AudioNoise:
                    placement.Record.audioNoiseColor =
                        ModularAudioParameterPolicy.CycleNoiseColor(
                            placement.Record.audioNoiseColor,
                            direction);
                    break;
                case MockInstrumentKind.AudioSequencer:
                    EnsureSequencerParameterArray(placement.Record);
                    var stepRange = AdjustableParameterPolicy.Find(
                        placement.Record.parameterSettings,
                        AdjustableParameterPolicy.SequencerStepValueId);
                    if (stepRange == null)
                    {
                        placement.Record.audioSequencerSteps[
                            audioParameterStepIndex] =
                            ModularAudioParameterPolicy.AdjustStepValue(
                                placement.Record.audioSequencerSteps[
                                    audioParameterStepIndex],
                                direction);
                        break;
                    }
                    stepRange.value = placement.Record.audioSequencerSteps[
                        audioParameterStepIndex];
                    var stepDescriptor = AdjustableParameterPolicy.Descriptors(
                        kind)[2];
                    AdjustableParameterPolicy.Adjust(
                        stepRange,
                        stepDescriptor,
                        AdjustableParameterField.Value,
                        direction);
                    placement.Record.audioSequencerSteps[
                        audioParameterStepIndex] = stepRange.value;
                    break;
            }
        }

        private static string FormatParameterValue(
            float value,
            string unit)
        {
            var format = Mathf.Abs(value) >= 100f
                ? "0"
                : Mathf.Abs(value) >= 10f
                    ? "0.0"
                    : "0.000";
            return string.IsNullOrEmpty(unit)
                ? value.ToString(format)
                : $"{value.ToString(format)} {unit}";
        }

        private static void EnsureSequencerParameterArray(
            PlacementRecord record)
        {
            if (record == null ||
                record.audioSequencerSteps?.Length ==
                ModularAudioParameterPolicy.SequencerStepCapacity)
            {
                return;
            }
            record.audioSequencerSteps =
                ModularAudioParameterPolicy.NormalizeSequencerSteps(
                    record.audioSequencerSteps,
                    AdjustableParameterPolicy.Find(
                        record.parameterSettings,
                        AdjustableParameterPolicy.SequencerStepValueId));
        }

        private static void CopyAudioParameterState(
            PlacementRecord source,
            PlacementRecord destination)
        {
            destination.audioWaveform = source.audioWaveform;
            destination.audioNoiseColor = source.audioNoiseColor;
            destination.audioSequencerSteps =
                source.audioSequencerSteps != null
                    ? (float[])source.audioSequencerSteps.Clone()
                    : ModularAudioParameterPolicy
                        .CreateDefaultSequencerSteps();
            destination.parameterSettings = source.parameterSettings != null
                ? source.parameterSettings.ConvertAll(
                    setting => setting?.Clone())
                : new List<AdjustableParameterSetting>();
        }

        private static void ApplyAudioParameters(RuntimePlacement placement)
        {
            if (placement?.Record == null)
                return;
            var kind = GetPlacementKind(placement);
            placement.Record.parameterSettings =
                AdjustableParameterPolicy.NormalizeSettings(
                    kind,
                    placement.Record.parameterSettings,
                    placement.Record.normalizedValue);
            var descriptors = AdjustableParameterPolicy.Descriptors(kind);
            if (descriptors.Count > 0 && placement.Interaction != null)
            {
                var primary = placement.Record.parameterSettings[0];
                placement.Interaction.ConfigureParameterRange(primary);
                if (MockInstrumentCatalog.GetCategory(kind) !=
                    MockInstrumentCategory.AudioModules)
                {
                    placement.Interaction.SetOutputValue(
                        primary.value,
                        InstrumentValueChangeOrigin.Restore);
                    placement.Record.normalizedValue =
                        placement.Interaction.NormalizedValue;
                }
            }
            if (placement.AudioModule == null)
                return;
            placement.AudioModule.ApplyPersistentParameters(
                placement.Record.audioWaveform,
                placement.Record.audioNoiseColor,
                placement.Record.audioSequencerSteps,
                placement.Record.parameterSettings);
        }

        private bool UpdateConnectTrigger(
            ref bool engaged,
            float triggerValue,
            Transform aimAnchor)
        {
            if (engaged)
            {
                if (triggerValue <= TriggerReleaseThreshold)
                    engaged = false;
                return false;
            }

            if (triggerValue < TriggerPressThreshold)
                return false;

            engaged = true;
            SelectConnectEndpoint(aimAnchor);
            return true;
        }

        private void SelectConnectEndpoint(Transform aimAnchor)
        {
            if (!TryResolveConnectionPlacement(
                    aimAnchor,
                    out var placement))
            {
                SetConnectNotice(
                    "CONNECT: AIM AT AN INSTRUMENT",
                    Color.yellow);
                return;
            }

            var kind = GetPlacementKind(placement);
            if (connectSource == null && connectTarget == null &&
                ReferenceEquals(connectEditPlacement, placement) &&
                ModularAudioPatchPolicy.SupportsSignalRole(kind))
            {
                SelectConnectSource(placement, false, true);
                return;
            }
            if (connectSource == null && connectTarget != null)
            {
                var targetKind = GetPlacementKind(connectTarget);
                if (ReferenceEquals(connectTarget, placement))
                {
                    if (ModularAudioPatchPolicy.SupportsSignalRole(kind))
                    {
                        SelectConnectSource(placement, false, true);
                        return;
                    }
                    SetConnectNotice(
                        "SOURCE AND TARGET MUST DIFFER",
                        Color.yellow);
                    return;
                }
                var canConnectAsAudio =
                    ModularAudioPatchPolicy.TryGetRoute(
                        kind,
                        targetKind,
                        ModularAudioPortDomain.Control,
                        out _,
                        out _,
                        out _);
                var canConnectAsSignal =
                    InstrumentSignalPolicy.CanConnect(kind, targetKind);
                if (!canConnectAsAudio && !canConnectAsSignal)
                {
                    SetConnectNotice(
                        $"{MockInstrumentCatalog.GetDisplayName(kind)} " +
                        "HAS NO OBSERVABLE OUTPUT",
                        Color.yellow);
                    return;
                }

                SelectConnectSource(
                    placement,
                    true,
                    !canConnectAsSignal && canConnectAsAudio);
                return;
            }

            if (connectSource == null)
            {
                if (kind == MockInstrumentKind.TrendMonitor ||
                    kind == MockInstrumentKind.WindowPanel ||
                    ModularAudioPatchPolicy.PrefersTargetWhenUnconnected(kind))
                {
                    ClearConnectEditSelection();
                    connectTarget = placement;
                    connectTargetMarker = CreateConnectMarker(
                        placement,
                        "[Connect] Target",
                        ConnectTargetColor,
                        0.012f);
                    connectStatusHoldUntil = 0f;
                    PulseHaptics();
                    UpdateConnectStatus();
                    return;
                }
                if (ModularAudioPatchPolicy.SupportsSignalRole(kind) &&
                    InstrumentSignalPolicy.CanTarget(kind))
                {
                    SelectConnectEditPlacement(placement);
                    return;
                }
                if (!InstrumentSignalPolicy.CanSource(kind) &&
                    !ModularAudioPatchPolicy.CanSource(kind))
                {
                    if (InstrumentSignalPolicy.CanTarget(kind))
                    {
                        SelectConnectEditPlacement(placement);
                    }
                    else
                    {
                        SetConnectNotice(
                            $"{MockInstrumentCatalog.GetDisplayName(kind)} " +
                            "HAS NO CONNECT PORT",
                            Color.yellow);
                    }
                    return;
                }

                SelectConnectSource(placement, false, false);
                return;
            }

            var sourceKind = GetPlacementKind(connectSource);
            if (ReferenceEquals(connectSource, placement))
            {
                if (ModularAudioPatchPolicy.SupportsSignalRole(sourceKind))
                {
                    ToggleObservableSourceRole(sourceKind);
                    return;
                }
                SetConnectNotice(
                    "SOURCE AND TARGET MUST DIFFER",
                    Color.yellow);
                return;
            }
            var canConnect = TryGetPendingModularRoute(
                                 sourceKind,
                                 kind,
                                 out _,
                                 out _,
                                 out _) ||
                             InstrumentSignalPolicy.CanConnect(
                                 sourceKind,
                                 kind);
            if (!canConnect)
            {
                SetConnectNotice(
                    $"{MockInstrumentCatalog.GetDisplayName(kind)} " +
                    "CANNOT ACCEPT THIS OUTPUT",
                    Color.yellow);
                return;
            }
            selectedConnectionForRemoval = null;
            selectedAudioPatchForRemoval = null;
            connectTarget = placement;
            if (connectTargetMarker != null)
                Destroy(connectTargetMarker);
            connectTargetMarker = CreateConnectMarker(
                placement,
                "[Connect] Target",
                ConnectTargetColor,
                0.012f);
            connectStatusHoldUntil = 0f;
            PulseHaptics();
            UpdateConnectStatus();
        }

        private void SelectConnectSource(
            RuntimePlacement placement,
            bool preserveTarget,
            bool observableAudioSource)
        {
            if (placement == null)
                return;
            if (connectSourceMarker != null)
                Destroy(connectSourceMarker);
            connectSourceMarker = null;
            connectSource = null;
            if (!preserveTarget)
            {
                if (connectTargetMarker != null)
                    Destroy(connectTargetMarker);
                connectTargetMarker = null;
                connectTarget = null;
            }
            ClearConnectEditSelection();
            selectedConnectionForRemoval = null;
            selectedAudioPatchForRemoval = null;
            pendingObservableAudioSource = observableAudioSource;
            pendingObservableOutputIndex = observableAudioSource
                ? connectTarget != null
                    ? ModularAudioPatchPolicy.GetDefaultPatchOutputIndex(
                        GetPlacementKind(placement),
                        GetPlacementKind(connectTarget))
                    : ModularAudioPatchPolicy.GetDefaultPatchOutputIndex(
                        GetPlacementKind(placement))
                : 0;
            connectSource = placement;
            connectSourceMarker = CreateConnectMarker(
                placement,
                "[Connect] Source",
                ConnectSourceColor,
                0.014f);
            connectStatusHoldUntil = 0f;
            PulseHaptics();
            UpdateConnectStatus();
        }

        private void ToggleObservableSourceRole(MockInstrumentKind sourceKind)
        {
            pendingObservableAudioSource = !pendingObservableAudioSource;
            pendingObservableOutputIndex = pendingObservableAudioSource
                ? connectTarget != null
                    ? ModularAudioPatchPolicy.GetDefaultPatchOutputIndex(
                        sourceKind,
                        GetPlacementKind(connectTarget))
                    : ModularAudioPatchPolicy.GetDefaultPatchOutputIndex(
                        sourceKind)
                : 0;
            selectedConnectionForRemoval = null;
            selectedAudioPatchForRemoval = null;
            connectStatusHoldUntil = 0f;
            PulseHaptics();
            UpdateConnectStatus();
        }

        private void SelectConnectEditPlacement(RuntimePlacement placement)
        {
            if (placement == null)
                return;

            if (connectSourceMarker != null)
                Destroy(connectSourceMarker);
            if (connectTargetMarker != null)
                Destroy(connectTargetMarker);
            connectSourceMarker = null;
            connectTargetMarker = null;
            connectSource = null;
            connectTarget = null;
            selectedAudioPatchForRemoval = null;
            ClearConnectEditSelection();

            connectEditPlacement = placement;
            connectEditMarker = CreateConnectMarker(
                placement,
                "[Connect] Edit Object",
                ConnectionEditObjectColor,
                0.014f);
            connectStatusHoldUntil = 0f;
            PulseHaptics();
            UpdateConnectStatus();
        }

        private bool TryResolveConnectionPlacement(
            Transform aimAnchor,
            out RuntimePlacement placement)
        {
            placement = null;
            return TryResolveOperationInteraction(
                aimAnchor,
                OperationResolveMode.Any,
                out _,
                out placement,
                out _);
        }

        private void ConfirmPendingConnection()
        {
            if (connectSource == null || connectTarget == null)
            {
                SetConnectNotice(
                    connectSource == null
                        ? "SELECT AN INPUT SOURCE FIRST"
                        : "SELECT A TARGET",
                    Color.yellow);
                return;
            }
            var pendingSourceKind = GetPlacementKind(connectSource);
            var pendingTargetKind = GetPlacementKind(connectTarget);
            if (TryGetPendingModularRoute(
                    pendingSourceKind,
                    pendingTargetKind,
                    out _,
                    out _,
                    out _))
            {
                ConfirmPendingAudioPatchConnection();
                return;
            }
            if (placementDocument?.connections == null)
                return;

            SignalConnectionRecord existing = null;
            foreach (var connection in placementDocument.connections)
            {
                if (connection.sourcePlacementId ==
                        connectSource.Record.placementId &&
                    connection.targetPlacementId ==
                        connectTarget.Record.placementId)
                {
                    existing = connection;
                    break;
                }
            }

            var added = false;
            var previousTransform = 0;
            if (existing != null)
            {
                previousTransform = existing.transformKind;
                existing.transformKind = (int)pendingSignalTransform;
            }
            else
            {
                var targetKind = GetPlacementKind(connectTarget);
                if (targetKind == MockInstrumentKind.TrendMonitor &&
                    CountIncomingConnections(
                        connectTarget.Record.placementId) >=
                        InstrumentSignalPolicy.MaximumTrendMonitorInputs)
                {
                    SetConnectNotice(
                        $"TREND MONITOR INPUT LIMIT " +
                        $"{InstrumentSignalPolicy.MaximumTrendMonitorInputs}",
                        Color.yellow);
                    return;
                }
                var targetInputSlot =
                    SignalConnectionRecord.AutomaticTargetInputSlot;
                if (targetKind == MockInstrumentKind.WindowPanel &&
                    !WindowPanelInputSlotPolicy.TryFindLowestAvailable(
                        placementDocument.connections,
                        connectTarget.Record.placementId,
                        out targetInputSlot))
                {
                    SetConnectNotice(
                        $"WINDOW PANEL INPUT LIMIT " +
                        $"{InstrumentSignalPolicy.MaximumWindowPanelInputs}",
                        Color.yellow);
                    return;
                }
                if (placementDocument.connections.Count >=
                    PlacementDocument.MaximumConnections)
                {
                    SetConnectNotice(
                        $"CONNECTION LIMIT " +
                        $"{PlacementDocument.MaximumConnections}",
                        Color.yellow);
                    return;
                }

                existing = new SignalConnectionRecord
                {
                    connectionId = Guid.NewGuid().ToString("D"),
                    sourcePlacementId =
                        connectSource.Record.placementId,
                    targetPlacementId =
                        connectTarget.Record.placementId,
                    transformKind = (int)pendingSignalTransform,
                    targetInputSlot = targetInputSlot
                };
                placementDocument.connections.Add(existing);
                added = true;
            }

            if (!SavePlacementDocument())
            {
                if (added)
                    placementDocument.connections.Remove(existing);
                else
                    existing.transformKind = previousTransform;
                SetConnectNotice("CONNECTION SAVE FAILED", Color.red);
                return;
            }

            var sourceName = MockInstrumentCatalog.GetDisplayName(
                GetPlacementKind(connectSource));
            var targetName = MockInstrumentCatalog.GetDisplayName(
                GetPlacementKind(connectTarget));
            var confirmedTransform = pendingSignalTransform;
            ClearConnectSelection();
            SetConnectNotice(
                $"{sourceName} -> {targetName}\n" +
                $"{confirmedTransform.ToString().ToUpperInvariant()} | " +
                $"{placementDocument.connections.Count}/" +
                $"{PlacementDocument.MaximumConnections} CONNECTED",
                ConnectionColor(confirmedTransform));
            PulseHaptics();
        }

        private void ConfirmPendingAudioPatchConnection()
        {
            if (placementDocument?.audioPatchConnections == null ||
                connectSource?.Record == null ||
                connectTarget?.Record == null)
                return;
            var sourceId = connectSource.Record.placementId;
            var targetId = connectTarget.Record.placementId;
            if (!TryGetPendingModularRoute(
                    GetPlacementKind(connectSource),
                    GetPlacementKind(connectTarget),
                    out var sourcePortId,
                    out var targetPortId,
                    out var domain))
            {
                SetConnectNotice("NO COMPATIBLE MODULE PORT", Color.yellow);
                return;
            }
            AudioPatchConnectionRecord existingPatch = null;
            foreach (var candidatePatch in
                     placementDocument.audioPatchConnections)
            {
                if (candidatePatch?.sourcePlacementId == sourceId)
                {
                    existingPatch = candidatePatch;
                    break;
                }
            }
            if (existingPatch == null &&
                placementDocument.audioPatchConnections.Count >=
                PlacementDocument.MaximumAudioPatchConnections)
            {
                SetConnectNotice(
                    $"AUDIO PATCH LIMIT " +
                    $"{PlacementDocument.MaximumAudioPatchConnections}",
                    Color.yellow);
                return;
            }

            var added = existingPatch == null;
            var previousTargetId = existingPatch?.targetPlacementId;
            var previousSourcePortId = existingPatch?.sourcePortId;
            var previousTargetPortId = existingPatch?.targetPortId;
            var previousDomain = existingPatch?.portDomain ?? 0;
            var newConnection = existingPatch ?? new AudioPatchConnectionRecord
            {
                connectionId = Guid.NewGuid().ToString("D"),
                sourcePlacementId = sourceId
            };
            newConnection.targetPlacementId = targetId;
            newConnection.sourcePortId = sourcePortId;
            newConnection.targetPortId = targetPortId;
            newConnection.portDomain = (int)domain;
            if (added)
                placementDocument.audioPatchConnections.Add(newConnection);
            if (!SavePlacementDocument())
            {
                if (added)
                    placementDocument.audioPatchConnections.Remove(newConnection);
                else
                {
                    newConnection.targetPlacementId = previousTargetId;
                    newConnection.sourcePortId = previousSourcePortId;
                    newConnection.targetPortId = previousTargetPortId;
                    newConnection.portDomain = previousDomain;
                }
                SetConnectNotice("AUDIO PATCH SAVE FAILED", Color.red);
                return;
            }

            var sourceName = MockInstrumentCatalog.GetDisplayName(
                GetPlacementKind(connectSource));
            var targetName = MockInstrumentCatalog.GetDisplayName(
                GetPlacementKind(connectTarget));
            ClearConnectSelection();
            SetConnectNotice(
                $"{sourceName} -> {targetName}\n" +
                $"{domain.ToString().ToUpperInvariant()} | " +
                $"{placementDocument.audioPatchConnections.Count}/" +
                $"{PlacementDocument.MaximumAudioPatchConnections} PATCHED",
                PatchColor(domain));
            PulseHaptics();
        }

        private void SelectNextConnectionForRemoval()
        {
            var selectedPlacement =
                connectEditPlacement ?? connectSource ?? connectTarget;
            if (selectedPlacement?.Record == null)
            {
                SetConnectNotice(
                    "SELECT ONE OBJECT + TRIGGER",
                    Color.yellow);
                return;
            }

            var placementId = selectedPlacement.Record.placementId;
            if (!MixedConnectionSelectionPolicy.TrySelectNext(
                placementDocument?.connections,
                placementDocument?.audioPatchConnections,
                placementId,
                selectedConnectionForRemoval?.connectionId,
                selectedAudioPatchForRemoval?.connectionId,
                out var nextSignal,
                out var nextAudioPatch))
            {
                selectedConnectionForRemoval = null;
                selectedAudioPatchForRemoval = null;
                SetConnectNotice(
                    "SELECTED OBJECT HAS NO CONNECTION",
                    Color.yellow);
                return;
            }

            selectedConnectionForRemoval = nextSignal;
            selectedAudioPatchForRemoval = nextAudioPatch;
            if (nextSignal != null)
            {
                selectedConnectionPendingTransform =
                    (SignalTransformKind)nextSignal.transformKind;
                selectedConnectionPendingSlot = nextSignal.targetInputSlot;
                selectedConnectionPendingPriority =
                    nextSignal.compositionPriority;
            }
            connectStatusHoldUntil = 0f;
            PulseHaptics();
            UpdateConnectStatus();
        }

        private void DeleteSelectedConnection()
        {
            if (selectedAudioPatchForRemoval != null)
            {
                DeleteSelectedAudioPatch();
                return;
            }
            if (selectedConnectionForRemoval == null ||
                placementDocument?.connections == null)
            {
                SetConnectNotice(
                    "A: SELECT CONNECTION TO DELETE",
                    Color.yellow);
                return;
            }

            var selected = selectedConnectionForRemoval;
            var originalIndex =
                placementDocument.connections.IndexOf(selected);
            if (originalIndex < 0)
            {
                selectedConnectionForRemoval = null;
                UpdateConnectStatus();
                return;
            }

            placementDocument.connections.RemoveAt(originalIndex);
            if (!SavePlacementDocument())
            {
                placementDocument.connections.Insert(
                    Mathf.Clamp(
                        originalIndex,
                        0,
                        placementDocument.connections.Count),
                    selected);
                SetConnectNotice(
                    "CONNECTION REMOVE FAILED",
                    Color.red);
                return;
            }
            selectedConnectionForRemoval = null;
            selectedConnectionPendingTransform =
                SignalTransformKind.Direct;
            selectedConnectionPendingSlot =
                SignalConnectionRecord.AutomaticTargetInputSlot;
            selectedConnectionPendingPriority =
                SignalConnectionRecord.DefaultCompositionPriority;
            SetConnectNotice(
                $"CONNECTION REMOVED | " +
                $"{placementDocument.connections.Count}/" +
                $"{PlacementDocument.MaximumConnections}\n" +
                "A: SELECT NEXT CONNECTION",
                Color.green);
            PulseHaptics();
        }

        private void DeleteSelectedAudioPatch()
        {
            var patches = placementDocument?.audioPatchConnections;
            if (patches == null || selectedAudioPatchForRemoval == null)
                return;
            var selected = selectedAudioPatchForRemoval;
            var originalIndex = patches.IndexOf(selected);
            if (originalIndex < 0)
            {
                selectedAudioPatchForRemoval = null;
                return;
            }
            patches.RemoveAt(originalIndex);
            if (!SavePlacementDocument())
            {
                patches.Insert(
                    Mathf.Clamp(originalIndex, 0, patches.Count),
                    selected);
                SetConnectNotice("AUDIO PATCH REMOVE FAILED", Color.red);
                return;
            }
            selectedAudioPatchForRemoval = null;
            SetConnectNotice(
                $"AUDIO PATCH REMOVED | {patches.Count}/" +
                $"{PlacementDocument.MaximumAudioPatchConnections}\n" +
                "A: SELECT NEXT PATCH",
                Color.green);
            PulseHaptics();
        }

        private void ConfirmSelectedConnectionTransform()
        {
            if (selectedConnectionForRemoval == null ||
                placementDocument?.connections == null ||
                !placementDocument.connections.Contains(
                    selectedConnectionForRemoval))
            {
                selectedConnectionForRemoval = null;
                SetConnectNotice(
                    "A: SELECT CONNECTION TO EDIT",
                    Color.yellow);
                return;
            }

            var connection = selectedConnectionForRemoval;
            var previousTransform = connection.transformKind;
            var previousSlot = connection.targetInputSlot;
            var previousPriority = connection.compositionPriority;
            connection.transformKind =
                (int)selectedConnectionPendingTransform;
            connection.targetInputSlot = selectedConnectionPendingSlot;
            connection.compositionPriority =
                selectedConnectionPendingPriority;
            if (!SavePlacementDocument())
            {
                connection.transformKind = previousTransform;
                connection.targetInputSlot = previousSlot;
                connection.compositionPriority = previousPriority;
                SetConnectNotice(
                    "CONNECTION UPDATE FAILED",
                    Color.red);
                return;
            }

            var confirmedTransform =
                selectedConnectionPendingTransform;
            selectedConnectionForRemoval = null;
            selectedConnectionPendingTransform =
                SignalTransformKind.Direct;
            selectedConnectionPendingSlot =
                SignalConnectionRecord.AutomaticTargetInputSlot;
            selectedConnectionPendingPriority =
                SignalConnectionRecord.DefaultCompositionPriority;
            connectStatusHoldUntil = 0f;
            SetConnectNotice(
                $"{confirmedTransform.ToString().ToUpperInvariant()} APPLIED\n" +
                "OBJECT REMAINS SELECTED | A: NEXT CONNECTION",
                ConnectionColor(confirmedTransform));
            PulseHaptics();
        }

        private void UpdateConnectStatus()
        {
            if (!AppInteractionModePolicy.AllowsConnecting(
                    interactionMode,
                    connectionEditing))
                return;
            if (Time.unscaledTime < connectStatusHoldUntil)
                return;

            var transformLabel =
                pendingSignalTransform.ToString().ToUpperInvariant();
            var editPlacement =
                connectEditPlacement ?? connectSource ?? connectTarget;
            if (selectedAudioPatchForRemoval != null &&
                editPlacement?.Record != null)
            {
                var patch = selectedAudioPatchForRemoval;
                var source = FindPlacementById(patch.sourcePlacementId);
                var target = FindPlacementById(patch.targetPlacementId);
                var audioSourceName = source == null
                    ? "UNKNOWN"
                    : MockInstrumentCatalog.GetDisplayName(
                        GetPlacementKind(source));
                var audioTargetName = target == null
                    ? "UNKNOWN"
                    : MockInstrumentCatalog.GetDisplayName(
                        GetPlacementKind(target));
                SetStatus(
                    $"{((ModularAudioPortDomain)patch.portDomain).ToString().ToUpperInvariant()} PATCH | " +
                    $"{audioSourceName} -> {audioTargetName}\n" +
                    $"{patch.sourcePortId} -> {patch.targetPortId}\n" +
                    "A: NEXT CONNECTION | B: DELETE",
                    SelectedAudioPatchColor);
                return;
            }
            if (connectionParameterDraft != null &&
                selectedConnectionForRemoval != null)
            {
                var transform = (SignalTransformKind)
                    connectionParameterDraft.transformKind;
                var source = FindPlacementById(
                    selectedConnectionForRemoval.sourcePlacementId);
                var input = source?.Interaction == null
                    ? 0f
                    : source.Interaction.OutputValue;
                var output = InstrumentSignalPolicy.Transform(
                    input,
                    connectionParameterDraft);
                SetStatus(
                    $"{transform.ToString().ToUpperInvariant()} PARAM | " +
                    $"{SignalConnectionParameterEditor.Label(connectionParameterField)} " +
                    $"{SignalConnectionParameterEditor.Value(connectionParameterDraft, connectionParameterField)}\n" +
                    $"PREVIEW {input:0.00} -> {output:0.00} | " +
                    "L STICK L/R: ADJUST\n" +
                    "R STICK U/D: FIELD | L STICK PRESS: APPLY\n" +
                    "Y / B: CANCEL",
                    ConnectionColor(transform));
                return;
            }
            if (selectedConnectionForRemoval != null &&
                editPlacement?.Record != null)
            {
                var connection = selectedConnectionForRemoval;
                var source = FindPlacementById(
                    connection.sourcePlacementId);
                var target = FindPlacementById(
                    connection.targetPlacementId);
                var selectedSourceName = source == null
                    ? "UNKNOWN"
                    : MockInstrumentCatalog.GetDisplayName(
                        GetPlacementKind(source));
                var selectedTargetName = target == null
                    ? "UNKNOWN"
                    : MockInstrumentCatalog.GetDisplayName(
                        GetPlacementKind(target));
                var selectedTransformLabel =
                    selectedConnectionPendingTransform
                    .ToString()
                    .ToUpperInvariant();
                var direction =
                    connection.sourcePlacementId ==
                    editPlacement.Record.placementId
                        ? "OUTPUT"
                        : "INPUT";
                var editsWindowPanelInput = target != null &&
                                            GetPlacementKind(target) ==
                                            MockInstrumentKind.WindowPanel;
                var editsPriorityInput = target?.Record != null &&
                    SignalCompositionEditor.NormalizeKind(
                        target.Record.signalCompositionKind) ==
                    SignalCompositionKind.Priority;
                var selectedIndex = 0;
                var selectedCount = 0;
                foreach (var candidate in placementDocument.connections)
                {
                    if (!SignalConnectionSelectionPolicy.TouchesPlacement(
                            candidate,
                            editPlacement.Record.placementId))
                    {
                        continue;
                    }
                    selectedCount++;
                    if (candidate.connectionId ==
                        connection.connectionId)
                    {
                        selectedIndex = selectedCount;
                    }
                }
                SetStatus(
                    $"{direction} {selectedIndex}/{selectedCount} | " +
                    $"{selectedSourceName} -> {selectedTargetName}\n" +
                    $"{selectedTransformLabel}" +
                    (editsWindowPanelInput
                        ? $" | SLOT {SlotLabel(selectedConnectionPendingSlot)}"
                        : editsPriorityInput
                            ? $" | PRIORITY {selectedConnectionPendingPriority}"
                        : string.Empty) +
                    " | L STICK L/R: CHANGE\n" +
                    (editsWindowPanelInput
                        ? "R STICK L/R: SLOT | "
                        : editsPriorityInput
                            ? "R STICK L/R: PRIORITY | "
                        : string.Empty) +
                    (SignalConnectionParameterEditor.Supports(
                            selectedConnectionPendingTransform)
                        ? "Y: PARAMETERS | "
                        : string.Empty) +
                    "L STICK PRESS: APPLY | A: NEXT | B: DELETE",
                    SelectedConnectionColorFor(
                        selectedConnectionPendingTransform));
                return;
            }

            if (connectEditPlacement != null)
            {
                var connectionCount = CountConnections(
                    connectEditPlacement.Record?.placementId);
                var patchCount = CountAudioPatches(
                    connectEditPlacement.Record?.placementId);
                var editName = MockInstrumentCatalog.GetDisplayName(
                    GetPlacementKind(connectEditPlacement));
                var editsWindowPanel =
                    GetPlacementKind(connectEditPlacement) ==
                    MockInstrumentKind.WindowPanel;
                var editsComposition =
                    SignalCompositionEditor.CanConfigureTarget(
                        GetPlacementKind(connectEditPlacement));
                SetStatus(
                    $"SELECTED: {editName} | " +
                    $"{connectionCount} SIGNAL / {patchCount} PATCH\n" +
                    (editsWindowPanel
                        ? $"PRESET: {((WindowPanelGraphicPreset)connectEditPlacement.Record.windowPanelPreset).ToString().ToUpperInvariant()} | " +
                          "R STICK U/D: CHANGE\n"
                        : editsComposition
                            ? $"COMPOSE: {SignalCompositionEditor.NormalizeKind(connectEditPlacement.Record.signalCompositionKind).ToString().ToUpperInvariant()} | " +
                              "R STICK U/D: CHANGE\n"
                        : string.Empty) +
                    "A: SELECT NEXT CONNECTION\n" +
                    "B: CANCEL",
                    ConnectionEditObjectColor);
                return;
            }

            if (connectSource == null && connectTarget != null)
            {
                var monitorTargetName = MockInstrumentCatalog.GetDisplayName(
                    GetPlacementKind(connectTarget));
                var isAudioTarget = ModularAudioPatchPolicy.CanTarget(
                    GetPlacementKind(connectTarget));
                var inputCount = isAudioTarget
                    ? CountAudioPatches(connectTarget.Record?.placementId)
                    : CountIncomingConnections(
                        connectTarget.Record?.placementId);
                var targetInputLimit = GetPlacementKind(connectTarget) ==
                                       MockInstrumentKind.WindowPanel
                    ? InstrumentSignalPolicy.MaximumWindowPanelInputs
                    : isAudioTarget
                        ? PlacementDocument.MaximumAudioPatchConnections
                        : InstrumentSignalPolicy.MaximumTrendMonitorInputs;
                SetStatus(
                    $"TARGET: {monitorTargetName} | INPUTS {inputCount}/" +
                    $"{targetInputLimit}\n" +
                    (GetPlacementKind(connectTarget) ==
                         MockInstrumentKind.WindowPanel
                        ? $"PRESET: {((WindowPanelGraphicPreset)connectTarget.Record.windowPanelPreset).ToString().ToUpperInvariant()} | " +
                          "R STICK U/D\n"
                        : SignalCompositionEditor.CanConfigureTarget(
                            GetPlacementKind(connectTarget))
                            ? $"COMPOSE: {SignalCompositionEditor.NormalizeKind(connectTarget.Record.signalCompositionKind).ToString().ToUpperInvariant()} | " +
                              "R STICK U/D\n"
                        : string.Empty) +
                    (isAudioTarget
                        ? "SELECT AUDIO SOURCE + TRIGGER\n"
                        : "SELECT INPUT SOURCE + TRIGGER\n") +
                    (isAudioTarget
                        ? "A: NEXT PATCH | B: CANCEL"
                        : "A: NEXT CONNECTION | B: CANCEL"),
                    ConnectTargetColor);
                return;
            }

            if (connectSource == null)
            {
                SetStatus(
                    $"CONNECT | SIGNAL " +
                    $"{placementDocument?.connections.Count ?? 0}/" +
                    $"{PlacementDocument.MaximumConnections} | AUDIO " +
                    $"{placementDocument?.audioPatchConnections.Count ?? 0}/" +
                    $"{PlacementDocument.MaximumAudioPatchConnections}\n" +
                    "SELECT OBJECT + TRIGGER\n" +
                    "D:CYN I:MAG R:GRN T:ORG",
                    ConnectBeamColor);
                return;
            }

            var sourceName = MockInstrumentCatalog.GetDisplayName(
                GetPlacementKind(connectSource));
            if (connectTarget == null)
            {
                var isAudioSource = ModularAudioPatchPolicy.CanSource(
                    GetPlacementKind(connectSource)) &&
                    (!ModularAudioPatchPolicy.SupportsSignalRole(
                         GetPlacementKind(connectSource)) ||
                     pendingObservableAudioSource);
                var connectionCount =
                    CountConnections(connectSource.Record?.placementId) +
                    CountAudioPatches(connectSource.Record?.placementId);
                var isObservableSource =
                    ModularAudioPatchPolicy.SupportsSignalRole(
                        GetPlacementKind(connectSource));
                SetStatus(
                    $"SOURCE: {sourceName}\n" +
                    (isObservableSource
                        ? $"ROLE: {GetObservableSourceRoleLabel(connectSource)}\n"
                        : string.Empty) +
                    (isAudioSource
                        ? GetModuleOutputStatus(
                            connectSource)
                        : $"TRANSFORM: {transformLabel} | L STICK L/R\n" +
                          (ModularAudioParameterPolicy.SupportsEditing(
                              GetPlacementKind(connectSource))
                              ? "Y: EDIT RANGE\n"
                              : string.Empty)) +
                    $"TARGET + TRIGGER | A: SELECT " +
                    $"({connectionCount})\n" +
                    (isObservableSource
                        ? "SOURCE + TRIGGER: SWITCH | B: CANCEL"
                        : "B: CANCEL"),
                    isAudioSource
                        ? ModuleSourceColor(
                            GetPlacementKind(connectSource))
                        : ConnectionColor(pendingSignalTransform));
                return;
            }

            var targetName = MockInstrumentCatalog.GetDisplayName(
                GetPlacementKind(connectTarget));
            var isPendingAudioPatch =
                TryGetPendingModularRoute(
                GetPlacementKind(connectSource),
                GetPlacementKind(connectTarget),
                out var pendingSourcePort,
                out var pendingTargetPort,
                out var pendingDomain);
            var isObservablePatchSource =
                pendingObservableAudioSource &&
                ModularAudioPatchPolicy.SupportsSignalRole(
                    GetPlacementKind(connectSource));
            SetStatus(
                $"{sourceName} -> {targetName}\n" +
                (isPendingAudioPatch
                    ? $"{pendingDomain.ToString().ToUpperInvariant()} | " +
                      $"{pendingSourcePort} -> {pendingTargetPort}"
                    : isObservablePatchSource
                        ? $"{GetObservableSourceRoleLabel(connectSource)} | " +
                          "TARGET HAS NO COMPATIBLE INPUT\n" +
                          "L STICK L/R: PORT"
                    : $"{transformLabel}" +
                      (GetPlacementKind(connectTarget) ==
                           MockInstrumentKind.WindowPanel &&
                       WindowPanelInputSlotPolicy.TryFindLowestAvailable(
                           placementDocument?.connections,
                           connectTarget.Record?.placementId,
                           out var pendingSlot)
                          ? $" | SLOT {SlotLabel(pendingSlot)}"
                          : string.Empty)) +
                (isObservablePatchSource && !isPendingAudioPatch
                    ? " | SOURCE + TRIGGER: SWITCH | B CANCEL"
                    : " | A CONFIRM | B CANCEL"),
                isPendingAudioPatch
                    ? PatchColor(pendingDomain)
                    : isObservablePatchSource
                        ? ModuleSourceColor(
                            GetPlacementKind(connectSource))
                    : ConnectionColor(pendingSignalTransform));
        }

        private string GetModuleOutputStatus(
            RuntimePlacement placement)
        {
            var kind = GetPlacementKind(placement);
            var editHint = ModularAudioParameterPolicy.SupportsEditing(kind)
                ? "Y: EDIT PARAMETERS\n"
                : string.Empty;
            var moduleStatus = string.Empty;
            if (kind == MockInstrumentKind.AudioSequencer &&
                placement?.AudioModule?.Node is
                    ModularSequencerNode sequencer)
            {
                moduleStatus = $"{sequencer.StepCount} STEP | " +
                               $"{sequencer.TempoBpm:0} BPM | " +
                               $"CLOCK: {(sequencer.UsesExternalClock ? "EXTERNAL" : "INTERNAL")}\n";
            }
            if (kind == MockInstrumentKind.AudioDelay &&
                placement?.AudioModule?.Node is ModularDelayNode delay)
            {
                return $"TIME: {delay.DelaySeconds * 1000f:0} MS | " +
                       $"FEEDBACK: {delay.Feedback * 100f:0}%\n" +
                       "PORT: AUDIO.OUT\n";
            }
            var outputCount =
                ModularAudioPatchPolicy.GetSelectableOutputCount(kind);
            if (outputCount > 0)
            {
                var portId =
                    ModularAudioPatchPolicy.GetSelectableOutputPortId(
                        kind,
                        pendingObservableOutputIndex);
                return $"PORT: {portId?.ToUpperInvariant()} " +
                       $"({pendingObservableOutputIndex + 1}/{outputCount}) | " +
                       "L STICK L/R\n" + moduleStatus + editHint;
            }
            return kind == MockInstrumentKind.AudioLfo
                ? $"RATE: {(pendingLfoAudioRate ? "AUDIO" : "CONTROL")} | " +
                  "L STICK L/R\n" + editHint
                : "PORT: AUDIO.OUT\n" + editHint;
        }

        private string GetObservableSourceRoleLabel(
            RuntimePlacement placement)
        {
            if (!pendingObservableAudioSource)
                return "CONTROL SIGNAL";
            var kind = GetPlacementKind(placement);
            var portId = ModularAudioPatchPolicy.GetSelectableOutputPortId(
                kind,
                pendingObservableOutputIndex);
            return ModularAudioPatchPolicy.TryGetOutputDomain(
                kind,
                portId,
                out var domain)
                ? $"{domain.ToString().ToUpperInvariant()} PATCH"
                : "PATCH";
        }

        private Color ModuleSourceColor(MockInstrumentKind kind)
        {
            var selectedPort =
                ModularAudioPatchPolicy.GetSelectableOutputPortId(
                    kind,
                    pendingObservableOutputIndex);
            if (selectedPort != null &&
                ModularAudioPatchPolicy.TryGetOutputDomain(
                    kind,
                    selectedPort,
                    out var selectedDomain))
            {
                return PatchColor(selectedDomain);
            }
            if (kind == MockInstrumentKind.AudioLfo)
            {
                return PatchColor(pendingLfoAudioRate
                    ? ModularAudioPortDomain.Audio
                    : ModularAudioPortDomain.Control);
            }
            return kind == MockInstrumentKind.AudioSequencer
                ? ControlPatchColor
                : AudioPatchColor;
        }

        private bool TryGetPendingModularRoute(
            MockInstrumentKind source,
            MockInstrumentKind target,
            out string sourcePortId,
            out string targetPortId,
            out ModularAudioPortDomain domain)
        {
            if (ModularAudioPatchPolicy.SupportsSignalRole(source) &&
                !pendingObservableAudioSource)
            {
                sourcePortId = null;
                targetPortId = null;
                domain = default;
                return false;
            }
            var selectedPort =
                ModularAudioPatchPolicy.GetSelectableOutputPortId(
                    source,
                    pendingObservableOutputIndex);
            if (selectedPort != null)
            {
                sourcePortId = selectedPort;
                return ModularAudioPatchPolicy.TryGetRouteFromPort(
                    source,
                    target,
                    sourcePortId,
                    out targetPortId,
                    out domain);
            }
            return ModularAudioPatchPolicy.TryGetRoute(
                source,
                target,
                pendingLfoAudioRate
                    ? ModularAudioPortDomain.Audio
                    : ModularAudioPortDomain.Control,
                out sourcePortId,
                out targetPortId,
                out domain);
        }

        private static string SlotLabel(int slot)
        {
            return WindowPanelInputSlotPolicy.IsValid(slot)
                ? ((char)('A' + slot)).ToString()
                : "AUTO";
        }

        private int CountConnections(string placementId)
        {
            return SignalConnectionSelectionPolicy.CountForPlacement(
                placementDocument?.connections,
                placementId);
        }

        private int CountAudioPatches(string placementId)
        {
            return ModularAudioPatchPolicy.CountForPlacement(
                placementDocument?.audioPatchConnections,
                placementId);
        }

        private int CountIncomingConnections(string placementId)
        {
            if (placementDocument?.connections == null ||
                string.IsNullOrEmpty(placementId))
            {
                return 0;
            }

            var count = 0;
            foreach (var connection in placementDocument.connections)
            {
                if (connection?.targetPlacementId == placementId)
                    count++;
            }
            return count;
        }

        private void SetConnectNotice(
            string message,
            Color color,
            float duration = 1.2f)
        {
            connectStatusHoldUntil =
                Time.unscaledTime + Mathf.Max(0f, duration);
            SetStatus(message, color);
        }

        private GameObject CreateConnectMarker(
            RuntimePlacement placement,
            string objectName,
            Color color,
            float width)
        {
            if (placement?.Root == null)
                return null;

            var size = GetBoundsSize(placement);
            var marker = new GameObject(objectName);
            marker.transform.SetParent(placement.Root.transform, false);
            var line = marker.AddComponent<LineRenderer>();
            line.useWorldSpace = false;
            line.loop = true;
            line.positionCount = 4;
            line.startWidth = width;
            line.endWidth = width;
            line.numCornerVertices = 2;
            var halfWidth = size.x * 0.5f + SelectionMarkerPadding;
            var halfHeight = size.y * 0.5f + SelectionMarkerPadding;
            var z = size.z * 0.5f + 0.014f;
            line.SetPosition(0, new Vector3(-halfWidth, -halfHeight, z));
            line.SetPosition(1, new Vector3(halfWidth, -halfHeight, z));
            line.SetPosition(2, new Vector3(halfWidth, halfHeight, z));
            line.SetPosition(3, new Vector3(-halfWidth, halfHeight, z));
            RuntimeMaterialUtility.ApplySharedUnlit(line, color);
            return marker;
        }

        private void ClearConnectSelection()
        {
            if (audioParameterEditPlacement != null)
                CancelAudioParameterEdit(true);
            if (connectSourceMarker != null)
                Destroy(connectSourceMarker);
            if (connectTargetMarker != null)
                Destroy(connectTargetMarker);
            connectSourceMarker = null;
            connectTargetMarker = null;
            connectSource = null;
            connectTarget = null;
            ClearConnectEditSelection();
            pendingSignalTransform = SignalTransformKind.Direct;
            selectedConnectionPendingTransform =
                SignalTransformKind.Direct;
            selectedConnectionPendingSlot =
                SignalConnectionRecord.AutomaticTargetInputSlot;
            selectedConnectionPendingPriority =
                SignalConnectionRecord.DefaultCompositionPriority;
            connectionParameterDraft = null;
            pendingLfoAudioRate = false;
            pendingObservableAudioSource = false;
            pendingObservableOutputIndex = 0;
            connectAxisEngaged = false;
            connectParameterFieldAxisEngaged = false;
            connectSlotAxisEngaged = false;
            connectTargetSettingAxisEngaged = false;
        }

        private void ClearConnectEditSelection()
        {
            if (connectEditMarker != null)
                Destroy(connectEditMarker);
            connectEditMarker = null;
            connectEditPlacement = null;
            selectedConnectionForRemoval = null;
            selectedAudioPatchForRemoval = null;
            selectedConnectionPendingTransform =
                SignalTransformKind.Direct;
            selectedConnectionPendingSlot =
                SignalConnectionRecord.AutomaticTargetInputSlot;
            selectedConnectionPendingPriority =
                SignalConnectionRecord.DefaultCompositionPriority;
            connectionParameterDraft = null;
            connectParameterFieldAxisEngaged = false;
            connectSlotAxisEngaged = false;
            connectTargetSettingAxisEngaged = false;
        }

        private void UpdateSignalGraph()
        {
            modularAudioModules.Clear();
            modularAudioOutputs.Clear();
            foreach (var placement in placements)
            {
                if (placement?.Record == null ||
                    placement.AudioModule == null)
                    continue;
                var placementId = placement.Record.placementId;
                modularAudioModules[placementId] = placement.AudioModule;
                if (placement.AudioGraphPlayer != null)
                {
                    modularAudioOutputs[placementId] =
                        placement.AudioGraphPlayer;
                }
            }
            modularAudioPatchRuntime.Refresh(
                placementDocument?.audioPatchConnections,
                modularAudioModules,
                modularAudioOutputs);

            signalInteractions.Clear();
            signalCompositionKinds.Clear();
            var connections = placementDocument?.connections;
            if (connections != null && connections.Count > 0)
            {
                foreach (var placement in placements)
                {
                    if (placement?.Record == null ||
                        placement.Interaction == null)
                    {
                        continue;
                    }
                    signalInteractions[placement.Record.placementId] =
                        placement.Interaction;
                    signalCompositionKinds[placement.Record.placementId] =
                        (SignalCompositionKind)
                        placement.Record.signalCompositionKind;
                }
            }
            signalGraphEvaluator.Evaluate(
                connections,
                signalInteractions,
                RefreshWindowPanelSignals(connections),
                signalCompositionKinds);

            signalMonitorRefreshQueue.Clear();
            foreach (var placement in placements)
            {
                if (placement?.SignalMonitor == null ||
                    placement.Record == null)
                {
                    continue;
                }
                signalMonitorRefreshQueue.Add(placement);
            }

            var refreshCount = signalMonitorRefreshScheduler.Accumulate(
                signalMonitorRefreshQueue.Count,
                Time.unscaledDeltaTime);
            for (var refresh = 0; refresh < refreshCount; refresh++)
            {
                var index = signalMonitorRefreshScheduler.TakeNextIndex(
                    signalMonitorRefreshQueue.Count);
                RefreshSignalMonitor(
                    signalMonitorRefreshQueue[index],
                    connections);
            }
        }

        private void RefreshSignalMonitor(
            RuntimePlacement placement,
            IReadOnlyList<SignalConnectionRecord> connections)
        {
            var monitor = placement.SignalMonitor;
            monitor.BeginRefresh();
            var minimumValue = float.PositiveInfinity;
            var maximumValue = float.NegativeInfinity;
            var finiteInputCount = 0;
            if (connections != null)
            {
                foreach (var connection in connections)
                {
                    if (connection == null ||
                        !string.Equals(
                            connection.targetPlacementId,
                            placement.Record.placementId,
                            StringComparison.Ordinal) ||
                        !signalInteractions.TryGetValue(
                            connection.sourcePlacementId,
                            out var source))
                    {
                        continue;
                    }

                    var value = InstrumentSignalPolicy.Transform(
                        source.OutputValue,
                        connection);
                    monitor.AddSample(connection.connectionId, value);
                    if (!float.IsNaN(value) && !float.IsInfinity(value))
                    {
                        minimumValue = Mathf.Min(minimumValue, value);
                        maximumValue = Mathf.Max(maximumValue, value);
                        finiteInputCount++;
                    }
                }
            }

            var compositionKind = SignalCompositionEditor.NormalizeKind(
                placement.Record.signalCompositionKind);
            if (signalGraphEvaluator.TryGetOutput(
                    placement.Record.placementId,
                    out var composedValue,
                    out var validInputCount))
            {
                monitor.AddComposedSample(
                    compositionKind,
                    composedValue,
                    validInputCount);
                placement.Audio?.SetTrendState(
                    composedValue,
                    finiteInputCount > 1
                        ? maximumValue - minimumValue
                        : 0f,
                    validInputCount,
                    true);
                placement.AudioModule?.SetTrendState(
                    composedValue,
                    finiteInputCount > 1
                        ? maximumValue - minimumValue
                        : 0f,
                    validInputCount,
                    true);
            }
            else if (monitor.TouchedChannelCount > 0)
            {
                monitor.SetComposedUnavailable(compositionKind);
                placement.Audio?.SetTrendState(0f, 0f, 0, false);
                placement.AudioModule?.SetTrendState(
                    0f, 0f, 0, false);
            }
            else
            {
                placement.Audio?.SetTrendState(0f, 0f, 0, false);
                placement.AudioModule?.SetTrendState(
                    0f, 0f, 0, false);
            }

            monitor.EndRefresh();
        }

        private ISet<string> RefreshWindowPanelSignals(
            IReadOnlyList<SignalConnectionRecord> connections)
        {
            windowPanelTargetIds.Clear();
            foreach (var placement in placements)
            {
                if (placement?.WindowPanelSignal == null ||
                    placement.Record == null)
                {
                    continue;
                }

                var placementId = placement.Record.placementId;
                windowPanelTargetIds.Add(placementId);
                placement.WindowPanelSignal.Refresh(
                    placementId,
                    connections,
                    signalInteractions);
                placement.WindowPanelSignal.ApplyTo(
                    placement.WindowPanelGraphic,
                    (WindowPanelGraphicPreset)
                    placement.Record.windowPanelPreset);
                placement.Audio?.SetWindowPanelState(
                    placement.WindowPanelSignal.GetGraphicInputs(),
                    (WindowPanelGraphicPreset)
                    placement.Record.windowPanelPreset);
                placement.AudioModule?.SetWindowPanelState(
                    placement.WindowPanelSignal.GetGraphicInputs());
                placement.Interaction?.SetNormalizedValue(
                    placement.WindowPanelSignal.OutputValue,
                    InstrumentValueChangeOrigin.SignalGraph);
            }
            return windowPanelTargetIds;
        }

        private void UpdateConnectionVisuals()
        {
            var visible =
                AppInteractionModePolicy.ShowsConnectionVisuals(
                    interactionMode,
                    operationConnectionVisualsVisible,
                    connectionEditing);
            foreach (var line in connectionLines.Values)
            {
                if (line != null)
                    line.enabled = visible;
            }
            if (!visible || placementDocument == null)
                return;

            activeConnectionLineIds.Clear();
            if (placementDocument.connections != null)
                foreach (var connection in placementDocument.connections)
            {
                if (connection == null)
                    continue;
                var source = FindPlacementById(
                    connection.sourcePlacementId);
                var target = FindPlacementById(
                    connection.targetPlacementId);
                if (source?.Root == null || target?.Root == null)
                    continue;

                activeConnectionLineIds.Add(connection.connectionId);
                if (!connectionLines.TryGetValue(
                        connection.connectionId,
                        out var line) ||
                    line == null)
                {
                    line = CreateConnectionLine(connection.connectionId);
                    connectionLines[connection.connectionId] = line;
                }

                SetConnectionLinePositions(line, source, target);
                RuntimeMaterialUtility.SetColor(
                    line,
                    selectedConnectionForRemoval?.connectionId ==
                    connection.connectionId
                        ? SelectedConnectionColorFor(
                            selectedConnectionPendingTransform)
                        : ConnectionColor(
                            (SignalTransformKind)connection.transformKind));
                var isSelected =
                    selectedConnectionForRemoval?.connectionId ==
                    connection.connectionId;
                line.startWidth = ControllerBeamWidth *
                    (isSelected ? 3.2f : 1.4f);
                line.endWidth = ControllerBeamWidth *
                    (isSelected ? 2.4f : 0.8f);
                line.enabled = true;
            }

            if (placementDocument.audioPatchConnections != null)
                foreach (var connection in
                         placementDocument.audioPatchConnections)
                {
                    if (connection == null)
                        continue;
                    var source = FindPlacementById(
                        connection.sourcePlacementId);
                    var target = FindPlacementById(
                        connection.targetPlacementId);
                    if (source?.Root == null || target?.Root == null)
                        continue;

                    var domain = (ModularAudioPortDomain)
                        connection.portDomain;
                    var lineId = $"patch:{connection.connectionId}";
                    activeConnectionLineIds.Add(lineId);
                    if (!connectionLines.TryGetValue(lineId, out var line) ||
                        line == null)
                    {
                        line = CreateConnectionLine(
                            lineId,
                            domain.ToString());
                        connectionLines[lineId] = line;
                    }

                    SetConnectionLinePositions(
                        line,
                        source,
                        target,
                        connection.sourcePortId,
                        connection.targetPortId);
                    var isSelected =
                        selectedAudioPatchForRemoval?.connectionId ==
                        connection.connectionId;
                    RuntimeMaterialUtility.SetColor(
                        line,
                        isSelected
                            ? SelectedAudioPatchColor
                            : PatchColor(domain));
                    line.startWidth = ControllerBeamWidth *
                        (isSelected ? 3.2f : 1.8f);
                    line.endWidth = ControllerBeamWidth *
                        (isSelected ? 2.4f : 1.1f);
                    line.enabled = true;
                }

            staleConnectionLineIds.Clear();
            foreach (var pair in connectionLines)
            {
                if (!activeConnectionLineIds.Contains(pair.Key))
                    staleConnectionLineIds.Add(pair.Key);
            }
            foreach (var staleId in staleConnectionLineIds)
            {
                if (connectionLines[staleId] != null)
                    Destroy(connectionLines[staleId].gameObject);
                connectionLines.Remove(staleId);
            }
        }

        private static void SetConnectionLinePositions(
            LineRenderer line,
            RuntimePlacement source,
            RuntimePlacement target,
            string sourcePortId = null,
            string targetPortId = null)
        {
            var sourcePosition = ResolveConnectionEndpoint(
                source,
                sourcePortId);
            var targetPosition = ResolveConnectionEndpoint(
                target,
                targetPortId);
            var midpoint = Vector3.Lerp(
                sourcePosition,
                targetPosition,
                0.5f);
            var outward =
                source.Root.transform.forward +
                target.Root.transform.forward;
            if (outward.sqrMagnitude < 0.0001f)
                outward = source.Root.transform.forward;
            midpoint += outward.normalized * Mathf.Min(
                0.15f,
                Vector3.Distance(sourcePosition, targetPosition) * 0.12f);
            line.SetPosition(0, sourcePosition);
            line.SetPosition(1, midpoint);
            line.SetPosition(2, targetPosition);
        }

        private static Vector3 ResolveConnectionEndpoint(
            RuntimePlacement placement,
            string portId)
        {
            if (placement?.Root == null)
                return Vector3.zero;

            var contract = placement.Contract != null
                ? placement.Contract
                : placement.Root.GetComponent<InstrumentGreyboxContract>();
            return contract != null
                ? contract.ResolvePortAnchor(portId).position
                : placement.Root.transform.position;
        }

        private LineRenderer CreateConnectionLine(
            string connectionId,
            string domainLabel = "Signal")
        {
            var lineObject = new GameObject(
                $"[Connect] {domainLabel} {connectionId}");
            lineObject.transform.SetParent(transform, false);
            var line = lineObject.AddComponent<LineRenderer>();
            line.useWorldSpace = true;
            line.positionCount = 3;
            line.startWidth = ControllerBeamWidth * 1.4f;
            line.endWidth = ControllerBeamWidth * 0.8f;
            line.numCapVertices = 4;
            line.numCornerVertices = 3;
            line.shadowCastingMode =
                UnityEngine.Rendering.ShadowCastingMode.Off;
            line.receiveShadows = false;
            RuntimeMaterialUtility.ApplySharedUnlit(
                line,
                ConnectionLineColor);
            return line;
        }

        private static Color ConnectionColor(
            SignalTransformKind transform)
        {
            return transform switch
            {
                SignalTransformKind.Invert =>
                    InvertConnectionColor,
                SignalTransformKind.Range =>
                    RangeConnectionColor,
                SignalTransformKind.Threshold =>
                    ThresholdConnectionColor,
                _ => DirectConnectionColor
            };
        }

        private static Color PatchColor(ModularAudioPortDomain domain)
        {
            return domain switch
            {
                ModularAudioPortDomain.Control => ControlPatchColor,
                ModularAudioPortDomain.Clock => ClockPatchColor,
                ModularAudioPortDomain.Gate => GatePatchColor,
                ModularAudioPortDomain.Trigger => TriggerPatchColor,
                _ => AudioPatchColor
            };
        }

        private static Color SelectedConnectionColorFor(
            SignalTransformKind transform)
        {
            var color = Color.Lerp(
                ConnectionColor(transform),
                Color.white,
                0.38f);
            color.a = 1f;
            return color;
        }

        private void ClearConnectionVisuals()
        {
            foreach (var line in connectionLines.Values)
            {
                if (line != null)
                    Destroy(line.gameObject);
            }
            connectionLines.Clear();
            activeConnectionLineIds.Clear();
        }

        private void SetAmbientMeterAnimationState(bool enabled)
        {
            foreach (var placement in placements)
            {
                var motion = placement?.Interaction?.Motion;
                if (motion != null &&
                    MockInstrumentCatalog.IsReadOnlyMeter(
                        GetPlacementKind(placement)))
                {
                    motion.SetAmbientAnimationEnabled(enabled);
                }
            }
        }

        private bool TryResolveNonOverlappingPose(
            Pose desiredPose,
            MockInstrumentKind kind,
            out Pose resolvedPose)
        {
            if (!OverlapsExistingPlacement(desiredPose, kind))
            {
                resolvedPose = desiredPose;
                return true;
            }

            var candidateBounds = InstrumentGreyboxSpecification.Get(kind).BoundsSize;
            var horizontalStep = candidateBounds.x + PlacementSpacing;
            var verticalStep = candidateBounds.y + PlacementSpacing;
            for (var ring = 1; ring <= AutoPlacementMaximumRing; ring++)
            {
                for (var y = -ring; y <= ring; y++)
                {
                    for (var x = -ring; x <= ring; x++)
                    {
                        if (Mathf.Max(Mathf.Abs(x), Mathf.Abs(y)) != ring)
                            continue;

                        var candidate = new Pose(
                            desiredPose.position +
                            desiredPose.rotation * new Vector3(
                                x * horizontalStep,
                                y * verticalStep,
                                0f),
                            desiredPose.rotation);
                        if (TrySnapToCurrentSurface(candidate, out var snappedCandidate) &&
                            !OverlapsExistingPlacement(snappedCandidate, kind))
                        {
                            resolvedPose = snappedCandidate;
                            return true;
                        }
                    }
                }
            }

            resolvedPose = desiredPose;
            return false;
        }

        private bool TrySnapToCurrentSurface(
            Pose candidate,
            out Pose snappedPose)
        {
            snappedPose = candidate;
            var forward = candidate.rotation * Vector3.forward;
            var ray = new Ray(
                candidate.position + forward * 0.2f,
                -forward);
            if (!TryRaycastCurrentSurface(
                    ray,
                    0.5f,
                    out var hit) ||
                Vector3.Dot(hit.Normal.normalized, forward) <
                    CoplanarNormalDotThreshold)
            {
                return false;
            }

            snappedPose = new Pose(
                hit.Point + hit.Normal.normalized * SurfaceOffset,
                candidate.rotation);
            return true;
        }

        private bool OverlapsExistingPlacement(
            Pose candidate,
            MockInstrumentKind candidateKind)
        {
            var candidateSpec = InstrumentGreyboxSpecification.Get(candidateKind);
            var candidateRight = candidate.rotation * Vector3.right;
            var candidateUp = candidate.rotation * Vector3.up;
            var candidateForward = candidate.rotation * Vector3.forward;

            foreach (var placement in placements)
            {
                if (placement?.Root == null)
                    continue;

                var other = placement.Root.transform;
                if (Vector3.Dot(candidateForward, other.forward) <
                    CoplanarNormalDotThreshold)
                {
                    continue;
                }

                var delta = other.position - candidate.position;
                if (Mathf.Abs(Vector3.Dot(delta, candidateForward)) >
                    CoplanarDistanceTolerance)
                {
                    continue;
                }

                var contract = placement.Root.GetComponent<InstrumentGreyboxContract>();
                var otherSpec = InstrumentGreyboxSpecification.Get(
                    contract != null ? contract.Kind : MockInstrumentKind.RoundMeter);
                var otherHalfX =
                    Mathf.Abs(Vector3.Dot(other.right, candidateRight)) *
                    otherSpec.BoundsSize.x * 0.5f +
                    Mathf.Abs(Vector3.Dot(other.up, candidateRight)) *
                    otherSpec.BoundsSize.y * 0.5f;
                var otherHalfY =
                    Mathf.Abs(Vector3.Dot(other.right, candidateUp)) *
                    otherSpec.BoundsSize.x * 0.5f +
                    Mathf.Abs(Vector3.Dot(other.up, candidateUp)) *
                    otherSpec.BoundsSize.y * 0.5f;

                if (Mathf.Abs(Vector3.Dot(delta, candidateRight)) <
                        candidateSpec.BoundsSize.x * 0.5f + otherHalfX +
                        CollisionMargin &&
                    Mathf.Abs(Vector3.Dot(delta, candidateUp)) <
                        candidateSpec.BoundsSize.y * 0.5f + otherHalfY +
                        CollisionMargin)
                {
                    return true;
                }
            }

            return false;
        }

        private void AlignSelection(bool vertical)
        {
            if (!PrepareLayoutSource())
                return;

            var reference = groupMovePivot;
            if (!AreCoplanar(groupMoveSelection, reference))
            {
                SetStatus(
                    "ALIGN BLOCKED: SELECT ONE SURFACE",
                    Color.yellow);
                return;
            }

            var referenceIndex = groupMoveSelection.IndexOf(reference);
            var referencePose = layoutSourcePoses[referenceIndex];
            var axis = referencePose.rotation *
                       (vertical ? Vector3.up : Vector3.right);
            var order = BuildSpatialOrder(axis, referencePose.position);
            var referenceRank = order.IndexOf(referenceIndex);
            var poses = new List<Pose>(layoutSourcePoses);
            var referencePosition = referencePose.position;
            var referenceSize = GetBoundsSize(reference);
            poses[referenceIndex] = new Pose(
                referencePosition,
                referencePose.rotation);

            var positiveCursor =
                (vertical ? referenceSize.y : referenceSize.x) * 0.5f;
            for (var rank = referenceRank + 1;
                 rank < order.Count;
                 rank++)
            {
                var index = order[rank];
                var placement = groupMoveSelection[index];
                var size = GetBoundsSize(placement);
                var extent = vertical ? size.y : size.x;
                poses[index] = new Pose(
                    referencePosition +
                    axis *
                    (positiveCursor +
                     PlacementSpacing +
                     extent * 0.5f),
                    referencePose.rotation);
                positiveCursor += PlacementSpacing + extent;
            }

            var negativeCursor =
                (vertical ? referenceSize.y : referenceSize.x) * 0.5f;
            for (var rank = referenceRank - 1; rank >= 0; rank--)
            {
                var index = order[rank];
                var placement = groupMoveSelection[index];
                var size = GetBoundsSize(placement);
                var extent = vertical ? size.y : size.x;
                poses[index] = new Pose(
                    referencePosition -
                    axis *
                    (negativeCursor +
                     PlacementSpacing +
                     extent * 0.5f),
                    referencePose.rotation);
                negativeCursor += PlacementSpacing + extent;
            }

            SetPendingLayout(
                vertical
                    ? PendingLayout.VerticalAlign
                    : PendingLayout.HorizontalAlign,
                poses);
        }

        private bool HandleAlignmentStick(Vector2 axis)
        {
            var magnitude = Mathf.Max(
                Mathf.Abs(axis.x),
                Mathf.Abs(axis.y));
            if (magnitude <= SelectionReleaseThreshold)
            {
                alignmentAxisEngaged = false;
                return false;
            }
            if (alignmentAxisEngaged ||
                magnitude < SelectionThreshold)
            {
                return false;
            }

            alignmentAxisEngaged = true;
            if (Mathf.Abs(axis.x) >= Mathf.Abs(axis.y))
            {
                if (axis.x < 0f)
                    AlignSelection(vertical: false);
                else
                    DistributeSelection(vertical: false);
            }
            else if (axis.y > 0f)
            {
                AlignSelection(vertical: true);
            }
            else
            {
                DistributeSelection(vertical: true);
            }
            return true;
        }

        private bool HandleSelectionRotationStick(Vector2 axis)
        {
            var magnitude = Mathf.Max(
                Mathf.Abs(axis.x),
                Mathf.Abs(axis.y));
            if (magnitude <= SelectionReleaseThreshold)
            {
                rotationAxisEngaged = false;
                return false;
            }
            if (rotationAxisEngaged ||
                magnitude < SelectionThreshold)
            {
                return false;
            }

            rotationAxisEngaged = true;
            RotateSelectionTowardStick(axis);
            return true;
        }

        private void DistributeSelection(bool vertical)
        {
            if (!PrepareLayoutSource())
                return;
            if (!AreCoplanar(groupMoveSelection, groupMovePivot))
            {
                SetStatus(
                    "DISTRIBUTE BLOCKED: SELECT ONE SURFACE",
                    Color.yellow);
                return;
            }

            var referenceIndex =
                groupMoveSelection.IndexOf(groupMovePivot);
            var referencePose = layoutSourcePoses[referenceIndex];
            var axis = vertical
                ? referencePose.rotation * Vector3.up
                : referencePose.rotation * Vector3.right;
            var order = BuildSpatialOrder(axis, referencePose.position);
            var firstIndex = order[0];
            var lastIndex = order[order.Count - 1];
            var firstProjection = Vector3.Dot(
                layoutSourcePoses[firstIndex].position -
                referencePose.position,
                axis);
            var lastProjection = Vector3.Dot(
                layoutSourcePoses[lastIndex].position -
                referencePose.position,
                axis);
            var poses = new List<Pose>(layoutSourcePoses);
            for (var rank = 0; rank < order.Count; rank++)
            {
                var index = order[rank];
                var t = rank / (float)(order.Count - 1);
                poses[index] = new Pose(
                    referencePose.position +
                    axis * Mathf.Lerp(
                        firstProjection,
                        lastProjection,
                        t),
                    referencePose.rotation);
            }

            SetPendingLayout(
                vertical
                    ? PendingLayout.VerticalDistribute
                    : PendingLayout.HorizontalDistribute,
                poses);
        }

        private bool PrepareLayoutSource()
        {
            if (groupMoveSelection.Count < 2 ||
                groupMovePivot?.Root == null)
            {
                SetStatus("SELECT TWO OR MORE INSTRUMENTS", Color.yellow);
                return false;
            }

            if (layoutSourcePoses.Count != groupMoveSelection.Count)
            {
                layoutSourcePoses.Clear();
                foreach (var placement in groupMoveSelection)
                {
                    var transform = placement.Root.transform;
                    layoutSourcePoses.Add(
                        new Pose(transform.position, transform.rotation));
                }
            }
            return true;
        }

        private List<int> BuildSpatialOrder(
            Vector3 axis,
            Vector3 origin)
        {
            var order = new List<int>(groupMoveSelection.Count);
            for (var index = 0;
                 index < groupMoveSelection.Count;
                 index++)
            {
                order.Add(index);
            }
            order.Sort((left, right) =>
            {
                var comparison = Vector3.Dot(
                        layoutSourcePoses[left].position - origin,
                        axis)
                    .CompareTo(Vector3.Dot(
                        layoutSourcePoses[right].position - origin,
                        axis));
                return comparison != 0
                    ? comparison
                    : string.Compare(
                        groupMoveSelection[left].Record.placementId,
                        groupMoveSelection[right].Record.placementId,
                        StringComparison.Ordinal);
            });
            return order;
        }

        private void SetPendingLayout(
            PendingLayout layout,
            IReadOnlyList<Pose> targetPoses)
        {
            pendingLayoutTargetPoses.Clear();
            pendingLayoutTargetPoses.AddRange(targetPoses);
            pendingLayout = layout;
            groupMoveArmed = true;
            SetPreviewVisible(false);
            PulseHaptics(OVRInput.Controller.LTouch);
            SetStatus(
                $"{PendingLayoutLabel(layout)} PREVIEW\n" +
                "A CONFIRM | CHOOSE ANOTHER L-STICK DIRECTION",
                Color.green);
        }

        private async void ConfirmPendingLayout()
        {
            if (pendingLayout == PendingLayout.None ||
                pendingLayoutTargetPoses.Count !=
                groupMoveSelection.Count)
            {
                return;
            }
            if (!EvaluateGroupMoveTarget(
                    pendingLayoutTargetPoses,
                    out var invalidReason))
            {
                SetStatus($"LAYOUT BLOCKED: {invalidReason}", Color.red);
                return;
            }

            var appliedLayout = pendingLayout;
            operationInProgress = true;
            try
            {
                if (await ApplyEditedWorldPosesAsync(
                        groupMoveSelection,
                        pendingLayoutTargetPoses,
                        null))
                {
                    ClearPendingLayout(clearSource: true);
                    RefreshSelectionMarkers();
                    PulseHaptics();
                    SetStatus(
                        $"{PendingLayoutLabel(appliedLayout)} CONFIRMED",
                        Color.green);
                }
            }
            finally
            {
                operationInProgress = false;
            }
        }

        private void ClearPendingLayout(bool clearSource)
        {
            pendingLayout = PendingLayout.None;
            pendingLayoutTargetPoses.Clear();
            if (clearSource)
                layoutSourcePoses.Clear();
            SetMoveTargetMarkersVisible(false);
        }

        private static string PendingLayoutLabel(PendingLayout layout)
        {
            return layout switch
            {
                PendingLayout.HorizontalAlign => "HORIZONTAL ALIGN",
                PendingLayout.VerticalAlign => "VERTICAL ALIGN",
                PendingLayout.HorizontalDistribute =>
                    "HORIZONTAL EVEN DISTRIBUTION",
                PendingLayout.VerticalDistribute =>
                    "VERTICAL EVEN DISTRIBUTION",
                _ => "LAYOUT"
            };
        }

        private async void RotateSelectionTowardStick(Vector2 stickDirection)
        {
            if (groupMoveSelection.Count < 2 ||
                groupMovePivot?.Root == null)
            {
                return;
            }

            ClearPendingLayout(clearSource: true);
            var group = new List<RuntimePlacement>(groupMoveSelection);
            var pivot = groupMovePivot.Root.transform;
            var sourceDirection = Vector3.zero;
            foreach (var placement in group)
            {
                if (ReferenceEquals(placement, groupMovePivot) ||
                    placement?.Root == null)
                {
                    continue;
                }

                sourceDirection =
                    Vector3.ProjectOnPlane(
                        placement.Root.transform.position - pivot.position,
                        pivot.forward);
                if (sourceDirection.sqrMagnitude > 0.000001f)
                    break;
            }
            if (sourceDirection.sqrMagnitude <= 0.000001f)
                sourceDirection = pivot.right;

            var cardinalStick = Mathf.Abs(stickDirection.x) >=
                                Mathf.Abs(stickDirection.y)
                ? new Vector2(Mathf.Sign(stickDirection.x), 0f)
                : new Vector2(0f, Mathf.Sign(stickDirection.y));
            var view = Camera.main != null
                ? Camera.main.transform
                : null;
            var planeRight = Vector3.ProjectOnPlane(
                view != null ? view.right : pivot.right,
                pivot.forward);
            if (planeRight.sqrMagnitude <= 0.000001f)
                planeRight = pivot.right;
            planeRight.Normalize();
            var planeUp = Vector3.ProjectOnPlane(
                view != null ? view.up : pivot.up,
                pivot.forward);
            if (planeUp.sqrMagnitude <= 0.000001f)
                planeUp = Vector3.Cross(pivot.forward, planeRight);
            planeUp.Normalize();
            var targetDirection =
                planeRight * cardinalStick.x +
                planeUp * cardinalStick.y;
            var angle = Vector3.SignedAngle(
                sourceDirection,
                targetDirection,
                pivot.forward);
            var rotation = Quaternion.AngleAxis(angle, pivot.forward);
            var poses = new List<Pose>(group.Count);
            foreach (var placement in group)
            {
                var transform = placement.Root.transform;
                poses.Add(new Pose(
                    pivot.position +
                    rotation * (transform.position - pivot.position),
                    rotation * transform.rotation));
            }

            operationInProgress = true;
            try
            {
                if (await ApplyEditedWorldPosesAsync(group, poses, null))
                {
                    RefreshSelectionMarkers();
                    PulseHaptics();
                    SetStatus(
                        $"ROTATED {group.Count} TOWARD " +
                        $"{StickDirectionLabel(cardinalStick)}\n" +
                        "FIRST OBJECT IS PIVOT",
                        Color.green);
                }
            }
            finally
            {
                operationInProgress = false;
            }
        }

        private static string StickDirectionLabel(Vector2 direction)
        {
            if (Mathf.Abs(direction.x) >= Mathf.Abs(direction.y))
                return direction.x < 0f ? "LEFT" : "RIGHT";
            return direction.y < 0f ? "DOWN" : "UP";
        }

        private static int GetAlignmentReferenceIndex(
            AlignmentAnchorMode mode,
            int groupCount,
            int originalReferenceIndex)
        {
            return mode switch
            {
                AlignmentAnchorMode.Trailing => groupCount - 1,
                AlignmentAnchorMode.Centered => (groupCount - 1) / 2,
                AlignmentAnchorMode.OriginalOrder =>
                    Mathf.Clamp(
                        originalReferenceIndex,
                        0,
                        groupCount - 1),
                _ => 0
            };
        }

        private static AlignmentAnchorMode NextAlignmentAnchorMode(
            AlignmentAnchorMode mode)
        {
            return mode switch
            {
                AlignmentAnchorMode.Leading =>
                    AlignmentAnchorMode.Trailing,
                AlignmentAnchorMode.Trailing =>
                    AlignmentAnchorMode.Centered,
                AlignmentAnchorMode.Centered =>
                    AlignmentAnchorMode.OriginalOrder,
                _ => AlignmentAnchorMode.Leading
            };
        }

        private static string AlignmentAnchorModeLabel(
            AlignmentAnchorMode mode)
        {
            return mode switch
            {
                AlignmentAnchorMode.Trailing => "FIRST AT END",
                AlignmentAnchorMode.Centered => "FIRST AT CENTER",
                AlignmentAnchorMode.OriginalOrder =>
                    "FIRST AT ORIGINAL ORDER",
                _ => "FIRST AT START"
            };
        }

        private static string BuildAlignmentGroupSignature(
            IReadOnlyList<RuntimePlacement> group)
        {
            var placementIds = new List<string>(group.Count);
            foreach (var placement in group)
                placementIds.Add(placement?.Record?.placementId ?? string.Empty);
            placementIds.Sort(StringComparer.Ordinal);
            return string.Join("|", placementIds);
        }

        private void ResetAlignmentCycle()
        {
            hasAlignmentCycle = false;
            lastAlignmentReference = null;
            lastAlignmentGroupSignature = null;
            lastAlignmentOriginalReferenceIndex = 0;
            nextAlignmentAnchorMode = AlignmentAnchorMode.Leading;
        }

        private async void HandleGroupMoveAction()
        {
            if (!groupMoveArmed)
            {
                RuntimePlacement aimed = null;
                if (TryResolvePlacedInteraction(out _, out _))
                    aimed = activePlacement;
                activePlacement = null;

                if (groupMoveSelection.Count == 0)
                {
                    if (aimed == null)
                    {
                        SetStatus(
                            "SELECT OR AIM AT AN INSTRUMENT\n" +
                            "LEFT GRIP + A TO ARM MOVE",
                            Color.yellow);
                        return;
                    }
                    groupMoveSelection.Add(aimed);
                    RefreshSelectionMarkers();
                }

                groupMovePivot =
                    aimed != null && groupMoveSelection.Contains(aimed)
                        ? aimed
                        : groupMoveSelection[0];
                ResetAlignmentCycle();
                groupMoveArmed = true;
                SetPreviewVisible(false);
                PulseHaptics();
                SetStatus(
                    $"GROUP SELECTED: {groupMoveSelection.Count}\n" +
                    "AIM AT A SURFACE | RELEASE TO CONFIRM\n" +
                    "B CLEAR SELECTION",
                    new Color(1f, 0.75f, 0.15f));
                return;
            }

            if (!hasPlacementPose || groupMovePivot?.Root == null)
            {
                SetStatus("AIM AT A DESTINATION SURFACE", Color.yellow);
                return;
            }

            foreach (var placement in groupMoveSelection)
            {
                var contract = placement.Root.GetComponent<InstrumentGreyboxContract>();
                if (pendingLayout == PendingLayout.None &&
                    contract != null &&
                    !MockInstrumentCatalog.SupportsSurface(
                        contract.Kind,
                        currentSurface))
                {
                    SetStatus(
                        $"{MockInstrumentCatalog.GetDisplayName(contract.Kind)} " +
                        $"IS NOT ALLOWED ON {currentSurface.ToString().ToUpperInvariant()}",
                        Color.yellow);
                    return;
                }
            }

            var poses = BuildGroupMoveTargetPoses();
            if (!EvaluateGroupMoveTarget(poses, out var invalidReason))
            {
                SetStatus($"MOVE BLOCKED: {invalidReason}", Color.red);
                return;
            }

            var movedCount = groupMoveSelection.Count;
            var newSurfaces = new List<int>(movedCount);
            for (var index = 0; index < movedCount; index++)
                newSurfaces.Add((int)currentSurface);

            operationInProgress = true;
            try
            {
                if (await ApplyEditedWorldPosesAsync(
                        groupMoveSelection,
                        poses,
                        newSurfaces,
                        isMove: true))
                {
                    ClearGroupMoveSelection();
                    PulseHaptics();
                    SetStatus($"MOVED {movedCount} INSTRUMENT(S)", Color.green);
                }
            }
            finally
            {
                operationInProgress = false;
            }
        }

        private List<Pose> BuildGroupMoveTargetPoses()
        {
            var poses = new List<Pose>(groupMoveSelection.Count);
            if (groupMovePivot?.Root == null)
                return poses;

            var pivotPose = new Pose(
                groupMovePivot.Root.transform.position,
                groupMovePivot.Root.transform.rotation);
            var rotationDelta =
                currentPlacementPose.rotation *
                Quaternion.Inverse(pivotPose.rotation);
            foreach (var placement in groupMoveSelection)
            {
                var oldTransform = placement.Root.transform;
                poses.Add(new Pose(
                    currentPlacementPose.position +
                    rotationDelta *
                    (oldTransform.position - pivotPose.position),
                    rotationDelta * oldTransform.rotation));
            }
            return poses;
        }

        private bool EvaluateGroupMoveTarget(
            IReadOnlyList<Pose> targetPoses,
            out string invalidReason)
        {
            invalidReason = string.Empty;
            if (targetPoses == null ||
                targetPoses.Count != groupMoveSelection.Count)
            {
                invalidReason = "NO DESTINATION";
                return false;
            }

            for (var index = 0; index < groupMoveSelection.Count; index++)
            {
                var placement = groupMoveSelection[index];
                var contract =
                    placement?.Root != null
                        ? placement.Root.GetComponent<InstrumentGreyboxContract>()
                        : null;
                if (pendingLayout == PendingLayout.None &&
                    contract != null &&
                    !MockInstrumentCatalog.SupportsSurface(
                        contract.Kind,
                        currentSurface))
                {
                    invalidReason =
                        $"{MockInstrumentCatalog.GetDisplayName(contract.Kind)} " +
                        "SURFACE NOT ALLOWED";
                    return false;
                }

                var leftSize = GetBoundsSize(placement);
                for (var otherIndex = 0;
                     otherIndex < placements.Count;
                     otherIndex++)
                {
                    var other = placements[otherIndex];
                    if (ReferenceEquals(placement, other) ||
                        other?.Root == null)
                    {
                        continue;
                    }

                    var selectedIndex = groupMoveSelection.IndexOf(other);
                    Pose otherPose;
                    if (selectedIndex >= 0)
                    {
                        otherPose = targetPoses[selectedIndex];
                    }
                    else
                    {
                        otherPose = new Pose(
                            other.Root.transform.position,
                            other.Root.transform.rotation);
                    }

                    if (PlacementPosesOverlap(
                            targetPoses[index],
                            leftSize,
                            otherPose,
                            GetBoundsSize(other)))
                    {
                        invalidReason = "DESTINATION OVERLAPS";
                        return false;
                    }
                }
            }
            return true;
        }

        private static bool PlacementPosesOverlap(
            Pose leftPose,
            Vector3 leftSize,
            Pose rightPose,
            Vector3 rightSize)
        {
            var leftRight = leftPose.rotation * Vector3.right;
            var leftUp = leftPose.rotation * Vector3.up;
            var leftForward = leftPose.rotation * Vector3.forward;
            var rightRight = rightPose.rotation * Vector3.right;
            var rightUp = rightPose.rotation * Vector3.up;
            var rightForward = rightPose.rotation * Vector3.forward;
            if (Vector3.Dot(leftForward, rightForward) <
                CoplanarNormalDotThreshold)
            {
                return false;
            }

            var delta = rightPose.position - leftPose.position;
            if (Mathf.Abs(Vector3.Dot(delta, leftForward)) >
                CoplanarDistanceTolerance)
            {
                return false;
            }

            var rightHalfX =
                Mathf.Abs(Vector3.Dot(rightRight, leftRight)) *
                rightSize.x * 0.5f +
                Mathf.Abs(Vector3.Dot(rightUp, leftRight)) *
                rightSize.y * 0.5f;
            var rightHalfY =
                Mathf.Abs(Vector3.Dot(rightRight, leftUp)) *
                rightSize.x * 0.5f +
                Mathf.Abs(Vector3.Dot(rightUp, leftUp)) *
                rightSize.y * 0.5f;
            return Mathf.Abs(Vector3.Dot(delta, leftRight)) <
                       leftSize.x * 0.5f + rightHalfX + CollisionMargin &&
                   Mathf.Abs(Vector3.Dot(delta, leftUp)) <
                       leftSize.y * 0.5f + rightHalfY + CollisionMargin;
        }

        private static bool AreCoplanar(
            IReadOnlyList<RuntimePlacement> group,
            RuntimePlacement reference)
        {
            if (reference?.Root == null)
                return false;

            var referenceTransform = reference.Root.transform;
            foreach (var placement in group)
            {
                if (placement?.Root == null ||
                    Vector3.Dot(
                        referenceTransform.forward,
                        placement.Root.transform.forward) <
                    CoplanarNormalDotThreshold ||
                    Mathf.Abs(Vector3.Dot(
                        placement.Root.transform.position -
                        referenceTransform.position,
                        referenceTransform.forward)) >
                    CoplanarDistanceTolerance)
                {
                    return false;
                }
            }
            return true;
        }

        private List<RuntimePlacement> GetCoplanarGroup(
            RuntimePlacement reference)
        {
            var group = new List<RuntimePlacement>();
            if (reference?.Root == null)
                return group;

            var referenceTransform = reference.Root.transform;
            foreach (var placement in placements)
            {
                if (placement?.Root == null)
                    continue;

                var candidate = placement.Root.transform;
                if (Vector3.Dot(referenceTransform.forward, candidate.forward) <
                        CoplanarNormalDotThreshold ||
                    Mathf.Abs(Vector3.Dot(
                        candidate.position - referenceTransform.position,
                        referenceTransform.forward)) >
                        CoplanarDistanceTolerance)
                {
                    continue;
                }
                group.Add(placement);
            }
            return group;
        }

        private async Task<bool> ApplyEditedWorldPosesAsync(
            IReadOnlyList<RuntimePlacement> editedPlacements,
            IReadOnlyList<Pose> worldPoses,
            IReadOnlyList<int> newSurfaces,
            bool recordHistory = true,
            bool isMove = false)
        {
            if (editedPlacements == null ||
                worldPoses == null ||
                editedPlacements.Count != worldPoses.Count ||
                (newSurfaces != null &&
                 newSurfaces.Count != editedPlacements.Count))
            {
                return false;
            }

            var beforeHistory = CaptureEditStates(editedPlacements);
            var previousStates =
                new List<PlacementRuntimeState>(editedPlacements.Count);
            foreach (var placement in editedPlacements)
            {
                if (placement?.Root == null ||
                    placement.AnchorRoot == null ||
                    placement.Anchor == null)
                {
                    return false;
                }
                previousStates.Add(new PlacementRuntimeState
                {
                    Placement = placement,
                    Anchor = placement.Anchor,
                    AnchorRoot = placement.AnchorRoot,
                    AnchorId = placement.Record.anchorId,
                    LocalPose = new Pose(
                        placement.Root.transform.localPosition,
                        placement.Root.transform.localRotation),
                    SurfaceKind = placement.Record.surfaceKind
                });
            }

            for (var index = 0; index < editedPlacements.Count; index++)
            {
                var placement = editedPlacements[index];
                SetPlacementWorldPose(placement, worldPoses[index]);
                if (newSurfaces != null)
                    placement.Record.surfaceKind = newSurfaces[index];
            }

            if (HasEditedPlacementOverlap(editedPlacements))
            {
                RestoreRuntimeStates(previousStates);
                SetStatus(
                    "EDIT BLOCKED: DESTINATION OVERLAPS",
                    Color.yellow);
                return false;
            }

            var coverageRadiusSquared =
                SharedAnchorCoverageRadius * SharedAnchorCoverageRadius;
            var createdTargets = new List<AnchorTarget>();
            var assignments =
                new Dictionary<RuntimePlacement, AnchorTarget>();
            try
            {
                for (var index = 0; index < editedPlacements.Count; index++)
                {
                    var placement = editedPlacements[index];
                    if (Vector3.SqrMagnitude(
                            worldPoses[index].position -
                            placement.AnchorRoot.transform.position) <=
                        coverageRadiusSquared)
                    {
                        continue;
                    }

                    var target = FindAnchorTargetForPosition(
                        worldPoses[index].position,
                        createdTargets);
                    if (target == null)
                    {
                        SetStatus("CREATING REPLACEMENT ANCHOR...");
                        var anchorRoot = new GameObject("[Anchor] Edited Group");
                        anchorRoot.transform.SetPositionAndRotation(
                            worldPoses[index].position,
                            worldPoses[index].rotation);
                        var surfaceValue = newSurfaces != null
                            ? newSurfaces[index]
                            : placement.Record.surfaceKind;
                        var surface = Enum.IsDefined(
                            typeof(SurfaceKind),
                            surfaceValue)
                            ? (SurfaceKind)surfaceValue
                            : SurfaceKind.Unknown;
                        var anchor = await anchorService.CreateAsync(
                            anchorRoot,
                            surface);
                        target = new AnchorTarget
                        {
                            Anchor = anchor,
                            Root = anchorRoot,
                            Created = true
                        };
                        createdTargets.Add(target);
                    }
                    assignments.Add(placement, target);
                }

                for (var index = 0; index < editedPlacements.Count; index++)
                {
                    var placement = editedPlacements[index];
                    if (assignments.TryGetValue(placement, out var target))
                    {
                        placement.Root.transform.SetParent(
                            target.Root.transform,
                            true);
                        placement.Anchor = target.Anchor;
                        placement.AnchorRoot = target.Root;
                        placement.Record.anchorId = target.Anchor.Id;
                    }
                    SetPlacementWorldPose(placement, worldPoses[index]);
                }

                if (!SavePlacementDocument())
                    throw new InvalidOperationException(
                        "Edited placement document could not be saved.");

                if (assignments.Count > 0)
                {
                    Debug.Log(
                        $"[Placement] Re-anchored {assignments.Count} edited " +
                        $"placement(s) using {createdTargets.Count} new anchor(s).");
                }
            }
            catch (Exception exception)
            {
                RestoreRuntimeStates(previousStates);
                await RemoveCreatedAnchorTargetsAsync(createdTargets);
                Debug.LogException(exception);
                SetStatus("EDIT SAVE OR RE-ANCHOR FAILED", Color.red);
                return false;
            }

            if (recordHistory)
            {
                PushEditHistory(new EditCommand
                {
                    Before = beforeHistory,
                    After = CaptureEditStates(editedPlacements),
                    IsMove = isMove
                });
            }

            await RemoveOrphanedPreviousAnchorsAsync(previousStates);
            return true;
        }

        private AnchorTarget FindAnchorTargetForPosition(
            Vector3 worldPosition,
            IReadOnlyList<AnchorTarget> createdTargets)
        {
            AnchorTarget nearest = null;
            var nearestDistanceSquared =
                SharedAnchorCoverageRadius * SharedAnchorCoverageRadius;
            foreach (var placement in placements)
            {
                if (placement?.AnchorRoot == null || placement.Anchor == null)
                    continue;

                var distanceSquared = Vector3.SqrMagnitude(
                    placement.AnchorRoot.transform.position - worldPosition);
                if (distanceSquared > nearestDistanceSquared)
                    continue;

                nearest = new AnchorTarget
                {
                    Anchor = placement.Anchor,
                    Root = placement.AnchorRoot
                };
                nearestDistanceSquared = distanceSquared;
            }

            foreach (var target in createdTargets)
            {
                var distanceSquared = Vector3.SqrMagnitude(
                    target.Root.transform.position - worldPosition);
                if (distanceSquared > nearestDistanceSquared)
                    continue;

                nearest = target;
                nearestDistanceSquared = distanceSquared;
            }
            return nearest;
        }

        private static void RestoreRuntimeStates(
            IReadOnlyList<PlacementRuntimeState> states)
        {
            foreach (var state in states)
            {
                var placement = state.Placement;
                placement.Root.transform.SetParent(
                    state.AnchorRoot.transform,
                    true);
                placement.Anchor = state.Anchor;
                placement.AnchorRoot = state.AnchorRoot;
                placement.Record.anchorId = state.AnchorId;
                placement.Record.surfaceKind = state.SurfaceKind;
                SetPlacementLocalPose(placement, state.LocalPose);
            }
        }

        private async Task RemoveCreatedAnchorTargetsAsync(
            IReadOnlyList<AnchorTarget> targets)
        {
            foreach (var target in targets)
            {
                if (!target.Created)
                    continue;
                try
                {
                    await anchorService.RemoveAsync(target.Anchor);
                }
                catch (Exception exception)
                {
                    Debug.LogWarning(
                        $"Replacement anchor rollback failed: " +
                        exception.Message);
                }
                if (target.Root != null)
                    Destroy(target.Root);
            }
        }

        private async Task RemoveOrphanedPreviousAnchorsAsync(
            IReadOnlyList<PlacementRuntimeState> previousStates)
        {
            var inspected = new HashSet<string>(
                StringComparer.OrdinalIgnoreCase);
            foreach (var state in previousStates)
            {
                if (!inspected.Add(state.AnchorId) ||
                    CountRuntimePlacementsForAnchor(state.AnchorId) > 0)
                {
                    continue;
                }

                try
                {
                    if (!await anchorService.RemoveAsync(state.Anchor))
                    {
                        Debug.LogWarning(
                            $"Old anchor cleanup was deferred: {state.AnchorId}.");
                    }
                }
                catch (Exception exception)
                {
                    Debug.LogWarning(
                        $"Old anchor cleanup failed for {state.AnchorId}: " +
                        exception.Message);
                }
                if (state.AnchorRoot != null)
                    Destroy(state.AnchorRoot);
            }
        }

        private bool HasEditedPlacementOverlap(
            IReadOnlyList<RuntimePlacement> editedPlacements)
        {
            for (var leftIndex = 0;
                 leftIndex < editedPlacements.Count;
                 leftIndex++)
            {
                var left = editedPlacements[leftIndex];
                if (left?.Root == null)
                    continue;

                for (var rightIndex = 0;
                     rightIndex < placements.Count;
                     rightIndex++)
                {
                    var right = placements[rightIndex];
                    if (ReferenceEquals(left, right) ||
                        right?.Root == null ||
                        right.Record.surfaceKind != left.Record.surfaceKind)
                    {
                        continue;
                    }

                    var leftTransform = left.Root.transform;
                    var rightTransform = right.Root.transform;
                    if (Vector3.Dot(
                            leftTransform.forward,
                            rightTransform.forward) <
                        CoplanarNormalDotThreshold)
                    {
                        continue;
                    }

                    var delta =
                        rightTransform.position - leftTransform.position;
                    if (Mathf.Abs(Vector3.Dot(
                            delta,
                            leftTransform.forward)) >
                        CoplanarDistanceTolerance)
                    {
                        continue;
                    }

                    var leftSize = GetBoundsSize(left);
                    var rightSize = GetBoundsSize(right);
                    var rightHalfX =
                        Mathf.Abs(Vector3.Dot(
                            rightTransform.right,
                            leftTransform.right)) *
                        rightSize.x * 0.5f +
                        Mathf.Abs(Vector3.Dot(
                            rightTransform.up,
                            leftTransform.right)) *
                        rightSize.y * 0.5f;
                    var rightHalfY =
                        Mathf.Abs(Vector3.Dot(
                            rightTransform.right,
                            leftTransform.up)) *
                        rightSize.x * 0.5f +
                        Mathf.Abs(Vector3.Dot(
                            rightTransform.up,
                            leftTransform.up)) *
                        rightSize.y * 0.5f;

                    if (Mathf.Abs(Vector3.Dot(
                                delta,
                                leftTransform.right)) <
                            leftSize.x * 0.5f + rightHalfX +
                            CollisionMargin &&
                        Mathf.Abs(Vector3.Dot(
                                delta,
                                leftTransform.up)) <
                            leftSize.y * 0.5f + rightHalfY +
                            CollisionMargin)
                    {
                        return true;
                    }
                }
            }

            return false;
        }

        private static void SetPlacementWorldPose(
            RuntimePlacement placement,
            Pose worldPose)
        {
            var anchorTransform = placement.AnchorRoot.transform;
            SetPlacementLocalPose(
                placement,
                new Pose(
                    anchorTransform.InverseTransformPoint(worldPose.position),
                    Quaternion.Inverse(anchorTransform.rotation) *
                    worldPose.rotation));
        }

        private static void SetPlacementLocalPose(
            RuntimePlacement placement,
            Pose localPose)
        {
            placement.Root.transform.localPosition = localPose.position;
            placement.Root.transform.localRotation = localPose.rotation;
            placement.Record.localOffset = SerializablePose.FromPose(localPose);
        }

        private static Vector3 GetBoundsSize(RuntimePlacement placement)
        {
            var contract = placement.Root.GetComponent<InstrumentGreyboxContract>();
            return InstrumentGreyboxSpecification.Get(
                contract != null ? contract.Kind : MockInstrumentKind.RoundMeter)
                .BoundsSize;
        }

        private void ToggleAimedSelection()
        {
            if (!TryResolvePlacedInteraction(out _, out _) ||
                activePlacement == null)
            {
                SetStatus("AIM AT AN INSTRUMENT TO SELECT", Color.yellow);
                return;
            }

            var target = activePlacement;
            activePlacement = null;
            editPlacementModifierChordActive = false;
            editMoveModifier = MovePlacementModifier.None;
            moveModifierAxisEngaged = false;
            ClearPendingLayout(clearSource: true);
            if (groupMoveSelection.Remove(target))
            {
                RemoveSelectionMarker(target);
                if (ReferenceEquals(groupMovePivot, target))
                {
                    groupMovePivot = groupMoveSelection.Count > 0
                        ? groupMoveSelection[0]
                        : null;
                }
                SetStatus(
                    $"DESELECTED | {groupMoveSelection.Count} SELECTED",
                    Color.white);
            }
            else
            {
                groupMoveSelection.Add(target);
                if (groupMovePivot == null)
                    groupMovePivot = target;
                SetStatus(
                    $"SELECTED | {groupMoveSelection.Count} TOTAL\n" +
                    "L-TRIGGER+GRIP TO MOVE",
                    new Color(1f, 0.75f, 0.15f));
            }
            groupMoveArmed = groupMoveSelection.Count > 0;
            ResetAlignmentCycle();
            RefreshSelectionMarkers();
            PulseHaptics();
        }

        private void CreateSelectionMarker(RuntimePlacement placement)
        {
            if (placement?.Root == null ||
                selectionMarkers.ContainsKey(placement))
            {
                return;
            }

            var size = GetBoundsSize(placement);
            var marker = new GameObject("[Edit] Selection");
            marker.transform.SetParent(placement.Root.transform, false);
            var line = marker.AddComponent<LineRenderer>();
            line.useWorldSpace = false;
            line.loop = true;
            line.positionCount = 4;
            var isFirstSelection =
                ReferenceEquals(placement, groupMovePivot);
            line.startWidth = isFirstSelection ? 0.014f : 0.008f;
            line.endWidth = line.startWidth;
            line.numCornerVertices = 2;
            line.numCapVertices = 2;
            var halfWidth = size.x * 0.5f + SelectionMarkerPadding;
            var halfHeight = size.y * 0.5f + SelectionMarkerPadding;
            var z = size.z * 0.5f + 0.012f;
            line.SetPosition(0, new Vector3(-halfWidth, -halfHeight, z));
            line.SetPosition(1, new Vector3(halfWidth, -halfHeight, z));
            line.SetPosition(2, new Vector3(halfWidth, halfHeight, z));
            line.SetPosition(3, new Vector3(-halfWidth, halfHeight, z));
            RuntimeMaterialUtility.ApplySharedUnlit(
                line,
                isFirstSelection
                    ? new Color(0.1f, 1f, 0.65f, 1f)
                    : new Color(1f, 0.65f, 0.05f, 1f));
            selectionMarkers.Add(placement, marker);
        }

        private bool UpdateMoveTargetMarkers(out string invalidReason)
        {
            invalidReason = string.Empty;
            if (!groupMoveArmed ||
                (pendingLayout == PendingLayout.None &&
                 !hasPlacementPose) ||
                groupMoveSelection.Count == 0)
            {
                SetMoveTargetMarkersVisible(false);
                invalidReason = "NO DESTINATION";
                return false;
            }

            while (moveTargetMarkers.Count < groupMoveSelection.Count)
                moveTargetMarkers.Add(CreateMoveTargetMarker());
            while (moveTargetMarkers.Count > groupMoveSelection.Count)
            {
                var lastIndex = moveTargetMarkers.Count - 1;
                Destroy(moveTargetMarkers[lastIndex]);
                moveTargetMarkers.RemoveAt(lastIndex);
            }

            IReadOnlyList<Pose> poses =
                pendingLayout != PendingLayout.None
                    ? pendingLayoutTargetPoses
                    : BuildGroupMoveTargetPoses();
            var targetIsValid =
                EvaluateGroupMoveTarget(poses, out invalidReason);
            for (var index = 0; index < moveTargetMarkers.Count; index++)
            {
                var marker = moveTargetMarkers[index];
                var placement = groupMoveSelection[index];
                if (marker == null ||
                    placement?.Root == null ||
                    index >= poses.Count)
                {
                    continue;
                }

                marker.SetActive(true);
                marker.transform.SetPositionAndRotation(
                    poses[index].position,
                    poses[index].rotation);
                var size = GetBoundsSize(placement);
                var halfWidth =
                    size.x * 0.5f + SelectionMarkerPadding;
                var halfHeight =
                    size.y * 0.5f + SelectionMarkerPadding;
                var line = marker.GetComponent<LineRenderer>();
                line.SetPosition(0, new Vector3(-halfWidth, -halfHeight, 0f));
                line.SetPosition(1, new Vector3(halfWidth, -halfHeight, 0f));
                line.SetPosition(2, new Vector3(halfWidth, halfHeight, 0f));
                line.SetPosition(3, new Vector3(-halfWidth, halfHeight, 0f));
                line.SetPosition(4, new Vector3(-halfWidth, -halfHeight, 0f));
                line.SetPosition(5, new Vector3(halfWidth, halfHeight, 0f));
                line.SetPosition(6, new Vector3(halfWidth, -halfHeight, 0f));
                line.SetPosition(7, new Vector3(-halfWidth, halfHeight, 0f));

                RuntimeMaterialUtility.SetColor(
                    line,
                    targetIsValid
                        ? new Color(0.1f, 1f, 0.65f, 1f)
                        : Color.red);
            }
            return targetIsValid;
        }

        private GameObject CreateMoveTargetMarker()
        {
            var marker = new GameObject("[Edit] Move Destination");
            marker.transform.SetParent(transform, false);
            var line = marker.AddComponent<LineRenderer>();
            line.useWorldSpace = false;
            line.positionCount = 8;
            line.startWidth = MoveTargetWidth;
            line.endWidth = MoveTargetWidth;
            line.numCornerVertices = 2;
            line.numCapVertices = 2;
            RuntimeMaterialUtility.ApplySharedUnlit(
                line,
                new Color(0.1f, 1f, 0.65f, 1f));
            return marker;
        }

        private void SetMoveTargetMarkersVisible(bool visible)
        {
            foreach (var marker in moveTargetMarkers)
            {
                if (marker != null && marker.activeSelf != visible)
                    marker.SetActive(visible);
            }
        }

        private void ClearMoveTargetMarkers()
        {
            foreach (var marker in moveTargetMarkers)
            {
                if (marker != null)
                    Destroy(marker);
            }
            moveTargetMarkers.Clear();
        }

        private void BuildSurfaceWireframes()
        {
            ClearSurfaceWireframes();
            if (currentRoom == null)
                return;

            foreach (var anchor in currentRoom.Anchors)
            {
                if (anchor == null)
                    continue;

                if (anchor.VolumeBounds.HasValue)
                {
                    surfaceWireframes.Add(
                        CreateVolumeWireframe(
                            anchor,
                            anchor.VolumeBounds.Value));
                    continue;
                }

                if (anchor.PlaneRect.HasValue &&
                    TryGetPlaneSurface(anchor.Label, out _))
                {
                    surfaceWireframes.Add(
                        CreatePlaneWireframe(
                            anchor,
                            anchor.PlaneRect.Value));
                }
            }

            SetSurfaceWireframesVisible(
                AppInteractionModePolicy.AllowsEditing(interactionMode));
        }

        private GameObject CreatePlaneWireframe(
            MRUKAnchor anchor,
            Rect rect)
        {
            var root = new GameObject(
                $"[Edit] Plane {anchor.Label}");
            root.transform.SetParent(anchor.transform, false);
            var line = CreateSurfaceWireframeRenderer(
                root,
                new Color(0.10f, 0.85f, 1f, 0.8f));
            line.loop = true;
            line.positionCount = 4;
            line.SetPosition(
                0,
                new Vector3(rect.xMin, rect.yMin, 0f));
            line.SetPosition(
                1,
                new Vector3(rect.xMax, rect.yMin, 0f));
            line.SetPosition(
                2,
                new Vector3(rect.xMax, rect.yMax, 0f));
            line.SetPosition(
                3,
                new Vector3(rect.xMin, rect.yMax, 0f));
            return root;
        }

        private GameObject CreateVolumeWireframe(
            MRUKAnchor anchor,
            Bounds bounds)
        {
            var root = new GameObject(
                $"[Edit] Volume {anchor.Label}");
            root.transform.SetParent(anchor.transform, false);
            var line = CreateSurfaceWireframeRenderer(
                root,
                new Color(0.75f, 0.35f, 1f, 0.8f));
            var min = bounds.min;
            var max = bounds.max;
            var b00 = new Vector3(min.x, min.y, min.z);
            var b10 = new Vector3(max.x, min.y, min.z);
            var b11 = new Vector3(max.x, max.y, min.z);
            var b01 = new Vector3(min.x, max.y, min.z);
            var t00 = new Vector3(min.x, min.y, max.z);
            var t10 = new Vector3(max.x, min.y, max.z);
            var t11 = new Vector3(max.x, max.y, max.z);
            var t01 = new Vector3(min.x, max.y, max.z);
            var points = new[]
            {
                b00, b10, b11, b01, b00,
                t00, t10, t11, t01, t00,
                t01, b01, b11, t11, t10, b10
            };
            line.positionCount = points.Length;
            line.SetPositions(points);
            return root;
        }

        private static LineRenderer CreateSurfaceWireframeRenderer(
            GameObject root,
            Color color)
        {
            var line = root.AddComponent<LineRenderer>();
            line.useWorldSpace = false;
            line.startWidth = SurfaceWireframeWidth;
            line.endWidth = SurfaceWireframeWidth;
            line.numCornerVertices = 2;
            line.numCapVertices = 2;
            line.shadowCastingMode =
                UnityEngine.Rendering.ShadowCastingMode.Off;
            line.receiveShadows = false;
            RuntimeMaterialUtility.ApplySharedUnlit(line, color);
            return line;
        }

        private void SetSurfaceWireframesVisible(bool visible)
        {
            foreach (var wireframe in surfaceWireframes)
            {
                if (wireframe != null &&
                    wireframe.activeSelf != visible)
                {
                    wireframe.SetActive(visible);
                }
            }
        }

        private void ClearSurfaceWireframes()
        {
            foreach (var wireframe in surfaceWireframes)
            {
                if (wireframe != null)
                    Destroy(wireframe);
            }
            surfaceWireframes.Clear();
        }

        private void RemoveSelectionMarker(RuntimePlacement placement)
        {
            if (!selectionMarkers.TryGetValue(placement, out var marker))
                return;

            selectionMarkers.Remove(placement);
            if (marker != null)
                Destroy(marker);
        }

        private void RefreshSelectionMarkers()
        {
            foreach (var marker in selectionMarkers.Values)
            {
                if (marker != null)
                    Destroy(marker);
            }
            selectionMarkers.Clear();
            foreach (var placement in groupMoveSelection)
                CreateSelectionMarker(placement);
        }

        private List<PlacementEditState> CaptureEditStates(
            IReadOnlyList<RuntimePlacement> editedPlacements)
        {
            var states =
                new List<PlacementEditState>(editedPlacements.Count);
            foreach (var placement in editedPlacements)
            {
                states.Add(new PlacementEditState
                {
                    PlacementId = placement.Record.placementId,
                    WorldPose = new Pose(
                        placement.Root.transform.position,
                        placement.Root.transform.rotation),
                    SurfaceKind = placement.Record.surfaceKind
                });
            }
            return states;
        }

        private void PushEditHistory(EditCommand command)
        {
            if (undoHistory.Count >= MaximumEditHistory)
            {
                var newestFirst = undoHistory.ToArray();
                undoHistory.Clear();
                var retained = Mathf.Min(
                    newestFirst.Length,
                    MaximumEditHistory - 1);
                for (var index = retained - 1; index >= 0; index--)
                    undoHistory.Push(newestFirst[index]);
            }
            undoHistory.Push(command);
            redoHistory.Clear();
        }

        private void ClearEditHistory()
        {
            undoHistory.Clear();
            redoHistory.Clear();
        }

        private async void UndoLastEdit()
        {
            if (undoHistory.Count == 0)
            {
                SetStatus("NOTHING TO UNDO", Color.yellow);
                return;
            }

            operationInProgress = true;
            try
            {
                var command = undoHistory.Peek();
                if (!await ApplyEditStatesAsync(command.Before))
                    return;

                undoHistory.Pop();
                redoHistory.Push(command);
                ResetAlignmentCycle();
                RefreshSelectionMarkers();
                PulseHaptics();
                SetStatus(
                    $"UNDO | {undoHistory.Count} STEP(S) REMAIN",
                    Color.green);
            }
            finally
            {
                operationInProgress = false;
            }
        }

        private async void RedoLastEdit()
        {
            if (redoHistory.Count == 0)
            {
                SetStatus("NOTHING TO REDO", Color.yellow);
                return;
            }

            operationInProgress = true;
            try
            {
                var command = redoHistory.Peek();
                if (!await ApplyEditStatesAsync(command.After))
                    return;

                redoHistory.Pop();
                undoHistory.Push(command);
                ResetAlignmentCycle();
                RefreshSelectionMarkers();
                PulseHaptics();
                SetStatus(
                    $"REDO | {redoHistory.Count} STEP(S) REMAIN",
                    Color.green);
            }
            finally
            {
                operationInProgress = false;
            }
        }

        private async Task<bool> ApplyEditStatesAsync(
            IReadOnlyList<PlacementEditState> states)
        {
            var editedPlacements =
                new List<RuntimePlacement>(states.Count);
            var poses = new List<Pose>(states.Count);
            var surfaces = new List<int>(states.Count);
            foreach (var state in states)
            {
                var placement = FindPlacementById(state.PlacementId);
                if (placement == null)
                {
                    SetStatus(
                        "UNDO/REDO BLOCKED: PLACEMENT MISSING",
                        Color.yellow);
                    return false;
                }
                editedPlacements.Add(placement);
                poses.Add(state.WorldPose);
                surfaces.Add(state.SurfaceKind);
            }
            return await ApplyEditedWorldPosesAsync(
                editedPlacements,
                poses,
                surfaces,
                recordHistory: false);
        }

        private RuntimePlacement FindPlacementById(string placementId)
        {
            foreach (var placement in placements)
            {
                if (string.Equals(
                        placement.Record.placementId,
                        placementId,
                        StringComparison.Ordinal))
                {
                    return placement;
                }
            }
            return null;
        }

        private void ClearGroupMoveSelection()
        {
            ClearPendingLayout(clearSource: true);
            foreach (var marker in selectionMarkers.Values)
            {
                if (marker != null)
                    Destroy(marker);
            }
            selectionMarkers.Clear();
            groupMoveSelection.Clear();
            groupMovePivot = null;
            groupMoveArmed = false;
            editPlacementModifierChordActive = false;
            editMoveModifier = MovePlacementModifier.None;
            moveModifierAxisEngaged = false;
            ResetAlignmentCycle();
            ClearMoveTargetMarkers();
        }

        private bool TryResolvePlacedInteraction(
            out MockInstrumentInteraction interaction,
            out InstrumentInteractionHitTest.Reach reach)
        {
            interaction = null;
            reach = InstrumentInteractionHitTest.Reach.None;
            activePlacement = null;
            if (placements.Count == 0 || leftAimAnchor == null)
                return false;

            interactionCandidates.Clear();
            for (var index = 0; index < placements.Count; index++)
            {
                if (placements[index].Interaction != null)
                    interactionCandidates.Add(placements[index].Interaction);
            }
            if (!InstrumentInteractionResolver.TryResolveBest(
                    interactionCandidates,
                    leftAimAnchor.position,
                    leftAimAnchor.forward,
                    DirectTipOffset,
                    DirectContactRadius,
                    MaxInteractionDistance,
                    out interaction,
                    out reach))
            {
                return false;
            }

            activePlacement = FindPlacement(interaction);
            return true;
        }

        private bool TryResolveOperationInteraction(
            Transform controllerAnchor,
            OperationResolveMode mode,
            out MockInstrumentInteraction interaction,
            out RuntimePlacement placement,
            out InstrumentInteractionHitTest.Reach reach)
        {
            interaction = null;
            placement = null;
            reach = InstrumentInteractionHitTest.Reach.None;
            if (placements.Count == 0 || controllerAnchor == null)
                return false;

            if (mode == OperationResolveMode.GripMotion)
            {
                return TryResolveGripMotionInteraction(
                    controllerAnchor,
                    out interaction,
                    out placement,
                    out reach);
            }

            interactionCandidates.Clear();
            for (var index = 0; index < placements.Count; index++)
            {
                var candidatePlacement = placements[index];
                var candidate = candidatePlacement?.Interaction;
                if (candidate == null)
                    continue;

                var kind = GetPlacementKind(candidatePlacement);
                var accepts = mode switch
                {
                    OperationResolveMode.DirectionalStep =>
                        MockInstrumentCatalog.SupportsDirectionalStep(kind),
                    OperationResolveMode.StickControl =>
                        MockInstrumentCatalog.SupportsStickControl(kind),
                    OperationResolveMode.ContactButton =>
                        MockInstrumentCatalog.UsesContactPress(kind),
                    OperationResolveMode.BeamButton =>
                        MockInstrumentCatalog.UsesContactPress(kind),
                    _ => true
                };
                if (accepts)
                    interactionCandidates.Add(candidate);
            }

            if (!InstrumentInteractionResolver.TryResolveBest(
                    interactionCandidates,
                    controllerAnchor.position,
                    controllerAnchor.forward,
                    DirectTipOffset,
                    DirectContactRadius,
                    MaxInteractionDistance,
                    out interaction,
                    out reach))
            {
                return false;
            }

            placement = FindPlacement(interaction);
            return placement != null;
        }

        private bool TryResolveGripMotionInteraction(
            Transform controllerAnchor,
            out MockInstrumentInteraction interaction,
            out RuntimePlacement placement,
            out InstrumentInteractionHitTest.Reach reach)
        {
            interaction = null;
            placement = null;
            reach = InstrumentInteractionHitTest.Reach.None;
            if (controllerAnchor == null)
                return false;

            var direction = controllerAnchor.forward.normalized;
            if (direction.sqrMagnitude < 0.0001f)
                return false;

            var controllerTip =
                controllerAnchor.position +
                direction * DirectTipOffset;
            var nearestDistanceSquared = float.PositiveInfinity;
            foreach (var candidatePlacement in placements)
            {
                var candidate = candidatePlacement?.Interaction;
                if (candidate?.Motion == null)
                    continue;

                var kind = GetPlacementKind(candidatePlacement);
                if (!MockInstrumentCatalog.SupportsDirectionalStep(kind) ||
                    MockInstrumentCatalog.IsSoundModule(kind))
                    continue;

                float distanceSquared;
                if (kind == MockInstrumentKind.ThrottleLever ||
                    kind == MockInstrumentKind.Lever ||
                    kind == MockInstrumentKind.PowerSlider)
                {
                    if (candidate.Motion.MovingPart == null)
                        continue;
                    distanceSquared = DistanceSquaredToMovingGrip(
                        candidate.Motion.MovingPart,
                        controllerTip,
                        kind switch
                        {
                            MockInstrumentKind.ThrottleLever =>
                                ThrottleGripContactPadding,
                            MockInstrumentKind.PowerSlider =>
                                PowerSliderGripContactPadding,
                            _ => LeverGripContactPadding
                        });
                }
                else
                {
                    var collider = candidate.InteractionCollider;
                    if (collider == null ||
                        !collider.enabled ||
                        !collider.gameObject.activeInHierarchy)
                    {
                        continue;
                    }
                    distanceSquared = (
                        collider.ClosestPoint(controllerTip) -
                        controllerTip).sqrMagnitude;
                    if (distanceSquared >
                        DirectContactRadius * DirectContactRadius)
                    {
                        continue;
                    }
                }

                if (float.IsPositiveInfinity(distanceSquared) ||
                    distanceSquared >= nearestDistanceSquared)
                {
                    continue;
                }

                nearestDistanceSquared = distanceSquared;
                interaction = candidate;
                placement = candidatePlacement;
                reach = InstrumentInteractionHitTest.Reach.Direct;
            }
            return interaction != null;
        }

        private static float DistanceSquaredToMovingGrip(
            Transform motionPivot,
            Vector3 worldPoint,
            float contactPadding)
        {
            var renderers =
                motionPivot.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0)
                return float.PositiveInfinity;

            var bounds = renderers[0].bounds;
            for (var index = 1; index < renderers.Length; index++)
                bounds.Encapsulate(renderers[index].bounds);
            bounds.Expand(contactPadding * 2f);

            return bounds.Contains(worldPoint)
                ? 0f
                : float.PositiveInfinity;
        }

        private void UpdateContactButtons()
        {
            var previousRight = rightOperationHand.ContactButton;
            var previousLeft = leftOperationHand.ContactButton;
            var nextRight = ResolveContactButton(rightControllerAnchor);
            var nextLeft = ResolveContactButton(leftControllerAnchor);

            rightOperationHand.ContactButton = nextRight;
            leftOperationHand.ContactButton = nextLeft;

            ReleaseContactButtonIfUnused(
                previousRight,
                nextRight,
                nextLeft);
            ReleaseContactButtonIfUnused(
                previousLeft,
                nextRight,
                nextLeft);
            PressContactButtonIfNew(
                nextRight,
                previousRight,
                previousLeft,
                rightOperationHand);
            PressContactButtonIfNew(
                nextLeft,
                previousRight,
                previousLeft,
                leftOperationHand);
        }

        private void UpdateBeamButton(
            HandOperationState hand,
            HandOperationState otherHand,
            Transform aimAnchor,
            float triggerValue)
        {
            if (triggerValue <= TriggerReleaseThreshold)
            {
                hand.BeamTriggerEngaged = false;
                ReleaseBeamButton(hand, otherHand);
                return;
            }

            if (triggerValue < TriggerPressThreshold ||
                hand.BeamTriggerEngaged)
            {
                return;
            }

            hand.BeamTriggerEngaged = true;
            if (hand.ContactButton != null ||
                hand.GripInteraction != null ||
                hand.StickInteraction != null ||
                !TryResolveOperationInteraction(
                    aimAnchor,
                    OperationResolveMode.BeamButton,
                    out var interaction,
                    out var placement,
                    out var reach) ||
                reach != InstrumentInteractionHitTest.Reach.Ray ||
                IsInteractionHeldByOtherHand(interaction, otherHand))
            {
                return;
            }

            hand.BeamButton = interaction;
            interaction.SetPressed(true);
            PulseHaptics(hand.Controller);
            operationStepNoticeUntil = Time.unscaledTime + 0.5f;
            SetStatus(
                $"{hand.Label} BEAM TRIGGER PRESS | " +
                $"{MockInstrumentCatalog.GetDisplayName(GetPlacementKind(placement))}",
                Color.green);
        }

        private void ReleaseBeamButton(
            HandOperationState hand,
            HandOperationState otherHand)
        {
            var interaction = hand.BeamButton;
            hand.BeamButton = null;
            if (interaction == null)
                return;

            if (!ReferenceEquals(interaction, hand.ContactButton) &&
                !ReferenceEquals(interaction, otherHand.ContactButton) &&
                !ReferenceEquals(interaction, otherHand.BeamButton))
            {
                interaction.SetPressed(false);
            }
            SaveInteractionState(interaction);
        }

        private MockInstrumentInteraction ResolveContactButton(
            Transform controllerAnchor)
        {
            if (!TryResolveOperationInteraction(
                    controllerAnchor,
                    OperationResolveMode.ContactButton,
                    out var interaction,
                    out _,
                    out var reach) ||
                reach != InstrumentInteractionHitTest.Reach.Direct)
            {
                return null;
            }
            return interaction;
        }

        private void ReleaseContactButtonIfUnused(
            MockInstrumentInteraction previous,
            MockInstrumentInteraction nextRight,
            MockInstrumentInteraction nextLeft)
        {
            if (previous == null ||
                ReferenceEquals(previous, nextRight) ||
                ReferenceEquals(previous, nextLeft))
            {
                return;
            }

            previous.SetPressed(false);
            SaveInteractionState(previous);
        }

        private void PressContactButtonIfNew(
            MockInstrumentInteraction next,
            MockInstrumentInteraction previousRight,
            MockInstrumentInteraction previousLeft,
            HandOperationState hand)
        {
            if (next == null ||
                ReferenceEquals(next, previousRight) ||
                ReferenceEquals(next, previousLeft))
            {
                return;
            }

            next.SetPressed(true);
            PulseHaptics(hand.Controller);
            var placement = FindPlacement(next);
            var displayName = MockInstrumentCatalog.GetDisplayName(
                GetPlacementKind(placement));
            SetStatus(
                $"{hand.Label} CONTACT PRESS | " +
                $"{displayName}",
                Color.green);
        }

        private static MockInstrumentKind GetPlacementKind(
            RuntimePlacement placement)
        {
            var contract = placement?.Root != null
                ? placement.Root.GetComponent<InstrumentGreyboxContract>()
                : null;
            return contract != null
                ? contract.Kind
                : MockInstrumentKind.RoundMeter;
        }

        private void ReleaseActiveInteraction()
        {
            ReleaseOperationInteractions();
            activePlacement = null;
        }

        private void ReleaseOperationInteractions()
        {
            rightOperationHand.PendingStepDirection = 0;
            leftOperationHand.PendingStepDirection = 0;
            rightOperationHand.ResetChordEngaged = false;
            leftOperationHand.ResetChordEngaged = false;
            SaveStickInteraction(rightOperationHand);
            SaveStickInteraction(leftOperationHand);
            ReleaseGripInteraction(rightOperationHand);
            ReleaseGripInteraction(leftOperationHand);

            var rightContact = rightOperationHand.ContactButton;
            var leftContact = leftOperationHand.ContactButton;
            var rightBeam = rightOperationHand.BeamButton;
            var leftBeam = leftOperationHand.BeamButton;
            rightOperationHand.ContactButton = null;
            leftOperationHand.ContactButton = null;
            rightOperationHand.BeamButton = null;
            leftOperationHand.BeamButton = null;
            rightOperationHand.BeamTriggerEngaged = false;
            leftOperationHand.BeamTriggerEngaged = false;
            var pressedInteractions = new[]
            {
                rightContact,
                leftContact,
                rightBeam,
                leftBeam
            };
            for (var index = 0; index < pressedInteractions.Length; index++)
            {
                var interaction = pressedInteractions[index];
                if (interaction == null)
                    continue;
                var alreadyReleased = false;
                for (var previous = 0; previous < index; previous++)
                {
                    if (ReferenceEquals(
                            interaction,
                            pressedInteractions[previous]))
                    {
                        alreadyReleased = true;
                        break;
                    }
                }
                if (alreadyReleased)
                    continue;
                interaction.SetPressed(false);
                SaveInteractionState(interaction);
            }

            OVRInput.SetControllerVibration(
                0f,
                0f,
                OVRInput.Controller.RTouch);
            OVRInput.SetControllerVibration(
                0f,
                0f,
                OVRInput.Controller.LTouch);
            hapticStopTime = 0f;
            leftHapticStopTime = 0f;
        }

        private void SaveStickInteraction(HandOperationState hand)
        {
            if (hand.StickInteraction != null)
            {
                hand.StickInteraction.EndStickControl();
                SaveInteractionState(hand.StickInteraction);
            }
            hand.StickInteraction = null;
            hand.StickXEngaged = false;
            hand.StickTargetInitialized = false;
        }

        private void ReleaseGripInteraction(HandOperationState hand)
        {
            if (hand.GripInteraction != null)
                SaveInteractionState(hand.GripInteraction);
            hand.GripInteraction = null;
            hand.GripPlacement = null;
        }

        private void SaveInteractionState(
            MockInstrumentInteraction interaction)
        {
            if (interaction == null)
                return;

            var placement = FindPlacement(interaction);
            if (placement == null)
                return;

            var previousValue = placement.Record.normalizedValue;
            var previousParameters = placement.Record.parameterSettings != null
                ? placement.Record.parameterSettings.ConvertAll(
                    setting => setting?.Clone())
                : null;
            placement.Record.normalizedValue = interaction.NormalizedValue;
            var kind = GetPlacementKind(placement);
            placement.Record.parameterSettings =
                AdjustableParameterPolicy.NormalizeSettings(
                    kind,
                    placement.Record.parameterSettings,
                    interaction.NormalizedValue);
            if (placement.Record.parameterSettings.Count > 0)
            {
                placement.Record.parameterSettings[0].value =
                    placement.AudioModule != null
                        ? placement.AudioModule.PrimaryParameterValue
                        : interaction.OutputValue;
            }
            if (!SavePlacementDocument())
            {
                placement.Record.normalizedValue = previousValue;
                placement.Record.parameterSettings = previousParameters;
                Debug.LogError(
                    $"[Placement] State save failed for {placement.Record.placementId}.");
            }
        }

        private void PulseHaptics()
        {
            PulseHaptics(OVRInput.Controller.RTouch);
        }

        private void PulseHaptics(OVRInput.Controller controller)
        {
            OVRInput.SetControllerVibration(
                0.08f,
                0.25f,
                controller);
            if (controller == OVRInput.Controller.LTouch)
                leftHapticStopTime = Time.unscaledTime + HapticDuration;
            else
                hapticStopTime = Time.unscaledTime + HapticDuration;
        }

        private void UpdateHaptics()
        {
            if (hapticStopTime > 0f &&
                Time.unscaledTime >= hapticStopTime)
            {
                OVRInput.SetControllerVibration(
                    0f,
                    0f,
                    OVRInput.Controller.RTouch);
                hapticStopTime = 0f;
            }
            if (leftHapticStopTime > 0f &&
                Time.unscaledTime >= leftHapticStopTime)
            {
                OVRInput.SetControllerVibration(
                    0f,
                    0f,
                    OVRInput.Controller.LTouch);
                leftHapticStopTime = 0f;
            }
        }

        private void UpdateSelection(
            Vector2 objectAxis,
            Vector2 themeAxis)
        {
            var objectMagnitude = Mathf.Max(
                Mathf.Abs(objectAxis.x),
                Mathf.Abs(objectAxis.y));
            if (objectMagnitude <= SelectionReleaseThreshold)
                selectionAxisEngaged = false;

            var themeMagnitude = Mathf.Abs(themeAxis.x);
            if (themeMagnitude <= SelectionReleaseThreshold)
                themeAxisEngaged = false;

            if (operationInProgress)
                return;

            if (!selectionAxisEngaged &&
                objectMagnitude >= SelectionThreshold)
            {
                selectionAxisEngaged = true;
                if (Mathf.Abs(objectAxis.x) >=
                    Mathf.Abs(objectAxis.y))
                {
                    SetSelectedKind(
                        MockInstrumentCatalog.Cycle(
                            selectedKind,
                            objectAxis.x < 0f ? -1 : 1));
                }
                else
                {
                    SetSelectedKind(
                        MockInstrumentCatalog.JumpCategory(
                            selectedKind,
                            objectAxis.y > 0f ? -1 : 1));
                }
            }

            if (!themeAxisEngaged &&
                themeMagnitude >= SelectionThreshold)
            {
                themeAxisEngaged = true;
                SetSelectedTheme(
                    MockInstrumentThemeCatalog.Cycle(
                        selectedTheme,
                        themeAxis.x < 0f ? -1 : 1));
            }
        }

        private void SetSelectedKind(MockInstrumentKind kind)
        {
            if (selectedKind == kind)
                return;

            selectedKind = kind;
            if (preview != null)
                MockInstrumentFactory.Destroy(preview);
            preview = null;
        }

        private void SetSelectedTheme(MockInstrumentTheme theme)
        {
            theme = MockInstrumentThemeCatalog.Normalize(theme);
            if (selectedTheme == theme)
                return;

            selectedTheme = theme;
            MockInstrumentThemePreference.Save(selectedTheme);
            if (preview != null)
                MockInstrumentFactory.ApplyTheme(preview, selectedTheme, preview: true);
            for (var index = 0; index < placements.Count; index++)
            {
                var placement = placements[index];
                MockInstrumentFactory.ApplyTheme(placement.Root, selectedTheme);
                RefreshPlacementRuntimeBindings(placement);
            }
            UpdateSignalGraph();
            SetStatus(
                $"THEME: {MockInstrumentThemeCatalog.GetDisplayName(selectedTheme)}\n" +
                $"{CurrentRoomPlacementCount():00}/" +
                $"{PlacementDocument.MaximumActivePlacements:00} IN ROOM",
                Color.green);
        }

        private static void RefreshPlacementRuntimeBindings(
            RuntimePlacement placement)
        {
            if (placement?.Root == null)
                return;

            var contract = placement.Root
                .GetComponent<InstrumentGreyboxContract>();
            placement.Interaction = contract?.InstrumentInteraction;
            placement.SignalMonitor = placement.Root
                .GetComponentInChildren<SignalMonitorView>(true);
            placement.WindowPanelGraphic = placement.Root
                .GetComponentInChildren<
                    WindowPanelGraphicsPrototypeView>(true);
        }

        private async void PlaceInstrument()
        {
            if (CurrentRoomPlacementCount() >=
                PlacementDocument.MaximumActivePlacements)
            {
                SetStatus(
                    $"ROOM PLACEMENT LIMIT " +
                    $"{PlacementDocument.MaximumActivePlacements}/" +
                    $"{PlacementDocument.MaximumActivePlacements}",
                    Color.yellow);
                return;
            }
            if (StoredPlacementCount() >=
                PlacementDocument.MaximumStoredPlacements)
            {
                SetStatus(
                    $"ALL-ROOM STORAGE LIMIT " +
                    $"{PlacementDocument.MaximumStoredPlacements}/" +
                    $"{PlacementDocument.MaximumStoredPlacements}",
                    Color.yellow);
                return;
            }

            ReleaseActiveInteraction();
            operationInProgress = true;
            SetPreviewVisible(false);
            SetStatus("SAVING SPATIAL ANCHOR...");

            GameObject newAnchorRoot = null;
            GameObject newInstrument = null;
            AnchorRecord newAnchor = null;
            PlacementRecord newRecord = null;
            var ownsNewAnchor = false;
            try
            {
                var sharedPlacement = FindReusableAnchorPlacement(
                    currentPlacementPose.position);
                if (sharedPlacement != null)
                {
                    newAnchorRoot = sharedPlacement.AnchorRoot;
                    newAnchor = sharedPlacement.Anchor;
                }
                else
                {
                    ownsNewAnchor = true;
                    newAnchorRoot = new GameObject(
                        $"[Anchor] {MockInstrumentCatalog.GetDisplayName(selectedKind)}");
                    newAnchorRoot.transform.SetPositionAndRotation(
                        currentPlacementPose.position,
                        currentPlacementPose.rotation);
                }

                newInstrument = MockInstrumentFactory.Create(
                    selectedKind,
                    currentPlacementPose,
                    theme: selectedTheme);
                newInstrument.transform.SetParent(newAnchorRoot.transform, true);
                if (ownsNewAnchor)
                {
                    newAnchor = await anchorService.CreateAsync(
                        newAnchorRoot,
                        currentSurface);
                }
                var contract = newInstrument
                    .GetComponent<InstrumentGreyboxContract>();
                var interaction = contract.InstrumentInteraction;
                var localPose = new Pose(
                    newInstrument.transform.localPosition,
                    newInstrument.transform.localRotation);
                newRecord = new PlacementRecord
                {
                    placementId = Guid.NewGuid().ToString("D"),
                    anchorId = newAnchor.Id,
                    roomId = GetRoomId(currentRoom),
                    instrumentTypeId = MockInstrumentCatalog.GetTypeId(selectedKind),
                    surfaceKind = (int)currentSurface,
                    localOffset = SerializablePose.FromPose(localPose),
                    normalizedValue = interaction.NormalizedValue,
                    lifecycle = (int)PlacementLifecycle.Active
                };
                newRecord.parameterSettings =
                    AdjustableParameterPolicy.NormalizeSettings(
                        selectedKind,
                        null,
                        interaction.NormalizedValue);
                placementDocument.placements.Add(newRecord);
                if (!SavePlacementDocument())
                {
                    placementDocument.placements.Remove(newRecord);
                    throw new InvalidOperationException(
                        "Spatial anchor was saved but placement JSON could not be committed.");
                }

                var runtimePlacement = new RuntimePlacement
                {
                    Record = newRecord,
                    Anchor = newAnchor,
                    AnchorRoot = newAnchorRoot,
                    Root = newInstrument,
                    Contract = contract,
                    Interaction = interaction,
                    Audio = newInstrument.GetComponentInChildren<
                        InstrumentAudioController>(true),
                    AudioModule = newInstrument.GetComponentInChildren<
                        ModularAudioModuleRuntime>(true),
                    AudioGraphPlayer = newInstrument.GetComponentInChildren<
                        ModularAudioGraphPlayer>(true),
                    SignalMonitor = newInstrument
                        .GetComponentInChildren<SignalMonitorView>(true),
                    WindowPanelSignal = selectedKind ==
                                        MockInstrumentKind.WindowPanel
                        ? new WindowPanelSignalRuntime()
                        : null,
                    WindowPanelGraphic = newInstrument
                        .GetComponentInChildren<
                            WindowPanelGraphicsPrototypeView>(true)
                };
                ApplyAudioParameters(runtimePlacement);
                placements.Add(runtimePlacement);
                ClearEditHistory();
                Debug.Log(
                    $"[Placement] Committed {newRecord.placementId} " +
                    $"{newRecord.instrumentTypeId} anchor {newRecord.anchorId} " +
                    $"shared={!ownsNewAnchor}.");
                newInstrument = null;
                newAnchorRoot = null;
                newAnchor = null;
                newRecord = null;

                SetStatus(
                    $"SAVED {currentSurface.ToString().ToUpperInvariant()} | " +
                    $"{CurrentRoomPlacementCount():00}/" +
                    $"{PlacementDocument.MaximumActivePlacements:00} IN ROOM",
                    Color.green);
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                if (newRecord != null)
                    placementDocument.placements.Remove(newRecord);
                if (ownsNewAnchor && newAnchor != null)
                {
                    try
                    {
                        await anchorService.RemoveAsync(newAnchor);
                    }
                    catch (Exception cleanupException)
                    {
                        Debug.LogWarning(
                            $"New anchor rollback failed: {cleanupException.Message}");
                    }
                }
                if (ownsNewAnchor && newAnchorRoot != null)
                    Destroy(newAnchorRoot);
                else if (newInstrument != null)
                    MockInstrumentFactory.Destroy(newInstrument);
                SetStatus("ANCHOR SAVE FAILED", Color.red);
            }
            finally
            {
                operationInProgress = false;
            }
        }

        private void DeleteAimedInstrument()
        {
            RuntimePlacement target = null;
            if (TryResolvePlacedInteraction(out _, out _))
                target = activePlacement;

            activePlacement = null;
            if (target == null)
            {
                SetStatus("AIM AT AN INSTRUMENT TO DELETE", Color.yellow);
                return;
            }
            DeletePlacement(target);
        }

        private void ReplaceAimedInstrument()
        {
            RuntimePlacement target = null;
            if (TryResolvePlacedInteraction(out _, out _))
                target = activePlacement;
            activePlacement = null;
            if (target == null)
            {
                SetStatus(
                    "AIM AT AN INSTRUMENT TO RE-PLACE",
                    Color.yellow);
                return;
            }

            var kind = GetPlacementKind(target);
            SetSelectedKind(kind);
            DeletePlacement(target);
        }

        private async void DeletePlacement(RuntimePlacement target)
        {
            ReleaseActiveInteraction();
            ClearGroupMoveSelection();
            operationInProgress = true;
            SetStatus("DELETING INSTRUMENT...");
            var removesSharedAnchor =
                CountRuntimePlacementsForAnchor(target.Record.anchorId) == 1;

            try
            {
                target.Record.lifecycle = (int)PlacementLifecycle.PendingDelete;
                if (!SavePlacementDocument())
                {
                    target.Record.lifecycle = (int)PlacementLifecycle.Active;
                    throw new InvalidOperationException(
                        "Could not persist pending-delete placement state.");
                }
                Debug.Log(
                    $"[Placement] Pending delete committed for " +
                    $"{target.Record.placementId} {target.Record.instrumentTypeId} " +
                    $"anchor {target.Record.anchorId}.");

                if (removesSharedAnchor &&
                    !await anchorService.RemoveAsync(target.Anchor))
                {
                    throw new InvalidOperationException("Spatial anchor erase failed.");
                }

                placements.Remove(target);
                placementDocument.connections?.RemoveAll(
                    connection =>
                        connection.sourcePlacementId ==
                            target.Record.placementId ||
                        connection.targetPlacementId ==
                            target.Record.placementId);
                placementDocument.audioPatchConnections?.RemoveAll(
                    connection =>
                        connection.sourcePlacementId ==
                            target.Record.placementId ||
                        connection.targetPlacementId ==
                            target.Record.placementId);
                ClearEditHistory();
                var recordRemoved = placementDocument.placements.Remove(target.Record);
                var removalSaved = SavePlacementDocument();
                Debug.Log(
                    $"[Placement] Delete finalized for {target.Record.placementId}: " +
                    $"recordRemoved={recordRemoved}, saved={removalSaved}.");
                if (!removalSaved)
                {
                    Debug.LogWarning(
                        removesSharedAnchor
                            ? "Anchor was erased; pending-delete record remains for recovery."
                            : "Shared anchor was retained; pending-delete record remains for recovery.");
                }
                if (removesSharedAnchor && target.AnchorRoot != null)
                    Destroy(target.AnchorRoot);
                else
                    MockInstrumentFactory.Destroy(target.Root);
                SetStatus(
                    $"INSTRUMENT DELETED | {placements.Count:00}/" +
                    $"{PlacementDocument.MaximumActivePlacements:00}",
                    Color.green);
            }
            catch (Exception exception)
            {
                target.Record.lifecycle = (int)PlacementLifecycle.Active;
                SavePlacementDocument();
                Debug.LogException(exception);
                SetStatus("DELETE FAILED", Color.red);
            }
            finally
            {
                operationInProgress = false;
            }
        }

        private async Task RestorePlacedInstrumentsAsync()
        {
            var roomId = GetRoomId(currentRoom);
            var recordsToRestore = new List<PlacementRecord>();
            var pendingDeletes = new List<PlacementRecord>();
            var anchorIds = new List<string>();
            var uniqueAnchorIds = new HashSet<string>(
                StringComparer.OrdinalIgnoreCase);
            foreach (var record in placementDocument.placements)
            {
                if (!BelongsToRoom(record, roomId))
                    continue;

                if (record.lifecycle == (int)PlacementLifecycle.PendingDelete)
                    pendingDeletes.Add(record);
                else if (record.lifecycle == (int)PlacementLifecycle.Active ||
                         record.lifecycle == (int)PlacementLifecycle.Unavailable)
                    recordsToRestore.Add(record);
                else
                    continue;
                if (uniqueAnchorIds.Add(record.anchorId))
                    anchorIds.Add(record.anchorId);
            }
            if (anchorIds.Count == 0)
                return;

            SetStatus($"RESTORING {anchorIds.Count} SPATIAL ANCHOR(S)...");
            var loadedAnchors = await anchorService.LoadAsync(anchorIds);
            var anchorsById = new Dictionary<string, AnchorRecord>(
                StringComparer.OrdinalIgnoreCase);
            foreach (var anchor in loadedAnchors)
                anchorsById[anchor.Id] = anchor;

            var documentChanged = false;
            foreach (var record in pendingDeletes)
            {
                if (HasRestorableRecordForAnchor(record.anchorId))
                {
                    placementDocument.placements.Remove(record);
                    documentChanged = true;
                    Debug.Log(
                        $"[Placement] Removed pending shared-anchor record: " +
                        $"{record.placementId}.");
                    continue;
                }

                if (!anchorsById.TryGetValue(record.anchorId, out var anchor))
                {
                    placementDocument.placements.Remove(record);
                    documentChanged = true;
                    Debug.Log(
                        $"[Placement] Removed completed pending-delete record: " +
                        record.anchorId);
                    continue;
                }
                if (!await anchorService.RemoveAsync(anchor))
                {
                    Debug.LogWarning(
                        $"[Placement] Pending anchor erase retry failed: {record.anchorId}.");
                    continue;
                }

                placementDocument.placements.Remove(record);
                anchorsById.Remove(record.anchorId);
                documentChanged = true;
                Debug.Log(
                    $"[Placement] Completed pending anchor erase: {record.anchorId}.");
            }

            var missing = 0;
            var reclassifiedAway = 0;
            var anchorRootsById = new Dictionary<string, GameObject>(
                StringComparer.OrdinalIgnoreCase);
            foreach (var record in recordsToRestore)
            {
                if (!anchorsById.TryGetValue(record.anchorId, out var anchor))
                {
                    missing++;
                    if (record.lifecycle != (int)PlacementLifecycle.Unavailable)
                    {
                        record.lifecycle = (int)PlacementLifecycle.Unavailable;
                        documentChanged = true;
                    }
                    Debug.LogWarning(
                        $"[Placement] Saved anchor {record.anchorId} was not found or localized.");
                    continue;
                }

                var resolvedRoomId = ResolvePlacementRoomId(
                    record,
                    anchor);
                if (!string.IsNullOrEmpty(resolvedRoomId) &&
                    !string.Equals(
                        record.roomId,
                        resolvedRoomId,
                        StringComparison.OrdinalIgnoreCase))
                {
                    record.roomId = resolvedRoomId;
                    documentChanged = true;
                }
                if (!string.IsNullOrEmpty(resolvedRoomId) &&
                    !string.Equals(
                        resolvedRoomId,
                        roomId,
                        StringComparison.OrdinalIgnoreCase))
                {
                    reclassifiedAway++;
                    continue;
                }

                var kind = MockInstrumentCatalog.FromTypeId(record.instrumentTypeId);
                if (!anchorRootsById.TryGetValue(
                        record.anchorId,
                        out var anchorRoot))
                {
                    anchorRoot = new GameObject(
                        $"[Anchor] {MockInstrumentCatalog.GetDisplayName(kind)}");
                    anchorRoot.transform.SetPositionAndRotation(
                        anchor.Pose.Position,
                        anchor.Pose.Rotation);
                    if (!anchorService.Bind(anchor, anchorRoot))
                    {
                        missing++;
                        Destroy(anchorRoot);
                        Debug.LogWarning(
                            $"[Placement] Saved anchor {record.anchorId} could not bind.");
                        continue;
                    }
                    anchorRootsById.Add(record.anchorId, anchorRoot);
                }

                var root = MockInstrumentFactory.Create(
                    kind,
                    new Pose(anchor.Pose.Position, anchor.Pose.Rotation),
                    theme: selectedTheme);
                root.transform.SetParent(anchorRoot.transform, true);

                var contract = root
                    .GetComponent<InstrumentGreyboxContract>();
                var interaction = contract.InstrumentInteraction;
                interaction.SetNormalizedValue(
                    record.normalizedValue,
                    InstrumentValueChangeOrigin.Restore);
                var runtimePlacement = new RuntimePlacement
                {
                    Record = record,
                    Anchor = anchor,
                    AnchorRoot = anchorRoot,
                    Root = root,
                    Contract = contract,
                    Interaction = interaction,
                    Audio = root.GetComponentInChildren<
                        InstrumentAudioController>(true),
                    AudioModule = root.GetComponentInChildren<
                        ModularAudioModuleRuntime>(true),
                    AudioGraphPlayer = root.GetComponentInChildren<
                        ModularAudioGraphPlayer>(true),
                    SignalMonitor = root
                        .GetComponentInChildren<SignalMonitorView>(true),
                    WindowPanelSignal = kind ==
                                        MockInstrumentKind.WindowPanel
                        ? new WindowPanelSignalRuntime()
                        : null,
                    WindowPanelGraphic = root
                        .GetComponentInChildren<
                            WindowPanelGraphicsPrototypeView>(true)
                };
                ApplyAudioParameters(runtimePlacement);
                SetPlacementLocalPose(
                    runtimePlacement,
                    record.localOffset.ToPose());
                placements.Add(runtimePlacement);
                Debug.Log(
                    $"[Placement] Restored {record.placementId} " +
                    $"{record.instrumentTypeId} anchor {record.anchorId} at " +
                    $"{anchor.Pose.Position}.");
                if (record.lifecycle != (int)PlacementLifecycle.Active)
                {
                    record.lifecycle = (int)PlacementLifecycle.Active;
                    documentChanged = true;
                }
                selectedKind = kind;
            }

            if (documentChanged && !SavePlacementDocument())
                Debug.LogError("[Placement] Reconciled placement state could not be saved.");

            Debug.Log(
                $"[Placement] Restore completed: {placements.Count}/" +
                $"{recordsToRestore.Count - reclassifiedAway} active, " +
                $"{missing} unavailable, {reclassifiedAway} in other room(s), " +
                $"{pendingDeletes.Count} pending-delete record(s) inspected.");

            if (preview != null)
            {
                MockInstrumentFactory.Destroy(preview);
                preview = null;
            }
            SetStatus(
                $"RESTORED {placements.Count}/" +
                $"{recordsToRestore.Count - reclassifiedAway} | " +
                MockInstrumentThemeCatalog.GetDisplayName(selectedTheme) +
                (missing > 0 ? $"\n{missing} ANCHOR(S) UNAVAILABLE" : string.Empty),
                missing > 0 ? Color.yellow : Color.green);
        }

        private string ResolvePlacementRoomId(
            PlacementRecord record,
            AnchorRecord anchor)
        {
            var rooms = MRUK.Instance?.Rooms;
            if (record == null ||
                anchor == null ||
                rooms == null ||
                rooms.Count == 0)
            {
                return record?.roomId ?? string.Empty;
            }

            var localPose = record.localOffset.ToPose();
            var worldPosition =
                anchor.Pose.Position +
                anchor.Pose.Rotation * localPose.position;
            MRUKRoom nearestRoom = null;
            var nearestSurfaceDistance = float.PositiveInfinity;
            foreach (var room in rooms)
            {
                if (room == null || room.Anchor == OVRAnchor.Null)
                    continue;

                if (room.IsPositionInRoom(worldPosition))
                    return GetRoomId(room);

                var surfaceDistance = room.TryGetClosestSurfacePosition(
                    worldPosition,
                    out _,
                    out _);
                if (surfaceDistance < nearestSurfaceDistance)
                {
                    nearestSurfaceDistance = surfaceDistance;
                    nearestRoom = room;
                }
            }

            return nearestRoom != null
                ? GetRoomId(nearestRoom)
                : !string.IsNullOrEmpty(record.roomId)
                    ? record.roomId
                    : GetRoomId(currentRoom);
        }

        private static bool BelongsToRoom(
            PlacementRecord record,
            string roomId)
        {
            return record != null &&
                   (string.IsNullOrEmpty(record.roomId) ||
                    string.Equals(
                        record.roomId,
                        roomId,
                        StringComparison.OrdinalIgnoreCase));
        }

        private RuntimePlacement FindPlacement(MockInstrumentInteraction interaction)
        {
            for (var index = 0; index < placements.Count; index++)
            {
                if (placements[index].Interaction == interaction)
                    return placements[index];
            }
            return null;
        }

        private RuntimePlacement FindReusableAnchorPlacement(
            Vector3 worldPosition)
        {
            RuntimePlacement nearest = null;
            var nearestDistanceSquared =
                SharedAnchorCoverageRadius * SharedAnchorCoverageRadius;
            foreach (var placement in placements)
            {
                if (placement?.AnchorRoot == null ||
                    placement.Record.lifecycle != (int)PlacementLifecycle.Active)
                {
                    continue;
                }

                var distanceSquared = Vector3.SqrMagnitude(
                    placement.AnchorRoot.transform.position - worldPosition);
                if (distanceSquared > nearestDistanceSquared)
                    continue;

                nearest = placement;
                nearestDistanceSquared = distanceSquared;
            }
            return nearest;
        }

        private int CountRuntimePlacementsForAnchor(string anchorId)
        {
            var count = 0;
            foreach (var placement in placements)
            {
                if (placement?.Record != null &&
                    string.Equals(
                        placement.Record.anchorId,
                        anchorId,
                        StringComparison.OrdinalIgnoreCase))
                {
                    count++;
                }
            }
            return count;
        }

        private bool HasRestorableRecordForAnchor(string anchorId)
        {
            foreach (var record in placementDocument.placements)
            {
                if (!string.Equals(
                        record.anchorId,
                        anchorId,
                        StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                if (record.lifecycle == (int)PlacementLifecycle.Active ||
                    record.lifecycle == (int)PlacementLifecycle.Unavailable)
                {
                    return true;
                }
            }
            return false;
        }

        private int CurrentRoomPlacementCount()
        {
            var roomId = GetRoomId(currentRoom);
            var count = 0;
            foreach (var record in placementDocument.placements)
            {
                if ((record.lifecycle == (int)PlacementLifecycle.Active ||
                     record.lifecycle ==
                     (int)PlacementLifecycle.Unavailable) &&
                    BelongsToRoom(record, roomId))
                {
                    count++;
                }
            }
            return count;
        }

        private int StoredPlacementCount()
        {
            var count = 0;
            foreach (var record in placementDocument.placements)
            {
                if (record.lifecycle == (int)PlacementLifecycle.Active ||
                    record.lifecycle ==
                    (int)PlacementLifecycle.Unavailable)
                {
                    count++;
                }
            }
            return count;
        }

        private bool SavePlacementDocument()
        {
            if (placementStore == null || placementDocument == null)
                return false;

            var previousRevision = placementDocument.revision;
            placementDocument.revision++;
            if (placementStore.Save(placementDocument))
                return true;

            placementDocument.revision = previousRevision;
            return false;
        }

        private bool TryRaycastPlacementSurface(
            Ray ray,
            float maximumDistance,
            out PlacementSurfaceHit hit)
        {
            return TryRaycastScenePlacementSurface(
                ray,
                maximumDistance,
                out hit);
        }

        private bool TryRaycastStablePlacementSurface(
            Ray ray,
            float maximumDistance,
            out PlacementSurfaceHit hit)
        {
            if (!TryRaycastPlacementSurface(
                    ray,
                    maximumDistance,
                    out var rawHit))
            {
                stableSurfaceMissFrames++;
                if (hasStablePlacementSurfaceHit &&
                    stableSurfaceMissFrames <=
                    SurfaceMissToleranceFrames)
                {
                    hit = stablePlacementSurfaceHit;
                    return true;
                }

                hasStablePlacementSurfaceHit = false;
                hasPendingPlacementSurfaceHit = false;
                hit = default;
                return false;
            }

            stableSurfaceMissFrames = 0;
            if (!hasStablePlacementSurfaceHit)
            {
                stablePlacementSurfaceHit = rawHit;
                hasStablePlacementSurfaceHit = true;
                hasPendingPlacementSurfaceHit = false;
                hit = rawHit;
                return true;
            }

            if (IsSameSurfaceSource(
                    stablePlacementSurfaceHit,
                    rawHit))
            {
                var pointDelta =
                    rawHit.Point - stablePlacementSurfaceHit.Point;
                var point = pointDelta.sqrMagnitude < 0.000036f
                    ? stablePlacementSurfaceHit.Point
                    : Vector3.Lerp(
                        stablePlacementSurfaceHit.Point,
                        rawHit.Point,
                        0.55f);
                var normal = Vector3.Lerp(
                    stablePlacementSurfaceHit.Normal,
                    rawHit.Normal,
                    0.35f).normalized;
                stablePlacementSurfaceHit =
                    new PlacementSurfaceHit(
                        point,
                        normal,
                        rawHit.Distance,
                        rawHit.Surface,
                        rawHit.SceneAnchor);
                hasPendingPlacementSurfaceHit = false;
                pendingSurfaceFrames = 0;
                hit = stablePlacementSurfaceHit;
                return true;
            }

            var immediatelyCloser =
                rawHit.Distance +
                SurfaceSwitchImmediateAdvantage <
                stablePlacementSurfaceHit.Distance;
            if (!hasPendingPlacementSurfaceHit ||
                !IsSameSurfaceSource(
                    pendingPlacementSurfaceHit,
                    rawHit))
            {
                pendingPlacementSurfaceHit = rawHit;
                hasPendingPlacementSurfaceHit = true;
                pendingSurfaceFrames = 1;
            }
            else
            {
                pendingPlacementSurfaceHit = rawHit;
                pendingSurfaceFrames++;
            }

            if (immediatelyCloser ||
                pendingSurfaceFrames >=
                SurfaceSwitchConfirmationFrames)
            {
                stablePlacementSurfaceHit = rawHit;
                hasPendingPlacementSurfaceHit = false;
                pendingSurfaceFrames = 0;
            }

            hit = stablePlacementSurfaceHit;
            return true;
        }

        private static bool IsSameSurfaceSource(
            PlacementSurfaceHit left,
            PlacementSurfaceHit right)
        {
            if (left.Surface != right.Surface)
                return false;
            if (left.Surface == SurfaceKind.Environment)
                return true;
            return ReferenceEquals(
                left.SceneAnchor,
                right.SceneAnchor);
        }

        private bool TryRaycastCurrentSurface(
            Ray ray,
            float maximumDistance,
            out PlacementSurfaceHit hit)
        {
            hit = default;
            if (currentSurface == SurfaceKind.Environment)
                return false;

            if (currentRoom == null)
                return false;

            if (currentSurface == SurfaceKind.Volume)
            {
                if (!currentRoom.Raycast(
                        ray,
                        maximumDistance,
                        PlacementVolumeFilter,
                        out var volumeHit,
                        out _) ||
                    !HasUsableSurfaceNormal(volumeHit.normal))
                {
                    return false;
                }

                hit = new PlacementSurfaceHit(
                    volumeHit.point,
                    volumeHit.normal.normalized,
                    volumeHit.distance,
                    SurfaceKind.Volume);
                return true;
            }

            if (!currentRoom.Raycast(
                    ray,
                    maximumDistance,
                    PlacementPlaneFilter,
                    out var planeHit,
                    out var planeAnchor) ||
                !TryGetPlaneSurface(planeAnchor.Label, out var surface) ||
                surface != currentSurface ||
                !HasUsableSurfaceNormal(planeHit.normal))
            {
                return false;
            }

            hit = new PlacementSurfaceHit(
                planeHit.point,
                planeHit.normal.normalized,
                planeHit.distance,
                surface,
                planeAnchor);
            return true;
        }

        private bool TryRaycastScenePlacementSurface(
            Ray ray,
            float maximumDistance,
            out PlacementSurfaceHit hit)
        {
            hit = default;
            if (currentRoom == null)
                return false;

            var planeSurface = SurfaceKind.Unknown;
            var hasPlane = currentRoom.Raycast(
                               ray,
                               maximumDistance,
                               PlacementPlaneFilter,
                               out var planeHit,
                               out var planeAnchor) &&
                           TryGetPlaneSurface(
                               planeAnchor.Label,
                               out planeSurface) &&
                           HasUsableSurfaceNormal(planeHit.normal);
            var hasVolume = currentRoom.Raycast(
                                ray,
                                maximumDistance,
                                PlacementVolumeFilter,
                                out var volumeHit,
                                out var volumeAnchor) &&
                            HasUsableSurfaceNormal(volumeHit.normal);

            if (!hasPlane && !hasVolume)
                return false;

            if (hasVolume &&
                (!hasPlane || volumeHit.distance < planeHit.distance))
            {
                hit = new PlacementSurfaceHit(
                    volumeHit.point,
                    volumeHit.normal.normalized,
                    volumeHit.distance,
                    SurfaceKind.Volume,
                    volumeAnchor);
                return true;
            }

            hit = new PlacementSurfaceHit(
                planeHit.point,
                planeHit.normal.normalized,
                planeHit.distance,
                planeSurface,
                planeAnchor);
            return true;
        }

        private static bool HasUsableSurfaceNormal(Vector3 normal)
        {
            return normal.sqrMagnitude > 0.25f;
        }

        private static bool TryGetPlaneSurface(
            MRUKAnchor.SceneLabels label,
            out SurfaceKind surface)
        {
            surface = SurfaceKind.Plane;
            return true;
        }

        private void SetPreviewVisible(bool visible)
        {
            if (preview != null && preview.activeSelf != visible)
                preview.SetActive(visible);
        }

        private void SetStatus(string message, Color? color = null)
        {
            if (statusLabel == null)
                return;

            statusLabel.text = message;
            statusLabel.color = color ?? Color.white;
        }
    }
}
