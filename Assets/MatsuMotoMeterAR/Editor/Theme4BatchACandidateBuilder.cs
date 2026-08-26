using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using MatsuMotoMeterAR.Instruments;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace MatsuMotoMeterAR.Editor
{
    /// <summary>
    /// Imports Phase 3 Batch A into an isolated candidate area. This never
    /// registers MachinedErgonomics as a runtime theme or replaces a production prefab.
    /// </summary>
    internal static class Theme4BatchACandidateBuilder
    {
        private const string SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6/batch_a";
        private const string ThrottleR1SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p6/batch_a_r1";
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging/Theme4_P6_BatchA_Delivery";
        private const string ModelRoot = CandidateRoot + "/Models";
        private const string TextureRoot = CandidateRoot + "/Textures";
        private const string MaterialRoot = CandidateRoot + "/Materials";
        private const string PrefabRoot = CandidateRoot + "/Prefabs";
        private const string QuestResourceRoot =
            CandidateRoot + "/Resources/Theme4_P6_BatchA_Delivery/" +
            "MachinedErgonomics/Prefabs";
        private const string ReportPath =
            "Builds/Reports/candidate-Theme4_P6-BatchA-delivery-validation.md";
        private const string VisualReviewRoot =
            "Builds/Reports/Theme4_P6_BatchA_VisualReview";
        private const float BoundsTolerance = 0.002f;
        private const float PositionTolerance = 0.0002f;

        private const string BaseColorName =
            "T_MachinedErgonomics_P4_Atlas_BaseColor.png";
        private const string NormalName =
            "T_MachinedErgonomics_P4_Atlas_Normal.png";
        private const string MetallicName =
            "T_MachinedErgonomics_P4_Atlas_MetallicSmoothness.png";
        private const string EmissionName =
            "T_MachinedErgonomics_P4_Atlas_Emission.png";
        private const string OpaqueMaterialPath =
            MaterialRoot + "/MAT_MachinedErgonomics_P6A_Atlas_Staging.mat";
        private const string EmissiveMaterialPath =
            MaterialRoot + "/MAT_MachinedErgonomics_P6A_Emissive_Staging.mat";

        private static readonly AssetSpec[] Assets =
        {
            AssetSpec.Rotate(
                "MeterMedium",
                "SM_MeterMedium_MachinedErgonomics_V6_Opus5_P6A.fbx",
                "needle_pivot",
                "needle",
                Vector3.forward,
                new Vector3(0f, 0f, 0.0622f),
                -115f,
                115f,
                3968,
                new Vector3(0.356f, 0.356f, 0.0862f),
                new Vector3(0.36f, 0.36f, 0.145f),
                new Vector3(0.36f, 0.36f, 0.132f),
                "6a9678bba06af2772029db5554482b129ee0a6fcf84881dcd52d0381eebd533f"),
            AssetSpec.Rotate(
                "MeterLarge",
                "SM_MeterLarge_MachinedErgonomics_V6_Opus5_P6A.fbx",
                "needle_pivot",
                "needle",
                Vector3.forward,
                new Vector3(0f, 0f, 0.0796f),
                -115f,
                115f,
                4256,
                new Vector3(0.544f, 0.544f, 0.1096f),
                new Vector3(0.55f, 0.55f, 0.205f),
                new Vector3(0.55f, 0.55f, 0.192f),
                "e4d5ba3a054e2a874f4211c801c942b4ea00e84fc9187aac4cb0de92a2a29efd"),
            AssetSpec.Rotate(
                "Throttle",
                "SM_Throttle_MachinedErgonomics_V6_Opus5_P6A_R1.fbx",
                "throttle_pivot",
                "throttle_handle",
                Vector3.right,
                new Vector3(0f, 0.108f, 0.034f),
                -70f,
                0f,
                4756,
                new Vector3(0.238988f, 0.338988f, 0.115734f),
                new Vector3(0.24f, 0.34f, 0.16f),
                new Vector3(0.28f, 0.38f, 0.18f),
                "6bbcb1cb68869871ebd8c00bf52dddf260d3b0a7c7b891538bf2f6b0a1ceff7c"),
            AssetSpec.Translate(
                "PowerSlider",
                "SM_PowerSlider_MachinedErgonomics_V6_Opus5_P6A.fbx",
                "slider_travel",
                "slider_handle",
                Vector3.up,
                Vector3.zero,
                -0.09f,
                0.09f,
                4992,
                new Vector3(0.169076f, 0.339076f, 0.121244f),
                new Vector3(0.17f, 0.34f, 0.195f),
                new Vector3(0.20f, 0.38f, 0.12f),
                "1ddfd96c8536f757cf9fc735a571a53913439b803ba9fb8eb1b62b90c48af147")
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build and Validate Phase 3 Batch A Candidate")]
        public static void BuildAndValidate()
        {
            Directory.CreateDirectory(ModelRoot);
            Directory.CreateDirectory(TextureRoot);
            Directory.CreateDirectory(MaterialRoot);
            Directory.CreateDirectory(PrefabRoot);

            foreach (var spec in Assets)
            {
                var sourceRoot = spec.Key == "Throttle"
                    ? ThrottleR1SourceRoot
                    : SourceRoot;
                var source = $"{sourceRoot}/{spec.FileName}";
                RequireHash(source, spec.Sha256);
                File.Copy(source, $"{ModelRoot}/{spec.FileName}", true);
            }

            CopyTexture(BaseColorName,
                "c9c952431cb4c0baaac65ce602c353ad0f746dfabe98c7b4791e4b2ce649e8bb");
            CopyTexture(NormalName,
                "c964f804ed178413d06cb293f3effc986f25b017b652c5d7caa50c731cd890e3");
            CopyTexture(MetallicName,
                "b1fe9ce80ddc7f5c170eeb3c9a78fd388efe008fd8a60faf1848750da883fd88");
            CopyTexture(EmissionName,
                "1a0810ff8b05d65a564e17dbd272e27800fbcd69f79cf898e230d4b7e197ca6c");

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var spec in Assets)
                ConfigureModel($"{ModelRoot}/{spec.FileName}");
            ConfigureTexture($"{TextureRoot}/{BaseColorName}", false, false);
            ConfigureTexture($"{TextureRoot}/{NormalName}", true, true);
            ConfigureTexture($"{TextureRoot}/{MetallicName}", false, true);
            ConfigureTexture($"{TextureRoot}/{EmissionName}", false, false);

            var opaque = BuildMaterial(OpaqueMaterialPath, false);
            var emissive = BuildMaterial(EmissiveMaterialPath, true);
            foreach (var spec in Assets)
                BuildPrefab(spec, opaque, emissive);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            Validate(opaque, emissive);
            RenderVisualReview();
        }

        internal static void PrepareQuestReviewResources()
        {
            BuildAndValidate();
            Directory.CreateDirectory(QuestResourceRoot);
            foreach (var spec in Assets)
            {
                var source =
                    $"{PrefabRoot}/PF_Visual_{spec.Key}_" +
                    "MachinedErgonomics_P6A_Staging.prefab";
                var destination =
                    $"{QuestResourceRoot}/PF_Visual_{spec.Key}_" +
                    "MachinedErgonomics.prefab";
                if (AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(destination) != null &&
                    !AssetDatabase.DeleteAsset(destination))
                {
                    throw new IOException(
                        "Could not replace generated Theme 4 Batch A " +
                        "review prefab: " + destination);
                }
                if (!AssetDatabase.CopyAsset(source, destination))
                {
                    throw new IOException(
                        "Could not stage Theme 4 Batch A review prefab: " +
                        destination);
                }
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        private static void CopyTexture(string fileName, string sha256)
        {
            var source = $"{SourceRoot}/{fileName}";
            RequireHash(source, sha256);
            File.Copy(source, $"{TextureRoot}/{fileName}", true);
        }

        private static void RequireHash(string path, string expected)
        {
            if (!File.Exists(path))
                throw new FileNotFoundException("Theme 4 P6A input is missing.", path);
            var actual = Sha256(path);
            if (!string.Equals(actual, expected, StringComparison.Ordinal))
            {
                throw new InvalidDataException(
                    $"Theme 4 P6A SHA mismatch for {path}: {actual}");
            }
        }

        private static void ConfigureModel(string path)
        {
            if (AssetImporter.GetAtPath(path) is not ModelImporter importer)
                throw new FileNotFoundException("ModelImporter is missing.", path);
            importer.bakeAxisConversion = true;
            importer.globalScale = 1f;
            importer.importAnimation = false;
            importer.importCameras = false;
            importer.importLights = false;
            importer.addCollider = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            importer.SaveAndReimport();
        }

        private static void ConfigureTexture(string path, bool normal, bool linear)
        {
            if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
                throw new FileNotFoundException("TextureImporter is missing.", path);
            importer.textureType = normal
                ? TextureImporterType.NormalMap
                : TextureImporterType.Default;
            importer.sRGBTexture = !linear && !normal;
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

        private static Material BuildMaterial(string path, bool emissive)
        {
            var shader = Shader.Find(
                emissive
                    ? "Universal Render Pipeline/Unlit"
                    : "Universal Render Pipeline/Lit");
            if (shader == null)
                throw new MissingReferenceException("Required URP shader is unavailable.");
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

            material.name = Path.GetFileNameWithoutExtension(path);
            material.SetColor("_BaseColor", Color.white);
            if (emissive)
            {
                material.SetTexture("_BaseMap", LoadTexture(EmissionName));
                material.DisableKeyword("_NORMALMAP");
                material.DisableKeyword("_METALLICSPECGLOSSMAP");
                material.DisableKeyword("_EMISSION");
                material.globalIlluminationFlags =
                    MaterialGlobalIlluminationFlags.None;
            }
            else
            {
                material.SetTexture("_BaseMap", LoadTexture(BaseColorName));
                material.SetTexture("_BumpMap", LoadTexture(NormalName));
                material.SetFloat("_BumpScale", 1f);
                material.EnableKeyword("_NORMALMAP");
                material.SetTexture("_MetallicGlossMap", LoadTexture(MetallicName));
                material.SetFloat("_Metallic", 1f);
                material.SetFloat("_Smoothness", 1f);
                material.EnableKeyword("_METALLICSPECGLOSSMAP");
                material.SetTexture("_EmissionMap", null);
                material.SetColor("_EmissionColor", Color.black);
                material.DisableKeyword("_EMISSION");
                material.globalIlluminationFlags =
                    MaterialGlobalIlluminationFlags.EmissiveIsBlack;
            }
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Texture2D LoadTexture(string name)
        {
            var path = $"{TextureRoot}/{name}";
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null)
                throw new FileNotFoundException("Texture asset is missing.", path);
            return texture;
        }

        private static void BuildPrefab(
            AssetSpec spec,
            Material opaque,
            Material emissive)
        {
            var modelPath = $"{ModelRoot}/{spec.FileName}";
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (source == null)
                throw new FileNotFoundException("Imported P6A FBX is missing.", modelPath);
            var imported = PrefabUtility.InstantiatePrefab(source) as GameObject;
            if (imported == null)
                throw new InvalidOperationException("Could not instantiate " + modelPath);

            var prefabName =
                $"PF_Visual_{spec.Key}_MachinedErgonomics_P6A_Staging";
            var root = new GameObject(prefabName);
            try
            {
                imported.transform.SetParent(root.transform, false);
                imported.transform.localPosition = Vector3.zero;
                imported.transform.localRotation = Quaternion.Euler(-90f, 0f, 0f);
                imported.transform.localScale = Vector3.one;

                foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
                {
                    var sourceMaterials = renderer.sharedMaterials;
                    var replacements = new Material[sourceMaterials.Length];
                    for (var index = 0; index < sourceMaterials.Length; index++)
                    {
                        var sourceName = sourceMaterials[index]?.name ?? string.Empty;
                        replacements[index] = sourceName.Contains(
                            "Emissive", StringComparison.OrdinalIgnoreCase)
                            ? emissive
                            : opaque;
                    }
                    renderer.sharedMaterials = replacements;
                }

                foreach (var collider in root.GetComponentsInChildren<Collider>(true))
                    UnityEngine.Object.DestroyImmediate(collider);

                var motionTarget = Find(root.transform, spec.PivotName);
                if (motionTarget == null)
                {
                    throw new MissingReferenceException(
                        $"{spec.Key} is missing {spec.PivotName}.");
                }
                var manifest = root.AddComponent<ThemeVisualManifest>();
                manifest.Configure(motionTarget, null, null);

                var prefabPath = $"{PrefabRoot}/{prefabName}.prefab";
                if (PrefabUtility.SaveAsPrefabAsset(root, prefabPath) == null)
                    throw new InvalidOperationException("Could not save " + prefabPath);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static void Validate(Material opaque, Material emissive)
        {
            var failures = new List<string>();
            var report = new StringBuilder();
            report.AppendLine("# Theme 4 Phase 3 Batch A isolated candidate validation");
            report.AppendLine();
            report.AppendLine(
                "Nonproduction candidate only. Existing themes, active prefabs, " +
                "runtime registration, and production materials were not changed.");
            report.AppendLine();
            report.AppendLine(
                "| Asset | Motion | Triangles / budget | Renderers / submeshes | Pivot m | " +
                "Rest bounds m | Swept bounds m | Mount min Z | Result |");
            report.AppendLine(
                "| --- | --- | ---: | --- | --- | --- | --- | ---: | --- |");
            foreach (var spec in Assets)
                ValidateAsset(spec, opaque, emissive, report, failures);

            ValidateTextureImporter(BaseColorName, false, true, failures);
            ValidateTextureImporter(NormalName, true, false, failures);
            ValidateTextureImporter(MetallicName, false, false, failures);
            ValidateTextureImporter(EmissionName, false, true, failures);

            report.AppendLine();
            report.AppendLine(failures.Count == 0 ? "Result: **PASS**" : "Result: **FAIL**");
            if (failures.Count > 0)
            {
                report.AppendLine();
                report.AppendLine("## Failures");
                report.AppendLine();
                foreach (var failure in failures)
                    report.AppendLine("- " + failure);
            }
            Directory.CreateDirectory(
                Path.GetDirectoryName(ReportPath) ?? "Builds/Reports");
            File.WriteAllText(ReportPath, report.ToString());
            if (failures.Count > 0)
            {
                throw new InvalidOperationException(
                    "Theme 4 P6A candidate validation failed. See " + ReportPath);
            }
            Debug.Log("Theme 4 P6A isolated candidate PASS: " + ReportPath);
        }

        private static void ValidateAsset(
            AssetSpec spec,
            Material opaque,
            Material emissive,
            StringBuilder report,
            ICollection<string> failures)
        {
            var prefabPath =
                $"{PrefabRoot}/PF_Visual_{spec.Key}_" +
                "MachinedErgonomics_P6A_Staging.prefab";
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (prefab == null)
            {
                failures.Add($"{spec.Key}: candidate prefab is missing.");
                return;
            }

            var instance = UnityEngine.Object.Instantiate(prefab);
            instance.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            instance.transform.localScale = Vector3.one;
            try
            {
                var pivot = Find(instance.transform, spec.PivotName);
                var moving = Find(instance.transform, spec.MovingPartName);
                var filters = instance.GetComponentsInChildren<MeshFilter>(true);
                var renderers = instance.GetComponentsInChildren<Renderer>(true);
                var triangles = 0;
                var submeshes = 0;
                foreach (var filter in filters)
                {
                    if (filter.sharedMesh == null)
                        continue;
                    triangles += filter.sharedMesh.triangles.Length / 3;
                    submeshes += filter.sharedMesh.subMeshCount;
                    for (var submesh = 0;
                         submesh < filter.sharedMesh.subMeshCount;
                         submesh++)
                    {
                        if (filter.sharedMesh.GetSubMesh(submesh).indexCount == 0)
                        {
                            failures.Add(
                                $"{spec.Key}: {filter.name} submesh {submesh} has zero indices.");
                        }
                    }
                }

                var rest = VertexBounds(instance.transform, filters);
                var swept = rest;
                var motionSpan = Vector3.zero;
                var pivotPosition = pivot != null
                    ? instance.transform.InverseTransformPoint(pivot.position)
                    : Vector3.positiveInfinity;
                if (pivot == null)
                    failures.Add($"{spec.Key}: pivot {spec.PivotName} is missing.");
                if (moving == null)
                    failures.Add($"{spec.Key}: moving part {spec.MovingPartName} is missing.");

                if (pivot != null && moving != null)
                {
                    if (spec.Motion == MotionKind.Rotate)
                        SweepRotation(instance.transform, pivot, filters, spec, ref swept);
                    else
                        SweepTranslation(
                            instance.transform,
                            pivot,
                            filters,
                            spec,
                            ref swept,
                            out motionSpan);
                }

                var materialsOk = ValidateMaterials(
                    renderers, opaque, emissive, out var usedOpaque, out var usedEmissive);
                var passed = true;
                passed &= Check(spec, "triangles", triangles, spec.Triangles, failures);
                passed &= CheckMaximum(
                    spec, "triangle budget", triangles, spec.TriangleBudget, failures);
                passed &= Check(spec, "renderers", renderers.Length, 2, failures);
                passed &= Check(spec, "submeshes", submeshes, 3, failures);
                passed &= CheckVector(
                    spec, "pivot", pivotPosition, spec.PivotPosition,
                    failures, PositionTolerance);
                passed &= CheckVector(
                    spec, "rest bounds", rest.size, spec.RestSize, failures);
                passed &= CheckWithin(spec, "rest envelope", rest.size,
                    spec.RestEnvelope, failures);
                passed &= CheckMotionSweep(
                    spec, rest, swept, motionSpan, failures);
                if (Mathf.Abs(rest.min.z) > PositionTolerance)
                {
                    failures.Add(
                        $"{spec.Key}: mount min Z {rest.min.z:F6}, expected 0.");
                    passed = false;
                }
                if (!materialsOk || !usedOpaque || !usedEmissive)
                {
                    failures.Add($"{spec.Key}: material identity contract failed.");
                    passed = false;
                }
                if (!opaque.IsKeywordEnabled("_NORMALMAP") ||
                    !opaque.IsKeywordEnabled("_METALLICSPECGLOSSMAP") ||
                    opaque.IsKeywordEnabled("_EMISSION") ||
                    emissive.shader.name != "Universal Render Pipeline/Unlit" ||
                    emissive.GetTexture("_BaseMap") != LoadTexture(EmissionName))
                {
                    failures.Add($"{spec.Key}: URP material contract failed.");
                    passed = false;
                }
                if (instance.GetComponentsInChildren<Collider>(true).Length != 0)
                {
                    failures.Add($"{spec.Key}: candidate contains a Collider.");
                    passed = false;
                }

                report.AppendLine(
                    $"| {spec.Key} | {spec.Motion} {spec.Minimum:+0.###;-0.###;0}" +
                    $"..{spec.Maximum:+0.###;-0.###;0} | " +
                    $"{triangles} / {spec.TriangleBudget} | " +
                    $"{renderers.Length} / {submeshes} | {Format(pivotPosition)} | " +
                    $"{Format(rest.size)} | {Format(swept.size)} @ " +
                    $"{Format(swept.center)} | {rest.min.z * 1000f:F3} mm | " +
                    $"{(passed ? "PASS" : "FAIL")} |");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static void SweepRotation(
            Transform root,
            Transform pivot,
            MeshFilter[] filters,
            AssetSpec spec,
            ref Bounds swept)
        {
            var originalParent = pivot.parent;
            var originalSibling = pivot.GetSiblingIndex();
            var proxy = new GameObject(spec.PivotName + " Runtime Motion").transform;
            proxy.SetParent(root, false);
            proxy.position = pivot.position;
            proxy.rotation = root.rotation;
            pivot.SetParent(proxy, true);
            try
            {
                for (var index = 0; index <= 96; index++)
                {
                    var value = Mathf.Lerp(spec.Minimum, spec.Maximum, index / 96f);
                    proxy.localRotation = Quaternion.AngleAxis(value, spec.Axis);
                    swept.Encapsulate(VertexBounds(root, filters));
                }
            }
            finally
            {
                pivot.SetParent(originalParent, true);
                pivot.SetSiblingIndex(originalSibling);
                UnityEngine.Object.DestroyImmediate(proxy.gameObject);
            }
        }

        private static void SweepTranslation(
            Transform root,
            Transform moving,
            MeshFilter[] filters,
            AssetSpec spec,
            ref Bounds swept,
            out Vector3 motionSpan)
        {
            var originalParent = moving.parent;
            var originalSibling = moving.GetSiblingIndex();
            var proxy = new GameObject(spec.PivotName + " Runtime Motion").transform;
            proxy.SetParent(root, false);
            proxy.position = moving.position;
            proxy.rotation = root.rotation;
            moving.SetParent(proxy, true);
            var initial = proxy.localPosition;
            var lowPosition = Vector3.zero;
            var highPosition = Vector3.zero;
            try
            {
                for (var index = 0; index <= 96; index++)
                {
                    var value = Mathf.Lerp(spec.Minimum, spec.Maximum, index / 96f);
                    proxy.localPosition = initial + spec.Axis * value;
                    if (index == 0)
                        lowPosition = root.InverseTransformPoint(proxy.position);
                    else if (index == 96)
                        highPosition = root.InverseTransformPoint(proxy.position);
                    swept.Encapsulate(VertexBounds(root, filters));
                }
                motionSpan = highPosition - lowPosition;
            }
            finally
            {
                moving.SetParent(originalParent, true);
                moving.SetSiblingIndex(originalSibling);
                UnityEngine.Object.DestroyImmediate(proxy.gameObject);
            }
        }

        private static bool CheckMotionSweep(
            AssetSpec spec,
            Bounds rest,
            Bounds swept,
            Vector3 motionSpan,
            ICollection<string> failures)
        {
            if (spec.Motion == MotionKind.Translate)
            {
                if (Mathf.Abs(motionSpan.x) <= PositionTolerance &&
                    Mathf.Abs(motionSpan.y - 0.18f) <= PositionTolerance &&
                    Mathf.Abs(motionSpan.z) <= PositionTolerance)
                {
                    return true;
                }
                failures.Add(
                    $"{spec.Key}: translation sweep is not on Unity +Y; " +
                    $"endpoint delta {Format(motionSpan)}, expected 0 x 0.18 x 0.");
                return false;
            }

            if (spec.Key == "Throttle")
            {
                var depthGrowth = swept.size.z - rest.size.z;
                if (depthGrowth >= 0.13f &&
                    swept.size.x <= spec.RestEnvelope.x + BoundsTolerance &&
                    swept.size.y <= spec.RestEnvelope.y + BoundsTolerance)
                {
                    return true;
                }
                failures.Add(
                    $"{spec.Key}: rotation sweep is not consistent with Unity +X; " +
                    $"rest {Format(rest.size)}, swept {Format(swept.size)}.");
                return false;
            }

            if ((swept.size - rest.size).magnitude <= BoundsTolerance)
                return true;
            failures.Add(
                $"{spec.Key}: circular meter sweep changed symmetric bounds; " +
                $"rest {Format(rest.size)}, swept {Format(swept.size)}.");
            return false;
        }

        private static bool ValidateMaterials(
            Renderer[] renderers,
            Material opaque,
            Material emissive,
            out bool usedOpaque,
            out bool usedEmissive)
        {
            var result = true;
            usedOpaque = false;
            usedEmissive = false;
            foreach (var renderer in renderers)
            {
                foreach (var material in renderer.sharedMaterials)
                {
                    if (material == opaque)
                        usedOpaque = true;
                    else if (material == emissive)
                        usedEmissive = true;
                    else
                        result = false;
                }
            }
            return result;
        }

        private static void ValidateTextureImporter(
            string name,
            bool normal,
            bool srgb,
            ICollection<string> failures)
        {
            var path = $"{TextureRoot}/{name}";
            if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
            {
                failures.Add(name + ": TextureImporter missing.");
                return;
            }
            if ((importer.textureType == TextureImporterType.NormalMap) != normal)
                failures.Add(name + ": texture type mismatch.");
            if (importer.sRGBTexture != srgb)
                failures.Add(name + ": sRGB setting mismatch.");
            if (!importer.mipmapEnabled || importer.maxTextureSize != 1024)
                failures.Add(name + ": mipmap or max-size mismatch.");
            var android = importer.GetPlatformTextureSettings("Android");
            if (!android.overridden || android.format != TextureImporterFormat.ASTC_6x6)
                failures.Add(name + ": Android ASTC 6x6 setting mismatch.");
        }

        private static void RenderVisualReview()
        {
            Directory.CreateDirectory(VisualReviewRoot);
            const int cellSize = 512;
            var views = new[]
            {
                new ViewSpec("front", new Vector3(0f, 0f, 1f)),
                new ViewSpec("oblique_left", new Vector3(-0.65f, 0.22f, 1f)),
                new ViewSpec("oblique_right", new Vector3(0.65f, 0.22f, 1f)),
                new ViewSpec("side", new Vector3(1f, 0.12f, 0.12f))
            };
            var cells = new List<Color32[]>();
            var errorShaderPixels = 0;
            var cyanPixels = 0;
            foreach (var spec in Assets)
            {
                var prefabPath =
                    $"{PrefabRoot}/PF_Visual_{spec.Key}_" +
                    "MachinedErgonomics_P6A_Staging.prefab";
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (prefab == null)
                {
                    throw new FileNotFoundException(
                        "Visual review prefab is missing.", prefabPath);
                }
                foreach (var view in views)
                {
                    var pixels = RenderPrefab(prefab, view.Direction, cellSize);
                    cells.Add(pixels);
                    foreach (var pixel in pixels)
                    {
                        if (pixel.r == 255 && pixel.g == 0 && pixel.b == 255)
                            errorShaderPixels++;
                        if (pixel.r < 210 && pixel.g > 180 && pixel.b > 180)
                            cyanPixels++;
                    }
                    WritePng(
                        $"{VisualReviewRoot}/Unity_{spec.Key}_{view.Name}.png",
                        pixels,
                        cellSize,
                        cellSize);
                }
            }

            if (errorShaderPixels != 0)
            {
                throw new InvalidOperationException(
                    $"Unity review contains {errorShaderPixels} Error Shader pixels.");
            }
            if (cyanPixels < 1000)
            {
                throw new InvalidOperationException(
                    $"Unity review contains only {cyanPixels} cyan readout pixels.");
            }

            WritePng(
                $"{VisualReviewRoot}/ContactSheet_Theme4_P6A_Unity_colour.png",
                BuildContactSheet(cells, 4, 4, cellSize, false),
                cellSize * 4,
                cellSize * 4);
            WritePng(
                $"{VisualReviewRoot}/ContactSheet_Theme4_P6A_Unity_grayscale.png",
                BuildContactSheet(cells, 4, 4, cellSize, true),
                cellSize * 4,
                cellSize * 4);
            File.AppendAllText(
                ReportPath,
                "\n## Unity fixed-camera visual review\n\n" +
                $"- 16 imported-prefab renders: `{VisualReviewRoot}/Unity_*.png`\n" +
                "- Colour and grayscale 4 x 4 contact sheets generated.\n" +
                "- Camera, lighting, framing, and 512 px cell size are fixed.\n" +
                $"- Error Shader pixels: **{errorShaderPixels}**.\n" +
                $"- Cyan readout pixels: **{cyanPixels}**.\n");
        }

        private static Color32[] RenderPrefab(
            GameObject prefab,
            Vector3 cameraDirection,
            int size)
        {
            var oldAmbientMode = RenderSettings.ambientMode;
            var oldAmbientLight = RenderSettings.ambientLight;
            var oldFog = RenderSettings.fog;
            var root = new GameObject("Theme4 P6A Visual Review Root");
            var instance = UnityEngine.Object.Instantiate(prefab, root.transform, false);
            var cameraObject = new GameObject("Theme4 P6A Review Camera");
            var lightObject = new GameObject("Theme4 P6A Review Key Light");
            var fillObject = new GameObject("Theme4 P6A Review Fill Light");
            var target = new RenderTexture(size, size, 24, RenderTextureFormat.ARGB32)
            {
                antiAliasing = 4
            };
            var readable = new Texture2D(
                size, size, TextureFormat.RGBA32, false, false);
            try
            {
                instance.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                var renderers = instance.GetComponentsInChildren<Renderer>(true);
                if (renderers.Length == 0)
                    throw new MissingReferenceException(prefab.name + " has no Renderer.");
                var bounds = renderers[0].bounds;
                for (var index = 1; index < renderers.Length; index++)
                    bounds.Encapsulate(renderers[index].bounds);

                var camera = cameraObject.AddComponent<Camera>();
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = new Color(0.055f, 0.06f, 0.07f, 1f);
                camera.fieldOfView = 30f;
                camera.nearClipPlane = 0.01f;
                camera.farClipPlane = 10f;
                camera.allowHDR = true;
                camera.allowMSAA = true;
                camera.targetTexture = target;
                var direction = cameraDirection.normalized;
                var radius = Mathf.Max(bounds.extents.magnitude, 0.05f);
                var distance = radius /
                    Mathf.Tan(camera.fieldOfView * 0.5f * Mathf.Deg2Rad) * 1.25f;
                camera.transform.position = bounds.center + direction * distance;
                camera.transform.rotation = Quaternion.LookRotation(
                    bounds.center - camera.transform.position,
                    Vector3.up);

                var key = lightObject.AddComponent<Light>();
                key.type = LightType.Directional;
                key.intensity = 1.35f;
                key.color = new Color(1f, 0.96f, 0.90f);
                key.transform.rotation = Quaternion.Euler(32f, -28f, 0f);
                var fill = fillObject.AddComponent<Light>();
                fill.type = LightType.Directional;
                fill.intensity = 0.55f;
                fill.color = new Color(0.70f, 0.82f, 1f);
                fill.transform.rotation = Quaternion.Euler(18f, 145f, 0f);
                RenderSettings.ambientMode = AmbientMode.Flat;
                RenderSettings.ambientLight = new Color(0.22f, 0.23f, 0.25f);
                RenderSettings.fog = false;

                camera.Render();
                var oldActive = RenderTexture.active;
                RenderTexture.active = target;
                readable.ReadPixels(new Rect(0, 0, size, size), 0, 0);
                readable.Apply(false, false);
                RenderTexture.active = oldActive;
                return readable.GetPixels32();
            }
            finally
            {
                RenderSettings.ambientMode = oldAmbientMode;
                RenderSettings.ambientLight = oldAmbientLight;
                RenderSettings.fog = oldFog;
                var camera = cameraObject.GetComponent<Camera>();
                if (camera != null)
                    camera.targetTexture = null;
                if (RenderTexture.active == target)
                    RenderTexture.active = null;
                target.Release();
                UnityEngine.Object.DestroyImmediate(readable);
                UnityEngine.Object.DestroyImmediate(target);
                UnityEngine.Object.DestroyImmediate(root);
                UnityEngine.Object.DestroyImmediate(cameraObject);
                UnityEngine.Object.DestroyImmediate(lightObject);
                UnityEngine.Object.DestroyImmediate(fillObject);
            }
        }

        private static Color32[] BuildContactSheet(
            IReadOnlyList<Color32[]> cells,
            int columns,
            int rows,
            int cellSize,
            bool grayscale)
        {
            var width = columns * cellSize;
            var height = rows * cellSize;
            var result = new Color32[width * height];
            for (var cell = 0; cell < cells.Count; cell++)
            {
                var column = cell % columns;
                var row = rows - 1 - cell / columns;
                var source = cells[cell];
                for (var y = 0; y < cellSize; y++)
                {
                    for (var x = 0; x < cellSize; x++)
                    {
                        var colour = source[y * cellSize + x];
                        if (grayscale)
                        {
                            var luminance = (byte)Mathf.Clamp(
                                Mathf.RoundToInt(
                                    colour.r * 0.2126f +
                                    colour.g * 0.7152f +
                                    colour.b * 0.0722f),
                                0,
                                255);
                            colour = new Color32(
                                luminance, luminance, luminance, colour.a);
                        }
                        var destinationX = column * cellSize + x;
                        var destinationY = row * cellSize + y;
                        result[destinationY * width + destinationX] = colour;
                    }
                }
            }
            return result;
        }

        private static void WritePng(
            string path,
            Color32[] pixels,
            int width,
            int height)
        {
            var texture = new Texture2D(
                width, height, TextureFormat.RGBA32, false, false);
            try
            {
                texture.SetPixels32(pixels);
                texture.Apply(false, false);
                File.WriteAllBytes(path, texture.EncodeToPNG());
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(texture);
            }
        }

        private static Bounds VertexBounds(Transform root, MeshFilter[] filters)
        {
            var initialized = false;
            var result = new Bounds();
            foreach (var filter in filters)
            {
                if (filter.sharedMesh == null)
                    continue;
                foreach (var vertex in filter.sharedMesh.vertices)
                {
                    var point = root.InverseTransformPoint(
                        filter.transform.TransformPoint(vertex));
                    if (!initialized)
                    {
                        result = new Bounds(point, Vector3.zero);
                        initialized = true;
                    }
                    else
                    {
                        result.Encapsulate(point);
                    }
                }
            }
            return result;
        }

        private static Transform Find(Transform root, string name)
        {
            foreach (var candidate in root.GetComponentsInChildren<Transform>(true))
            {
                if (candidate.name == name)
                    return candidate;
            }
            return null;
        }

        private static bool Check(
            AssetSpec spec,
            string label,
            int actual,
            int expected,
            ICollection<string> failures)
        {
            if (actual == expected)
                return true;
            failures.Add($"{spec.Key}: {label} {actual}, expected {expected}.");
            return false;
        }

        private static bool CheckMaximum(
            AssetSpec spec,
            string label,
            int actual,
            int maximum,
            ICollection<string> failures)
        {
            if (actual <= maximum)
                return true;
            failures.Add(
                $"{spec.Key}: {label} {actual} exceeds {maximum} total triangles.");
            return false;
        }

        private static bool CheckVector(
            AssetSpec spec,
            string label,
            Vector3 actual,
            Vector3 expected,
            ICollection<string> failures,
            float tolerance = BoundsTolerance)
        {
            if ((actual - expected).magnitude <= tolerance)
                return true;
            failures.Add(
                $"{spec.Key}: {label} {Format(actual)}, expected {Format(expected)}.");
            return false;
        }

        private static bool CheckWithin(
            AssetSpec spec,
            string label,
            Vector3 actual,
            Vector3 maximum,
            ICollection<string> failures)
        {
            if (actual.x <= maximum.x + BoundsTolerance &&
                actual.y <= maximum.y + BoundsTolerance &&
                actual.z <= maximum.z + BoundsTolerance)
            {
                return true;
            }
            failures.Add(
                $"{spec.Key}: {label} {Format(actual)} exceeds {Format(maximum)}.");
            return false;
        }

        private static string Format(Vector3 value) =>
            $"{value.x:F6} x {value.y:F6} x {value.z:F6}";

        private static string Sha256(string path)
        {
            using var stream = File.OpenRead(path);
            using var sha = SHA256.Create();
            return BitConverter.ToString(sha.ComputeHash(stream))
                .Replace("-", string.Empty)
                .ToLowerInvariant();
        }

        private enum MotionKind
        {
            Rotate,
            Translate
        }

        private readonly struct ViewSpec
        {
            public ViewSpec(string name, Vector3 direction)
            {
                Name = name;
                Direction = direction;
            }

            public string Name { get; }
            public Vector3 Direction { get; }
        }

        private sealed class AssetSpec
        {
            private AssetSpec(
                string key,
                string fileName,
                string pivotName,
                string movingPartName,
                MotionKind motion,
                Vector3 axis,
                Vector3 pivotPosition,
                float minimum,
                float maximum,
                int triangles,
                Vector3 restSize,
                Vector3 restEnvelope,
                Vector3 sweptEnvelope,
                string sha256)
            {
                Key = key;
                FileName = fileName;
                PivotName = pivotName;
                MovingPartName = movingPartName;
                Motion = motion;
                Axis = axis;
                PivotPosition = pivotPosition;
                Minimum = minimum;
                Maximum = maximum;
                Triangles = triangles;
                RestSize = restSize;
                RestEnvelope = restEnvelope;
                SweptEnvelope = sweptEnvelope;
                Sha256 = sha256;
            }

            public static AssetSpec Rotate(
                string key,
                string fileName,
                string pivotName,
                string movingPartName,
                Vector3 axis,
                Vector3 pivotPosition,
                float minimum,
                float maximum,
                int triangles,
                Vector3 restSize,
                Vector3 restEnvelope,
                Vector3 sweptEnvelope,
                string sha256) =>
                new(key, fileName, pivotName, movingPartName, MotionKind.Rotate,
                    axis, pivotPosition, minimum, maximum, triangles, restSize,
                    restEnvelope, sweptEnvelope, sha256);

            public static AssetSpec Translate(
                string key,
                string fileName,
                string pivotName,
                string movingPartName,
                Vector3 axis,
                Vector3 pivotPosition,
                float minimum,
                float maximum,
                int triangles,
                Vector3 restSize,
                Vector3 restEnvelope,
                Vector3 sweptEnvelope,
                string sha256) =>
                new(key, fileName, pivotName, movingPartName, MotionKind.Translate,
                    axis, pivotPosition, minimum, maximum, triangles, restSize,
                    restEnvelope, sweptEnvelope, sha256);

            public string Key { get; }
            public string FileName { get; }
            public string PivotName { get; }
            public string MovingPartName { get; }
            public MotionKind Motion { get; }
            public Vector3 Axis { get; }
            public Vector3 PivotPosition { get; }
            public float Minimum { get; }
            public float Maximum { get; }
            public int Triangles { get; }
            public int TriangleBudget =>
                Key == "MeterMedium" || Key == "MeterLarge" ? 25000 : 5000;
            public Vector3 RestSize { get; }
            public Vector3 RestEnvelope { get; }
            public Vector3 SweptEnvelope { get; }
            public string Sha256 { get; }
        }
    }
}
