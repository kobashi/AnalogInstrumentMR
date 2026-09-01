using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using MatsuMotoMeterAR.Anchors;
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
        private const float GroupMoveGripThreshold = 0.65f;
        private const float OperationGripPressThreshold = 0.65f;
        private const float OperationGripReleaseThreshold = 0.35f;
        private const float LeverGripTravelMeters = 0.24f;
        private const float SharedAnchorCoverageRadius = 2.75f;
        private const int MaximumEditHistory = 32;
        private const float ControllerBeamStartOffset = 0.035f;
        private const float ControllerBeamWidth = 0.004f;
        private const float ExitHoldSeconds = 2f;
        private const float ModeLockHoldSeconds = 2f;
        private const float MoveTargetWidth = 0.008f;
        private const float SurfaceWireframeWidth = 0.006f;
        private const float PlacementGridSpacing = 0.10f;
        private const float AutoAlignSearchRadius = 1.0f;
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
        private RuntimePlacement groupMovePivot;
        private RuntimePlacement lastAlignmentReference;
        private AlignmentAnchorMode nextAlignmentAnchorMode =
            AlignmentAnchorMode.Leading;
        private string lastAlignmentGroupSignature;
        private int lastAlignmentOriginalReferenceIndex;
        private float hapticStopTime;
        private float leftHapticStopTime;
        private float exitHoldTime;
        private float modeLockHoldTime;
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
        private bool connectRightTriggerEngaged;
        private bool connectLeftTriggerEngaged;
        private bool connectAxisEngaged;
        private bool connectParameterFieldAxisEngaged;
        private bool connectSlotAxisEngaged;
        private bool connectTargetSettingAxisEngaged;
        private bool groupMoveArmed;
        private bool selectionAxisEngaged;
        private bool themeAxisEngaged;
        private bool alignmentAxisEngaged;
        private bool rotationAxisEngaged;
        private bool hasStablePlacementSurfaceHit;
        private bool hasPendingPlacementSurfaceHit;
        private bool placementPoseAutoAligned;
        private bool placementPoseGridSnapped;
        private PendingLayout pendingLayout;
        private bool operationInProgress;
        private bool isExiting;
        private bool modeSwitchLocked;
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
            public MockInstrumentInteraction Interaction;
            public SignalMonitorView SignalMonitor;
            public WindowPanelSignalRuntime WindowPanelSignal;
            public WindowPanelGraphicsPrototypeView WindowPanelGraphic;
        }

        private sealed class HandOperationState
        {
            public readonly OVRInput.Controller Controller;
            public readonly string Label;
            public MockInstrumentInteraction TriggerInteraction;
            public MockInstrumentInteraction GripInteraction;
            public MockInstrumentInteraction ContactButton;
            public RuntimePlacement GripPlacement;
            public Vector3 GripStartPosition;
            public Vector3 GripStartDirection;
            public float GripStartValue;
            public int GripLastDetent;
            public bool TriggerEngaged;
            public bool GripEngaged;

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

        private enum OperationResolveMode
        {
            Any,
            Trigger,
            GripMotion,
            ContactButton
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
            bool allowInEditMode)
        {
            if (beam == null || controllerAnchor == null)
                return;
            if (!allowInEditMode &&
                AppInteractionModePolicy.AllowsEditing(interactionMode))
            {
                beam.enabled = false;
                return;
            }
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

            if (AppInteractionModePolicy.AllowsEditing(interactionMode))
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
                    ? EditBeamColor
                    : AppInteractionModePolicy.AllowsConnecting(
                        interactionMode)
                        ? ConnectBeamColor
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
            placementPoseAutoAligned = false;
            placementPoseGridSnapped = false;
            isAimingAtPlacedObject = false;
            SetMoveTargetMarkersVisible(false);
            if (!AppInteractionModePolicy.AllowsEditing(interactionMode) ||
                currentRoom == null ||
                rightAimAnchor == null ||
                operationInProgress)
            {
                hasStablePlacementSurfaceHit = false;
                hasPendingPlacementSurfaceHit = false;
                SetPreviewVisible(false);
                return;
            }

            if (!groupMoveArmed && groupMoveSelection.Count > 0)
            {
                SetPreviewVisible(false);
                SetStatus(
                    $"{groupMoveSelection.Count} SELECTED | " +
                    "CYAN = FIRST ANCHOR\n" +
                    "TRIGGER TO CHANGE | A MOVE\n" +
                    "L-STICK: L/UP ALIGN | R/D DISTRIBUTE\n" +
                    "R-STICK: ROTATE | B CLEAR SELECTION",
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
                    "TRIGGER SELECT | B DELETE\n" +
                    "R-CLICK RE-PLACE",
                    Color.white);
                return;
            }

            var ray = new Ray(
                rightAimAnchor.position,
                rightAimAnchor.forward);
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
            ApplyPlacementModifiers(ref currentPlacementPose);
            hasPlacementPose = true;

            if (groupMoveArmed)
            {
                SetPreviewVisible(false);
                var targetIsValid =
                    UpdateMoveTargetMarkers(out var invalidReason);
                SetStatus(
                    targetIsValid
                        ? $"GROUP MOVE: {groupMoveSelection.Count} INSTRUMENT(S)\n" +
                          $"TARGET: {currentSurface.ToString().ToUpperInvariant()} | A CONFIRM\n" +
                          PlacementModifierStatus() +
                          "R-STICK ROTATE | B CANCEL"
                        : $"MOVE BLOCKED: {invalidReason}\n" +
                          $"TARGET: {currentSurface.ToString().ToUpperInvariant()} | B CANCEL",
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
                PlacementModifierStatus() +
                "R \u2190/\u2192 OBJECT | R \u2191/\u2193 CATEGORY\n" +
                "L \u2190/\u2192 THEME\n" +
                "TRIGGER SELECT | A PLACE | B DELETE\n" +
                "L-GRIP AUTO ALIGN | +L-TRIGGER GRID\n" +
                "R-CLICK REPLACE | X CONNECT");
        }

        private void ApplyPlacementModifiers(ref Pose pose)
        {
            var leftGrip = Mathf.Max(
                OVRInput.Get(
                    OVRInput.RawAxis1D.LHandTrigger,
                    OVRInput.Controller.LTouch),
                ReadFloat(leftGripAction));
            if (leftGrip < GroupMoveGripThreshold)
                return;

            var leftTrigger = Mathf.Max(
                OVRInput.Get(
                    OVRInput.RawAxis1D.LIndexTrigger,
                    OVRInput.Controller.LTouch),
                ReadFloat(leftTriggerAction));
            if (leftTrigger >= TriggerPressThreshold)
            {
                SnapPoseToGrid(ref pose);
                placementPoseGridSnapped = true;
                return;
            }

            if (TryAutoAlignPose(ref pose))
                placementPoseAutoAligned = true;
        }

        private bool TryAutoAlignPose(ref Pose pose)
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

                var transform = placement.Root.transform;
                if (Vector3.Dot(transform.forward, pose.rotation *
                        Vector3.forward) < CoplanarNormalDotThreshold)
                {
                    continue;
                }

                var distanceSquared =
                    (transform.position - pose.position).sqrMagnitude;
                if (distanceSquared >= nearestDistanceSquared)
                    continue;
                nearestDistanceSquared = distanceSquared;
                nearest = placement;
            }
            if (nearest == null)
                return false;

            var target = nearest.Root.transform;
            var delta = pose.position - target.position;
            var x = Vector3.Dot(delta, target.right);
            var y = Vector3.Dot(delta, target.up);
            if (Mathf.Abs(x) <= Mathf.Abs(y))
                delta -= target.right * x;
            else
                delta -= target.up * y;
            pose = new Pose(
                target.position + delta,
                target.rotation);
            return true;
        }

        private static void SnapPoseToGrid(ref Pose pose)
        {
            var right = pose.rotation * Vector3.right;
            var up = pose.rotation * Vector3.up;
            var x = Vector3.Dot(pose.position, right);
            var y = Vector3.Dot(pose.position, up);
            pose.position += right *
                             (Mathf.Round(x / PlacementGridSpacing) *
                              PlacementGridSpacing - x);
            pose.position += up *
                             (Mathf.Round(y / PlacementGridSpacing) *
                              PlacementGridSpacing - y);
        }

        private string PlacementModifierStatus()
        {
            if (placementPoseGridSnapped)
                return "GRID SNAP 10 CM\n";
            if (placementPoseAutoAligned)
                return "AUTO ALIGNED TO NEARBY OBJECT\n";
            return string.Empty;
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
            var connecting =
                AppInteractionModePolicy.AllowsConnecting(interactionMode);
            var exitInputConsumed =
                UpdateLeftStickHold(
                    leftThumbstickButton,
                    editing,
                    AppInteractionModePolicy.AllowsInstrumentOperation(
                        interactionMode));

            if (!exitInputConsumed &&
                !operationInProgress &&
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

            if (!exitInputConsumed && !modeToggled && editing)
            {
                if (groupMoveSelection.Count == 0 &&
                    !thumbstickButton)
                {
                    UpdateSelection(
                        thumbstick,
                        leftThumbstick);
                }

                var editActionConsumed = false;
                if (!operationInProgress &&
                    editTrigger &&
                    !previousEditTrigger)
                {
                    ToggleAimedSelection();
                    editActionConsumed = true;
                }
                // Y is intentionally reserved for a future Edit-mode action.
                if (!editActionConsumed &&
                    !operationInProgress &&
                    groupMoveSelection.Count >= 2)
                {
                    editActionConsumed =
                        HandleSelectionRotationStick(thumbstick);
                }
                if (!editActionConsumed &&
                    !operationInProgress &&
                    groupMoveSelection.Count >= 2)
                {
                    editActionConsumed =
                        HandleAlignmentStick(leftThumbstick);
                }
                if (!editActionConsumed &&
                    !operationInProgress &&
                    groupMoveArmed &&
                    (hasPlacementPose ||
                     pendingLayout != PendingLayout.None) &&
                    aButton &&
                    !previousAButton)
                {
                    if (pendingLayout != PendingLayout.None)
                        ConfirmPendingLayout();
                    else
                        HandleGroupMoveAction();
                    editActionConsumed = true;
                }
                if (!editActionConsumed &&
                    !operationInProgress &&
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
            else if (!exitInputConsumed &&
                     !modeToggled &&
                     connecting)
            {
                UpdateSelection(
                    Vector2.zero,
                    Vector2.zero);
                UpdateConnectInput(
                    trigger,
                    leftTrigger,
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
                UpdateSelection(
                    Vector2.zero,
                    Vector2.zero);
            }

            previousAButton = aButton;
            previousBButton = bButton;
            previousXButton = xButton;
            previousYButton = yButton;
            previousGroupMoveChord = false;
            previousThumbstickButton = thumbstickButton;
            previousLeftThumbstickButton = leftThumbstickButton;
            previousEditTrigger = editTrigger;
            UpdateInstrumentInteractions(
                trigger,
                leftTrigger,
                rightGrip,
                leftGrip);
            UpdateHaptics();
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
                    SetModeStatus();
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
            float leftGrip)
        {
            var operationAllowed =
                AppInteractionModePolicy.AllowsInstrumentOperation(
                    interactionMode) &&
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
            UpdateGripInteraction(
                rightOperationHand,
                leftOperationHand,
                rightControllerAnchor,
                rightGrip);
            UpdateGripInteraction(
                leftOperationHand,
                rightOperationHand,
                leftControllerAnchor,
                leftGrip);
            UpdateTriggerInteraction(
                rightOperationHand,
                leftOperationHand,
                rightAimAnchor,
                rightTrigger);
            UpdateTriggerInteraction(
                leftOperationHand,
                rightOperationHand,
                leftAimAnchor,
                leftTrigger);

            if (!HasActiveOperationInteraction())
                UpdateOperationHoverStatus();
        }

        private void UpdateTriggerInteraction(
            HandOperationState hand,
            HandOperationState otherHand,
            Transform controllerAnchor,
            float triggerValue)
        {
            if (hand.TriggerEngaged)
            {
                if (triggerValue <= TriggerReleaseThreshold)
                {
                    ReleaseTriggerInteraction(hand);
                    hand.TriggerEngaged = false;
                }
                return;
            }

            if (triggerValue < TriggerPressThreshold ||
                controllerAnchor == null ||
                hand.GripInteraction != null)
            {
                return;
            }

            hand.TriggerEngaged = true;
            if (!TryResolveOperationInteraction(
                    controllerAnchor,
                    OperationResolveMode.Trigger,
                    out var interaction,
                    out var placement,
                    out var reach) ||
                IsInteractionHeldByOtherHand(interaction, otherHand))
            {
                return;
            }

            hand.TriggerInteraction = interaction;
            interaction.SetPressed(true);
            SaveInteractionState(interaction);
            PulseHaptics(hand.Controller);
            var kind = GetPlacementKind(placement);
            SetStatus(
                $"{hand.Label} {reach.ToString().ToUpperInvariant()} TRIGGER | " +
                $"{MockInstrumentCatalog.GetDisplayName(kind)}\n" +
                FormatOperationState(interaction),
                Color.green);
        }

        private void UpdateGripInteraction(
            HandOperationState hand,
            HandOperationState otherHand,
            Transform controllerAnchor,
            float gripValue)
        {
            if (hand.GripInteraction != null)
            {
                if (gripValue <= OperationGripReleaseThreshold ||
                    controllerAnchor == null ||
                    hand.GripPlacement?.Root == null)
                {
                    ReleaseGripInteraction(hand);
                    hand.GripEngaged = false;
                    return;
                }

                var kind = GetPlacementKind(hand.GripPlacement);
                float normalizedValue;
                if (kind == MockInstrumentKind.ThrottleLever ||
                    kind == MockInstrumentKind.Lever)
                {
                    var rotationAxis =
                        hand.GripPlacement.Root.transform.right;
                    var pivot =
                        hand.GripInteraction.Motion.MovingPart.position;
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
                        kind == MockInstrumentKind.ThrottleLever
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
                hand.GripInteraction.SetNormalizedValue(normalizedValue);
                if (hand.GripLastDetent !=
                    hand.GripInteraction.DetentIndex)
                {
                    hand.GripLastDetent =
                        hand.GripInteraction.DetentIndex;
                    PulseHaptics(hand.Controller);
                }
                SetStatus(
                    $"{hand.Label} GRIP + MOTION | " +
                    $"{MockInstrumentCatalog.GetDisplayName(kind)}\n" +
                    FormatOperationState(hand.GripInteraction),
                    Color.green);
                return;
            }

            if (gripValue < OperationGripPressThreshold ||
                hand.GripEngaged ||
                controllerAnchor == null)
            {
                if (gripValue <= OperationGripReleaseThreshold)
                    hand.GripEngaged = false;
                return;
            }

            hand.GripEngaged = true;
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
            hand.GripPlacement = placement;
            hand.GripStartPosition = controllerAnchor.position;
            var captureAxis = placement.Root.transform.right;
            var capturePivot = interaction.Motion.MovingPart.position;
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
            SetStatus(
                $"{hand.Label} GRIP CAPTURED | " +
                $"{displayName}\n" +
                (GetPlacementKind(placement) switch
                {
                    MockInstrumentKind.ThrottleLever =>
                        "MOVE THROUGH THROTTLE ARC",
                    MockInstrumentKind.Lever =>
                        "MOVE THROUGH LEVER ARC",
                    _ => "MOVE UP / DOWN"
                }),
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
            return ReferenceEquals(
                       interaction,
                       otherHand.TriggerInteraction) ||
                   ReferenceEquals(
                       interaction,
                       otherHand.GripInteraction);
        }

        private bool HasActiveOperationInteraction()
        {
            return rightOperationHand.TriggerInteraction != null ||
                   leftOperationHand.TriggerInteraction != null ||
                   rightOperationHand.GripInteraction != null ||
                   leftOperationHand.GripInteraction != null ||
                   rightOperationHand.ContactButton != null ||
                   leftOperationHand.ContactButton != null;
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
            if (MockInstrumentCatalog.IsReadOnlyMeter(kind))
            {
                instruction = "READ ONLY | AMBIENT MOTION";
            }
            else if (MockInstrumentCatalog.UsesContactPress(kind))
            {
                instruction = reach == InstrumentInteractionHitTest.Reach.Direct
                    ? "CONTACT PRESS"
                    : "TOUCH TO PRESS";
            }
            else if (MockInstrumentCatalog.SupportsGripMotion(kind))
            {
                instruction = reach == InstrumentInteractionHitTest.Reach.Direct
                    ? "GRIP + MOVE OR TRIGGER"
                    : "TRIGGER | TOUCH + GRIP TO MOVE";
            }
            else
            {
                instruction = interaction.DetentCount > 0
                    ? "TRIGGER: NEXT STATE"
                    : "TRIGGER";
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
                    roomPrefix + "EDIT MODE | X: CONNECT\n" +
                    "TRIGGER SELECT | A PLACE/MOVE | B DELETE/CLEAR\n" +
                    "L-STICK: ALIGN/DISTRIBUTE | R-STICK: ROTATE\n" +
                    "L-GRIP: AUTO | +TRIGGER: GRID\n" +
                    "HOLD L-STICK 2s TO EXIT",
                    new Color(1f, 0.75f, 0.15f));
                return;
            }

            if (AppInteractionModePolicy.AllowsConnecting(interactionMode))
            {
                SetStatus(
                    roomPrefix + "CONNECT MODE | X: OPERATE\n" +
                    "INPUT TRIGGER -> OUTPUT TRIGGER\n" +
                    "L STICK L/R: TRANSFORM | A CONFIRM\n" +
                    "ONE OBJECT: A NEXT CONNECTION\n" +
                    "L STICK PRESS: APPLY | B DELETE/CANCEL",
                    ConnectBeamColor);
                return;
            }

            SetStatus(
                modeSwitchLocked
                    ? roomPrefix +
                      "OPERATION MODE | MODE SWITCH LOCKED\n" +
                      "X DISABLED | HOLD L-STICK 2s TO UNLOCK\n" +
                      "BOTH HANDS: AIM + TRIGGER\n" +
                      "LEVER/SLIDER: TOUCH + GRIP + MOVE"
                    : roomPrefix + "OPERATION MODE | X: EDIT\n" +
                      "HOLD L-STICK 2s TO LOCK MODE SWITCH\n" +
                      "BOTH HANDS: AIM + TRIGGER\n" +
                      "LEVER/SLIDER: TOUCH + GRIP + MOVE\n" +
                      "BUTTON: TOUCH | METERS: READ ONLY",
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

            if (parameterEditPressed &&
                selectedConnectionForRemoval != null)
            {
                BeginConnectionParameterEdit();
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
                else
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
                if (selectedConnectionForRemoval != null)
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
            if (connectSource == null && connectTarget != null)
            {
                var targetKind = GetPlacementKind(connectTarget);
                if (ReferenceEquals(connectTarget, placement))
                {
                    SetConnectNotice(
                        "SOURCE AND TARGET MUST DIFFER",
                        Color.yellow);
                    return;
                }
                if (!InstrumentSignalPolicy.CanConnect(kind, targetKind))
                {
                    SetConnectNotice(
                        $"{MockInstrumentCatalog.GetDisplayName(kind)} " +
                        "HAS NO OBSERVABLE OUTPUT",
                        Color.yellow);
                    return;
                }

                connectSource = placement;
                connectSourceMarker = CreateConnectMarker(
                    placement,
                    "[Connect] Source",
                    ConnectSourceColor,
                    0.014f);
                connectStatusHoldUntil = 0f;
                PulseHaptics();
                UpdateConnectStatus();
                return;
            }

            if (connectSource == null)
            {
                if (kind == MockInstrumentKind.TrendMonitor ||
                    kind == MockInstrumentKind.WindowPanel)
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
                if (!InstrumentSignalPolicy.CanSource(kind))
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

                ClearConnectEditSelection();
                connectSource = placement;
                connectSourceMarker = CreateConnectMarker(
                    placement,
                    "[Connect] Source",
                    ConnectSourceColor,
                    0.014f);
                connectStatusHoldUntil = 0f;
                PulseHaptics();
                UpdateConnectStatus();
                return;
            }

            var sourceKind = GetPlacementKind(connectSource);
            if (!InstrumentSignalPolicy.CanConnect(sourceKind, kind))
            {
                SetConnectNotice(
                    $"{MockInstrumentCatalog.GetDisplayName(kind)} " +
                    "CANNOT ACCEPT THIS OUTPUT",
                    Color.yellow);
                return;
            }
            if (ReferenceEquals(connectSource, placement))
            {
                SetConnectNotice(
                    "SOURCE AND TARGET MUST DIFFER",
                    Color.yellow);
                return;
            }

            selectedConnectionForRemoval = null;
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

        private void SelectNextConnectionForRemoval()
        {
            var selectedPlacement =
                connectEditPlacement ?? connectSource ?? connectTarget;
            if (selectedPlacement?.Record == null ||
                placementDocument?.connections == null)
            {
                SetConnectNotice(
                    "SELECT ONE OBJECT + TRIGGER",
                    Color.yellow);
                return;
            }

            var placementId = selectedPlacement.Record.placementId;
            var next = SignalConnectionSelectionPolicy.SelectNext(
                placementDocument.connections,
                placementId,
                selectedConnectionForRemoval?.connectionId);
            if (next == null)
            {
                selectedConnectionForRemoval = null;
                SetConnectNotice(
                    "SELECTED OBJECT HAS NO CONNECTION",
                    Color.yellow);
                return;
            }

            selectedConnectionForRemoval = next;
            selectedConnectionPendingTransform =
                (SignalTransformKind)next.transformKind;
            selectedConnectionPendingSlot = next.targetInputSlot;
            selectedConnectionPendingPriority = next.compositionPriority;
            connectStatusHoldUntil = 0f;
            PulseHaptics();
            UpdateConnectStatus();
        }

        private void DeleteSelectedConnection()
        {
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
            if (!AppInteractionModePolicy.AllowsConnecting(interactionMode))
                return;
            if (Time.unscaledTime < connectStatusHoldUntil)
                return;

            var transformLabel =
                pendingSignalTransform.ToString().ToUpperInvariant();
            var editPlacement =
                connectEditPlacement ?? connectSource ?? connectTarget;
            if (connectionParameterDraft != null &&
                selectedConnectionForRemoval != null)
            {
                var transform = (SignalTransformKind)
                    connectionParameterDraft.transformKind;
                var source = FindPlacementById(
                    selectedConnectionForRemoval.sourcePlacementId);
                var input = source?.Interaction == null
                    ? 0f
                    : source.Interaction.NormalizedValue;
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
                    $"{connectionCount} CONNECTION(S)\n" +
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
                var inputCount = CountIncomingConnections(
                    connectTarget.Record?.placementId);
                var targetInputLimit = GetPlacementKind(connectTarget) ==
                                       MockInstrumentKind.WindowPanel
                    ? InstrumentSignalPolicy.MaximumWindowPanelInputs
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
                    "SELECT INPUT SOURCE + TRIGGER\n" +
                    "A: NEXT CONNECTION | B: CANCEL",
                    ConnectTargetColor);
                return;
            }

            if (connectSource == null)
            {
                SetStatus(
                    $"CONNECT | {placementDocument?.connections.Count ?? 0}/" +
                    $"{PlacementDocument.MaximumConnections}\n" +
                    "SELECT OBJECT + TRIGGER\n" +
                    "D:CYN I:MAG R:GRN T:ORG",
                    ConnectBeamColor);
                return;
            }

            var sourceName = MockInstrumentCatalog.GetDisplayName(
                GetPlacementKind(connectSource));
            if (connectTarget == null)
            {
                var connectionCount = CountConnections(
                    connectSource.Record?.placementId);
                SetStatus(
                    $"SOURCE: {sourceName}\n" +
                    $"TRANSFORM: {transformLabel} | L STICK L/R\n" +
                    $"TARGET + TRIGGER | A: SELECT " +
                    $"({connectionCount})\n" +
                    "B: CANCEL",
                    ConnectionColor(pendingSignalTransform));
                return;
            }

            var targetName = MockInstrumentCatalog.GetDisplayName(
                GetPlacementKind(connectTarget));
            SetStatus(
                $"{sourceName} -> {targetName}\n" +
                $"{transformLabel}" +
                (GetPlacementKind(connectTarget) ==
                     MockInstrumentKind.WindowPanel &&
                 WindowPanelInputSlotPolicy.TryFindLowestAvailable(
                     placementDocument?.connections,
                     connectTarget.Record?.placementId,
                     out var pendingSlot)
                    ? $" | SLOT {SlotLabel(pendingSlot)}"
                    : string.Empty) +
                " | A CONFIRM | B CANCEL",
                ConnectionColor(pendingSignalTransform));
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
                        source.NormalizedValue,
                        connection);
                    monitor.AddSample(connection.connectionId, value);
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
            }
            else if (monitor.TouchedChannelCount > 0)
            {
                monitor.SetComposedUnavailable(compositionKind);
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
                placement.Interaction?.SetNormalizedValue(
                    placement.WindowPanelSignal.OutputValue);
            }
            return windowPanelTargetIds;
        }

        private void UpdateConnectionVisuals()
        {
            var visible =
                AppInteractionModePolicy.AllowsConnecting(interactionMode);
            foreach (var line in connectionLines.Values)
            {
                if (line != null)
                    line.enabled = visible;
            }
            if (!visible || placementDocument?.connections == null)
                return;

            activeConnectionLineIds.Clear();
            foreach (var connection in placementDocument.connections)
            {
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

                var sourcePosition = source.Root.transform.position;
                var targetPosition = target.Root.transform.position;
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

        private LineRenderer CreateConnectionLine(string connectionId)
        {
            var lineObject = new GameObject(
                $"[Connect] Signal {connectionId}");
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
                    "AIM AT A SURFACE | A CONFIRM\n" +
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
                        newSurfaces))
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
            bool recordHistory = true)
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
                    After = CaptureEditStates(editedPlacements)
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
                    "AIM AT DESTINATION | A TO MOVE",
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
            if (placements.Count == 0 || rightAimAnchor == null)
                return false;

            interactionCandidates.Clear();
            for (var index = 0; index < placements.Count; index++)
            {
                if (placements[index].Interaction != null)
                    interactionCandidates.Add(placements[index].Interaction);
            }
            if (!InstrumentInteractionResolver.TryResolveBest(
                    interactionCandidates,
                    rightAimAnchor.position,
                    rightAimAnchor.forward,
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
                    OperationResolveMode.Trigger =>
                        !MockInstrumentCatalog.IsReadOnlyMeter(kind),
                    OperationResolveMode.GripMotion =>
                        MockInstrumentCatalog.SupportsGripMotion(kind),
                    OperationResolveMode.ContactButton =>
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
                if (candidate?.Motion?.MovingPart == null)
                    continue;

                var kind = GetPlacementKind(candidatePlacement);
                if (!MockInstrumentCatalog.SupportsGripMotion(kind))
                    continue;

                float distanceSquared;
                if (kind == MockInstrumentKind.ThrottleLever ||
                    kind == MockInstrumentKind.Lever ||
                    kind == MockInstrumentKind.PowerSlider)
                {
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
            ReleaseTriggerInteraction(rightOperationHand);
            ReleaseTriggerInteraction(leftOperationHand);
            ReleaseGripInteraction(rightOperationHand);
            ReleaseGripInteraction(leftOperationHand);

            var rightContact = rightOperationHand.ContactButton;
            var leftContact = leftOperationHand.ContactButton;
            rightOperationHand.ContactButton = null;
            leftOperationHand.ContactButton = null;
            if (rightContact != null)
            {
                rightContact.SetPressed(false);
                SaveInteractionState(rightContact);
            }
            if (leftContact != null &&
                !ReferenceEquals(leftContact, rightContact))
            {
                leftContact.SetPressed(false);
                SaveInteractionState(leftContact);
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

        private void ReleaseTriggerInteraction(HandOperationState hand)
        {
            if (hand.TriggerInteraction == null)
                return;

            hand.TriggerInteraction.SetPressed(false);
            SaveInteractionState(hand.TriggerInteraction);
            hand.TriggerInteraction = null;
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
            placement.Record.normalizedValue = interaction.NormalizedValue;
            if (!SavePlacementDocument())
            {
                placement.Record.normalizedValue = previousValue;
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
                placement.Interaction = placement.Root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
            }
            SetStatus(
                $"THEME: {MockInstrumentThemeCatalog.GetDisplayName(selectedTheme)}\n" +
                $"{CurrentRoomPlacementCount():00}/" +
                $"{PlacementDocument.MaximumActivePlacements:00} IN ROOM",
                Color.green);
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
                var interaction = newInstrument
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
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
                placementDocument.placements.Add(newRecord);
                if (!SavePlacementDocument())
                {
                    placementDocument.placements.Remove(newRecord);
                    throw new InvalidOperationException(
                        "Spatial anchor was saved but placement JSON could not be committed.");
                }

                placements.Add(new RuntimePlacement
                {
                    Record = newRecord,
                    Anchor = newAnchor,
                    AnchorRoot = newAnchorRoot,
                    Root = newInstrument,
                    Interaction = interaction,
                    SignalMonitor = newInstrument
                        .GetComponentInChildren<SignalMonitorView>(true),
                    WindowPanelSignal = selectedKind ==
                                        MockInstrumentKind.WindowPanel
                        ? new WindowPanelSignalRuntime()
                        : null,
                    WindowPanelGraphic = newInstrument
                        .GetComponentInChildren<
                            WindowPanelGraphicsPrototypeView>(true)
                });
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

                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                interaction.SetNormalizedValue(record.normalizedValue);
                var runtimePlacement = new RuntimePlacement
                {
                    Record = record,
                    Anchor = anchor,
                    AnchorRoot = anchorRoot,
                    Root = root,
                    Interaction = interaction,
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
