using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;
using UnityEngine;

namespace MatsuMotoMeterAR.Signals
{
    public sealed class WindowPanelSignalRuntime
    {
        private readonly float[] values =
            new float[WindowPanelGraphicGeometry.SlotCount];
        private readonly bool[] connected =
            new bool[WindowPanelGraphicGeometry.SlotCount];

        public float OutputValue { get; private set; } = 0.5f;
        public int ConnectedCount { get; private set; }
        public bool HasInvalidInput { get; private set; }

        public void Refresh(
            string targetPlacementId,
            IReadOnlyList<SignalConnectionRecord> connections,
            IReadOnlyDictionary<string, MockInstrumentInteraction> instruments)
        {
            Array.Clear(connected, 0, connected.Length);
            ConnectedCount = 0;
            HasInvalidInput = false;

            if (connections != null && instruments != null)
            {
                foreach (var connection in connections)
                {
                    if (connection == null ||
                        connection.targetPlacementId != targetPlacementId ||
                        !WindowPanelInputSlotPolicy.IsValid(
                            connection.targetInputSlot) ||
                        !instruments.TryGetValue(
                            connection.sourcePlacementId,
                            out var source))
                    {
                        continue;
                    }

                    var slot = connection.targetInputSlot;
                    if (connected[slot])
                        continue;
                    var value = InstrumentSignalPolicy.Transform(
                        source.NormalizedValue,
                        connection);
                    values[slot] = value;
                    connected[slot] = true;
                    ConnectedCount++;
                    HasInvalidInput |= float.IsNaN(value) ||
                                       float.IsInfinity(value);
                }
            }

            OutputValue = connected[0] &&
                          !float.IsNaN(values[0]) &&
                          !float.IsInfinity(values[0])
                ? Mathf.Clamp01(values[0])
                : 0.5f;
        }

        public bool TryGetSlot(int slot, out float value)
        {
            if (!WindowPanelInputSlotPolicy.IsValid(slot) ||
                !connected[slot])
            {
                value = 0f;
                return false;
            }
            value = values[slot];
            return true;
        }

        public void ApplyTo(
            WindowPanelGraphicsPrototypeView view,
            WindowPanelGraphicPreset preset)
        {
            if (view == null)
                return;
            view.SetPreset(preset);
            for (var slot = 0; slot < values.Length; slot++)
                view.SetSlot(slot, values[slot], connected[slot]);
            view.ApplyNow();
        }
    }
}
