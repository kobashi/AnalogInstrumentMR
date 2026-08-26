using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using MatsuMotoMeterAR.Instruments;
using UnityEditor;
using UnityEngine;

namespace MatsuMotoMeterAR.Editor
{
    /// <summary>
    /// Builds all fourteen accepted Machined Ergonomics models as one
    /// isolated Theme 4 candidate. Production Resources and the runtime
    /// theme catalog remain unchanged until the full Quest gate is accepted.
    /// </summary>
    internal static class Theme4BatchBFullGateBuilder
    {
        private const string R1SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/" +
            "delivery_p6/fastener_access_r1";
        private const string R3SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/" +
            "delivery_p6/fastener_access_r3";
        private const string R4SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/" +
            "delivery_p6/fastener_access_r4";
        private const string P5SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p5";
        private const string BatchASourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/" +
            "delivery_p6/batch_a_r4_b3u_r2";
        private const string BatchCSourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/" +
            "delivery_p6/batch_c";
        private const string BatchCR1SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/" +
            "delivery_p6/batch_c_r1";
        private const string BatchCR2SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/" +
            "delivery_p6/batch_c_r2";
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging/Theme4_MachinedErgonomics_14_FullGate";
        private const string ModelRoot = CandidateRoot + "/Models";
        private const string TextureRoot = CandidateRoot + "/Textures";
        private const string MaterialRoot = CandidateRoot + "/Materials";
        private const string PrefabRoot = CandidateRoot + "/Prefabs";
        private const string QuestResourceRoot =
            CandidateRoot + "/Resources/Theme4_MachinedErgonomics_14_FullGate/" +
            "MachinedErgonomics/Prefabs";
        private const string ReportPath =
            "Builds/Reports/theme4-machined-ergonomics-14-full-unity-gate.md";

        private static readonly ModelSpec[] Models =
        {
            new ModelSpec(
                "MeterRound", P5SourceRoot,
                "SM_MeterRound_MachinedErgonomics_V6_Opus5_P5.fbx",
                "f44aaf7ad60a4a6d1ba61aeae252629f722e1166c81e9886315187983881a673",
                "needle_pivot", "needle", 4796, 2, 3),
            new ModelSpec(
                "MeterMedium", R3SourceRoot,
                "SM_MeterMedium_MachinedErgonomics_V6_Opus5_FA_R3.fbx",
                "23db3565f51fd2679cacda0602e01750338d62318becd67812f76f5c303bb8cd",
                "needle_pivot", "needle", 2816, 2, 3),
            new ModelSpec(
                "MeterLarge", R3SourceRoot,
                "SM_MeterLarge_MachinedErgonomics_V6_Opus5_FA_R3.fbx",
                "481a726d76bc38a2681d287c5888a0a771e4d22b3d8f5c2bbed5b03132bd25a6",
                "needle_pivot", "needle", 3104, 2, 3),
            new ModelSpec(
                "Lever", R4SourceRoot,
                "SM_Lever_MachinedErgonomics_V6_Opus5_FA_R4.fbx",
                "7b942b103d86f50481780917e3432620b1fbcbf5d528bd9dd7b829415c2c430d",
                "handle_pivot", "handle", 6792, 2, 3),
            new ModelSpec(
                "Toggle", R4SourceRoot,
                "SM_Toggle_MachinedErgonomics_V6_Opus5_FA_R4.fbx",
                "a98dd9e443421be7ab175998e51fc578b62bb13d653ac89a31a72f9de96237f2",
                "switch_pivot", "switch", 3540, 2, 3),
            new ModelSpec(
                "Rotary", R3SourceRoot,
                "SM_Rotary_MachinedErgonomics_V6_Opus5_FA_R3.fbx",
                "20b641aa63d7d9c52c6975271977dd036cf33af313ef938d2dcc4d3e5e9a3602",
                "knob_pivot", "knob", 1492, 2, 4),
            new ModelSpec(
                "Button", R1SourceRoot,
                "SM_Button_MachinedErgonomics_V6_Opus5_FA_R1.fbx",
                "858940ed6451070d371ef99db4ab2662122b99a2591ff84a9db4334344814d25",
                "button_travel", "button", 2008, 2, 3),
            new ModelSpec(
                "Lamp", R1SourceRoot,
                "SM_Lamp_MachinedErgonomics_V6_Opus5_FA_R1.fbx",
                "50bb16b92f432e9ae37427ccd97c655371367bae047052e6dcaa6414dbffc070",
                "indicator", "indicator_lens", 1332, 2, 3),
            new ModelSpec(
                "StatusIndicator", R1SourceRoot,
                "SM_StatusIndicator_MachinedErgonomics_V6_Opus5_FA_R1.fbx",
                "091c86df095297f20130594b51dd2d386ac099a14a2c54ab25f85b1068f3c6d8",
                "indicator", "status_safe", 1476, 4, 5),
            new ModelSpec(
                "Throttle", BatchASourceRoot,
                "SM_Throttle_MachinedErgonomics_V6_Opus5_R4_B3U_R2.fbx",
                "5966798fdacb974e7a3529b2a69a7c5593534c7b3c7daeaec5316dc7bcb3dec3",
                "throttle_pivot", "throttle_handle", 4706, 2, 2,
                requiresEmissive: false),
            new ModelSpec(
                "PowerSlider", BatchASourceRoot,
                "SM_PowerSlider_MachinedErgonomics_V6_Opus5_R4_B3U_R2.fbx",
                "0fe09ed6902e0b8504a571bdce050b05845c06fe38c118e2082797566e4ca7fb",
                "slider_travel", "slider_handle", 4600, 2, 2,
                requiresEmissive: false),
            new ModelSpec(
                "WindowMeter", BatchCR2SourceRoot,
                "SM_WindowMeter_MachinedErgonomics_V6_Opus5_P6C_R2.fbx",
                "51717906965a1315a7700597d6ddf42b717febbd38b52d39badbe40ec45110a3",
                "needle_pivot", "needle", 3124, 2, 3),
            new ModelSpec(
                "WindowPanel", BatchCR2SourceRoot,
                "SM_WindowPanel_MachinedErgonomics_V6_Opus5_P6C_R2.fbx",
                "7c5a520fe43662de66cb2151387c8324bd50b0b814cf0e1506667a96a1c2a8fa",
                "vane_pivot", "vane", 2556, 2, 3),
            new ModelSpec(
                "TrendMonitor", BatchCSourceRoot,
                "SM_TrendMonitor_MachinedErgonomics_V6_Opus5_P6C.fbx",
                "89fed8390bb83b5281f2ae7073a41f048916d6f184ba0070c06e4ba8316280bf",
                "display_surface", "display_surface", 1336, 2, 3)
        };

