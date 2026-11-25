using System.Collections;
using GemXpert.Core;
using GemXpert.UI;
using Unity.XR.CoreUtils;
using UnityEngine;
using UnityEngine.InputSystem.XR;

namespace GemXpert.Interaction
{
    /// <summary>
    /// Decides how the experience is driven and configures the rig accordingly:
    ///  * HeadsetXR         – a real OpenXR display is running: headset tracking, simulator and desktop off.
    ///  * XRDeviceSimulator – XRI Device Simulator drives simulated HMD/controllers/hands.
    ///  * Desktop           – no XR devices: tracked-pose drivers off, mouse/keyboard preview on.
    /// Auto picks HeadsetXR when an XR display is running, otherwise <see cref="noHeadsetFallback"/>.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class RunModeController : MonoBehaviour
    {
        [SerializeField] private RunMode requestedMode = RunMode.Auto;

        [Tooltip("Used by Auto when no headset is detected. Desktop is the friendliest for demos; " +
                 "XRDeviceSimulator exercises the real XR interactors.")]
        [SerializeField] private RunMode noHeadsetFallback = RunMode.Desktop;

        [SerializeField] private XROrigin xrOrigin;
        [Tooltip("Scene instance of the XRI 'XR Device Simulator' prefab (kept inactive until needed).")]
        [SerializeField] private GameObject deviceSimulator;
        [SerializeField] private DesktopPreviewController desktopController;
        [SerializeField] private ScreenRouter screenRouter;

        public RunMode ActiveMode { get; private set; } = RunMode.Auto;

        public void Configure(XROrigin origin, GameObject simulator, DesktopPreviewController desktop, ScreenRouter router)
        {
            xrOrigin = origin;
            deviceSimulator = simulator;
            desktopController = desktop;
            screenRouter = router;
        }

        private void Awake()
        {
            // Nothing XR-simulated may run before the mode is decided.
            if (deviceSimulator != null && requestedMode != RunMode.XRDeviceSimulator) deviceSimulator.SetActive(false);
            if (desktopController != null) desktopController.enabled = false;
        }

        private IEnumerator Start()
        {
            // Give the XR loader one frame to start a display subsystem if a headset is attached.
            yield return null;
            Apply(Resolve());
        }

        private RunMode Resolve()
        {
            if (requestedMode != RunMode.Auto) return requestedMode;
            if (GemXpertRuntime.IsXRDisplayRunning()) return RunMode.HeadsetXR;
            return noHeadsetFallback == RunMode.Auto ? RunMode.Desktop : noHeadsetFallback;
        }

        public void Apply(RunMode mode)
        {
            if (mode == RunMode.XRDeviceSimulator && deviceSimulator == null)
            {
                Debug.LogWarning("[GemXpert] XR Device Simulator requested but none is assigned. Falling back to Desktop. " +
                                 "Run GemXpert > Setup > Run Full Setup to import the simulator sample, then rebuild the scene.");
                mode = RunMode.Desktop;
            }

            var desktop = mode == RunMode.Desktop;

            if (deviceSimulator != null) deviceSimulator.SetActive(mode == RunMode.XRDeviceSimulator);
            SetTrackedPoseDrivers(!desktop);
            if (desktopController != null)
            {
                desktopController.enabled = desktop;
                desktopController.RecallMenuRequested -= RecallMenu;
                if (desktop) desktopController.RecallMenuRequested += RecallMenu;
            }

            ActiveMode = mode;
            GemXpertRuntime.SetRunMode(mode);
            Debug.Log($"[GemXpert] Run mode: {GemXpertRuntime.Describe(mode)}");
        }

        /// <summary>Brings the main panel in front of the user's head.</summary>
        public void RecallMenu()
        {
            if (screenRouter == null) return;
            var cam = xrOrigin != null && xrOrigin.Camera != null ? xrOrigin.Camera : Camera.main;
            if (cam != null) screenRouter.RecallInFront(cam.transform);
        }

        private void SetTrackedPoseDrivers(bool enabledState)
        {
            if (xrOrigin == null) return;
            // In Desktop mode nothing is tracked; tracked pose drivers would pin the camera to the origin.
            foreach (var driver in xrOrigin.GetComponentsInChildren<TrackedPoseDriver>(true))
            {
                driver.enabled = enabledState;
            }
        }
    }
}
