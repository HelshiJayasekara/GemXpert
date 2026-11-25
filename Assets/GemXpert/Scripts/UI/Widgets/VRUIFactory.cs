using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

namespace GemXpert.UI
{
    public enum ButtonStyle
    {
        /// <summary>Gold fill, dark text: the one main action on a screen.</summary>
        Primary,
        /// <summary>Dark fill with a gold outline: secondary actions.</summary>
        Secondary,
        /// <summary>Text-only, for header actions (Back / Home).</summary>
        Quiet,
    }

    /// <summary>
    /// Builds GemXpert UI elements in code with consistent styling.
    /// World-space canvases use 1 canvas pixel = 1 millimetre, so layout numbers are physical sizes.
    /// </summary>
    public static class VRUIFactory
    {
        public const float MetresPerPixel = 0.001f;

        // ------------------------------------------------------------------ canvases

        public static Canvas CreateWorldCanvas(string name, Transform parent, Vector2 sizeMm)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            var uiLayer = LayerMask.NameToLayer("UI");
            if (uiLayer >= 0) go.layer = uiLayer;

            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            rt.sizeDelta = sizeMm;
            rt.localPosition = Vector3.zero;
            rt.localRotation = Quaternion.identity;
            rt.localScale = Vector3.one * MetresPerPixel;

            var canvas = go.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.WorldSpace;
            canvas.worldCamera = Camera.main;
            canvas.sortingOrder = 10;

            var scaler = go.GetComponent<CanvasScaler>();
            scaler.dynamicPixelsPerUnit = 4f;
            scaler.referencePixelsPerUnit = 100f;

            GemXpertCanvasRegistry.Register(canvas);
            return canvas;
        }

        // ------------------------------------------------------------------ primitives

