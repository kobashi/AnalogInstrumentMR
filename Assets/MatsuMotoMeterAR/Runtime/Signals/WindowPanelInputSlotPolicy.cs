using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.PlacementPersistence;

namespace MatsuMotoMeterAR.Signals
{
    public static class WindowPanelInputSlotPolicy
    {
        public static bool IsValid(int slot)
        {
            return slot >= 0 &&
                   slot < WindowPanelGraphicGeometry.SlotCount;
        }

        public static bool TryReserve(
            bool[] occupiedSlots,
            int requestedSlot,
            out int assignedSlot)
        {
            if (occupiedSlots == null ||
                occupiedSlots.Length < WindowPanelGraphicGeometry.SlotCount)
            {
                throw new ArgumentException(
                    $"Slot buffer must contain {WindowPanelGraphicGeometry.SlotCount} values.",
                    nameof(occupiedSlots));
            }

            assignedSlot = SignalConnectionRecord.AutomaticTargetInputSlot;
            if (requestedSlot ==
                SignalConnectionRecord.AutomaticTargetInputSlot)
            {
                for (var slot = 0;
                     slot < WindowPanelGraphicGeometry.SlotCount;
                     slot++)
                {
                    if (occupiedSlots[slot])
                        continue;
                    occupiedSlots[slot] = true;
                    assignedSlot = slot;
                    return true;
                }
                return false;
            }

            if (!IsValid(requestedSlot) || occupiedSlots[requestedSlot])
                return false;

            occupiedSlots[requestedSlot] = true;
            assignedSlot = requestedSlot;
            return true;
        }

        public static bool TryFindLowestAvailable(
            IReadOnlyList<SignalConnectionRecord> connections,
            string targetPlacementId,
            out int slot)
        {
            var occupied = BuildOccupied(
                connections,
                targetPlacementId,
                null);
            return TryReserve(
                occupied,
                SignalConnectionRecord.AutomaticTargetInputSlot,
                out slot);
        }

        public static int CycleAvailable(
            IReadOnlyList<SignalConnectionRecord> connections,
            string targetPlacementId,
            string editedConnectionId,
            int currentSlot,
            int direction)
        {
            var occupied = BuildOccupied(
                connections,
                targetPlacementId,
                editedConnectionId);
            var start = IsValid(currentSlot) ? currentSlot : 0;
            var step = direction < 0 ? -1 : 1;
            for (var offset = 1;
                 offset <= WindowPanelGraphicGeometry.SlotCount;
                 offset++)
            {
                var candidate =
                    (start + step * offset +
                     WindowPanelGraphicGeometry.SlotCount * 2) %
                    WindowPanelGraphicGeometry.SlotCount;
                if (!occupied[candidate])
                    return candidate;
            }
            return start;
        }

        private static bool[] BuildOccupied(
            IReadOnlyList<SignalConnectionRecord> connections,
            string targetPlacementId,
            string excludedConnectionId)
        {
            var occupied = new bool[WindowPanelGraphicGeometry.SlotCount];
            if (connections == null || string.IsNullOrEmpty(targetPlacementId))
                return occupied;

            foreach (var connection in connections)
            {
                if (connection == null ||
                    connection.targetPlacementId != targetPlacementId ||
                    connection.connectionId == excludedConnectionId ||
                    !IsValid(connection.targetInputSlot))
                {
                    continue;
                }
                occupied[connection.targetInputSlot] = true;
            }
            return occupied;
        }
    }
}
