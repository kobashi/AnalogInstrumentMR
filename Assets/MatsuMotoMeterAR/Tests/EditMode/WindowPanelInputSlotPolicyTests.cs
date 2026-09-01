using MatsuMotoMeterAR.PlacementPersistence;
using MatsuMotoMeterAR.Signals;
using NUnit.Framework;
using System.Collections.Generic;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class WindowPanelInputSlotPolicyTests
    {
        [Test]
        public void AutomaticReservation_UsesLowestAvailableAndReusesReleasedSlot()
        {
            var occupied = new[] { true, false, true, false };

            Assert.That(
                WindowPanelInputSlotPolicy.TryReserve(
                    occupied,
                    SignalConnectionRecord.AutomaticTargetInputSlot,
                    out var first),
                Is.True);
            Assert.That(first, Is.EqualTo(1));

            occupied[1] = false;
            Assert.That(
                WindowPanelInputSlotPolicy.TryReserve(
                    occupied,
                    SignalConnectionRecord.AutomaticTargetInputSlot,
                    out var reused),
                Is.True);
            Assert.That(reused, Is.EqualTo(1));
        }

        [Test]
        public void ExplicitReservation_RejectsDuplicateAndOutOfRange()
        {
            var occupied = new bool[WindowPanelGraphicGeometry.SlotCount];

            Assert.That(
                WindowPanelInputSlotPolicy.TryReserve(
                    occupied, 2, out var assigned),
                Is.True);
            Assert.That(assigned, Is.EqualTo(2));
            Assert.That(
                WindowPanelInputSlotPolicy.TryReserve(
                    occupied, 2, out _),
                Is.False);
            Assert.That(
                WindowPanelInputSlotPolicy.TryReserve(
                    occupied, 4, out _),
                Is.False);
        }

        [Test]
        public void ConnectionPolicy_FindsLowestAndCyclesAroundOccupiedSlots()
        {
            var connections = new List<SignalConnectionRecord>
            {
                Connection("first", 0),
                Connection("edited", 1),
                Connection("third", 2)
            };

            Assert.That(
                WindowPanelInputSlotPolicy.TryFindLowestAvailable(
                    connections, "panel", out var lowest),
                Is.True);
            Assert.That(lowest, Is.EqualTo(3));
            Assert.That(
                WindowPanelInputSlotPolicy.CycleAvailable(
                    connections, "panel", "edited", 1, 1),
                Is.EqualTo(3));
            Assert.That(
                WindowPanelInputSlotPolicy.CycleAvailable(
                    connections, "panel", "edited", 1, -1),
                Is.EqualTo(3));
        }

        private static SignalConnectionRecord Connection(string id, int slot)
        {
            return new SignalConnectionRecord
            {
                connectionId = id,
                sourcePlacementId = id + "-source",
                targetPlacementId = "panel",
                targetInputSlot = slot
            };
        }
    }
}
