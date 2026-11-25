using System.Linq;
using GemXpert.Core.Catalogue;
using NUnit.Framework;

namespace GemXpert.Tests
{
    public class CatalogueTests
    {
        private CatalogueDatabase _db;

        [OneTimeSetUp]
        public void Load() => _db = CatalogueDatabase.LoadFromResources();

        [Test]
        public void Catalogue_IsInternallyConsistent()
        {
            var errors = _db.Validate();
            Assert.IsEmpty(errors, string.Join("\n", errors));
        }

        [Test]
        public void Catalogue_ContainsRequiredRingDesigns()
        {
            CollectionAssert.IsSupersetOf(_db.Rings.Select(r => r.id).ToList(),
                new[] { "solitaire", "halo", "three_stone", "prong", "bezel" });
        }

        [Test]
        public void Catalogue_ContainsRequiredGemstones()
        {
            CollectionAssert.IsSupersetOf(_db.Gemstones.Select(g => g.id).ToList(),
                new[] { "blue_sapphire", "ruby", "emerald", "yellow_sapphire", "diamond" });
        }

        [Test]
        public void Catalogue_ContainsRequiredShapes()
        {
            CollectionAssert.IsSupersetOf(_db.Shapes.Select(s => s.id).ToList(),
                new[] { "round", "oval", "cushion", "pear", "emerald", "princess" });
        }

        [Test]
        public void Catalogue_ContainsRequiredMetals()
        {
            CollectionAssert.IsSupersetOf(_db.Metals.Select(m => m.id).ToList(),
                new[] { "yellow_gold", "white_gold", "rose_gold", "silver" });
        }

        [Test]
        public void EveryRing_DefaultStoneFitsItsCenterMount()
        {
            foreach (var ring in _db.Rings)
            {
                var center = ring.mounts.Single(m => m.role == "center");
                var shape = _db.FindShape(ring.defaultShapeId);
                Assert.Contains(ring.defaultShapeId, center.supportedShapes, $"{ring.id}: default shape not supported by its center mount");
                Assert.That(shape.defaultLengthMm, Is.InRange(center.minLengthMm, center.maxLengthMm), $"{ring.id}: default length out of range");
                Assert.That(shape.defaultWidthMm, Is.InRange(center.minWidthMm, center.maxWidthMm), $"{ring.id}: default width out of range");
                Assert.That(shape.defaultWidthMm * shape.depthRatio, Is.LessThanOrEqualTo(center.maxDepthMm), $"{ring.id}: default depth too deep");
            }
        }

        [Test]
        public void MalformedReference_IsReported()
        {
            var ring = new RingDesignDefinition
            {
                id = "broken", defaultMetalId = "unobtainium", defaultGemstoneId = "ruby", defaultShapeId = "round",
                mounts = new[] { new MountPointDefinition { id = "Center", role = "center", supportedShapes = new[] { "round" },
                    minLengthMm = 5, maxLengthMm = 6, minWidthMm = 5, maxWidthMm = 6 } },
            };
            var db = new CatalogueDatabase(new[] { ring }, _db.Gemstones.ToArray(), _db.Shapes.ToArray(), _db.Metals.ToArray());
            Assert.That(db.Validate(), Has.Some.Contains("unobtainium"));
        }
    }
}
