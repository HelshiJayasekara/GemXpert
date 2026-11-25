# OpenXR / Meta Quest Configuration (for when a headset is added)

The automated setup installs XR Plug-in Management and OpenXR but deliberately does **not** script the
Android/OpenXR settings. Those settings live on the Android build target, which needs the Android Build
Support module (not installed, because no headset is in use and disk space is tight), and they can't be verified without a headset.
These are the exact manual steps.

1. Unity Hub → Installs → your Unity 6 editor → **Add modules → Android Build Support** (+ OpenJDK, Android SDK & NDK Tools). ~4–5 GB.
2. **File ▸ Build Profiles** → Android → *Switch Platform*.
3. **Edit ▸ Project Settings ▸ XR Plug-in Management** → Android tab → tick **OpenXR**.
4. **XR Plug-in Management ▸ OpenXR** (Android tab):
   * Interaction Profiles: **Oculus Touch Controller Profile**, **Hand Interaction Profile**.
   * OpenXR Feature Groups: **Meta Quest Support** (tick *Meta Quest Support* feature).
   * Features: **Hand Tracking Subsystem** and **Meta Hand Tracking Aim** (from XR Hands).
5. Fix anything flagged in **XR Plug-in Management ▸ Project Validation**.
6. **Player ▸ Android**: Minimum API Level 32, Scripting Backend **IL2CPP**, Target Architecture **ARM64** only,
   Graphics API **Vulkan** (or OpenGLES3), Texture compression **ASTC**.
7. URP asset (already created by setup): MSAA 4x, HDR off. Keep these for Quest.
8. Enable Developer Mode on the headset (Meta Horizon app), connect USB, **Build And Run**.

Standalone macOS has no OpenXR runtime. On a Mac the Standalone tab stays without a loader, and GemXpert
runs in Desktop or XR Device Simulator mode.
