# GemXpert – Architecture & Implementation Plan

## 1. Key technical decisions

| Topic | Decision | Why |
|---|---|---|
| Engine | Unity 6 LTS, URP, C# | Quest-class performance, OpenXR support, XR Interaction Toolkit 3.x |
| Input | Unity Input System only | Required by XRI 3; one input path for XR, simulator and desktop |
| XR | XR Plug-in Management + OpenXR (Meta Quest feature group on Android) | Vendor-neutral; Quest is the target headset |
| Interaction | XR Interaction Toolkit 3.x Starter Assets rig + XR Device Simulator | Proven rig and locomotion; the simulator lets us test without a headset |
| Hands | XR Hands package (OpenXR hand tracking) with a simulated-hand fallback | Headset tracks hand position; the ESP32 only adds orientation and gestures |
| No-headset operation | Three run modes: `HeadsetXR`, `XRDeviceSimulator`, `Desktop` (`Auto` chooses one) | No headset is available for development |
| UI | World-space canvases (1 px = 1 mm) built in code, `TrackedDeviceGraphicRaycaster` for XR rays + `GraphicRaycaster` for the mouse | Readable, consistent, works with every run mode |
| Text | TextMeshPro (SDF) | Sharp text at VR distances |
| Model format into Unity | **FBX** (plus GLB copies for review) | Unity imports FBX natively with no extra package. Materials are authored in Unity URP anyway, because neither FBX nor glTF carry Blender transmission shaders faithfully into URP |
| Units | 1 Unity unit = 1 m; jewellery modelled at real size (a ring ≈ 20 mm). Catalogue sizes are in **mm** | Correct on-finger scale; inspection uses a magnified display stand |
| Catalogue | JSON in `Configurations/Resources/Catalogue/` loaded with `JsonUtility` | Editable specs, no code change to add a gem or ring |
| Assemblies | One `.asmdef` per subsystem. Assemblies that need XR packages are gated by `versionDefines` + `defineConstraints` | A fresh project compiles cleanly *before* packages are installed, then everything compiles once they are |
| BLE | `IWearableTransport` abstraction with: Mock (in-Unity simulator), UDP bridge (macOS editor ← Python `bleak` bridge), Android BLE plugin (Quest, later) | Unity has no built-in BLE API; macOS editor and Quest need different native paths |

## 2. Project structure

```
<repo root = Unity project root>
├─ Assets/GemXpert/
│  ├─ Scripts/
│  │  ├─ Core/          GemXpert.Core – app state, navigation, catalogue schema & loader, runtime info (no package deps)
│  │  ├─ UI/            GemXpert.UI – theme, panel/widget factory, screens, router
│  │  ├─ Interaction/   GemXpert.Interaction – run modes, desktop preview, XR canvas wiring (needs XRI)
│  │  ├─ Jewellery/     Phase 3 – model manager, material manager
│  │  ├─ Gemstones/     Phase 3 – replacement manager, fit manager
│  │  ├─ HandTracking/  Phase 4 – virtual hand manager, ring-on-finger attachment
│  │  ├─ Hardware/      Phase 5 – wearable input abstraction, BLE transports, filters, gestures
│  │  ├─ Saving/        Phase 6 – design manager (save/restore)
│  │  └─ Editor/        GemXpert.Editor (+ Bootstrap) – project setup, URP config, scene builder
│  ├─ Configurations/Resources/Catalogue/   rings.json, gemstones.json, shapes.json, metals.json
│  ├─ Models/{Rings,Gemstones}/             FBX imported from Blender/Exports
│  ├─ Materials/{Metals,Gemstones,Environment}/
│  ├─ Prefabs/{Rings,Gemstones,UI}/
│  ├─ Scenes/MainShowroom/
│  ├─ Settings/Rendering/                   URP assets
│  ├─ Textures/  Audio/
│  └─ Tests/EditMode/
├─ Blender/
│  ├─ Scripts/   headless generator scripts (source of truth for the models)
│  ├─ Source/    .blend files
│  └─ Exports/   FBX + GLB
├─ Firmware/ESP32/   PlatformIO project (Phase 5)
├─ Tools/BleBridge/  Python BLE→UDP bridge for the macOS editor (Phase 5)
└─ Documentation/{Architecture,Hardware,Testing}/
```

## 3. Runtime architecture

