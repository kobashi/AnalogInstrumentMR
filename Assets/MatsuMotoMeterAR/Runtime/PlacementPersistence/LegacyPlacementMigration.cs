using System;
using MatsuMotoMeterAR.Anchors;
using MatsuMotoMeterAR.Instruments;
using UnityEngine;

namespace MatsuMotoMeterAR.PlacementPersistence
{
    public interface ILegacyPlacementSource
    {
        bool IsMigrationCompleted { get; }
        bool TryRead(out LegacyPlacementData data);
        void MarkMigrationCompleted();
    }

    public readonly struct LegacyPlacementData
    {
        public LegacyPlacementData(string anchorId, string instrumentTypeId, float value)
        {
            AnchorId = anchorId;
            InstrumentTypeId = instrumentTypeId;
            NormalizedValue = value;
        }

        public string AnchorId { get; }
        public string InstrumentTypeId { get; }
        public float NormalizedValue { get; }
    }

    public sealed class PlayerPrefsLegacyPlacementSource : ILegacyPlacementSource
    {
        public const string MigrationCompletedKey =
            "placements.legacyMigration.completed";
        public const string AnchorUuidKey = "placement.meter.round.anchorUuid";
        public const string InstrumentTypeIdKey = "placement.instrument.typeId";
        public const string InstrumentStateValueKey = "placement.instrument.stateValue";

        public bool IsMigrationCompleted =>
            PlayerPrefs.GetInt(MigrationCompletedKey, 0) == 1;

        public bool TryRead(out LegacyPlacementData data)
        {
            data = default;
            if (IsMigrationCompleted)
                return false;
            if (!Guid.TryParse(PlayerPrefs.GetString(AnchorUuidKey), out var anchorId))
                return false;

            var typeId = PlayerPrefs.GetString(
                InstrumentTypeIdKey,
                MockInstrumentCatalog.GetTypeId(MockInstrumentKind.RoundMeter));
            var kind = MockInstrumentCatalog.FromTypeId(typeId);
            var defaultValue = kind == MockInstrumentKind.RoundMeter ||
                               kind == MockInstrumentKind.Lever ||
                               kind == MockInstrumentKind.ToggleSwitch
                ? 0.5f
                : kind == MockInstrumentKind.IndicatorLamp ? 1f : 0f;
            data = new LegacyPlacementData(
                anchorId.ToString("D"),
                MockInstrumentCatalog.IsKnownTypeId(typeId)
                    ? typeId
                    : MockInstrumentCatalog.GetTypeId(MockInstrumentKind.RoundMeter),
                Mathf.Clamp01(PlayerPrefs.GetFloat(InstrumentStateValueKey, defaultValue)));
            return true;
        }

        public void MarkMigrationCompleted()
        {
            PlayerPrefs.SetInt(MigrationCompletedKey, 1);
            PlayerPrefs.Save();
        }
    }

    public static class LegacyPlacementMigration
    {
        public static PlacementLoadResult LoadOrMigrate(
            IPlacementStore store,
            ILegacyPlacementSource legacySource)
        {
            if (store == null)
                throw new ArgumentNullException(nameof(store));
            if (legacySource == null)
                throw new ArgumentNullException(nameof(legacySource));

            var existing = store.Load();
            if (existing.Status == PlacementLoadStatus.Loaded)
            {
                if (!existing.RequiresSave)
                    return existing;
                if (!store.Save(existing.Document))
                {
                    return new PlacementLoadResult(
                        PlacementLoadStatus.SaveFailed,
                        existing.Document,
                        "Placement schema migration could not be committed.");
                }
                Debug.Log(
                    $"[Placement] {existing.Message} " +
                    $"{existing.Document.placements.Count} record(s) preserved.");
                return store.Load();
            }
            if (existing.Status == PlacementLoadStatus.UnsupportedVersion)
            {
                return existing;
            }

            if (legacySource.IsMigrationCompleted)
                return existing;
            if (!legacySource.TryRead(out var legacy))
                return existing;

            var document = new PlacementDocument { revision = 1 };
            document.placements.Add(new PlacementRecord
            {
                placementId = $"legacy-{legacy.AnchorId}",
                anchorId = legacy.AnchorId,
                instrumentTypeId = legacy.InstrumentTypeId,
                surfaceKind = (int)SurfaceKind.Unknown,
                localOffset = SerializablePose.Identity,
                normalizedValue = legacy.NormalizedValue,
                lifecycle = (int)PlacementLifecycle.Active
            });
            document = PlacementJsonCodec.Normalize(document);
            if (!store.Save(document))
            {
                return new PlacementLoadResult(
                    PlacementLoadStatus.SaveFailed,
                    document,
                    "Legacy placement could not be committed to the v2 store.");
            }

            var verified = store.Load();
            if (verified.Status == PlacementLoadStatus.Loaded)
            {
                legacySource.MarkMigrationCompleted();
                return verified;
            }
            return new PlacementLoadResult(
                    PlacementLoadStatus.SaveFailed,
                    document,
                    "Legacy placement write could not be verified.");
        }
    }
}
