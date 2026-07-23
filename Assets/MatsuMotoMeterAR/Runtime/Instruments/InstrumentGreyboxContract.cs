using UnityEngine;

namespace MatsuMotoMeterAR.Instruments
{
    public sealed class InstrumentGreyboxContract : MonoBehaviour
    {
        public MockInstrumentKind Kind { get; private set; }
        public MockInstrumentTheme Theme { get; private set; }
        public Transform MountOrigin { get; private set; }
        public Transform Logic { get; private set; }
        public Transform Interaction { get; private set; }
        public Collider InteractionCollider { get; private set; }
        public MockInstrumentInteraction InstrumentInteraction { get; private set; }
        public Transform VisualSocket { get; private set; }
        public Transform OcclusionProxy { get; private set; }
        public Transform LabelSocket { get; private set; }
        public Transform AudioSocket { get; private set; }
        public Transform VfxSocket { get; private set; }

        public void Configure(
            MockInstrumentKind kind,
            MockInstrumentTheme theme,
            Transform mountOrigin,
            Transform logic,
            Transform interaction,
            Collider interactionCollider,
            MockInstrumentInteraction instrumentInteraction,
            Transform visualSocket,
            Transform occlusionProxy,
            Transform labelSocket,
            Transform audioSocket,
            Transform vfxSocket)
        {
            Kind = kind;
            Theme = theme;
            MountOrigin = mountOrigin;
            Logic = logic;
            Interaction = interaction;
            InteractionCollider = interactionCollider;
            InstrumentInteraction = instrumentInteraction;
            VisualSocket = visualSocket;
            OcclusionProxy = occlusionProxy;
            LabelSocket = labelSocket;
            AudioSocket = audioSocket;
            VfxSocket = vfxSocket;
        }

        public void SetTheme(MockInstrumentTheme theme)
        {
            Theme = MockInstrumentThemeCatalog.Normalize(theme);
        }
    }
}
