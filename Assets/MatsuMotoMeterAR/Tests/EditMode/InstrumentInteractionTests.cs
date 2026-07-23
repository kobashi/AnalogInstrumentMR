using MatsuMotoMeterAR.Instruments;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class InstrumentInteractionTests
    {
        [Test]
        public void TriggerPressAndRelease_UseDeterministicSemanticsForAllKinds()
        {
            var initialValues = new[] { 0.5f, 0.5f, 0.5f, 0f, 0f, 1f };
            var pressedValues = new[] { 0.75f, 0f, 0f, 0.125f, 1f, 0f };
            var releasedValues = new[] { 0.75f, 0f, 0f, 0.125f, 0f, 0f };

            for (var index = 0; index < MockInstrumentCatalog.Count; index++)
            {
                var root = MockInstrumentFactory.Create(
                    (MockInstrumentKind)index,
                    Pose.identity);
                try
                {
                    var interaction = root
                        .GetComponent<InstrumentGreyboxContract>()
                        .InstrumentInteraction;
                    Assert.That(
                        interaction.NormalizedValue,
                        Is.EqualTo(initialValues[index]).Within(0.0001f));

                    interaction.SetPressed(true);
                    Assert.That(
                        interaction.NormalizedValue,
                        Is.EqualTo(pressedValues[index]).Within(0.0001f));

                    interaction.SetPressed(true);
                    Assert.That(
                        interaction.NormalizedValue,
                        Is.EqualTo(pressedValues[index]).Within(0.0001f),
                        "Held trigger must not repeat an action.");

                    interaction.SetPressed(false);
                    Assert.That(
                        interaction.NormalizedValue,
                        Is.EqualTo(releasedValues[index]).Within(0.0001f));
                }
                finally
                {
                    Object.DestroyImmediate(root);
                }
            }
        }

        [Test]
        public void HitTest_PrioritizesDirectThenFallsBackToRay()
        {
            var target = new GameObject("Interaction Target");
            var collider = target.AddComponent<BoxCollider>();
            collider.size = Vector3.one * 0.2f;
            target.transform.position = new Vector3(0f, 0f, 2f);
            Physics.SyncTransforms();

            try
            {
                Assert.That(
                    InstrumentInteractionHitTest.Resolve(
                        collider,
                        Vector3.zero,
                        Vector3.forward,
                        0.06f,
                        0.05f,
                        5f),
                    Is.EqualTo(InstrumentInteractionHitTest.Reach.Ray));

                Assert.That(
                    InstrumentInteractionHitTest.Resolve(
                        collider,
                        new Vector3(0f, 0f, 1.84f),
                        Vector3.forward,
                        0.06f,
                        0.05f,
                        5f),
                    Is.EqualTo(InstrumentInteractionHitTest.Reach.Direct));

                Assert.That(
                    InstrumentInteractionHitTest.Resolve(
                        collider,
                        Vector3.zero,
                        Vector3.right,
                        0.06f,
                        0.05f,
                        5f),
                    Is.EqualTo(InstrumentInteractionHitTest.Reach.None));

                target.transform.position = new Vector3(0f, 0f, 6f);
                Physics.SyncTransforms();
                Assert.That(
                    InstrumentInteractionHitTest.Resolve(
                        collider,
                        Vector3.zero,
                        Vector3.forward,
                        0.06f,
                        0.05f,
                        5f),
                    Is.EqualTo(InstrumentInteractionHitTest.Reach.None));
            }
            finally
            {
                Object.DestroyImmediate(target);
            }
        }

        [Test]
        public void Resolver_PrioritizesAnyDirectHitThenNearestRayHit()
        {
            var nearRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.PushButton,
                new Pose(new Vector3(0f, 0f, 1f), Quaternion.identity));
            var farRoot = MockInstrumentFactory.Create(
                MockInstrumentKind.IndicatorLamp,
                new Pose(new Vector3(0f, 0f, 2f), Quaternion.identity));
            try
            {
                var near = nearRoot.GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                var far = farRoot.GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                var interactions = new[] { far, near };

                Assert.That(
                    InstrumentInteractionResolver.TryResolveBest(
                        interactions,
                        Vector3.zero,
                        Vector3.forward,
                        0.06f,
                        0.05f,
                        5f,
                        out var rayTarget,
                        out var rayReach),
                    Is.True);
                Assert.That(rayTarget, Is.SameAs(near));
                Assert.That(rayReach, Is.EqualTo(InstrumentInteractionHitTest.Reach.Ray));

                var directPosition = far.InteractionCollider.bounds.center -
                                     Vector3.forward * 0.06f;
                Assert.That(
                    InstrumentInteractionResolver.TryResolveBest(
                        interactions,
                        directPosition,
                        Vector3.forward,
                        0.06f,
                        0.05f,
                        5f,
                        out var directTarget,
                        out var directReach),
                    Is.True);
                Assert.That(directTarget, Is.SameAs(far));
                Assert.That(directReach, Is.EqualTo(InstrumentInteractionHitTest.Reach.Direct));
            }
            finally
            {
                Object.DestroyImmediate(nearRoot);
                Object.DestroyImmediate(farRoot);
            }
        }

        [Test]
        public void Preview_HasNoInteractionTarget()
        {
            var preview = MockInstrumentFactory.Create(
                MockInstrumentKind.PushButton,
                Pose.identity,
                preview: true);
            try
            {
                var contract = preview.GetComponent<InstrumentGreyboxContract>();
                Assert.That(contract.InstrumentInteraction, Is.Null);
                Assert.That(preview.GetComponentsInChildren<Collider>(), Is.Empty);
            }
            finally
            {
                Object.DestroyImmediate(preview);
            }
        }
    }
}
