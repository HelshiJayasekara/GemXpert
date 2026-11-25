using UnityEngine;

namespace GemXpert.UI
{
    /// <summary>
    /// Generates an anti-aliased, 9-sliced rounded-rectangle sprite at runtime so panels and buttons
    /// get soft corners without shipping texture assets.
    /// </summary>
    public static class RoundedSprite
    {
        private const int Size = 64;
        private const int Radius = 24;

        private static Sprite _cached;

        public static Sprite Get()
        {
            if (_cached != null) return _cached;

            var tex = new Texture2D(Size, Size, TextureFormat.RGBA32, false)
            {
                name = "GemXpert_RoundedRect",
                wrapMode = TextureWrapMode.Clamp,
                filterMode = FilterMode.Bilinear,
                hideFlags = HideFlags.DontSave,
            };

            var pixels = new Color32[Size * Size];
            for (var y = 0; y < Size; y++)
            {
                for (var x = 0; x < Size; x++)
                {
                    // Distance from the nearest corner-circle centre (0 inside the straight edges).
                    var cx = Mathf.Clamp(x + 0.5f, Radius, Size - Radius);
                    var cy = Mathf.Clamp(y + 0.5f, Radius, Size - Radius);
                    var d = Vector2.Distance(new Vector2(x + 0.5f, y + 0.5f), new Vector2(cx, cy));
                    var a = Mathf.Clamp01(Radius - d + 0.5f);
                    pixels[y * Size + x] = new Color32(255, 255, 255, (byte)(a * 255));
                }
            }

            tex.SetPixels32(pixels);
            tex.Apply(false, true);

            _cached = Sprite.Create(
                tex,
                new Rect(0, 0, Size, Size),
                new Vector2(0.5f, 0.5f),
                100f,
                0,
                SpriteMeshType.FullRect,
                new Vector4(Radius, Radius, Radius, Radius));
            _cached.name = "GemXpert_RoundedRect";
            _cached.hideFlags = HideFlags.DontSave;
            return _cached;
        }
    }
}
