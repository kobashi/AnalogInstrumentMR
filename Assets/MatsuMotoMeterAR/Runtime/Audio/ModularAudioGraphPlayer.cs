using UnityEngine;

namespace MatsuMotoMeterAR.Audio
{
    [DisallowMultipleComponent]
    public sealed class ModularAudioGraphPlayer : MonoBehaviour
    {
        private readonly float[] monoScratch =
            new float[ModularAudioGraph.MaximumBlockFrames];
        private ModularAudioGraph graph;
        private AudioSource source;
        private AudioClip clip;
        private int sampleRate = 48000;

        public ModularAudioGraph Graph => graph;
        public AudioSource Source => source;

        public void Configure(ModularAudioGraph audioGraph)
        {
            graph = audioGraph;
            if (source == null)
                source = gameObject.AddComponent<AudioSource>();
            source.playOnAwake = false;
            source.loop = true;
            source.spatialBlend = 1f;
            source.dopplerLevel = 0f;
            source.rolloffMode = AudioRolloffMode.Logarithmic;
            source.minDistance = InstrumentAudioController.MinimumDistance;
            source.maxDistance = InstrumentAudioController.MaximumDistance;
            source.priority = 128;
            source.volume = 1f;
        }

        public bool RenderForValidation(
            float[] output,
            int frameCount,
            int outputSampleRate = 48000)
        {
            return graph != null &&
                   graph.Render(output, frameCount, outputSampleRate);
        }

        private void Start()
        {
            if (graph == null || source == null || !graph.IsCompiled)
                return;
            sampleRate = Mathf.Max(8000, AudioSettings.outputSampleRate);
            clip = AudioClip.Create(
                "Generated_ModularAudioOutput",
                sampleRate,
                1,
                sampleRate,
                true,
                OnAudioRead);
            source.clip = clip;
            source.Play();
        }

        private void OnAudioRead(float[] data)
        {
            if (data == null)
                return;
            var offset = 0;
            while (offset < data.Length)
            {
                var count = Mathf.Min(
                    ModularAudioGraph.MaximumBlockFrames,
                    data.Length - offset);
                if (graph == null ||
                    !graph.Render(monoScratch, count, sampleRate))
                {
                    System.Array.Clear(monoScratch, 0, count);
                }
                System.Array.Copy(monoScratch, 0, data, offset, count);
                offset += count;
            }
        }

        private void OnDestroy()
        {
            if (clip != null)
                Destroy(clip);
        }
    }
}
