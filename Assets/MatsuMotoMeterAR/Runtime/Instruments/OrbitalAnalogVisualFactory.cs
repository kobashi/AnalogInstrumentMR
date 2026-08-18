using MatsuMotoMeterAR.Rendering;
using UnityEngine;
#if ANALOGMR_OPUS5_R2_REVIEW
using System.Collections.Generic;
using UnityEngine.Profiling;
#endif

namespace MatsuMotoMeterAR.Instruments
{
    internal static class InstrumentThemeVisualFactory
    {
        private static readonly Color PreviewGreen = new(0.1f, 0.95f, 0.45f);
#if ANALOGMR_CANDIDATE_REVIEW
        private const string CandidateReviewConfigurationResource =
            "CandidateReviewConfiguration";
        private static CandidateReviewConfiguration candidateReviewConfiguration;
        private static bool candidateReviewConfigurationRead;
        private static bool candidateReviewMarkerLogged;
#endif
#if ANALOGMR_OPUS5_R2_REVIEW
        private static bool r2CandidateMarkerLogged;
        private static bool largeCandidateMarkerLogged;
        private static bool mediumCandidateMarkerLogged;
        private static bool atlasProfileRead;
        private static bool atlasProfileLogged;
        private static string atlasProfile;
        private static bool largeAtlasProfileRead;
        private static bool largeAtlasProfileLogged;
        private static string largeAtlasProfile;
        private static bool mediumAtlasProfileRead;
        private static bool mediumAtlasProfileLogged;
        private static string mediumAtlasProfile;
#endif

        public static bool TryBuild(
            MockInstrumentKind kind,
            MockInstrumentTheme theme,
            Transform visualSocket,
            Transform logic,
            bool preview)
        {
            var resourcePath = ResourcePath(kind, theme);
            var prefab = Resources.Load<GameObject>(resourcePath);
            if (prefab == null)
            {
                if (kind != MockInstrumentKind.ThrottleLever &&
                    kind != MockInstrumentKind.PowerSlider &&
                    kind != MockInstrumentKind.StatusIndicator &&
                    kind != MockInstrumentKind.WindowMeter &&
                    kind != MockInstrumentKind.WindowPanel)
                {
                    Debug.LogWarning(
                        $"{theme} visual prefab is missing for {kind}; " +
                        "using the primitive fallback.");
                }
                return false;
            }
#if ANALOGMR_CANDIDATE_REVIEW
            if (!candidateReviewMarkerLogged &&
                resourcePath != $"{ThemeFolder(theme)}/Prefabs/" +
                PrefabName(kind, theme))
            {
                candidateReviewMarkerLogged = true;
                Debug.Log(
                    "[CandidateReview] Manifest Resources override is active.");
            }
#endif
#if ANALOGMR_OPUS5_R2_REVIEW
            if (!r2CandidateMarkerLogged &&
                resourcePath.StartsWith("Opus5_R2/"))
            {
                r2CandidateMarkerLogged = true;
                Debug.Log(
                    "[Opus5R2Review] Candidate Resources override is active.");
            }
            if (!largeCandidateMarkerLogged &&
                resourcePath.StartsWith("Opus5_Large/"))
            {
                largeCandidateMarkerLogged = true;
                Debug.Log(
                    "[Opus5LargeReview] Candidate Resources override is active.");
            }
            if (!mediumCandidateMarkerLogged &&
                resourcePath.StartsWith("Opus5_Medium/"))
            {
                mediumCandidateMarkerLogged = true;
                Debug.Log(
                    "[Opus5MediumReview] Candidate Resources override is active.");
            }
#endif

            var visual = Object.Instantiate(prefab, visualSocket, false);
            visual.name = prefab.name;
#if ANALOGMR_OPUS5_R2_REVIEW
            if (resourcePath.StartsWith("Opus5_R2/"))
                ApplyReviewAtlasProfile(visual);
            else if (resourcePath.StartsWith("Opus5_Large/"))
                ApplyLargeReviewAtlasProfile(visual);
            else if (resourcePath.StartsWith("Opus5_Medium/"))
                ApplyMediumReviewAtlasProfile(visual);
#endif
            var manifest = visual.GetComponent<ThemeVisualManifest>();
            if (manifest == null || manifest.MotionTarget == null)
            {
                Object.DestroyImmediate(visual);
                throw new MissingReferenceException(
                    $"{theme} prefab {prefab.name} has no valid visual manifest.");
            }
            foreach (var collider in visual.GetComponentsInChildren<Collider>(true))
                DestroyComponent(collider);

            if (preview)
            {
                foreach (var renderer in visual.GetComponentsInChildren<Renderer>(true))
                {
                    var previewColor = PreviewTint(renderer.sharedMaterial);
                    RuntimeMaterialUtility.SetColor(renderer, previewColor);
                    RuntimeMaterialUtility.SetEmissionColor(
                        renderer,
                        previewColor * 0.18f);
                }
                return true;
            }

            ConfigureMotion(kind, theme, manifest, logic);
            return true;
        }

