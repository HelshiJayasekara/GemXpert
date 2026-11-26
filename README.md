# GemXpert – Immersive VR Gemstone & Jewellery Visualisation

Customers enter a virtual jewellery showroom, choose a ring, pendant, necklace or bracelet, fit a gemstone into it, customise the stone's cut,
size, position and the metal, and inspect the result on their own virtual hand. An optional ESP32 + IMU
finger wearable adds orientation and gesture input.

**Target:** Unity 6 LTS · URP · OpenXR (Meta Quest) · XR Interaction Toolkit 3 · Input System
**Runs without a headset:** Desktop preview mode and the XR Device Simulator.

## Status

| Phase | Scope | State |
|---|---|---|
| 1 | Project setup, showroom scene builder, VR UI framework, navigation, run modes, catalogue schema | **Code written, awaiting first compile** (Unity was not installed when this was written) |
| 2 | Blender ring & gemstone models | **Done in Blender**: 5 rings, 6 cuts, materials, FBX/GLB exports, Cycles renders ([pipeline](Documentation/Architecture/ASSET_PIPELINE.md)). Unity import not yet checked |
| Web | GemXpert Studio web app (`Web/`, Vite + React + TypeScript + three.js), deployable to Vercel at gemxpert.4axismedia.com ([deploy guide](Documentation/Deployment/VERCEL_DEPLOY.md)) | **Working** locally: all screens, ring on a clean rigged hand, Bluetooth wearable. Replaces `Prototype/Interface` (kept for reference) |
| Jewellery | Pendants, necklaces, bracelets and earring pairs in the web app, built in Blender with the ring mount rules and shown on their own in the 3D view ([details](Documentation/Architecture/JEWELLERY.md)) | **Working in `Web/`**: 18 pieces (7 pendants, 3 necklaces, 2 bracelets, 6 earring pairs). Not in Unity yet |
| Extra | Design a ring from a photo: Claude reads the design, a JS generator rebuilds it; `build_custom.py` builds the same spec for Unity ([ring spec](Documentation/Architecture/RING_SPEC.md)) | **Working** in the interface. Runs through claude.ai on the published page, or through `Tools/serve_interface.py` with your own API key on the local copy. A real Claude answer not yet seen |
| 3 | Ring / gemstone / metal / fit systems | Not started |
| 4 | Virtual hand, ring-on-finger, inspection | Not started |
| 5 | ESP32 wearable layer + mock simulator | **Started**: ESP32 + MPU6050 firmware streams orientation and taps over Bluetooth LE; the web app's ring and hand follow it ([setup & wiring](Documentation/Hardware/ESP32_WEARABLE_SETUP.md)). Unity transport not started |
| 6 | Saved designs, polish, performance | Not started |

## Quick start

1. Install **Unity 6 LTS** through Unity Hub (no extra modules needed for desktop).
2. Unity Hub → Add project from disk → this folder.
3. In Unity: **GemXpert ▸ Setup ▸ Run Full Setup** (installs packages, imports samples, configures URP, builds the scene).
4. Open `Assets/GemXpert/Scenes/MainShowroom/MainShowroom.unity` → Play.
   Hold right mouse to look, WASD to walk, click panel buttons, **M** recalls the menu.

Full test procedure: [Documentation/Testing/PHASE1_TESTING.md](Documentation/Testing/PHASE1_TESTING.md)

## Documentation

* [Pendants, necklaces and bracelets](Documentation/Architecture/JEWELLERY.md)
* [Environment report](Documentation/Architecture/ENVIRONMENT_REPORT.md) – what is installed, what is missing
* [Architecture & implementation plan](Documentation/Architecture/IMPLEMENTATION_PLAN.md)
* [OpenXR / Quest setup](Documentation/Architecture/OPENXR_QUEST_SETUP.md)
* [Hardware tests still outstanding](Documentation/Testing/HARDWARE_TESTS_REMAINING.md)

## Layout

```
Assets/GemXpert/   Unity content (Scripts, Configurations, Scenes, Materials, Prefabs, Tests ...)
Blender/           Scripts (model generators), Source (.blend), Exports (FBX/GLB)
Web/               GemXpert Studio web app (Vite + React + TypeScript), deployed on Vercel
Firmware/ESP32/    Wearable firmware, Bluetooth LE (Phase 5)
Tools/BleBridge/   macOS BLE -> UDP bridge for the editor (Phase 5)
Documentation/     Architecture, Hardware, Testing
```
