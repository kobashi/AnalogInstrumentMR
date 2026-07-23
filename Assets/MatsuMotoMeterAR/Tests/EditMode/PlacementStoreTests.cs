using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Anchors;
using MatsuMotoMeterAR.Instruments;
using MatsuMotoMeterAR.PlacementPersistence;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class PlacementStoreTests
    {
        [TestCase(0)]
        [TestCase(1)]
        [TestCase(24)]
        public void Json_RoundTripsSupportedPlacementCounts(int count)
        {
            var source = CreateDocument(count);

            var json = PlacementJsonCodec.Serialize(source);
            var result = PlacementJsonCodec.Deserialize(json);

            Assert.That(result.Status, Is.EqualTo(PlacementLoadStatus.Loaded));
            Assert.That(result.Document.schemaVersion, Is.EqualTo(1));
            Assert.That(result.Document.revision, Is.EqualTo(7));
            Assert.That(result.Document.placements, Has.Count.EqualTo(count));
            for (var index = 0; index < count; index++)
            {
                var record = result.Document.placements[index];
                Assert.That(record.placementId, Is.EqualTo($"placement-{index}"));
                Assert.That(record.anchorId, Is.EqualTo(AnchorId(index)));
                Assert.That(record.normalizedValue, Is.EqualTo(index / 24f).Within(0.0001f));
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
                "{\"schemaVersion\":2,\"revision\":9,\"placements\":[]}");
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

            Assert.That(normalized.placements, Has.Count.EqualTo(2));
            Assert.That(normalized.placements[0].normalizedValue, Is.Zero);
            Assert.That(normalized.placements[0].instrumentTypeId, Is.EqualTo("meter.round"));
            Assert.That(normalized.placements[0].surfaceKind, Is.EqualTo((int)SurfaceKind.Unknown));
        }

        [Test]
        public void Normalize_CapsActivePlacementsAtTwentyFour()
        {
            var normalized = PlacementJsonCodec.Normalize(CreateDocument(30));

            Assert.That(
                normalized.placements.FindAll(
                    record => record.lifecycle == (int)PlacementLifecycle.Active),
                Has.Count.EqualTo(24));
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
                    new PlacementDocument { schemaVersion = 2 })
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
                    instrumentTypeId = MockInstrumentCatalog.GetTypeId(
                        (MockInstrumentKind)(index % MockInstrumentCatalog.Count)),
                    surfaceKind = (int)(SurfaceKind)(index % 3),
                    localOffset = SerializablePose.FromPose(new Pose(
                        new Vector3(index, index * 2f, -index),
                        Quaternion.Euler(0f, index, 0f))),
                    normalizedValue = index / 24f
                });
            }
            return document;
        }

        private static string AnchorId(int index)
        {
            return new Guid(index + 1, 0, 0, new byte[8]).ToString("D");
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
