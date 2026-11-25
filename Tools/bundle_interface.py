"""
Builds the self-contained published version of the GemXpert interface.

    python3 Tools/bundle_interface.py

Reads   Prototype/Interface/index.html (development page; loads side files with fetch)
        Prototype/Interface/data/*.json, Blender/Exports/GLB/Web/*.glb, Prototype/Interface/renders/*.png
Writes  Prototype/Interface/dist/index.html with everything inline as window.GX_BUNDLE.

The page checks GX_BUNDLE before making any request, so the bundled page needs no file fetches. That matters
because some browsers (Safari, for example) block an embedded page from fetching its own side files.
"""
import base64
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "Prototype", "Interface")
GLB_DIR = os.path.join(ROOT, "Blender", "Exports", "GLB", "Web")
OUT = os.path.join(SRC, "dist", "index.html")


def main():
    with open(os.path.join(SRC, "index.html"), encoding="utf-8") as fh:
        page = fh.read()

    data = {}
    for name in ("rings", "gemstones", "shapes", "metals", "asset_metadata"):
        with open(os.path.join(SRC, "data", f"{name}.json"), encoding="utf-8") as fh:
            data[f"data/{name}.json"] = json.load(fh)

    # Every model the page references as models/<Name>.json, taken from the compact GLB export.
    referenced = sorted(set(re.findall(r"models/(?:\$\{[^}]+\}|[A-Za-z0-9_]+)\.json", page)))
    models = {}
    for glb in sorted(os.listdir(GLB_DIR)):
        if glb.endswith(".glb"):
            with open(os.path.join(GLB_DIR, glb), "rb") as fh:
                models[f"models/{glb[:-4]}.json"] = base64.b64encode(fh.read()).decode("ascii")

    images = {}
    for png in sorted(os.listdir(os.path.join(SRC, "renders"))):
        if png.endswith(".png"):
            with open(os.path.join(SRC, "renders", png), "rb") as fh:
                images[f"renders/{png}"] = "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")

    payload = json.dumps({"data": data, "models": models, "images": images}, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")  # never close the <script> early
    tag = f"<script>window.GX_BUNDLE={payload};</script>\n"

    marker = '<script type="importmap">'
    if marker not in page:
        raise SystemExit("index.html has no import map; cannot place the bundle before the module script")
    page = page.replace(marker, tag + marker, 1)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"bundled {len(data)} data files, {len(models)} models, {len(images)} images -> {OUT} "
          f"({os.path.getsize(OUT) / 1e6:.2f} MB); page references: {', '.join(referenced) or 'none'}")


if __name__ == "__main__":
    main()
