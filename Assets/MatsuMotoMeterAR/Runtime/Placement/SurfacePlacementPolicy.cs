using MatsuMotoMeterAR.Anchors;
using UnityEngine;

namespace MatsuMotoMeterAR.Placement
{
    public static class SurfacePlacementPolicy
    {
        public static bool IsCompatible(SurfaceKind required, Vector3 surfaceNormal)
        {
            var isPlacementSurface =
                required == SurfaceKind.Plane ||
                required == SurfaceKind.Volume ||
                required == SurfaceKind.Wall ||
                required == SurfaceKind.Floor ||
                required == SurfaceKind.Ceiling;
            return isPlacementSurface &&
                   surfaceNormal.sqrMagnitude > 0.5f;
        }
    }
}
