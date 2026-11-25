"""
Builds custom rings from GemXpert ring spec files (the JSON produced by the interface's "From a photo" screen).

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python Blender/Scripts/build_custom.py -- Blender/Specs/my_ring.json [more.json ...] [--no-render]

For each spec it writes:
    Blender/Source/Rings/Custom/<Object>.blend
    Blender/Exports/FBX/Rings/Custom/<Object>.fbx      (setting only, mounts included; copied to Assets/GemXpert/Models/Rings/Custom)
    Blender/Exports/GLB/Custom/<Object>_Preview.glb
    Blender/Exports/Renders/Custom/<Object>.png
    Blender/Exports/Custom/<Object>.meta.json          (measured mounts in Unity axes, like asset_metadata.json)

Spec schema: Documentation/Architecture/RING_SPEC.md
"""
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gx_common as gx  # noqa: E402
import gx_rings as rings  # noqa: E402
from build_all import blender_to_unity_position, make_materials, unit_gem_object  # noqa: E402

EXPORTS = os.path.join(gx.ROOT, "Blender", "Exports")
SOURCE = os.path.join(gx.ROOT, "Blender", "Source")
UNITY = os.path.join(gx.ROOT, "Assets", "GemXpert", "Models", "Rings", "Custom")

STYLES = {"solitaire", "halo", "three_stone", "bezel"}


def object_name(spec):
    slug = re.sub(r"[^A-Za-z0-9]+", " ", spec.get("name") or spec.get("id") or "Custom").title().replace(" ", "")
    return "Ring_Custom_" + (slug[:40] or "Ring")


def validate(spec, catalogue):
    problems = []
    if spec.get("style") not in STYLES:
        problems.append(f"style must be one of {sorted(STYLES)}")
    st = spec.get("stone", {})
    if st.get("shapeId") not in catalogue["shapes"]:
        problems.append(f"stone.shapeId must be one of {sorted(catalogue['shapes'])}")
    if st.get("gemId") not in catalogue["gemstones"]:
        problems.append(f"stone.gemId must be one of {sorted(catalogue['gemstones'])}")
    if spec.get("metalId") not in catalogue["metals"]:
        problems.append(f"metalId must be one of {sorted(catalogue['metals'])}")
    for key, lo, hi in (("bandWidthMm", 1.4, 4.0), ("bandThicknessMm", 1.3, 2.6)):
        v = spec.get(key)
        if not isinstance(v, (int, float)) or not lo <= v <= hi:
            problems.append(f"{key} must be a number between {lo} and {hi}")
    for key in ("lengthMm", "widthMm"):
        v = st.get(key)
        if not isinstance(v, (int, float)) or not 2.5 <= v <= 14.0:
            problems.append(f"stone.{key} must be a number between 2.5 and 14")
    return problems


def build(spec_path, catalogue, render):
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    problems = validate(spec, catalogue)
    if problems:
        raise SystemExit(f"{spec_path}: invalid spec\n  - " + "\n  - ".join(problems))
    spec["objectName"] = object_name(spec)
    name = spec["objectName"]

    gx.reset_scene()
    metals, gem_mats = make_materials(catalogue)
    setting_col = gx.collection("Setting")
    preview_col = gx.collection("PreviewGems")
    root, meta, previews = rings.build_custom_ring(spec, metals[spec["metalId"]], gem_mats["diamond"], setting_col)
    preview_objs = []
    for mount_id, mount_ob, gspec in previews:
        gem_id = spec["stone"]["gemId"] if mount_id == "Center" else "diamond"
        preview_objs.append(unit_gem_object(gspec.cut, preview_col, f"PreviewGem_{mount_id}", gem_mats[gem_id],
                                            (gspec.width, gspec.length, gspec.depth), parent=mount_ob))
    setting = [o for o in gx.descendants(root) if not o.name.startswith("PreviewGem_")]
    fbx = os.path.join(EXPORTS, "FBX", "Rings", "Custom", f"{name}.fbx")
    gx.export_fbx(fbx, setting)
    gx.export_glb(os.path.join(EXPORTS, "GLB", "Custom", f"{name}_Preview.glb"), setting + preview_objs)
    os.makedirs(UNITY, exist_ok=True)
    shutil.copy2(fbx, os.path.join(UNITY, f"{name}.fbx"))

    for m in meta["mounts"].values():
        m["unityPositionMm"] = blender_to_unity_position(m["blenderPositionMm"])
        m["unityEulerDeg"] = [0.0, 0.0, round(m["blenderRotationDeg"][1], 3)]
    meta["spec"] = spec
    meta["settingTriangles"] = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in setting if o.type == "MESH")
    os.makedirs(os.path.join(EXPORTS, "Custom"), exist_ok=True)
    with open(os.path.join(EXPORTS, "Custom", f"{name}.meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    if render:
        studio_col = gx.collection("Studio")
        floor = -(spec.get("innerDiameterMm", 17.3) / 2.0 + spec["bandThicknessMm"] * 0.9) - 0.05
        gx.studio(studio_col, target_mm=(0, 0, 3), floor_z_mm=floor)
        gx.camera(studio_col, (58, -74, 36), (0, 0, 2.5), lens=90)
        gx.setup_cycles(48, 1000, 800)
        gx.render(os.path.join(EXPORTS, "Renders", "Custom", f"{name}.png"))
    gx.save_blend(os.path.join(SOURCE, "Rings", "Custom", f"{name}.blend"))
    print(f"[GemXpert] custom ring {name}: {meta['settingTriangles']} tris -> {fbx}")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    render = "--no-render" not in argv
    specs = [a for a in argv if a.endswith(".json")]
    if not specs:
        raise SystemExit("usage: ... --python build_custom.py -- spec.json [more.json] [--no-render]")
    catalogue = {k: gx.load_catalogue(k) for k in ("gemstones", "shapes", "metals")}
    for path in specs:
        build(os.path.abspath(path), catalogue, render)


if __name__ == "__main__":
    main()
