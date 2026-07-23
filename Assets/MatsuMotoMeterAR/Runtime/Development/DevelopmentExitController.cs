using UnityEngine;
using UnityEngine.InputSystem;
using MatsuMotoMeterAR.PerformanceGate;
using MatsuMotoMeterAR.Rendering;

namespace MatsuMotoMeterAR.Development
{
    /// <summary>
    /// Temporary safety controls used while the Quest application is under development.
    /// Remove or disable this bootstrap before a production build.
    /// </summary>
    [DefaultExecutionOrder(-100)]
    public sealed class DevelopmentExitController : MonoBehaviour
    {
        private const float ExitHoldSeconds = 1.5f;
        private const float ExitButtonHoldSeconds = 0.75f;
        private const float HudDistance = 0.8f;
        private const float PointerDistance = 20f;
        private const float ExitAimToleranceDegrees = 4f;
        private const float ExitAimMaximumDistance = 1.5f;
        private const float ExitAimLostGraceSeconds = 0.15f;

        private InputAction secondaryButtonAction;
        private InputAction triggerButtonAction;
        private Transform hudRoot;
        private Transform rightControllerAnchor;
        private Collider exitButtonCollider;
        private Renderer exitButtonRenderer;
        private Renderer runningMarkerRenderer;
        private LineRenderer pointerLine;
        private TextMesh inputStatusLabel;
        private float secondaryButtonHoldTime;
        private float exitButtonHoldTime;
        private float lastExitAimHitTime;
        private float nextInputStatusUpdateTime;
        private bool exitAimLocked;
        private bool isQuitting;

        public static bool IsTriggerReserved { get; private set; }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
#if UNITY_EDITOR || MATSU_DEV_EXIT
            if (PerformanceGateConfiguration.IsEnabled)
                return;

            if (FindAnyObjectByType<DevelopmentExitController>() != null)
                return;

            var host = new GameObject("[Development] Exit Controls");
            DontDestroyOnLoad(host);
            host.AddComponent<DevelopmentExitController>();
#endif
        }

        private void OnEnable()
        {
            secondaryButtonAction = new InputAction(
                "Development Exit (B)",
                InputActionType.Button,
                "<XRController>{RightHand}/{secondaryButton}");
            triggerButtonAction = new InputAction(
                "Development Exit (Trigger)",
                InputActionType.Button,
                "<XRController>{RightHand}/{triggerButton}");

            secondaryButtonAction.Enable();
            triggerButtonAction.Enable();
        }

        private void OnDisable()
        {
            IsTriggerReserved = false;
            secondaryButtonAction?.Dispose();
            triggerButtonAction?.Dispose();
            secondaryButtonAction = null;
            triggerButtonAction = null;

            if (pointerLine != null)
                Destroy(pointerLine.gameObject);
        }

        private void Update()
        {
            EnsureHud();
            EnsureControllerAnchor();
            EnsurePointerLine();
            UpdateRunningMarker();

            if (isQuitting)
                return;

            UpdateInputStatus();
            UpdateSecondaryButtonExit();
            UpdatePointAndTriggerExit();
        }

        private void EnsureHud()
        {
            if (hudRoot != null)
                return;

            var camera = Camera.main;
            if (camera == null)
                return;

            var root = new GameObject("Safety HUD").transform;
            root.SetParent(camera.transform, false);
            root.localPosition = new Vector3(0f, -0.18f, HudDistance);
            hudRoot = root;

            var marker = CreateBox(
                "Running Marker",
                root,
                new Vector3(-0.19f, 0.12f, 0f),
                new Vector3(0.12f, 0.035f, 0.012f),
                new Color(0.05f, 0.9f, 1f));
            runningMarkerRenderer = marker.GetComponent<Renderer>();
            CreateLabel("APP RUNNING", root, new Vector3(-0.19f, 0.12f, -0.008f), 0.012f);

            var exitButton = CreateBox(
                "Exit Button",
                root,
                new Vector3(0.16f, 0f, 0f),
                new Vector3(0.3f, 0.12f, 0.025f),
                new Color(0.85f, 0.08f, 0.05f));
            exitButtonCollider = exitButton.GetComponent<Collider>();
            exitButtonRenderer = exitButton.GetComponent<Renderer>();
            CreateLabel("POINT + TRIGGER\nEXIT", root, new Vector3(0.16f, 0f, -0.016f), 0.011f);

            inputStatusLabel = CreateLabel(
                "B INPUT: CONNECTING",
                root,
                new Vector3(-0.05f, -0.085f, 0f),
                0.011f);
        }

        private static GameObject CreateBox(
            string objectName,
            Transform parent,
            Vector3 localPosition,
            Vector3 localScale,
            Color color)
        {
            var box = GameObject.CreatePrimitive(PrimitiveType.Cube);
            box.name = objectName;
            box.transform.SetParent(parent, false);
            box.transform.localPosition = localPosition;
            box.transform.localScale = localScale;

            RuntimeMaterialUtility.ApplyUnlit(box.GetComponent<Renderer>(), color);

            return box;
        }

