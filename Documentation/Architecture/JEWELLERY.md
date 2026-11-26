# Pendants, Necklaces, Bracelets and Earrings

GemXpert has eighteen pieces besides the rings. They use the **same mount contract as the rings**, so choosing a stone,
the fit check, the size sliders, metals, compare, saving and the wearable all work on them unchanged.

| Category | Pieces | Shown on |
|---|---|---|
| Pendant | Solitaire Pendant, Halo Pendant, Bezel Drop Pendant, Double Halo Pear Pendant, Pear Cluster Pendant (claw-set halo), Blossom Pendant (five pave petals), Starburst Pendant (six sprays of coloured ovals) (each on an 18-inch cable chain) | On its own (modelled hanging as it would on a display bust) |
| Necklace | Riviera Necklace (22 graduated accents + centre drop), Bezel Station Necklace (6 stations + centre drop), Oval Halo Lariat (Y necklace: halo centre, 32 mm chain, claw-set drop) | On its own (modelled draped as it would on a display bust) |
| Bracelet | Three-Stone Bangle (62 × 52 mm inside), Tennis Bracelet (43 × 3 mm accents + raised centre stone) | On its own |
| Earring pair | Solitaire Studs, Halo Studs, Blossom Studs (butterfly backs), Pear Cluster Studs (screw backs), Bezel Drop Earrings (French hooks), Oval Halo Drop Earrings (halo stud + chain drop) | On their own, no stand (posts, butterfly backs and hooks visible) |

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
  the app gives them the diamond-style accent material. A piece's `accentGems` can colour some of them: on the Blossom
  pieces `AccentPink_*` is pink sapphire, and `"AccentMatch": "center"` gives a drop the same gemstone as the centre.
* **Chain drops** (`Drop_Center` / `Drop_Pair`, lariat and oval drop earrings) hang from the bottom of the head in their own
  empty. The app does not scale them; it moves them with the bottom of the head, so a larger stone pushes the drop down.
* **Starburst.** Only the centre head (claws and the ring of pink accents) scales with the stone. The sprays and rays are
  under `Attach_Burst`, and the bail's origin is at the centre, so the burst and the bail stay put as the stone changes.
  Each spray's colour comes from `accentGems` (`AccentGarnet_*` = garnet, and so on).
* **Point-up pears.** `pointUp` turns a head half a turn about its table normal, so a pear hangs with its point to the bail
  (pendants) or upwards (studs).
* **Stone size.** `defaultStoneLengthMm` / `defaultStoneWidthMm` set the stone a piece is modelled round (the Blossom takes a
  3.5 mm centre), and the app starts the design at that size instead of the cut's default.

## Not done yet

* Unity: FBX files are exported to `Blender/Exports/FBX/Jewellery`, but they are not copied into `Assets/` and the Unity
  code has no categories yet (the Unity project has never been compiled).
* The prototype page (`Prototype/Interface`) still shows rings only; the jewellery is in the React app (`Web/`).
* Design-from-a-photo for pendants, necklaces and bracelets (`Web/src/photo/piece.ts`, `PhotoPiece.tsx`) matches the photo to the closest catalogue piece and takes its centre stone and metal; it does not generate new chain, bail or bracelet geometry.
* No hand or wrist try-on for bracelets.
