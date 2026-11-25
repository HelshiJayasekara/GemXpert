using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR;

namespace GemXpert.Core
{
    /// <summary>
    /// Small, dependency-free runtime facts shared between assemblies (run mode, wearable status).
    /// The XR/Interaction assembly writes these values; UI reads them.
    /// </summary>
    public static class GemXpertRuntime
    {
        private static readonly List<XRDisplaySubsystem> DisplayBuffer = new List<XRDisplaySubsystem>();

        public static RunMode ActiveRunMode { get; private set; } = RunMode.Auto;
        public static event Action<RunMode> RunModeChanged;

        /// <summary>Human-readable wearable status. Phase 5 replaces the default with live connection state.</summary>
        public static string WearableStatus { get; private set; } = "Wearable: not connected";
        public static event Action<string> WearableStatusChanged;

        public static void SetRunMode(RunMode mode)
        {
            if (ActiveRunMode == mode) return;
            ActiveRunMode = mode;
            RunModeChanged?.Invoke(mode);
        }

        public static void SetWearableStatus(string status)
        {
            if (WearableStatus == status) return;
            WearableStatus = status;
            WearableStatusChanged?.Invoke(status);
        }

        /// <summary>True when an XR display subsystem (a real headset runtime) is rendering.</summary>
        public static bool IsXRDisplayRunning()
        {
            SubsystemManager.GetSubsystems(DisplayBuffer);
            foreach (var display in DisplayBuffer)
            {
                if (display != null && display.running) return true;
            }
            return false;
        }

        public static string Describe(RunMode mode)
        {
            switch (mode)
            {
                case RunMode.HeadsetXR: return "VR headset";
                case RunMode.XRDeviceSimulator: return "XR Device Simulator";
                case RunMode.Desktop: return "Desktop preview";
                default: return "Detecting...";
            }
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            // Supports "Enter Play Mode Options" with domain reload disabled.
            ActiveRunMode = RunMode.Auto;
            RunModeChanged = null;
            WearableStatus = "Wearable: not connected";
            WearableStatusChanged = null;
        }
    }
}
