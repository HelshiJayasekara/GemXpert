using System;
using UnityEngine;

namespace GemXpert.Core.Catalogue
{
    // ------------------------------------------------------------------------------------------
    // JSON schema for the GemXpert catalogue. All public fields so Unity's JsonUtility can read them.
    // Units: lengths in MILLIMETRES (mm) unless the field name says otherwise; angles in degrees.
    // Ring model space: band axis (finger direction) = +Z, gemstone "up" (out of the table) = +Y,
    // origin = centre of the band. Gem model space: girdle centre at origin, table facing +Y,
    // length along +Z, width along +X.
    // ------------------------------------------------------------------------------------------

    [Serializable]
    public struct Vector3Mm
    {
        public float x;
        public float y;
        public float z;

        public Vector3Mm(float x, float y, float z)
        {
            this.x = x;
            this.y = y;
            this.z = z;
        }

        /// <summary>Converts millimetres to Unity metres.</summary>
        public Vector3 ToMetres() => new Vector3(x, y, z) * 0.001f;
        public Vector3 ToVector3() => new Vector3(x, y, z);
    }

    /// <summary>A place on a ring where a gemstone can be mounted.</summary>
    [Serializable]
    public class MountPointDefinition
    {
        /// <summary>Matches the empty named "GemMount_{id}" in the ring model (e.g. "Center").</summary>
        public string id;
        /// <summary>"center" or "side". Customisation UI edits the center stone; side stones follow rules.</summary>
        public string role;
        /// <summary>Fallback girdle position (mm) if the model has no GemMount empty.</summary>
        public Vector3Mm fallbackPositionMm;
        /// <summary>Fallback rotation (degrees) if the model has no GemMount empty.</summary>
        public Vector3Mm fallbackEulerDeg;
        public string[] supportedShapes;
        public float minLengthMm;
        public float maxLengthMm;
        public float minWidthMm;
        public float maxWidthMm;
        /// <summary>Maximum total depth (table to culet) the head can hold, in mm.</summary>
        public float maxDepthMm;
        /// <summary>How far (mm) the customer may slide the stone along each local axis from the seat.</summary>
        public Vector3Mm adjustRangeMm;
        /// <summary>Optional fixed stone for side mounts (gem id / shape id / size). Empty = follows center.</summary>
        public string fixedGemstoneId;
        public string fixedShapeId;
        public float fixedLengthMm;
    }

    [Serializable]
    public class RingDesignDefinition
    {
        public string id;
        public string displayName;
        public string settingStyle;
        public string description;
        /// <summary>Resources path of the ring prefab (Phase 2), e.g. "GemXpert/Rings/Ring_Solitaire".</summary>
        public string prefabResource;
        public float innerDiameterMm;
        public float bandWidthMm;
        public float bandThicknessMm;
        public string defaultMetalId;
        public string defaultGemstoneId;
        public string defaultShapeId;
        public MountPointDefinition[] mounts;
        /// <summary>Renderer name prefixes that receive the metal material (never gemstones).</summary>
        public string[] metalRendererPrefixes;
        /// <summary>Renderer name prefixes for fixed accent stones (e.g. halo melee) that keep a gem material.</summary>
        public string[] accentStoneRendererPrefixes;
    }

    [Serializable]
    public class GemstoneDefinition
    {
        public string id;
        public string displayName;
        public string mineral;
        public string description;
        /// <summary>Body colour as #RRGGBB.</summary>
        public string colorHex;
        public float refractiveIndex;
        public float dispersion;
        public float hardnessMohs;
        /// <summary>0 = opaque, 1 = water-clear. Drives the real-time material's transparency.</summary>
        public float transparency;
        /// <summary>Material smoothness 0-1 (polished stones are high).</summary>
        public float smoothness;
        public string[] availableShapes;
    }

    [Serializable]
    public class GemShapeDefinition
    {
        public string id;
        public string displayName;
        /// <summary>Resources path of the unit-size gem mesh prefab (Phase 2).</summary>
        public string prefabResource;
        public float defaultLengthMm;
        public float defaultWidthMm;
        /// <summary>Total depth as a fraction of width (e.g. 0.61 for a round brilliant).</summary>
        public float depthRatio;
        /// <summary>True when length must equal width (round, princess, square cushion).</summary>
        public bool lockAspect;
        public float minLengthMm;
        public float maxLengthMm;
    }

    [Serializable]
    public class MetalDefinition
    {
        public string id;
        public string displayName;
        public string colorHex;
        public float metallic;
        public float smoothness;
        public string description;
    }

    // JsonUtility cannot read top-level arrays, so each file wraps its list in { "items": [...] }.
    [Serializable] public class RingDesignList { public RingDesignDefinition[] items; }
    [Serializable] public class GemstoneList { public GemstoneDefinition[] items; }
    [Serializable] public class GemShapeList { public GemShapeDefinition[] items; }
    [Serializable] public class MetalList { public MetalDefinition[] items; }
}
