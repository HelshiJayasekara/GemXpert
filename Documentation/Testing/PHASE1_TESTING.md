# Phase 1 – Setup, Showroom & Navigation: How to Test

> **Status: written, NOT yet compiled.** Unity was not installed when Phase 1 was written, so
> none of the C# below has been through the Unity compiler yet. The first task once the Editor is installed
> is to run setup, fix any compile errors and run these tests. This file will be updated with real results.

## 0. Prerequisites

* Unity 6 LTS installed through Unity Hub (no extra modules needed).
* Signed in to Unity Hub with an activated Personal licence.

## 1. Open the project and run setup

1. Unity Hub → **Projects → Add → Add project from disk** → choose this repository's root folder
   (the one containing `Assets/`). Open it with your Unity 6 LTS editor.
   Unity creates `Packages/` and `ProjectSettings/` on first open.
2. Menu **GemXpert ▸ Setup ▸ Run Full Setup**. It will:
   install URP, Input System, XR Management, OpenXR, XR Interaction Toolkit, XR Hands → import the XRI
   *Starter Assets* and *XR Device Simulator* samples → import TextMeshPro essentials → set the Input System as active
   input handling → create and assign the URP asset → build `Scenes/MainShowroom/MainShowroom.unity`.
   Progress is logged in the Console with the `[GemXpert Setup]` prefix.
3. If the log says **"RESTART the editor"**, close and reopen the project (needed once, when the input handling changes).

Batch alternative (once the Editor path is known):

```bash
"/Applications/Unity/Hub/Editor/<version>/Unity.app/Contents/MacOS/Unity" -batchmode -projectPath "<repo>" -executeMethod GemXpert.EditorTools.Bootstrap.GemXpertProjectSetup.RunFullSetupBatch -logFile -
```

## 2. Automated tests (EditMode)

**Window ▸ General ▸ Test Runner ▸ EditMode ▸ Run All**. Expected: all pass.

| Test class | What it proves |
|---|---|
| `CatalogueTests` | The JSON catalogue loads, has no dangling ids, contains all required rings/gems/cuts/metals, and every ring's default stone fits its own centre mount |
| `NavigationModelTests` | Navigate / Back / Home history behaves correctly |

## 3. Manual tests – Desktop mode (default when no headset is present)

Open `Assets/GemXpert/Scenes/MainShowroom/MainShowroom.unity` and press **Play**.

| # | Step | Expected |
|---|---|---|
| D1 | Press Play | Showroom visible: dark room, gold trim, 5 lit display stands with ring names, GEMXPERT on the back wall. Welcome panel in front. Console: `Run mode: Desktop preview`, `Catalogue loaded: 5 rings, 5 gemstones, 6 shapes, 4 metals.` |
| D2 | Hold right mouse and drag | View turns. Pitch stops at ±70° |
| D3 | W A S D | Walks slowly. Cannot leave the room |
| D4 | Hover a button | Button lifts slightly and brightens |
| D5 | Click **HOW IT WORKS** | Instructions screen, with Desktop controls listed. Header shows `< BACK` and `SHOWROOM` |
| D6 | `< BACK` | Returns to Welcome |
| D7 | **START EXPERIENCE** | Showroom hub with 6 tiles, each marked "Coming in Phase N" |
| D8 | Click any tile | "In development – Phase N" screen. **BACK TO SHOWROOM** returns to the hub |
| D9 | Walk away, turn, press **M** | Panel glides to ~1.4 m in front of you, slightly below eye level |
| D10 | Press **R** | View resets to the start position, panel recalled |
| D11 | Footer | Shows `Desktop preview   |   Wearable: not connected` |

## 4. Manual tests – XR Device Simulator mode

Select **GemXpert Systems** → `RunModeController` → *Requested Mode* = **XRDeviceSimulator**, then Play.

| # | Step | Expected |
|---|---|---|
| S1 | Play | Console `Run mode: XR Device Simulator`. Simulator help overlay visible |
| S2 | Use simulator keys to point a controller ray at the panel, then left click | Buttons respond exactly as in Desktop mode |
| S3 | Teleport onto the floor (simulator teleport input) | Rig moves. Floor is the only teleport target |

## 5. Not testable on this machine (needs a headset)

See `HARDWARE_TESTS_REMAINING.md`.
