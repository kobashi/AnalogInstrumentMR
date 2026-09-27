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
        public void Toggle_SwitchesOperationAndEditOnly()
        {
            var mode = AppInteractionModePolicy.Toggle(
                AppInteractionMode.Operation);
            Assert.That(mode, Is.EqualTo(AppInteractionMode.Edit));

            mode = AppInteractionModePolicy.Toggle(mode);
            Assert.That(mode, Is.EqualTo(AppInteractionMode.Operation));

            mode = AppInteractionModePolicy.Toggle(mode);
            Assert.That(mode, Is.EqualTo(AppInteractionMode.Edit));
        }

        [TestCase(AppInteractionMode.Operation, false, false, false)]
        [TestCase(AppInteractionMode.Operation, true, false, true)]
        [TestCase(AppInteractionMode.Edit, true, false, false)]
        [TestCase(AppInteractionMode.Edit, false, true, true)]
        [TestCase(AppInteractionMode.Edit, true, true, true)]
        public void ConnectionVisuals_UseActiveEditRoleOrOperationOverride(
            AppInteractionMode mode,
            bool operationVisible,
            bool connectionEditing,
            bool expected)
        {
            Assert.That(
                AppInteractionModePolicy.ShowsConnectionVisuals(
                    mode,
                    operationVisible,
                    connectionEditing),
                Is.EqualTo(expected));
        }

        [TestCase(AppInteractionMode.Operation, true, true)]
        [TestCase(AppInteractionMode.Operation, false, false)]
        [TestCase(AppInteractionMode.Edit, true, false)]
        public void ConnectionVisualToggle_RequiresLockedOperationMode(
            AppInteractionMode mode,
            bool locked,
            bool expected)
        {
            Assert.That(
                AppInteractionModePolicy.CanToggleConnectionVisuals(
                    mode,
                    locked),
                Is.EqualTo(expected));
        }

        [TestCase(AppInteractionMode.Operation, true, true)]
        [TestCase(AppInteractionMode.Operation, false, false)]
        [TestCase(AppInteractionMode.Edit, true, false)]
        [TestCase(AppInteractionMode.Edit, false, false)]
        public void ApplicationExit_RequiresVisibleOperationSettings(
            AppInteractionMode mode,
            bool globalSettingsVisible,
            bool expected)
        {
            Assert.That(
                AppInteractionModePolicy.CanRequestApplicationExit(
                    mode,
                    globalSettingsVisible),
                Is.EqualTo(expected));
        }

        [TestCase(AppInteractionMode.Operation, true, false)]
        [TestCase(AppInteractionMode.Edit, false, false)]
        [TestCase(AppInteractionMode.Edit, true, true)]
        public void ConnectionEditing_RequiresEditModeAndRightHandRole(
            AppInteractionMode mode,
            bool connectionEditing,
            bool expected)
        {
            Assert.That(
                AppInteractionModePolicy.AllowsConnecting(
                    mode,
                    connectionEditing),
                Is.EqualTo(expected));
        }
    }
}
