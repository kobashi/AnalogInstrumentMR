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

        [Test]
        public void AlignNearestAxis_AlignsTheSmallerOffsetAndRotation()
        {
            var candidate = new Pose(
                new Vector3(2.2f, 4f, 0.4f),
                Quaternion.identity);
            var reference = new Pose(
                new Vector3(2f, 3f, 0f),
                Quaternion.Euler(0f, 0f, 0f));

            var aligned = PlacementPoseUtility.AlignNearestAxis(
                candidate,
                reference);

            Assert.That(aligned.position.x, Is.EqualTo(2f).Within(0.0001f));
            Assert.That(aligned.position.y, Is.EqualTo(4f).Within(0.0001f));
            Assert.That(aligned.position.z, Is.EqualTo(0.4f).Within(0.0001f));
            Assert.That(aligned.rotation, Is.EqualTo(reference.rotation));
        }

        [Test]
        public void SnapToGrid_SnapsLocalPlaneWithoutChangingDepth()
        {
            var pose = new Pose(
                new Vector3(0.14f, 0.26f, 0.73f),
                Quaternion.identity);

            var snapped = PlacementPoseUtility.SnapToGrid(pose, 0.1f);

            Assert.That(snapped.position.x, Is.EqualTo(0.1f).Within(0.0001f));
            Assert.That(snapped.position.y, Is.EqualTo(0.3f).Within(0.0001f));
            Assert.That(snapped.position.z, Is.EqualTo(0.73f).Within(0.0001f));
            Assert.That(snapped.rotation, Is.EqualTo(pose.rotation));
        }

        [Test]
        public void AlignNearestAxis_UsesReferenceLocalAxes()
        {
            var reference = new Pose(
                new Vector3(1f, 1f, 0f),
                Quaternion.Euler(0f, 0f, 90f));
            var candidate = new Pose(
                new Vector3(2f, 1.1f, 0f),
                Quaternion.identity);

            var aligned = PlacementPoseUtility.AlignNearestAxis(
                candidate,
                reference);

            Assert.That(aligned.position.x, Is.EqualTo(2f).Within(0.0001f));
            Assert.That(aligned.position.y, Is.EqualTo(1f).Within(0.0001f));
            Assert.That(aligned.rotation, Is.EqualTo(reference.rotation));
        }
    }
}
