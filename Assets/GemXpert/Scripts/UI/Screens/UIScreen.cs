using GemXpert.Core;
using UnityEngine;

namespace GemXpert.UI
{
    /// <summary>Services a screen may use while building itself.</summary>
    public sealed class ScreenContext
    {
        public ScreenContext(AppStateController state, ScreenRouter router)
        {
            State = state;
            Router = router;
        }

        public AppStateController State { get; }
        public ScreenRouter Router { get; }
    }

    /// <summary>
    /// A screen builds its widgets into the router's content area every time it is shown,
    /// and its widgets are destroyed when it is hidden. Screens hold no scene state of their own.
    /// </summary>
    public abstract class UIScreen
    {
        public abstract AppScreen Id { get; }

        /// <summary>Title shown in the panel header. Ignored when <see cref="ShowHeader"/> is false.</summary>
        public abstract string Title { get; }

        /// <summary>Welcome uses its own large branding and hides the standard header.</summary>
        public virtual bool ShowHeader => true;

        public abstract void Build(ScreenContext context, RectTransform content);

        /// <summary>Called after the screen is hidden and its widgets destroyed. Unsubscribe events here.</summary>
        public virtual void OnHidden() { }
    }
}
