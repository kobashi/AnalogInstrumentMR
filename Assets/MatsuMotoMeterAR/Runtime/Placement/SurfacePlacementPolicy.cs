using MatsuMotoMeterAR.Anchors;
using UnityEngine;

namespace MatsuMotoMeterAR.Placement
{
    public static class SurfacePlacementPolicy
    {
        public static bool IsCompatible(SurfaceKind required, Vector3 surfaceNormal)
        {
            var normal = surfaceNormal.normalized;
            return required switch
            {
                SurfaceKind.Floor => Vector3.Dot(normal, Vector3.up) > 0.7f,
                SurfaceKind.Ceiling => Vector3.Dot(normal, Vector3.down) > 0.7f,
                SurfaceKind.Wall => Mathf.Abs(Vector3.Dot(normal, Vector3.up)) < 0.3f,
                _ => false
            };
        }
    }
}

