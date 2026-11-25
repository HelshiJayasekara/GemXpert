using GemXpert.Core;
using TMPro;
using UnityEngine;

namespace GemXpert.UI
{
    /// <summary>
    /// Shown for screens whose features are not built yet. It says so plainly, with the phase that delivers it,
    /// so unfinished work is never presented as complete.
    /// </summary>
    public sealed class PendingFeatureScreen : UIScreen
    {
        private readonly ScreenCatalogue.Entry _entry;

        public PendingFeatureScreen(ScreenCatalogue.Entry entry)
        {
            _entry = entry;
        }

        public override AppScreen Id => _entry.Screen;
        public override string Title => _entry.Title;

        public override void Build(ScreenContext ctx, RectTransform content)
        {
            VRUIFactory.AddVertical(content, 22f, new RectOffset(120, 120, 80, 40), TextAnchor.MiddleCenter);

            var badge = VRUIFactory.CreateText(content, $"IN DEVELOPMENT  -  PHASE {_entry.Phase}", UITheme.CaptionSize,
                UITheme.Warning, TextAlignmentOptions.Center, FontStyles.Bold);
            badge.characterSpacing = 10f;
            VRUIFactory.SetPreferred(badge, 30f);

            var title = VRUIFactory.CreateText(content, _entry.Title, UITheme.TitleSize, UITheme.GoldBright,
                TextAlignmentOptions.Center, FontStyles.Bold);
            VRUIFactory.SetPreferred(title, 64f);

            var detail = VRUIFactory.CreateText(content, _entry.Detail, UITheme.BodySize, UITheme.TextPrimary, TextAlignmentOptions.Center);
            VRUIFactory.SetPreferred(detail, 130f);

            var note = VRUIFactory.CreateText(content,
                "This area is not available in the current build.",
                UITheme.CaptionSize, UITheme.TextMuted, TextAlignmentOptions.Center, FontStyles.Italic);
            VRUIFactory.SetPreferred(note, 30f);

            var back = VRUIFactory.CreateButton(content, "BACK TO SHOWROOM", () => ctx.State.Home(), ButtonStyle.Secondary);
            VRUIFactory.SetPreferred(back, UITheme.ButtonHeight, 440f);
        }
    }
}
