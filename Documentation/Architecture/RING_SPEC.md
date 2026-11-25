# Ring Spec and "Design from a Photo"

A **ring spec** is a small JSON description of a ring design. Two generators build the same setting from it:

| Generator | Where | Used for |
|---|---|---|
| JavaScript (`GEN` in `Prototype/Interface/index.html`) | The browser interface | Live 3D preview and customisation |
| Python (`gx_rings.build_custom_ring`, run by `Blender/Scripts/build_custom.py`) | Headless Blender | FBX for the Unity app, `.blend` source, renders |

Both follow the same rules as the catalogue rings (band, claw-prong heads with gallery rails, halo frame with
bead-set accents, bezel collar, cathedral shoulders) and produce the same part names (`Band`, `Head_Center`,
`Halo_Frame`, `Accent_NN`, `Bezel`, `Cathedral`, `GemMount_*`). Custom rings therefore get swappable stones,
fit checks, metal changes and the hand view exactly like catalogue rings.

## Schema (specVersion 1)

```json
{
  "specVersion": 1,
  "name": "Six-Prong Oval Sapphire",
  "style": "solitaire | halo | three_stone | bezel",
  "prongs": 4,                       // 4, 6 or 8 (solitaire / three-stone centre)
  "cathedral": false,                // arched shoulders (solitaire / three-stone)
  "headHeight": "medium",            // low 0.45 mm | medium 1.0 mm | high 1.6 mm clearance above the band
  "innerDiameterMm": 17.3,
  "bandWidthMm": 2.0,                // 1.6 - 3.5
  "bandThicknessMm": 1.7,            // 1.5 - 2.4
  "stone": { "gemId": "blue_sapphire", "shapeId": "oval", "lengthMm": 9.0, "widthMm": 7.0 },
  "metalId": "yellow_gold",
  "halo": { "accentSizeMm": 1.3 },   // 1.0 - 1.8, halo only
  "sideStones": { "sizeMm": 4.0 }    // 3.0 - 5.0, three-stone only
}
```

`gemId`, `shapeId` and `metalId` are ids from the catalogue JSON. Out-of-range values are clamped by the page
(`normalizeSpec`) and rejected with a clear message by `build_custom.py`.

## Design from a Photo (interface)

1. The viewer picks a ring photo (JPEG, PNG, WebP).
2. **Analyse photo** sends it to Claude through the artifact `sample` capability (images enabled). This runs on
   the viewer's own Claude account and asks permission on first use. The prompt lists only the generator's
   options and asks for JSON: the spec fields, plus `observations` (what was seen), `notMatched` (features the
   generator can't express, e.g. milgrain or a twisted band) and `confidence`.
3. The answer is clamped to buildable values, shown in an editable form, and generated live on the stand.
4. **Save to my designs** adds it to Ring Designs (stored in this browser). **Download spec / Copy spec** hands the
   JSON to Blender.

When `sample` isn't available (a viewer who declines, or a local copy without the setup below), the same form
works as a hand-design builder.

### Photo analysis on the local copy

On `127.0.0.1` there is no claude.ai connection, so the local server `Tools/serve_interface.py` stands in for it.
It serves the interface and sends the photo to the Claude API (`claude-opus-5-5`, with server-side refusal
fallback) using **your own Anthropic API key**, billed to that account. The key stays in the server process; the
browser never sees it.

1. Get a key at console.anthropic.com.
2. Copy `Tools/local_secrets.env.example` to `Tools/local_secrets.env` and put the key after `ANTHROPIC_API_KEY=`
   (the file is git-ignored). An exported `ANTHROPIC_API_KEY` or an `ant auth login` profile also works.
3. Start the server: `Tools/.venv/bin/python Tools/serve_interface.py` (the app's preview does this), then open
   http://127.0.0.1:8765/.

The page checks `/api/photo-status` and shows what's missing if analysis can't run. The server binds to
127.0.0.1 only and refuses cross-site requests. `Tools/.venv` holds the `anthropic` Python library
(`python3 -m venv Tools/.venv && Tools/.venv/bin/pip install anthropic`).

## Building a spec in Blender (for Unity)

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python Blender/Scripts/build_custom.py -- Blender/Specs/example_six_prong_oval.json
```

Outputs `Exports/FBX/Rings/Custom/<Name>.fbx` (copied to `Assets/GemXpert/Models/Rings/Custom`), a preview GLB,
a render, the `.blend` source and `<Name>.meta.json` with the measured mounts in Unity axes.

## Publishing the interface

The published page is the **self-contained build**: run `python3 Tools/bundle_interface.py` after changing
`Prototype/Interface/index.html`, the models or the catalogue, then publish `Prototype/Interface/dist/index.html`.
It embeds the catalogue, models and thumbnails (about 4.5 MB) so it makes no file requests. Some browsers,
Safari for example, can't fetch an embedded page's side files ("The catalogue could not be loaded"). The
development page (`index.html` + `data/`, `models/`, `renders/`) still loads separate files for local work.

## Limits (be clear with customers)

* The result is the **closest buildable match**, not a scan or an exact copy. Styles outside solitaire / halo /
  three-stone / bezel (with 4, 6 or 8 prongs and optional cathedral shoulders) come out as the nearest of these.
* Sizes come from the photo alone. Without a scale reference, Claude assumes a band about 2 mm wide, so stone
  size is an estimate that the customer should check.
* Not yet generated: pavé bands, milgrain, engraving, twisted or split shanks, vintage filigree, eternity bands,
  coloured side stones, non-round side stones.
* Photo analysis was tested in the interface with a local stand-in answer (`?mockClaude=1`, 127.0.0.1 only).
  The local server's API call was checked up to authentication (a deliberately invalid key is rejected by the
  API). A real Claude answer has not yet been seen, locally or on the published page.
