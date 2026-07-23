using System;
using System.Collections.Generic;
using MatsuMotoMeterAR.Anchors;
using UnityEngine;

namespace MatsuMotoMeterAR.PlacementPersistence
{
    [Serializable]
    public sealed class PlacementDocument
    {
        public const int CurrentSchemaVersion = 1;
        public const int MaximumActivePlacements = 24;

        public int schemaVersion = CurrentSchemaVersion;
        public long revision;
        public List<PlacementRecord> placements = new();
    }

    [Serializable]
    public sealed class PlacementRecord
    {
        public string placementId;
        public string anchorId;
        public string instrumentTypeId;
        public int surfaceKind = (int)SurfaceKind.Unknown;
        public SerializablePose localOffset = SerializablePose.Identity;
        public float normalizedValue;
        public int lifecycle = (int)PlacementLifecycle.Active;

        public PlacementRecord Clone()
        {
            return new PlacementRecord
            {
                placementId = placementId,
                anchorId = anchorId,
                instrumentTypeId = instrumentTypeId,
                surfaceKind = surfaceKind,
                localOffset = localOffset,
                normalizedValue = normalizedValue,
                lifecycle = lifecycle
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
