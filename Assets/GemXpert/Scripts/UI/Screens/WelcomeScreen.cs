using GemXpert.Core;
using TMPro;
using UnityEngine;

namespace GemXpert.UI
{
    /// <summary>Stage A – branding, Start Experience, How it works, device connection.</summary>
    public sealed class WelcomeScreen : UIScreen
    {
        public override AppScreen Id => AppScreen.Welcome;
        public override string Title => "Welcome";
        public override bool ShowHeader => false;

        public override void Build(ScreenContext ctx, RectTransform content)
        {
            VRUIFactory.AddVertical(content, 18f, new RectOffset(120, 120, 70, 50), TextAnchor.MiddleCenter);

            var eyebrow = VRUIFactory.CreateText(content, "WELCOME TO", UITheme.CaptionSize, UITheme.TextMuted,
                TextAlignmentOptions.Center, FontStyles.Bold);
            eyebrow.characterSpacing = 18f;
            VRUIFactory.SetPreferred(eyebrow, 30f);

            var brand = VRUIFactory.CreateText(content, "GEMXPERT", UITheme.BrandSize, UITheme.GoldBright,
                TextAlignmentOptions.Center, FontStyles.Bold);
            brand.characterSpacing = 22f;
            VRUIFactory.SetPreferred(brand, 130f);

            var tagline = VRUIFactory.CreateText(content, "Immersive Gemstone & Jewellery Studio", UITheme.SubtitleSize,
                UITheme.TextPrimary, TextAlignmentOptions.Center);
            tagline.characterSpacing = 3f;
            VRUIFactory.SetPreferred(tagline, 46f);

            var rule = VRUIFactory.CreateDivider(content, 2f);
            VRUIFactory.SetPreferred(rule, 2f, 260f);
            rule.GetComponent<UnityEngine.UI.LayoutElement>().flexibleWidth = 0f;

            var intro = VRUIFactory.CreateText(content,
                "Choose a ring design, fit a gemstone to its setting, adjust its cut, size and metal, " +
                "then inspect the finished piece up close on your own hand.",
                UITheme.BodySize, UITheme.TextMuted, TextAlignmentOptions.Center);
            VRUIFactory.SetPreferred(intro, 90f);

            var spacer = VRUIFactory.CreateRect("Spacer", content);
            VRUIFactory.SetPreferred(spacer, 10f);

            var start = VRUIFactory.CreateButton(content, "START EXPERIENCE",
                () => ctx.State.NavigateTo(AppScreen.Showroom), ButtonStyle.Primary, 96f);
            VRUIFactory.SetPreferred(start, 96f, 520f);

            var row = VRUIFactory.CreateRect("SecondaryRow", content);
            VRUIFactory.AddHorizontal(row, 20f, null, TextAnchor.MiddleCenter);
            VRUIFactory.SetPreferred(row, UITheme.ButtonHeight);
            var how = VRUIFactory.CreateButton(row, "HOW IT WORKS", () => ctx.State.NavigateTo(AppScreen.Instructions));
            VRUIFactory.SetPreferred(how, -1f, 300f);
            var device = VRUIFactory.CreateButton(row, "WEARABLE DEVICE", () => ctx.State.NavigateTo(AppScreen.DeviceConnection));
            VRUIFactory.SetPreferred(device, -1f, 300f);
        }
    }
}