```
                ┌──────────────────────── GemXpert Systems (scene object) ────────────────────────┐
                │ AppStateController ──(ScreenChanged)──► ScreenRouter ──► UIScreen implementations │
                │        ▲                                     │                                   │
                │        │ NavigateTo/Back/Home                 └─ GemXpertCanvasRegistry ─► XRCanvasSetup (adds XR raycaster)
                │ CatalogueService (JSON) ─────────► screens / jewellery managers (Phase 3)          │
                │ RunModeController ─► XR Device Simulator | DesktopPreviewController | headset      │
                └──────────────────────────────────────────────────────────────────────────────────┘
Phase 3:  JewelleryModelManager ─► RingInstance(mount points) ◄─ GemstoneReplacementManager ◄─ GemstoneFitManager
          JewelleryMaterialManager (metal renderers only)
Phase 4:  VirtualHandManager (XR Hands joints | simulated hand) ─► FingerRingAttachment
Phase 5:  IWearableInput ◄─ WearableInputService ◄─ IWearableTransport {Mock, UdpBridge, AndroidBle}
          └─ SensorFilter (complementary/Madgwick) ─► OrientationEstimator ─► GestureDetector
Phase 6:  DesignManager (JSON in Application.persistentDataPath)
```

The rule: jewellery visualisation never references hardware or BLE types. It only consumes
`IWearableInput` (orientation + gesture events), which the mock satisfies.

## 4. Gemstone mounting model (core feature)

* Every ring prefab contains one or more empties named `GemMount_<id>` (e.g. `GemMount_Center`, `GemMount_SideL`).
  The empty's transform is the gem's **girdle centre**. Local +Y points out of the table, +Z runs along the length of the stone.
* `rings.json` describes each mount: allowed shapes, min/max length & width (mm), max depth, and an
  adjustable offset range (mm). If the model has the empty, the model wins. The JSON position is a fallback.
* Gem meshes are modelled at a **unit size** (1 mm length along Z), so scaling by the requested
  `length × width × depth` in mm gives exact dimensions without rebuilding meshes.
* `GemstoneFitManager` returns `Fits` / `Warning` / `DoesNotFit` with a reason (shape unsupported,
  too long, too wide, too deep). The UI shows it, and an invalid combination is never silently mounted.
* Version 1 uses predefined compatibility (shape lists + size ranges per mount). It does not claim universal fit.

## 5. Phases and acceptance criteria

| Phase | Deliverables | Done when |
|---|---|---|
| **1** Setup & navigation | Packages + URP + Input System + OpenXR (config), showroom scene builder, VR UI framework, Welcome / Instructions / Showroom hub, run modes, catalogue schema + JSON, EditMode tests | Project compiles with zero errors. Play mode in Desktop and Simulator modes shows the showroom, every navigation button works, tests pass |
| **2** Blender assets | Generator scripts, 4 ring models (solitaire, halo, three-stone, bezel) plus the prong variant, 6 gem cuts, metal & gem material definitions, FBX/GLB exports, Unity import + scale check | Assets open in Blender, import into Unity at correct mm scale with mounts present, and look correct in a render |
| **3** Jewellery systems | Model, replacement, material and fit managers. Ring / gem / customisation screens | Any valid ring+gem+shape+size+metal combination works. Invalid combinations are flagged |
| **4** Hands & inspection | VirtualHandManager, finger attachment, simulated hand, rotate/zoom/close-up/reset, compare | Ring stays on the finger as the simulated hand moves; inspection controls work |
| **5** Wearable | Input abstraction, mock simulator UI, UDP bridge, Android BLE plugin skeleton, ESP32 firmware, documented protocol | Mock wearable rotates the hand and triggers gestures. Firmware compiles. Real-hardware tests listed |
| **6** Saving & polish | DesignManager, saved-designs screen, showroom polish, performance pass, end-to-end test | Save → quit → reload restores a design. Performance budget checked in the editor profiler |

## 6. Known limitations and compatibility concerns (stated up front)

1. **No headset**: hand tracking, real controller feel, Quest frame-rate and passthrough cannot be verified here. Simulator results are not a substitute for an on-device test.
2. **macOS has no OpenXR runtime**: XR Play mode on this Mac is only possible through the XR Device Simulator.
3. **Gem optics in real time**: URP has no true refraction or dispersion. Gems use a tuned transparent/reflective material, a reflection probe and (Phase 6) an optional fake-dispersion shader. They will look convincing, not physically exact.
4. **BLE**: Unity has no cross-platform BLE API. The macOS editor uses a Python bridge, and Quest needs a native Android plugin. Whether Quest OS allows a third-party app to use a custom BLE GATT peripheral must be **verified on a real Quest**.
5. **IMU**: an MPU6050 gives orientation (with yaw drift unless a magnetometer is added) and gestures, **not** absolute position.
6. **Disk**: ~23 GB free; enough for the desktop setup, tight if the Android module is added later.
