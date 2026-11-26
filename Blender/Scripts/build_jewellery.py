"""
Builds the GemXpert pendants, necklaces, bracelets and earring pairs (and the display bust). Run headless from the repo root:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python Blender/Scripts/build_jewellery.py -- [--no-render] [--samples 64] [--only pendant_halo,bust]

Reads   Assets/GemXpert/Configurations/Resources/Catalogue/jewellery.json  (+ shapes, metals, gemstones)
Writes  Blender/Source/Jewellery/<Piece>.blend         source, with preview stones
        Blender/Exports/FBX/Jewellery/<Piece>.fbx      setting only (Unity)
        Blender/Exports/GLB/Web/<Piece>.glb            setting only (web app), also copied to Web/public/models
        Blender/Exports/GLB/<Piece>_Preview.glb        setting + default stones
        Blender/Exports/Renders/<Piece>.png            Cycles render; a 360 x 288 card goes to Web/public/renders
        Blender/Exports/jewellery_metadata.json        measured mounts (copied to Web/public/data)
        Display_Bust.glb                               the neck form pendants and necklaces are modelled on (reference only)
"""
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import build_all as ba  # noqa: E402
import gx_common as gx  # noqa: E402
import gx_jewellery as gj  # noqa: E402

EXPORTS = ba.EXPORTS
SOURCE = os.path.join(ba.SOURCE, "Jewellery")
WEB = os.path.join(gx.ROOT, "Web", "public")


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"render": True, "samples": 64, "only": None}
    i = 0
    while i < len(argv):
        if argv[i] == "--no-render":
            opts["render"] = False
        elif argv[i] == "--samples":
            opts["samples"] = int(argv[i + 1]); i += 1
        elif argv[i] == "--only":
            opts["only"] = set(argv[i + 1].split(",")); i += 1
        i += 1
    return opts


def load_pieces():
    with open(os.path.join(gx.CATALOGUE, "jewellery.json"), encoding="utf-8") as fh:
        return json.load(fh)["items"]


def card(src, dst):
    """360 x 288 thumbnail for the web app's design cards (macOS sips; plain copy elsewhere)."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        subprocess.run(["sips", "-z", "288", "360", src, "--out", dst], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        shutil.copy2(src, dst)


def render_piece(piece, meta, opts):
    col = gx.collection("Studio")
    M = meta["mounts"]["Center"]["blenderPositionMm"]
    cat = piece["category"]
    if cat == "pendant":
        gx.studio(col, target_mm=M, floor_z_mm=M[2] - 30, overhead=True, distance_scale=1.3)
        gx.camera(col, (M[0] + 34, M[1] - 96, M[2] + 26), (M[0], M[1], M[2] + 3), lens=80)
    elif cat == "necklace":
        gx.studio(col, target_mm=(0, -40, -40), floor_z_mm=M[2] - 25, overhead=True, distance_scale=3.0)
        gx.camera(col, (60, -300, 95), (0, -35, -32), lens=58)
    elif cat == "earring":
        gx.studio(col, target_mm=(0, 0, 2), floor_z_mm=-16, overhead=True, distance_scale=1.6)
        gx.camera(col, (34, -118, 26), (0, 0, 1.5), lens=82)
    else:
        floor = -(piece["innerHeightMm"] / 2 + 3.0)
        gx.studio(col, target_mm=(0, 0, 6), floor_z_mm=floor, distance_scale=2.6)
        gx.camera(col, (130, -165, 80), (0, 0, 3), lens=72)
    gx.setup_cycles(opts["samples"], 1000, 800)
    out = os.path.join(EXPORTS, "Renders", f"{piece['modelFile']}.png")
    gx.render(out)
    card(out, os.path.join(WEB, "renders", f"{piece['modelFile']}.png"))


def build_piece_asset(piece, catalogue, opts):
    gx.reset_scene()
    metals, gem_mats = ba.make_materials(catalogue)
    setting_col = gx.collection("Setting")
    preview_col = gx.collection("PreviewGems")
    root, meta, previews = gj.build_piece(piece, catalogue["shapes"], metals[piece["defaultMetalId"]],
                                          gem_mats["diamond"], setting_col)
    preview_objs = []
    for mount_id, spec in previews:
        gem_id = piece["defaultGemstoneId"] if mount_id in ("Center", "Pair") else "diamond"
        preview_objs.append(ba.unit_gem_object(spec.cut, preview_col, f"PreviewGem_{mount_id}", gem_mats[gem_id],
                                               (spec.width, spec.length, spec.depth),
                                               parent=bpy.data.objects[f"GemMount_{mount_id}"]))
    name = piece["modelFile"]
    setting = [o for o in gx.descendants(root) if not o.name.startswith("PreviewGem_")]
    gx.export_glb(os.path.join(EXPORTS, "GLB", "Web", f"{name}.glb"), setting)
    gx.export_glb(os.path.join(EXPORTS, "GLB", f"{name}_Preview.glb"), setting + preview_objs)
    gx.export_fbx(os.path.join(EXPORTS, "FBX", "Jewellery", f"{name}.fbx"), setting)
    os.makedirs(os.path.join(WEB, "models"), exist_ok=True)
    shutil.copy2(os.path.join(EXPORTS, "GLB", "Web", f"{name}.glb"), os.path.join(WEB, "models", f"{name}.glb"))

    meta["settingTriangles"] = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in setting if o.type == "MESH")
    for m in meta["mounts"].values():
        m["unityPositionMm"] = ba.blender_to_unity_position(m["blenderPositionMm"])
    if opts["render"]:
        render_piece(piece, meta, opts)
    gx.save_blend(os.path.join(SOURCE, f"{name}.blend"))
    return meta


def build_bust():
    gx.reset_scene()
    col = gx.collection("Display")
    leather = gx.principled("Display_White", (0.82, 0.81, 0.79, 1), roughness=0.55)
    v, f = gj.bust_mesh()
    obs = [gx.MeshBuilder().add(v, f).build("Display_Bust", col, leather)]
    (pv, pf), (bv, bf) = gj.stand_meshes()
    obs.append(gx.MeshBuilder().add(pv, pf).build("Display_Post", col, leather, smooth=False))
    obs.append(gx.MeshBuilder().add(bv, bf).build("Display_Base", col, leather, smooth=False))
    gx.export_glb(os.path.join(EXPORTS, "GLB", "Web", "Display_Bust.glb"), obs)
    gx.save_blend(os.path.join(SOURCE, "Display_Bust.blend"))


def main():
    opts = parse_args()
    t0 = time.time()
    catalogue = {k: gx.load_catalogue(k) for k in ("gemstones", "shapes", "metals")}
    meta_path = os.path.join(EXPORTS, "jewellery_metadata.json")
    metadata = {"generatedBy": "Blender/Scripts/build_jewellery.py", "blenderVersion": bpy.app.version_string,
                "units": "millimetres (Blender axes); unityPositionMm in Unity axes", "pieces": {}}
    if opts["only"] and os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as fh:
            metadata["pieces"] = json.load(fh).get("pieces", {})
    if not opts["only"] or "bust" in opts["only"]:
        build_bust()
    for piece in load_pieces():
        if opts["only"] and piece["id"] not in opts["only"]:
            continue
        print(f"[GemXpert] Building {piece['category']} '{piece['id']}'...", flush=True)
        metadata["pieces"][piece["id"]] = build_piece_asset(piece, catalogue, opts)
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)
    shutil.copy2(meta_path, os.path.join(WEB, "data", "jewellery_metadata.json"))
    print(f"[GemXpert] Jewellery build finished in {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
