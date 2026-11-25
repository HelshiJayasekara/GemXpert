using GemXpert.UI;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using UnityEngine.XR.Interaction.Toolkit.UI;

namespace GemXpert.Interaction
{
    /// <summary>
    /// Makes every GemXpert canvas usable by XR rays/pokes AND the desktop mouse:
    ///  * one EventSystem with XRUIInputModule (which also handles mouse input),
    ///  * TrackedDeviceGraphicRaycaster on each registered canvas (XR pointers),
    ///  * the existing GraphicRaycaster stays for the mouse in Desktop mode.
    /// </summary>
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(-800)]
    public sealed class XRCanvasSetup : MonoBehaviour
    {
        private void Awake()
        {
            EnsureEventSystem();
            GemXpertCanvasRegistry.CanvasRegistered += Configure;
        }

        private void Start()
        {
            foreach (var canvas in GemXpertCanvasRegistry.All) Configure(canvas);
        }

        private void OnDestroy()
        {
            GemXpertCanvasRegistry.CanvasRegistered -= Configure;
        }

        private static void Configure(Canvas canvas)
        {
            if (canvas == null) return;
            if (canvas.GetComponent<TrackedDeviceGraphicRaycaster>() == null)
            {
                canvas.gameObject.AddComponent<TrackedDeviceGraphicRaycaster>();
            }
            if (canvas.GetComponent<GraphicRaycaster>() == null)
            {
                canvas.gameObject.AddComponent<GraphicRaycaster>();
            }
            if (canvas.worldCamera == null) canvas.worldCamera = Camera.main;
        }

        private static void EnsureEventSystem()
        {
            var eventSystem = FindFirstObjectByType<EventSystem>();
            if (eventSystem == null)
            {
                eventSystem = new GameObject("EventSystem", typeof(EventSystem)).GetComponent<EventSystem>();
            }

            // Remove modules that would fight XRUIInputModule for pointer input.
            foreach (var module in eventSystem.GetComponents<BaseInputModule>())
            {
                if (module is XRUIInputModule) continue;
                Debug.Log($"[GemXpert] Replacing {module.GetType().Name} with XRUIInputModule.");
                Destroy(module);
            }

            if (eventSystem.GetComponent<XRUIInputModule>() == null)
            {
                eventSystem.gameObject.AddComponent<XRUIInputModule>();
            }
        }
    }
}