        private static TextMesh CreateLabel(
            string value,
            Transform parent,
            Vector3 localPosition,
            float characterSize)
        {
            var labelObject = new GameObject(value);
            labelObject.transform.SetParent(parent, false);
            labelObject.transform.localPosition = localPosition;

            var label = labelObject.AddComponent<TextMesh>();
            label.text = value;
            label.anchor = TextAnchor.MiddleCenter;
            label.alignment = TextAlignment.Center;
            label.characterSize = characterSize;
            label.fontSize = 64;
            label.color = Color.white;
            return label;
        }

        private void EnsureControllerAnchor()
        {
            if (rightControllerAnchor != null)
                return;

            var anchorObject = GameObject.Find("RightControllerAnchor");
            if (anchorObject != null)
                rightControllerAnchor = anchorObject.transform;
        }

        private void EnsurePointerLine()
        {
            if (pointerLine != null || rightControllerAnchor == null || runningMarkerRenderer == null)
                return;

            var pointerObject = new GameObject("Development Controller Pointer");
            pointerObject.transform.SetParent(transform, false);

            pointerLine = pointerObject.AddComponent<LineRenderer>();
            pointerLine.useWorldSpace = true;
            pointerLine.positionCount = 2;
            pointerLine.startWidth = 0.004f;
            pointerLine.endWidth = 0.002f;
            pointerLine.numCapVertices = 4;
            pointerLine.sharedMaterial = RuntimeMaterialUtility.CreateUnlit(
                new Color(0.05f, 0.9f, 1f, 1f));
            SetPointerColor(new Color(0.05f, 0.9f, 1f, 0.9f));
        }

        private void UpdateRunningMarker()
        {
            if (runningMarkerRenderer == null)
                return;

            var pulse = 0.7f + 0.3f * Mathf.Sin(Time.unscaledTime * 4f);
            RuntimeMaterialUtility.SetColor(
                runningMarkerRenderer,
                new Color(0.05f, 0.9f * pulse, pulse));
        }

        private void UpdateInputStatus()
        {
            if (inputStatusLabel == null)
                return;

            var metaBPressed = OVRInput.Get(OVRInput.RawButton.B, OVRInput.Controller.RTouch);
            var metaTriggerPressed = OVRInput.Get(
                OVRInput.RawAxis1D.RIndexTrigger,
                OVRInput.Controller.RTouch) > 0.55f;
            if (metaBPressed || metaTriggerPressed)
            {
                inputStatusLabel.text = metaBPressed ? "META B DOWN" : "META TRIGGER DOWN";
                inputStatusLabel.color = Color.green;
                return;
            }

            if (Time.unscaledTime < nextInputStatusUpdateTime)
                return;

            nextInputStatusUpdateTime = Time.unscaledTime + 0.5f;
            var isReady = OVRInput.IsControllerConnected(OVRInput.Controller.RTouch) ||
                          OVRInput.GetControllerPositionTracked(OVRInput.Controller.RTouch);
            inputStatusLabel.text = isReady
                ? "META INPUT READY - HOLD B 1.5s"
                : "META INPUT NOT FOUND";
            inputStatusLabel.color = isReady ? Color.white : Color.yellow;
        }

        private void UpdateSecondaryButtonExit()
        {
            var isPressed = OVRInput.Get(OVRInput.RawButton.B, OVRInput.Controller.RTouch) ||
                            (secondaryButtonAction != null && secondaryButtonAction.IsPressed());

            secondaryButtonHoldTime = isPressed
                ? secondaryButtonHoldTime + Time.unscaledDeltaTime
                : 0f;

            UpdateExitButtonColor(isPressed, secondaryButtonHoldTime / ExitHoldSeconds);

            if (secondaryButtonHoldTime >= ExitHoldSeconds)
                QuitApplication("right controller B button");
        }

