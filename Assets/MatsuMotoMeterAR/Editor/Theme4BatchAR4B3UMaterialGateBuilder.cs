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
    /// Imports the R4 B3U UV/material delivery into an isolated candidate area.
    /// Production prefabs and the runtime theme catalog are never modified.
    /// </summary>
    internal static class Theme4BatchAR4B3UMaterialGateBuilder
    {
        private const string SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/" +
            "delivery_p6/batch_a_r4_b3u";
        private const string CandidateRoot =
            "Assets/MatsuMotoMeterAR/Content/RefinedCandidates/" +
            "CandidateStaging/Theme4_P6_BatchA_R4_B3U_MaterialGate";
        private const string ModelRoot = CandidateRoot + "/Models";
        private const string TextureRoot = CandidateRoot + "/Textures";
        private const string MaterialRoot = CandidateRoot + "/Materials";
        private const string PrefabRoot = CandidateRoot + "/Prefabs";
        private const string QuestResourceRoot =
            CandidateRoot + "/Resources/Theme4_P6_BatchA_R4_B3U_1024/" +
            "MachinedErgonomics/Prefabs";
        private const string ReportPath =
            "Builds/Reports/theme4-batch-a-r4-b3u-unity-material-gate.md";
        private const string R2SourceRoot =
            "ArtSource/Blender/BrushUp/Opus5/MachinedErgonomics/" +
            "delivery_p6/batch_a_r4_b3u_r2";
        private const string R2Root = CandidateRoot + "/R2";
        private const string R2ModelRoot = R2Root + "/Models";
        private const string R2PrefabRoot = R2Root + "/Prefabs";
        private const string R2QuestResourceRoot =
            R2Root + "/Resources/Theme4_P6_BatchA_R4_B3U_R2_1024/" +
            "MachinedErgonomics/Prefabs";
        private const string R2ReportPath =
            "Builds/Reports/theme4-batch-a-r4-b3u-r2-unity-gate.md";

        private static readonly ModelSpec[] Models =
        {
            new ModelSpec(
                "Throttle",
                "SM_Throttle_MachinedErgonomics_V6_Opus5_P6A_R4_B3U.fbx",
                "8f925a1895fac8fcdcbd00c661b5acc03d10009e6908e2d5799e6430b7e5c280",
                "throttle_pivot", "throttle_handle", 4750),
            new ModelSpec(
                "PowerSlider",
                "SM_PowerSlider_MachinedErgonomics_V6_Opus5_P6A_R4_B3U.fbx",
                "01e6b10e7155822f828adb332a0d3fc68f243a96f13346ccd2bd34b855e0d441",
                "slider_travel", "slider_handle", 4644)
        };

        private static readonly TextureSpec[] Textures =
        {
            new TextureSpec(1024, "BaseColor", false, false,
                "c9c952431cb4c0baaac65ce602c353ad0f746dfabe98c7b4791e4b2ce649e8bb"),
            new TextureSpec(1024, "Normal", true, true,
                "663aa68846dd63d3109c4c29119491063d9c40ccc0365e5dacc289f5f2c366cb"),
            new TextureSpec(1024, "MetallicSmoothness", false, true,
                "b1fe9ce80ddc7f5c170eeb3c9a78fd388efe008fd8a60faf1848750da883fd88"),
            new TextureSpec(1024, "Emission", false, false,
                "1a0810ff8b05d65a564e17dbd272e27800fbcd69f79cf898e230d4b7e197ca6c"),
            new TextureSpec(2048, "BaseColor", false, false,
                "9510bb5c9c7f8a7a8ed43011768b3ae80bf0e0edde28583da5ab36c4ac711c9e"),
            new TextureSpec(2048, "Normal", true, true,
                "8a8e21d0ef1f197a1ebcdf8e0c1b41a3182441b423dc42a4da5d4920ba877b5e"),
            new TextureSpec(2048, "MetallicSmoothness", false, true,
                "76908bcd70ecc55a02fa7e478094e7367ad27bbfddc902fc7c98b1df09fcb8a6"),
            new TextureSpec(2048, "Emission", false, false,
                "d42f369562c468bc0077361739cce7d13ce6bc73532cd3bab20f5dab114fedc9")
        };

        private static readonly ModelSpec[] R2Models =
        {
            new ModelSpec(
                "Throttle",
                "SM_Throttle_MachinedErgonomics_V6_Opus5_R4_B3U_R2.fbx",
                "5966798fdacb974e7a3529b2a69a7c5593534c7b3c7daeaec5316dc7bcb3dec3",
                "throttle_pivot", "throttle_handle", 4706),
            new ModelSpec(
                "PowerSlider",
                "SM_PowerSlider_MachinedErgonomics_V6_Opus5_R4_B3U_R2.fbx",
                "0fe09ed6902e0b8504a571bdce050b05845c06fe38c118e2082797566e4ca7fb",
                "slider_travel", "slider_handle", 4600)
        };

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build and Validate Batch A R4 B3U Material Gate")]
        public static void BuildAndValidate()
        {
            Directory.CreateDirectory(ModelRoot);
            Directory.CreateDirectory(TextureRoot);
            Directory.CreateDirectory(MaterialRoot);
            Directory.CreateDirectory(PrefabRoot);

            foreach (var model in Models)
            {
                var source = SourceRoot + "/" + model.FileName;
                RequireHash(source, model.Sha256);
                File.Copy(source, ModelRoot + "/" + model.FileName, true);
            }

            foreach (var texture in Textures)
            {
                var source = SourceRoot + "/" + texture.FileName;
                RequireHash(source, texture.Sha256);
                File.Copy(source, TextureRoot + "/" + texture.FileName, true);
            }

            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var model in Models)
                ConfigureModel(ModelRoot + "/" + model.FileName);
            foreach (var texture in Textures)
                ConfigureTexture(TextureRoot + "/" + texture.FileName, texture);

            foreach (var resolution in new[] { 1024, 2048 })
            {
                var opaque = BuildMaterial(resolution, false);
                var emissive = BuildMaterial(resolution, true);
                foreach (var model in Models)
                    BuildPrefab(model, resolution, opaque, emissive);
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            WriteValidationReport();
            Debug.Log("Theme 4 Batch A R4 B3U Unity Material Gate: PASS\n" +
                      ReportPath);
        }

        [MenuItem(
            "Tools/MatsuMotoMeterAR/Theme 4/" +
            "Build and Validate Batch A R4 B3U R2 Gate")]
        public static void BuildAndValidateR2()
        {
            // Reuse the already validated byte-identical 1024 texture set and
            // opaque material. R2 changes geometry only by deleting plate_label.
            BuildAndValidate();
            Directory.CreateDirectory(R2ModelRoot);
            Directory.CreateDirectory(R2PrefabRoot);
            foreach (var model in R2Models)
            {
                var source = R2SourceRoot + "/" + model.FileName;
                RequireHash(source, model.Sha256);
                var destination = R2ModelRoot + "/" + model.FileName;
                File.Copy(source, destination, true);
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            foreach (var model in R2Models)
                ConfigureModel(R2ModelRoot + "/" + model.FileName);
            var opaque = AssetDatabase.LoadAssetAtPath<Material>(
                MaterialRoot + "/MAT_MachinedErgonomics_B3U_1024_Opaque.mat");
            if (opaque == null)
                throw new FileNotFoundException("B3U 1024 opaque material missing");
            foreach (var model in R2Models)
                BuildR2Prefab(model, opaque);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateR2();
            Debug.Log("Theme 4 Batch A R4 B3U R2 Unity Gate: PASS\n" +
                      R2ReportPath);
        }

        internal static void PrepareR2QuestReviewResources1024()
        {
            BuildAndValidateR2();
            Directory.CreateDirectory(R2QuestResourceRoot);
            foreach (var spec in R2Models)
            {
                var source =
                    $"{R2PrefabRoot}/PF_Visual_{spec.Key}_" +
                    "MachinedErgonomics_B3U_R2_1024.prefab";
                var destination =
                    $"{R2QuestResourceRoot}/PF_Visual_{spec.Key}_" +
                    "MachinedErgonomics.prefab";
                if (AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(destination) != null &&
                    !AssetDatabase.DeleteAsset(destination))
                    throw new IOException("Could not replace R2 review prefab: " + destination);
                if (!AssetDatabase.CopyAsset(source, destination))
                    throw new IOException("Could not stage R2 review prefab: " + destination);
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        internal static void PrepareQuestReviewResources1024()
        {
            BuildAndValidate();
            Directory.CreateDirectory(QuestResourceRoot);
            foreach (var spec in Models)
            {
                var source =
                    $"{PrefabRoot}/PF_Visual_{spec.Key}_" +
                    "MachinedErgonomics_B3U_1024.prefab";
                var destination =
                    $"{QuestResourceRoot}/PF_Visual_{spec.Key}_" +
                    "MachinedErgonomics.prefab";
                if (AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(destination) != null &&
                    !AssetDatabase.DeleteAsset(destination))
                    throw new IOException("Could not replace review prefab: " + destination);
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
            importer.maxTextureSize = spec.Resolution;
            importer.textureCompression = TextureImporterCompression.Compressed;
            var android = importer.GetPlatformTextureSettings("Android");
            android.name = "Android";
            android.overridden = true;
            android.maxTextureSize = spec.Resolution;
            android.format = TextureImporterFormat.ASTC_6x6;
            importer.SetPlatformTextureSettings(android);
            importer.SaveAndReimport();
        }

        private static Material BuildMaterial(int resolution, bool emissive)
        {
            var suffix = emissive ? "Emissive" : "Opaque";
            var path = $"{MaterialRoot}/MAT_MachinedErgonomics_B3U_{resolution}_{suffix}.mat";
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
                material.SetTexture("_BaseMap", LoadTexture(resolution, "Emission"));
                material.DisableKeyword("_NORMALMAP");
                material.DisableKeyword("_METALLICSPECGLOSSMAP");
            }
            else
            {
                material.SetTexture("_BaseMap", LoadTexture(resolution, "BaseColor"));
                material.SetTexture("_BumpMap", LoadTexture(resolution, "Normal"));
                material.SetFloat("_BumpScale", 1f);
                material.EnableKeyword("_NORMALMAP");
                material.SetTexture("_MetallicGlossMap",
                    LoadTexture(resolution, "MetallicSmoothness"));
                material.SetFloat("_Metallic", 1f);
                material.SetFloat("_Smoothness", 1f);
                material.EnableKeyword("_METALLICSPECGLOSSMAP");
            }
            material.enableInstancing = true;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Texture2D LoadTexture(int resolution, string role)
        {
            var path = $"{TextureRoot}/T_MachinedErgonomics_B3_{resolution}_{role}.png";
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            if (texture == null)
                throw new FileNotFoundException("Texture missing", path);
            return texture;
        }

        private static void BuildPrefab(
            ModelSpec spec, int resolution, Material opaque, Material emissive)
        {
            var modelPath = ModelRoot + "/" + spec.FileName;
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (source == null)
                throw new FileNotFoundException("Imported FBX missing", modelPath);
            var imported = PrefabUtility.InstantiatePrefab(source) as GameObject;
            if (imported == null)
                throw new InvalidOperationException("Could not instantiate " + modelPath);
            var root = new GameObject($"PF_Visual_{spec.Key}_MachinedErgonomics_B3U_{resolution}");
            try
            {
                imported.transform.SetParent(root.transform, false);
                imported.transform.localPosition = Vector3.zero;
                imported.transform.localRotation = Quaternion.Euler(-90f, 0f, 0f);
                imported.transform.localScale = Vector3.one;
                foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
                {
                    var sourceMaterials = renderer.sharedMaterials;
                    var assigned = new Material[sourceMaterials.Length];
                    for (var i = 0; i < assigned.Length; i++)
                    {
                        var sourceName = sourceMaterials[i] != null
                            ? sourceMaterials[i].name
                            : string.Empty;
                        assigned[i] = sourceName.IndexOf("Emissive",
                            StringComparison.OrdinalIgnoreCase) >= 0
                            ? emissive
                            : opaque;
                    }
                    renderer.sharedMaterials = assigned;
                }
                foreach (var collider in root.GetComponentsInChildren<Collider>(true))
                    UnityEngine.Object.DestroyImmediate(collider);
                var motionTarget = Find(root.transform, spec.Pivot);
                if (motionTarget == null)
                    throw new MissingReferenceException(
                        $"{spec.Key} is missing motion target {spec.Pivot}");
                var manifest = root.AddComponent<ThemeVisualManifest>();
                manifest.Configure(motionTarget, null, null);
                var path = $"{PrefabRoot}/{root.name}.prefab";
                PrefabUtility.SaveAsPrefabAsset(root, path);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static void BuildR2Prefab(ModelSpec spec, Material opaque)
        {
            var modelPath = R2ModelRoot + "/" + spec.FileName;
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
            if (source == null)
                throw new FileNotFoundException("Imported R2 FBX missing", modelPath);
            var imported = PrefabUtility.InstantiatePrefab(source) as GameObject;
            if (imported == null)
                throw new InvalidOperationException("Could not instantiate " + modelPath);
            var root = new GameObject(
                $"PF_Visual_{spec.Key}_MachinedErgonomics_B3U_R2_1024");
            try
            {
                imported.transform.SetParent(root.transform, false);
                imported.transform.localPosition = Vector3.zero;
                imported.transform.localRotation = Quaternion.Euler(-90f, 0f, 0f);
                imported.transform.localScale = Vector3.one;
                foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
                    renderer.sharedMaterials =
                        Enumerable.Repeat(opaque, renderer.sharedMaterials.Length).ToArray();
                foreach (var collider in root.GetComponentsInChildren<Collider>(true))
                    UnityEngine.Object.DestroyImmediate(collider);
                var motionTarget = Find(root.transform, spec.Pivot);
                if (motionTarget == null)
                    throw new MissingReferenceException(
                        $"{spec.Key} is missing motion target {spec.Pivot}");
                var manifest = root.AddComponent<ThemeVisualManifest>();
                manifest.Configure(motionTarget, null, null);
                var path = $"{R2PrefabRoot}/{root.name}.prefab";
                if (PrefabUtility.SaveAsPrefabAsset(root, path) == null)
                    throw new InvalidOperationException("Could not save " + path);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static void ValidateR2()
        {
            var rows = new List<string>();
            foreach (var spec in R2Models)
            {
                var path =
                    $"{R2PrefabRoot}/PF_Visual_{spec.Key}_" +
                    "MachinedErgonomics_B3U_R2_1024.prefab";
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null)
                    throw new FileNotFoundException("R2 prefab missing", path);
                var filters = prefab.GetComponentsInChildren<MeshFilter>(true);
                var renderers = prefab.GetComponentsInChildren<Renderer>(true);
                var triangles = filters.Sum(f =>
                    f.sharedMesh != null ? f.sharedMesh.triangles.Length / 3 : 0);
                var submeshes = filters.Sum(f =>
                    f.sharedMesh != null ? f.sharedMesh.subMeshCount : 0);
                var materials = renderers.SelectMany(r => r.sharedMaterials).ToArray();
                var manifest = prefab.GetComponent<ThemeVisualManifest>();
                if (triangles != spec.Triangles || renderers.Length != 2 ||
                    submeshes != 2 || materials.Length != 2 ||
                    materials.Any(m => m == null || !m.name.Contains("Opaque")) ||
                    manifest == null || manifest.MotionTarget == null ||
                    manifest.MotionTarget.name != spec.Pivot ||
                    Find(prefab.transform, spec.Moving) == null)
                    throw new InvalidDataException(
                        $"{spec.Key}: R2 Unity contract mismatch");
                if (prefab.GetComponentsInChildren<Transform>(true).Any(t =>
                    t.name.IndexOf("plate_label", StringComparison.OrdinalIgnoreCase) >= 0))
                    throw new InvalidDataException(spec.Key + ": plate_label residue");
                if (materials.Any(m => m.shader == null ||
                    string.Equals(m.shader.name, "Hidden/InternalErrorShader",
                        StringComparison.Ordinal)))
                    throw new InvalidDataException(spec.Key + ": invalid shader");
                rows.Add($"| {spec.Key} | {triangles} | {renderers.Length} | " +
                         $"{submeshes} | 1 opaque | 0 | PASS |");
            }
            Directory.CreateDirectory(Path.GetDirectoryName(R2ReportPath) ??
                                      "Builds/Reports");
            var report = new StringBuilder();
            report.AppendLine("# Theme 4 Batch A R4 B3U R2 Unity Gate");
            report.AppendLine();
            report.AppendLine("| Asset | Triangles | Renderers | Submeshes | Material | plate_label | Result |");
            report.AppendLine("|---|---:|---:|---:|---|---:|---|");
            foreach (var row in rows) report.AppendLine(row);
            report.AppendLine();
            report.AppendLine("- Atlas: B3U 1024, byte-identical");
            report.AppendLine("- Visual Manifest: valid");
            report.AppendLine("- Error Shader: 0");
            report.AppendLine("- Production assets/runtime catalog: unchanged");
            File.WriteAllText(R2ReportPath, report.ToString());
        }

        private static void WriteValidationReport()
        {
            var rows = new List<string>();
            foreach (var resolution in new[] { 1024, 2048 })
            {
                ValidateTextureSet(resolution);
                foreach (var spec in Models)
                {
                    var path = $"{PrefabRoot}/PF_Visual_{spec.Key}_MachinedErgonomics_B3U_{resolution}.prefab";
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                    if (prefab == null)
                        throw new FileNotFoundException("Prefab missing", path);
                    var filters = prefab.GetComponentsInChildren<MeshFilter>(true);
                    var renderers = prefab.GetComponentsInChildren<Renderer>(true);
                    var triangles = filters.Sum(f =>
                        f.sharedMesh != null ? f.sharedMesh.triangles.Length / 3 : 0);
                    var submeshes = filters.Sum(f =>
                        f.sharedMesh != null ? f.sharedMesh.subMeshCount : 0);
                    if (triangles != spec.Triangles || renderers.Length != 2 || submeshes != 3)
                        throw new InvalidDataException(
                            $"{spec.Key} {resolution}: geometry contract mismatch " +
                            $"tris={triangles}, renderers={renderers.Length}, submeshes={submeshes}");
                    if (Find(prefab.transform, spec.Pivot) == null ||
                        Find(prefab.transform, spec.Moving) == null)
                        throw new InvalidDataException(spec.Key + ": motion nodes missing");
                    var manifest = prefab.GetComponent<ThemeVisualManifest>();
                    if (manifest == null || manifest.MotionTarget == null ||
                        manifest.MotionTarget.name != spec.Pivot)
                        throw new InvalidDataException(spec.Key + ": visual manifest invalid");
                    var materials = renderers.SelectMany(r => r.sharedMaterials).ToArray();
                    if (materials.Any(m => m == null || m.shader == null ||
                        string.Equals(m.shader.name, "Hidden/InternalErrorShader",
                            StringComparison.Ordinal)))
                        throw new InvalidDataException(spec.Key + ": invalid material/shader");
                    if (!materials.Any(m => m.name.Contains("Emissive")) ||
                        !materials.Any(m => m.name.Contains("Opaque")))
                        throw new InvalidDataException(spec.Key + ": material role missing");
                    var opaque = materials.First(m => m.name.Contains("Opaque"));
                    if (!opaque.IsKeywordEnabled("_NORMALMAP") ||
                        opaque.GetTexture("_BumpMap") == null ||
                        opaque.GetTexture("_MetallicGlossMap") == null)
                        throw new InvalidDataException(spec.Key + ": relief material incomplete");
                    rows.Add($"| {resolution} | {spec.Key} | {triangles} | " +
                             $"{renderers.Length} | {submeshes} | PASS |");
                }
            }

            Directory.CreateDirectory(Path.GetDirectoryName(ReportPath) ?? "Builds/Reports");
            var text = new StringBuilder();
            text.AppendLine("# Theme 4 Batch A R4 B3U Unity Material Gate");
            text.AppendLine();
            text.AppendLine("| Atlas | Asset | Triangles | Renderers | Submeshes | Result |");
            text.AppendLine("|---:|---|---:|---:|---:|---|");
            foreach (var row in rows) text.AppendLine(row);
            text.AppendLine();
            text.AppendLine("- Android override: ASTC 6x6");
            text.AppendLine("- Mipmaps: enabled");
            text.AppendLine("- Normal: NormalMap / linear");
            text.AppendLine("- MetallicSmoothness: linear");
            text.AppendLine("- BaseColor / Emission: sRGB");
            text.AppendLine("- Production prefabs and runtime catalog: unchanged");
            File.WriteAllText(ReportPath, text.ToString());
        }

        private static void ValidateTextureSet(int resolution)
        {
            foreach (var spec in Textures.Where(t => t.Resolution == resolution))
            {
                var path = TextureRoot + "/" + spec.FileName;
                if (AssetImporter.GetAtPath(path) is not TextureImporter importer)
                    throw new FileNotFoundException("TextureImporter missing", path);
                var android = importer.GetPlatformTextureSettings("Android");
                if (!importer.mipmapEnabled || !android.overridden ||
                    android.format != TextureImporterFormat.ASTC_6x6 ||
                    android.maxTextureSize != resolution ||
                    importer.sRGBTexture != (!spec.Linear && !spec.Normal) ||
                    (spec.Normal && importer.textureType != TextureImporterType.NormalMap))
                    throw new InvalidDataException("Texture contract mismatch: " + path);
            }
        }

        private static Transform Find(Transform root, string name)
        {
            if (root.name == name) return root;
            foreach (Transform child in root)
            {
                var result = Find(child, name);
                if (result != null) return result;
            }
            return null;
        }

        private static void RequireHash(string path, string expected)
        {
            if (!File.Exists(path))
                throw new FileNotFoundException("B3U input missing", path);
            using var stream = File.OpenRead(path);
            using var sha = SHA256.Create();
            var actual = string.Concat(sha.ComputeHash(stream).Select(b => b.ToString("x2")));
            if (!string.Equals(actual, expected, StringComparison.Ordinal))
                throw new InvalidDataException("SHA mismatch: " + path);
        }

        private readonly struct ModelSpec
        {
            public readonly string Key, FileName, Sha256, Pivot, Moving;
            public readonly int Triangles;
            public ModelSpec(string key, string fileName, string sha256,
                string pivot, string moving, int triangles)
            {
                Key = key; FileName = fileName; Sha256 = sha256;
                Pivot = pivot; Moving = moving; Triangles = triangles;
            }
        }

        private readonly struct TextureSpec
        {
            public readonly int Resolution;
            public readonly string Role, Sha256;
            public readonly bool Normal, Linear;
            public string FileName =>
                $"T_MachinedErgonomics_B3_{Resolution}_{Role}.png";
            public TextureSpec(int resolution, string role, bool normal,
                bool linear, string sha256)
            {
                Resolution = resolution; Role = role; Normal = normal;
                Linear = linear; Sha256 = sha256;
            }
        }
    }
}
