using UnityEngine;

namespace MatsuMotoMeterAR.PerformanceGate
{
    public static class PerformanceGateLayout
    {
        public const int Columns = 6;

        public static Pose GetPose(
            int index,
            int count,
            Vector3 origin,
            Vector3 right,
            Vector3 up,
            Vector3 normal)
        {
            var rows = Mathf.CeilToInt(count / (float)Columns);
            var column = index % Columns;
            var row = index / Columns;
            const float horizontalSpacing = 0.22f;
            const float verticalSpacing = 0.19f;
            var horizontal = (column - (Columns - 1) * 0.5f) * horizontalSpacing;
            var vertical = ((rows - 1) * 0.5f - row) * verticalSpacing;
            var position = origin + right * horizontal + up * vertical;
            return new Pose(position, Quaternion.LookRotation(normal, up));
        }
    }
}
