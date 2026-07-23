using System;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.XR.OpenXR;
using UnityEngine.XR.OpenXR.Features.MetaQuestSupport;

namespace MatsuMotoMeterAR.Editor
{
    internal sealed class RenderPipelineMigrationValidator : IPreprocessBuildWithReport
    {
        private const string BuiltInMaterialPath =
            "Assets/MatsuMotoMeterAR/Resources/Materials/MAT_RuntimeBuiltInUnlit.mat";
        private const string UrpMaterialPath =
            "Assets/MatsuMotoMeterAR/Resources/Materials/MAT_RuntimeUrpUnlit.mat";

        public int callbackOrder => 0;

        [MenuItem("Tools/MatsuMotoMeterAR/Validate Render Pipeline Migration")]
        private static void ValidateFromMenu()
        {
            Validate();
            Debug.Log("Render pipeline migration validation passed.");
        }

        public void OnPreprocessBuild(BuildReport report)
        {
            try
            {
                Validate();
            }
            catch (Exception exception)
            {
                throw new BuildFailedException(
                    $"Render pipeline migration validation failed: {exception.Message}");
            }
        }

        private static void Validate()
        {
            ValidateMaterial(
                BuiltInMaterialPath,
                "Unlit/Color",
                "_Color");
            ValidateMaterial(
                UrpMaterialPath,
                "Universal Render Pipeline/Unlit",
                "_BaseColor");

            var defaultPipeline = GraphicsSettings.defaultRenderPipeline;
            var qualityPipeline = QualitySettings.renderPipeline;
            var activePipeline = qualityPipeline != null
                ? qualityPipeline
                : defaultPipeline;

            if (activePipeline != null && activePipeline is not UniversalRenderPipelineAsset)
            {
                throw new InvalidOperationException(
                    $"Unsupported active Render Pipeline Asset: {activePipeline.GetType().FullName}.");
            }

            if (activePipeline is UniversalRenderPipelineAsset urpAsset)
                ValidateQuestUrpSettings(urpAsset);

            Debug.Log(
                $"Build render pipeline: " +
                $"{(activePipeline is UniversalRenderPipelineAsset ? "URP" : "Built-in")}; " +
                $"quality: {QualitySettings.names[QualitySettings.GetQualityLevel()]}.");
        }

        private static void ValidateQuestUrpSettings(UniversalRenderPipelineAsset pipelineAsset)
        {
            if (pipelineAsset.supportsCameraDepthTexture ||
                pipelineAsset.supportsCameraOpaqueTexture ||
                pipelineAsset.supportsHDR)
            {
                throw new InvalidOperationException(
                    "Quest URP baseline requires Depth Texture, Opaque Texture, and HDR off.");
            }

            if (pipelineAsset.msaaSampleCount != 4 ||
                !Mathf.Approximately(pipelineAsset.renderScale, 1f))
            {
                throw new InvalidOperationException(
                    "Quest URP baseline requires 4x MSAA and Render Scale 1.0.");
            }

            if (!pipelineAsset.useSRPBatcher || pipelineAsset.supportsDynamicBatching)
            {
                throw new InvalidOperationException(
                    "Quest URP baseline requires SRP Batcher on and Dynamic Batching off.");
            }

            var rendererDataList = pipelineAsset.rendererDataList;
            if (rendererDataList.Length == 0 ||
                rendererDataList[0] is not UniversalRendererData rendererData)
            {
                throw new InvalidOperationException(
                    "Quest URP baseline requires a Universal Renderer.");
            }

            if (rendererData.renderingMode != RenderingMode.Forward ||
                rendererData.depthPrimingMode != DepthPrimingMode.Disabled ||
                rendererData.intermediateTextureMode != IntermediateTextureMode.Auto)
            {
                throw new InvalidOperationException(
                    "Quest renderer requires Forward, Depth Priming Disabled, " +
                    "and Intermediate Texture Auto.");
            }

            var openXrSettings =
                OpenXRSettings.GetSettingsForBuildTargetGroup(BuildTargetGroup.Android);
            var metaQuestFeature =
                openXrSettings != null
                    ? openXrSettings.GetFeature<MetaQuestFeature>()
                    : null;
            if (metaQuestFeature == null)
            {
                throw new InvalidOperationException(
                    "Android Meta Quest OpenXR feature is missing.");
            }

            var serializedFeature = new SerializedObject(metaQuestFeature);
            var foveationApi =
                serializedFeature.FindProperty("m_foveatedRenderingApi");
            if (foveationApi == null || foveationApi.intValue != 1)
            {
                throw new InvalidOperationException(
                    "URP requires the Meta Quest SRP Foveation API.");
            }
        }

        private static void ValidateMaterial(
            string assetPath,
            string expectedShaderName,
            string requiredColorProperty)
        {
            var material = AssetDatabase.LoadAssetAtPath<Material>(assetPath);
            if (material == null)
                throw new InvalidOperationException($"Material is missing: {assetPath}.");

            if (material.shader == null)
                throw new InvalidOperationException($"Shader is missing: {assetPath}.");

            if (material.shader.name != expectedShaderName)
            {
                throw new InvalidOperationException(
                    $"{assetPath} uses {material.shader.name}; expected {expectedShaderName}.");
            }

            if (material.shader.name == "Hidden/InternalErrorShader")
                throw new InvalidOperationException($"Error Shader is assigned: {assetPath}.");

            if (!material.HasProperty(requiredColorProperty))
            {
                throw new InvalidOperationException(
                    $"{assetPath} does not expose {requiredColorProperty}.");
            }
        }
    }
}
