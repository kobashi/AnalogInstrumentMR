using System.Threading.Tasks;
using MatsuMotoMeterAR.Anchors;
using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class AnchorServiceTests
    {
        [Test]
        public async Task MockService_CreatesLoadsBindsAndRemovesByStableId()
        {
            var source = new GameObject("Source");
            var target = new GameObject("Target");
            try
            {
                source.transform.SetPositionAndRotation(
                    new Vector3(1f, 2f, 3f),
                    Quaternion.Euler(10f, 20f, 30f));
                var service = new MockAnchorService();

                var created = await service.CreateAsync(source, SurfaceKind.Wall);
                var loaded = await service.LoadAsync(new[] { created.Id, "missing" });

                Assert.That(System.Guid.TryParse(created.Id, out _), Is.True);
                Assert.That(loaded, Has.Count.EqualTo(1));
                Assert.That(loaded[0].Id, Is.EqualTo(created.Id));
                Assert.That(service.Bind(loaded[0], target), Is.True);
                Assert.That(target.transform.position, Is.EqualTo(source.transform.position));
                Assert.That(
                    Quaternion.Angle(target.transform.rotation, source.transform.rotation),
                    Is.LessThan(0.001f));
                Assert.That(await service.RemoveAsync(created), Is.True);
                Assert.That(await service.LoadAsync(new[] { created.Id }), Is.Empty);
            }
            finally
            {
                Object.DestroyImmediate(source);
                Object.DestroyImmediate(target);
            }
        }
    }
}
