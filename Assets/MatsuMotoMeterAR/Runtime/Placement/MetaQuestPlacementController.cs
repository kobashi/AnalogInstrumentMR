using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using MatsuMotoMeterAR.Anchors;
using MatsuMotoMeterAR.Development;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.InteractionModes;
using MatsuMotoMeterAR.PlacementPersistence;
using MatsuMotoMeterAR.Rendering;
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
        private const float HapticDuration = 0.06f;
        private const float PlacementSpacing = 0.012f;
        private const float CollisionMargin = 0.002f;
        private const float SelectionMarkerPadding = 0.012f;
        private const int AutoPlacementMaximumRing = 4;
        private const float CoplanarDistanceTolerance = 0.15f;
        private const float CoplanarNormalDotThreshold = 0.95f;
        private const float GroupMoveGripThreshold = 0.65f;
        private const float SharedAnchorCoverageRadius = 2.75f;
        private const int MaximumEditHistory = 32;
        private const float ControllerBeamStartOffset = 0.035f;
        private const float ControllerBeamWidth = 0.004f;
        private const float ExitHoldSeconds = 2f;
        private const float MoveTargetWidth = 0.008f;

        private static readonly Color EditBeamColor =
            new(1f, 0.65f, 0.05f, 1f);
        private static readonly Color OperationBeamColor =
            new(0.05f, 0.9f, 1f, 1f);

        private static readonly LabelFilter PlacementSurfaceFilter = new(
            MRUKAnchor.SceneLabels.WALL_FACE |
            MRUKAnchor.SceneLabels.FLOOR |
            MRUKAnchor.SceneLabels.CEILING);

        private Transform rightControllerAnchor;
        private Transform trackingSpace;
        private TextMesh statusLabel;
        private LineRenderer controllerBeam;
        private MRUKRoom currentRoom;
        private GameObject preview;
        private readonly List<GameObject> moveTargetMarkers = new();
        private readonly List<RuntimePlacement> placements = new();
        private readonly List<MockInstrumentInteraction> interactionCandidates = new();
        private readonly List<RuntimePlacement> groupMoveSelection = new();
        private readonly Dictionary<RuntimePlacement, GameObject> selectionMarkers = new();
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
        private MockInstrumentInteraction activeInteraction;
        private RuntimePlacement activePlacement;
        private RuntimePlacement groupMovePivot;
        private float hapticStopTime;
        private float exitHoldTime;
        private bool hasPlacementPose;
        private bool placementPoseWasAdjusted;
        private bool isAimingAtPlacedObject;
        private bool previousAButton;
        private bool previousXButton;
        private bool previousYButton;
        private bool previousGroupMoveChord;
        private bool previousThumbstickButton;
        private bool previousLeftThumbstickButton;
        private bool previousEditTrigger;
        private bool groupMoveArmed;
        private bool selectionAxisEngaged;
        private bool triggerEngaged;
        private bool operationInProgress;
        private bool isExiting;
        private int controllerPoseResyncFrames;
        private InputAction rightPrimaryButtonAction;
        private InputAction rightSecondaryButtonAction;
        private InputAction leftPrimaryButtonAction;
        private InputAction leftSecondaryButtonAction;
        private InputAction rightThumbstickButtonAction;
        private InputAction leftThumbstickButtonAction;
        private InputAction rightThumbstickAction;
        private InputAction rightTriggerAction;
        private InputAction leftGripAction;
        private InputAction rightPositionAction;
        private InputAction rightRotationAction;

        private sealed class RuntimePlacement
        {
            public PlacementRecord Record;
            public AnchorRecord Anchor;
            public GameObject AnchorRoot;
            public GameObject Root;
            public MockInstrumentInteraction Interaction;
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
                if (await Task.WhenAny(roomLoadTask, Task.Delay(20000)) != roomLoadTask)
                {
                    Debug.LogError(
                        "[Placement] MRUK room load timed out because saved room anchors could not be localized.");
                    SetStatus("ROOM TRACKING LOST\nRUN SPACE SETUP", Color.yellow);
                    return;
                }

                var loadResult = await roomLoadTask;
                Debug.Log($"[Placement] MRUK room load completed: {loadResult}.");
                if (loadResult != MRUK.LoadDeviceResult.Success)
                {
                    SetStatus(
                        loadResult == MRUK.LoadDeviceResult.NoRoomsFound
                            ? "NO ROOM DATA\nRUN SPACE SETUP"
                            : $"ROOM ERROR: {loadResult}",
                        Color.yellow);
                    return;
                }

                currentRoom = mruk.GetCurrentRoom();
                if (currentRoom == null)
                {
                    SetStatus("ROOM NOT FOUND", Color.yellow);
                    return;
                }

                SetStatus("ROOM READY - AIM AT SURFACE");
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
                "Safe Exit",
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
            rightTriggerAction = CreateAction(
                "Right Trigger",
                InputActionType.Value,
                "<XRController>{RightHand}/trigger");
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
            DisposeAction(ref rightTriggerAction);
            DisposeAction(ref leftGripAction);
            DisposeAction(ref rightPositionAction);
            DisposeAction(ref rightRotationAction);
            ClearMoveTargetMarkers();
        }

        private void Update()
        {
            EnsureControllerAnchor();
            UpdateOpenXrControllerPose();
            UpdatePlacementPreview();
            UpdateControllerBeam();
            UpdateInput();
        }

        private void OnBeforeRender()
        {
            EnsureControllerAnchor();
            UpdateOpenXrControllerPose();
            UpdateControllerBeam();
        }

        private void OnApplicationPause(bool isPaused)
        {
            if (isPaused)
            {
                if (controllerBeam != null)
                    controllerBeam.enabled = false;
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
            Debug.Log("[Input] Refreshing right controller pose after XR focus restore.");
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
            if (rightControllerAnchor != null && trackingSpace != null)
                return;

            if (rightControllerAnchor == null)
            {
                var anchorObject = GameObject.Find("RightControllerAnchor");
                if (anchorObject != null)
                    rightControllerAnchor = anchorObject.transform;
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
            if (rightControllerAnchor == null ||
                trackingSpace == null ||
                rightPositionAction?.activeControl == null ||
                rightRotationAction?.activeControl == null)
            {
                return;
            }

            var localPosition = rightPositionAction.ReadValue<Vector3>();
            var localRotation = rightRotationAction.ReadValue<Quaternion>();
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
                return;
            }

            rightControllerAnchor.SetPositionAndRotation(
                trackingSpace.TransformPoint(localPosition),
                trackingSpace.rotation * localRotation);
            if (controllerPoseResyncFrames > 0)
                controllerPoseResyncFrames--;
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
            if (controllerBeam != null || rightControllerAnchor == null)
                return;

            var beamObject = new GameObject("[Interaction] Controller Beam");
            beamObject.transform.SetParent(transform, false);
            controllerBeam = beamObject.AddComponent<LineRenderer>();
            controllerBeam.useWorldSpace = true;
            controllerBeam.positionCount = 2;
            controllerBeam.startWidth = ControllerBeamWidth;
            controllerBeam.endWidth = ControllerBeamWidth * 0.5f;
            controllerBeam.numCapVertices = 4;
            controllerBeam.shadowCastingMode =
                UnityEngine.Rendering.ShadowCastingMode.Off;
            controllerBeam.receiveShadows = false;
            RuntimeMaterialUtility.ApplySharedUnlit(
                controllerBeam,
                EditBeamColor);
        }

        private void UpdateControllerBeam()
        {
            EnsureControllerBeam();
            if (controllerBeam == null || rightControllerAnchor == null)
                return;
            if (controllerPoseResyncFrames > 0)
            {
                controllerBeam.enabled = false;
                return;
            }

            var direction = rightControllerAnchor.forward.normalized;
            if (direction.sqrMagnitude < 0.0001f)
            {
                controllerBeam.enabled = false;
                return;
            }

            controllerBeam.enabled = true;
            var maximumDistance =
                AppInteractionModePolicy.AllowsEditing(interactionMode)
                    ? MaxPlacementDistance
                    : MaxInteractionDistance;
            var ray = new Ray(rightControllerAnchor.position, direction);
            var beamDistance = maximumDistance;

            if (AppInteractionModePolicy.AllowsEditing(interactionMode))
            {
                if (currentRoom != null &&
                    currentRoom.Raycast(
                        ray,
                        maximumDistance,
                        PlacementSurfaceFilter,
                        out var roomHit,
                        out _))
                {
                    beamDistance = roomHit.distance;
                }
            }
            else if (TryGetNearestInstrumentHitDistance(
                         ray,
                         maximumDistance,
                         out var instrumentDistance))
            {
                beamDistance = instrumentDistance;
            }

            controllerBeam.SetPosition(
                0,
                ray.origin + direction * ControllerBeamStartOffset);
            controllerBeam.SetPosition(
                1,
                ray.origin + direction * Mathf.Max(
                    beamDistance,
                    ControllerBeamStartOffset));
            RuntimeMaterialUtility.SetColor(
                controllerBeam,
                AppInteractionModePolicy.AllowsEditing(interactionMode)
                    ? EditBeamColor
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
            isAimingAtPlacedObject = false;
            SetMoveTargetMarkersVisible(false);
            if (!AppInteractionModePolicy.AllowsEditing(interactionMode) ||
                currentRoom == null ||
                rightControllerAnchor == null ||
                operationInProgress)
            {
                SetPreviewVisible(false);
                return;
            }

            if (!groupMoveArmed && groupMoveSelection.Count > 0)
            {
                SetPreviewVisible(false);
                SetStatus(
                    $"{groupMoveSelection.Count} SELECTED | " +
                    "CYAN = FIRST ANCHOR\n" +
                    "TRIGGER TO CHANGE | GRIP+A MOVE\n" +
                    "Y H-ALIGN | GRIP+Y V-ALIGN",
                    new Color(1f, 0.75f, 0.15f));
                return;
            }

            if (!groupMoveArmed &&
                TryResolvePlacedInteraction(out _, out _))
            {
                isAimingAtPlacedObject = true;
                SetPreviewVisible(false);
                SetStatus(
                    "EXISTING OBJECT AIMED\n" +
                    "TRIGGER SELECT | CLICK DELETE",
                    Color.white);
                return;
            }

            var ray = new Ray(rightControllerAnchor.position, rightControllerAnchor.forward);
            if (!currentRoom.Raycast(
                    ray,
                    MaxPlacementDistance,
                    PlacementSurfaceFilter,
                    out var hit,
                    out var sceneAnchor) ||
                !TryGetSurface(sceneAnchor.Label, out currentSurface))
            {
                SetPreviewVisible(false);
                SetStatus("ROOM READY - AIM AT WALL/FLOOR/CEILING");
                return;
            }

            var cameraForward = Camera.main != null ? Camera.main.transform.forward : Vector3.forward;
            currentPlacementPose = PlacementPoseUtility.FromSurface(
                hit.point + hit.normal.normalized * SurfaceOffset,
                hit.normal,
                cameraForward);
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
                          "X CANCEL"
                        : $"MOVE BLOCKED: {invalidReason}\n" +
                          $"TARGET: {currentSurface.ToString().ToUpperInvariant()} | X CANCEL",
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
                $"{MockInstrumentCatalog.GetDisplayName(selectedKind)} | " +
                $"{MockInstrumentThemeCatalog.GetDisplayName(selectedTheme)}\n" +
                $"{currentSurface.ToString().ToUpperInvariant()} | " +
                $"{placements.Count:00}/{PlacementDocument.MaximumActivePlacements:00}\n" +
                (placementPoseWasAdjusted ? "AUTO OFFSET: OVERLAP AVOIDED\n" : string.Empty) +
                "STICK \u2190/\u2192 TYPE \u2191/\u2193 THEME\n" +
                "TRIGGER SELECT | A PLACE | CLICK DELETE\n" +
                "Y H-ALIGN | GRIP+Y V-ALIGN\n" +
                "GRIP+A MOVE | L-STICK UNDO\n" +
                "GRIP+L-STICK REDO | X OPERATE");
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
            var trigger = Mathf.Max(
                OVRInput.Get(
                    OVRInput.RawAxis1D.RIndexTrigger,
                    OVRInput.Controller.RTouch),
                ReadFloat(rightTriggerAction));
            var leftGrip = Mathf.Max(
                OVRInput.Get(
                    OVRInput.RawAxis1D.LHandTrigger,
                    OVRInput.Controller.LTouch),
                ReadFloat(leftGripAction));
            var groupMoveChord =
                leftGrip >= GroupMoveGripThreshold && aButton;
            var verticalAlignChord =
                leftGrip >= GroupMoveGripThreshold && yButton;
            var editTrigger = trigger >= TriggerPressThreshold;
            var modeToggled = false;

            if (UpdateSafeExit(bButton))
                return;

            if (!operationInProgress &&
                currentRoom != null &&
                xButton &&
                !previousXButton)
            {
                if (groupMoveArmed &&
                    AppInteractionModePolicy.AllowsEditing(interactionMode))
                {
                    ClearGroupMoveSelection();
                    SetModeStatus();
                    PulseHaptics();
                }
                else
                {
                    ToggleInteractionMode(trigger);
                }
                modeToggled = true;
            }

            if (!modeToggled &&
                AppInteractionModePolicy.AllowsEditing(interactionMode))
            {
                if (!groupMoveArmed &&
                    groupMoveSelection.Count == 0 &&
                    !thumbstickButton)
                {
                    UpdateSelection(thumbstick);
                }

                var editActionConsumed = false;
                if (!operationInProgress &&
                    !groupMoveArmed &&
                    editTrigger &&
                    !previousEditTrigger)
                {
                    ToggleAimedSelection();
                    editActionConsumed = true;
                }
                if (!editActionConsumed &&
                    !operationInProgress &&
                    !groupMoveArmed &&
                    leftThumbstickButton &&
                    !previousLeftThumbstickButton)
                {
                    if (leftGrip >= GroupMoveGripThreshold)
                        RedoLastEdit();
                    else
                        UndoLastEdit();
                    editActionConsumed = true;
                }
                if (!editActionConsumed &&
                    !operationInProgress &&
                    !groupMoveArmed &&
                    groupMoveChord &&
                    !previousGroupMoveChord)
                {
                    HandleGroupMoveAction();
                    editActionConsumed = true;
                }
                if (!editActionConsumed &&
                    !operationInProgress &&
                    groupMoveArmed &&
                    hasPlacementPose &&
                    aButton &&
                    !previousAButton)
                {
                    HandleGroupMoveAction();
                    editActionConsumed = true;
                }
                if (!editActionConsumed &&
                    !operationInProgress &&
                    !groupMoveArmed &&
                    yButton &&
                    !previousYButton)
                {
                    AlignSelection(verticalAlignChord);
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
                    !groupMoveArmed &&
                    groupMoveSelection.Count == 0 &&
                    placements.Count > 0 &&
                    thumbstickButton &&
                    !previousThumbstickButton)
                {
                    DeleteAimedInstrument();
                }
            }
            else
            {
                UpdateSelection(Vector2.zero);
            }

            previousAButton = aButton;
            previousXButton = xButton;
            previousYButton = yButton;
            previousGroupMoveChord = groupMoveChord;
            previousThumbstickButton = thumbstickButton;
            previousLeftThumbstickButton = leftThumbstickButton;
            previousEditTrigger = editTrigger;
            UpdateInstrumentInteraction(trigger);
            UpdateHaptics();
        }

        private bool UpdateSafeExit(bool isPressed)
        {
            if (isExiting)
                return true;

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
                }
                return false;
            }

            exitHoldTime += Time.unscaledDeltaTime;
            SetStatus(
                $"SAFE EXIT: HOLD B {Mathf.Clamp01(exitHoldTime / ExitHoldSeconds):P0}",
                new Color(1f, 0.35f, 0.1f));
            if (exitHoldTime < ExitHoldSeconds)
                return true;

            isExiting = true;
            SetPreviewVisible(false);
            SetMoveTargetMarkersVisible(false);
            if (controllerBeam != null)
                controllerBeam.enabled = false;
            SetStatus("EXITING SAFELY", Color.green);
            Debug.Log("[Application] Safe exit requested by right B hold.");

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

        private void UpdateInstrumentInteraction(float triggerValue)
        {
            if (!AppInteractionModePolicy.AllowsInstrumentOperation(interactionMode) ||
                DevelopmentExitController.IsTriggerReserved ||
                operationInProgress)
            {
                ReleaseActiveInteraction();
                triggerEngaged = triggerValue > TriggerReleaseThreshold;
                return;
            }

            if (triggerEngaged)
            {
                if (triggerValue <= TriggerReleaseThreshold)
                {
                    ReleaseActiveInteraction();
                    triggerEngaged = false;
                }
                return;
            }

            if (triggerValue >= TriggerPressThreshold)
            {
                triggerEngaged = true;
                if (!TryResolvePlacedInteraction(
                        out activeInteraction,
                        out var reach))
                {
                    activeInteraction = null;
                    return;
                }

                activeInteraction.SetPressed(true);
                SaveInteractionState(activeInteraction);
                PulseHaptics();
                var placedKind = activePlacement?.Root != null
                    ? activePlacement.Root.GetComponent<InstrumentGreyboxContract>()?.Kind
                    : null;
                SetStatus(
                    $"{reach.ToString().ToUpperInvariant()} TRIGGER | " +
                    $"{MockInstrumentCatalog.GetDisplayName(placedKind ?? selectedKind)}\n" +
                    FormatOperationState(activeInteraction),
                    Color.green);
                return;
            }

            if (TryResolvePlacedInteraction(
                    out var hoverInteraction,
                    out var hoverReach))
            {
                SetStatus(
                    $"{hoverReach.ToString().ToUpperInvariant()} READY | " +
                    (hoverInteraction.DetentCount > 0
                        ? $"RIGHT TRIGGER: NEXT " +
                          $"{(string.IsNullOrEmpty(hoverInteraction.StateName) ? "DETENT" : "STATE")}\n" +
                          FormatOperationState(hoverInteraction)
                        : "RIGHT TRIGGER"),
                    Color.white);
            }
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

        private void ToggleInteractionMode(float triggerValue)
        {
            ReleaseActiveInteraction();
            ClearGroupMoveSelection();
            interactionMode = AppInteractionModePolicy.Toggle(interactionMode);
            triggerEngaged = triggerValue > TriggerReleaseThreshold;
            selectionAxisEngaged = false;
            SetPreviewVisible(false);
            PulseHaptics();
            SetModeStatus();
            Debug.Log($"[InteractionMode] Switched to {interactionMode} mode.");
        }

        private void SetModeStatus()
        {
            if (AppInteractionModePolicy.AllowsEditing(interactionMode))
            {
                SetStatus(
                    "EDIT MODE | X: OPERATE\n" +
                    "TRIGGER SELECT | A PLACE | CLICK DELETE\n" +
                    "Y H-ALIGN | GRIP+Y V-ALIGN\n" +
                    "GRIP+A MOVE | L-STICK UNDO\n" +
                    "GRIP+L-STICK REDO | HOLD B EXIT",
                    new Color(1f, 0.75f, 0.15f));
                return;
            }

            SetStatus(
                "OPERATION MODE | X: EDIT\n" +
                "AIM + RIGHT TRIGGER TO OPERATE\n" +
                "HOLD B 2s TO EXIT",
                new Color(0.2f, 0.9f, 1f));
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
            if (currentRoom == null ||
                !currentRoom.Raycast(
                    ray,
                    0.5f,
                    PlacementSurfaceFilter,
                    out var hit,
                    out var sceneAnchor) ||
                !TryGetSurface(sceneAnchor.Label, out var surface) ||
                surface != currentSurface ||
                Vector3.Dot(hit.normal.normalized, forward) <
                    CoplanarNormalDotThreshold)
            {
                return false;
            }

            snappedPose = new Pose(
                hit.point + hit.normal.normalized * SurfaceOffset,
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
                if (placement?.Root == null ||
                    placement.Record.surfaceKind != (int)currentSurface)
                {
                    continue;
                }

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

        private async void AlignSelection(bool vertical)
        {
            RuntimePlacement reference = null;
            var group = new List<RuntimePlacement>();
            if (groupMoveSelection.Count >= 2)
            {
                group.AddRange(groupMoveSelection);
                reference = groupMovePivot ?? group[0];
            }
            else if (TryResolvePlacedInteraction(out _, out _) &&
                     activePlacement != null)
            {
                reference = activePlacement;
                group = GetCoplanarGroup(reference);
                activePlacement = null;
            }

            if (reference == null)
            {
                SetStatus("AIM AT AN INSTRUMENT TO ALIGN", Color.yellow);
                return;
            }
            if (group.Count < 2)
            {
                SetStatus("NO OTHER INSTRUMENTS ON THIS SURFACE", Color.yellow);
                return;
            }
            if (!AreCoplanar(group, reference))
            {
                SetStatus(
                    "ALIGN BLOCKED: SELECT ONE SURFACE",
                    Color.yellow);
                return;
            }

            var right = reference.Root.transform.right;
            var up = reference.Root.transform.up;
            var axis = vertical ? up : right;
            group.Remove(reference);
            if (groupMoveSelection.Count < 2)
            {
                group.Sort((left, rightPlacement) =>
                    Vector3.Dot(
                            left.Root.transform.position -
                            reference.Root.transform.position,
                            axis)
                        .CompareTo(
                            Vector3.Dot(
                                rightPlacement.Root.transform.position -
                                reference.Root.transform.position,
                                axis)));
            }
            group.Insert(0, reference);

            var poses = new List<Pose>(group.Count);
            var referencePosition = reference.Root.transform.position;
            var referenceSize = GetBoundsSize(reference);
            var cursor =
                (vertical ? referenceSize.y : referenceSize.x) * 0.5f;
            for (var index = 0; index < group.Count; index++)
            {
                var placement = group[index];
                var size = GetBoundsSize(placement);
                var extent = vertical ? size.y : size.x;
                var position = index == 0
                    ? referencePosition
                    : referencePosition +
                      axis *
                      (cursor + PlacementSpacing + extent * 0.5f);
                poses.Add(new Pose(position, reference.Root.transform.rotation));
                if (index > 0)
                    cursor += PlacementSpacing + extent;
            }

            operationInProgress = true;
            try
            {
                if (await ApplyEditedWorldPosesAsync(group, poses, null))
                {
                    RefreshSelectionMarkers();
                    PulseHaptics();
                    SetStatus(
                        $"{(vertical ? "VERTICAL" : "HORIZONTAL")} ALIGN: " +
                        $"{group.Count} INSTRUMENT(S)",
                        Color.green);
                }
            }
            finally
            {
                operationInProgress = false;
            }
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
                groupMoveArmed = true;
                SetPreviewVisible(false);
                PulseHaptics();
                SetStatus(
                    $"GROUP SELECTED: {groupMoveSelection.Count}\n" +
                    "AIM AT WALL/FLOOR/CEILING | A CONFIRM\n" +
                    "X CANCEL",
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
                if (contract != null &&
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
                if (contract != null &&
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
                        if (other.Record.surfaceKind != (int)currentSurface)
                            continue;
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
                    placement.Record.surfaceKind != reference.Record.surfaceKind ||
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
                if (placement?.Root == null ||
                    placement.Record.surfaceKind != reference.Record.surfaceKind)
                {
                    continue;
                }

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
            groupMoveArmed = false;
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
                    "TRIGGER TO TOGGLE | GRIP+A TO MOVE",
                    new Color(1f, 0.75f, 0.15f));
            }
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
                !hasPlacementPose ||
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

            var poses = BuildGroupMoveTargetPoses();
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
            foreach (var marker in selectionMarkers.Values)
            {
                if (marker != null)
                    Destroy(marker);
            }
            selectionMarkers.Clear();
            groupMoveSelection.Clear();
            groupMovePivot = null;
            groupMoveArmed = false;
            ClearMoveTargetMarkers();
        }

        private bool TryResolvePlacedInteraction(
            out MockInstrumentInteraction interaction,
            out InstrumentInteractionHitTest.Reach reach)
        {
            interaction = null;
            reach = InstrumentInteractionHitTest.Reach.None;
            activePlacement = null;
            if (placements.Count == 0 || rightControllerAnchor == null)
                return false;

            interactionCandidates.Clear();
            for (var index = 0; index < placements.Count; index++)
            {
                if (placements[index].Interaction != null)
                    interactionCandidates.Add(placements[index].Interaction);
            }
            if (!InstrumentInteractionResolver.TryResolveBest(
                    interactionCandidates,
                    rightControllerAnchor.position,
                    rightControllerAnchor.forward,
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

        private void ReleaseActiveInteraction()
        {
            if (activeInteraction == null)
                return;

            activeInteraction.SetPressed(false);
            SaveInteractionState(activeInteraction);
            activeInteraction = null;
            activePlacement = null;
            OVRInput.SetControllerVibration(
                0f,
                0f,
                OVRInput.Controller.RTouch);
            hapticStopTime = 0f;
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
            OVRInput.SetControllerVibration(
                0.08f,
                0.25f,
                OVRInput.Controller.RTouch);
            hapticStopTime = Time.unscaledTime + HapticDuration;
        }

        private void UpdateHaptics()
        {
            if (hapticStopTime <= 0f || Time.unscaledTime < hapticStopTime)
                return;

            OVRInput.SetControllerVibration(
                0f,
                0f,
                OVRInput.Controller.RTouch);
            hapticStopTime = 0f;
        }

        private void UpdateSelection(Vector2 axis)
        {
            var magnitude = Mathf.Max(Mathf.Abs(axis.x), Mathf.Abs(axis.y));
            if (magnitude <= SelectionReleaseThreshold)
            {
                selectionAxisEngaged = false;
                return;
            }

            if (operationInProgress ||
                selectionAxisEngaged ||
                magnitude < SelectionThreshold)
            {
                return;
            }

            selectionAxisEngaged = true;
            if (Mathf.Abs(axis.x) >= Mathf.Abs(axis.y))
            {
                SetSelectedKind(
                    MockInstrumentCatalog.Cycle(
                        selectedKind,
                        axis.x < 0f ? -1 : 1));
                return;
            }

            SetSelectedTheme(
                MockInstrumentThemeCatalog.Cycle(
                    selectedTheme,
                    axis.y < 0f ? -1 : 1));
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
                $"{placements.Count:00}/{PlacementDocument.MaximumActivePlacements:00} PLACED",
                Color.green);
        }

        private async void PlaceInstrument()
        {
            if (ActivePlacementCount() >= PlacementDocument.MaximumActivePlacements)
            {
                SetStatus(
                    $"PLACEMENT LIMIT " +
                    $"{PlacementDocument.MaximumActivePlacements}/" +
                    $"{PlacementDocument.MaximumActivePlacements}",
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
                    Interaction = interaction
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
                    $"{placements.Count:00}/{PlacementDocument.MaximumActivePlacements:00}",
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
            else if (placements.Count == 1)
                target = placements[0];

            activePlacement = null;
            if (target == null)
            {
                SetStatus("AIM AT AN INSTRUMENT TO DELETE", Color.yellow);
                return;
            }
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
            var recordsToRestore = new List<PlacementRecord>();
            var pendingDeletes = new List<PlacementRecord>();
            var anchorIds = new List<string>();
            var uniqueAnchorIds = new HashSet<string>(
                StringComparer.OrdinalIgnoreCase);
            foreach (var record in placementDocument.placements)
            {
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
                    Interaction = interaction
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
                $"{recordsToRestore.Count} active, {missing} unavailable, " +
                $"{pendingDeletes.Count} pending-delete record(s) inspected.");

            if (preview != null)
            {
                MockInstrumentFactory.Destroy(preview);
                preview = null;
            }
            SetStatus(
                $"RESTORED {placements.Count}/{recordsToRestore.Count} | " +
                MockInstrumentThemeCatalog.GetDisplayName(selectedTheme) +
                (missing > 0 ? $"\n{missing} ANCHOR(S) UNAVAILABLE" : string.Empty),
                missing > 0 ? Color.yellow : Color.green);
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

        private int ActivePlacementCount()
        {
            var count = 0;
            foreach (var record in placementDocument.placements)
            {
                if (record.lifecycle == (int)PlacementLifecycle.Active)
                    count++;
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

        private static bool TryGetSurface(MRUKAnchor.SceneLabels label, out SurfaceKind surface)
        {
            if (label.HasFlag(MRUKAnchor.SceneLabels.FLOOR))
            {
                surface = SurfaceKind.Floor;
                return true;
            }

            if (label.HasFlag(MRUKAnchor.SceneLabels.CEILING))
            {
                surface = SurfaceKind.Ceiling;
                return true;
            }

            if (label.HasFlag(MRUKAnchor.SceneLabels.WALL_FACE))
            {
                surface = SurfaceKind.Wall;
                return true;
            }

            surface = default;
            return false;
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
