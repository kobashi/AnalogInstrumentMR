using System.Collections.Generic;
using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    public static class InstrumentAudioVoiceBudget
    {
        public const int MaximumContinuousVoices = 8;
        public const float RefreshIntervalSeconds = 0.25f;

        private static readonly List<InstrumentAudioController> Controllers =
            new();
        private static AudioListener listener;
        private static float nextRefreshTime;

        public static void Register(InstrumentAudioController controller)
        {
            if (controller != null && !Controllers.Contains(controller))
                Controllers.Add(controller);
        }

        public static void Unregister(InstrumentAudioController controller)
        {
            Controllers.Remove(controller);
        }

        public static void RefreshIfDue()
        {
            if (Time.unscaledTime < nextRefreshTime)
                return;
            nextRefreshTime =
                Time.unscaledTime + RefreshIntervalSeconds;
            if (listener == null)
            {
                listener = Object.FindFirstObjectByType<AudioListener>(
                    FindObjectsInactive.Exclude);
            }
            if (listener == null)
            {
                SetAllUnselected();
                return;
            }
            RefreshAt(listener.transform.position);
        }

        public static void RefreshAt(Vector3 listenerPosition)
        {
            RemoveMissingControllers();
            SetAllUnselected();
            var selectedCount = Mathf.Min(
                MaximumContinuousVoices,
                Controllers.Count);
            for (var rank = 0; rank < selectedCount; rank++)
            {
                InstrumentAudioController nearest = null;
                var nearestDistance = float.PositiveInfinity;
                foreach (var controller in Controllers)
                {
                    if (controller == null ||
                        controller.ContinuousSelected ||
                        !controller.isActiveAndEnabled ||
                        controller.ContinuousSource == null)
                    {
                        continue;
                    }

                    var distance = (
                        controller.transform.position - listenerPosition)
                        .sqrMagnitude;
                    if (distance >= nearestDistance)
                        continue;
                    nearest = controller;
                    nearestDistance = distance;
                }

                if (nearest == null)
                    break;
                nearest.SetContinuousSelected(true);
            }
        }

        private static void SetAllUnselected()
        {
            RemoveMissingControllers();
            foreach (var controller in Controllers)
            {
                if (controller != null)
                    controller.SetContinuousSelected(false);
            }
        }

        private static void RemoveMissingControllers()
        {
            for (var index = Controllers.Count - 1; index >= 0; index--)
            {
                if (Controllers[index] == null)
                    Controllers.RemoveAt(index);
            }
        }
    }
}
