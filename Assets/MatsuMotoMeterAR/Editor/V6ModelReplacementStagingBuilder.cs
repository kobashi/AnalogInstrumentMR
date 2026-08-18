using System;
using System.Collections.Generic;
using System.IO;
using MatsuMotoMeterAR.Instruments;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    internal static class V6ModelReplacementStagingBuilder
    {
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates";
        private const string StagingRoot =
            CandidateRoot + "/V6ReplacementStaging";
        private const string Opus5R2CandidateId = "Opus5_R2";
        private const string Opus5R2SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/KineticSafety/staging/fbx";
        private const string Opus5R2StagingRoot =
            CandidateRoot + "/CandidateStaging/" + Opus5R2CandidateId;
        private const string Opus5LargeCandidateId = "Opus5_Large";
        private const string Opus5LargeSourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/KineticSafety/staging/large_fbx";
        private const string Opus5LargeTextureRoot =
            "ArtSource/Blender/BrushUp/Opus5/KineticSafety/textures";
        private const string Opus5LargeStagingRoot =
            CandidateRoot + "/CandidateStaging/" + Opus5LargeCandidateId;
        private const string Opus5MediumCandidateId = "Opus5_Medium";
        private const string Opus5MediumSourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/KineticSafety/staging/medium_fbx";
        private const string Opus5MediumTextureRoot =
            "ArtSource/Blender/BrushUp/Opus5/KineticSafety/textures";
        private const string Opus5MediumStagingRoot =
            CandidateRoot + "/CandidateStaging/" + Opus5MediumCandidateId;
        private const string Opus5R2ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Opus5_R2.json";
        private const string MeterM2n3ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n3.json";
        private const string MeterM2n5ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n5.json";
        private const string MeterM2n7ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n7.json";
        private const string MeterM2n8ManifestPath =
            "Assets/MatsuMotoMeterAR/Editor/Opus5CandidateManifests/" +
            "Meter_M2n8.json";

        private static readonly ThemeEntry[] Themes =
        {
            new(
                "OrbitalAnalog",
                new Color(0.10f, 0.68f, 0.78f),
                3.2f),
            new(
                "ForgeBrass",
                new Color(0.78f, 0.28f, 0.025f),
                2.8f),
            new(
                "KineticSafety",
                new Color(0.02f, 0.62f, 0.76f),
                3.4f)
        };

        private static readonly ModelEntry[] Models =
        {
            new("MeterRound", "needle_pivot"),
            new("Lever", "handle_pivot"),
            new("Toggle", "switch_pivot"),
            new("Rotary", "knob_pivot"),
            new("Button", "button_travel"),
            new("Lamp", "indicator"),
            new("Throttle", "throttle_pivot"),
            new("PowerSlider", "slider_travel"),
            new("StatusIndicator", "indicator"),
            new("MeterMedium", "needle_pivot"),
            new("MeterLarge", "needle_pivot"),
            new("WindowMeter", "needle_pivot"),
            new("WindowPanel", "vane_pivot")
        };

        private static readonly ModelEntry[] Opus5R2Models =
        {
            new("MeterRound", "needle_pivot"),
            new("Lever", "handle_pivot"),
            new("Throttle", "throttle_pivot")
        };

        private static readonly ModelEntry[] Opus5LargeModels =
        {
            new("MeterLarge", "needle_pivot"),
            new("WindowMeter", "needle_pivot"),
            new("WindowPanel", "vane_pivot")
        };

        private static readonly ModelEntry[] Opus5MediumModels =
        {
            new("MeterMedium", "needle_pivot")
        };

        private const float StandardBumpScale = 0.32f;
        private const float MediumBumpScale = 0.28f;
        private const float LargeBumpScale = 0.24f;

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build V6 Staging Prefabs")]
        public static void Build()
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var theme in Themes)
                BuildTheme(theme);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            Debug.Log(
                "V6 replacement staging is ready. Active models and " +
                "prefabs were not modified.");
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Selected Candidate Manifest")]
        public static void BuildSelectedCandidateManifest()
        {
            BuildCandidateManifest(SelectedManifestPath());
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Opus 5 R2 Manifest Candidate Staging")]
        public static void BuildOpus5R2ManifestCandidate()
        {
            BuildCandidateManifest(Opus5R2ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Meter M2n3 Manifest Candidate Staging")]
        public static void BuildMeterM2n3ManifestCandidate()
        {
            BuildCandidateManifest(MeterM2n3ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Meter M2n5 Manifest Candidate Staging")]
        public static void BuildMeterM2n5ManifestCandidate()
        {
            BuildCandidateManifest(MeterM2n5ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Meter M2n7 Manifest Candidate Staging")]
        public static void BuildMeterM2n7ManifestCandidate()
        {
            BuildCandidateManifest(MeterM2n7ManifestPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Meter M2n8 Manifest Candidate Staging")]
        public static void BuildMeterM2n8ManifestCandidate()
        {
            BuildCandidateManifest(MeterM2n8ManifestPath);
        }

        internal static string BuildCandidateManifest(string manifestPath)
        {
            var manifest = CandidateStagingManifest.Load(manifestPath);
            var resolved = ResolveManifestEntries(manifest);
            var stagingRoot =
                $"{CandidateRoot}/CandidateStaging/{manifest.candidateId}";
            var resourceRoot =
                $"{stagingRoot}/Resources/{manifest.candidateId}";
            var modelsByTheme =
                new Dictionary<string, List<ModelEntry>>(StringComparer.Ordinal);

            foreach (var candidate in resolved)
            {
                var modelRoot =
                    $"{stagingRoot}/Models/{candidate.Theme.Folder}";
                var destinationStem =
                    $"SM_{candidate.Model.Key}_{candidate.Theme.Folder}_" +
                    "V6_Material";
                CopyRequired(
                    candidate.Entry.sourceFbx,
                    $"{modelRoot}/{destinationStem}.fbx");
                if (!string.IsNullOrWhiteSpace(candidate.Entry.sourceReport))
                {
                    CopyRequired(
                        candidate.Entry.sourceReport,
                        $"{modelRoot}/{destinationStem}.json");
                }

                if (!modelsByTheme.TryGetValue(
                        candidate.Theme.Folder,
                        out var models))
                {
                    models = new List<ModelEntry>();
                    modelsByTheme.Add(candidate.Theme.Folder, models);
                }
                models.Add(candidate.Model);
            }

            Directory.CreateDirectory(stagingRoot);
            File.Copy(
                manifestPath,
                $"{stagingRoot}/candidate-manifest.json",
                true);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var theme in Themes)
            {
                if (!modelsByTheme.TryGetValue(theme.Folder, out var models))
                    continue;
                BuildTheme(
                    theme,
                    models,
                    $"{stagingRoot}/Models/{theme.Folder}",
                    resourceRoot,
                    configureTextureImporters: false,
                    useSolidRoleMaterials:
                        manifest.candidateId == "Meter_M2n5" ||
                        manifest.candidateId == "Meter_M2n7" ||
                        manifest.candidateId == "Meter_M2n8");
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            Debug.Log(
                $"Candidate {manifest.candidateId} staging is ready at " +
                $"{stagingRoot}. Active assets were not modified.");
            return stagingRoot;
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Opus 5 R2 Candidate Staging")]
        public static void BuildOpus5R2Candidate()
        {
            var theme = Themes[2];
            var modelRoot = $"{Opus5R2StagingRoot}/Models";
            Directory.CreateDirectory(modelRoot);
            foreach (var model in Opus5R2Models)
            {
                var sourceStem =
                    $"SM_{model.Key}_{theme.Folder}_V6_" +
                    $"{Opus5R2CandidateId}_Material";
                var destinationStem =
                    $"SM_{model.Key}_{theme.Folder}_V6_Material";
                CopyRequired(
                    $"{Opus5R2SourceRoot}/{sourceStem}.fbx",
                    $"{modelRoot}/{destinationStem}.fbx");
                CopyRequired(
                    $"{Opus5R2SourceRoot}/{sourceStem}.json",
                    $"{modelRoot}/{destinationStem}.json");
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            BuildTheme(
                theme,
                Opus5R2Models,
                modelRoot,
                $"{Opus5R2StagingRoot}/Resources/{Opus5R2CandidateId}",
                configureTextureImporters: false);
            BuildOpus5R2AtlasProfiles(theme);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            Debug.Log(
                $"Candidate {Opus5R2CandidateId} staging is ready at " +
                $"{Opus5R2StagingRoot}. Existing V6 staging and active " +
                "assets were not modified.");
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Opus 5 Large Atlas Candidate Staging")]
        public static void BuildOpus5LargeCandidate()
        {
            var theme = Themes[2];
            var modelRoot = $"{Opus5LargeStagingRoot}/Models";
            Directory.CreateDirectory(modelRoot);
            foreach (var model in Opus5LargeModels)
            {
                CopyRequired(
                    $"{Opus5LargeSourceRoot}/" +
                    $"SM_{model.Key}_{theme.Folder}_V6_Opus5_LargeUV.fbx",
                    $"{modelRoot}/" +
                    $"SM_{model.Key}_{theme.Folder}_V6_Material.fbx");
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            BuildTheme(
                theme,
                Opus5LargeModels,
                modelRoot,
                $"{Opus5LargeStagingRoot}/Resources/" +
                Opus5LargeCandidateId,
                configureTextureImporters: false);
            BuildOpus5LargeAtlasProfiles(theme);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            Debug.Log(
                $"Candidate {Opus5LargeCandidateId} staging is ready at " +
                $"{Opus5LargeStagingRoot}. Active assets were not modified.");
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Build Opus 5 Medium Atlas Candidate Staging")]
        public static void BuildOpus5MediumCandidate()
        {
            var theme = Themes[2];
            var modelRoot = $"{Opus5MediumStagingRoot}/Models";
            Directory.CreateDirectory(modelRoot);
            foreach (var model in Opus5MediumModels)
            {
                CopyRequired(
                    $"{Opus5MediumSourceRoot}/" +
                    $"SM_{model.Key}_{theme.Folder}_V6_Opus5_MediumUV.fbx",
                    $"{modelRoot}/" +
                    $"SM_{model.Key}_{theme.Folder}_V6_Material.fbx");
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            BuildTheme(
                theme,
                Opus5MediumModels,
                modelRoot,
                $"{Opus5MediumStagingRoot}/Resources/" +
                Opus5MediumCandidateId,
                configureTextureImporters: false);
            BuildOpus5MediumAtlasProfiles(theme);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            Debug.Log(
                $"Candidate {Opus5MediumCandidateId} staging is ready at " +
                $"{Opus5MediumStagingRoot}. Active assets were not modified.");
        }

        private static void BuildOpus5MediumAtlasProfiles(ThemeEntry theme)
        {
            var resourceRoot =
                $"{Opus5MediumStagingRoot}/Resources/" +
                $"{Opus5MediumCandidateId}/{theme.Folder}/AtlasProfiles";
            var profiles = new[]
            {
                new LargeAtlasProfile("Control", "Medium_Control"),
                new LargeAtlasProfile("Fine", "Medium_Fine")
            };
            foreach (var profile in profiles)
            {
                var source =
                    $"{Opus5MediumTextureRoot}/{profile.SourceFolder}/" +
                    theme.Folder;
                var destination = $"{resourceRoot}/{profile.ResourceName}";
                Directory.CreateDirectory(destination);
                foreach (var suffix in new[]
                         {
                             "BaseColor",
                             "Normal",
                             "MetallicSmoothness",
                             "Emission"
                         })
                {
                    CopyRequired(
                        $"{source}/T_{theme.Folder}_V6_Atlas_Medium_" +
                        $"{suffix}.png",
                        $"{destination}/T_{theme.Folder}_V6_Atlas_Medium_" +
                        $"{suffix}.png");
                }
                CopyRequired(
                    $"{source}/T_{theme.Folder}_V6_Atlas_Medium.manifest.json",
                    $"{destination}/" +
                    $"T_{theme.Folder}_V6_Atlas_Medium.manifest.json");
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var profile in profiles)
            {
                var textureRoot =
                    $"{resourceRoot}/{profile.ResourceName}";
                ConfigureTexture(
                    $"{textureRoot}/" +
                    $"T_{theme.Folder}_V6_Atlas_Medium_BaseColor.png",
                    false);
                ConfigureTexture(
                    $"{textureRoot}/" +
                    $"T_{theme.Folder}_V6_Atlas_Medium_Normal.png",
                    true);
                ConfigureTexture(
                    $"{textureRoot}/" +
                    $"T_{theme.Folder}_V6_Atlas_Medium_" +
                    "MetallicSmoothness.png",
                    false,
                    linear: true);
                ConfigureTexture(
                    $"{textureRoot}/" +
                    $"T_{theme.Folder}_V6_Atlas_Medium_Emission.png",
                    false);
                BuildOpaqueMaterial(
                    textureRoot,
                    textureRoot,
                    theme.Folder,
                    "_Medium",
                    MediumBumpScale);
                BuildEmissiveMaterial(
                    textureRoot,
                    textureRoot,
                    theme,
                    "_Medium",
                    MediumBumpScale);
            }
        }

        private static void BuildOpus5LargeAtlasProfiles(ThemeEntry theme)
        {
            var resourceRoot =
                $"{Opus5LargeStagingRoot}/Resources/" +
                $"{Opus5LargeCandidateId}/{theme.Folder}/AtlasProfiles";
            var profiles = new[]
            {
                new LargeAtlasProfile("Control1K", "Large_Control_1K"),
                new LargeAtlasProfile("Same2K", "Large_2K_SameRepeats"),
                new LargeAtlasProfile("Finer2K", "Large_2K_FinerRepeats")
            };
            foreach (var profile in profiles)
            {
                var source =
                    $"{Opus5LargeTextureRoot}/{profile.SourceFolder}/" +
                    theme.Folder;
                var destination = $"{resourceRoot}/{profile.ResourceName}";
                Directory.CreateDirectory(destination);
                foreach (var suffix in new[]
                         {
                             "BaseColor",
                             "Normal",
                             "MetallicSmoothness",
                             "Emission"
                         })
                {
                    CopyRequired(
                        $"{source}/T_{theme.Folder}_V6_Atlas_Large_" +
                        $"{suffix}.png",
                        $"{destination}/T_{theme.Folder}_V6_Atlas_Large_" +
                        $"{suffix}.png");
                }
                CopyRequired(
                    $"{source}/T_{theme.Folder}_V6_Atlas_Large.manifest.json",
                    $"{destination}/" +
                    $"T_{theme.Folder}_V6_Atlas_Large.manifest.json");
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var profile in profiles)
            {
                var textureRoot =
                    $"{resourceRoot}/{profile.ResourceName}";
                ConfigureTexture(
                    $"{textureRoot}/" +
                    $"T_{theme.Folder}_V6_Atlas_Large_BaseColor.png",
                    false);
                ConfigureTexture(
                    $"{textureRoot}/" +
                    $"T_{theme.Folder}_V6_Atlas_Large_Normal.png",
                    true);
                ConfigureTexture(
                    $"{textureRoot}/" +
                    $"T_{theme.Folder}_V6_Atlas_Large_" +
                    "MetallicSmoothness.png",
                    false,
                    linear: true);
                ConfigureTexture(
                    $"{textureRoot}/" +
                    $"T_{theme.Folder}_V6_Atlas_Large_Emission.png",
                    false);
                BuildOpaqueMaterial(
                    textureRoot,
                    textureRoot,
                    theme.Folder,
                    "_Large",
                    LargeBumpScale);
                BuildEmissiveMaterial(
                    textureRoot,
                    textureRoot,
                    theme,
                    "_Large",
                    LargeBumpScale);
            }
        }

        private static void BuildOpus5R2AtlasProfiles(ThemeEntry theme)
        {
            const string sourceRoot =
                "ArtSource/Blender/BrushUp/Opus5/KineticSafety/textures";
            var resourceRoot =
                $"{Opus5R2StagingRoot}/Resources/{Opus5R2CandidateId}/" +
                $"{theme.Folder}/AtlasProfiles";
            foreach (var profile in new[] { "A", "B", "BT" })
            {
                var source =
                    $"{sourceRoot}/Repeats{profile}/{theme.Folder}";
                var destination = $"{resourceRoot}/{profile}";
                Directory.CreateDirectory(destination);
                foreach (var suffix in new[]
                         {
                             "BaseColor",
                             "Normal",
                             "MetallicSmoothness",
                             "Emission"
                         })
                {
                    CopyRequired(
                        $"{source}/T_{theme.Folder}_V6_Atlas_{suffix}.png",
                        $"{destination}/" +
                        $"T_{theme.Folder}_V6_Atlas_{suffix}.png");
                }
                CopyRequired(
                    $"{source}/T_{theme.Folder}_V6_Atlas.manifest.json",
                    $"{destination}/T_{theme.Folder}_V6_Atlas.manifest.json");
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var profile in new[] { "A", "B", "BT" })
            {
                var textureRoot = $"{resourceRoot}/{profile}";
                ConfigureTexture(
                    $"{textureRoot}/T_{theme.Folder}_V6_Atlas_BaseColor.png",
                    false);
                ConfigureTexture(
                    $"{textureRoot}/T_{theme.Folder}_V6_Atlas_Normal.png",
                    true);
                ConfigureTexture(
                    $"{textureRoot}/" +
                    $"T_{theme.Folder}_V6_Atlas_MetallicSmoothness.png",
                    false,
                    linear: true);
                ConfigureTexture(
                    $"{textureRoot}/T_{theme.Folder}_V6_Atlas_Emission.png",
                    false);
                BuildOpaqueMaterial(
                    textureRoot,
                    textureRoot,
                    theme.Folder,
                    "",
                    StandardBumpScale);
                BuildEmissiveMaterial(
                    textureRoot,
                    textureRoot,
                    theme,
                    "",
                    StandardBumpScale);
            }
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Model Replacement/" +
            "Apply V6 Staging to Production")]
        public static void ApplyToProduction()
        {
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            var backupRoot =
                $"Builds/ModelReplacementBackups/" +
                $"V6PreSwitch_{DateTime.Now:yyyyMMdd_HHmmss}";
            foreach (var theme in Themes)
            {
                foreach (var model in Models)
                {
                    var staged =
                        $"{CandidateRoot}/{theme.Folder}/" +
                        "ThemeHardSurfaceV6Material/" +
                        $"SM_{model.Key}_{theme.Folder}_V6_Material.fbx";
                    var active =
                        $"Assets/MatsuMotoMeterAR/Content/Themes/" +
                        $"{theme.Folder}/Models/" +
                        $"SM_{model.Key}_{theme.Folder}.fbx";
                    BackupIfPresent(active, backupRoot);
                    CopyRequired(staged, active);
                }

                var activePrefabRoot =
                    $"Assets/MatsuMotoMeterAR/Resources/" +
                    $"{theme.Folder}/Prefabs";
                foreach (var model in Models)
                {
                    BackupIfPresent(
                        $"{activePrefabRoot}/" +
                        $"PF_Visual_{model.Key}_{theme.Folder}.prefab",
                        backupRoot);
                }
                BackupIfPresent(
                    $"Assets/MatsuMotoMeterAR/Content/Themes/" +
                    $"{theme.Folder}/Materials/" +
                    $"MAT_{theme.Folder}_Atlas.mat",
                    backupRoot);
                BackupIfPresent(
                    $"Assets/MatsuMotoMeterAR/Content/Themes/" +
                    $"{theme.Folder}/Materials/" +
                    $"MAT_{theme.Folder}_Emissive.mat",
                    backupRoot);
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            OrbitalAnalogUnityAssetBuilder.Rebuild();
            RefinedModelReplacementValidator.ValidateActivePrefabs();
            Debug.Log(
                $"V6 production replacement completed. Backup: {backupRoot}");
        }

        private static void BuildTheme(ThemeEntry theme)
        {
            var modelRoot =
                $"{CandidateRoot}/{theme.Folder}/" +
                "ThemeHardSurfaceV6Material";
            BuildTheme(
                theme,
                Models,
                modelRoot,
                StagingRoot,
                configureTextureImporters: true);
        }

        private static void BuildTheme(
            ThemeEntry theme,
            IReadOnlyList<ModelEntry> models,
            string modelRoot,
            string stagingRoot,
            bool configureTextureImporters,
            bool useSolidRoleMaterials = false)
        {
            var textureRoot =
                $"Assets/MatsuMotoMeterAR/Content/Themes/{theme.Folder}/" +
                "Textures/ThemeMaterialV6";
            var materialRoot =
                $"{stagingRoot}/{theme.Folder}/Materials";
            var prefabRoot =
                $"{stagingRoot}/{theme.Folder}/Prefabs";
            Directory.CreateDirectory(materialRoot);
            Directory.CreateDirectory(prefabRoot);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

            if (configureTextureImporters)
            {
                foreach (var atlasSuffix in new[] { "", "_Medium", "_Large" })
                {
                    ConfigureTexture(
                        $"{textureRoot}/T_{theme.Folder}_V6_Atlas" +
                        $"{atlasSuffix}_BaseColor.png",
                        false);
                    ConfigureTexture(
                        $"{textureRoot}/T_{theme.Folder}_V6_Atlas" +
                        $"{atlasSuffix}_Normal.png",
                        true);
                    ConfigureTexture(
                        $"{textureRoot}/T_{theme.Folder}_V6_Atlas" +
                        $"{atlasSuffix}_MetallicSmoothness.png",
                        false,
                        linear: true);
                    ConfigureTexture(
                        $"{textureRoot}/T_{theme.Folder}_V6_Atlas" +
                        $"{atlasSuffix}_Emission.png",
                        false);
                }
            }

            foreach (var model in models)
            {
                ConfigureModel(
                    $"{modelRoot}/" +
                    $"SM_{model.Key}_{theme.Folder}_V6_Material.fbx");
            }

            var opaque = BuildOpaqueMaterial(
                materialRoot,
                textureRoot,
                theme.Folder,
                "",
                StandardBumpScale);
            var emissive = BuildEmissiveMaterial(
                materialRoot,
                textureRoot,
                theme,
                "",
                StandardBumpScale);
            var largeOpaque = BuildOpaqueMaterial(
                materialRoot,
                textureRoot,
                theme.Folder,
                "_Large",
                LargeBumpScale);
            var largeEmissive = BuildEmissiveMaterial(
                materialRoot,
                textureRoot,
                theme,
                "_Large",
                LargeBumpScale);
            var mediumOpaque = BuildOpaqueMaterial(
                materialRoot,
                textureRoot,
                theme.Folder,
                "_Medium",
                MediumBumpScale);
            var mediumEmissive = BuildEmissiveMaterial(
                materialRoot,
                textureRoot,
                theme,
                "_Medium",
                MediumBumpScale);
            if (useSolidRoleMaterials)
            {
                opaque = BuildSolidRoleMaterial(
                    materialRoot,
                    theme,
                    emissive: false);
                emissive = BuildSolidRoleMaterial(
                    materialRoot,
                    theme,
                    emissive: true);
                largeOpaque = opaque;
                largeEmissive = emissive;
                mediumOpaque = opaque;
                mediumEmissive = emissive;
            }
            foreach (var model in models)
            {
                BuildPrefab(
                    modelRoot,
                    prefabRoot,
                    theme.Folder,
                    model,
                    IsLargeAsset(model.Key)
                        ? largeOpaque
                        : IsMediumAsset(model.Key)
                            ? mediumOpaque
                            : opaque,
                    IsLargeAsset(model.Key)
                        ? largeEmissive
                        : IsMediumAsset(model.Key)
                            ? mediumEmissive
                            : emissive);
            }
        }

        private static Material BuildOpaqueMaterial(
            string materialRoot,
            string textureRoot,
            string theme,
            string scaleSuffix,
            float bumpScale)
        {
            var material = LoadOrCreateMaterial(
                $"{materialRoot}/MAT_{theme}_V6_Atlas" +
                $"{scaleSuffix}_Staging.mat");
            ConfigureLitMaterial(
                material,
                textureRoot,
                theme,
                scaleSuffix,
                bumpScale);
            material.DisableKeyword("_EMISSION");
            material.SetColor("_EmissionColor", Color.black);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material BuildEmissiveMaterial(
            string materialRoot,
            string textureRoot,
            ThemeEntry theme,
            string scaleSuffix,
            float bumpScale)
        {
            var material = LoadOrCreateMaterial(
                $"{materialRoot}/" +
                $"MAT_{theme.Folder}_V6_Emissive" +
                $"{scaleSuffix}_Staging.mat");
            ConfigureLitMaterial(
                material,
                textureRoot,
                theme.Folder,
                scaleSuffix,
                bumpScale);
            material.SetTexture(
                "_EmissionMap",
                LoadTexture(
                    $"{textureRoot}/" +
                    $"T_{theme.Folder}_V6_Atlas" +
                    $"{scaleSuffix}_Emission.png"));
            material.SetColor(
                "_EmissionColor",
                theme.EmissionColor * theme.EmissionStrength);
            material.EnableKeyword("_EMISSION");
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material BuildSolidRoleMaterial(
            string materialRoot,
            ThemeEntry theme,
            bool emissive)
        {
            var role = emissive ? "Readout" : "Opaque";
            var material = LoadOrCreateMaterial(
                $"{materialRoot}/MAT_{theme.Folder}_V6_Solid_{role}_Staging.mat");
            foreach (var property in new[]
                     {
                         "_BaseMap",
                         "_MainTex",
                         "_BumpMap",
                         "_MetallicGlossMap",
                         "_EmissionMap"
                     })
            {
                if (material.HasProperty(property))
                    material.SetTexture(property, null);
            }
            material.DisableKeyword("_NORMALMAP");
            material.DisableKeyword("_METALLICSPECGLOSSMAP");
            var baseColor = emissive
                ? new Color(0.02f, 0.46f, 0.57f, 1f)
                : new Color(0.11f, 0.14f, 0.17f, 1f);
            material.color = baseColor;
            if (material.HasProperty("_BaseColor"))
                material.SetColor("_BaseColor", baseColor);
            material.SetFloat("_Metallic", emissive ? 0.05f : 0.48f);
            material.SetFloat("_Smoothness", emissive ? 0.38f : 0.56f);
            if (emissive)
            {
                material.SetColor(
                    "_EmissionColor",
                    theme.EmissionColor *
                    (theme.EmissionStrength * 1.65f));
                material.EnableKeyword("_EMISSION");
            }
            else
            {
                material.SetColor("_EmissionColor", Color.black);
                material.DisableKeyword("_EMISSION");
            }
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void ConfigureLitMaterial(
            Material material,
            string textureRoot,
            string theme,
            string scaleSuffix,
            float bumpScale)
        {
            var atlasPrefix =
                $"{textureRoot}/T_{theme}_V6_Atlas{scaleSuffix}";
            material.SetTexture(
                "_BaseMap",
                LoadTexture($"{atlasPrefix}_BaseColor.png"));
            material.SetTexture(
                "_BumpMap",
                LoadTexture($"{atlasPrefix}_Normal.png"));
            material.SetTexture(
                "_MetallicGlossMap",
                LoadTexture(
                    $"{atlasPrefix}_MetallicSmoothness.png"));
            material.SetFloat("_BumpScale", bumpScale);
            material.SetFloat("_Metallic", 1f);
            material.SetFloat("_Smoothness", 1f);
            material.EnableKeyword("_NORMALMAP");
            material.EnableKeyword("_METALLICSPECGLOSSMAP");
        }

        private static bool IsLargeAsset(string key)
        {
            return key == "MeterLarge" ||
                   key == "WindowMeter" ||
                   key == "WindowPanel";
        }

        private static bool IsMediumAsset(string key)
        {
            return key == "MeterMedium";
        }

        private static Material LoadOrCreateMaterial(string path)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null)
            {
                throw new InvalidOperationException(
                    "Universal Render Pipeline/Lit shader was not found.");
            }

            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(material, path);
            }
            else
            {
                material.shader = shader;
            }
            return material;
        }

        private static void BuildPrefab(
            string modelRoot,
            string prefabRoot,
            string theme,
            ModelEntry model,
            Material opaque,
            Material emissive)
        {
            var modelPath =
                $"{modelRoot}/SM_{model.Key}_{theme}_V6_Material.fbx";
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (source == null)
                throw new FileNotFoundException($"Missing V6 FBX: {modelPath}");

            var imported =
                PrefabUtility.InstantiatePrefab(source) as GameObject;
            if (imported == null)
            {
                throw new InvalidOperationException(
                    $"Could not instantiate V6 FBX: {modelPath}");
            }

            var prefabName = $"PF_Visual_{model.Key}_{theme}";
            var root = new GameObject(prefabName);
            imported.transform.SetParent(root.transform, false);
            imported.transform.localPosition = Vector3.zero;
            imported.transform.localRotation =
                Quaternion.Euler(-90f, 0f, 0f);
            imported.transform.localScale = Vector3.one;

            try
            {
                MoveVisualInFrontOfMountPlane(imported);
                foreach (var renderer in
                         root.GetComponentsInChildren<Renderer>(true))
                {
                    var sourceMaterials = renderer.sharedMaterials;
                    var replacements =
                        new Material[sourceMaterials.Length];
                    for (var index = 0;
                         index < sourceMaterials.Length;
                         index++)
                    {
                        var sourceMaterial = sourceMaterials[index];
                        replacements[index] =
                            IsEmissiveMaterialRole(sourceMaterial?.name)
                                ? emissive
                                : opaque;
                    }
                    renderer.sharedMaterials = replacements;
                }

                foreach (var collider in
                         root.GetComponentsInChildren<Collider>(true))
                {
                    UnityEngine.Object.DestroyImmediate(collider);
                }

                var motionTarget = FindNode(
                    root.transform,
                    model.MotionTarget);
                var manifest = root.AddComponent<ThemeVisualManifest>();
                var indicatorRenderer =
                    model.Key == "Lamp"
                        ? FindRenderer(
                            root.transform,
                            model.MotionTarget)
                        : null;
                var stateRenderers =
                    model.Key == "StatusIndicator"
                        ? new[]
                        {
                            FindRenderer(root.transform, "status_safe"),
                            FindRenderer(root.transform, "status_warn"),
                            FindRenderer(root.transform, "status_danger")
                        }
                        : null;
                manifest.Configure(
                    motionTarget,
                    indicatorRenderer,
                    stateRenderers);

                var prefabPath =
                    $"{prefabRoot}/{prefabName}.prefab";
                if (PrefabUtility.SaveAsPrefabAsset(root, prefabPath) == null)
                {
                    throw new InvalidOperationException(
                        $"Could not save staging prefab: {prefabPath}");
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static Transform FindNode(
            Transform root,
            string expectedName)
        {
            foreach (var candidate in
                     root.GetComponentsInChildren<Transform>(true))
            {
                if (candidate.name == expectedName)
                    return candidate;
            }
            throw new MissingReferenceException(
                $"{root.name} is missing {expectedName}.");
        }

        internal static bool IsEmissiveMaterialRole(string materialName)
        {
            if (string.IsNullOrWhiteSpace(materialName))
                return false;

            return materialName.Contains(
                       "Emissive",
                       StringComparison.OrdinalIgnoreCase) ||
                   materialName.Contains(
                       "Readout",
                       StringComparison.OrdinalIgnoreCase);
        }

        private static Renderer FindRenderer(
            Transform root,
            string expectedName)
        {
            var node = FindNode(root, expectedName);
            var renderer = node.GetComponentInChildren<Renderer>(true);
            if (renderer == null)
            {
                throw new MissingReferenceException(
                    $"{root.name}/{expectedName} has no Renderer.");
            }
            return renderer;
        }

        private static void MoveVisualInFrontOfMountPlane(GameObject visual)
        {
            var renderers = visual.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0)
                return;
            var bounds = renderers[0].bounds;
            for (var index = 1; index < renderers.Length; index++)
                bounds.Encapsulate(renderers[index].bounds);
            if (bounds.min.z < 0f)
            {
                visual.transform.localPosition +=
                    Vector3.forward * -bounds.min.z;
            }
        }

        private static Texture2D LoadTexture(string path)
        {
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null)
                throw new FileNotFoundException($"Missing texture: {path}");
            return texture;
        }

        private static void ConfigureTexture(
            string path,
            bool normalMap,
            bool linear = false)
        {
            if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
            {
                throw new FileNotFoundException(
                    $"Texture importer was not found: {path}");
            }
            importer.textureType =
                normalMap
                    ? TextureImporterType.NormalMap
                    : TextureImporterType.Default;
            importer.sRGBTexture = !linear && !normalMap;
            importer.mipmapEnabled = true;
            importer.wrapMode = TextureWrapMode.Repeat;
            importer.filterMode = FilterMode.Bilinear;
            importer.anisoLevel = 1;
            importer.maxTextureSize = 2048;
            importer.textureCompression =
                TextureImporterCompression.Compressed;
            importer.SaveAndReimport();
        }

        private static void ConfigureModel(string path)
        {
            if (AssetImporter.GetAtPath(path) is not ModelImporter importer)
                throw new FileNotFoundException($"Missing model: {path}");
            importer.bakeAxisConversion = true;
            importer.globalScale = 1f;
            importer.importAnimation = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.addCollider = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            importer.SaveAndReimport();
        }

        private static void CopyRequired(string source, string destination)
        {
            if (!File.Exists(source))
                throw new FileNotFoundException($"Missing staged FBX: {source}");
            var directory = Path.GetDirectoryName(destination);
            if (!string.IsNullOrEmpty(directory))
                Directory.CreateDirectory(directory);
            File.Copy(source, destination, true);
        }

        private static string SelectedManifestPath()
        {
            return CandidateStagingManifest.SelectedAssetPath();
        }

        private static IReadOnlyList<ResolvedCandidateEntry>
            ResolveManifestEntries(CandidateStagingManifest manifest)
        {
            var resolved = new List<ResolvedCandidateEntry>();
            foreach (var entry in manifest.entries)
            {
                resolved.Add(
                    new ResolvedCandidateEntry(
                        entry,
                        FindTheme(entry.theme),
                        FindModel(entry.model)));
            }
            return resolved;
        }

        private static ThemeEntry FindTheme(string folder)
        {
            foreach (var theme in Themes)
            {
                if (theme.Folder == folder)
                    return theme;
            }
            throw new InvalidDataException(
                $"Unsupported candidate theme: {folder}.");
        }

        private static ModelEntry FindModel(string key)
        {
            foreach (var model in Models)
            {
                if (model.Key == key)
                    return model;
            }
            throw new InvalidDataException(
                $"Unsupported candidate model: {key}.");
        }

        private static void BackupIfPresent(
            string source,
            string backupRoot)
        {
            if (!File.Exists(source))
                return;
            var destination = Path.Combine(backupRoot, source);
            var directory = Path.GetDirectoryName(destination);
            if (!string.IsNullOrEmpty(directory))
                Directory.CreateDirectory(directory);
            File.Copy(source, destination, true);
        }

        private readonly struct ThemeEntry
        {
            public ThemeEntry(
                string folder,
                Color emissionColor,
                float emissionStrength)
            {
                Folder = folder;
                EmissionColor = emissionColor;
                EmissionStrength = emissionStrength;
            }

            public string Folder { get; }
            public Color EmissionColor { get; }
            public float EmissionStrength { get; }
        }

        private readonly struct ModelEntry
        {
            public ModelEntry(string key, string motionTarget)
            {
                Key = key;
                MotionTarget = motionTarget;
            }

            public string Key { get; }
            public string MotionTarget { get; }
        }

        private readonly struct LargeAtlasProfile
        {
            public LargeAtlasProfile(
                string resourceName,
                string sourceFolder)
            {
                ResourceName = resourceName;
                SourceFolder = sourceFolder;
            }

            public string ResourceName { get; }
            public string SourceFolder { get; }
        }

        private readonly struct ResolvedCandidateEntry
        {
            public ResolvedCandidateEntry(
                CandidateStagingEntry entry,
                ThemeEntry theme,
                ModelEntry model)
            {
                Entry = entry;
                Theme = theme;
                Model = model;
            }

            public CandidateStagingEntry Entry { get; }
            public ThemeEntry Theme { get; }
            public ModelEntry Model { get; }
        }
    }
}
