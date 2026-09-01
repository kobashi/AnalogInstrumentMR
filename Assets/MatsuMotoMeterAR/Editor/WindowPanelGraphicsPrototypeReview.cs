using System;
using System.IO;
using MatsuMotoMeterAR.Rendering;
using MatsuMotoMeterAR.Signals;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class WindowPanelGraphicsPrototypeReview
    {
        private const int CellWidth = 512;
        private const int CellHeight = 384;
        private const int Columns = 4;
        private const int Rows = 3;
        private const string OutputPath =
            "Builds/Reports/window-panel-WP1-prototype-contact-sheet.png";
        private const string ReportPath =
            "Builds/Reports/window-panel-WP1-prototype.md";

        private static readonly WindowPanelGraphicPreset[] Presets =
        {
            WindowPanelGraphicPreset.Orbit,
            WindowPanelGraphicPreset.Rose,
            WindowPanelGraphicPreset.Lissajous
        };

        private static readonly float[][] States =
        {
            new[] { 0f, 0f, 0f, 0f },
            new[] { 0.5f, 0.5f, 0.5f, 0.5f },
            new[] { 1f, 1f, 1f, 1f },
            new[] { 0.8f, float.NaN, 0.25f, 0.8f }
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Window Panel/" +
            "Render WP1 Prototype Review")]
        public static void Render()
        {
            Directory.CreateDirectory("Builds/Reports");
            var sceneRoot = new GameObject("[WP1 Review]");
            var cameraObject = new GameObject("[WP1 Review] Camera");
            var camera = cameraObject.AddComponent<Camera>();
            var target = new RenderTexture(
                CellWidth,
                CellHeight,
                24,
                RenderTextureFormat.ARGB32)
            {
                antiAliasing = 4
            };
            var sheet = new Texture2D(
                CellWidth * Columns,
                CellHeight * Rows,
                TextureFormat.RGBA32,
                false);
            try
            {
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = new Color(0.006f, 0.009f, 0.012f, 1f);
                camera.orthographic = true;
                camera.orthographicSize = 0.82f;
                camera.nearClipPlane = 0.01f;
                camera.farClipPlane = 10f;
                camera.transform.position = new Vector3(0f, 0f, 2f);
                camera.transform.rotation = Quaternion.Euler(0f, 180f, 0f);
                camera.targetTexture = target;

                BuildPanel(sceneRoot.transform);
                var view = WindowPanelGraphicsPrototypeView.Create(
                    sceneRoot.transform);
                // The display cube front is at local Z 0.0525. Keep the
                // generated ribbon just above it so the front-view review
                // exercises depth testing instead of viewing through the
                // back of the panel.
                view.transform.localPosition = new Vector3(0f, 0f, 0.053f);
                for (var row = 0; row < Rows; row++)
                for (var column = 0; column < Columns; column++)
                {
                    view.SetPreset(Presets[row]);
                    for (var slot = 0; slot < 4; slot++)
                        view.SetSlot(slot, States[column][slot], true);
                    view.ApplyNow();
                    var cell = RenderCell(camera, target);
                    sheet.SetPixels32(
                        column * CellWidth,
                        (Rows - row - 1) * CellHeight,
                        CellWidth,
                        CellHeight,
                        cell.GetPixels32());
                    UnityEngine.Object.DestroyImmediate(cell);
                }
                sheet.Apply(false, false);
                File.WriteAllBytes(OutputPath, sheet.EncodeToPNG());
                File.WriteAllText(
                    ReportPath,
                    "# Window Panel WP1 prototype\n\n" +
                    "Result: **RENDERED**\n\n" +
                    "- Rows: Orbit / Rose / Lissajous\n" +
                    "- Columns: all minimum / all neutral / all maximum / " +
                    "invalid Balance\n" +
                    "- Geometry: 2 contours, 64 samples, 256 vertices, " +
                    "768 indices\n" +
                    "- Renderer: 1 MeshRenderer / 1 shared material\n" +
                    "- Production prefab / FBX / persistence: unchanged\n");
                AssetDatabase.Refresh();
                Debug.Log($"Window Panel WP1 review: {OutputPath}");
            }
            finally
            {
                camera.targetTexture = null;
                if (RenderTexture.active == target)
                    RenderTexture.active = null;
                target.Release();
                UnityEngine.Object.DestroyImmediate(target);
                UnityEngine.Object.DestroyImmediate(sheet);
                UnityEngine.Object.DestroyImmediate(cameraObject);
                UnityEngine.Object.DestroyImmediate(sceneRoot);
            }
        }

        private static void BuildPanel(Transform parent)
        {
            CreateBlock(
                "Display",
                parent,
                new Vector3(0f, 0f, 0.035f),
                new Vector3(2.12f, 1.20f, 0.035f),
                new Color(0.012f, 0.020f, 0.028f, 1f));
            var frame = new Color(0.13f, 0.16f, 0.18f, 1f);
            CreateBlock("Top", parent,
                new Vector3(0f, 0.61f, 0.015f),
                new Vector3(2.22f, 0.10f, 0.055f), frame);
            CreateBlock("Bottom", parent,
                new Vector3(0f, -0.61f, 0.015f),
                new Vector3(2.22f, 0.10f, 0.055f), frame);
            CreateBlock("Left", parent,
                new Vector3(-1.06f, 0f, 0.015f),
                new Vector3(0.10f, 1.12f, 0.055f), frame);
            CreateBlock("Right", parent,
                new Vector3(1.06f, 0f, 0.015f),
                new Vector3(0.10f, 1.12f, 0.055f), frame);
        }

        private static void CreateBlock(
            string name,
            Transform parent,
            Vector3 position,
            Vector3 scale,
            Color color)
        {
            var block = GameObject.CreatePrimitive(PrimitiveType.Cube);
            block.name = name;
            block.transform.SetParent(parent, false);
            block.transform.localPosition = position;
            block.transform.localScale = scale;
            UnityEngine.Object.DestroyImmediate(
                block.GetComponent<Collider>());
            RuntimeMaterialUtility.ApplySharedUnlit(
                block.GetComponent<Renderer>(),
                color);
        }

        private static Texture2D RenderCell(
            Camera camera,
            RenderTexture target)
        {
            var previous = RenderTexture.active;
            camera.Render();
            RenderTexture.active = target;
            var image = new Texture2D(
                CellWidth,
                CellHeight,
                TextureFormat.RGBA32,
                false);
            image.ReadPixels(
                new Rect(0, 0, CellWidth, CellHeight),
                0,
                0,
                false);
            image.Apply(false, false);
            RenderTexture.active = previous;
            return image;
        }
    }
}
