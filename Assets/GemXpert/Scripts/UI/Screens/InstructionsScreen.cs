using GemXpert.Core;
using TMPro;
using UnityEngine;

namespace GemXpert.UI
{
    /// <summary>Stage A – how the experience works, plus the controls for the active run mode.</summary>
    public sealed class InstructionsScreen : UIScreen
    {
        public override AppScreen Id => AppScreen.Instructions;
        public override string Title => "How It Works";

        private static readonly (string step, string title, string body)[] Steps =
        {
            ("01", "Choose a setting", "Browse solitaire, halo, three-stone, prong and bezel rings."),
            ("02", "Fit a gemstone", "Pick sapphire, ruby, emerald or diamond-style. GemXpert checks it fits the setting."),
            ("03", "Make it yours", "Adjust the cut, size and position of the stone, and the metal of the band."),
            ("04", "Inspect & save", "Turn your hand, zoom in on the stone, compare designs and save your favourite."),
        };

        public override void Build(ScreenContext ctx, RectTransform content)
        {
            VRUIFactory.AddVertical(content, 14f, new RectOffset(64, 64, 28, 28), TextAnchor.UpperLeft);

            foreach (var (step, title, body) in Steps)
            {
                var row = VRUIFactory.CreateRect($"Step{step}", content);
                VRUIFactory.AddHorizontal(row, 24f, null, TextAnchor.UpperLeft);
                VRUIFactory.SetPreferred(row, 70f);

                var number = VRUIFactory.CreateText(row, step, 40f, UITheme.Gold, TextAlignmentOptions.TopLeft, FontStyles.Bold);
                VRUIFactory.SetPreferred(number, -1f, 70f);

                var col = VRUIFactory.CreateRect("Text", row);
                VRUIFactory.AddVertical(col, 2f, null, TextAnchor.UpperLeft);
                VRUIFactory.SetPreferred(col, -1f, -1f, 1f);
                var t = VRUIFactory.CreateText(col, title, 30f, UITheme.TextPrimary, TextAlignmentOptions.TopLeft, FontStyles.Bold);
                VRUIFactory.SetPreferred(t, 36f);
                var b = VRUIFactory.CreateText(col, body, UITheme.CaptionSize + 2f, UITheme.TextMuted, TextAlignmentOptions.TopLeft);
                VRUIFactory.SetPreferred(b, 30f);
            }

            VRUIFactory.CreateDivider(content, 2f);

            var controlsTitle = VRUIFactory.CreateText(content, "CONTROLS  -  " + GemXpertRuntime.Describe(GemXpertRuntime.ActiveRunMode).ToUpperInvariant(),
                UITheme.CaptionSize, UITheme.Gold, TextAlignmentOptions.TopLeft, FontStyles.Bold);
            controlsTitle.characterSpacing = 8f;
            VRUIFactory.SetPreferred(controlsTitle, 30f);

            var controls = VRUIFactory.CreateText(content, ControlsFor(GemXpertRuntime.ActiveRunMode),
                UITheme.CaptionSize + 2f, UITheme.TextPrimary, TextAlignmentOptions.TopLeft);
            VRUIFactory.SetPreferred(controls, 96f);

            var start = VRUIFactory.CreateButton(content, "ENTER THE SHOWROOM", () => ctx.State.NavigateTo(AppScreen.Showroom), ButtonStyle.Primary);
            VRUIFactory.SetPreferred(start, UITheme.ButtonHeight);
        }

        public static string ControlsFor(RunMode mode)
        {
            switch (mode)
            {
                case RunMode.HeadsetXR:
                    return "Point at a panel and pull the trigger (or pinch) to select.  Left stick: teleport / move.  " +
                           "Right stick: snap turn.  Grip: grab jewellery.  Menu button: bring this panel in front of you.";
                case RunMode.XRDeviceSimulator:
                    return "Hold right mouse to look.  WASD moves the simulated headset.  Tab cycles the active controller.  " +
                           "Left click = trigger, G = grip.  The simulator's on-screen help lists every key.";
                case RunMode.Desktop:
                    return "Hold right mouse and drag to look.  W A S D to walk.  Left click a panel button to select.  " +
                           "M brings the menu in front of you.  R resets your view.";
                default:
                    return "Detecting your device...";
            }
        }
    }
}
