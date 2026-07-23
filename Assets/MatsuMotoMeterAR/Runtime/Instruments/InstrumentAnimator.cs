using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public sealed class InstrumentAnimator : MonoBehaviour
    {
        [SerializeField] private Transform movingPart;
        [SerializeField, Min(0f)] private float degreesPerSecond = 45f;
        [SerializeField] private Vector3 localAxis = Vector3.forward;

        private void Reset() => movingPart = transform;

        public void Configure(Transform part, Vector3 axis, float speed)
        {
            movingPart = part;
            localAxis = axis;
            degreesPerSecond = Mathf.Max(0f, speed);
        }

        private void Update()
        {
            if (movingPart == null)
                return;

            movingPart.Rotate(localAxis, degreesPerSecond * Time.deltaTime, Space.Self);
        }
    }
}
