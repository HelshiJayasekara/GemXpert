# Pendants, Necklaces, Bracelets and Earrings

GemXpert has ten pieces besides the rings. They use the **same mount contract as the rings**, so choosing a stone,
the fit check, the size sliders, metals, compare, saving and the wearable all work on them unchanged.

| Category | Pieces | Shown on |
|---|---|---|
| Pendant | Solitaire Pendant, Halo Pendant, Bezel Drop Pendant (each on an 18-inch cable chain) | On its own (modelled hanging as it would on a display bust) |
| Necklace | Riviera Necklace (22 graduated accents + centre drop), Bezel Station Necklace (6 stations + centre drop) | On its own (modelled draped as it would on a display bust) |
| Bracelet | Three-Stone Bangle (62 × 52 mm inside), Tennis Bracelet (43 × 3 mm accents + raised centre stone) | On its own |
| Earring pair | Solitaire Studs, Halo Studs (butterfly backs), Bezel Drop Earrings (French hooks) | On their own, no stand (posts, butterfly backs and hooks visible) |

**Earring pairs.** Each model has `GemMount_Center` (the right earring as you look at it) and its mirror twin
`GemMount_Pair`, with identical heads. The catalogue lists only the Center mount: the app gives the twin the same
stone, head scaling and (mirrored) seat. Posts, butterfly backs and hooks are `Attach_*` objects, so they are not
scaled; drops scale about their `Attach_Bail` like pendants. Both earrings face -Y; the plane y = 0 just behind the
heads is where an earring card or ear lobe would be (no stand is shown).

## Files

| Path | What |
|---|---|
| `Assets/GemXpert/Configurations/Resources/Catalogue/jewellery.json` | Catalogue (copied to `Web/public/data/jewellery.json`). Same mount schema as `rings.json`, plus `category`, `modelFile`, `display` and builder settings |
| `Blender/Scripts/gx_jewellery.py` | Generators: display bust, necklace path, cable chain, bails, collets, bangle, tennis line, earring studs and drops |
| `Blender/Scripts/build_jewellery.py` | Builds every piece: `.blend`, FBX, web GLB, preview GLB, render, card thumbnail, metadata |
| `Blender/Exports/jewellery_metadata.json` | Measured mounts (copied to `Web/public/data/jewellery_metadata.json`) |
| `Web/public/models/{Pendant,Necklace,Bracelet,Earring}_*.glb` | Web models |
| `Web/public/renders/{Pendant,Necklace,Bracelet}_*.png` | Design-card thumbnails |

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python Blender/Scripts/build_jewellery.py -- --samples 64
```

`--no-render` skips the Cycles renders; `--only pendant_halo,bust` rebuilds selected pieces.

## Conventions

* **Mounts.** Each piece has `GemMount_Center` at the centre stone's girdle centre, local +Z out of the table, with the head
  (`Head_Center`, `Halo_Frame`, `Bezel`, `Accent_Halo`) under it. The app scales the head with the stone, as for rings.
  The bangle also has fixed `GemMount_SideL/SideR` stones.
* **Bails stay on the chain.** A pendant's bail is `Attach_Bail` under the mount. The app does not scale it; it scales the
  head about the bail instead, so a larger stone hangs lower rather than pulling the bail off the chain.
* **Bust space.** Pendants and necklaces are modelled where they would lie on a display bust (Blender Z up, facing -Y),
  so the chain drapes naturally and the pendant tilts like it would on the chest. The bust itself (`Display_Bust`, built
  by `build_jewellery.py`) is a modelling reference only: the web app shows the pieces on their own.
* **Bracelets** use ring axes (wrist along Blender Y, centre stone at the top) and are shown on their own.
* **Fixed accents** (riviera line, stations, tennis line, halo) are merged meshes whose names start with `Accent`, so
  the app gives them the diamond-style accent material.

## Not done yet

* Unity: FBX files are exported to `Blender/Exports/FBX/Jewellery`, but they are not copied into `Assets/` and the Unity
  code has no categories yet (the Unity project has never been compiled).
* The prototype page (`Prototype/Interface`) still shows rings only; the jewellery is in the React app (`Web/`).
* Design-from-a-photo for pendants, necklaces and bracelets (`Web/src/photo/piece.ts`, `PhotoPiece.tsx`) matches the photo to the closest catalogue piece and takes its centre stone and metal; it does not generate new chain, bail or bracelet geometry.
* No hand or wrist try-on for bracelets.