        public static bool HasVisualPrefab(
            MockInstrumentKind kind,
            MockInstrumentTheme theme)
        {
            var resourcePath = ResourcePath(kind, theme);
            return Resources.Load<GameObject>(resourcePath) != null;
        }

        private static string ResourcePath(
            MockInstrumentKind kind,
            MockInstrumentTheme theme)
        {
            var prefabName = PrefabName(kind, theme);
#if ANALOGMR_CANDIDATE_REVIEW
            var candidatePath = CandidateReviewResourcePath(prefabName);
            if (!string.IsNullOrEmpty(candidatePath))
                return candidatePath;
#endif
#if ANALOGMR_OPUS5_R2_REVIEW
            if (theme == MockInstrumentTheme.KineticSafety &&
                (kind == MockInstrumentKind.RoundMeter ||
                 kind == MockInstrumentKind.Lever ||
                 kind == MockInstrumentKind.ThrottleLever))
            {
                return $"Opus5_R2/KineticSafety/Prefabs/{prefabName}";
            }
            if (theme == MockInstrumentTheme.KineticSafety &&
                kind == MockInstrumentKind.RoundMeterMedium)
            {
                return $"Opus5_Medium/KineticSafety/Prefabs/{prefabName}";
            }
            if (theme == MockInstrumentTheme.KineticSafety &&
                (kind == MockInstrumentKind.RoundMeterLarge ||
                 kind == MockInstrumentKind.WindowMeter ||
                 kind == MockInstrumentKind.WindowPanel))
            {
                return $"Opus5_Large/KineticSafety/Prefabs/{prefabName}";
            }
#endif
            return $"{ThemeFolder(theme)}/Prefabs/{prefabName}";
        }

#if ANALOGMR_CANDIDATE_REVIEW
        private static string CandidateReviewResourcePath(string prefabName)
        {
            var configuration = LoadCandidateReviewConfiguration();
            if (configuration?.entries == null)
                return null;
            foreach (var entry in configuration.entries)
            {
                if (entry != null && entry.prefabName == prefabName)
                    return entry.resourcePath;
            }
            return null;
        }

        private static CandidateReviewConfiguration
            LoadCandidateReviewConfiguration()
        {
            if (candidateReviewConfigurationRead)
                return candidateReviewConfiguration;

            candidateReviewConfigurationRead = true;
            var asset = Resources.Load<TextAsset>(
                CandidateReviewConfigurationResource);
            if (asset == null)
            {
                Debug.LogError(
                    "[CandidateReview] Review configuration is missing.");
                return null;
            }

            candidateReviewConfiguration =
                JsonUtility.FromJson<CandidateReviewConfiguration>(asset.text);
            if (candidateReviewConfiguration?.entries == null)
            {
                Debug.LogError(
                    "[CandidateReview] Review configuration is invalid.");
                return null;
            }
            Debug.Log(
                $"[CandidateReview] candidateId=" +
                $"{candidateReviewConfiguration.candidateId}, entries=" +
                $"{candidateReviewConfiguration.entries.Length}.");
            return candidateReviewConfiguration;
        }

        [System.Serializable]
        private sealed class CandidateReviewConfiguration
        {
            public string candidateId;
            public CandidateReviewEntry[] entries;
        }

        [System.Serializable]
        private sealed class CandidateReviewEntry
        {
            public string prefabName;
            public string resourcePath;
        }
#endif

#if ANALOGMR_OPUS5_R2_REVIEW
        private static void ApplyReviewAtlasProfile(GameObject visual)
        {
            var profile = ReviewAtlasProfile();
            if (string.IsNullOrEmpty(profile))
                return;

            var root =
                $"Opus5_R2/KineticSafety/AtlasProfiles/{profile}";
            var opaque = Resources.Load<Material>(
                $"{root}/MAT_KineticSafety_V6_Atlas_Staging");
            var emissive = Resources.Load<Material>(
                $"{root}/MAT_KineticSafety_V6_Emissive_Staging");
            if (opaque == null || emissive == null)
            {
                Debug.LogError(
                    $"[Opus5R2Review] Atlas profile {profile} is missing.");
                return;
            }

            ReplaceReviewMaterials(visual, opaque, emissive);

            if (!atlasProfileLogged)
            {
                atlasProfileLogged = true;
                Debug.Log($"[Opus5R2Review] Atlas profile={profile}.");
            }
        }

