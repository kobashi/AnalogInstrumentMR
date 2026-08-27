using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Anchors;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;
using MatsuMotoMeterAR.Signals;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class PlacementStoreTests
    {
        [TestCase(0)]
        [TestCase(1)]
        [TestCase(24)]
        [TestCase(48)]
        public void Json_RoundTripsSupportedPlacementCounts(int count)
        {
            var source = CreateDocument(count);

            var json = PlacementJsonCodec.Serialize(source);
            var result = PlacementJsonCodec.Deserialize(json);

            Assert.That(result.Status, Is.EqualTo(PlacementLoadStatus.Loaded));
            Assert.That(
                result.Document.schemaVersion,
                Is.EqualTo(PlacementDocument.CurrentSchemaVersion));
            Assert.That(result.Document.revision, Is.EqualTo(7));
            Assert.That(result.Document.placements, Has.Count.EqualTo(count));
            for (var index = 0; index < count; index++)
            {
                var record = result.Document.placements[index];
                Assert.That(record.placementId, Is.EqualTo($"placement-{index}"));
                Assert.That(record.anchorId, Is.EqualTo(AnchorId(index)));
                Assert.That(record.roomId, Is.EqualTo(RoomId(index % 2)));
                var expectedValue = count > 0 ? index / (float)count : 0f;
                Assert.That(
                    record.normalizedValue,
                    Is.EqualTo(expectedValue).Within(0.0001f));
            }
        }

        [Test]
        public void Json_RejectsCorruptAndProtectsFutureSchema()
        {
            Assert.That(
                PlacementJsonCodec.Deserialize("not json").Status,
                Is.EqualTo(PlacementLoadStatus.Corrupt));
            Assert.That(
                PlacementJsonCodec.Deserialize("{}").Status,
                Is.EqualTo(PlacementLoadStatus.Corrupt));

            var future = PlacementJsonCodec.Deserialize(
                "{\"schemaVersion\":6,\"revision\":9,\"placements\":[]}");
            Assert.That(future.Status, Is.EqualTo(PlacementLoadStatus.UnsupportedVersion));
            Assert.That(future.CanWrite, Is.False);
            Assert.That(future.Document.revision, Is.EqualTo(9));
        }

        [Test]
        public void Normalize_FiltersDuplicatesAndInvalidIdsAndClampsState()
        {
            var document = CreateDocument(2);
            document.placements[0].normalizedValue = -4f;
            document.placements[0].instrumentTypeId = "unknown";
            document.placements[0].surfaceKind = 99;
            document.placements[0].roomId = "not-a-room-guid";
            document.placements.Add(new PlacementRecord
            {
                placementId = "placement-0",
                anchorId = AnchorId(3),
                instrumentTypeId = "control.lever",
                localOffset = SerializablePose.Identity
            });
            document.placements.Add(new PlacementRecord
            {
                placementId = "duplicate-anchor",
                anchorId = AnchorId(1),
                instrumentTypeId = "control.toggle",
                localOffset = SerializablePose.Identity
            });
            document.placements.Add(new PlacementRecord
            {
                placementId = "bad-anchor",
                anchorId = "not-a-guid",
                instrumentTypeId = "control.rotary",
                localOffset = SerializablePose.Identity
            });

            var normalized = PlacementJsonCodec.Normalize(document);

            Assert.That(normalized.placements, Has.Count.EqualTo(3));
            Assert.That(normalized.placements[0].normalizedValue, Is.Zero);
            Assert.That(normalized.placements[0].instrumentTypeId, Is.EqualTo("meter.round"));
            Assert.That(normalized.placements[0].surfaceKind, Is.EqualTo((int)SurfaceKind.Unknown));
            Assert.That(
                normalized.placements[2].anchorId,
                Is.EqualTo(normalized.placements[1].anchorId));
            Assert.That(normalized.placements[0].roomId, Is.Empty);
        }

        [Test]
        public void Normalize_CapsPlacementsAtFortyEightPerRoom()
        {
            var document = CreateDocument(60);
            foreach (var record in document.placements)
                record.roomId = RoomId(0);

            var normalized = PlacementJsonCodec.Normalize(document);

            Assert.That(
                normalized.placements.FindAll(
                    record => record.lifecycle == (int)PlacementLifecycle.Active),
                Has.Count.EqualTo(48));
        }

        [Test]
        public void Normalize_AllowsFortyEightPlacementsInEachRoom()
        {
            var document = CreateDocument(96);
            for (var index = 0; index < document.placements.Count; index++)
                document.placements[index].roomId = RoomId(index / 48);

            var normalized = PlacementJsonCodec.Normalize(document);

            Assert.That(normalized.placements, Has.Count.EqualTo(96));
        }

        [Test]
        public void Normalize_CapsAllRoomStorageAtOneHundredNinetyTwo()
        {
            var document = CreateDocument(240);
            for (var index = 0; index < document.placements.Count; index++)
                document.placements[index].roomId = RoomId(index / 48);

            var normalized = PlacementJsonCodec.Normalize(document);

            Assert.That(
                normalized.placements,
                Has.Count.EqualTo(
                    PlacementDocument.MaximumStoredPlacements));
        }

        [Test]
        public void Normalize_PreservesConnectionsForTemporarilyUnavailableRoomAnchors()
        {
            var document = CreateDocument(2);
            document.placements[0].instrumentTypeId = "control.lever";
            document.placements[1].instrumentTypeId = "indicator.status";
            document.placements[1].lifecycle =
                (int)PlacementLifecycle.Unavailable;
            document.connections.Add(new SignalConnectionRecord
            {
                connectionId = "cross-room",
                sourcePlacementId = document.placements[0].placementId,
                targetPlacementId = document.placements[1].placementId
            });

            var normalized = PlacementJsonCodec.Normalize(document);

            Assert.That(normalized.connections, Has.Count.EqualTo(1));
            Assert.That(
                normalized.connections[0].connectionId,
                Is.EqualTo("cross-room"));
        }

        [Test]
        public void Normalize_AllowsMeterObservationOnlyForTrendMonitor()
        {
            var document = CreateDocument(3);
            document.placements[0].instrumentTypeId = "meter.round";
            document.placements[1].instrumentTypeId = "meter.window";
            document.placements[2].instrumentTypeId = "monitor.trend";
            document.connections.Add(Connection(
                "meter-to-meter",
                document.placements[0].placementId,
                document.placements[1].placementId));
            document.connections.Add(Connection(
                "meter-to-monitor",
                document.placements[0].placementId,
                document.placements[2].placementId));

            var normalized = PlacementJsonCodec.Normalize(document);

            Assert.That(normalized.connections, Has.Count.EqualTo(1));
            Assert.That(
                normalized.connections[0].connectionId,
                Is.EqualTo("meter-to-monitor"));
        }

        [Test]
        public void Normalize_CapsTrendMonitorAtFourInputs()
        {
            var document = CreateDocument(6);
            for (var index = 0; index < 5; index++)
                document.placements[index].instrumentTypeId = "meter.round";
            document.placements[5].instrumentTypeId = "monitor.trend";
            for (var index = 0; index < 5; index++)
            {
                document.connections.Add(Connection(
                    $"monitor-input-{index}",
                    document.placements[index].placementId,
                    document.placements[5].placementId));
            }

            var normalized = PlacementJsonCodec.Normalize(document);

            Assert.That(
                normalized.connections,
                Has.Count.EqualTo(
                    InstrumentSignalPolicy.MaximumTrendMonitorInputs));
            Assert.That(
                normalized.connections[
                    normalized.connections.Count - 1].connectionId,
                Is.EqualTo("monitor-input-3"));
        }

        [Test]
        public void Json_MigratesLegacySchemasToV5WithConnectionDefaults()
        {
            foreach (var schemaVersion in new[] { 1, 2, 3, 4 })
            {
                var document = CreateDocument(2);
                document.schemaVersion = schemaVersion;
                document.placements[0].instrumentTypeId = "control.lever";
                document.placements[1].instrumentTypeId = "indicator.status";
                var legacyConnection = Connection(
                    "legacy-connection",
                    document.placements[0].placementId,
                    document.placements[1].placementId);
                legacyConnection.inputMinimum = 0.15f;
                legacyConnection.inputMaximum = 0.85f;
                legacyConnection.outputMinimum = 0.3f;
                legacyConnection.outputMaximum = 0.7f;
                legacyConnection.thresholdValue = 0.75f;
                legacyConnection.thresholdComparison =
                    (int)SignalThresholdComparison.Below;
                document.connections.Add(legacyConnection);
                var result = PlacementJsonCodec.Deserialize(
                    JsonUtility.ToJson(document));

                Assert.That(
                    result.Status,
                    Is.EqualTo(PlacementLoadStatus.Loaded));
                Assert.That(result.RequiresSave, Is.True);
                Assert.That(
                    result.Document.schemaVersion,
                    Is.EqualTo(PlacementDocument.CurrentSchemaVersion));
                var connection = result.Document.connections[0];
                Assert.That(connection.inputMinimum, Is.Zero);
                Assert.That(connection.inputMaximum, Is.EqualTo(1f));
                Assert.That(connection.outputMinimum, Is.EqualTo(0.2f));
                Assert.That(connection.outputMaximum, Is.EqualTo(0.8f));
                Assert.That(connection.thresholdValue, Is.EqualTo(0.5f));
                Assert.That(
                    connection.thresholdComparison,
                    Is.EqualTo((int)SignalThresholdComparison.Above));
            }
        }

        [Test]
        public void Json_RoundTripsConnectionParametersAndClonePreservesThem()
        {
            var document = CreateDocument(2);
            document.placements[0].instrumentTypeId = "control.lever";
            document.placements[1].instrumentTypeId = "indicator.status";
            var source = Connection(
                "configured",
                document.placements[0].placementId,
                document.placements[1].placementId);
            source.transformKind = (int)SignalTransformKind.Threshold;
            source.inputMinimum = 0.1f;
            source.inputMaximum = 0.9f;
            source.outputMinimum = 0.25f;
            source.outputMaximum = 0.75f;
            source.thresholdValue = 0.65f;
            source.thresholdComparison = (int)SignalThresholdComparison.Below;
            document.connections.Add(source);

            var result = PlacementJsonCodec.Deserialize(
                PlacementJsonCodec.Serialize(document));
            var connection = result.Document.connections[0];
            var clone = connection.Clone();

            Assert.That(connection.inputMinimum, Is.EqualTo(0.1f));
            Assert.That(connection.inputMaximum, Is.EqualTo(0.9f));
            Assert.That(connection.outputMinimum, Is.EqualTo(0.25f));
            Assert.That(connection.outputMaximum, Is.EqualTo(0.75f));
            Assert.That(connection.thresholdValue, Is.EqualTo(0.65f));
            Assert.That(
                connection.thresholdComparison,
                Is.EqualTo((int)SignalThresholdComparison.Below));
            Assert.That(clone.inputMinimum, Is.EqualTo(connection.inputMinimum));
            Assert.That(clone.inputMaximum, Is.EqualTo(connection.inputMaximum));
            Assert.That(clone.outputMinimum, Is.EqualTo(connection.outputMinimum));
            Assert.That(clone.outputMaximum, Is.EqualTo(connection.outputMaximum));
            Assert.That(clone.thresholdValue, Is.EqualTo(connection.thresholdValue));
            Assert.That(clone.thresholdComparison, Is.EqualTo(connection.thresholdComparison));
        }

        [Test]
        public void Normalize_ClampsOrdersAndRepairsConnectionParameters()
        {
            var document = CreateDocument(2);
            document.placements[0].instrumentTypeId = "control.lever";
            document.placements[1].instrumentTypeId = "indicator.status";
            var connection = Connection(
                "invalid-parameters",
                document.placements[0].placementId,
                document.placements[1].placementId);
            connection.inputMinimum = 2f;
            connection.inputMaximum = -1f;
            connection.outputMinimum = float.NaN;
            connection.outputMaximum = float.PositiveInfinity;
            connection.thresholdValue = -4f;
            connection.thresholdComparison = 99;
            document.connections.Add(connection);

            var normalized = PlacementJsonCodec.Normalize(document).connections[0];

            Assert.That(normalized.inputMinimum, Is.Zero);
            Assert.That(normalized.inputMaximum, Is.EqualTo(1f));
            Assert.That(normalized.outputMinimum, Is.EqualTo(0.2f));
            Assert.That(normalized.outputMaximum, Is.EqualTo(0.8f));
            Assert.That(normalized.thresholdValue, Is.Zero);
            Assert.That(
                normalized.thresholdComparison,
                Is.EqualTo((int)SignalThresholdComparison.Above));
        }

        [Test]
        public void ConnectionTransform_UsesConfiguredRangeAndThresholdDirection()
        {
            var connection = new SignalConnectionRecord
            {
                transformKind = (int)SignalTransformKind.Range,
                inputMinimum = 0.25f,
                inputMaximum = 0.75f,
                outputMinimum = 0.1f,
                outputMaximum = 0.9f
            };

            Assert.That(
                InstrumentSignalPolicy.Transform(0.5f, connection),
                Is.EqualTo(0.5f).Within(0.0001f));
            Assert.That(
                InstrumentSignalPolicy.Transform(0f, connection),
                Is.EqualTo(0.1f).Within(0.0001f));
            Assert.That(
                InstrumentSignalPolicy.Transform(1f, connection),
                Is.EqualTo(0.9f).Within(0.0001f));

            connection.transformKind = (int)SignalTransformKind.Threshold;
            connection.thresholdValue = 0.4f;
            connection.thresholdComparison = (int)SignalThresholdComparison.Above;
            Assert.That(InstrumentSignalPolicy.Transform(0.6f, connection), Is.EqualTo(1f));
            Assert.That(InstrumentSignalPolicy.Transform(0.2f, connection), Is.Zero);
            connection.thresholdComparison = (int)SignalThresholdComparison.Below;
            Assert.That(InstrumentSignalPolicy.Transform(0.2f, connection), Is.EqualTo(1f));
            Assert.That(InstrumentSignalPolicy.Transform(0.6f, connection), Is.Zero);
        }

        [Test]
        public void ConnectionSelection_CyclesIncomingAndOutgoingConnections()
        {
            var outgoingFirst = Connection("first", "selected", "target-a");
            var incoming = Connection("second", "source-b", "selected");
            var unrelated = Connection("other", "source-c", "target-c");
            var outgoingLast = Connection("third", "selected", "target-d");
            var connections = new List<SignalConnectionRecord>
            {
                outgoingFirst,
                incoming,
                unrelated,
                outgoingLast
            };

            var selected = SignalConnectionSelectionPolicy.SelectNext(
                connections,
                "selected",
                null);
            Assert.That(selected, Is.SameAs(outgoingFirst));

            selected = SignalConnectionSelectionPolicy.SelectNext(
                connections,
                "selected",
                selected.connectionId);
            Assert.That(selected, Is.SameAs(incoming));

            selected = SignalConnectionSelectionPolicy.SelectNext(
                connections,
                "selected",
                selected.connectionId);
            Assert.That(selected, Is.SameAs(outgoingLast));

            selected = SignalConnectionSelectionPolicy.SelectNext(
                connections,
                "selected",
                selected.connectionId);
            Assert.That(selected, Is.SameAs(outgoingFirst));
        }

        [Test]
        public void ConnectionSelection_CountsOnlySelectedObjectConnections()
        {
            var connections = new List<SignalConnectionRecord>
            {
                Connection("first", "selected", "target-a"),
                Connection("second", "source-b", "selected"),
                Connection("other", "source-c", "target-c")
            };

            Assert.That(
                SignalConnectionSelectionPolicy.CountForPlacement(
                    connections,
                    "selected"),
                Is.EqualTo(2));
            Assert.That(
                SignalConnectionSelectionPolicy.CountForPlacement(
                    connections,
                    "missing"),
                Is.Zero);
        }

        [Test]
        public void ConnectionTransform_CyclesInBothDirectionsAndWraps()
        {
            Assert.That(
                InstrumentSignalPolicy.Cycle(
                    SignalTransformKind.Direct,
                    1),
                Is.EqualTo(SignalTransformKind.Invert));
            Assert.That(
                InstrumentSignalPolicy.Cycle(
                    SignalTransformKind.Invert,
                    1),
                Is.EqualTo(SignalTransformKind.Range));
            Assert.That(
                InstrumentSignalPolicy.Cycle(
                    SignalTransformKind.Range,
                    1),
                Is.EqualTo(SignalTransformKind.Threshold));
            Assert.That(
                InstrumentSignalPolicy.Cycle(
                    SignalTransformKind.Threshold,
                    1),
                Is.EqualTo(SignalTransformKind.Direct));
            Assert.That(
                InstrumentSignalPolicy.Cycle(
                    SignalTransformKind.Direct,
                    -1),
                Is.EqualTo(SignalTransformKind.Threshold));
        }

        [Test]
        public void LegacyMigration_PreservesAnchorAndIsIdempotent()
        {
            var store = new MemoryPlacementStore();
            var legacy = new FixedLegacySource(new LegacyPlacementData(
                AnchorId(9),
                "control.toggle",
                0.8f));

            var first = LegacyPlacementMigration.LoadOrMigrate(store, legacy);
            var second = LegacyPlacementMigration.LoadOrMigrate(store, legacy);

            Assert.That(first.Status, Is.EqualTo(PlacementLoadStatus.Loaded));
            Assert.That(second.Status, Is.EqualTo(PlacementLoadStatus.Loaded));
            Assert.That(store.SaveCount, Is.EqualTo(1));
            Assert.That(legacy.IsMigrationCompleted, Is.True);
            Assert.That(second.Document.placements, Has.Count.EqualTo(1));
            var record = second.Document.placements[0];
            Assert.That(record.placementId, Is.EqualTo($"legacy-{AnchorId(9)}"));
            Assert.That(record.anchorId, Is.EqualTo(AnchorId(9)));
            Assert.That(record.instrumentTypeId, Is.EqualTo("control.toggle"));
            Assert.That(record.normalizedValue, Is.EqualTo(0.8f).Within(0.0001f));
        }

        [Test]
        public void LegacyMigration_DoesNotOverwriteFutureSchema()
        {
            var store = new MemoryPlacementStore
            {
                Result = new PlacementLoadResult(
                    PlacementLoadStatus.UnsupportedVersion,
                    new PlacementDocument { schemaVersion = 6 })
            };

            var result = LegacyPlacementMigration.LoadOrMigrate(
                store,
                new FixedLegacySource(new LegacyPlacementData(
                    AnchorId(4),
                    "meter.round",
                    0.5f)));

            Assert.That(result.Status, Is.EqualTo(PlacementLoadStatus.UnsupportedVersion));
            Assert.That(store.SaveCount, Is.Zero);
        }

        [Test]
        public void LegacyMigration_DoesNotReplaceCorruptV1AfterCompletedMigration()
        {
            var store = new MemoryPlacementStore
            {
                Result = new PlacementLoadResult(
                    PlacementLoadStatus.Corrupt,
                    new PlacementDocument(),
                    "damaged")
            };
            var legacy = new FixedLegacySource(
                new LegacyPlacementData(AnchorId(4), "meter.round", 0.5f),
                migrationCompleted: true);

            var result = LegacyPlacementMigration.LoadOrMigrate(store, legacy);

            Assert.That(result.Status, Is.EqualTo(PlacementLoadStatus.Corrupt));
            Assert.That(store.SaveCount, Is.Zero);
            Assert.That(legacy.ReadCount, Is.Zero);
        }

        [Test]
        public void LegacyMigration_ReportsSaveFailureWithoutMutatingSource()
        {
            var store = new MemoryPlacementStore { FailSave = true };
            var legacy = new FixedLegacySource(new LegacyPlacementData(
                AnchorId(5),
                "control.button",
                1f));

            var result = LegacyPlacementMigration.LoadOrMigrate(store, legacy);

            Assert.That(result.Status, Is.EqualTo(PlacementLoadStatus.SaveFailed));
            Assert.That(legacy.ReadCount, Is.EqualTo(1));
        }

        private static PlacementDocument CreateDocument(int count)
        {
            var document = new PlacementDocument { revision = 7 };
            for (var index = 0; index < count; index++)
            {
                document.placements.Add(new PlacementRecord
                {
                    placementId = $"placement-{index}",
                    anchorId = AnchorId(index),
                    roomId = RoomId(index % 2),
                    instrumentTypeId = MockInstrumentCatalog.GetTypeId(
                        (MockInstrumentKind)(index % MockInstrumentCatalog.Count)),
                    surfaceKind = (int)(SurfaceKind)(index % 3),
                    localOffset = SerializablePose.FromPose(new Pose(
                        new Vector3(index, index * 2f, -index),
                        Quaternion.Euler(0f, index, 0f))),
                    normalizedValue = count > 0 ? index / (float)count : 0f
                });
            }
            return document;
        }

        private static string AnchorId(int index)
        {
            return new Guid(index + 1, 0, 0, new byte[8]).ToString("D");
        }

        private static string RoomId(int index)
        {
            return new Guid(1000 + index, 0, 0, new byte[8]).ToString("D");
        }

        private static SignalConnectionRecord Connection(
            string id,
            string sourceId,
            string targetId)
        {
            return new SignalConnectionRecord
            {
                connectionId = id,
                sourcePlacementId = sourceId,
                targetPlacementId = targetId
            };
        }

        private sealed class FixedLegacySource : ILegacyPlacementSource
        {
            private readonly LegacyPlacementData data;

            public FixedLegacySource(
                LegacyPlacementData data,
                bool migrationCompleted = false)
            {
                this.data = data;
                IsMigrationCompleted = migrationCompleted;
            }

            public int ReadCount { get; private set; }
            public bool IsMigrationCompleted { get; private set; }

            public bool TryRead(out LegacyPlacementData value)
            {
                ReadCount++;
                value = data;
                return true;
            }

            public void MarkMigrationCompleted()
            {
                IsMigrationCompleted = true;
            }
        }

        private sealed class MemoryPlacementStore : IPlacementStore
        {
            public PlacementLoadResult Result = new(
                PlacementLoadStatus.Missing,
                new PlacementDocument());
            public bool FailSave;
            public int SaveCount;

            public PlacementLoadResult Load()
            {
                return Result;
            }

            public bool Save(PlacementDocument document)
            {
                SaveCount++;
                if (FailSave)
                    return false;

                Result = PlacementJsonCodec.Deserialize(
                    PlacementJsonCodec.Serialize(document));
                return true;
            }
        }
    }
}
