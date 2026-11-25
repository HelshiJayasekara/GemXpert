"""
GemXpert asset build. Run headless from the repository root:

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
        --python Blender/Scripts/build_all.py -- [--no-render] [--samples 64] [--only solitaire,halo]

Outputs
    Blender/Source/Materials/GemXpert_Materials.blend   metal + gem PBR material library
    Blender/Source/Gemstones/GemXpert_GemCuts.blend      6 unit cuts + real-size showcase
    Blender/Source/Rings/Ring_<Design>.blend             one source file per ring (with preview stones)
    Blender/Exports/FBX/{Rings,Gemstones}/*.fbx          Unity imports (settings WITHOUT stones; unit gems)
    Blender/Exports/GLB/*.glb                            review copies (ring + default stone + materials)
    Blender/Exports/Renders/*.png                        Cycles preview renders
    Blender/Exports/asset_metadata.json                  measured mount positions & gem proportions (Unity axes)
    Assets/GemXpert/Models/{Rings,Gemstones}/*.fbx       copies for the Unity project
"""
import json
import math
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import gx_common as gx  # noqa: E402
import gx_gems as gems  # noqa: E402
import gx_hand as hand  # noqa: E402
import gx_rings as rings  # noqa: E402

BLENDER_DIR = os.path.join(gx.ROOT, "Blender")
EXPORTS = os.path.join(BLENDER_DIR, "Exports")
SOURCE = os.path.join(BLENDER_DIR, "Source")
UNITY_MODELS = os.path.join(gx.ROOT, "Assets", "GemXpert", "Models")

GEM_OBJECT_NAMES = {"round": "Gem_Round", "oval": "Gem_Oval", "cushion": "Gem_Cushion", "pear": "Gem_Pear",
                    "emerald": "Gem_EmeraldCut", "princess": "Gem_Princess"}


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


def blender_to_unity_position(p_mm):
    """Blender (x, y, z) -> Unity (x, y, z) for our FBX settings: (-x, z, -y)."""
    return [round(-p_mm[0], 4), round(p_mm[2], 4), round(-p_mm[1], 4)]


def make_materials(catalogue):
    metals = {mid: gx.metal_material(m) for mid, m in catalogue["metals"].items()}
    gem_mats = {gid: gx.gem_material(g) for gid, g in catalogue["gemstones"].items()}
    return metals, gem_mats


def unit_gem_object(cut, col, name, material=None, size_mm=(1.0, 1.0, 1.0), parent=None, location_mm=(0, 0, 0)):
    verts, faces, _ = gems.build_cut_cached(cut)
    w, l, d = size_mm
    return gx.MeshBuilder().add(verts * [w, l, d], faces).build(
        name, col, material, smooth=False, parent=parent, location_mm=location_mm)


# ----------------------------------------------------------------------------------------- builds

def build_material_library(catalogue):
    gx.reset_scene()
    make_materials(catalogue)
    gx.save_blend(os.path.join(SOURCE, "Materials", "GemXpert_Materials.blend"))


