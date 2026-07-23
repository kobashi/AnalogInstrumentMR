using UnityEngine;

namespace MatsuMotoMeterAR.Anchors
{
    public readonly struct AnchorPose
    {
        public AnchorPose(Vector3 position, Quaternion rotation, SurfaceKind surface)
        {
            Position = position;
            Rotation = rotation;
            Surface = surface;
        }

        public Vector3 Position { get; }
        public Quaternion Rotation { get; }
        public SurfaceKind Surface { get; }
    }
}