        public static RectTransform CreateRect(string name, Transform parent)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.layer = parent.gameObject.layer;
            var rt = (RectTransform)go.transform;
            rt.SetParent(parent, false);
            return rt;
        }

        public static void Stretch(RectTransform rt, float inset = 0f)
        {
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = new Vector2(inset, inset);
            rt.offsetMax = new Vector2(-inset, -inset);
        }

        public static Image CreateRoundedImage(string name, Transform parent, Color color, float cornerPx = UITheme.CornerRadius)
        {
            var rt = CreateRect(name, parent);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = RoundedSprite.Get();
            img.type = Image.Type.Sliced;
            // Sprite corners are 24 px at PPU 100; scale them to the requested radius.
            img.pixelsPerUnitMultiplier = 24f / Mathf.Max(1f, cornerPx);
            img.color = color;
            return img;
        }

        /// <summary>Rounded panel with a thin gold border (border image + inset fill).</summary>
        public static RectTransform CreateFramedPanel(string name, Transform parent, Color fill, Color border)
        {
            var frame = CreateRoundedImage(name, parent, border, UITheme.CornerRadius + UITheme.BorderWidth);
            frame.raycastTarget = true; // blocks rays from passing through the panel
            var inner = CreateRoundedImage("Fill", frame.transform, fill);
            inner.raycastTarget = false;
            Stretch(inner.rectTransform, UITheme.BorderWidth);
            return frame.rectTransform;
        }

        public static Image CreateDivider(Transform parent, float thickness = 2f, Color? color = null)
        {
            var rt = CreateRect("Divider", parent);
            var img = rt.gameObject.AddComponent<Image>();
            img.color = color ?? new Color(UITheme.Gold.r, UITheme.Gold.g, UITheme.Gold.b, 0.55f);
            img.raycastTarget = false;
            var le = rt.gameObject.AddComponent<LayoutElement>();
            le.preferredHeight = thickness;
            le.minHeight = thickness;
            le.flexibleWidth = 1f;
            return img;
        }

        public static TextMeshProUGUI CreateText(
            Transform parent,
            string text,
            float size,
            Color color,
            TextAlignmentOptions alignment = TextAlignmentOptions.Left,
            FontStyles style = FontStyles.Normal)
        {
            var rt = CreateRect("Text", parent);
            var tmp = rt.gameObject.AddComponent<TextMeshProUGUI>();
            tmp.text = text;
            tmp.fontSize = size;
            tmp.color = color;
            tmp.alignment = alignment;
            tmp.fontStyle = style;
            tmp.textWrappingMode = TextWrappingModes.Normal;
            tmp.raycastTarget = false;
            return tmp;
        }

        public static LayoutElement SetPreferred(Component c, float height = -1f, float width = -1f, float flexibleWidth = -1f, float flexibleHeight = -1f)
        {
            // Explicit Unity null check: '??' would not detect the editor's "fake null" component.
            var le = c.GetComponent<LayoutElement>();
            if (le == null) le = c.gameObject.AddComponent<LayoutElement>();
            if (height >= 0) { le.preferredHeight = height; le.minHeight = height; }
            if (width >= 0) { le.preferredWidth = width; le.minWidth = width; }
            if (flexibleWidth >= 0) le.flexibleWidth = flexibleWidth;
            if (flexibleHeight >= 0) le.flexibleHeight = flexibleHeight;
            return le;
        }

        // ------------------------------------------------------------------ layout groups

        public static VerticalLayoutGroup AddVertical(RectTransform rt, float spacing = UITheme.Spacing, RectOffset padding = null,
            TextAnchor align = TextAnchor.UpperCenter)
        {
            var v = rt.gameObject.AddComponent<VerticalLayoutGroup>();
            v.spacing = spacing;
            v.padding = padding ?? new RectOffset(0, 0, 0, 0);
            v.childAlignment = align;
            // Children size to their preferred width (capped at the panel width) so fixed-width
            // buttons stay centred. Use LayoutElement.flexibleWidth = 1 for full-width children.
            v.childControlWidth = true;
            v.childControlHeight = true;
            v.childForceExpandWidth = false;
            v.childForceExpandHeight = false;
            return v;
        }

        public static HorizontalLayoutGroup AddHorizontal(RectTransform rt, float spacing = UITheme.Spacing, RectOffset padding = null,
            TextAnchor align = TextAnchor.MiddleCenter)
        {
            var h = rt.gameObject.AddComponent<HorizontalLayoutGroup>();
            h.spacing = spacing;
            h.padding = padding ?? new RectOffset(0, 0, 0, 0);
            h.childAlignment = align;
            h.childControlWidth = true;
            h.childControlHeight = true;
            h.childForceExpandWidth = false;
            h.childForceExpandHeight = true;
            return h;
        }

        // ------------------------------------------------------------------ buttons

        public static Button CreateButton(Transform parent, string label, UnityAction onClick, ButtonStyle style = ButtonStyle.Secondary,
            float height = UITheme.ButtonHeight)
        {
            Image background;
            RectTransform root;

            if (style == ButtonStyle.Secondary)
            {
                root = CreateFramedPanel($"Button_{label}", parent, UITheme.Surface, UITheme.GoldDeep);
                background = root.GetComponent<Image>();
            }
            else
            {
                background = CreateRoundedImage($"Button_{label}", parent,
                    style == ButtonStyle.Primary ? UITheme.Gold : new Color(0, 0, 0, 0));
                root = background.rectTransform;
            }

            var button = root.gameObject.AddComponent<Button>();
            button.targetGraphic = style == ButtonStyle.Secondary ? root.Find("Fill").GetComponent<Image>() : background;
            button.navigation = new Navigation { mode = Navigation.Mode.None };
            var colors = button.colors;
            colors.fadeDuration = 0.08f;
            colors.colorMultiplier = 1f;
            switch (style)
            {
                case ButtonStyle.Primary:
                    colors.normalColor = Color.white;
                    colors.highlightedColor = new Color(1.12f, 1.1f, 1.04f, 1f);
                    colors.pressedColor = new Color(0.8f, 0.78f, 0.72f, 1f);
                    break;
                case ButtonStyle.Secondary:
                    // Tint multiplies the dark fill colour, so >1 values brighten it on hover.
                    colors.normalColor = Color.white;
                    colors.highlightedColor = new Color(1.6f, 1.55f, 1.45f, 1f);
                    colors.pressedColor = new Color(0.85f, 0.8f, 0.7f, 1f);
                    break;
                default:
                    colors.normalColor = Color.white;
                    colors.highlightedColor = new Color(1f, 1f, 1f, 1f);
                    colors.pressedColor = new Color(0.8f, 0.8f, 0.8f, 1f);
                    break;
            }
            colors.selectedColor = colors.normalColor;
            colors.disabledColor = new Color(0.5f, 0.5f, 0.5f, 0.5f);
            button.colors = colors;

            var text = CreateText(root, label, UITheme.ButtonSize,
                style == ButtonStyle.Primary ? UITheme.TextOnGold : (style == ButtonStyle.Quiet ? UITheme.GoldBright : UITheme.TextPrimary),
                TextAlignmentOptions.Center,
                style == ButtonStyle.Primary ? FontStyles.Bold : FontStyles.Normal);
            text.characterSpacing = 4f;
            text.textWrappingMode = TextWrappingModes.NoWrap;
            Stretch(text.rectTransform, 8f);

            SetPreferred(root, height);
            root.gameObject.AddComponent<VRButtonFeedback>();
            if (onClick != null) button.onClick.AddListener(onClick);
            return button;
        }

        /// <summary>A catalogue-style tile: title, one-line description and an optional status badge.</summary>
        public static Button CreateTile(Transform parent, string title, string description, string badge, UnityAction onClick)
        {
            var root = CreateFramedPanel($"Tile_{title}", parent, UITheme.Surface, UITheme.GoldDeep);
            var fill = root.Find("Fill").GetComponent<Image>();

            var button = root.gameObject.AddComponent<Button>();
            button.targetGraphic = fill;
            button.navigation = new Navigation { mode = Navigation.Mode.None };
            var colors = button.colors;
            colors.normalColor = Color.white;
            colors.highlightedColor = new Color(1.6f, 1.55f, 1.45f, 1f);
            colors.pressedColor = new Color(0.85f, 0.8f, 0.7f, 1f);
            colors.selectedColor = Color.white;
            colors.fadeDuration = 0.08f;
            button.colors = colors;

            var content = CreateRect("Content", root);
            Stretch(content, 26f);
            AddVertical(content, 8f, null, TextAnchor.UpperLeft);

            var titleText = CreateText(content, title, 32f, UITheme.GoldBright, TextAlignmentOptions.TopLeft, FontStyles.Bold);
            SetPreferred(titleText, 42f);
            var descText = CreateText(content, description, UITheme.CaptionSize, UITheme.TextMuted, TextAlignmentOptions.TopLeft);
            SetPreferred(descText, -1f, -1f, -1f, 1f);
            if (!string.IsNullOrEmpty(badge))
            {
                var badgeText = CreateText(content, badge.ToUpperInvariant(), 18f, UITheme.Warning, TextAlignmentOptions.BottomLeft, FontStyles.Bold);
                badgeText.characterSpacing = 6f;
                SetPreferred(badgeText, 26f);
            }

            root.gameObject.AddComponent<VRButtonFeedback>();
            if (onClick != null) button.onClick.AddListener(onClick);
            return button;
        }
    }
}