        private static string ReviewAtlasProfile()
        {
            if (atlasProfileRead)
                return atlasProfile;

            atlasProfileRead = true;
#if UNITY_ANDROID && !UNITY_EDITOR
            using var unityPlayer = new AndroidJavaClass(
                "com.unity3d.player.UnityPlayer");
            using var activity = unityPlayer.GetStatic<AndroidJavaObject>(
                "currentActivity");
            using var intent = activity.Call<AndroidJavaObject>("getIntent");
            var requested = intent.Call<string>(
                "getStringExtra",
                "matsu_atlas_profile");
            if (requested == "A" || requested == "B" || requested == "BT")
                atlasProfile = requested;
#endif
            return atlasProfile;
        }

        private static void ApplyLargeReviewAtlasProfile(GameObject visual)
        {
            var profile = ReviewLargeAtlasProfile();
            var root =
                $"Opus5_Large/KineticSafety/AtlasProfiles/{profile}";
            var opaque = Resources.Load<Material>(
                $"{root}/MAT_KineticSafety_V6_Atlas_Large_Staging");
            var emissive = Resources.Load<Material>(
                $"{root}/MAT_KineticSafety_V6_Emissive_Large_Staging");
            if (opaque == null || emissive == null)
            {
                Debug.LogError(
                    $"[Opus5LargeReview] Atlas profile {profile} is missing.");
                return;
            }

            ReplaceReviewMaterials(visual, opaque, emissive);
            if (!largeAtlasProfileLogged)
            {
                largeAtlasProfileLogged = true;
                Debug.Log($"[Opus5LargeReview] Atlas profile={profile}.");
                LogLargeTextureMemory(profile, opaque, emissive);
            }
        }

        private static string ReviewLargeAtlasProfile()
        {
            if (largeAtlasProfileRead)
                return largeAtlasProfile;

            largeAtlasProfileRead = true;
            largeAtlasProfile = "Control1K";
#if UNITY_ANDROID && !UNITY_EDITOR
            using var unityPlayer = new AndroidJavaClass(
                "com.unity3d.player.UnityPlayer");
            using var activity = unityPlayer.GetStatic<AndroidJavaObject>(
                "currentActivity");
            using var intent = activity.Call<AndroidJavaObject>("getIntent");
            var requested = intent.Call<string>(
                "getStringExtra",
                "matsu_large_profile");
            if (requested == "Control1K" ||
                requested == "Same2K" ||
                requested == "Finer2K")
            {
                largeAtlasProfile = requested;
            }
#endif
            return largeAtlasProfile;
        }

        private static void ApplyMediumReviewAtlasProfile(GameObject visual)
        {
            var profile = ReviewMediumAtlasProfile();
            var root =
                $"Opus5_Medium/KineticSafety/AtlasProfiles/{profile}";
            var opaque = Resources.Load<Material>(
                $"{root}/MAT_KineticSafety_V6_Atlas_Medium_Staging");
            var emissive = Resources.Load<Material>(
                $"{root}/MAT_KineticSafety_V6_Emissive_Medium_Staging");
            if (opaque == null || emissive == null)
            {
                Debug.LogError(
                    $"[Opus5MediumReview] Atlas profile {profile} is missing.");
                return;
            }

            ReplaceReviewMaterials(visual, opaque, emissive);
            if (!mediumAtlasProfileLogged)
            {
                mediumAtlasProfileLogged = true;
                Debug.Log($"[Opus5MediumReview] Atlas profile={profile}.");
                LogTextureMemory(
                    "Opus5MediumReview",
                    profile,
                    opaque,
                    emissive);
            }
        }

        private static string ReviewMediumAtlasProfile()
        {
            if (mediumAtlasProfileRead)
                return mediumAtlasProfile;

            mediumAtlasProfileRead = true;
            mediumAtlasProfile = "Control";
#if UNITY_ANDROID && !UNITY_EDITOR
            using var unityPlayer = new AndroidJavaClass(
                "com.unity3d.player.UnityPlayer");
            using var activity = unityPlayer.GetStatic<AndroidJavaObject>(
                "currentActivity");
            using var intent = activity.Call<AndroidJavaObject>("getIntent");
            var requested = intent.Call<string>(
                "getStringExtra",
                "matsu_medium_profile");
            if (requested == "Control" || requested == "Fine")
                mediumAtlasProfile = requested;
#endif
            return mediumAtlasProfile;
        }

