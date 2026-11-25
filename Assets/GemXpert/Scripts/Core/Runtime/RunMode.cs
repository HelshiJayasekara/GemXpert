namespace GemXpert.Core
{
    /// <summary>How the experience is being driven on this machine.</summary>
    public enum RunMode
    {
        /// <summary>Pick automatically: headset if an XR display is running, otherwise Desktop.</summary>
        Auto = 0,
        /// <summary>A real OpenXR headset (e.g. Meta Quest) is rendering.</summary>
        HeadsetXR = 1,
        /// <summary>XR Interaction Toolkit Device Simulator: simulated HMD, controllers and hands.</summary>
        XRDeviceSimulator = 2,
        /// <summary>Mouse + keyboard preview of the same world-space VR scene (no XR devices).</summary>
        Desktop = 3,
    }
}
