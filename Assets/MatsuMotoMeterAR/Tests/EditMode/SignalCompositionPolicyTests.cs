using MatsuMotoMeterAR.Signals;
using NUnit.Framework;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class SignalCompositionPolicyTests
    {
        [TestCase(SignalCompositionKind.Average, 0.5f)]
        [TestCase(SignalCompositionKind.Sum, 1f)]
        [TestCase(SignalCompositionKind.Minimum, 0.2f)]
        [TestCase(SignalCompositionKind.Maximum, 0.8f)]
        public void Accumulator_ComposesFiniteUnitValues(
            SignalCompositionKind kind,
            float expected)
        {
            var accumulator = new SignalCompositionAccumulator(kind);

            accumulator.Add(0.2f, 0, "a");
            accumulator.Add(0.5f, 0, "b");
            accumulator.Add(0.8f, 0, "c");

            Assert.That(accumulator.TryGetValue(out var value), Is.True);
            Assert.That(value, Is.EqualTo(expected).Within(0.0001f));
            Assert.That(accumulator.ValidCount, Is.EqualTo(3));
        }

        [Test]
        public void Accumulator_ClampsInputsAndIgnoresNonFiniteValues()
        {
            var accumulator = new SignalCompositionAccumulator(
                SignalCompositionKind.Average);

            Assert.That(accumulator.Add(float.NaN, 0, "nan"), Is.False);
            Assert.That(
                accumulator.Add(float.PositiveInfinity, 0, "infinity"),
                Is.False);
            Assert.That(accumulator.Add(-2f, 0, "low"), Is.True);
            Assert.That(accumulator.Add(3f, 0, "high"), Is.True);

            Assert.That(accumulator.TryGetValue(out var value), Is.True);
            Assert.That(value, Is.EqualTo(0.5f).Within(0.0001f));
            Assert.That(accumulator.ValidCount, Is.EqualTo(2));
        }

        [Test]
        public void Priority_SelectsHighestRankWithStableIdTieBreak()
        {
            var accumulator = new SignalCompositionAccumulator(
                SignalCompositionKind.Priority);

            accumulator.Add(0.2f, 1, "low");
            accumulator.Add(0.9f, 3, "z-last");
            accumulator.Add(0.6f, 3, "a-first");

            Assert.That(accumulator.TryGetValue(out var value), Is.True);
            Assert.That(value, Is.EqualTo(0.6f).Within(0.0001f));
        }

        [Test]
        public void EmptyAccumulator_HasNoOutput()
        {
            var accumulator = new SignalCompositionAccumulator(
                SignalCompositionKind.Average);

            Assert.That(accumulator.TryGetValue(out var value), Is.False);
            Assert.That(value, Is.Zero);
            Assert.That(accumulator.ValidCount, Is.Zero);
        }

        [Test]
        public void DefaultAccumulator_IsAValidAverageAccumulator()
        {
            var accumulator = default(SignalCompositionAccumulator);
            accumulator.Add(0.7f, 0, "only");

            Assert.That(accumulator.TryGetValue(out var value), Is.True);
            Assert.That(value, Is.EqualTo(0.7f).Within(0.0001f));
        }

        [Test]
        public void UnknownKind_FallsBackToAverage()
        {
            var accumulator = new SignalCompositionAccumulator(
                (SignalCompositionKind)999);
            accumulator.Add(0.2f, 0, "a");
            accumulator.Add(0.8f, 0, "b");

            Assert.That(accumulator.TryGetValue(out var value), Is.True);
            Assert.That(value, Is.EqualTo(0.5f).Within(0.0001f));
        }
    }
}
