using UnityEngine;

namespace GemXpert.UI
{
    /// <summary>
    /// The GemXpert visual language: dark lacquer surfaces, champagne-gold accents, ivory text.
    /// Sizes are in canvas pixels. On GemXpert world-space canvases 1 px = 1 mm.
    /// </summary>
    public static class UITheme
    {
        // Colours
        public static readonly Color Backdrop = Hex("#0B0B0D", 0.94f);
        public static readonly Color Surface = Hex("#16161A");
        public static readonly Color SurfaceHover = Hex("#222228");
        public static readonly Color SurfacePressed = Hex("#2C2A26");
        public static readonly Color Gold = Hex("#C9A45C");
        public static readonly Color GoldBright = Hex("#E6C983");
        public static readonly Color GoldDeep = Hex("#8E6F35");
        public static readonly Color TextPrimary = Hex("#F3EEE5");
        public static readonly Color TextMuted = Hex("#9D978C");
        public static readonly Color TextOnGold = Hex("#141210");
        public static readonly Color Success = Hex("#73C291");
        public static readonly Color Warning = Hex("#E2B04A");
        public static readonly Color Danger = Hex("#E0675F");

        // Typography (px; 1 px = 1 mm in world space -> 30 px ~ 3 cm cap height at ~1.5 m is comfortably readable)
        public const float BrandSize = 112f;
        public const float TitleSize = 52f;
        public const float SubtitleSize = 34f;
        public const float BodySize = 28f;
        public const float CaptionSize = 22f;
        public const float ButtonSize = 30f;

        // Metrics (px)
        public const float PanelPadding = 48f;
        public const float Spacing = 20f;
        public const float ButtonHeight = 88f;
        public const float CornerRadius = 18f;
        public const float BorderWidth = 3f;

        public static Color Hex(string hex, float alpha = 1f)
        {
            if (!ColorUtility.TryParseHtmlString(hex, out var c)) c = Color.magenta;
            c.a = alpha;
            return c;
        }
    }
}
