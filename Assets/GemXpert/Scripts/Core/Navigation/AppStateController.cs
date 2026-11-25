using System;
using UnityEngine;

namespace GemXpert.Core
{
    /// <summary>
    /// Scene-level owner of the current <see cref="AppScreen"/>. UI and gameplay systems call
    /// <see cref="NavigateTo"/>, <see cref="Back"/> and <see cref="Home"/>, and listen to <see cref="ScreenChanged"/>.
    /// </summary>
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(-1000)]
    public sealed class AppStateController : MonoBehaviour
    {
        [SerializeField] private AppScreen initialScreen = AppScreen.Welcome;

        private NavigationModel _model;

        public static AppStateController Instance { get; private set; }

        /// <summary>(previous, current)</summary>
        public event Action<AppScreen, AppScreen> ScreenChanged;

        public AppScreen Current => _model != null ? _model.Current : initialScreen;
        public bool CanGoBack => _model != null && _model.CanGoBack;

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Debug.LogWarning("[GemXpert] A second AppStateController was found and disabled.", this);
                enabled = false;
                return;
            }

            Instance = this;
            _model = new NavigationModel(initialScreen);
            _model.Changed += (prev, next) =>
            {
                Debug.Log($"[GemXpert] Screen: {prev} -> {next}");
                ScreenChanged?.Invoke(prev, next);
            };
        }

        private void OnDestroy()
        {
            if (Instance == this) Instance = null;
        }

        public void NavigateTo(AppScreen screen) => _model?.NavigateTo(screen);
        public void Back() => _model?.Back();
        public void Home() => _model?.Home();
    }
}
