"""
Exports web-ready GLBs from the saved .blend sources (run after build_all.py):

    Blender --background --factory-startup --python Blender/Scripts/export_web.py

    Blender/Exports/GLB/Web/Ring_<Design>.glb   setting only (band, heads, mounts, accents) - no centre stones
    Blender/Exports/GLB/Web/Gem_<Cut>.glb       unit cut (1 x 1 x 1 mm), girdle centre at origin

These feed the browser preview of the GemXpert interface; Unity uses the FBX exports.
"""
import base64
import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Blender", "Exports", "GLB", "Web")
SOURCE = os.path.join(ROOT, "Blender", "Source")
PROTOTYPE_MODELS = os.path.join(ROOT, "Prototype", "Interface", "models")


def glb_to_embedded_json(glb_path, json_path):
    """Converts a .glb into a self-contained glTF JSON (buffer as a base64 data URI).
    Hosts that only serve common web types can serve this as .json; three.js GLTFLoader parses it directly."""
    with open(glb_path, "rb") as fh:
        data = fh.read()
    magic, _version, _length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF", f"{glb_path} is not a GLB"
    offset, doc, binary = 12, None, b""
    while offset < len(data):
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        chunk = data[offset + 8: offset + 8 + chunk_len]
        if chunk_type == 0x4E4F534A:    # JSON
            doc = json.loads(chunk.decode("utf-8"))
        elif chunk_type == 0x004E4942:  # BIN
            binary = chunk
        offset += 8 + chunk_len
    doc["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(binary).decode("ascii")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"))


def convert_all():
    os.makedirs(PROTOTYPE_MODELS, exist_ok=True)
    for glb in sorted(glob.glob(os.path.join(OUT, "*.glb"))):
        name = os.path.splitext(os.path.basename(glb))[0]
        glb_to_embedded_json(glb, os.path.join(PROTOTYPE_MODELS, f"{name}.json"))
        print(f"[GemXpert] embedded glTF JSON: {name}.json")


def main():
    import bpy
    import gx_common as gx

    os.makedirs(OUT, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(SOURCE, "Rings", "Ring_*.blend"))):
        bpy.ops.wm.open_mainfile(filepath=path)
        name = os.path.splitext(os.path.basename(path))[0]
        root = bpy.data.objects[name]
        objs = [o for o in gx.descendants(root) if not o.name.startswith("PreviewGem_")]
        gx.export_glb(os.path.join(OUT, f"{name}.glb"), objs)
        print(f"[GemXpert] web export {name}: {len(objs)} objects")

    bpy.ops.wm.open_mainfile(filepath=os.path.join(SOURCE, "Gemstones", "GemXpert_GemCuts.blend"))
    for ob in [o for o in bpy.data.objects if o.name.startswith("Gem_")]:
        saved = ob.location.copy()
        ob.location = (0, 0, 0)
        gx.export_glb(os.path.join(OUT, f"{ob.name}.glb"), [ob])
        ob.location = saved
        print(f"[GemXpert] web export {ob.name}")
    convert_all()


if __name__ == "__main__":
    if "--convert-only" in sys.argv:   # plain python3: re-embed existing GLBs without Blender
        convert_all()
    else:
        main()
