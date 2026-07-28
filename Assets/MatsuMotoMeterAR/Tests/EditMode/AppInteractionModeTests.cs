using MatsuMotoMeterAR.InteractionModes;
using NUnit.Framework;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class AppInteractionModeTests
    {
        [Test]
        public void DefaultMode_AllowsOperationOnly()
        {
            var mode = AppInteractionModePolicy.DefaultMode;

            Assert.That(mode, Is.EqualTo(AppInteractionMode.Operation));
            Assert.That(
                AppInteractionModePolicy.AllowsInstrumentOperation(mode),
                Is.True);
            Assert.That(AppInteractionModePolicy.AllowsEditing(mode), Is.False);
        }

        [Test]
        public void EditMode_AllowsEditingOnly()
        {
            const AppInteractionMode mode = AppInteractionMode.Edit;

            Assert.That(AppInteractionModePolicy.AllowsEditing(mode), Is.True);
            Assert.That(
                AppInteractionModePolicy.AllowsInstrumentOperation(mode),
                Is.False);
        }

        [Test]
        public void Toggle_AlternatesBetweenOperationAndEdit()
        {
            var mode = AppInteractionModePolicy.Toggle(
                AppInteractionMode.Operation);
            Assert.That(mode, Is.EqualTo(AppInteractionMode.Edit));

            mode = AppInteractionModePolicy.Toggle(mode);
            Assert.That(mode, Is.EqualTo(AppInteractionMode.Operation));
        }
    }
}
