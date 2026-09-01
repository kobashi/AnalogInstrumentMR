#if ANALOGMR_WINDOW_PANEL_WP1_REVIEW
using System.Collections;
using MatsuMotoMeterAR.Rendering;
using UnityEngine;

namespace MatsuMotoMeterAR.Signals
{
    internal sealed class WindowPanelQuestReviewBootstrap : MonoBehaviour
    {
        private const float RefreshIntervalSeconds = 0.1f;
        private readonly WindowPanelGraphicsPrototypeView[] views =
            new WindowPanelGraphicsPrototypeView[4];
        private float nextRefreshTime;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Install()
        {
            if (FindAnyObjectByType<WindowPanelQuestReviewBootstrap>() != null)
                return;
            var host = new GameObject("[WindowPanel WP1 Quest Review]");
            DontDestroyOnLoad(host);
            host.AddComponent<WindowPanelQuestReviewBootstrap>();
        }

        private IEnumerator Start()
        {
            Camera camera = null;
            for (var frame = 0; frame < 300 && camera == null; frame++)
            {
                camera = Camera.main;
                yield return null;
            }
            if (camera == null)
            {
                Debug.LogError("[WindowPanelWP1] Main camera unavailable.");
                yield break;
            }

            var forward = Vector3.ProjectOnPlane(
                camera.transform.forward,
                Vector3.up).normalized;
            if (forward.sqrMagnitude < 0.001f)
                forward = Vector3.forward;
            var right = Vector3.Cross(Vector3.up, forward).normalized;
            var center = camera.transform.position +
                         forward * 1.15f -
                         Vector3.up * 0.04f;
            var rotation = Quaternion.LookRotation(forward, Vector3.up);
            var presets = new[]
            {
                WindowPanelGraphicPreset.Orbit,
                WindowPanelGraphicPreset.Rose,
                WindowPanelGraphicPreset.Lissajous,
                WindowPanelGraphicPreset.Orbit
            };
            var labels = new[]
            {
                "ORBIT", "ROSE", "LISSAJOUS", "INVALID"
            };
            for (var index = 0; index < views.Length; index++)
            {
                var column = index % 2;
                var row = index / 2;
                var panel = new GameObject($"WP1 {labels[index]}");
                panel.transform.SetParent(transform, false);
                panel.transform.SetPositionAndRotation(
                    center + right * ((column - 0.5f) * 0.43f) +
                    Vector3.up * ((0.5f - row) * 0.28f),
                    rotation);
                panel.transform.localScale = Vector3.one * 0.16f;
                BuildPanel(panel.transform);
                BuildLabel(panel.transform, labels[index]);
                views[index] = WindowPanelGraphicsPrototypeView.Create(
                    panel.transform);
                views[index].SetPreset(presets[index]);
            }
            Refresh(Time.unscaledTime);
            Debug.Log(
                "[WindowPanelWP1] Review tableau ready: " +
                "Orbit/Rose/Lissajous animated at 10 Hz; invalid panel red.");
        }

        private void Update()
        {
            if (views[0] == null || Time.unscaledTime < nextRefreshTime)
                return;
            Refresh(Time.unscaledTime);
        }

        private void Refresh(float time)
        {
            nextRefreshTime = time + RefreshIntervalSeconds;
            for (var index = 0; index < 3; index++)
            {
                var offset = index * 0.73f;
                views[index].SetSlot(
                    0, 0.5f + 0.45f * Mathf.Sin(time * 0.55f + offset), true);
                views[index].SetSlot(
                    1, 0.5f + 0.45f * Mathf.Sin(time * 0.37f + offset), true);
                views[index].SetSlot(
                    2, Mathf.Repeat(time * 0.08f + index * 0.23f, 1f), true);
                views[index].SetSlot(
                    3, 0.5f + 0.5f * Mathf.Sin(time * 0.29f + offset), true);
                views[index].ApplyNow();
            }
            views[3].SetSlot(0, 0.75f, true);
            views[3].SetSlot(1, float.NaN, true);
            views[3].SetSlot(2, 0.5f, true);
            views[3].SetSlot(3, 0.8f, true);
            views[3].ApplyNow();
        }

        private static void BuildPanel(Transform parent)
        {
            CreateBlock(parent, "Display",
                new Vector3(0f, 0f, 0.035f),
                new Vector3(2.12f, 1.20f, 0.035f),
                new Color(0.012f, 0.020f, 0.028f, 1f));
            var frame = new Color(0.13f, 0.16f, 0.18f, 1f);
            CreateBlock(parent, "Top", new Vector3(0f, 0.61f, 0.015f),
                new Vector3(2.22f, 0.10f, 0.055f), frame);
            CreateBlock(parent, "Bottom", new Vector3(0f, -0.61f, 0.015f),
                new Vector3(2.22f, 0.10f, 0.055f), frame);
            CreateBlock(parent, "Left", new Vector3(-1.06f, 0f, 0.015f),
                new Vector3(0.10f, 1.12f, 0.055f), frame);
            CreateBlock(parent, "Right", new Vector3(1.06f, 0f, 0.015f),
                new Vector3(0.10f, 1.12f, 0.055f), frame);
        }

        private static void BuildLabel(Transform parent, string value)
        {
            var labelObject = new GameObject("Label");
            labelObject.transform.SetParent(parent, false);
            labelObject.transform.localPosition = new Vector3(0f, 0.76f, -0.02f);
            labelObject.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
            var text = labelObject.AddComponent<TextMesh>();
            text.text = value;
            text.anchor = TextAnchor.MiddleCenter;
            text.alignment = TextAlignment.Center;
            text.fontSize = 64;
            text.characterSize = 0.065f;
            text.color = new Color(0.72f, 0.78f, 0.82f, 1f);
            RuntimeMaterialUtility.ApplyDepthTestedText(text);
        }

        private static void CreateBlock(
            Transform parent,
            string name,
            Vector3 position,
            Vector3 scale,
            Color color)
        {
            var block = GameObject.CreatePrimitive(PrimitiveType.Cube);
            block.name = name;
            block.transform.SetParent(parent, false);
            block.transform.localPosition = position;
            block.transform.localScale = scale;
            Destroy(block.GetComponent<Collider>());
            RuntimeMaterialUtility.ApplySharedUnlit(
                block.GetComponent<Renderer>(), color);
        }
    }
}
#endif