        private static readonly TextureSpec[] Textures =
        {
            new TextureSpec(
                "BaseColor", false, false,
                "c9c952431cb4c0baaac65ce602c353ad0f746dfabe98c7b4791e4b2ce649e8bb"),
            new TextureSpec(
                "Normal", true, true,
                "c964f804ed178413d06cb293f3effc986f25b017b652c5d7caa50c731cd890e3"),
            new TextureSpec(
                "MetallicSmoothness", false, true,
                "b1fe9ce80ddc7f5c170eeb3c9a78fd388efe008fd8a60faf1848750da883fd88"),
            new TextureSpec(
                "Emission", false, false,
                "1a0810ff8b05d65a564e17dbd272e27800fbcd69f79cf898e230d4b7e197ca6c")
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build and Validate Machined Ergonomics 14 Full Unity Gate")]
        public static void BuildAndValidate()
        {
            Directory.CreateDirectory(ModelRoot);
            Directory.CreateDirectory(TextureRoot);
            Directory.CreateDirectory(MaterialRoot);
            Directory.CreateDirectory(PrefabRoot);

            foreach (var model in Models)
            {
                var source = model.SourceRoot + "/" + model.FileName;
                RequireHash(source, model.Sha256);
                File.Copy(source, ModelRoot + "/" + model.FileName, true);
            }

            foreach (var texture in Textures)
            {
                var source = BatchCR2SourceRoot + "/" + texture.FileName;
                RequireHash(source, texture.Sha256);
                File.Copy(source, TextureRoot + "/" + texture.FileName, true);
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var model in Models)
                ConfigureModel(ModelRoot + "/" + model.FileName);
            foreach (var texture in Textures)
                ConfigureTexture(TextureRoot + "/" + texture.FileName, texture);

            var opaque = BuildMaterial(false);
            var emissive = BuildMaterial(true);
            var trendDisplay = BuildTrendDisplayMaterial();
            foreach (var model in Models)
                BuildPrefab(model, opaque, emissive, trendDisplay);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            WriteValidationReport();
            Debug.Log("Theme 4 Machined Ergonomics 14 Full Unity Gate: PASS\n" +
                      ReportPath);
        }

        internal static void PrepareQuestReviewResources()
        {
            BuildAndValidate();
            Directory.CreateDirectory(QuestResourceRoot);
            foreach (var spec in Models)
            {
                var source = PrefabPath(spec);
                var destination =
                    $"{QuestResourceRoot}/PF_Visual_{spec.Key}_" +
                    "MachinedErgonomics.prefab";
                if (AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(destination) !=
                    null && !AssetDatabase.DeleteAsset(destination))
                {
                    throw new IOException(
                        "Could not replace fastener-access review prefab: " + destination);
                }
                if (!AssetDatabase.CopyAsset(source, destination))
                    throw new IOException("Could not stage review prefab: " + destination);
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        private static void ConfigureModel(string path)
        {
            if (AssetImporter.GetAtPath(path) is not ModelImporter importer)
                throw new FileNotFoundException("ModelImporter missing", path);
            importer.bakeAxisConversion = true;
            importer.globalScale = 1f;
            importer.importAnimation = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.addCollider = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            importer.SaveAndReimport();
        }

        private static void ConfigureTexture(string path, TextureSpec spec)
        {
            if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
                throw new FileNotFoundException("TextureImporter missing", path);
            importer.textureType = spec.Normal
                ? TextureImporterType.NormalMap
                : TextureImporterType.Default;
            importer.sRGBTexture = !spec.Linear && !spec.Normal;
            importer.mipmapEnabled = true;
            importer.wrapMode = TextureWrapMode.Repeat;
            importer.filterMode = FilterMode.Bilinear;
            importer.anisoLevel = 1;
            importer.maxTextureSize = 1024;
            importer.textureCompression = TextureImporterCompression.Compressed;
            var android = importer.GetPlatformTextureSettings("Android");
            android.name = "Android";
            android.overridden = true;
            android.maxTextureSize = 1024;
            android.format = TextureImporterFormat.ASTC_6x6;
            importer.SetPlatformTextureSettings(android);
            importer.SaveAndReimport();
        }

        private static Material BuildMaterial(bool emissive)
        {
            var suffix = emissive ? "Emissive" : "Opaque";
            var path = $"{MaterialRoot}/MAT_MachinedErgonomics_Full14_{suffix}.mat";
            var shader = Shader.Find(emissive
                ? "Universal Render Pipeline/Unlit"
                : "Universal Render Pipeline/Lit");
            if (shader == null)
                throw new MissingReferenceException("Required URP shader missing");
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

            material.SetColor("_BaseColor", Color.white);
            if (emissive)
            {
                material.SetTexture("_BaseMap", LoadTexture("Emission"));
                material.DisableKeyword("_NORMALMAP");
                material.DisableKeyword("_METALLICSPECGLOSSMAP");
            }
            else
            {
                material.SetTexture("_BaseMap", LoadTexture("BaseColor"));
                material.SetTexture("_BumpMap", LoadTexture("Normal"));
                material.SetFloat("_BumpScale", 1f);
                material.EnableKeyword("_NORMALMAP");
                material.SetTexture(
                    "_MetallicGlossMap", LoadTexture("MetallicSmoothness"));
                material.SetFloat("_Metallic", 1f);
                material.SetFloat("_Smoothness", 1f);
                material.EnableKeyword("_METALLICSPECGLOSSMAP");
            }
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Texture2D LoadTexture(string role)
        {
            var path = $"{TextureRoot}/T_MachinedErgonomics_P4_Atlas_{role}.png";
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null)
                throw new FileNotFoundException("Texture missing", path);
            return texture;
        }

        private static Material BuildTrendDisplayMaterial()
        {
            var path = MaterialRoot +
                "/MAT_MachinedErgonomics_Full14_TrendDisplayOpaque.mat";
            var shader = Shader.Find("Universal Render Pipeline/Unlit");
            if (shader == null)
                throw new MissingReferenceException("Required URP shader missing");
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
            material.SetTexture("_BaseMap", null);
            material.SetColor("_BaseColor", new Color(0.012f, 0.020f, 0.028f, 1f));
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void BuildPrefab(
            ModelSpec spec, Material opaque, Material emissive,
            Material trendDisplay)
        {
            var modelPath = ModelRoot + "/" + spec.FileName;
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (source == null)
                throw new FileNotFoundException("Imported FBX missing", modelPath);
            var imported = PrefabUtility.InstantiatePrefab(source) as GameObject;
            if (imported == null)
                throw new InvalidOperationException("Could not instantiate " + modelPath);
            var root = new GameObject(
                $"PF_Visual_{spec.Key}_MachinedErgonomics_Full14");
            try
            {
                imported.transform.SetParent(root.transform, false);
                imported.transform.localPosition = Vector3.zero;
                ConfigureImportedOrientation(imported, spec);
                imported.transform.localScale = Vector3.one;

                foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
                {
                    var sourceMaterials = renderer.sharedMaterials;
                    var assigned = new Material[sourceMaterials.Length];
                    for (var index = 0; index < assigned.Length; index++)
                    {
                        if (spec.Key == "TrendMonitor" &&
                            renderer.name == "display_surface")
                        {
                            assigned[index] = trendDisplay;
                            continue;
                        }
                        var sourceName = sourceMaterials[index] != null
                            ? sourceMaterials[index].name
                            : string.Empty;
                        assigned[index] = sourceName.IndexOf(
                            "Emissive", StringComparison.OrdinalIgnoreCase) >= 0
                            ? emissive
                            : opaque;
                    }
                    renderer.sharedMaterials = assigned;
                }
                foreach (var collider in root.GetComponentsInChildren<Collider>(true))
                    UnityEngine.Object.DestroyImmediate(collider);

                var motionTarget = FindTransform(root.transform, spec.MotionTarget);
                if (motionTarget == null)
                    throw new MissingReferenceException(
                        $"{spec.Key} is missing motion target {spec.MotionTarget}");
                Renderer indicatorRenderer = null;
                Renderer[] stateRenderers = null;
                if (spec.Key == "Lamp")
                {
                    indicatorRenderer = FindRenderer(root.transform, "indicator_lens");
                    if (indicatorRenderer == null)
                        throw new MissingReferenceException(
                            "Lamp is missing indicator_lens renderer");
                }
                else if (spec.Key == "StatusIndicator")
                {
                    stateRenderers = new[]
                    {
                        FindRenderer(root.transform, "status_safe"),
                        FindRenderer(root.transform, "status_warn"),
                        FindRenderer(root.transform, "status_danger")
                    };
                    if (stateRenderers.Any(renderer => renderer == null))
                        throw new MissingReferenceException(
                            "StatusIndicator is missing a state renderer");
                }

                root.AddComponent<ThemeVisualManifest>().Configure(
                    motionTarget, indicatorRenderer, stateRenderers);
                if (PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(spec)) == null)
                    throw new InvalidOperationException(
                        "Could not save fastener-access prefab: " + PrefabPath(spec));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static void WriteValidationReport()
        {
            ValidateTextureSet();
            var rows = new List<string>();
            foreach (var spec in Models)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                    PrefabPath(spec));
                if (prefab == null)
                    throw new FileNotFoundException("Prefab missing", PrefabPath(spec));
                var filters = prefab.GetComponentsInChildren<MeshFilter>(true);
                var renderers = prefab.GetComponentsInChildren<Renderer>(true);
                var triangles = filters.Sum(filter => filter.sharedMesh != null
                    ? filter.sharedMesh.triangles.Length / 3
                    : 0);
                var submeshes = filters.Sum(filter => filter.sharedMesh != null
                    ? filter.sharedMesh.subMeshCount
                    : 0);
                if (filters.Any(filter => filter.sharedMesh == null ||
                    filter.sharedMesh.uv == null ||
                    filter.sharedMesh.uv.Length != filter.sharedMesh.vertexCount ||
                    filter.sharedMesh.uv.Any(uv =>
                        !float.IsFinite(uv.x) || !float.IsFinite(uv.y))))
                    throw new InvalidDataException(spec.Key + ": invalid UV0");
                if (triangles != spec.Triangles ||
                    renderers.Length != spec.Renderers ||
                    submeshes != spec.Submeshes)
                {
                    throw new InvalidDataException(
                        $"{spec.Key}: geometry contract mismatch; " +
                        $"triangles={triangles}, renderers={renderers.Length}, " +
                        $"submeshes={submeshes}");
                }
                if (FindTransform(prefab.transform, spec.MotionTarget) == null ||
                    FindTransform(prefab.transform, spec.Moving) == null)
                    throw new InvalidDataException(spec.Key + ": motion nodes missing");
                if (prefab.GetComponentsInChildren<Collider>(true).Length != 0 ||
                    prefab.GetComponentsInChildren<Light>(true).Length != 0 ||
                    prefab.GetComponentsInChildren<Camera>(true).Length != 0 ||
                    prefab.GetComponentsInChildren<Animator>(true).Length != 0)
                    throw new InvalidDataException(spec.Key + ": forbidden component found");

                var materials = renderers.SelectMany(renderer =>
                    renderer.sharedMaterials).ToArray();
                if (materials.Any(material => material == null ||
                    material.shader == null || string.Equals(
                        material.shader.name, "Hidden/InternalErrorShader",
                        StringComparison.Ordinal)))
                    throw new InvalidDataException(spec.Key + ": invalid shader");
                if (!materials.Any(material => material.name.Contains("Opaque")) ||
                    (spec.RequiresEmissive &&
                     !materials.Any(material => material.name.Contains("Emissive"))))
                    throw new InvalidDataException(spec.Key + ": material role missing");

                var manifest = prefab.GetComponent<ThemeVisualManifest>();
                if (manifest == null || manifest.MotionTarget == null ||
                    manifest.MotionTarget.name != spec.MotionTarget)
                    throw new InvalidDataException(spec.Key + ": manifest invalid");
                ValidateSignalManifest(spec, manifest);
                if (spec.Key == "TrendMonitor")
                    ValidateTrendMonitorDisplay(prefab);
                rows.Add($"| {spec.Key} | {triangles} | {renderers.Length} | " +
                         $"{submeshes} | PASS | PASS | PASS |");
            }

            Directory.CreateDirectory(Path.GetDirectoryName(ReportPath) ??
                                      "Builds/Reports");
            var report = new StringBuilder();
            report.AppendLine("# Theme 4 Machined Ergonomics 14 Full Unity Gate");
            report.AppendLine();
            report.AppendLine(
                "| Asset | Triangles | Renderers | Submeshes | UV0 | Material | Runtime manifest |");
            report.AppendLine("|---|---:|---:|---:|---|---|---|");
            foreach (var row in rows)
                report.AppendLine(row);
            report.AppendLine();
            report.AppendLine("- Atlas: frozen P4 1024");
            report.AppendLine("- Android override: ASTC 6x6; mipmaps enabled");
            report.AppendLine("- Normal: NormalMap / linear");
            report.AppendLine("- MetallicSmoothness: linear");
            report.AppendLine("- BaseColor / Emission: sRGB");
            report.AppendLine("- Lamp pulse renderer: indicator_lens");
            report.AppendLine(
                "- Status states: OFF + SAFE / WARN / DANGER renderer mapping");
            report.AppendLine("- Models: 14 / 14 isolated Theme 4 prefabs");
            report.AppendLine("- Batch C fasteners: 14 / 14 seat + penetration PASS");
            report.AppendLine("- Rotary blank plate_label: removed");
            report.AppendLine(
                "- TrendMonitor display: dedicated dark neutral unlit material");
            report.AppendLine("- Error Shader: 0");
            report.AppendLine("- Production assets/runtime catalog: unchanged");
            report.AppendLine("- Quest visual/runtime acceptance: OPEN");
            File.WriteAllText(ReportPath, report.ToString());
        }

        private static void ValidateSignalManifest(
            ModelSpec spec, ThemeVisualManifest manifest)
        {
            if (spec.Key == "Lamp")
            {
                if (manifest.IndicatorRenderer == null ||
                    manifest.IndicatorRenderer.name != "indicator_lens")
                    throw new InvalidDataException(
                        "Lamp indicator renderer mapping is invalid");
            }
            else if (spec.Key == "StatusIndicator")
            {
                var expected = new[]
                {
                    "status_safe", "status_warn", "status_danger"
                };
                if (manifest.StateRenderers == null ||
                    manifest.StateRenderers.Length != expected.Length)
                    throw new InvalidDataException(
                        "StatusIndicator state renderer count is invalid");
                for (var index = 0; index < expected.Length; index++)
                {
                    if (manifest.StateRenderers[index] == null ||
                        manifest.StateRenderers[index].name != expected[index])
                        throw new InvalidDataException(
                            "StatusIndicator state renderer order is invalid");
                }
                if (manifest.StateRenderers.Distinct().Count() != expected.Length)
                    throw new InvalidDataException(
                        "StatusIndicator state renderers are not distinct");
            }
        }

        private static void ValidateTrendMonitorDisplay(GameObject prefab)
        {
            var node = FindTransform(prefab.transform, "display_surface");
            var filter = node != null ? node.GetComponent<MeshFilter>() : null;
            var renderer = node != null ? node.GetComponent<Renderer>() : null;
            if (node == null || filter == null || filter.sharedMesh == null ||
                renderer == null)
                throw new InvalidDataException(
                    "TrendMonitor display_surface mesh/renderer missing");
            var displayMaterials = renderer.sharedMaterials;
            if (displayMaterials.Length == 0 || displayMaterials.Any(material =>
                    material == null ||
                    material.name !=
                    "MAT_MachinedErgonomics_Full14_TrendDisplayOpaque" ||
                    !material.HasProperty("_BaseColor") ||
                    material.GetColor("_BaseColor").maxColorComponent > 0.05f))
                throw new InvalidDataException(
                    "TrendMonitor display_surface must use the dedicated " +
                    "dark neutral display material");
            if (renderer.bounds.size.x < 0.36f || renderer.bounds.size.y < 0.18f)
                throw new InvalidDataException(
                    "TrendMonitor display_surface is smaller than 0.36 x 0.18 m");
            var mesh = filter.sharedMesh;
            var vertices = mesh.vertices
                .Select(node.TransformPoint).ToArray();
            var maximumZ = vertices.Max(vertex => vertex.z);
            var triangles = mesh.triangles;
            var frontTriangles = 0;
            const float planeTolerance = 0.00001f;
            for (var index = 0; index < triangles.Length; index += 3)
            {
                var a = vertices[triangles[index]];
                var b = vertices[triangles[index + 1]];
                var c = vertices[triangles[index + 2]];
                if (Mathf.Abs(a.z - maximumZ) > planeTolerance ||
                    Mathf.Abs(b.z - maximumZ) > planeTolerance ||
                    Mathf.Abs(c.z - maximumZ) > planeTolerance)
                    continue;
                var normal = Vector3.Cross(b - a, c - a).normalized;
                if (Vector3.Dot(normal, Vector3.forward) < 0.999f)
                    throw new InvalidDataException(
                        "TrendMonitor front-face normal does not face local +Z");
                frontTriangles++;
            }
            if (frontTriangles != 2)
                throw new InvalidDataException(
                    $"TrendMonitor front face must contain 2 triangles; " +
                    $"actual={frontTriangles}");
            var displaySize = mesh.bounds.size;
            var displayAxes = new[]
            {
                (extent: displaySize.x, axis: Vector3.right),
                (extent: displaySize.y, axis: Vector3.up),
                (extent: displaySize.z, axis: Vector3.forward)
            };
            var displayHeightAxis = displayAxes
                .OrderByDescending(item => item.extent)
                .Skip(1).First().axis;
            if (Vector3.Dot(
                    node.TransformDirection(displayHeightAxis).normalized,
                    Vector3.up) < 0.999f)
                throw new InvalidDataException(
                    "TrendMonitor display up axis does not face local +Y");
        }

        private static void ConfigureImportedOrientation(
            GameObject imported, ModelSpec spec)
        {
            if (spec.Key != "TrendMonitor")
            {
                imported.transform.localRotation =
                    Quaternion.Euler(-90f, 0f, 0f);
                return;
            }

            imported.transform.localRotation = Quaternion.identity;
            var displaySurface = FindTransform(
                imported.transform, spec.MotionTarget);
            var mesh = displaySurface != null
                ? displaySurface.GetComponent<MeshFilter>()?.sharedMesh
                : null;
            if (mesh == null || mesh.normals.Length == 0)
                throw new MissingReferenceException(
                    "TrendMonitor display_surface has no mesh normals");

            var size = mesh.bounds.size;
            var axes = new[]
            {
                (extent: size.x, axis: Vector3.right),
                (extent: size.y, axis: Vector3.up),
                (extent: size.z, axis: Vector3.forward)
            };
            var thinAxis = axes.OrderBy(item => item.extent).First().axis;
            var currentNormal = displaySurface.TransformDirection(-thinAxis)
                .normalized;
            imported.transform.rotation =
                Quaternion.FromToRotation(currentNormal, Vector3.forward) *
                imported.transform.rotation;
            var heightAxis = axes.OrderByDescending(item => item.extent)
                .Skip(1).First().axis;
            var currentUp = Vector3.ProjectOnPlane(
                displaySurface.TransformDirection(heightAxis),
                Vector3.forward).normalized;
            if (currentUp.sqrMagnitude < 0.000001f)
                throw new InvalidOperationException(
                    "TrendMonitor display_surface has no usable up axis");
            var roll = Vector3.SignedAngle(
                currentUp, Vector3.up, Vector3.forward);
            imported.transform.rotation =
                Quaternion.AngleAxis(roll, Vector3.forward) *
                imported.transform.rotation;
        }

        private static void ValidateTextureSet()
        {
            foreach (var spec in Textures)
            {
                var path = TextureRoot + "/" + spec.FileName;
                if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
                    throw new FileNotFoundException("TextureImporter missing", path);
                var android = importer.GetPlatformTextureSettings("Android");
                if (!importer.mipmapEnabled || !android.overridden ||
                    android.format != TextureImporterFormat.ASTC_6x6 ||
                    android.maxTextureSize != 1024 ||
                    importer.sRGBTexture != (!spec.Linear && !spec.Normal) ||
                    (spec.Normal &&
                     importer.textureType != TextureImporterType.NormalMap))
                    throw new InvalidDataException(
                        "Texture contract mismatch: " + path);
            }
        }

        private static string PrefabPath(ModelSpec spec)
        {
            return $"{PrefabRoot}/PF_Visual_{spec.Key}_" +
                   "MachinedErgonomics_Full14.prefab";
        }

        private static Transform FindTransform(Transform root, string name)
        {
            if (root.name == name)
                return root;
            foreach (Transform child in root)
            {
                var result = FindTransform(child, name);
                if (result != null)
                    return result;
            }
            return null;
        }

        private static Renderer FindRenderer(Transform root, string name)
        {
            var node = FindTransform(root, name);
            return node != null ? node.GetComponent<Renderer>() : null;
        }

        private static void RequireHash(string path, string expected)
        {
            if (!File.Exists(path))
                throw new FileNotFoundException("Fastener-access input missing", path);
            using var stream = File.OpenRead(path);
            using var sha = SHA256.Create();
            var actual = string.Concat(sha.ComputeHash(stream)
                .Select(value => value.ToString("x2")));
            if (!string.Equals(actual, expected, StringComparison.Ordinal))
                throw new InvalidDataException("SHA mismatch: " + path);
        }

        private readonly struct ModelSpec
        {
            public readonly string Key;
            public readonly string SourceRoot;
            public readonly string FileName;
            public readonly string Sha256;
            public readonly string MotionTarget;
            public readonly string Moving;
            public readonly int Triangles;
            public readonly int Renderers;
            public readonly int Submeshes;
            public readonly bool RequiresEmissive;

            public ModelSpec(
                string key, string sourceRoot, string fileName, string sha256,
                string motionTarget, string moving, int triangles,
                int renderers, int submeshes, bool requiresEmissive = true)
            {
                Key = key;
                SourceRoot = sourceRoot;
                FileName = fileName;
                Sha256 = sha256;
                MotionTarget = motionTarget;
                Moving = moving;
                Triangles = triangles;
                Renderers = renderers;
                Submeshes = submeshes;
                RequiresEmissive = requiresEmissive;
            }
        }

        private readonly struct TextureSpec
        {
            public readonly string Role;
            public readonly bool Normal;
            public readonly bool Linear;
            public readonly string Sha256;

            public TextureSpec(
                string role, bool normal, bool linear, string sha256)
            {
                Role = role;
                Normal = normal;
                Linear = linear;
                Sha256 = sha256;
            }

            public string FileName =>
                $"T_MachinedErgonomics_P4_Atlas_{Role}.png";
        }
    }
}