def build_gemstones(catalogue, opts):
    gx.reset_scene()
    _, gem_mats = make_materials(catalogue)
    shapes = catalogue["shapes"]
    unit_col = gx.collection("Gem_Cuts_Unit_1mm")
    unit_col.hide_render = True  # 1 mm export copies; only the real-size showcase is rendered
    show_col = gx.collection("Showcase_RealSize")
    meta = {}

    # 1) Unit cuts: 1 mm x 1 mm x 1 mm bounding box, girdle centre at origin -> scale (W, D, L) in Unity.
    for i, cut in enumerate(gems.CUTS):
        name = GEM_OBJECT_NAMES[cut]
        ob = unit_gem_object(cut, unit_col, name, gem_mats["diamond"])
        _, faces, info = gems.build_cut_cached(cut)
        info["object"] = name
        meta[cut] = info
        ob.location.x = (i * 2.0) * gx.MM  # spread out in the .blend; reset to origin for export
        saved = ob.location.copy()
        ob.location = (0, 0, 0)
        gx.export_fbx(os.path.join(EXPORTS, "FBX", "Gemstones", f"{name}.fbx"), [ob])
        ob.location = saved

    # 2) Real-size showcase: the combinations requested in the brief.
    showcase = [("round", "blue_sapphire", "Round Sapphire"), ("oval", "blue_sapphire", "Oval Sapphire"),
                ("cushion", "blue_sapphire", "Cushion Sapphire"), ("oval", "ruby", "Ruby"),
                ("emerald", "emerald", "Emerald"), ("cushion", "yellow_sapphire", "Yellow Sapphire"),
                ("round", "diamond", "Diamond-style"), ("pear", "diamond", "Pear Diamond-style"),
                ("princess", "ruby", "Princess Ruby")]
    spacing = 13.0
    objects = []
    for i, (cut, gem_id, label) in enumerate(showcase):
        s = shapes[cut]
        _, _, info = gems.build_cut_cached(cut)
        w, l = s["defaultWidthMm"], s["defaultLengthMm"]
        d = w * info["depth_ratio"]
        x = (i % 3 - 1) * spacing           # 3 x 3 grid, table up
        y = (1 - i // 3) * spacing
        ob = unit_gem_object(cut, show_col, f"Showcase_{label.replace(' ', '_').replace('-', '')}", gem_mats[gem_id],
                             (w, l, d), location_mm=(x, y, d * info["pavilion_fraction"]))
        objects.append(ob)
    gx.export_glb(os.path.join(EXPORTS, "GLB", "GemShowcase.glb"), objects)

    if opts["render"]:
        studio_col = gx.collection("Studio")
        gx.studio(studio_col, target_mm=(0, 0, 2), floor_z_mm=0.0, overhead=False)
        gx.camera(studio_col, (0, -26, 104), (0, -0.5, 0), lens=78)  # near top-down: true outlines, little foreshortening
        gx.setup_cycles(opts["samples"], 1200, 1000)
        gx.render(os.path.join(EXPORTS, "Renders", "Gemstones_Showcase.png"))

    gx.save_blend(os.path.join(SOURCE, "Gemstones", "GemXpert_GemCuts.blend"))
    return meta


def build_ring_asset(ring_def, catalogue, opts):
    gx.reset_scene()
    metals, gem_mats = make_materials(catalogue)
    setting_col = gx.collection("Setting")
    preview_col = gx.collection("PreviewGems")
    root, meta, previews = rings.build_ring(ring_def, catalogue["shapes"], metals[ring_def["defaultMetalId"]],
                                            gem_mats["diamond"], setting_col)

    # Preview stones (in the .blend / GLB only - NOT in the Unity setting FBX).
    preview_objs = []
    for mount_id, mount_ob, spec in previews:
        gem_id = ring_def["defaultGemstoneId"] if mount_id == "Center" else "diamond"
        preview_objs.append(unit_gem_object(spec.cut, preview_col, f"PreviewGem_{mount_id}", gem_mats[gem_id],
                                            (spec.width, spec.length, spec.depth), parent=mount_ob))

    setting_objs = gx.descendants(root)
    setting_objs = [o for o in setting_objs if not o.name.startswith("PreviewGem_")]
    gx.export_fbx(os.path.join(EXPORTS, "FBX", "Rings", f"{meta['object']}.fbx"), setting_objs)
    gx.export_glb(os.path.join(EXPORTS, "GLB", f"{meta['object']}_Preview.glb"), setting_objs + preview_objs)

    # Measured statistics
    tris = 0
    for o in setting_objs:
        if o.type == "MESH":
            tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
    meta["settingTriangles"] = tris
    for mount_id, m in meta["mounts"].items():
        m["unityPositionMm"] = blender_to_unity_position(m["blenderPositionMm"])
        # Only Y rotations are used: Blender Ry(+a) tilts +Z towards +X, which is Unity rotation Z(+a).
        m["unityEulerDeg"] = [0.0, 0.0, round(m["blenderRotationDeg"][1], 3)]

    if opts["render"]:
        studio_col = gx.collection("Studio")
        floor = -(ring_def["innerDiameterMm"] / 2.0 + ring_def["bandThicknessMm"] * 0.9) - 0.05
        gx.studio(studio_col, target_mm=(0, 0, 3), floor_z_mm=floor)
        gx.camera(studio_col, (58, -74, 36), (0, 0, 2.5), lens=90)
        gx.setup_cycles(opts["samples"], 1000, 800)
        gx.render(os.path.join(EXPORTS, "Renders", f"{meta['object']}.png"))
        # Close-up of the head
        mount_z = meta["mounts"]["Center"]["blenderPositionMm"][2]
        bpy.data.objects.remove(bpy.context.scene.camera, do_unlink=True)
        gx.camera(studio_col, (22, -30, mount_z + 22), (0, 0, mount_z - 0.5), lens=100)
        gx.render(os.path.join(EXPORTS, "Renders", f"{meta['object']}_CloseUp.png"))

    gx.save_blend(os.path.join(SOURCE, "Rings", f"{meta['object']}.blend"))
    return meta


def build_hand_asset(catalogue, opts):
    """Simulated left hand: FBX for Unity (Phase 4 fallback hand), web GLB, hero render with a ring on it."""
    gx.reset_scene()
    metals, gem_mats = make_materials(catalogue)
    col = gx.collection("Hand")
    root, skin, nails, anchor, meta = hand.build_hand(col, hand.skin_material(), hand.nail_material())
    objs = gx.descendants(root)
    gx.export_fbx(os.path.join(EXPORTS, "FBX", "Hands", "SimulatedHand_L.fbx"), objs)
    gx.export_glb(os.path.join(EXPORTS, "GLB", "Web", "SimulatedHand_L.glb"), objs, vertex_colors=True)

    if opts["render"]:
        ring_def = catalogue["rings"]["halo"]
        ring_col = gx.collection("RingOnHand")
        r_root, _meta, previews = rings.build_ring(ring_def, catalogue["shapes"], metals[ring_def["defaultMetalId"]],
                                                   gem_mats["diamond"], ring_col)
        r_root.parent = anchor
        for mount_id, mount_ob, spec in previews:
            gem_id = ring_def["defaultGemstoneId"] if mount_id == "Center" else "diamond"
            unit_gem_object(spec.cut, ring_col, f"PreviewGem_{mount_id}", gem_mats[gem_id],
                            (spec.width, spec.length, spec.depth), parent=mount_ob)
        min_z = min(v.co.z for v in skin.data.vertices) / gx.MM
        studio_col = gx.collection("Studio")
        # Skin is diffuse and much larger than a ring: keep irradiance on the skin ~1/12 of the ring studio's.
        gx.studio(studio_col, target_mm=(-10, -10, 5), floor_z_mm=min_z - 0.3, distance_scale=3.0, energy_scale=0.03)
        gx.camera(studio_col, (95, -200, 175), (-14, -12, 0), lens=55)
        gx.setup_cycles(opts["samples"], 1200, 900)
        gx.render(os.path.join(EXPORTS, "Renders", "Hand_RingOnFinger.png"))
        bpy.data.objects.remove(bpy.context.scene.camera, do_unlink=True)
        gx.camera(studio_col, (30, -62, 52), (0, -4, 6), lens=85)
        gx.render(os.path.join(EXPORTS, "Renders", "Hand_RingOnFinger_CloseUp.png"))

    gx.save_blend(os.path.join(SOURCE, "Hands", "SimulatedHand_L.blend"))
    return meta


def copy_to_unity():
    for kind in ("Rings", "Gemstones", "Hands"):
        src = os.path.join(EXPORTS, "FBX", kind)
        dst = os.path.join(UNITY_MODELS, kind)
        os.makedirs(dst, exist_ok=True)
        for f in sorted(os.listdir(src)):
            if f.endswith(".fbx"):
                shutil.copy2(os.path.join(src, f), os.path.join(dst, f))


def main():
    opts = parse_args()
    t0 = time.time()
    catalogue = {k: gx.load_catalogue(k) for k in ("rings", "gemstones", "shapes", "metals")}
    metadata = {"generatedBy": "Blender/Scripts/build_all.py", "blenderVersion": bpy.app.version_string,
                "units": "millimetres; unity* fields are already converted to Unity axes", "gemCuts": {}, "rings": {}}

    if not opts["only"] or "materials" in opts["only"]:
        build_material_library(catalogue)
    if not opts["only"] or "gems" in opts["only"]:
        metadata["gemCuts"] = build_gemstones(catalogue, opts)
    for rid, ring_def in catalogue["rings"].items():
        if opts["only"] and rid not in opts["only"]:
            continue
        print(f"[GemXpert] Building ring '{rid}'...")
        metadata["rings"][rid] = build_ring_asset(ring_def, catalogue, opts)
    if not opts["only"] or "hand" in opts["only"]:
        print("[GemXpert] Building simulated hand...")
        metadata["hand"] = build_hand_asset(catalogue, opts)

    # Merge into the existing metadata so partial (--only) builds keep everything else.
    meta_path = os.path.join(EXPORTS, "asset_metadata.json")
    if opts["only"] and os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as fh:
            existing = json.load(fh)
        for key in ("gemCuts", "rings"):
            existing.setdefault(key, {}).update(metadata[key])
        if "hand" in metadata:
            existing["hand"] = metadata["hand"]
        metadata = existing
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)
    copy_to_unity()
    print(f"[GemXpert] Build finished in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
