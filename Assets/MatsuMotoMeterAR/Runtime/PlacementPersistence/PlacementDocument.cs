using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Anchors;
using MatsuMotoMeterAR.Signals;
using UnityEngine;

namespace MatsuMotoMeterAR.PlacementPersistence
{
    [Serializable]
    public sealed class PlacementDocument
    {
        public const int LegacySchemaVersion = 1;
        public const int PreviousSchemaVersion = 6;
        public const int CurrentSchemaVersion = 7;
        public const int MaximumActivePlacements = 48;
        public const int MaximumStoredPlacements = 192;
        public const int MaximumConnections = 192;

        public int schemaVersion = CurrentSchemaVersion;
        public long revision;
        public List<PlacementRecord> placements = new();
        public List<SignalConnectionRecord> connections = new();
    }

    [Serializable]
    public sealed class SignalConnectionRecord
    {
        public const float DefaultInputMinimum = 0f;
        public const float DefaultInputMaximum = 1f;
        public const float DefaultOutputMinimum = 0.2f;
        public const float DefaultOutputMaximum = 0.8f;
        public const float DefaultThresholdValue = 0.5f;
        public const int AutomaticTargetInputSlot = -1;
        public const int DefaultCompositionPriority = 0;
        public const int MinimumCompositionPriority = 0;
        public const int MaximumCompositionPriority = 3;

        public string connectionId;
        public string sourcePlacementId;
        public string targetPlacementId;
        public int transformKind = (int)SignalTransformKind.Direct;
        public float inputMinimum = DefaultInputMinimum;
        public float inputMaximum = DefaultInputMaximum;
        public float outputMinimum = DefaultOutputMinimum;
        public float outputMaximum = DefaultOutputMaximum;
        public float thresholdValue = DefaultThresholdValue;
        public int thresholdComparison = (int)SignalThresholdComparison.Above;
        public int targetInputSlot = AutomaticTargetInputSlot;
        public int compositionPriority = DefaultCompositionPriority;

        public SignalConnectionRecord Clone()
        {
            return new SignalConnectionRecord
            {
                connectionId = connectionId,
                sourcePlacementId = sourcePlacementId,
                targetPlacementId = targetPlacementId,
                transformKind = transformKind,
                inputMinimum = inputMinimum,
                inputMaximum = inputMaximum,
                outputMinimum = outputMinimum,
                outputMaximum = outputMaximum,
                thresholdValue = thresholdValue,
                thresholdComparison = thresholdComparison,
                targetInputSlot = targetInputSlot,
                compositionPriority = compositionPriority
            };
        }
    }

    [Serializable]
    public sealed class PlacementRecord
    {
        public string placementId;
        public string anchorId;
        public string roomId;
        public string instrumentTypeId;
        public int surfaceKind = (int)SurfaceKind.Unknown;
        public SerializablePose localOffset = SerializablePose.Identity;
        public float normalizedValue;
        public int lifecycle = (int)PlacementLifecycle.Active;
        public int windowPanelPreset = (int)WindowPanelGraphicPreset.Orbit;
        public int signalCompositionKind =
            (int)SignalCompositionKind.Average;

        public PlacementRecord Clone()
        {
            return new PlacementRecord
            {
                placementId = placementId,
                anchorId = anchorId,
                roomId = roomId,
                instrumentTypeId = instrumentTypeId,
                surfaceKind = surfaceKind,
                localOffset = localOffset,
                normalizedValue = normalizedValue,
                lifecycle = lifecycle,
                windowPanelPreset = windowPanelPreset,
                signalCompositionKind = signalCompositionKind
            };
        }
    }

    public enum PlacementLifecycle
    {
        Active,
        PendingDelete,
        Unavailable
    }

    [Serializable]
    public struct SerializablePose
    {
        public float px;
        public float py;
        public float pz;
        public float qx;
        public float qy;
        public float qz;
        public float qw;

        public static SerializablePose Identity => new()
        {
            qw = 1f
        };

        public Pose ToPose()
        {
            return new Pose(
                new Vector3(px, py, pz),
                new Quaternion(qx, qy, qz, qw));
        }

        public static SerializablePose FromPose(Pose pose)
        {
            return new SerializablePose
            {
                px = pose.position.x,
                py = pose.position.y,
                pz = pose.position.z,
                qx = pose.rotation.x,
                qy = pose.rotation.y,
                qz = pose.rotation.z,
                qw = pose.rotation.w
            };
        }
    }
}