        private static void ReplaceReviewMaterials(
            GameObject visual,
            Material opaque,
            Material emissive)
        {
            foreach (var renderer in
                     visual.GetComponentsInChildren<Renderer>(true))
            {
                var materials = renderer.sharedMaterials;
                for (var index = 0; index < materials.Length; index++)
                {
                    var source = materials[index];
                    materials[index] =
                        source != null && source.name.Contains("Emissive")
                            ? emissive
                            : opaque;
                }
                renderer.sharedMaterials = materials;
            }
        }

        private static void LogLargeTextureMemory(
            string profile,
            Material opaque,
            Material emissive)
        {
            LogTextureMemory(
                "Opus5LargeReview",
                profile,
                opaque,
                emissive);
        }

        private static void LogTextureMemory(
            string logPrefix,
            string profile,
            Material opaque,
            Material emissive)
        {
            var textures = new HashSet<Texture>();
            foreach (var material in new[] { opaque, emissive })
            {
                foreach (var property in new[]
                         {
                             "_BaseMap",
                             "_BumpMap",
                             "_MetallicGlossMap",
                             "_EmissionMap"
                         })
                {
                    var texture = material.GetTexture(property);
                    if (texture != null)
                        textures.Add(texture);
                }
            }

            long totalBytes = 0;
            foreach (var texture in textures)
            {
                var bytes = Profiler.GetRuntimeMemorySizeLong(texture);
                totalBytes += bytes;
                if (texture is Texture2D texture2D)
                {
                    Debug.Log(
                        $"[{logPrefix}] Texture {texture.name}: " +
                        $"{texture2D.width}x{texture2D.height}, " +
                        $"format={texture2D.format}, mips={texture2D.mipmapCount}, " +
                        $"runtimeBytes={bytes}.");
                }
            }
            Debug.Log(
                $"[{logPrefix}] Resident texture summary: " +
                $"profile={profile}, count={textures.Count}, " +
                $"runtimeBytes={totalBytes}.");
        }
#endif

