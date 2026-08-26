using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Anchors;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.Signals;
using UnityEngine;

namespace MatsuMotoMeterAR.PlacementPersistence
{
    public enum PlacementLoadStatus
    {
        Loaded,
        Missing,
        Corrupt,
        UnsupportedVersion,
        SaveFailed
    }

    public readonly struct PlacementLoadResult
    {
        public PlacementLoadResult(
            PlacementLoadStatus status,
            PlacementDocument document,
            string message = null,
            bool requiresSave = false)
        {
            Status = status;
            Document = document;
            Message = message;
            RequiresSave = requiresSave;
        }

        public PlacementLoadStatus Status { get; }
        public PlacementDocument Document { get; }
        public string Message { get; }
        public bool RequiresSave { get; }
        public bool CanWrite => Status == PlacementLoadStatus.Loaded ||
                                Status == PlacementLoadStatus.Missing;
    }

    public interface IPlacementStore
    {
        PlacementLoadResult Load();
        bool Save(PlacementDocument document);
    }

    public sealed class PlayerPrefsPlacementStore : IPlacementStore
    {
        public const string PlayerPrefsKey = "placements.document.json";

        public PlacementLoadResult Load()
        {
            if (!PlayerPrefs.HasKey(PlayerPrefsKey))
            {
                return new PlacementLoadResult(
                    PlacementLoadStatus.Missing,
                    new PlacementDocument());
            }

            return PlacementJsonCodec.Deserialize(
                PlayerPrefs.GetString(PlayerPrefsKey));
        }

        public bool Save(PlacementDocument document)
        {
            try
            {
                var json = PlacementJsonCodec.Serialize(document);
                PlayerPrefs.SetString(PlayerPrefsKey, json);
                PlayerPrefs.Save();
                return PlayerPrefs.GetString(PlayerPrefsKey) == json;
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                return false;
            }
        }
    }

    public static class PlacementJsonCodec
    {
        public static string Serialize(PlacementDocument document)
        {
            if (document == null)
                throw new ArgumentNullException(nameof(document));

            var normalized = Normalize(document);
            return JsonUtility.ToJson(normalized);
        }

        public static PlacementLoadResult Deserialize(string json)
        {
            if (string.IsNullOrWhiteSpace(json) ||
                json.IndexOf("\"schemaVersion\"", StringComparison.Ordinal) < 0)
            {
                return Corrupt("Missing schemaVersion.");
            }

            try
            {
                var document = JsonUtility.FromJson<PlacementDocument>(json);
                if (document == null)
                    return Corrupt("JSON produced no placement document.");
                if (document.schemaVersion > PlacementDocument.CurrentSchemaVersion)
                {
                    return new PlacementLoadResult(
                        PlacementLoadStatus.UnsupportedVersion,
                        document,
                        $"Schema {document.schemaVersion} is newer than supported schema " +
                        $"{PlacementDocument.CurrentSchemaVersion}.");
                }
                if (document.schemaVersion >=
                    PlacementDocument.LegacySchemaVersion &&
                    document.schemaVersion <
                    PlacementDocument.CurrentSchemaVersion)
                {
                    var sourceVersion = document.schemaVersion;
                    return new PlacementLoadResult(
                        PlacementLoadStatus.Loaded,
                        Normalize(document),
                        $"Migrated placement schema " +
                        $"{sourceVersion} to " +
                        $"{PlacementDocument.CurrentSchemaVersion}.",
                        requiresSave: true);
                }
                if (document.schemaVersion != PlacementDocument.CurrentSchemaVersion)
                    return Corrupt($"Unsupported legacy schema {document.schemaVersion}.");

                return new PlacementLoadResult(
                    PlacementLoadStatus.Loaded,
                    Normalize(document));
            }
            catch (Exception exception)
            {
                return Corrupt(exception.Message);
            }
        }

        public static PlacementDocument Normalize(PlacementDocument source)
        {
            var normalized = new PlacementDocument
            {
                schemaVersion = PlacementDocument.CurrentSchemaVersion,
                revision = Math.Max(0, source?.revision ?? 0),
                placements = new List<PlacementRecord>(),
                connections = new List<SignalConnectionRecord>()
            };
            if (source?.placements == null)
                return normalized;

            var placementIds = new HashSet<string>(StringComparer.Ordinal);
            var activeTypeIds = new Dictionary<string, string>(
                StringComparer.Ordinal);
            var storedCount = 0;
            var roomPlacementCounts = new Dictionary<string, int>(
                StringComparer.OrdinalIgnoreCase);
            foreach (var sourceRecord in source.placements)
            {
                if (!TryNormalizeRecord(sourceRecord, out var record) ||
                    !placementIds.Add(record.placementId))
                {
                    continue;
                }

                if (record.lifecycle == (int)PlacementLifecycle.Active ||
                    record.lifecycle == (int)PlacementLifecycle.Unavailable)
                {
                    var roomKey = record.roomId ?? string.Empty;
                    roomPlacementCounts.TryGetValue(
                        roomKey,
                        out var roomPlacementCount);
                    if (roomPlacementCount >=
                            PlacementDocument.MaximumActivePlacements ||
                        storedCount >=
                            PlacementDocument.MaximumStoredPlacements)
                    {
                        continue;
                    }
                    roomPlacementCounts[roomKey] =
                        roomPlacementCount + 1;
                    storedCount++;
                    activeTypeIds[record.placementId] =
                        record.instrumentTypeId;
                }
                normalized.placements.Add(record);
            }

            if (source.connections == null)
                return normalized;

            var connectionIds = new HashSet<string>(StringComparer.Ordinal);
            var endpointPairs = new HashSet<string>(StringComparer.Ordinal);
            var trendMonitorInputCounts = new Dictionary<string, int>(
                StringComparer.Ordinal);
            foreach (var sourceConnection in source.connections)
            {
                if (normalized.connections.Count >=
                    PlacementDocument.MaximumConnections)
                {
                    break;
                }
                if (!TryNormalizeConnection(
                        sourceConnection,
                        activeTypeIds,
                        connectionIds,
                        endpointPairs,
                        out var connection))
                {
                    continue;
                }

                var targetKind = MockInstrumentCatalog.FromTypeId(
                    activeTypeIds[connection.targetPlacementId]);
                if (targetKind == MockInstrumentKind.TrendMonitor)
                {
                    trendMonitorInputCounts.TryGetValue(
                        connection.targetPlacementId,
                        out var inputCount);
                    if (inputCount >=
                        InstrumentSignalPolicy.MaximumTrendMonitorInputs)
                    {
                        continue;
                    }
                    trendMonitorInputCounts[connection.targetPlacementId] =
                        inputCount + 1;
                }
                normalized.connections.Add(connection);
            }
            return normalized;
        }

