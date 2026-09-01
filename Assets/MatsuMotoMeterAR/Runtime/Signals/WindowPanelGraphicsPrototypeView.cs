using MatsuMotoMeterAR.Rendering;
using UnityEngine;
using UnityEngine.Rendering;

namespace MatsuMotoMeterAR.Signals
{
    public sealed class WindowPanelGraphicsPrototypeView : MonoBehaviour
    {
        private static readonly Color ActiveColor =
            new(0.20f, 0.95f, 1f, 1f);
        private static readonly Color NeutralColor =
            new(0.24f, 0.30f, 0.34f, 1f);
        private static readonly Color InvalidColor =
            new(1f, 0.22f, 0.08f, 1f);

        private readonly float[] values = new float[4];
        private readonly bool[] connected = new bool[4];
        private readonly float[] resolved = new float[4];
        private readonly Vector3[] vertices =
            new Vector3[WindowPanelGraphicGeometry.VertexCapacity];
        private readonly int[] indices =
            new int[WindowPanelGraphicGeometry.IndexCapacity];

        private Mesh mesh;
        private MeshRenderer meshRenderer;
        private WindowPanelGraphicPreset preset;

        public WindowPanelGraphicInputs CurrentInputs { get; private set; }
        public Mesh RuntimeMesh => mesh;

        public static WindowPanelGraphicsPrototypeView Create(
            Transform parent)
        {
            var root = new GameObject("WindowPanelGraphics_WP1");
            root.transform.SetParent(parent, false);
            var view = root.AddComponent<WindowPanelGraphicsPrototypeView>();
            view.EnsureBuilt();
            view.ApplyNow();
            return view;
        }

        public void SetPreset(WindowPanelGraphicPreset value)
        {
            preset = value;
        }

        public void SetSlot(int slot, float value, bool isConnected)
        {
            if (slot < 0 || slot >= values.Length)
                return;
            values[slot] = value;
            connected[slot] = isConnected;
        }

        public void ApplyNow()
        {
            EnsureBuilt();
            CurrentInputs = WindowPanelGraphicGeometry.ResolveInputs(
                values,
                connected,
                resolved);
            WindowPanelGraphicGeometry.BuildRibbon(
                preset,
                CurrentInputs,
                vertices,
                indices,
                out var vertexCount,
                out var indexCount,
                out var bounds);
            mesh.SetVertices(
                vertices,
                0,
                vertexCount,
                MeshUpdateFlags.DontRecalculateBounds |
                MeshUpdateFlags.DontValidateIndices);
            mesh.SetIndices(
                indices,
                0,
                indexCount,
                MeshTopology.Triangles,
                0,
                false);
            mesh.bounds = bounds;
            RuntimeMaterialUtility.SetColor(
                meshRenderer,
                CurrentInputs.HasInvalidInput
                    ? InvalidColor
                    : CurrentInputs.ConnectedCount == 0
                        ? NeutralColor
                        : ActiveColor);
        }

        private void EnsureBuilt()
        {
            if (mesh != null)
                return;
            var filter = gameObject.AddComponent<MeshFilter>();
            meshRenderer = gameObject.AddComponent<MeshRenderer>();
            meshRenderer.shadowCastingMode = ShadowCastingMode.Off;
            meshRenderer.receiveShadows = false;
            mesh = new Mesh
            {
                name = "WindowPanelGraphics_WP1_RuntimeMesh"
            };
            mesh.MarkDynamic();
            filter.sharedMesh = mesh;
            RuntimeMaterialUtility.ApplySharedUnlit(
                meshRenderer,
                NeutralColor);
        }

        private void OnDestroy()
        {
            if (mesh == null)
                return;
            if (Application.isPlaying)
                Destroy(mesh);
            else
                DestroyImmediate(mesh);
        }
    }
}
