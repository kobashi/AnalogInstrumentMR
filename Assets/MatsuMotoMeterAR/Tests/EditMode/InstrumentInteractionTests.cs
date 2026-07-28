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
            var initialValues = new[] {
                0.5f, 0.5f, 0.5f, 0f, 0f, 1f, 0.5f, 0.5f, 0f, 0f, 0f
            };
            var pressedValues = new[] {
                0.75f, 0.75f, 0f, 0.125f, 1f, 0f, 0.75f, 0.75f, 1f / 3f, 0.2f, 0.1f
            };
            var releasedValues = new[] {
                0.75f, 0.75f, 0f, 0.125f, 0f, 0f, 0.75f, 0.75f, 1f / 3f, 0.2f, 0.1f
            };

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
        public void Lever_AdvancesAcrossFiveDetentsAndReversesAtEnds()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.Lever,
                Pose.identity);
            try
            {
                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                var expectedDetents = new[] { 3, 4, 3, 2, 1, 0, 1 };

                Assert.That(
                    interaction.DetentCount,
                    Is.EqualTo(MockInstrumentMotion.LeverDetentCount));
                Assert.That(interaction.DetentIndex, Is.EqualTo(2));

                foreach (var expectedDetent in expectedDetents)
                {
                    interaction.SetPressed(true);
                    Assert.That(
                        interaction.DetentIndex,
                        Is.EqualTo(expectedDetent));
                    Assert.That(
                        interaction.NormalizedValue,
                        Is.EqualTo(expectedDetent / 4f).Within(0.0001f));
                    interaction.SetPressed(false);
                }

                interaction.SetNormalizedValue(0.62f);
                Assert.That(interaction.DetentIndex, Is.EqualTo(2));
                Assert.That(
                    interaction.NormalizedValue,
                    Is.EqualTo(0.5f).Within(0.0001f));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void Lever_ExtremeDetentsStayParallelToMountPlane()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.Lever,
                Pose.identity);
            try
            {
                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                var movingPart = interaction.Motion.MovingPart;
                var neutralRotation = movingPart.localRotation;
                var neutralPosition = movingPart.localPosition;
                var neutralForward = neutralRotation * Vector3.forward;

                interaction.SetLeverDetentIndex(0);

                Assert.That(
                    Quaternion.Angle(
                        neutralRotation,
                        movingPart.localRotation),
                    Is.EqualTo(
                        InstrumentGreyboxSpecification
                            .LeverMaximumAngleDegrees)
                        .Within(0.001f));
                Assert.That(movingPart.localPosition, Is.EqualTo(neutralPosition));
                Assert.That(
                    Vector3.Dot(
                        neutralForward,
                        movingPart.localRotation * Vector3.forward),
                    Is.GreaterThan(0.9999f),
                    "Lever must swing across the panel, not into its base.");
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void StatusIndicator_CyclesOffSafeWarnDanger()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.StatusIndicator,
                Pose.identity);
            try
            {
                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                var expectedStates =
                    new[] { "OFF", "SAFE", "WARN", "DANGER", "OFF" };

                Assert.That(
                    interaction.DetentCount,
                    Is.EqualTo(MockInstrumentMotion.StatusIndicatorStateCount));
                Assert.That(interaction.StateName, Is.EqualTo(expectedStates[0]));

                for (var index = 1; index < expectedStates.Length; index++)
                {
                    interaction.SetPressed(true);
                    Assert.That(
                        interaction.StateName,
                        Is.EqualTo(expectedStates[index]));
                    interaction.SetPressed(false);
                }
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void Throttle_AdvancesAcrossSixDetentsAndReversesAtFull()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.ThrottleLever,
                Pose.identity);
            try
            {
                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                var expectedStates = new[]
                {
                    "CUTOFF", "IDLE", "LOW", "CRUISE",
                    "HIGH", "FULL", "HIGH"
                };

                Assert.That(
                    interaction.DetentCount,
                    Is.EqualTo(MockInstrumentMotion.ThrottleDetentCount));
                Assert.That(interaction.StateName, Is.EqualTo(expectedStates[0]));
                for (var index = 1; index < expectedStates.Length; index++)
                {
                    interaction.SetPressed(true);
                    Assert.That(
                        interaction.StateName,
                        Is.EqualTo(expectedStates[index]));
                    interaction.SetPressed(false);
                }
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void PowerSlider_AdvancesByTenPercentAndReversesAtMaximum()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.PowerSlider,
                Pose.identity);
            try
            {
                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;

                Assert.That(
                    interaction.DetentCount,
                    Is.EqualTo(MockInstrumentMotion.PowerSliderDetentCount));
                Assert.That(interaction.StateName, Is.EqualTo("OFF"));

                for (var index = 1;
                     index < MockInstrumentMotion.PowerSliderDetentCount;
                     index++)
                {
                    interaction.SetPressed(true);
                    interaction.SetPressed(false);
                }
                Assert.That(interaction.StateName, Is.EqualTo("MAX"));
                Assert.That(interaction.NormalizedValue, Is.EqualTo(1f));

                interaction.SetPressed(true);
                Assert.That(interaction.StateName, Is.EqualTo("90%"));
                Assert.That(
                    interaction.NormalizedValue,
                    Is.EqualTo(0.9f).Within(0.0001f));
            }
            finally
            {
                Object.DestroyImmediate(root);
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
