using System;
using System.Collections.Generic;
using UnityEngine;

namespace GemXpert.UI
{
    /// <summary>
    /// Every world-space canvas GemXpert creates is registered here so the XR layer can add
    /// tracked-device raycasters without the UI assembly depending on XR packages.
    /// </summary>
    public static class GemXpertCanvasRegistry
    {
        private static readonly List<Canvas> Canvases = new List<Canvas>();

        public static event Action<Canvas> CanvasRegistered;

        public static IReadOnlyList<Canvas> All
        {
            get
            {
                Canvases.RemoveAll(c => c == null);
                return Canvases;
            }
        }

        public static void Register(Canvas canvas)
        {
            if (canvas == null || Canvases.Contains(canvas)) return;
            Canvases.Add(canvas);
            CanvasRegistered?.Invoke(canvas);
        }

        public static void Unregister(Canvas canvas) => Canvases.Remove(canvas);

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Canvases.Clear();
            CanvasRegistered = null;
        }
    }
}
