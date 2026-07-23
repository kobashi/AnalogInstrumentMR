using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace MatsuMotoMeterAR.Anchors
{
    public sealed class MockAnchorService : IAnchorService
    {
        private readonly Dictionary<string, AnchorRecord> records = new();
        public Task<AnchorRecord> CreateAsync(
            GameObject anchoredObject,
            SurfaceKind surface,
            CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var id = System.Guid.NewGuid().ToString("D");
            var record = new AnchorRecord
            {
                Id = id,
                Pose = new AnchorPose(
                    anchoredObject.transform.position,
                    anchoredObject.transform.rotation,
                    surface),
                BoundObject = anchoredObject
            };
            records.Add(id, record);
            return Task.FromResult(record);
        }

        public Task<IReadOnlyList<AnchorRecord>> LoadAsync(
            IReadOnlyList<string> ids,
            CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var snapshot = new List<AnchorRecord>();
            foreach (var id in ids)
            {
                if (records.TryGetValue(id, out var record))
                    snapshot.Add(record);
            }
            return Task.FromResult<IReadOnlyList<AnchorRecord>>(snapshot);
        }

        public bool Bind(AnchorRecord anchor, GameObject anchoredObject)
        {
            if (anchor == null || anchoredObject == null || !records.ContainsKey(anchor.Id))
                return false;

            anchoredObject.transform.SetPositionAndRotation(
                anchor.Pose.Position,
                anchor.Pose.Rotation);
            anchor.BoundObject = anchoredObject;
            return true;
        }

        public Task<bool> RemoveAsync(
            AnchorRecord anchor,
            CancellationToken cancellationToken = default)
        {
            cancellationToken.ThrowIfCancellationRequested();
            return Task.FromResult(anchor != null && records.Remove(anchor.Id));
        }
    }
}
