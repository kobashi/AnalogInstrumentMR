using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public sealed class ThemeVisualManifest : MonoBehaviour
    {
        [SerializeField] private Transform motionTarget;
        [SerializeField] private Renderer indicatorRenderer;

        public Transform MotionTarget => motionTarget;
        public Renderer IndicatorRenderer => indicatorRenderer;

        public void Configure(Transform target, Renderer indicator = null)
        {
            motionTarget = target;
            indicatorRenderer = indicator;
        }
    }
}
