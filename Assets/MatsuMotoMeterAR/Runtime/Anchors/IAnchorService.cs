using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace MatsuMotoMeterAR.Anchors
{
    public interface IAnchorService
    {
        Task<AnchorRecord> CreateAsync(
            GameObject anchoredObject,
            SurfaceKind surface,
            CancellationToken cancellationToken = default);
        Task<IReadOnlyList<AnchorRecord>> LoadAsync(
            IReadOnlyList<string> ids,
            CancellationToken cancellationToken = default);
        bool Bind(AnchorRecord anchor, GameObject anchoredObject);
        Task<bool> RemoveAsync(
            AnchorRecord anchor,
            CancellationToken cancellationToken = default);
    }

    [Serializable]
    public sealed class AnchorRecord
    {
        public string Id;
        public AnchorPose Pose;
        internal object NativeHandle;
        internal GameObject BoundObject;
    }
}
