using NUnit.Framework;
using UnityEngine;

namespace MatsuMotoMeterAR.Tests
{
    public sealed class RuntimeMaterialAssetsTests
    {
        [TestCase(
            "Materials/MAT_RuntimeBuiltInUnlit",
            "Unlit/Color",
            "_Color")]
        [TestCase(
            "Materials/MAT_RuntimeUrpUnlit",
            "Universal Render Pipeline/Unlit",
            "_BaseColor")]
        public void RuntimeMaterialMatchesPipelineContract(
            string resourcePath,
            string expectedShader,
            string requiredColorProperty)
        {
            var material = Resources.Load<Material>(resourcePath);

            Assert.That(material, Is.Not.Null);
            Assert.That(material.shader, Is.Not.Null);
            Assert.That(material.shader.name, Is.EqualTo(expectedShader));
            Assert.That(material.HasProperty(requiredColorProperty), Is.True);
        }
    }
}
