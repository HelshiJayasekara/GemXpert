using System;
using System.Collections.Generic;
using UnityEngine;

namespace GemXpert.Core.Catalogue
{
    /// <summary>In-memory catalogue with id lookups and referential validation.</summary>
    public sealed class CatalogueDatabase
    {
        public const string ResourcesRoot = "Catalogue/";

        public IReadOnlyList<RingDesignDefinition> Rings => _rings;
        public IReadOnlyList<GemstoneDefinition> Gemstones => _gemstones;
        public IReadOnlyList<GemShapeDefinition> Shapes => _shapes;
        public IReadOnlyList<MetalDefinition> Metals => _metals;

        private readonly RingDesignDefinition[] _rings;
        private readonly GemstoneDefinition[] _gemstones;
        private readonly GemShapeDefinition[] _shapes;
        private readonly MetalDefinition[] _metals;

        public CatalogueDatabase(
            RingDesignDefinition[] rings,
            GemstoneDefinition[] gemstones,
            GemShapeDefinition[] shapes,
            MetalDefinition[] metals)
        {
            _rings = rings ?? Array.Empty<RingDesignDefinition>();
            _gemstones = gemstones ?? Array.Empty<GemstoneDefinition>();
            _shapes = shapes ?? Array.Empty<GemShapeDefinition>();
            _metals = metals ?? Array.Empty<MetalDefinition>();
        }

        public RingDesignDefinition FindRing(string id) => Find(_rings, id, r => r.id);
        public GemstoneDefinition FindGemstone(string id) => Find(_gemstones, id, g => g.id);
        public GemShapeDefinition FindShape(string id) => Find(_shapes, id, s => s.id);
        public MetalDefinition FindMetal(string id) => Find(_metals, id, m => m.id);

        private static T Find<T>(T[] items, string id, Func<T, string> key) where T : class
        {
            if (string.IsNullOrEmpty(id)) return null;
            foreach (var item in items)
            {
                if (item != null && string.Equals(key(item), id, StringComparison.Ordinal)) return item;
            }
            return null;
        }

        // ---------------------------------------------------------------- loading

        /// <summary>Parses the four catalogue JSON documents. Throws on malformed JSON.</summary>
        public static CatalogueDatabase FromJson(string ringsJson, string gemstonesJson, string shapesJson, string metalsJson)
        {
            return new CatalogueDatabase(
                JsonUtility.FromJson<RingDesignList>(ringsJson)?.items,
                JsonUtility.FromJson<GemstoneList>(gemstonesJson)?.items,
                JsonUtility.FromJson<GemShapeList>(shapesJson)?.items,
                JsonUtility.FromJson<MetalList>(metalsJson)?.items);
        }

        /// <summary>Loads Resources/Catalogue/{rings,gemstones,shapes,metals}.json.</summary>
        public static CatalogueDatabase LoadFromResources()
        {
            return FromJson(
                LoadText("rings"),
                LoadText("gemstones"),
                LoadText("shapes"),
                LoadText("metals"));
        }

        private static string LoadText(string file)
        {
            var asset = Resources.Load<TextAsset>(ResourcesRoot + file);
            if (asset == null)
            {
                throw new InvalidOperationException($"[GemXpert] Missing catalogue file Resources/{ResourcesRoot}{file}.json");
            }
            return asset.text;
        }

        // ---------------------------------------------------------------- validation

        /// <summary>Returns a list of human-readable problems. Empty list = catalogue is consistent.</summary>
        public List<string> Validate()
        {
            var errors = new List<string>();
            CheckUnique(_rings, r => r.id, "ring", errors);
            CheckUnique(_gemstones, g => g.id, "gemstone", errors);
            CheckUnique(_shapes, s => s.id, "shape", errors);
            CheckUnique(_metals, m => m.id, "metal", errors);

            foreach (var gem in _gemstones)
            {
                if (!TryParseColor(gem.colorHex, out _)) errors.Add($"gemstone '{gem.id}': invalid colorHex '{gem.colorHex}'");
                foreach (var shapeId in gem.availableShapes ?? Array.Empty<string>())
                {
                    if (FindShape(shapeId) == null) errors.Add($"gemstone '{gem.id}': unknown shape '{shapeId}'");
                }
            }

            foreach (var metal in _metals)
            {
                if (!TryParseColor(metal.colorHex, out _)) errors.Add($"metal '{metal.id}': invalid colorHex '{metal.colorHex}'");
            }

            foreach (var shape in _shapes)
            {
                if (shape.minLengthMm <= 0 || shape.maxLengthMm < shape.minLengthMm)
                    errors.Add($"shape '{shape.id}': invalid length range {shape.minLengthMm}-{shape.maxLengthMm} mm");
                if (shape.depthRatio <= 0) errors.Add($"shape '{shape.id}': depthRatio must be > 0");
            }

            foreach (var ring in _rings)
            {
                if (FindMetal(ring.defaultMetalId) == null) errors.Add($"ring '{ring.id}': unknown defaultMetalId '{ring.defaultMetalId}'");
                if (FindGemstone(ring.defaultGemstoneId) == null) errors.Add($"ring '{ring.id}': unknown defaultGemstoneId '{ring.defaultGemstoneId}'");
                if (FindShape(ring.defaultShapeId) == null) errors.Add($"ring '{ring.id}': unknown defaultShapeId '{ring.defaultShapeId}'");
                if (ring.mounts == null || ring.mounts.Length == 0)
                {
                    errors.Add($"ring '{ring.id}': has no mount points");
                    continue;
                }

                var hasCenter = false;
                foreach (var mount in ring.mounts)
                {
                    if (mount.role == "center") hasCenter = true;
                    if (mount.maxLengthMm < mount.minLengthMm || mount.maxWidthMm < mount.minWidthMm)
                        errors.Add($"ring '{ring.id}' mount '{mount.id}': max size below min size");
                    foreach (var shapeId in mount.supportedShapes ?? Array.Empty<string>())
                    {
                        if (FindShape(shapeId) == null) errors.Add($"ring '{ring.id}' mount '{mount.id}': unknown shape '{shapeId}'");
                    }
                    if (!string.IsNullOrEmpty(mount.fixedGemstoneId) && FindGemstone(mount.fixedGemstoneId) == null)
                        errors.Add($"ring '{ring.id}' mount '{mount.id}': unknown fixedGemstoneId '{mount.fixedGemstoneId}'");
                }
                if (!hasCenter) errors.Add($"ring '{ring.id}': needs exactly one mount with role 'center'");
            }

            return errors;
        }

        private static void CheckUnique<T>(T[] items, Func<T, string> key, string label, List<string> errors)
        {
            var seen = new HashSet<string>();
            foreach (var item in items)
            {
                var id = item == null ? null : key(item);
                if (string.IsNullOrEmpty(id)) { errors.Add($"{label}: entry without id"); continue; }
                if (!seen.Add(id)) errors.Add($"{label}: duplicate id '{id}'");
            }
        }

        public static bool TryParseColor(string hex, out Color color)
        {
            color = Color.magenta;
            return !string.IsNullOrEmpty(hex) && ColorUtility.TryParseHtmlString(hex, out color);
        }
    }
}