        private static bool TryNormalizeConnection(
            SignalConnectionRecord source,
            IReadOnlyDictionary<string, string> activeTypeIds,
            ISet<string> connectionIds,
            ISet<string> endpointPairs,
            out SignalConnectionRecord connection)
        {
            connection = null;
            if (source == null ||
                string.IsNullOrWhiteSpace(source.connectionId) ||
                string.IsNullOrWhiteSpace(source.sourcePlacementId) ||
                string.IsNullOrWhiteSpace(source.targetPlacementId))
            {
                return false;
            }

            var connectionId = source.connectionId.Trim();
            var sourceId = source.sourcePlacementId.Trim();
            var targetId = source.targetPlacementId.Trim();
            if (sourceId == targetId ||
                !connectionIds.Add(connectionId) ||
                !activeTypeIds.TryGetValue(sourceId, out var sourceTypeId) ||
                !activeTypeIds.TryGetValue(targetId, out var targetTypeId) ||
                !InstrumentSignalPolicy.CanConnect(
                    MockInstrumentCatalog.FromTypeId(sourceTypeId),
                    MockInstrumentCatalog.FromTypeId(targetTypeId)))
            {
                return false;
            }

            var endpointPair = sourceId + "\n" + targetId;
            if (!endpointPairs.Add(endpointPair))
                return false;

            var transform = Enum.IsDefined(
                typeof(SignalTransformKind),
                source.transformKind)
                ? source.transformKind
                : (int)SignalTransformKind.Direct;
            connection = new SignalConnectionRecord
            {
                connectionId = connectionId,
                sourcePlacementId = sourceId,
                targetPlacementId = targetId,
                transformKind = transform
            };
            return true;
        }

        private static bool TryNormalizeRecord(
            PlacementRecord source,
            out PlacementRecord record)
        {
            record = null;
            if (source == null ||
                string.IsNullOrWhiteSpace(source.placementId) ||
                !Guid.TryParse(source.anchorId, out var anchorId))
            {
                return false;
            }

            var offset = source.localOffset;
            if (!IsFinite(offset.px) || !IsFinite(offset.py) || !IsFinite(offset.pz) ||
                !IsFinite(offset.qx) || !IsFinite(offset.qy) || !IsFinite(offset.qz) ||
                !IsFinite(offset.qw) || !IsFinite(source.normalizedValue))
            {
                return false;
            }

            var rotation = new Quaternion(offset.qx, offset.qy, offset.qz, offset.qw);
            if (Quaternion.Dot(rotation, rotation) < 0.0001f)
                rotation = Quaternion.identity;
            else
                rotation = Quaternion.Normalize(rotation);

            var surface = Enum.IsDefined(typeof(SurfaceKind), source.surfaceKind)
                ? source.surfaceKind
                : (int)SurfaceKind.Unknown;
            var lifecycle = Enum.IsDefined(typeof(PlacementLifecycle), source.lifecycle)
                ? source.lifecycle
                : (int)PlacementLifecycle.Active;

            record = source.Clone();
            record.placementId = source.placementId.Trim();
            record.anchorId = anchorId.ToString("D");
            record.roomId = Guid.TryParse(
                source.roomId,
                out var roomId)
                ? roomId.ToString("D")
                : string.Empty;
            record.instrumentTypeId = MockInstrumentCatalog.IsKnownTypeId(
                    source.instrumentTypeId)
                ? source.instrumentTypeId
                : MockInstrumentCatalog.GetTypeId(MockInstrumentKind.RoundMeter);
            record.surfaceKind = surface;
            record.localOffset = SerializablePose.FromPose(
                new Pose(new Vector3(offset.px, offset.py, offset.pz), rotation));
            record.normalizedValue = Mathf.Clamp01(source.normalizedValue);
            record.lifecycle = lifecycle;
            return true;
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static PlacementLoadResult Corrupt(string message)
        {
            return new PlacementLoadResult(
                PlacementLoadStatus.Corrupt,
                new PlacementDocument(),
                message);
        }
    }
}
