using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public static class InstrumentInteractionHitTest
    {
        public enum Reach
        {
            None,
            Direct,
            Ray
        }

        public static Reach Resolve(
            Collider interactionCollider,
            Vector3 controllerPosition,
            Vector3 controllerForward,
            float directTipOffset,
            float directRadius,
            float rayDistance)
        {
            if (interactionCollider == null ||
                !interactionCollider.enabled ||
                controllerForward.sqrMagnitude < 0.0001f)
            {
                return Reach.None;
            }

            var direction = controllerForward.normalized;
            var controllerTip =
                controllerPosition + direction * directTipOffset;
            var closestPoint = interactionCollider.ClosestPoint(controllerTip);
            if ((closestPoint - controllerTip).sqrMagnitude <=
                directRadius * directRadius)
            {
                return Reach.Direct;
            }

            return interactionCollider.Raycast(
                new Ray(controllerPosition, direction),
                out _,
                rayDistance)
                ? Reach.Ray
                : Reach.None;
        }
    }
}
