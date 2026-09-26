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

        public static Pose AlignNearestAxis(Pose candidate, Pose reference)
        {
            var delta = candidate.position - reference.position;
            var right = reference.rotation * Vector3.right;
            var up = reference.rotation * Vector3.up;
            var horizontalOffset = Vector3.Dot(delta, right);
            var verticalOffset = Vector3.Dot(delta, up);
            delta -= Mathf.Abs(horizontalOffset) <= Mathf.Abs(verticalOffset)
                ? right * horizontalOffset
                : up * verticalOffset;
            return new Pose(reference.position + delta, reference.rotation);
        }

        public static Pose SnapToGrid(Pose pose, float spacing)
        {
            if (spacing <= 0f)
                return pose;

            var right = pose.rotation * Vector3.right;
            var up = pose.rotation * Vector3.up;
            var x = Vector3.Dot(pose.position, right);
            var y = Vector3.Dot(pose.position, up);
            pose.position += right *
                             (Mathf.Round(x / spacing) * spacing - x);
            pose.position += up *
                             (Mathf.Round(y / spacing) * spacing - y);
            return pose;
        }
    }
}