        private void UpdatePointAndTriggerExit()
        {
            if (exitButtonCollider == null || rightControllerAnchor == null)
            {
                IsTriggerReserved = false;
                if (pointerLine != null)
                    pointerLine.enabled = false;
                return;
            }

            var pointerRay = new Ray(
                rightControllerAnchor.position,
                rightControllerAnchor.forward);
            var hasExactExitHit = exitButtonCollider.Raycast(
                pointerRay,
                out var exitHit,
                PointerDistance);
            var toExitCenter = exitButtonCollider.bounds.center - pointerRay.origin;
            var isInsideAimCone = toExitCenter.sqrMagnitude > 0.0025f &&
                                  toExitCenter.sqrMagnitude <
                                  ExitAimMaximumDistance * ExitAimMaximumDistance &&
                                  Vector3.Angle(pointerRay.direction, toExitCenter) <=
                                  ExitAimToleranceDegrees;
            var hasExitAimCandidate = hasExactExitHit || isInsideAimCone;
            if (hasExitAimCandidate)
                lastExitAimHitTime = Time.unscaledTime;

            var isPointingAtExit = hasExitAimCandidate ||
                                   exitAimLocked &&
                                   Time.unscaledTime - lastExitAimHitTime <=
                                   ExitAimLostGraceSeconds;
            exitAimLocked = isPointingAtExit;
            IsTriggerReserved = isPointingAtExit;
            var pointerEnd = isPointingAtExit
                ? exitHit.collider != null ? exitHit.point : exitButtonCollider.bounds.center
                : rightControllerAnchor.position + rightControllerAnchor.forward * PointerDistance;

            if (!isPointingAtExit &&
                Physics.Raycast(pointerRay, out var nearestHit, PointerDistance))
            {
                pointerEnd = nearestHit.point;
            }

            var triggerIsPressed = OVRInput.Get(
                                       OVRInput.RawAxis1D.RIndexTrigger,
                                       OVRInput.Controller.RTouch) > 0.55f ||
                                   (triggerButtonAction != null && triggerButtonAction.IsPressed());

            if (pointerLine != null)
            {
                pointerLine.enabled = OVRInput.IsControllerConnected(OVRInput.Controller.RTouch) ||
                                      OVRInput.GetControllerPositionTracked(OVRInput.Controller.RTouch);
                pointerLine.SetPosition(0, rightControllerAnchor.position);
                pointerLine.SetPosition(1, pointerEnd);
                SetPointerColor(
                    isPointingAtExit
                        ? triggerIsPressed ? Color.yellow : Color.green
                        : new Color(0.05f, 0.9f, 1f, 1f));
            }

            exitButtonHoldTime = isPointingAtExit && triggerIsPressed
                ? exitButtonHoldTime + Time.unscaledDeltaTime
                : 0f;

            if (isPointingAtExit && inputStatusLabel != null)
            {
                inputStatusLabel.text = triggerIsPressed
                    ? $"EXIT HOLD {Mathf.Clamp01(exitButtonHoldTime / ExitButtonHoldSeconds):P0}"
                    : "EXIT TARGET - HOLD TRIGGER";
                inputStatusLabel.color = triggerIsPressed ? Color.green : Color.white;
            }

            if (isPointingAtExit)
            {
                RuntimeMaterialUtility.SetColor(
                    exitButtonRenderer,
                    triggerIsPressed
                        ? Color.Lerp(
                            Color.green,
                            Color.yellow,
                            Mathf.Clamp01(exitButtonHoldTime / ExitButtonHoldSeconds))
                        : Color.green);
            }
            else
            {
                UpdateExitButtonColor(false, 0f);
            }

            if (exitButtonHoldTime >= ExitButtonHoldSeconds)
                QuitApplication("development exit button");
        }

        private void SetPointerColor(Color color)
        {
            if (pointerLine == null)
                return;

            pointerLine.startColor = color;
            pointerLine.endColor = color;
            RuntimeMaterialUtility.SetColor(pointerLine, color);
        }

        private void OnApplicationPause(bool isPaused)
        {
            if (!isPaused)
                ResetExitState();
        }

        private void OnApplicationFocus(bool hasFocus)
        {
            if (hasFocus)
                ResetExitState();
        }

        private void ResetExitState()
        {
            isQuitting = false;
            secondaryButtonHoldTime = 0f;
            exitButtonHoldTime = 0f;
            exitAimLocked = false;
        }

        private void UpdateExitButtonColor(bool active, float progress)
        {
            if (exitButtonRenderer == null)
                return;

            var intensity = active ? Mathf.Lerp(0.55f, 1f, Mathf.Clamp01(progress)) : 0.55f;
            RuntimeMaterialUtility.SetColor(
                exitButtonRenderer,
                new Color(intensity, 0.05f, 0.03f));
        }

        private void QuitApplication(string source)
        {
            if (isQuitting)
                return;

            isQuitting = true;
            Debug.Log($"Development exit requested by {source}.");

            if (inputStatusLabel != null)
            {
                inputStatusLabel.text = "EXIT REQUESTED";
                inputStatusLabel.color = Color.green;
            }

#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#elif UNITY_ANDROID
            try
            {
                using var unityPlayer = new AndroidJavaClass("com.unity3d.player.UnityPlayer");
                using var activity = unityPlayer.GetStatic<AndroidJavaObject>("currentActivity");
                if (activity != null)
                    activity.Call("finishAndRemoveTask");
            }
            catch (AndroidJavaException exception)
            {
                Debug.LogWarning($"Could not finish the Android activity: {exception.Message}");
            }

            Application.Quit();
#else
            Application.Quit();
#endif
        }
    }
}