        private static void ConfigureMotion(
            MockInstrumentKind kind,
            MockInstrumentTheme theme,
            ThemeVisualManifest manifest,
            Transform logic)
        {
            var motionTarget = CreateRuntimeMotionTarget(
                manifest.MotionTarget,
                manifest.transform);
            switch (kind)
            {
                case MockInstrumentKind.RoundMeter:
                case MockInstrumentKind.RoundMeterMedium:
                case MockInstrumentKind.RoundMeterLarge:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Meter,
                        motionTarget,
                        Vector3.forward,
                        InstrumentGreyboxSpecification.MeterSweepDegrees,
                        0.18f);
                    break;
                case MockInstrumentKind.Lever:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Lever,
                        motionTarget,
                        Vector3.right,
                        InstrumentGreyboxSpecification.LeverMaximumAngleDegrees,
                        0.14f,
                        -InstrumentGreyboxSpecification.LeverMaximumAngleDegrees);
                    break;
                case MockInstrumentKind.ToggleSwitch:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Toggle,
                        motionTarget,
                        Vector3.right,
                        28f,
                        0.2f,
                        -28f);
                    break;
                case MockInstrumentKind.RotaryKnob:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Rotate,
                        motionTarget,
                        Vector3.forward,
                        48f,
                        1f);
                    break;
                case MockInstrumentKind.PushButton:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Press,
                        motionTarget,
                        Vector3.back,
                        0.014f,
                        0.3f);
                    break;
                case MockInstrumentKind.IndicatorLamp:
                    var warning =
                        MockInstrumentThemeCatalog.GetPalette(theme).Warning;
                    PrepareDynamicIndicator(
                        manifest.IndicatorRenderer);
                    GetOrAddMotion(logic).Configure(
                        MockInstrumentMotion.MotionKind.Pulse,
                        motionTarget,
                        Vector3.forward,
                        1f,
                        0.55f,
                        manifest.IndicatorRenderer,
                        warning);
                    break;
                case MockInstrumentKind.StatusIndicator:
                    var statusPalette =
                        MockInstrumentThemeCatalog.GetPalette(theme);
                    PrepareDynamicIndicators(
                        manifest.StateRenderers);
                    GetOrAddMotion(logic).ConfigureStatus(
                        motionTarget,
                        manifest.IndicatorRenderer,
                        statusPalette.Ready,
                        statusPalette.Warning,
                        statusPalette.Primary,
                        manifest.StateRenderers);
                    break;
                case MockInstrumentKind.ThrottleLever:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Throttle,
                        motionTarget,
                        Vector3.right,
                        InstrumentGreyboxSpecification
                            .ThrottleMaximumAngleDegrees,
                        0f,
                        -InstrumentGreyboxSpecification
                            .ThrottleMaximumAngleDegrees);
                    break;
                case MockInstrumentKind.PowerSlider:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.PowerSlider,
                        motionTarget,
                        Vector3.up,
                        InstrumentGreyboxSpecification
                            .PowerSliderTravelMeters,
                        0f);
                    break;
                case MockInstrumentKind.WindowMeter:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Meter,
                        motionTarget,
                        Vector3.forward,
                        55f,
                        0.12f);
                    break;
                case MockInstrumentKind.WindowPanel:
                    AddMotion(
                        logic,
                        MockInstrumentMotion.MotionKind.Meter,
                        motionTarget,
                        Vector3.forward,
                        42f,
                        0.1f);
                    break;
            }
        }

        private static void PrepareDynamicIndicators(
            Renderer[] renderers)
        {
            if (renderers == null)
                return;

            foreach (var renderer in renderers)
                PrepareDynamicIndicator(renderer);
        }

        private static void PrepareDynamicIndicator(
            Renderer renderer)
        {
            if (renderer == null)
                return;

            RuntimeMaterialUtility.ApplySharedUnlit(
                renderer,
                Color.black);
        }

        private static Transform CreateRuntimeMotionTarget(
            Transform source,
            Transform coordinateRoot)
        {
            var proxy = new GameObject(
                $"{source.name} Runtime Motion").transform;
            proxy.SetParent(coordinateRoot, false);
            proxy.position = source.position;
            proxy.rotation = coordinateRoot.rotation;
            proxy.localScale = Vector3.one;

            source.SetParent(proxy, true);
            return proxy;
        }

        private static void AddMotion(
            Transform logic,
            MockInstrumentMotion.MotionKind kind,
            Transform movingPart,
            Vector3 axis,
            float range,
            float frequency,
            float rotationOffset = 0f)
        {
            GetOrAddMotion(logic).Configure(
                kind,
                movingPart,
                axis,
                range,
                frequency,
                rotationOffset: rotationOffset);
        }

        private static MockInstrumentMotion GetOrAddMotion(Transform logic)
        {
            var motion = logic.GetComponent<MockInstrumentMotion>();
            return motion != null
                ? motion
                : logic.gameObject.AddComponent<MockInstrumentMotion>();
        }

        private static string PrefabName(
            MockInstrumentKind kind,
            MockInstrumentTheme theme)
        {
            var key = kind switch
            {
                MockInstrumentKind.Lever => "Lever",
                MockInstrumentKind.ToggleSwitch => "Toggle",
                MockInstrumentKind.RotaryKnob => "Rotary",
                MockInstrumentKind.PushButton => "Button",
                MockInstrumentKind.IndicatorLamp => "Lamp",
                MockInstrumentKind.StatusIndicator => "StatusIndicator",
                MockInstrumentKind.ThrottleLever => "Throttle",
                MockInstrumentKind.PowerSlider => "PowerSlider",
                MockInstrumentKind.WindowMeter => "WindowMeter",
                MockInstrumentKind.WindowPanel => "WindowPanel",
                MockInstrumentKind.RoundMeterMedium => "MeterMedium",
                MockInstrumentKind.RoundMeterLarge => "MeterLarge",
                _ => "MeterRound"
            };
            return $"PF_Visual_{key}_{ThemeFolder(theme)}";
        }

        private static string ThemeFolder(MockInstrumentTheme theme)
        {
            return theme switch
            {
                MockInstrumentTheme.ForgeBrass => "ForgeBrass",
                MockInstrumentTheme.KineticSafety => "KineticSafety",
                _ => "OrbitalAnalog"
            };
        }

        private static void DestroyComponent(Component component)
        {
            if (Application.isPlaying)
                Object.Destroy(component);
            else
                Object.DestroyImmediate(component);
        }

        private static Color PreviewTint(Material material)
        {
            var source = material != null && material.HasProperty("_BaseColor")
                ? material.GetColor("_BaseColor")
                : material != null && material.HasProperty("_Color")
                    ? material.GetColor("_Color")
                    : Color.white;
            var luminance = Mathf.Clamp01(
                source.r * 0.2126f +
                source.g * 0.7152f +
                source.b * 0.0722f);
            var shade = Mathf.Lerp(0.35f, 1f, luminance);
            return new Color(
                PreviewGreen.r * Mathf.Lerp(0.45f, 1f, shade),
                PreviewGreen.g * Mathf.Lerp(0.38f, 1f, shade),
                PreviewGreen.b * Mathf.Lerp(0.45f, 1f, shade),
                source.a);
        }
    }
}
