using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class InstrumentGreyboxContractTests
    {
        [Test]
        public void ThemeIds_AreStableUniqueAndRoundTrip()
        {
            var ids = new HashSet<string>();
            for (var index = 0; index < MockInstrumentThemeCatalog.Count; index++)
            {
                var theme = (MockInstrumentTheme)index;
                var themeId = MockInstrumentThemeCatalog.GetThemeId(theme);
                Assert.That(ids.Add(themeId), Is.True, $"Duplicate theme ID: {themeId}");
                Assert.That(
                    MockInstrumentThemeCatalog.FromThemeId(themeId),
                    Is.EqualTo(theme));
            }

            Assert.That(
                MockInstrumentThemeCatalog.FromThemeId("missing"),
                Is.EqualTo(MockInstrumentThemeCatalog.DefaultTheme));
        }

        [Test]
        public void ThemeCycle_WrapsAndInvalidValuesNormalizeToDefault()
        {
            Assert.That(
                MockInstrumentThemeCatalog.Cycle(
                    MockInstrumentTheme.KineticSafety,
                    1),
                Is.EqualTo(MockInstrumentTheme.ForgeBrass));
            Assert.That(
                MockInstrumentThemeCatalog.Cycle(
                    MockInstrumentTheme.ForgeBrass,
                    -1),
                Is.EqualTo(MockInstrumentTheme.KineticSafety));
            Assert.That(
                MockInstrumentThemeCatalog.Normalize((MockInstrumentTheme)999),
                Is.EqualTo(MockInstrumentThemeCatalog.DefaultTheme));
        }

        [Test]
        public void GlobalThemePreference_RoundTripsAndUnknownFallsBack()
        {
            var key = MockInstrumentThemePreference.PlayerPrefsKey;
            var hadPreviousValue = PlayerPrefs.HasKey(key);
            var previousValue = PlayerPrefs.GetString(key);
            try
            {
                PlayerPrefs.DeleteKey(key);
                Assert.That(
                    MockInstrumentThemePreference.Load(),
                    Is.EqualTo(MockInstrumentThemeCatalog.DefaultTheme));

                MockInstrumentThemePreference.Save(MockInstrumentTheme.ForgeBrass);
                Assert.That(
                    MockInstrumentThemePreference.Load(),
                    Is.EqualTo(MockInstrumentTheme.ForgeBrass));
                Assert.That(
                    PlayerPrefs.GetString(key),
                    Is.EqualTo("forge-brass"));

                PlayerPrefs.SetString(key, "unknown-theme");
                Assert.That(
                    MockInstrumentThemePreference.Load(),
                    Is.EqualTo(MockInstrumentThemeCatalog.DefaultTheme));
            }
            finally
            {
                if (hadPreviousValue)
                    PlayerPrefs.SetString(key, previousValue);
                else
                    PlayerPrefs.DeleteKey(key);
                PlayerPrefs.Save();
            }
        }

        [Test]
        public void AllKindsAndThemes_UseCommonRootAndSocketContract()
        {
            var pose = new Pose(
                new Vector3(1.25f, -0.5f, 2.75f),
                Quaternion.Euler(12f, 34f, 56f));

            for (var kindIndex = 0; kindIndex < MockInstrumentCatalog.Count; kindIndex++)
            {
                var kind = (MockInstrumentKind)kindIndex;
                for (var themeIndex = 0;
                     themeIndex < MockInstrumentThemeCatalog.Count;
                     themeIndex++)
                {
                    var theme = (MockInstrumentTheme)themeIndex;
                    var root = MockInstrumentFactory.Create(kind, pose, theme: theme);
                    try
                    {
                        var contract = root.GetComponent<InstrumentGreyboxContract>();
                        Assert.That(contract, Is.Not.Null);
                        Assert.That(contract.Kind, Is.EqualTo(kind));
                        Assert.That(contract.Theme, Is.EqualTo(theme));
                        Assert.That(root.transform.position, Is.EqualTo(pose.position));
                        Assert.That(
                            Quaternion.Angle(root.transform.rotation, pose.rotation),
                            Is.LessThan(0.001f));
                        Assert.That(root.transform.localScale, Is.EqualTo(Vector3.one));
                        AssertSocket(contract.MountOrigin, "MountOrigin");
                        AssertSocket(contract.Logic, "Logic");
                        AssertSocket(contract.Interaction, "Interaction");
                        AssertSocket(contract.VisualSocket, "VisualSocket");
                        AssertSocket(contract.OcclusionProxy, "OcclusionProxy");
                        AssertSocket(contract.LabelSocket, "LabelSocket");
                        AssertSocket(contract.AudioSocket, "AudioSocket");
                        AssertSocket(contract.VfxSocket, "VfxSocket");
                        Assert.That(contract.InteractionCollider, Is.Not.Null);
                        Assert.That(contract.InstrumentInteraction, Is.Not.Null);
                        Assert.That(
                            contract.InstrumentInteraction.transform,
                            Is.EqualTo(contract.Interaction));
                        Assert.That(
                            contract.InstrumentInteraction.InteractionCollider,
                            Is.SameAs(contract.InteractionCollider));
                        Assert.That(
                            contract.InteractionCollider.transform.parent,
                            Is.EqualTo(contract.Interaction));
                        var spec = InstrumentGreyboxSpecification.Get(kind);
                        Assert.That(
                            ((BoxCollider)contract.InteractionCollider).center,
                            Is.EqualTo(spec.InteractionCenter));
                        Assert.That(
                            ((BoxCollider)contract.InteractionCollider).size,
                            Is.EqualTo(spec.InteractionSize));
                        Assert.That(
                            contract.VisualSocket.GetComponentsInChildren<Collider>(),
                            Is.Empty);
                    }
                    finally
                    {
                        Object.DestroyImmediate(root);
                    }
                }
            }
        }

        [Test]
        public void AllKinds_StayInsideGreyboxRendererAndTriangleBudgets()
        {
            for (var index = 0; index < MockInstrumentCatalog.Count; index++)
            {
                var kind = (MockInstrumentKind)index;
                var root = MockInstrumentFactory.Create(kind, Pose.identity);
                try
                {
                    var spec = InstrumentGreyboxSpecification.Get(kind);
                    var renderers = root.GetComponentsInChildren<Renderer>();
                    Assert.That(renderers.Length, Is.LessThanOrEqualTo(spec.RendererBudget));

                    var materials = new HashSet<Material>();
                    foreach (var renderer in renderers)
                        materials.Add(renderer.sharedMaterial);
                    Assert.That(
                        materials.Count,
                        Is.LessThanOrEqualTo(
                            InstrumentGreyboxSpecification.SharedMaterialBudgetPerInstrument));

                    var triangles = 0;
                    foreach (var filter in root.GetComponentsInChildren<MeshFilter>())
                    {
                        if (filter.sharedMesh != null)
                            triangles += filter.sharedMesh.triangles.Length / 3;
                    }
                    Assert.That(
                        triangles,
                        Is.LessThanOrEqualTo(
                            InstrumentGreyboxSpecification.GetTriangleBudget(kind)),
                        $"{kind} exceeds its runtime triangle budget.");
                }
                finally
                {
                    Object.DestroyImmediate(root);
                }
            }
        }

        [Test]
        public void TwentyFourMixedInstruments_StayInsideAggregateQuestContentBudget()
        {
            const int maximumTriangles = 120000;
            const int maximumRenderers = 96;
            for (var themeIndex = 0;
                 themeIndex < MockInstrumentThemeCatalog.Count;
                 themeIndex++)
            {
                var roots = new List<GameObject>();
                try
                {
                    var triangles = 0;
                    var renderers = 0;
                    var colliders = 0;
                    var realtimeLights = 0;
                    for (var index = 0;
                         index < 24;
                         index++)
                    {
                        var root = MockInstrumentFactory.Create(
                            (MockInstrumentKind)(index % MockInstrumentCatalog.Count),
                            Pose.identity,
                            theme: (MockInstrumentTheme)themeIndex);
                        roots.Add(root);
                        renderers += root.GetComponentsInChildren<Renderer>().Length;
                        colliders += root.GetComponentsInChildren<Collider>().Length;
                        realtimeLights += root.GetComponentsInChildren<Light>().Length;
                        foreach (var filter in root.GetComponentsInChildren<MeshFilter>())
                        {
                            if (filter.sharedMesh != null)
                                triangles += filter.sharedMesh.triangles.Length / 3;
                        }
                    }

                    Assert.That(triangles, Is.LessThanOrEqualTo(maximumTriangles));
                    Assert.That(renderers, Is.LessThanOrEqualTo(maximumRenderers));
                    Assert.That(colliders, Is.EqualTo(24));
                    Assert.That(realtimeLights, Is.Zero);
                }
                finally
                {
                    foreach (var root in roots)
                        Object.DestroyImmediate(root);
                }
            }
        }

        [Test]
        public void Preview_HasNoColliderAndKeepsAnchorPose()
        {
            var pose = new Pose(new Vector3(-1f, 2f, 3f), Quaternion.Euler(0f, 90f, 0f));
            for (var index = 0; index < MockInstrumentCatalog.Count; index++)
            {
                var root = MockInstrumentFactory.Create(
                    (MockInstrumentKind)index,
                    pose,
                    preview: true);
                try
                {
                    Assert.That(root.GetComponentsInChildren<Collider>(), Is.Empty);
                    Assert.That(root.transform.position, Is.EqualTo(pose.position));
                    Assert.That(
                        Quaternion.Angle(root.transform.rotation, pose.rotation),
                        Is.LessThan(0.001f));
                }
                finally
                {
                    Object.DestroyImmediate(root);
                }
            }
        }

        [Test]
        public void AllThemes_UseImportedVisualHierarchy()
        {
            var expectedNodes = new[]
            {
                "needle_pivot",
                "handle_pivot",
                "switch_pivot",
                "knob_pivot",
                "button_travel",
                "indicator"
            };

            for (var themeIndex = 0;
                 themeIndex < MockInstrumentThemeCatalog.Count;
                 themeIndex++)
            {
                var theme = (MockInstrumentTheme)themeIndex;
                for (var index = 0;
                     index < MockInstrumentCatalog.PerformanceBaselineCount;
                     index++)
                {
                    var root = MockInstrumentFactory.Create(
                        (MockInstrumentKind)index,
                        Pose.identity,
                        theme: theme);
                    try
                    {
                        var contract = root.GetComponent<InstrumentGreyboxContract>();
                        var manifest =
                            contract.VisualSocket.GetComponentInChildren<ThemeVisualManifest>();
                        Assert.That(manifest, Is.Not.Null, $"Missing manifest for {theme}.");
                        Assert.That(manifest.MotionTarget, Is.Not.Null);
                        Assert.That(manifest.transform.parent, Is.EqualTo(contract.VisualSocket));
                        Assert.That(manifest.transform.localPosition, Is.EqualTo(Vector3.zero));
                        Assert.That(manifest.transform.localRotation, Is.EqualTo(Quaternion.identity));
                        Assert.That(manifest.transform.localScale, Is.EqualTo(Vector3.one));
                        Assert.That(
                            FindDescendant(contract.VisualSocket, expectedNodes[index]),
                            Is.Not.Null,
                            $"Missing imported visual node {expectedNodes[index]} for {theme}.");

                        var renderers =
                            contract.VisualSocket.GetComponentsInChildren<Renderer>();
                        Assert.That(renderers, Is.Not.Empty, $"Missing renderers for {theme}.");
                        var bounds = renderers[0].bounds;
                        for (var rendererIndex = 1;
                             rendererIndex < renderers.Length;
                             rendererIndex++)
                        {
                            bounds.Encapsulate(renderers[rendererIndex].bounds);
                        }
                        var spec = InstrumentGreyboxSpecification.Get(
                            (MockInstrumentKind)index);
                        Assert.That(bounds.size.x, Is.LessThanOrEqualTo(spec.BoundsSize.x + 0.001f));
                        Assert.That(bounds.size.y, Is.LessThanOrEqualTo(spec.BoundsSize.y + 0.001f));
                        Assert.That(bounds.size.z, Is.LessThanOrEqualTo(spec.BoundsSize.z + 0.001f));
                        Assert.That(
                            bounds.min.z,
                            Is.GreaterThanOrEqualTo(-0.001f),
                            $"Imported visual for {theme} must extend along Unity local +Z.");
                        Assert.That(
                            contract.VisualSocket.GetComponentsInChildren<Collider>(),
                            Is.Empty);
                    }
                    finally
                    {
                        Object.DestroyImmediate(root);
                    }
                }
            }
        }

        [Test]
        public void ApplyTheme_PreservesRootAnchorAndInteractionContract()
        {
            var pose = new Pose(
                new Vector3(1.5f, -0.25f, 3f),
                Quaternion.Euler(15f, 25f, 35f));

            for (var index = 0; index < MockInstrumentCatalog.Count; index++)
            {
                var kind = (MockInstrumentKind)index;
                var root = MockInstrumentFactory.Create(
                    kind,
                    pose,
                    theme: MockInstrumentTheme.OrbitalAnalog);
                try
                {
                    var contract = root.GetComponent<InstrumentGreyboxContract>();
                    var rootTransform = root.transform;
                    var mountOrigin = contract.MountOrigin;
                    var logic = contract.Logic;
                    var interaction = contract.Interaction;
                    var interactionCollider = contract.InteractionCollider;
                    var instrumentInteraction = contract.InstrumentInteraction;
                    var motion = instrumentInteraction.Motion;
                    var visualSocket = contract.VisualSocket;
                    var occlusionProxy = contract.OcclusionProxy;
                    var labelSocket = contract.LabelSocket;
                    var audioSocket = contract.AudioSocket;
                    var vfxSocket = contract.VfxSocket;
                    var beforeManifest =
                        visualSocket.GetComponentInChildren<ThemeVisualManifest>();
                    instrumentInteraction.SetNormalizedValue(0.75f);
                    var expectedNormalizedValue =
                        kind == MockInstrumentKind.StatusIndicator
                            ? 2f / 3f
                            : kind == MockInstrumentKind.ThrottleLever ||
                              kind == MockInstrumentKind.PowerSlider
                                ? 0.8f
                                : 0.75f;

                    Assert.That(
                        MockInstrumentFactory.ApplyTheme(
                            root,
                            MockInstrumentTheme.ForgeBrass),
                        Is.True);
                    Assert.That(root.transform, Is.SameAs(rootTransform));
                    Assert.That(root.transform.position, Is.EqualTo(pose.position));
                    Assert.That(
                        Quaternion.Angle(root.transform.rotation, pose.rotation),
                        Is.LessThan(0.001f));
                    Assert.That(contract.Kind, Is.EqualTo(kind));
                    Assert.That(contract.Theme, Is.EqualTo(MockInstrumentTheme.ForgeBrass));
                    Assert.That(contract.MountOrigin, Is.SameAs(mountOrigin));
                    Assert.That(contract.Logic, Is.SameAs(logic));
                    Assert.That(contract.Interaction, Is.SameAs(interaction));
                    Assert.That(
                        contract.InteractionCollider,
                        Is.SameAs(interactionCollider));
                    Assert.That(
                        contract.InstrumentInteraction,
                        Is.SameAs(instrumentInteraction));
                    Assert.That(
                        contract.InstrumentInteraction.Motion,
                        Is.SameAs(motion));
                    Assert.That(
                        contract.InstrumentInteraction.NormalizedValue,
                        Is.EqualTo(expectedNormalizedValue).Within(0.0001f));
                    Assert.That(contract.VisualSocket, Is.SameAs(visualSocket));
                    Assert.That(contract.OcclusionProxy, Is.SameAs(occlusionProxy));
                    Assert.That(contract.LabelSocket, Is.SameAs(labelSocket));
                    Assert.That(contract.AudioSocket, Is.SameAs(audioSocket));
                    Assert.That(contract.VfxSocket, Is.SameAs(vfxSocket));
                    Assert.That(visualSocket.childCount, Is.EqualTo(1));
                    Assert.That(
                        logic.GetComponents<MockInstrumentMotion>().Length,
                        Is.EqualTo(1));

                    var afterManifest =
                        visualSocket.GetComponentInChildren<ThemeVisualManifest>();
                    Assert.That(afterManifest, Is.Not.SameAs(beforeManifest));
                    Assert.That(
                        afterManifest.name,
                        Does.EndWith("_ForgeBrass"));
                    Assert.That(
                        motion.MovingPart.parent,
                        Is.SameAs(afterManifest.transform));
                    Assert.That(
                        afterManifest.MotionTarget.IsChildOf(motion.MovingPart),
                        Is.True);
                    Assert.That(
                        visualSocket.GetComponentsInChildren<Collider>(),
                        Is.Empty);

                    Assert.That(
                        MockInstrumentFactory.ApplyTheme(
                            root,
                            (MockInstrumentTheme)999),
                        Is.True);
                    Assert.That(
                        contract.Theme,
                        Is.EqualTo(MockInstrumentThemeCatalog.DefaultTheme));
                }
                finally
                {
                    Object.DestroyImmediate(root);
                }
            }
        }

        private static void AssertSocket(Transform socket, string expectedName)
        {
            Assert.That(socket, Is.Not.Null);
            Assert.That(socket.name, Is.EqualTo(expectedName));
            Assert.That(socket.localPosition, Is.EqualTo(Vector3.zero));
            Assert.That(socket.localRotation, Is.EqualTo(Quaternion.identity));
            Assert.That(socket.localScale, Is.EqualTo(Vector3.one));
        }

        private static Transform FindDescendant(Transform root, string name)
        {
            foreach (var candidate in root.GetComponentsInChildren<Transform>(true))
            {
                if (candidate.name == name)
                    return candidate;
            }
            return null;
        }
    }
}
