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
    internal static class Theme4Phase4CandidateBuilder
    {
        private const string SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/delivery_p4";
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging/Theme4_P4_Delivery";
        private const string ModelRoot = CandidateRoot + "/Models";
        private const string TextureRoot = CandidateRoot + "/Textures";
        private const string MaterialRoot = CandidateRoot + "/Materials";
        private const string PrefabRoot = CandidateRoot + "/Prefabs";
        private const string QuestResourceRoot =
            CandidateRoot + "/Resources/Theme4_P4_Delivery/" +
            "MachinedErgonomics/Prefabs";
        private const string ReportPath =
            "Builds/Reports/candidate-Theme4_P4-delivery-validation.md";
        private const string VisualReviewRoot =
            "Builds/Reports/Theme4_P4_VisualReview";
        private const float BoundsTolerance = 0.002f;
        private const float CenterTolerance = 0.0001f;

        private const string BaseColorName =
            "T_MachinedErgonomics_P4_Atlas_BaseColor.png";
        private const string NormalName =
            "T_MachinedErgonomics_P4_Atlas_Normal.png";
        private const string MetallicName =
            "T_MachinedErgonomics_P4_Atlas_MetallicSmoothness.png";
        private const string EmissionName =
            "T_MachinedErgonomics_P4_Atlas_Emission.png";
        private const string OpaqueMaterialPath =
            MaterialRoot + "/MAT_MachinedErgonomics_P4_Atlas_Staging.mat";
        private const string EmissiveMaterialPath =
            MaterialRoot + "/MAT_MachinedErgonomics_P4_Emissive_Staging.mat";

        private static readonly AssetSpec[] Assets =
        {
            new(
                "MeterRound",
                "SM_MeterRound_MachinedErgonomics_V6_Opus5_P4.fbx",
                "needle_pivot",
                "needle",
                Vector3.forward,
                new Vector3(0f, 0f, 0.030f),
                -115f,
                115f,
                4796,
                new Vector3(0.149f, 0.149f, 0.0426f),
                new Vector3(0f, 0f, 0.0213f),
                new Vector3(0.149f, 0.149f, 0.0426f),
                0.0335f,
                "a9301fe32db5ad44bc4d6783bf703d959243ee3613acebbf2433fdc012bbf3fc"),
            new(
                "Lever",
                "SM_Lever_MachinedErgonomics_V6_Opus5_P4.fbx",
                "handle_pivot",
                "handle",
                Vector3.right,
                new Vector3(0f, 0.080f, 0.033f),
                -48f,
                0f,
                6412,
                new Vector3(0.238810f, 0.438810f, 0.139306f),
                new Vector3(0f, 0f, 0.140364f),
                new Vector3(0.238810f, 0.438810f, 0.280728f),
                0.0148f,
                "574b9e5e6bc7026a7e454913c15038087789a691afd294898697cabfa228d9dd"),
            new(
                "Toggle",
                "SM_Toggle_MachinedErgonomics_V6_Opus5_P4.fbx",
                "switch_pivot",
                "switch",
                Vector3.right,
                new Vector3(0f, 0f, 0.042f),
                -56f,
                0f,
                3540,
                new Vector3(0.119084f, 0.169084f, 0.0612f),
                new Vector3(0f, 0f, 0.057143f),
                new Vector3(0.119084f, 0.169084f, 0.114286f),
                0.032f,
                "e50427a7961e6e15b314aef16665cb63b5c3fd18fd7d5149d71660a747003e07")
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build and Validate Phase 4 Candidate")]
        public static void BuildAndValidate()
        {
            Directory.CreateDirectory(ModelRoot);
            Directory.CreateDirectory(TextureRoot);
            Directory.CreateDirectory(MaterialRoot);
            Directory.CreateDirectory(PrefabRoot);

            foreach (var spec in Assets)
            {
                var source = $"{SourceRoot}/{spec.FileName}";
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
                    "MachinedErgonomics_P4_Staging.prefab";
                var destination =
                    $"{QuestResourceRoot}/PF_Visual_{spec.Key}_" +
                    "MachinedErgonomics.prefab";
                if (AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(destination) != null &&
                    !AssetDatabase.DeleteAsset(destination))
                {
                    throw new IOException(
                        "Could not replace generated Theme 4 review prefab: " +
                        destination);
                }
                if (!AssetDatabase.CopyAsset(source, destination))
                {
                    throw new IOException(
                        "Could not stage Theme 4 review prefab: " + destination);
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
                throw new FileNotFoundException("Theme 4 P4 input is missing.", path);
            var actual = Sha256(path);
            if (!string.Equals(actual, expected, StringComparison.Ordinal))
            {
                throw new InvalidDataException(
                    $"Theme 4 P4 SHA mismatch for {path}: {actual}");
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
                material.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
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
                throw new FileNotFoundException("Imported P4 FBX is missing.", modelPath);
            var imported = PrefabUtility.InstantiatePrefab(source) as GameObject;
            if (imported == null)
                throw new InvalidOperationException("Could not instantiate " + modelPath);

            var prefabName = $"PF_Visual_{spec.Key}_MachinedErgonomics_P4_Staging";
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

                var motionTarget = Find(root.transform, spec.MovingPartName);
                if (motionTarget == null)
                    throw new MissingReferenceException(
                        $"{spec.Key} is missing {spec.MovingPartName}.");
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
            report.AppendLine("# Theme 4 Phase 4 isolated candidate validation");
            report.AppendLine();
            report.AppendLine(
                "Nonproduction candidate only. Active prefabs, runtime registration, " +
                "production materials, and the existing three themes were not changed.");
            report.AppendLine();
            report.AppendLine(
                "| Asset | Triangles | Renderers / submeshes | Materials | Pivot m | " +
                "Rest bounds m | Swept collider m | Mount | Result |");
            report.AppendLine(
                "| --- | ---: | --- | --- | --- | --- | --- | --- | --- |");
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
            Directory.CreateDirectory(Path.GetDirectoryName(ReportPath) ?? "Builds/Reports");
            File.WriteAllText(ReportPath, report.ToString());
            if (failures.Count > 0)
                throw new InvalidOperationException("Theme 4 P4 candidate validation failed.");
            Debug.Log("Theme 4 P4 isolated candidate PASS: " + ReportPath);
        }

        private static void ValidateAsset(
            AssetSpec spec,
            Material opaque,
            Material emissive,
            StringBuilder report,
            ICollection<string> failures)
        {
            var prefabPath =
                $"{PrefabRoot}/PF_Visual_{spec.Key}_MachinedErgonomics_P4_Staging.prefab";
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

                var materialsOk = true;
                var usedOpaque = false;
                var usedEmissive = false;
                foreach (var renderer in renderers)
                {
                    foreach (var material in renderer.sharedMaterials)
                    {
                        if (material == opaque)
                            usedOpaque = true;
                        else if (material == emissive)
                            usedEmissive = true;
                        else
                            materialsOk = false;
                    }
                }

                var rest = VertexBounds(instance.transform, filters);
                var swept = rest;
                var minimumMovingZ = float.PositiveInfinity;
                var pivotPosition = pivot != null
                    ? instance.transform.InverseTransformPoint(pivot.position)
                    : Vector3.positiveInfinity;
                if (pivot != null && moving != null)
                {
                    var movingFilters = moving.GetComponentsInChildren<MeshFilter>(true);
                    var proxy = new GameObject(spec.PivotName + " Runtime Motion").transform;
                    proxy.SetParent(instance.transform, false);
                    proxy.position = pivot.position;
                    proxy.rotation = instance.transform.rotation;
                    pivot.SetParent(proxy, true);
                    for (var index = 0; index <= 96; index++)
                    {
                        var angle = Mathf.Lerp(spec.MinimumAngle, spec.MaximumAngle, index / 96f);
                        proxy.localRotation = Quaternion.AngleAxis(angle, spec.Axis);
                        swept.Encapsulate(VertexBounds(instance.transform, filters));
                        minimumMovingZ = Mathf.Min(
                            minimumMovingZ,
                            VertexBounds(instance.transform, movingFilters).min.z);
                    }
                }

                var passed = true;
                passed &= Check(spec, "triangles", triangles, spec.Triangles, failures);
                passed &= Check(spec, "renderers", renderers.Length, 2, failures);
                passed &= Check(spec, "submeshes", submeshes, 3, failures);
                passed &= CheckVector(spec, "pivot", pivotPosition, spec.PivotPosition,
                    failures, CenterTolerance);
                passed &= CheckVector(spec, "rest bounds", rest.size, spec.RestSize, failures);
                passed &= CheckVector(spec, "swept size", swept.size, spec.SweptSize, failures);
                passed &= CheckVector(spec, "swept centre", swept.center, spec.SweptCenter,
                    failures, CenterTolerance);
                if (!materialsOk || !usedOpaque || !usedEmissive)
                {
                    failures.Add($"{spec.Key}: material identity contract failed.");
                    passed = false;
                }
                if (!opaque.IsKeywordEnabled("_NORMALMAP") ||
                    !opaque.IsKeywordEnabled("_METALLICSPECGLOSSMAP") ||
                    opaque.IsKeywordEnabled("_EMISSION") ||
                    emissive.shader.name != "Universal Render Pipeline/Unlit" ||
                    emissive.GetTexture("_BaseMap") != LoadTexture(EmissionName) ||
                    emissive.IsKeywordEnabled("_NORMALMAP") ||
                    emissive.IsKeywordEnabled("_METALLICSPECGLOSSMAP") ||
                    emissive.IsKeywordEnabled("_EMISSION"))
                {
                    failures.Add($"{spec.Key}: URP material contract failed.");
                    passed = false;
                }
                if (instance.GetComponentsInChildren<Collider>(true).Length != 0)
                {
                    failures.Add($"{spec.Key}: candidate contains a Collider.");
                    passed = false;
                }
                if (Mathf.Abs(minimumMovingZ - spec.Clearance) > BoundsTolerance)
                {
                    failures.Add(
                        $"{spec.Key}: clearance {minimumMovingZ:F6}, expected {spec.Clearance:F6}.");
                    passed = false;
                }

                report.AppendLine(
                    $"| {spec.Key} | {triangles} | {renderers.Length} / {submeshes} | " +
                    $"{(materialsOk && usedOpaque && usedEmissive ? "2 shared" : "FAIL")} | " +
                    $"{Format(pivotPosition)} | {Format(rest.size)} | " +
                    $"{Format(swept.size)} @ {Format(swept.center)} | " +
                    $"{minimumMovingZ * 1000f:F3} mm | {(passed ? "PASS" : "FAIL")} |");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
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
            var colourCells = new List<Color32[]>();
            var errorShaderPixels = 0;
            var cyanReadoutPixels = 0;
            foreach (var spec in Assets)
            {
                var prefabPath =
                    $"{PrefabRoot}/PF_Visual_{spec.Key}_MachinedErgonomics_P4_Staging.prefab";
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (prefab == null)
                    throw new FileNotFoundException("Visual review prefab is missing.", prefabPath);
                foreach (var view in views)
                {
                    var pixels = RenderPrefab(prefab, view.Direction, cellSize);
                    colourCells.Add(pixels);
                    foreach (var pixel in pixels)
                    {
                        if (pixel.r == 255 && pixel.g == 0 && pixel.b == 255)
                            errorShaderPixels++;
                        if (pixel.r < 210 && pixel.g > 180 && pixel.b > 180)
                            cyanReadoutPixels++;
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
                    $"Unity visual review contains {errorShaderPixels} Error Shader pixels.");
            }
            if (cyanReadoutPixels < 1000)
            {
                throw new InvalidOperationException(
                    $"Unity visual review contains only {cyanReadoutPixels} cyan readout pixels.");
            }
            var roleLuminance = ValidateAtlasRoleLuminance();

            var colourSheet = BuildContactSheet(colourCells, 4, 3, cellSize, false);
            var grayscaleSheet = BuildContactSheet(colourCells, 4, 3, cellSize, true);
            WritePng(
                $"{VisualReviewRoot}/ContactSheet_Theme4_P4_Unity_colour.png",
                colourSheet,
                cellSize * 4,
                cellSize * 3);
            WritePng(
                $"{VisualReviewRoot}/ContactSheet_Theme4_P4_Unity_grayscale.png",
                grayscaleSheet,
                cellSize * 4,
                cellSize * 3);

            var meterPath =
                $"{PrefabRoot}/PF_Visual_MeterRound_MachinedErgonomics_P4_Staging.prefab";
            var meterPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(meterPath);
            if (meterPrefab == null)
                throw new FileNotFoundException("Meter needle gate prefab is missing.", meterPath);
            var needleCounts = new List<int>();
            foreach (var angle in new[] { -115f, 0f, 115f })
            {
                var pixels = RenderPrefab(
                    meterPrefab,
                    Vector3.forward,
                    cellSize,
                    "needle",
                    angle,
                    Vector3.forward);
                var cyan = 0;
                foreach (var pixel in pixels)
                {
                    if (pixel.r < 210 && pixel.g > 180 && pixel.b > 180)
                        cyan++;
                }
                if (cyan < 150)
                {
                    throw new InvalidOperationException(
                        $"Meter needle at {angle:F0} degrees has only {cyan} cyan pixels.");
                }
                needleCounts.Add(cyan);
                WritePng(
                    $"{VisualReviewRoot}/Unity_MeterRound_needle_{angle:+0;-0;0}.png",
                    pixels,
                    cellSize,
                    cellSize);
            }
            File.AppendAllText(
                ReportPath,
                "\n## Unity fixed-camera visual review\n\n" +
                "- 12 fixed-camera renders: `Builds/Reports/Theme4_P4_VisualReview/Unity_*.png`\n" +
                "- Colour contact sheet: `ContactSheet_Theme4_P4_Unity_colour.png`\n" +
                "- Grayscale contact sheet: `ContactSheet_Theme4_P4_Unity_grayscale.png`\n" +
                "- Camera, lighting, framing, and 512 px cell size are fixed by the builder.\n" +
                $"- Error Shader pixels: **{errorShaderPixels}**; cyan readout pixels: **{cyanReadoutPixels}**.\n" +
                $"- Imported FBX needle-only cyan pixels at -115 / 0 / +115 degrees: " +
                $"**{needleCounts[0]} / {needleCounts[1]} / {needleCounts[2]}**: PASS.\n" +
                $"- Atlas luminance: gasket {roleLuminance.Gasket:F3} < metal " +
                $"{roleLuminance.Metal:F3} < body {roleLuminance.Body:F3} < readout " +
                $"{roleLuminance.Readout:F3}: **PASS**.\n");
            Debug.Log("Theme 4 P4 Unity visual review written to " + VisualReviewRoot);
        }

        private static RoleLuminance ValidateAtlasRoleLuminance()
        {
            var basePath = $"{TextureRoot}/{BaseColorName}";
            var emissionPath = $"{TextureRoot}/{EmissionName}";
            var baseTexture = new Texture2D(2, 2, TextureFormat.RGBA32, false, false);
            var emissionTexture = new Texture2D(2, 2, TextureFormat.RGBA32, false, false);
            try
            {
                if (!baseTexture.LoadImage(File.ReadAllBytes(basePath), false) ||
                    !emissionTexture.LoadImage(File.ReadAllBytes(emissionPath), false))
                {
                    throw new InvalidDataException("Could not decode Theme 4 P4 atlas PNGs.");
                }
                var body = Luminance(baseTexture.GetPixel(256, 768));
                var metal = Luminance(baseTexture.GetPixel(768, 768));
                var gasket = Luminance(baseTexture.GetPixel(256, 256));
                var readout = Luminance(baseTexture.GetPixel(768, 256));
                var emissionBody = Luminance(emissionTexture.GetPixel(256, 768));
                var emissionMetal = Luminance(emissionTexture.GetPixel(768, 768));
                var emissionGasket = Luminance(emissionTexture.GetPixel(256, 256));
                var emissionReadout = Luminance(emissionTexture.GetPixel(768, 256));
                if (!(gasket < metal && metal < body && body < readout))
                    throw new InvalidDataException("Theme 4 P4 BaseColor role luminance order failed.");
                if (emissionBody > 0.01f || emissionMetal > 0.01f ||
                    emissionGasket > 0.01f || emissionReadout < 0.5f)
                {
                    throw new InvalidDataException("Theme 4 P4 emission quadrant contract failed.");
                }
                return new RoleLuminance(gasket, metal, body, readout);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(baseTexture);
                UnityEngine.Object.DestroyImmediate(emissionTexture);
            }
        }

        private static float Luminance(Color value) =>
            value.r * 0.2126f + value.g * 0.7152f + value.b * 0.0722f;

        private static Color32[] RenderPrefab(
            GameObject prefab,
            Vector3 cameraDirection,
            int size,
            string isolatedTransformName = null,
            float isolatedAngle = 0f,
            Vector3 isolatedAxis = default)
        {
            var oldAmbientMode = RenderSettings.ambientMode;
            var oldAmbientLight = RenderSettings.ambientLight;
            var oldFog = RenderSettings.fog;
            var root = new GameObject("Theme4 P4 Visual Review Root");
            var instance = UnityEngine.Object.Instantiate(prefab, root.transform, false);
            var cameraObject = new GameObject("Theme4 P4 Review Camera");
            var lightObject = new GameObject("Theme4 P4 Review Key Light");
            var fillObject = new GameObject("Theme4 P4 Review Fill Light");
            var texture = new RenderTexture(size, size, 24, RenderTextureFormat.ARGB32)
            {
                antiAliasing = 4
            };
            var readable = new Texture2D(size, size, TextureFormat.RGBA32, false, false);
            try
            {
                instance.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                var renderers = instance.GetComponentsInChildren<Renderer>(true);
                if (renderers.Length == 0)
                    throw new MissingReferenceException(prefab.name + " has no Renderer.");
                var bounds = renderers[0].bounds;
                for (var index = 1; index < renderers.Length; index++)
                    bounds.Encapsulate(renderers[index].bounds);
                if (!string.IsNullOrEmpty(isolatedTransformName))
                {
                    var isolated = Find(instance.transform, isolatedTransformName);
                    if (isolated == null)
                    {
                        throw new MissingReferenceException(
                            prefab.name + " is missing " + isolatedTransformName + ".");
                    }
                    isolated.localRotation = Quaternion.AngleAxis(
                        isolatedAngle,
                        isolatedAxis);
                    foreach (var renderer in renderers)
                    {
                        renderer.enabled = renderer.transform == isolated ||
                                           renderer.transform.IsChildOf(isolated);
                    }
                }

                var camera = cameraObject.AddComponent<Camera>();
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = new Color(0.055f, 0.06f, 0.07f, 1f);
                camera.fieldOfView = 30f;
                camera.nearClipPlane = 0.01f;
                camera.farClipPlane = 10f;
                camera.allowHDR = true;
                camera.allowMSAA = true;
                camera.targetTexture = texture;
                var direction = cameraDirection.normalized;
                var radius = Mathf.Max(bounds.extents.magnitude, 0.05f);
                var distance = radius / Mathf.Tan(camera.fieldOfView * 0.5f * Mathf.Deg2Rad) * 1.25f;
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
                RenderTexture.active = texture;
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
                if (RenderTexture.active == texture)
                    RenderTexture.active = null;
                texture.Release();
                UnityEngine.Object.DestroyImmediate(readable);
                UnityEngine.Object.DestroyImmediate(texture);
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
                var rowFromTop = cell / columns;
                var row = rows - 1 - rowFromTop;
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
                                    colour.r * 0.2126f + colour.g * 0.7152f + colour.b * 0.0722f),
                                0,
                                255);
                            colour = new Color32(luminance, luminance, luminance, colour.a);
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
            var texture = new Texture2D(width, height, TextureFormat.RGBA32, false, false);
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
                    var point = root.InverseTransformPoint(filter.transform.TransformPoint(vertex));
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
            failures.Add($"{spec.Key}: {label} {Format(actual)}, expected {Format(expected)}.");
            return false;
        }

        private static string Format(Vector3 value) =>
            $"{value.x:F6} × {value.y:F6} × {value.z:F6}";

        private static string Sha256(string path)
        {
            using var stream = File.OpenRead(path);
            using var sha = SHA256.Create();
            return BitConverter.ToString(sha.ComputeHash(stream))
                .Replace("-", string.Empty)
                .ToLowerInvariant();
        }

        private sealed class AssetSpec
        {
            public AssetSpec(
                string key,
                string fileName,
                string pivotName,
                string movingPartName,
                Vector3 axis,
                Vector3 pivotPosition,
                float minimumAngle,
                float maximumAngle,
                int triangles,
                Vector3 restSize,
                Vector3 sweptCenter,
                Vector3 sweptSize,
                float clearance,
                string sha256)
            {
                Key = key;
                FileName = fileName;
                PivotName = pivotName;
                MovingPartName = movingPartName;
                Axis = axis;
                PivotPosition = pivotPosition;
                MinimumAngle = minimumAngle;
                MaximumAngle = maximumAngle;
                Triangles = triangles;
                RestSize = restSize;
                SweptCenter = sweptCenter;
                SweptSize = sweptSize;
                Clearance = clearance;
                Sha256 = sha256;
            }

            public string Key { get; }
            public string FileName { get; }
            public string PivotName { get; }
            public string MovingPartName { get; }
            public Vector3 Axis { get; }
            public Vector3 PivotPosition { get; }
            public float MinimumAngle { get; }
            public float MaximumAngle { get; }
            public int Triangles { get; }
            public Vector3 RestSize { get; }
            public Vector3 SweptCenter { get; }
            public Vector3 SweptSize { get; }
            public float Clearance { get; }
            public string Sha256 { get; }
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

        private readonly struct RoleLuminance
        {
            public RoleLuminance(float gasket, float metal, float body, float readout)
            {
                Gasket = gasket;
                Metal = metal;
                Body = body;
                Readout = readout;
            }

            public float Gasket { get; }
            public float Metal { get; }
            public float Body { get; }
            public float Readout { get; }
        }
    }
}
