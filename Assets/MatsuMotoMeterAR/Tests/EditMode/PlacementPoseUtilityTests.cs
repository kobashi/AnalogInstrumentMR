using MatsuMotoMeterAR.Placement;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class PlacementPoseUtilityTests
    {
        [TestCase(0f, 1f, 0f)]
        [TestCase(0f, -1f, 0f)]
        [TestCase(1f, 0f, 0f)]
        public void AlignsLocalForwardWithSurfaceNormal(float x, float y, float z)
        {
            var normal = new Vector3(x, y, z);
            var pose = PlacementPoseUtility.FromSurface(Vector3.one, normal, Vector3.forward);

            Assert.That(Vector3.Dot(pose.rotation * Vector3.forward, normal.normalized), Is.GreaterThan(0.999f));
            Assert.That(pose.position, Is.EqualTo(Vector3.one));
        }
    }
}
