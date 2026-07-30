using System;
using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public sealed class ThemeVisualManifest : MonoBehaviour
    {
        [SerializeField] private Transform motionTarget;
        [SerializeField] private Renderer indicatorRenderer;
        [SerializeField] private Renderer[] stateRenderers =
            Array.Empty<Renderer>();

        public Transform MotionTarget => motionTarget;
        public Renderer IndicatorRenderer => indicatorRenderer;
        public Renderer[] StateRenderers => stateRenderers;

        public void Configure(
            Transform target,
            Renderer indicator = null,
            Renderer[] states = null)
        {
            motionTarget = target;
            indicatorRenderer = indicator;
            stateRenderers = states ?? Array.Empty<Renderer>();
        }
    }
}
