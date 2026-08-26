using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace MatsuMotoMeterAR.Rendering
{
    public static class RuntimeMaterialUtility
    {
        private const string BuiltInMaterialPath =
            "Materials/MAT_RuntimeBuiltInUnlit";
        private const string UrpMaterialPath =
            "Materials/MAT_RuntimeUrpUnlit";
        private const string DepthTestedTextMaterialPath =
            "Materials/MAT_RuntimeDepthTestedText";

        private static readonly int ColorId = Shader.PropertyToID("_Color");
        private static readonly int BaseColorId = Shader.PropertyToID("_BaseColor");
        private static readonly int EmissionColorId = Shader.PropertyToID("_EmissionColor");
        private static readonly MaterialPropertyBlock SharedProperties = new();
        private static Material runtimeUnlitTemplate;
        private static Material depthTestedTextTemplate;
        private static readonly Dictionary<Texture, Material>
            DepthTestedTextMaterials = new();
        private static bool? templateUsesUrp;

        public static Material CreateUnlit(Color color)
        {
            var currentPipeline = GraphicsSettings.currentRenderPipeline;
            var usesUrp = currentPipeline is UniversalRenderPipelineAsset;
            if (currentPipeline != null && !usesUrp)
            {
                Debug.LogError(
                    $"Unsupported render pipeline: {currentPipeline.GetType().FullName}.");
                return null;
            }
            if (runtimeUnlitTemplate == null || templateUsesUrp != usesUrp)
            {
                var materialPath = usesUrp ? UrpMaterialPath : BuiltInMaterialPath;
                runtimeUnlitTemplate = Resources.Load<Material>(materialPath);
                templateUsesUrp = usesUrp;

                Debug.Log(
                    $"Runtime rendering pipeline: {(usesUrp ? "URP" : "Built-in")}; " +
                    $"material: {materialPath}.");
            }

            if (runtimeUnlitTemplate == null)
            {
                Debug.LogError(
                    $"Runtime {(usesUrp ? "URP" : "Built-in")} unlit material could not be loaded.");
                return null;
            }

            var material = new Material(runtimeUnlitTemplate)
            {
                name = usesUrp ? "MAT_RuntimeUrpUnlit" : "MAT_RuntimeBuiltInUnlit"
            };
            SetMaterialColor(material, color);
            return material;
        }

        public static void ApplyUnlit(Renderer renderer, Color color)
        {
            if (renderer == null)
                return;

            var material = CreateUnlit(color);
            if (material != null)
                renderer.sharedMaterial = material;
        }

        public static void ApplySharedUnlit(Renderer renderer, Color color)
        {
            if (renderer == null)
                return;

            var template = GetUnlitTemplate();
            if (template == null)
                return;

            renderer.sharedMaterial = template;
            SetColor(renderer, color);
        }

        public static void ApplyDepthTestedText(TextMesh text)
        {
            if (text == null)
                return;

            var renderer = text.GetComponent<MeshRenderer>();
            if (renderer == null)
                return;

            if (depthTestedTextTemplate == null)
            {
                depthTestedTextTemplate =
                    Resources.Load<Material>(DepthTestedTextMaterialPath);
            }
            if (depthTestedTextTemplate == null)
            {
                Debug.LogError(
                    $"Depth-tested text material could not be loaded: " +
                    $"{DepthTestedTextMaterialPath}.");
                return;
            }

            var sourceMaterial = renderer.sharedMaterial;
            var fontTexture = sourceMaterial != null
                ? sourceMaterial.mainTexture
                : text.font?.material?.mainTexture;
            if (fontTexture == null)
            {
                Debug.LogError("TextMesh font atlas could not be resolved.");
                return;
            }

            if (!DepthTestedTextMaterials.TryGetValue(
                    fontTexture,
                    out var material) ||
                material == null)
            {
                material = new Material(depthTestedTextTemplate)
                {
                    name = $"MAT_RuntimeDepthTestedText_{fontTexture.name}",
                    mainTexture = fontTexture
                };
                DepthTestedTextMaterials[fontTexture] = material;
            }
            renderer.sharedMaterial = material;
        }

        public static void SetColor(Renderer renderer, Color color)
        {
            if (renderer == null || renderer.sharedMaterial == null)
                return;

            renderer.GetPropertyBlock(SharedProperties);
            if (renderer.sharedMaterial.HasProperty(BaseColorId))
                SharedProperties.SetColor(BaseColorId, color);
            if (renderer.sharedMaterial.HasProperty(ColorId))
                SharedProperties.SetColor(ColorId, color);
            renderer.SetPropertyBlock(SharedProperties);
            SharedProperties.Clear();
        }

        public static void SetEmissionColor(Renderer renderer, Color color)
        {
            if (renderer == null ||
                renderer.sharedMaterial == null ||
                !renderer.sharedMaterial.HasProperty(EmissionColorId))
                return;

            renderer.GetPropertyBlock(SharedProperties);
            SharedProperties.SetColor(EmissionColorId, color);
            renderer.SetPropertyBlock(SharedProperties);
            SharedProperties.Clear();
        }

        private static Material GetUnlitTemplate()
        {
            var currentPipeline = GraphicsSettings.currentRenderPipeline;
            var usesUrp = currentPipeline is UniversalRenderPipelineAsset;
            if (currentPipeline != null && !usesUrp)
            {
                Debug.LogError(
                    $"Unsupported render pipeline: {currentPipeline.GetType().FullName}.");
                return null;
            }
            if (runtimeUnlitTemplate == null || templateUsesUrp != usesUrp)
            {
                var materialPath = usesUrp ? UrpMaterialPath : BuiltInMaterialPath;
                runtimeUnlitTemplate = Resources.Load<Material>(materialPath);
                templateUsesUrp = usesUrp;

                Debug.Log(
                    $"Runtime rendering pipeline: {(usesUrp ? "URP" : "Built-in")}; " +
                    $"material: {materialPath}.");
            }

            if (runtimeUnlitTemplate == null)
            {
                Debug.LogError(
                    $"Runtime {(usesUrp ? "URP" : "Built-in")} unlit material could not be loaded.");
            }
            return runtimeUnlitTemplate;
        }

        private static void SetMaterialColor(Material material, Color color)
        {
            if (material.HasProperty(BaseColorId))
                material.SetColor(BaseColorId, color);

            if (material.HasProperty(ColorId))
                material.SetColor(ColorId, color);
        }
    }
}
