using System.Collections.Generic;
using GemXpert.Core;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace GemXpert.UI
{
    /// <summary>
    /// Owns the main GemXpert world-space panel (frame, header, content, footer) and rebuilds the
    /// content whenever <see cref="AppStateController"/> changes screen. Screens that are not
    /// implemented yet fall back to <see cref="PendingFeatureScreen"/>.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class ScreenRouter : MonoBehaviour
    {
        [Tooltip("Panel size in millimetres (canvas pixels).")]
        [SerializeField] private Vector2 panelSizeMm = new Vector2(1280f, 820f);

        [Tooltip("Distance from the head when the panel is recalled in front of the user (m).")]
        [SerializeField] private float recallDistance = 1.4f;

        [Tooltip("How far below eye level the panel centre sits when recalled (m). Slightly low is more comfortable.")]
        [SerializeField] private float recallDrop = 0.18f;

        [SerializeField] private float recallSmoothing = 8f;

        private readonly Dictionary<AppScreen, UIScreen> _screens = new Dictionary<AppScreen, UIScreen>();

        private AppStateController _state;
        private ScreenContext _context;
        private Canvas _canvas;
        private RectTransform _header;
        private TextMeshProUGUI _headerTitle;
        private Button _backButton;
        private RectTransform _content;
        private TextMeshProUGUI _footerStatus;
        private UIScreen _active;

        private bool _recalling;
        private Vector3 _recallPosition;
        private Quaternion _recallRotation;

        public Canvas Canvas => _canvas;

        private void Awake()
        {
            Register(new WelcomeScreen());
            Register(new InstructionsScreen());
            Register(new ShowroomHubScreen());
            BuildFrame();
        }

        private void OnEnable()
        {
            GemXpertRuntime.RunModeChanged += OnRuntimeChanged;
            GemXpertRuntime.WearableStatusChanged += OnWearableChanged;
        }

        private void Start()
        {
            _state = AppStateController.Instance;
            if (_state == null)
            {
                Debug.LogError("[GemXpert] ScreenRouter needs an AppStateController in the scene.", this);
                enabled = false;
                return;
            }

            _context = new ScreenContext(_state, this);
            _state.ScreenChanged += OnScreenChanged;
            Show(_state.Current);
            RefreshFooter();
        }

        private void OnDisable()
        {
            GemXpertRuntime.RunModeChanged -= OnRuntimeChanged;
            GemXpertRuntime.WearableStatusChanged -= OnWearableChanged;
        }

        private void OnDestroy()
        {
            if (_state != null) _state.ScreenChanged -= OnScreenChanged;
            if (_canvas != null) GemXpertCanvasRegistry.Unregister(_canvas);
        }

        private void Update()
        {
            if (!_recalling) return;
            var t = 1f - Mathf.Exp(-recallSmoothing * Time.unscaledDeltaTime);
            transform.SetPositionAndRotation(
                Vector3.Lerp(transform.position, _recallPosition, t),
                Quaternion.Slerp(transform.rotation, _recallRotation, t));
            if ((transform.position - _recallPosition).sqrMagnitude < 1e-6f) _recalling = false;
        }

        // ------------------------------------------------------------------ public API

        /// <summary>Adds or replaces the implementation for a screen (later phases register theirs here).</summary>
        public void Register(UIScreen screen)
        {
            _screens[screen.Id] = screen;
        }

        public bool IsImplemented(AppScreen screen) => _screens.ContainsKey(screen);

        /// <summary>Smoothly brings the panel in front of <paramref name="head"/> at a comfortable height.</summary>
        public void RecallInFront(Transform head)
        {
            if (head == null) return;
            var forward = Vector3.ProjectOnPlane(head.forward, Vector3.up);
            if (forward.sqrMagnitude < 1e-4f) forward = Vector3.ProjectOnPlane(head.up, Vector3.up);
            forward.Normalize();
            _recallPosition = head.position + forward * recallDistance + Vector3.down * recallDrop;
            _recallRotation = Quaternion.LookRotation(forward, Vector3.up);
            _recalling = true;
        }

        // ------------------------------------------------------------------ screen switching

        private void OnScreenChanged(AppScreen previous, AppScreen current) => Show(current);

        private void Show(AppScreen id)
        {
            if (_active != null)
            {
                _active.OnHidden();
                _active = null;
            }

            for (var i = _content.childCount - 1; i >= 0; i--)
            {
                // Deactivate first: Destroy is deferred to end of frame, and inactive children are
                // ignored by the new screen's layout, so there is no one-frame overlap.
                var child = _content.GetChild(i).gameObject;
                child.SetActive(false);
                Destroy(child);
            }
            // Layout groups added by the previous screen live on the content object itself.
            foreach (var group in _content.GetComponents<LayoutGroup>()) DestroyImmediate(group);

            if (!_screens.TryGetValue(id, out var screen))
            {
                screen = ScreenCatalogue.TryGet(id, out var entry) ? new PendingFeatureScreen(entry) : null;
            }

            if (screen == null)
            {
                Debug.LogError($"[GemXpert] No screen registered for {id}.", this);
                return;
            }

            _header.gameObject.SetActive(screen.ShowHeader);
            _headerTitle.text = screen.Title.ToUpperInvariant();
            _backButton.gameObject.SetActive(_state.CanGoBack);
            ApplyContentInsets(screen.ShowHeader);

            screen.Build(_context, _content);
            _active = screen;
        }

        // ------------------------------------------------------------------ frame

        private const float HeaderHeight = 104f;
        private const float FooterHeight = 64f;

        private void BuildFrame()
        {
            _canvas = VRUIFactory.CreateWorldCanvas("GemXpert Main Panel", transform, panelSizeMm);
            var root = (RectTransform)_canvas.transform;

            var frame = VRUIFactory.CreateFramedPanel("Frame", root, UITheme.Backdrop, UITheme.Gold);
            VRUIFactory.Stretch(frame);

            // Header: [Back]  TITLE  [Showroom]
            _header = VRUIFactory.CreateRect("Header", frame);
            _header.anchorMin = new Vector2(0, 1);
            _header.anchorMax = new Vector2(1, 1);
            _header.pivot = new Vector2(0.5f, 1);
            _header.sizeDelta = new Vector2(-2 * UITheme.PanelPadding, HeaderHeight);
            _header.anchoredPosition = new Vector2(0, -8f);
            VRUIFactory.AddHorizontal(_header, 12f, null, TextAnchor.MiddleCenter);

            _backButton = VRUIFactory.CreateButton(_header, "< BACK", () => _state?.Back(), ButtonStyle.Quiet, 72f);
            VRUIFactory.SetPreferred(_backButton, 72f, 200f);

            _headerTitle = VRUIFactory.CreateText(_header, "", 34f, UITheme.TextPrimary, TextAlignmentOptions.Center, FontStyles.Bold);
            _headerTitle.characterSpacing = 12f;
            VRUIFactory.SetPreferred(_headerTitle, -1f, -1f, 1f);

            var home = VRUIFactory.CreateButton(_header, "SHOWROOM", () => _state?.Home(), ButtonStyle.Quiet, 72f);
            VRUIFactory.SetPreferred(home, 72f, 200f);

            var headerRule = VRUIFactory.CreateDivider(_header, 2f);
            var ruleRt = headerRule.rectTransform;
            ruleRt.GetComponent<LayoutElement>().ignoreLayout = true;
            ruleRt.anchorMin = new Vector2(0, 0);
            ruleRt.anchorMax = new Vector2(1, 0);
            ruleRt.sizeDelta = new Vector2(0, 2f);
            ruleRt.anchoredPosition = Vector2.zero;

            // Content
            _content = VRUIFactory.CreateRect("Content", frame);

            // Footer: brand mark + status
            var footer = VRUIFactory.CreateRect("Footer", frame);
            footer.anchorMin = new Vector2(0, 0);
            footer.anchorMax = new Vector2(1, 0);
            footer.pivot = new Vector2(0.5f, 0);
            footer.sizeDelta = new Vector2(-2 * UITheme.PanelPadding, FooterHeight);
            footer.anchoredPosition = new Vector2(0, 6f);
            VRUIFactory.AddHorizontal(footer, 12f, null, TextAnchor.MiddleLeft);

            var mark = VRUIFactory.CreateText(footer, "GEMXPERT", UITheme.CaptionSize, UITheme.Gold, TextAlignmentOptions.Left, FontStyles.Bold);
            mark.characterSpacing = 14f;
            VRUIFactory.SetPreferred(mark, -1f, 220f);

            _footerStatus = VRUIFactory.CreateText(footer, "", 20f, UITheme.TextMuted, TextAlignmentOptions.Right);
            VRUIFactory.SetPreferred(_footerStatus, -1f, -1f, 1f);
        }

        private void ApplyContentInsets(bool withHeader)
        {
            _content.anchorMin = Vector2.zero;
            _content.anchorMax = Vector2.one;
            _content.offsetMin = new Vector2(UITheme.BorderWidth, FooterHeight + 6f);
            _content.offsetMax = new Vector2(-UITheme.BorderWidth, withHeader ? -(HeaderHeight + 12f) : -UITheme.BorderWidth);
        }

        private void OnRuntimeChanged(RunMode mode)
        {
            RefreshFooter();
            // The instructions text depends on the run mode.
            if (_active != null && _active.Id == AppScreen.Instructions) Show(AppScreen.Instructions);
        }

        private void OnWearableChanged(string status) => RefreshFooter();

        private void RefreshFooter()
        {
            if (_footerStatus == null) return;
            _footerStatus.text = $"{GemXpertRuntime.Describe(GemXpertRuntime.ActiveRunMode)}   |   {GemXpertRuntime.WearableStatus}";
        }
    }
}
