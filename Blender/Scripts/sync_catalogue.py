"""
Writes values measured from the generated models back into the Unity catalogue (plain python3, no Blender):

    python3 Blender/Scripts/sync_catalogue.py

  shapes.json  depthRatio          := real total depth / width of each generated cut
  rings.json   fallbackPositionMm  := measured GemMount_* positions (already converted to Unity axes)
               fallbackEulerDeg    := measured mount rotations (Unity axes)

Run after build_all.py so Unity's fallbacks and fit checks match the geometry exactly.
"""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CATALOGUE = os.path.join(ROOT, "Assets", "GemXpert", "Configurations", "Resources", "Catalogue")
META = os.path.join(ROOT, "Blender", "Exports", "asset_metadata.json")


def main():
    with open(META, encoding="utf-8") as fh:
        meta = json.load(fh)

    shapes_path = os.path.join(CATALOGUE, "shapes.json")
    with open(shapes_path, encoding="utf-8") as fh:
        text = fh.read()
    for cut, info in meta["gemCuts"].items():
        # Targeted edit keeps the file's compact one-entry-per-shape layout.
        text, n = re.subn(r'("id": "%s".*?"depthRatio": )[0-9.]+' % re.escape(cut),
                          r"\g<1>%.3f" % info["depth_ratio"], text, count=1, flags=re.S)
        if n != 1:
            raise SystemExit(f"shape '{cut}' not found in shapes.json")
        print(f"shape {cut:9s} depthRatio {info['depth_ratio']:.3f}")
    with open(shapes_path, "w", encoding="utf-8") as fh:
        fh.write(text)

    rings_path = os.path.join(CATALOGUE, "rings.json")
    with open(rings_path, encoding="utf-8") as fh:
        rings = json.load(fh)
    for ring in rings["items"]:
        measured = meta["rings"][ring["id"]]["mounts"]
        for mount in ring["mounts"]:
            m = measured[mount["id"]]
            x, y, z = m["unityPositionMm"]
            ex, ey, ez = m["unityEulerDeg"]
            mount["fallbackPositionMm"] = {"x": round(x + 0.0, 2), "y": round(y, 2), "z": round(z + 0.0, 2)}
            mount["fallbackEulerDeg"] = {"x": ex, "y": ey, "z": ez}
            print(f"ring {ring['id']:11s} {mount['id']:7s} pos {mount['fallbackPositionMm']} rotZ {ez}")
    with open(rings_path, "w", encoding="utf-8") as fh:
        json.dump(rings, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    main()
