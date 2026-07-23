using MatsuMotoMeterAR.Anchors;
using MatsuMotoMeterAR.Placement;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class SurfacePlacementPolicyTests
    {
        [TestCase(SurfaceKind.Floor, 0f, 1f, 0f)]
        [TestCase(SurfaceKind.Ceiling, 0f, -1f, 0f)]
        [TestCase(SurfaceKind.Wall, 1f, 0f, 0f)]
        public void AcceptsMatchingSurface(SurfaceKind kind, float x, float y, float z)
        {
            Assert.That(SurfacePlacementPolicy.IsCompatible(kind, new Vector3(x, y, z)), Is.True);
        }
    }
}

