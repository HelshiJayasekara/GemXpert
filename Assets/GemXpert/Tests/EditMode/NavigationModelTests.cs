using GemXpert.Core;
using NUnit.Framework;

namespace GemXpert.Tests
{
    public class NavigationModelTests
    {
        [Test]
        public void StartsOnInitialScreen_WithNoHistory()
        {
            var nav = new NavigationModel(AppScreen.Welcome);
            Assert.AreEqual(AppScreen.Welcome, nav.Current);
            Assert.IsFalse(nav.CanGoBack);
        }

        [Test]
        public void NavigateThenBack_ReturnsToPreviousScreen()
        {
            var nav = new NavigationModel(AppScreen.Welcome);
            nav.NavigateTo(AppScreen.Showroom);
            nav.NavigateTo(AppScreen.RingSelection);
            Assert.IsTrue(nav.Back());
            Assert.AreEqual(AppScreen.Showroom, nav.Current);
            Assert.IsTrue(nav.Back());
            Assert.AreEqual(AppScreen.Welcome, nav.Current);
            Assert.IsFalse(nav.Back());
        }

        [Test]
        public void NavigatingToCurrentScreen_IsIgnored()
        {
            var nav = new NavigationModel(AppScreen.Showroom);
            var raised = 0;
            nav.Changed += (_, __) => raised++;
            Assert.IsFalse(nav.NavigateTo(AppScreen.Showroom));
            Assert.AreEqual(0, raised);
            Assert.AreEqual(0, nav.Depth);
        }

        [Test]
        public void Home_ClearsHistory()
        {
            var nav = new NavigationModel(AppScreen.Welcome);
            nav.NavigateTo(AppScreen.Showroom);
            nav.NavigateTo(AppScreen.Customization);
            nav.Home();
            Assert.AreEqual(AppScreen.Showroom, nav.Current);
            Assert.IsFalse(nav.CanGoBack);
        }

        [Test]
        public void Changed_ReportsPreviousAndCurrent()
        {
            var nav = new NavigationModel(AppScreen.Welcome);
            AppScreen? prev = null, next = null;
            nav.Changed += (p, n) => { prev = p; next = n; };
            nav.NavigateTo(AppScreen.Instructions);
            Assert.AreEqual(AppScreen.Welcome, prev);
            Assert.AreEqual(AppScreen.Instructions, next);
        }
    }
}
