# Meter M2n8 production Quest smoke

Date: 2026-08-18
Device: Quest 3 (`2G0YC1ZG2J02HL`, `eureka`)
APK: `Builds/QuestSmoke/AnalogInstrumentMR-Meter_M2n8-production-smoke-quest3.apk`
SHA-256: `d7303a5ab44c7864f6c0d145aabe80fc89241d6241923d8e554f5810c4a66244`

## Deployment

- `adb install -r`: PASS (`Success`)
- package: `com.DefaultCompany.MatsuMotoMeterAR`
- activity: `com.unity3d.player.UnityPlayerGameActivity`
- initial PID: `10808`
- Quest wake state: Awake
- Spatial Anchor locate: 20 / 20
- fatal crash at launch: none

## User acceptance

| Check | Result |
| --- | --- |
| Round axis / counterweight flicker absent | PASS |
| Medium / Large single ticks and ring clearance | PASS |
| Needle reaches min / max endpoints | PASS |
| OFF / ON material display | PASS |

Overall: **PASS**
