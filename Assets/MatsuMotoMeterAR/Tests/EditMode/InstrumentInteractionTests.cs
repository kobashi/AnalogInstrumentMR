using MatsuMotoMeterAR.Audio;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Placement;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class InstrumentInteractionTests
    {
        [TestCase(MockInstrumentKind.Lever, 0.5f, 0.75f)]
        [TestCase(MockInstrumentKind.ThrottleLever, 0f, 0.2f)]
        [TestCase(MockInstrumentKind.PowerSlider, 0f, 0.1f)]
        [TestCase(MockInstrumentKind.RotaryKnob, 0f, 0.125f)]
        [TestCase(MockInstrumentKind.StatusIndicator, 0f, 1f / 3f)]
        [TestCase(MockInstrumentKind.AudioOscillator, 0.5f, 0.625f)]
        public void DirectionalStep_TriggerIncreasesAndGripDecreases(
            MockInstrumentKind kind,
            float initial,
            float increased)
        {
            var root = MockInstrumentFactory.Create(kind, Pose.identity);
            try
            {
                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                Assert.That(interaction.NormalizedValue,
                    Is.EqualTo(initial).Within(0.0001f));

                interaction.Step(1);
                Assert.That(interaction.NormalizedValue,
                    Is.EqualTo(increased).Within(0.0001f));
                interaction.Step(-1);
                Assert.That(interaction.NormalizedValue,
                    Is.EqualTo(initial).Within(0.0001f));

                interaction.SetNormalizedValue(0f);
                interaction.Step(-1);
                Assert.That(interaction.NormalizedValue, Is.EqualTo(0f));
                interaction.SetNormalizedValue(1f);
                interaction.Step(1);
                Assert.That(interaction.NormalizedValue, Is.EqualTo(1f));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void ContactOnlyControls_DoNotAlsoReceiveDirectionalSteps()
        {
            Assert.That(MockInstrumentCatalog.UsesContactPress(
                MockInstrumentKind.PushButton), Is.True);
            Assert.That(MockInstrumentCatalog.UsesContactPress(
                MockInstrumentKind.ToggleSwitch), Is.True);
            Assert.That(MockInstrumentCatalog.SupportsDirectionalStep(
                MockInstrumentKind.PushButton), Is.False);
            Assert.That(MockInstrumentCatalog.SupportsDirectionalStep(
                MockInstrumentKind.ToggleSwitch), Is.False);
            Assert.That(MockInstrumentCatalog.SupportsDirectionalStep(
                MockInstrumentKind.Lever), Is.True);
            Assert.That(MockInstrumentCatalog.SupportsDirectionalStep(
                MockInstrumentKind.TrendMonitor), Is.False);
        }

        [TestCase(MockInstrumentKind.Lever)]
        [TestCase(MockInstrumentKind.ThrottleLever)]
        [TestCase(MockInstrumentKind.PowerSlider)]
        [TestCase(MockInstrumentKind.PushButton)]
        [TestCase(MockInstrumentKind.ToggleSwitch)]
        [TestCase(MockInstrumentKind.IndicatorLamp)]
        [TestCase(MockInstrumentKind.StatusIndicator)]
        [TestCase(MockInstrumentKind.AudioOscillator)]
        public void StickControl_AcceptsEveryOperableControl(
            MockInstrumentKind kind)
        {
            Assert.That(
                MockInstrumentCatalog.SupportsStickControl(kind),
                Is.True);
        }

        [TestCase(MockInstrumentKind.RoundMeter)]
        [TestCase(MockInstrumentKind.WindowMeter)]
        [TestCase(MockInstrumentKind.WindowPanel)]
        [TestCase(MockInstrumentKind.TrendMonitor)]
        public void StickControl_RejectsReadOnlyDisplays(
            MockInstrumentKind kind)
        {
            Assert.That(
                MockInstrumentCatalog.SupportsStickControl(kind),
                Is.False);
        }

        [Test]
        public void AnalogStickAccumulator_CrossesQuantizedLeverDetent()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.Lever,
                Pose.identity);
            try
            {
                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                var unquantizedTarget = interaction.NormalizedValue;
                for (var index = 0; index < 15; index++)
                {
                    unquantizedTarget += 0.01f;
                    interaction.SetNormalizedValue(unquantizedTarget);
                }
                Assert.That(interaction.NormalizedValue, Is.EqualTo(0.75f));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void OperationStickVertical_UpDecreasesAndDownIncreases()
        {
            Assert.That(
                OperationStickInputPolicy.ApplyVerticalDelta(
                    MockInstrumentKind.Lever,
                    0.5f,
                    1f,
                    0.25f,
                    1f),
                Is.EqualTo(0.25f).Within(0.0001f));
            Assert.That(
                OperationStickInputPolicy.ApplyVerticalDelta(
                    MockInstrumentKind.Lever,
                    0.5f,
                    -1f,
                    0.25f,
                    1f),
                Is.EqualTo(0.75f).Within(0.0001f));
            Assert.That(
                OperationStickInputPolicy.ApplyVerticalDelta(
                    MockInstrumentKind.AudioOscillator,
                    0.5f,
                    1f,
                    0.25f,
                    1f),
                Is.EqualTo(0.75f).Within(0.0001f));
        }

        [Test]
        public void StickControlledLever_KeepsContinuousVisualTarget()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.Lever,
                Pose.identity);
            try
            {
                var motion = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction
                    .Motion;

                motion.SetStickControlledValue(0.62f);

                Assert.That(motion.NormalizedValue,
                    Is.EqualTo(0.5f).Within(0.0001f));
                Assert.That(motion.StickVisualTarget,
                    Is.EqualTo(0.62f).Within(0.0001f));

                motion.EndStickControl();
                Assert.That(motion.StickVisualTarget,
                    Is.EqualTo(0.5f).Within(0.0001f));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [TestCase(MockInstrumentKind.AudioOscillator, 0.5f)]
        [TestCase(MockInstrumentKind.AudioNoise, 0.35f)]
        [TestCase(MockInstrumentKind.AudioOutput, 0.5f)]
        [TestCase(MockInstrumentKind.AudioLfo, 0.5f)]
        [TestCase(MockInstrumentKind.AudioSequencer, 0.25f)]
        [TestCase(MockInstrumentKind.AudioDelay, 0.5f)]
        [TestCase(MockInstrumentKind.AudioVca, 0.5f)]
        [TestCase(MockInstrumentKind.AudioMixer, 0.5f)]
        [TestCase(MockInstrumentKind.AudioFilter, 0.5f)]
        [TestCase(MockInstrumentKind.AudioEnvelope, 0.5f)]
        public void SoundModule_GripStepsBackwardAndResetRestoresDefault(
            MockInstrumentKind kind,
            float defaultValue)
        {
            var root = MockInstrumentFactory.Create(kind, Pose.identity);
            try
            {
                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                Assert.That(MockInstrumentCatalog.IsSoundModule(kind), Is.True);
                Assert.That(interaction.NormalizedValue,
                    Is.EqualTo(defaultValue).Within(0.0001f));

                interaction.SetNormalizedValue(0.875f);
                interaction.Step(-1);
                Assert.That(interaction.NormalizedValue,
                    Is.EqualTo(0.75f).Within(0.0001f));

                interaction.ResetSoundModuleValue(kind);
                Assert.That(interaction.NormalizedValue,
                    Is.EqualTo(defaultValue).Within(0.0001f));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void SoundModuleReset_DoesNotAffectOrdinaryRotaryKnob()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.RotaryKnob,
                Pose.identity);
            try
            {
                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                interaction.SetNormalizedValue(0.75f);
                interaction.ResetSoundModuleValue(
                    MockInstrumentKind.RotaryKnob);
                Assert.That(interaction.NormalizedValue,
                    Is.EqualTo(0.75f).Within(0.0001f));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void SoundModule_GripAndResetRespectConfiguredStepCount()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.AudioNoise,
                Pose.identity);
            try
            {
                var interaction = root
                    .GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction;
                interaction.ConfigureParameterRange(
                    new AdjustableParameterSetting
                    {
                        minimum = 0.02f,
                        maximum = 0.35f,
                        stepCount = 101
                    });
                interaction.SetNormalizedValue(0.35f);
                interaction.Step(-1);
                Assert.That(interaction.NormalizedValue,
                    Is.EqualTo(0.34f).Within(0.0001f));

                interaction.ResetSoundModuleValue(
                    MockInstrumentKind.AudioNoise);
                Assert.That(interaction.NormalizedValue,
                    Is.EqualTo(0.35f).Within(0.0001f));
                Assert.That(interaction.DetentCount, Is.EqualTo(101));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void TriggerPressAndRelease_UseDeterministicSemanticsForAllKinds()
        {
            var initialValues = new[] {
                0.5f, 0.5f, 0.5f, 0f, 0f, 1f, 0.5f,
                0.5f, 0f, 0f, 0f, 0.5f, 0.5f, 0f,
                0.5f, 0.35f, 0.5f, 0.5f, 0.25f, 0.5f,
                0.5f, 0.5f, 0.5f, 0.5f
            };
            var pressedValues = new[] {
                0.5f, 0.75f, 0f, 0.125f, 1f, 0f, 0.5f,
                0.5f, 1f / 3f, 0.2f, 0.1f, 0.5f, 0.5f, 0f,
                0.625f, 0.475f, 0.625f, 0.625f, 0.375f, 0.625f,
                0.625f, 0.625f, 0.625f, 0.625f
            };
            var releasedValues = new[] {
                0.5f, 0.75f, 0f, 0.125f, 0f, 0f, 0.5f,
                0.5f, 1f / 3f, 0.2f, 0.1f, 0.5f, 0.5f, 0f,
                0.625f, 0.475f, 0.625f, 0.625f, 0.375f, 0.625f,
                0.625f, 0.625f, 0.625f, 0.625f
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
        public void Lever_ExtremeDetentsRotateAroundMountPlaneAxis()
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
                var neutralAxis = neutralRotation * Vector3.right;

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
                        neutralAxis,
                        movingPart.localRotation * Vector3.right),
                    Is.GreaterThan(0.9999f),
                    "Lever rotation axis must stay in the mounting plane.");
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
