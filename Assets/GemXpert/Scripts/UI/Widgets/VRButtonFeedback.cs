using System;
using UnityEngine;
using UnityEngine.EventSystems;

namespace GemXpert.UI
{
    /// <summary>
    /// Subtle press/hover response for VR buttons: a small scale "lift" on hover and a dip on press.
    /// Works with XR ray/poke pointers and the desktop mouse because both arrive as UI pointer events.
    /// <see cref="Hovered"/> and <see cref="Pressed"/> are raised so the XR layer can add haptics.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class VRButtonFeedback : MonoBehaviour,
        IPointerEnterHandler, IPointerExitHandler, IPointerDownHandler, IPointerUpHandler
    {
        public static event Action<GameObject> Hovered;
        public static event Action<GameObject> Pressed;

        [SerializeField] private float hoverScale = 1.025f;
        [SerializeField] private float pressScale = 0.975f;
        [SerializeField] private float speed = 18f;

        private Vector3 _baseScale = Vector3.one;
        private float _target = 1f;
        private bool _hover;

        private void Awake() => _baseScale = transform.localScale;

        private void OnDisable()
        {
            _hover = false;
            _target = 1f;
            transform.localScale = _baseScale;
        }

        private void Update()
        {
            var current = transform.localScale.x / Mathf.Max(_baseScale.x, 1e-5f);
            if (Mathf.Abs(current - _target) < 0.0005f) return;
            var next = Mathf.Lerp(current, _target, 1f - Mathf.Exp(-speed * Time.unscaledDeltaTime));
            transform.localScale = _baseScale * next;
        }

        public void OnPointerEnter(PointerEventData eventData)
        {
            _hover = true;
            _target = hoverScale;
            Hovered?.Invoke(gameObject);
        }

        public void OnPointerExit(PointerEventData eventData)
        {
            _hover = false;
            _target = 1f;
        }

        public void OnPointerDown(PointerEventData eventData)
        {
            _target = pressScale;
            Pressed?.Invoke(gameObject);
        }

        public void OnPointerUp(PointerEventData eventData) => _target = _hover ? hoverScale : 1f;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Hovered = null;
            Pressed = null;
        }
    }
}
