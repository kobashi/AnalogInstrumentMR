using MatsuMotoMeterAR.Audio;
using MatsuMotoMeterAR.Instruments;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class InstrumentAudioTests
    {
        [Test]
        public void RuntimeInstruments_HaveConfiguredSpatialAudioAtAudioSocket()
        {
            for (var index = 0; index < MockInstrumentCatalog.Count; index++)
            {
                var kind = (MockInstrumentKind)index;
                for (var themeIndex = 0;
                     themeIndex < MockInstrumentThemeCatalog.Count;
                     themeIndex++)
                {
                    var theme = (MockInstrumentTheme)themeIndex;
                    var root = MockInstrumentFactory.Create(
                        kind,
                        Pose.identity,
                        theme: theme);
                    try
                    {
                        var contract = root.GetComponent<InstrumentGreyboxContract>();
                        var controller = contract.AudioSocket
                            .GetComponent<InstrumentAudioController>();
                        Assert.That(controller, Is.Not.Null, $"{theme}/{kind}");
                        Assert.That(controller.InstrumentKind, Is.EqualTo(kind));
                        Assert.That(controller.Theme, Is.EqualTo(theme));
                        Assert.That(
                            controller.Motion,
                            Is.SameAs(contract.InstrumentInteraction.Motion));
                        Assert.That(controller.OneShotSource.playOnAwake, Is.False);
                        Assert.That(controller.OneShotSource.loop, Is.False);
                        Assert.That(controller.OneShotSource.spatialBlend, Is.EqualTo(1f));
                        Assert.That(controller.OneShotSource.dopplerLevel, Is.Zero);
                        Assert.That(
                            controller.OneShotSource.minDistance,
                            Is.EqualTo(InstrumentAudioController.MinimumDistance));
                        Assert.That(
                            controller.OneShotSource.maxDistance,
                            Is.EqualTo(InstrumentAudioController.MaximumDistance));
                        var continuousMode =
                            InstrumentContinuousAudioSynth.ModeFor(kind);
                        Assert.That(
                            controller.ContinuousSource != null,
                            Is.EqualTo(
                                continuousMode !=
                                InstrumentContinuousAudioMode.None));
                        Assert.That(controller.CueCount, Is.Zero);
                    }
                    finally
                    {
                        Object.DestroyImmediate(root);
                    }
                }
            }
        }

        [Test]
        public void PlacementPreviews_RemainSilentAndHaveNoAudioSource()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.ToggleSwitch,
                Pose.identity,
                preview: true);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                Assert.That(
                    contract.AudioSocket.GetComponent<InstrumentAudioController>(),
                    Is.Null);
                Assert.That(contract.AudioSocket.GetComponent<AudioSource>(), Is.Null);
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void MotionEvent_ReportsOriginAndIgnoresEquivalentAssignments()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.Lever,
                Pose.identity);
            try
            {
                var motion = root.GetComponent<InstrumentGreyboxContract>()
                    .InstrumentInteraction.Motion;
                var eventCount = 0;
                var observed = default(InstrumentValueChange);
                motion.ValueChanged += change =>
                {
                    eventCount++;
                    observed = change;
                };

                motion.SetNormalizedValue(
                    0.5f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(eventCount, Is.Zero);

                motion.SetNormalizedValue(
                    0.75f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(eventCount, Is.EqualTo(1));
                Assert.That(observed.PreviousValue, Is.EqualTo(0.5f));
                Assert.That(observed.CurrentValue, Is.EqualTo(0.75f));
                Assert.That(observed.PreviousDetent, Is.EqualTo(2));
                Assert.That(observed.CurrentDetent, Is.EqualTo(3));
                Assert.That(
                    observed.Origin,
                    Is.EqualTo(InstrumentValueChangeOrigin.SignalGraph));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [TestCase(MockInstrumentKind.Lever)]
        [TestCase(MockInstrumentKind.ThrottleLever)]
        [TestCase(MockInstrumentKind.PowerSlider)]
        public void DetentedControls_EmitOneDirectionalCuePerChangedStep(
            MockInstrumentKind kind)
        {
            var root = MockInstrumentFactory.Create(kind, Pose.identity);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var interaction = contract.InstrumentInteraction;
                var controller = contract.AudioSocket
                    .GetComponent<InstrumentAudioController>();
                var before = interaction.DetentIndex;

                interaction.SetPressed(true);

                Assert.That(controller.CueCount, Is.EqualTo(1));
                Assert.That(
                    controller.LastCue,
                    Is.EqualTo(
                        interaction.DetentIndex > before
                            ? InstrumentAudioCue.DetentUp
                            : InstrumentAudioCue.DetentDown));
                interaction.SetPressed(true);
                Assert.That(controller.CueCount, Is.EqualTo(1));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void ToggleRotaryAndButton_UseSemanticCues()
        {
            AssertPressedCue(
                MockInstrumentKind.ToggleSwitch,
                InstrumentAudioCue.SwitchOff);
            AssertPressedCue(
                MockInstrumentKind.RotaryKnob,
                InstrumentAudioCue.RotaryStep);

            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.PushButton,
                Pose.identity);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var controller = contract.AudioSocket
                    .GetComponent<InstrumentAudioController>();
                contract.InstrumentInteraction.SetPressed(true);
                Assert.That(controller.LastCue, Is.EqualTo(InstrumentAudioCue.ButtonDown));
                contract.InstrumentInteraction.SetPressed(false);
                Assert.That(controller.LastCue, Is.EqualTo(InstrumentAudioCue.ButtonUp));
                Assert.That(controller.CueCount, Is.EqualTo(2));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void Lamp_UsesFourStagesWithHysteresisAndNoBoundaryChatter()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.IndicatorLamp,
                Pose.identity);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var controller = contract.AudioSocket
                    .GetComponent<InstrumentAudioController>();
                var interaction = contract.InstrumentInteraction;

                Assert.That(controller.LampStage, Is.EqualTo(3));
                interaction.SetNormalizedValue(0.74f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.CueCount, Is.Zero);
                interaction.SetNormalizedValue(0.71f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.LastCue,
                    Is.EqualTo(InstrumentAudioCue.LampMedium));
                Assert.That(controller.LampStage, Is.EqualTo(2));

                interaction.SetNormalizedValue(0.45f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.CueCount, Is.EqualTo(1));
                interaction.SetNormalizedValue(0.41f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.LastCue,
                    Is.EqualTo(InstrumentAudioCue.LampLow));
                Assert.That(controller.CueCount, Is.EqualTo(2));

                interaction.SetNormalizedValue(0.15f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.CueCount, Is.EqualTo(2));
                interaction.SetNormalizedValue(0.11f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.LastCue,
                    Is.EqualTo(InstrumentAudioCue.LampOff));

                interaction.SetNormalizedValue(0.17f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.CueCount, Is.EqualTo(3));
                interaction.SetNormalizedValue(0.19f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.LastCue,
                    Is.EqualTo(InstrumentAudioCue.LampLow));
                interaction.SetNormalizedValue(0.49f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.LastCue,
                    Is.EqualTo(InstrumentAudioCue.LampMedium));
                interaction.SetNormalizedValue(0.79f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.LastCue,
                    Is.EqualTo(InstrumentAudioCue.LampHigh));
                Assert.That(controller.CueCount, Is.EqualTo(6));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void Lamp_MultiStageJumpEmitsOnlyDestinationCue()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.IndicatorLamp,
                Pose.identity);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var controller = contract.AudioSocket
                    .GetComponent<InstrumentAudioController>();
                contract.InstrumentInteraction.SetNormalizedValue(
                    0f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.LampStage, Is.Zero);
                Assert.That(controller.LastCue,
                    Is.EqualTo(InstrumentAudioCue.LampOff));
                Assert.That(controller.CueCount, Is.EqualTo(1));

                contract.InstrumentInteraction.SetNormalizedValue(
                    1f,
                    InstrumentValueChangeOrigin.SignalGraph);
                Assert.That(controller.LampStage, Is.EqualTo(3));
                Assert.That(controller.LastCue,
                    Is.EqualTo(InstrumentAudioCue.LampHigh));
                Assert.That(controller.CueCount, Is.EqualTo(2));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void DetentedInstrumentTypes_HaveDistinctSoundProfilesAndClips()
        {
            var lever = InstrumentSoundProfileCatalog.Get(
                MockInstrumentKind.Lever);
            var throttle = InstrumentSoundProfileCatalog.Get(
                MockInstrumentKind.ThrottleLever);
            var slider = InstrumentSoundProfileCatalog.Get(
                MockInstrumentKind.PowerSlider);
            Assert.That(lever.Pitch, Is.Not.EqualTo(throttle.Pitch));
            Assert.That(throttle.Pitch, Is.Not.EqualTo(slider.Pitch));
            Assert.That(lever.OvertoneRatio,
                Is.Not.EqualTo(slider.OvertoneRatio));

            var leverClip = InstrumentAudioClipLibrary.Get(
                MockInstrumentTheme.OrbitalAnalog,
                MockInstrumentKind.Lever,
                InstrumentAudioCue.DetentUp);
            var throttleClip = InstrumentAudioClipLibrary.Get(
                MockInstrumentTheme.OrbitalAnalog,
                MockInstrumentKind.ThrottleLever,
                InstrumentAudioCue.DetentUp);
            var sliderClip = InstrumentAudioClipLibrary.Get(
                MockInstrumentTheme.OrbitalAnalog,
                MockInstrumentKind.PowerSlider,
                InstrumentAudioCue.DetentUp);
            Assert.That(ClipDifference(leverClip, throttleClip),
                Is.GreaterThan(1f));
            Assert.That(ClipDifference(throttleClip, sliderClip),
                Is.GreaterThan(1f));
        }

        [Test]
        public void LampStages_GenerateDistinctShortClips()
        {
            var low = InstrumentAudioClipLibrary.Get(
                MockInstrumentTheme.OrbitalAnalog,
                MockInstrumentKind.IndicatorLamp,
                InstrumentAudioCue.LampLow,
                1);
            var medium = InstrumentAudioClipLibrary.Get(
                MockInstrumentTheme.OrbitalAnalog,
                MockInstrumentKind.IndicatorLamp,
                InstrumentAudioCue.LampMedium,
                2);
            var high = InstrumentAudioClipLibrary.Get(
                MockInstrumentTheme.OrbitalAnalog,
                MockInstrumentKind.IndicatorLamp,
                InstrumentAudioCue.LampHigh,
                3);
            Assert.That(ClipDifference(low, medium), Is.GreaterThan(1f));
            Assert.That(ClipDifference(medium, high), Is.GreaterThan(1f));
            Assert.That(high.length, Is.LessThanOrEqualTo(0.076f));
        }

        [Test]
        public void RestoreAndThemeChange_UpdateStateWithoutOneShot()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.ToggleSwitch,
                Pose.identity,
                theme: MockInstrumentTheme.OrbitalAnalog);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var controller = contract.AudioSocket
                    .GetComponent<InstrumentAudioController>();
                contract.InstrumentInteraction.SetNormalizedValue(
                    0f,
                    InstrumentValueChangeOrigin.Restore);
                Assert.That(controller.CueCount, Is.Zero);

                Assert.That(
                    MockInstrumentFactory.ApplyTheme(
                        root,
                        MockInstrumentTheme.ForgeBrass),
                    Is.True);
                Assert.That(controller.CueCount, Is.Zero);
                Assert.That(controller.Theme, Is.EqualTo(MockInstrumentTheme.ForgeBrass));

                contract.InstrumentInteraction.SetNormalizedValue(
                    1f,
                    InstrumentValueChangeOrigin.Programmatic);
                Assert.That(controller.LastCue, Is.EqualTo(InstrumentAudioCue.SwitchOn));
                Assert.That(controller.CueCount, Is.EqualTo(1));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void StatusIndicator_UsesStateDistinctCues()
        {
            var root = MockInstrumentFactory.Create(
                MockInstrumentKind.StatusIndicator,
                Pose.identity);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var controller = contract.AudioSocket
                    .GetComponent<InstrumentAudioController>();
                var expected = new[]
                {
                    InstrumentAudioCue.StatusSafe,
                    InstrumentAudioCue.StatusWarning,
                    InstrumentAudioCue.StatusDanger,
                    InstrumentAudioCue.StatusOff
                };
                foreach (var cue in expected)
                {
                    contract.InstrumentInteraction.SetPressed(true);
                    contract.InstrumentInteraction.SetPressed(false);
                    Assert.That(controller.LastCue, Is.EqualTo(cue));
                }
                Assert.That(controller.CueCount, Is.EqualTo(expected.Length));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        [Test]
        public void ContinuousModes_CoverMetersAndBothDisplayKindsOnly()
        {
            var meters = new[]
            {
                MockInstrumentKind.RoundMeter,
                MockInstrumentKind.RoundMeterMedium,
                MockInstrumentKind.RoundMeterLarge,
                MockInstrumentKind.WindowMeter
            };
            foreach (var kind in meters)
            {
                Assert.That(
                    InstrumentContinuousAudioSynth.ModeFor(kind),
                    Is.EqualTo(InstrumentContinuousAudioMode.Meter));
            }
            Assert.That(
                InstrumentContinuousAudioSynth.ModeFor(
                    MockInstrumentKind.TrendMonitor),
                Is.EqualTo(InstrumentContinuousAudioMode.TrendMonitor));
            Assert.That(
                InstrumentContinuousAudioSynth.ModeFor(
                    MockInstrumentKind.WindowPanel),
                Is.EqualTo(InstrumentContinuousAudioMode.WindowPanel));
            Assert.That(
                InstrumentContinuousAudioSynth.ModeFor(
                    MockInstrumentKind.ToggleSwitch),
                Is.EqualTo(InstrumentContinuousAudioMode.None));
        }

        [Test]
        public void MeterSynthesis_IsFiniteBoundedAndPitchMonotonic()
        {
            Assert.That(
                InstrumentContinuousAudioSynth.MeterFrequency(0f),
                Is.LessThan(InstrumentContinuousAudioSynth.MeterFrequency(0.5f)));
            Assert.That(
                InstrumentContinuousAudioSynth.MeterFrequency(0.5f),
                Is.LessThan(InstrumentContinuousAudioSynth.MeterFrequency(1f)));

            var synth = new InstrumentContinuousAudioSynth(
                InstrumentContinuousAudioMode.Meter);
            synth.SetMeter(float.PositiveInfinity);
            var samples = new float[4096];
            synth.Fill(samples, 2, 48000);
            AssertFiniteAndBounded(samples);
            Assert.That(synth.SmoothedValue, Is.InRange(0f, 1f));
            Assert.That(synth.SmoothedGain, Is.GreaterThan(0f));
        }

        [Test]
        public void DisplaySynthesis_NoInputIsSilentAndInvalidValuesStayFinite()
        {
            var trend = new InstrumentContinuousAudioSynth(
                InstrumentContinuousAudioMode.TrendMonitor);
            trend.SetTrend(float.NaN, float.PositiveInfinity, -10f, 0, false);
            var trendSamples = new float[1024];
            trend.Fill(trendSamples, 1, 48000);
            AssertFiniteAndBounded(trendSamples);
            Assert.That(MaximumAbsolute(trendSamples), Is.Zero);

            var panel = new InstrumentContinuousAudioSynth(
                InstrumentContinuousAudioMode.WindowPanel);
            panel.SetWindowPanel(
                float.NaN,
                float.PositiveInfinity,
                float.NegativeInfinity,
                float.NaN,
                4,
                99,
                true);
            var panelSamples = new float[4096];
            panel.Fill(panelSamples, 2, 48000);
            AssertFiniteAndBounded(panelSamples);
        }

        [Test]
        public void ContinuousVoiceBudget_SelectsNearestEightSources()
        {
            var roots = new GameObject[10];
            try
            {
                for (var index = 0; index < roots.Length; index++)
                {
                    roots[index] = MockInstrumentFactory.Create(
                        MockInstrumentKind.RoundMeter,
                        new Pose(new Vector3(index, 0f, 0f), Quaternion.identity));
                }

                InstrumentAudioVoiceBudget.RefreshAt(Vector3.zero);
                var selected = 0;
                for (var index = 0; index < roots.Length; index++)
                {
                    var controller = roots[index]
                        .GetComponentInChildren<InstrumentAudioController>(true);
                    if (controller.ContinuousSelected)
                        selected++;
                    Assert.That(
                        controller.ContinuousSelected,
                        Is.EqualTo(index < 8));
                }
                Assert.That(
                    selected,
                    Is.EqualTo(
                        InstrumentAudioVoiceBudget.MaximumContinuousVoices));
            }
            finally
            {
                foreach (var root in roots)
                {
                    if (root != null)
                        Object.DestroyImmediate(root);
                }
            }
        }

        [Test]
        public void GeneratedOneShots_AreShortMonoFiniteAndBounded()
        {
            for (var themeIndex = 0;
                 themeIndex < MockInstrumentThemeCatalog.Count;
                 themeIndex++)
            {
                var theme = (MockInstrumentTheme)themeIndex;
                for (var cueIndex = (int)InstrumentAudioCue.SwitchOn;
                     cueIndex <= (int)InstrumentAudioCue.StatusOff;
                     cueIndex++)
                {
                    var cue = (InstrumentAudioCue)cueIndex;
                    var clip = InstrumentAudioClipLibrary.Get(theme, cue);
                    Assert.That(clip, Is.Not.Null, $"{theme}/{cue}");
                    Assert.That(clip.channels, Is.EqualTo(1));
                    Assert.That(clip.frequency, Is.EqualTo(24000));
                    Assert.That(clip.length, Is.LessThanOrEqualTo(0.076f));
                    var samples = new float[clip.samples];
                    Assert.That(clip.GetData(samples, 0), Is.True);
                    foreach (var sample in samples)
                    {
                        Assert.That(float.IsNaN(sample), Is.False);
                        Assert.That(float.IsInfinity(sample), Is.False);
                        Assert.That(Mathf.Abs(sample), Is.LessThanOrEqualTo(0.72001f));
                    }
                }
            }
        }

        private static void AssertPressedCue(
            MockInstrumentKind kind,
            InstrumentAudioCue expected)
        {
            var root = MockInstrumentFactory.Create(kind, Pose.identity);
            try
            {
                var contract = root.GetComponent<InstrumentGreyboxContract>();
                var controller = contract.AudioSocket
                    .GetComponent<InstrumentAudioController>();
                contract.InstrumentInteraction.SetPressed(true);
                Assert.That(controller.LastCue, Is.EqualTo(expected));
                Assert.That(controller.CueCount, Is.EqualTo(1));
            }
            finally
            {
                Object.DestroyImmediate(root);
            }
        }

        private static void AssertFiniteAndBounded(float[] samples)
        {
            foreach (var sample in samples)
            {
                Assert.That(float.IsNaN(sample), Is.False);
                Assert.That(float.IsInfinity(sample), Is.False);
                Assert.That(Mathf.Abs(sample), Is.LessThanOrEqualTo(0.18001f));
            }
        }

        private static float MaximumAbsolute(float[] samples)
        {
            var maximum = 0f;
            foreach (var sample in samples)
                maximum = Mathf.Max(maximum, Mathf.Abs(sample));
            return maximum;
        }

        private static float ClipDifference(AudioClip first, AudioClip second)
        {
            var firstSamples = new float[first.samples];
            var secondSamples = new float[second.samples];
            Assert.That(first.GetData(firstSamples, 0), Is.True);
            Assert.That(second.GetData(secondSamples, 0), Is.True);
            var count = Mathf.Min(firstSamples.Length, secondSamples.Length);
            var difference = 0f;
            for (var index = 0; index < count; index++)
                difference += Mathf.Abs(firstSamples[index] - secondSamples[index]);
            return difference;
        }
    }
}
