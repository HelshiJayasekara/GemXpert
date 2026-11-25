using GemXpert.Core;
using UnityEngine;
using UnityEngine.UI;

namespace GemXpert.UI
{
    /// <summary>Main navigation hub inside the showroom. Every studio area is reached from here.</summary>
    public sealed class ShowroomHubScreen : UIScreen
    {
        public override AppScreen Id => AppScreen.Showroom;
        public override string Title => "The Showroom";

        public override void Build(ScreenContext ctx, RectTransform content)
        {
            VRUIFactory.AddVertical(content, 16f, new RectOffset(56, 56, 24, 24), TextAnchor.UpperCenter);

            var intro = VRUIFactory.CreateText(content,
                "Where would you like to begin? Start with a ring design, or go straight to a gemstone.",
                UITheme.BodySize, UITheme.TextMuted, TMPro.TextAlignmentOptions.Center);
            VRUIFactory.SetPreferred(intro, 44f);

            var grid = VRUIFactory.CreateRect("Grid", content);
            VRUIFactory.SetPreferred(grid, 560f);
            var layout = grid.gameObject.AddComponent<GridLayoutGroup>();
            layout.cellSize = new Vector2(370f, 172f);
            layout.spacing = new Vector2(22f, 22f);
            layout.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
            layout.constraintCount = 3;
            layout.childAlignment = TextAnchor.UpperCenter;

            foreach (var entry in ScreenCatalogue.HubEntries)
            {
                var target = entry.Screen;
                var badge = ctx.Router.IsImplemented(target) ? null : $"Coming in Phase {entry.Phase}";
                VRUIFactory.CreateTile(grid, entry.Title, entry.Summary, badge, () => ctx.State.NavigateTo(target));
            }
        }
    }
}
