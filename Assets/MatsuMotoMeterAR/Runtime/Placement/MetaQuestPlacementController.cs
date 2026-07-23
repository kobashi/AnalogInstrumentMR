using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using MatsuMotoMeterAR.Anchors;
using MatsuMotoMeterAR.Development;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;
using Meta.XR.MRUtilityKit;
using UnityEngine;

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

        private static readonly LabelFilter PlacementSurfaceFilter = new(
            MRUKAnchor.SceneLabels.WALL_FACE |
            MRUKAnchor.SceneLabels.FLOOR |
            MRUKAnchor.SceneLabels.CEILING);

        private Transform rightControllerAnchor;
        private TextMesh statusLabel;
        private MRUKRoom currentRoom;
        private GameObject preview;
        private readonly List<RuntimePlacement> placements = new();
        private readonly List<MockInstrumentInteraction> interactionCandidates = new();
        private IPlacementStore placementStore;
        private IAnchorService anchorService;
        private PlacementDocument placementDocument;
        private Pose currentPlacementPose;
        private SurfaceKind currentSurface;
        private MockInstrumentKind selectedKind = MockInstrumentKind.RoundMeter;
        private MockInstrumentTheme selectedTheme =
            MockInstrumentThemeCatalog.DefaultTheme;
        private MockInstrumentInteraction activeInteraction;
        private RuntimePlacement activePlacement;
        private float hapticStopTime;
        private bool hasPlacementPose;
        private bool previousAButton;
        private bool previousThumbstickButton;
        private bool selectionAxisEngaged;
        private bool triggerEngaged;
        private bool operationInProgress;

        private sealed class RuntimePlacement
        {
            public PlacementRecord Record;
            public AnchorRecord Anchor;
            public GameObject Root;
            public MockInstrumentInteraction Interaction;
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
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                SetStatus("PLACEMENT START FAILED", Color.red);
            }
        }

        private void Update()
        {
            EnsureControllerAnchor();
            UpdatePlacementPreview();
            UpdateInput();
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
            statusLabel.characterSize = 0.011f;
            statusLabel.fontSize = 64;
            statusLabel.color = Color.white;
        }

        private void EnsureControllerAnchor()
        {
            if (rightControllerAnchor != null)
                return;

            var anchorObject = GameObject.Find("RightControllerAnchor");
            if (anchorObject != null)
                rightControllerAnchor = anchorObject.transform;
        }

        private void UpdatePlacementPreview()
        {
            hasPlacementPose = false;
            if (currentRoom == null || rightControllerAnchor == null || operationInProgress)
            {
                SetPreviewVisible(false);
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

            if (!MockInstrumentCatalog.SupportsSurface(selectedKind, currentSurface))
            {
                SetPreviewVisible(false);
                SetStatus(
                    $"{MockInstrumentCatalog.GetDisplayName(selectedKind)}\n" +
                    $"NOT ALLOWED ON {currentSurface.ToString().ToUpperInvariant()}",
                    Color.yellow);
                return;
            }

            hasPlacementPose = true;

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
                "STICK \u2190/\u2192 TYPE \u2191/\u2193 THEME\n" +
                "A PLACE | AIM + CLICK DELETE");
        }

        private void UpdateInput()
        {
            var aButton = OVRInput.Get(OVRInput.RawButton.A, OVRInput.Controller.RTouch);
            var thumbstickButton = OVRInput.Get(
                OVRInput.RawButton.RThumbstick,
                OVRInput.Controller.RTouch);
            var thumbstick = OVRInput.Get(
                OVRInput.RawAxis2D.RThumbstick,
                OVRInput.Controller.RTouch);
            var trigger = OVRInput.Get(
                OVRInput.RawAxis1D.RIndexTrigger,
                OVRInput.Controller.RTouch);

            if (!thumbstickButton)
                UpdateSelection(thumbstick);

            if (!operationInProgress && hasPlacementPose && aButton && !previousAButton)
                PlaceInstrument();
            if (!operationInProgress &&
                placements.Count > 0 &&
                thumbstickButton &&
                !previousThumbstickButton)
            {
                DeleteAimedInstrument();
            }

            previousAButton = aButton;
            previousThumbstickButton = thumbstickButton;
            UpdateInstrumentInteraction(trigger);
            UpdateHaptics();
        }

        private void UpdateInstrumentInteraction(float triggerValue)
        {
            if (DevelopmentExitController.IsTriggerReserved || operationInProgress)
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
                    $"VALUE {activeInteraction.NormalizedValue:0.000}",
                    Color.green);
                return;
            }

            if (TryResolvePlacedInteraction(out _, out var hoverReach))
            {
                SetStatus(
                    $"{hoverReach.ToString().ToUpperInvariant()} READY | " +
                    "RIGHT TRIGGER",
                    Color.white);
            }
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
                SetStatus("PLACEMENT LIMIT 24/24", Color.yellow);
                return;
            }

            ReleaseActiveInteraction();
            operationInProgress = true;
            SetPreviewVisible(false);
            SetStatus("SAVING SPATIAL ANCHOR...");

            GameObject newInstrument = null;
            AnchorRecord newAnchor = null;
            PlacementRecord newRecord = null;
            try
            {
                newInstrument = MockInstrumentFactory.Create(
                    selectedKind,
                    currentPlacementPose,
                    theme: selectedTheme);
                newAnchor = await anchorService.CreateAsync(
                    newInstrument,
                    currentSurface);
                var interaction = newInstrument
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                newRecord = new PlacementRecord
                {
                    placementId = Guid.NewGuid().ToString("D"),
                    anchorId = newAnchor.Id,
                    instrumentTypeId = MockInstrumentCatalog.GetTypeId(selectedKind),
                    surfaceKind = (int)currentSurface,
                    localOffset = SerializablePose.Identity,
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
                    Root = newInstrument,
                    Interaction = interaction
                });
                Debug.Log(
                    $"[Placement] Committed {newRecord.placementId} " +
                    $"{newRecord.instrumentTypeId} anchor {newRecord.anchorId}.");
                newInstrument = null;
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
                if (newAnchor != null)
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
                if (newInstrument != null)
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
            operationInProgress = true;
            SetStatus("DELETING INSTRUMENT...");

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

                if (!await anchorService.RemoveAsync(target.Anchor))
                    throw new InvalidOperationException("Spatial anchor erase failed.");

                placements.Remove(target);
                var recordRemoved = placementDocument.placements.Remove(target.Record);
                var removalSaved = SavePlacementDocument();
                Debug.Log(
                    $"[Placement] Delete finalized for {target.Record.placementId}: " +
                    $"recordRemoved={recordRemoved}, saved={removalSaved}.");
                if (!removalSaved)
                {
                    Debug.LogWarning(
                        "Anchor was erased; pending-delete record remains for recovery.");
                }
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
            foreach (var record in placementDocument.placements)
            {
                if (record.lifecycle == (int)PlacementLifecycle.PendingDelete)
                    pendingDeletes.Add(record);
                else if (record.lifecycle == (int)PlacementLifecycle.Active ||
                         record.lifecycle == (int)PlacementLifecycle.Unavailable)
                    recordsToRestore.Add(record);
                else
                    continue;
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
                var root = MockInstrumentFactory.Create(
                    kind,
                    new Pose(anchor.Pose.Position, anchor.Pose.Rotation),
                    theme: selectedTheme);
                if (!anchorService.Bind(anchor, root))
                {
                    missing++;
                    MockInstrumentFactory.Destroy(root);
                    Debug.LogWarning(
                        $"[Placement] Saved anchor {record.anchorId} could not bind.");
                    continue;
                }

                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                interaction.SetNormalizedValue(record.normalizedValue);
                placements.Add(new RuntimePlacement
                {
                    Record = record,
                    Anchor = anchor,
                    Root = root,
                    Interaction = interaction
                });
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
