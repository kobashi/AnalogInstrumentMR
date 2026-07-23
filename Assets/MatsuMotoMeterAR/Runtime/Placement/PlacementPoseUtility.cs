using UnityEngine;

namespace MatsuMotoMeterAR.Placement
{
    public static class PlacementPoseUtility
    {
        public static Pose FromSurface(Vector3 position, Vector3 surfaceNormal, Vector3 viewerForward)
        {
            var normal = surfaceNormal.sqrMagnitude > 0.0001f
                ? surfaceNormal.normalized
                : Vector3.forward;
            var up = Vector3.ProjectOnPlane(Vector3.up, normal);

            if (up.sqrMagnitude < 0.0001f)
                up = Vector3.ProjectOnPlane(viewerForward, normal);
            if (up.sqrMagnitude < 0.0001f)
                up = Vector3.ProjectOnPlane(Vector3.forward, normal);
            if (up.sqrMagnitude < 0.0001f)
                up = Vector3.right;

            return new Pose(position, Quaternion.LookRotation(normal, up.normalized));
        }
    }
}
