using System.Collections.Generic;
using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public static class InstrumentInteractionResolver
    {
        public static bool TryResolveBest(
            IReadOnlyList<MockInstrumentInteraction> interactions,
            Vector3 controllerPosition,
            Vector3 controllerForward,
            float directTipOffset,
            float directRadius,
            float rayDistance,
            out MockInstrumentInteraction interaction,
            out InstrumentInteractionHitTest.Reach reach)
        {
            interaction = null;
            reach = InstrumentInteractionHitTest.Reach.None;
            if (interactions == null || controllerForward.sqrMagnitude < 0.0001f)
                return false;

            var direction = controllerForward.normalized;
            var tip = controllerPosition + direction * directTipOffset;
            var bestDirectDistance = float.PositiveInfinity;
            for (var index = 0; index < interactions.Count; index++)
            {
                var candidate = interactions[index];
                var collider = candidate != null ? candidate.InteractionCollider : null;
                if (collider == null || !collider.enabled || !collider.gameObject.activeInHierarchy)
                    continue;

                var distance = (collider.ClosestPoint(tip) - tip).sqrMagnitude;
                if (distance <= directRadius * directRadius && distance < bestDirectDistance)
                {
                    bestDirectDistance = distance;
                    interaction = candidate;
                    reach = InstrumentInteractionHitTest.Reach.Direct;
                }
            }
            if (interaction != null)
                return true;

            var ray = new Ray(controllerPosition, direction);
            var bestRayDistance = float.PositiveInfinity;
            for (var index = 0; index < interactions.Count; index++)
            {
                var candidate = interactions[index];
                var collider = candidate != null ? candidate.InteractionCollider : null;
                if (collider == null || !collider.enabled || !collider.gameObject.activeInHierarchy)
                    continue;
                if (collider.Raycast(ray, out var hit, rayDistance) &&
                    hit.distance < bestRayDistance)
                {
                    bestRayDistance = hit.distance;
                    interaction = candidate;
                    reach = InstrumentInteractionHitTest.Reach.Ray;
                }
            }
            return interaction != null;
        }
    }
}
