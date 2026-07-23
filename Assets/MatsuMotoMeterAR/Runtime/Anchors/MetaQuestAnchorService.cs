using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace MatsuMotoMeterAR.Anchors
{
    public sealed class MetaQuestAnchorService : IAnchorService
    {
        private const double LocalizationTimeoutSeconds = 10d;

        public async Task<AnchorRecord> CreateAsync(
            GameObject anchoredObject,
            SurfaceKind surface,
            CancellationToken cancellationToken = default)
        {
            if (anchoredObject == null)
                throw new ArgumentNullException(nameof(anchoredObject));
            cancellationToken.ThrowIfCancellationRequested();

            var spatialAnchor = anchoredObject.AddComponent<OVRSpatialAnchor>();
            if (!await spatialAnchor.WhenLocalizedAsync())
                throw new InvalidOperationException("Spatial anchor could not be localized.");
            cancellationToken.ThrowIfCancellationRequested();

            var saveResult = await spatialAnchor.SaveAnchorAsync();
            if (!saveResult.Success)
            {
                throw new InvalidOperationException(
                    $"Spatial anchor save failed: {saveResult.Status}");
            }

            return new AnchorRecord
            {
                Id = spatialAnchor.Uuid.ToString("D"),
                Pose = new AnchorPose(
                    anchoredObject.transform.position,
                    anchoredObject.transform.rotation,
                    surface),
                NativeHandle = spatialAnchor,
                BoundObject = anchoredObject
            };
        }

        public async Task<IReadOnlyList<AnchorRecord>> LoadAsync(
            IReadOnlyList<string> ids,
            CancellationToken cancellationToken = default)
        {
            if (ids == null)
                throw new ArgumentNullException(nameof(ids));

            var uuids = new List<Guid>(ids.Count);
            foreach (var id in ids)
            {
                if (Guid.TryParse(id, out var uuid))
                    uuids.Add(uuid);
            }
            if (uuids.Count == 0)
                return Array.Empty<AnchorRecord>();

            cancellationToken.ThrowIfCancellationRequested();
            var unboundAnchors = new List<OVRSpatialAnchor.UnboundAnchor>();
            var loadResult = await OVRSpatialAnchor.LoadUnboundAnchorsAsync(
                uuids,
                unboundAnchors);
            if (!loadResult.Success)
                return Array.Empty<AnchorRecord>();

            var records = new List<AnchorRecord>(unboundAnchors.Count);
            foreach (var unbound in unboundAnchors)
            {
                cancellationToken.ThrowIfCancellationRequested();
                if (!unbound.Localized &&
                    !await unbound.LocalizeAsync(LocalizationTimeoutSeconds))
                {
                    Debug.LogWarning($"Spatial anchor {unbound.Uuid:D} could not localize.");
                    continue;
                }
                if (!unbound.TryGetPose(out var pose))
                {
                    Debug.LogWarning($"Spatial anchor {unbound.Uuid:D} has no pose.");
                    continue;
                }

                records.Add(new AnchorRecord
                {
                    Id = unbound.Uuid.ToString("D"),
                    Pose = new AnchorPose(
                        pose.position,
                        pose.rotation,
                        SurfaceKind.Unknown),
                    NativeHandle = unbound
                });
            }
            return records;
        }

        public bool Bind(AnchorRecord anchor, GameObject anchoredObject)
        {
            if (anchor == null || anchoredObject == null)
                return false;

            anchoredObject.transform.SetPositionAndRotation(
                anchor.Pose.Position,
                anchor.Pose.Rotation);
            if (anchor.NativeHandle is OVRSpatialAnchor.UnboundAnchor unbound)
            {
                var spatialAnchor = anchoredObject.AddComponent<OVRSpatialAnchor>();
                unbound.BindTo(spatialAnchor);
                anchor.NativeHandle = spatialAnchor;
                anchor.BoundObject = anchoredObject;
                return true;
            }

            if (anchor.NativeHandle is OVRSpatialAnchor existing)
            {
                anchor.BoundObject = anchoredObject;
                return existing.gameObject == anchoredObject;
            }
            return false;
        }

        public async Task<bool> RemoveAsync(
            AnchorRecord anchor,
            CancellationToken cancellationToken = default)
        {
            if (anchor == null)
                return false;

            GameObject temporaryObject = null;
            OVRSpatialAnchor spatialAnchor;
            if (anchor.NativeHandle is OVRSpatialAnchor boundAnchor)
            {
                spatialAnchor = boundAnchor;
            }
            else if (anchor.NativeHandle is OVRSpatialAnchor.UnboundAnchor unbound)
            {
                temporaryObject = new GameObject("[App] Pending Anchor Erase");
                temporaryObject.transform.SetPositionAndRotation(
                    anchor.Pose.Position,
                    anchor.Pose.Rotation);
                spatialAnchor = temporaryObject.AddComponent<OVRSpatialAnchor>();
                unbound.BindTo(spatialAnchor);
            }
            else
            {
                return false;
            }

            try
            {
                cancellationToken.ThrowIfCancellationRequested();
                var eraseResult = await spatialAnchor.EraseAnchorAsync();
                return eraseResult.Success;
            }
            finally
            {
                if (temporaryObject != null)
                    UnityEngine.Object.Destroy(temporaryObject);
            }
        }
    }
}
