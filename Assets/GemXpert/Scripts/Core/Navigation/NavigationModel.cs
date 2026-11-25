using System;
using System.Collections.Generic;

namespace GemXpert.Core
{
    /// <summary>
    /// Pure C# navigation history (no Unity dependencies) so it can be unit-tested in EditMode.
    /// Wrapped at runtime by <see cref="AppStateController"/>.
    /// </summary>
    public sealed class NavigationModel
    {
        private readonly Stack<AppScreen> _history = new Stack<AppScreen>();

        /// <summary>Raised after every change: (previous, current).</summary>
        public event Action<AppScreen, AppScreen> Changed;

        public NavigationModel(AppScreen initial)
        {
            Current = initial;
        }

        public AppScreen Current { get; private set; }
        public bool CanGoBack => _history.Count > 0;
        public int Depth => _history.Count;

        /// <summary>Moves to <paramref name="target"/> and remembers the current screen for Back.</summary>
        public bool NavigateTo(AppScreen target)
        {
            if (target == Current) return false;
            _history.Push(Current);
            Set(target);
            return true;
        }

        /// <summary>Returns to the previous screen. Returns false when there is no history.</summary>
        public bool Back()
        {
            if (_history.Count == 0) return false;
            Set(_history.Pop());
            return true;
        }

        /// <summary>Clears history and jumps to <paramref name="home"/> (default: the showroom hub).</summary>
        public void Home(AppScreen home = AppScreen.Showroom)
        {
            _history.Clear();
            if (Current != home)
            {
                Set(home);
            }
        }

        private void Set(AppScreen next)
        {
            var previous = Current;
            Current = next;
            Changed?.Invoke(previous, next);
        }
    }
}
