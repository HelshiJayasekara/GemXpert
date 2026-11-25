"""
Concept render of the GemXpert motion ring (ESP32 + MPU-9250), built from the planned component list.

    Blender --background --factory-startup --python Blender/Scripts/build_wearable_concept.py -- [--samples N]

Writes Blender/Exports/Renders/Wearable_Concept_raw.png (transparent background), a JSON file with the
on-screen position of each labelled part, and Blender/Source/Wearable/Wearable_Concept.blend.
Then run annotate_wearable.py (needs Pillow) to add the background, title and labels.

Layout (mm, Z up, the arm/finger axis along +X):
  * wrist pod at the origin on a velcro strap: ESP32 DevKit, TP4056 charger, 3.3 V regulator, LiPo underneath,
    slide switch and recentre button on the walls, smoked lid lifted to show the inside;
  * ring at x = 125 mm: 3D-printed band with a flat pad holding the GY-9250 (MPU-9250) board;
  * four wires (VCC red, GND black, SCL yellow, SDA green) from the ring board into the pod.
Board sizes follow the real modules (DevKit 51 x 28 mm, GY-9250 25.5 x 15.5 mm, TP4056 26 x 17 mm).
"""
import json
import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gx_common import (MM, ROOT, MeshBuilder, camera, catmull_rom, collection, principled, render,  # noqa: E402
                       reset_scene, save_blend, setup_cycles, studio, tube)

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAMPLES = int(ARGS[ARGS.index("--samples") + 1]) if "--samples" in ARGS else 192
OUT_DIR = os.path.join(ROOT, "Blender", "Exports", "Renders")
RAW = os.path.join(OUT_DIR, "Wearable_Concept_raw.png")
ANCHORS = os.path.join(OUT_DIR, "Wearable_Concept_anchors.json")
BLEND = os.path.join(ROOT, "Blender", "Source", "Wearable", "Wearable_Concept.blend")
W, H = 1500, 1000


# ------------------------------------------------------------------------------------------ helpers
def box_geo(lo, hi):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return v, f


def box(name, col, mat, lo, hi, bevel=0.0):
    ob = MeshBuilder().add(*box_geo(lo, hi)).build(name, col, mat, smooth=False)
    if bevel > 0:
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width = bevel * MM
        m.segments = 3
        m.limit_method = "ANGLE"
        for p in ob.data.polygons:
            p.use_smooth = True
        ob.modifiers.new("Smooth", "WEIGHTED_NORMAL")
    return ob


def boxes(name, col, mat, items, bevel=0.0):
    mb = MeshBuilder()
    for lo, hi in items:
        mb.add(*box_geo(lo, hi))
    ob = mb.build(name, col, mat, smooth=False)
    if bevel > 0:
        m = ob.modifiers.new("Bevel", "BEVEL")
        m.width = bevel * MM
        m.segments = 2
        m.limit_method = "ANGLE"
    return ob


def cyl(name, col, mat, a, b, r, seg=24):
    v, f = tube(np.array([a, b], float), r, segments=seg)
    return MeshBuilder().add(v, f).build(name, col, mat)


def wire(name, col, mat, pts, r=0.42):
    path = catmull_rom(np.array(pts, float), samples_per_segment=14)
    v, f = tube(path, r, segments=10)
    return MeshBuilder().add(v, f).build(name, col, mat)


def rounded_rect(hw, r0, r1, rad, n=5):
    """Closed profile in (u, r): u across [-hw, hw], r in [r0, r1], corner radius rad."""
    pts = []
    for cu, cr, a0 in ((hw - rad, r1 - rad, 0), (-hw + rad, r1 - rad, 90), (-hw + rad, r0 + rad, 180), (hw - rad, r0 + rad, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cu + rad * math.cos(a), cr + rad * math.sin(a)))
    return pts


def ring_band(name, col, mat, centre, r_in, thick, width, seg=128):
    prof = rounded_rect(width / 2, r_in, r_in + thick, 0.8)
    cx, cy, cz = centre
    verts, faces, m = [], [], len(prof)
    for i in range(seg):
        t = 2 * math.pi * i / seg
        for u, r in prof:
            verts.append((cx + u, cy + r * math.cos(t), cz + r * math.sin(t)))
    for i in range(seg):
        j = (i + 1) % seg
        for k in range(m):
            k2 = (k + 1) % m
            faces.append([i * m + k, i * m + k2, j * m + k2, j * m + k])
    return MeshBuilder().add(verts, faces).build(name, col, mat)


def strap(name, col, mat, a, b, zc, width, thick, seg=160):
    verts, faces = [], []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        p = np.array([0, a * math.cos(t), zc + b * math.sin(t)])
        n = np.array([0, math.cos(t) / a, math.sin(t) / b]); n /= np.linalg.norm(n)
        for dx, dn in ((-width / 2, -thick / 2), (width / 2, -thick / 2), (width / 2, thick / 2), (-width / 2, thick / 2)):
            verts.append(p + np.array([dx, 0, 0]) + dn * n)
    for i in range(seg):
        j = (i + 1) % seg
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append([i * 4 + k, i * 4 + k2, j * 4 + k2, j * 4 + k])
    return MeshBuilder().add(verts, faces).build(name, col, mat)


def text(name, col, mat, body, loc, rot_deg, size, extrude=0.25):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size * MM
    cu.extrude = extrude * MM
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new(name, cu)
    ob.location = [c * MM for c in loc]
    ob.rotation_euler = [math.radians(a) for a in rot_deg]
    col.objects.link(ob)
    cu.materials.append(mat)
    return ob


# ------------------------------------------------------------------------------------------ scene
def build():
    scene = reset_scene()
    col = collection("Wearable")
    rig = collection("Studio")

    # Materials
    pla = principled("PLA_Graphite", (0.045, 0.045, 0.05, 1), roughness=0.55)
    pla_ring = principled("PLA_Ring", (0.06, 0.055, 0.06, 1), roughness=0.45)
    gold = principled("Gold", (0.95, 0.72, 0.36, 1), metallic=1.0, roughness=0.22)
    smoke = principled("Smoked_Acrylic", (0.55, 0.5, 0.48, 1), roughness=0.06, transmission=1.0, ior=1.49)
    fabric = principled("Strap_Fabric", (0.018, 0.018, 0.02, 1), roughness=0.9)
    pcb_black = principled("PCB_Black", (0.012, 0.012, 0.014, 1), roughness=0.35, coat=0.6)
    pcb_blue = principled("PCB_Blue", (0.01, 0.06, 0.32, 1), roughness=0.35, coat=0.6)
    pcb_purple = principled("PCB_Purple", (0.17, 0.03, 0.33, 1), roughness=0.35, coat=0.6)
    pcb_green = principled("PCB_Green", (0.01, 0.16, 0.05, 1), roughness=0.35, coat=0.6)
    module_pcb = principled("PCB_Module", (0.02, 0.03, 0.08, 1), roughness=0.35, coat=0.6)
    tin = principled("Tin", (0.85, 0.85, 0.87, 1), metallic=1.0, roughness=0.25)
    foil = principled("LiPo_Foil", (0.75, 0.75, 0.78, 1), metallic=0.9, roughness=0.42)
    kapton = principled("Kapton", (0.85, 0.45, 0.05, 1), roughness=0.35)
    chip = principled("IC_Black", (0.02, 0.02, 0.022, 1), roughness=0.5)
    header = principled("Header_Black", (0.015, 0.015, 0.017, 1), roughness=0.6)
    ceramic = principled("Capacitor", (0.55, 0.42, 0.25, 1), roughness=0.5)
    led_r = principled("LED_Red", (0.9, 0.05, 0.03, 1), roughness=0.2)
    led_b = principled("LED_Blue", (0.05, 0.2, 0.95, 1), roughness=0.2)
    cap_red = principled("Button_Red", (0.6, 0.03, 0.03, 1), roughness=0.4)
    wire_mats = [principled("Wire_Red", (0.7, 0.02, 0.02, 1), roughness=0.4),
                 principled("Wire_Black", (0.02, 0.02, 0.02, 1), roughness=0.4),
                 principled("Wire_Yellow", (0.85, 0.6, 0.02, 1), roughness=0.4),
                 principled("Wire_Green", (0.02, 0.45, 0.08, 1), roughness=0.4)]

    anchors = {}

    # ---- strap and wrist pod
    strap("Strap", col, fabric, a=31.0, b=24.0, zc=25.3, width=24.0, thick=2.5)
    anchors["strap"] = (-12, -31.5, 22)
    z0 = 50.5
    boxes("Pod_Case", col, pla, [((-31, -28, z0), (31, 28, z0 + 2)),
                                  ((-31, -28, z0), (-29, 28, z0 + 18)), ((29, -28, z0), (31, 28, z0 + 18)),
                                  ((-31, -28, z0), (31, -26, z0 + 18)), ((-31, 26, z0), (31, 28, z0 + 18))], bevel=0.6)
    # Lid hinged open along the back (+Y) edge so the inside stays visible.
    lid = box("Pod_Lid", col, smoke, (-31, -56, 0), (31, 0, 2), bevel=1.2)
    lid.location = (0, 28.5 * MM, (z0 + 18) * MM)
    lid.rotation_euler = (math.radians(-100), 0, 0)
    anchors["lid"] = (-20, 38.3, 112.5)
    text("Pod_Logo", col, gold, "GEMXPERT", (0, -28.05, 60.5), (90, 0, 0), 5.0)
    boxes("Pod_Ports", col, chip, [((-31.3, -14.2, 62.6), (-30.9, -6.8, 66.6)), ((-31.3, 12.0, 62.4), (-30.9, 19.0, 66.0))])

    # LiPo under the boards, with Kapton tape and leads to the charger
    box("LiPo", col, foil, (-26, -22, z0 + 2), (24, 16, z0 + 7.5), bevel=1.5)
    box("LiPo_Tape", col, kapton, (-27, -2, z0 + 2.2), (-25.8, 6, z0 + 7.3))
    wire("LiPo_Lead_Red", col, wire_mats[0], [(-22, 16.2, 56.5), (-22, 19.5, 59), (-19.5, 22.5, 62.2), (-17, 22.8, 63.6)], r=0.5)
    wire("LiPo_Lead_Black", col, wire_mats[1], [(-19, 16.2, 56.5), (-18.5, 19, 59), (-15.5, 21, 62.2), (-14, 21.2, 63.6)], r=0.5)
    anchors["battery"] = (12, 5.2, 57.6)

    # ESP32 DevKit: 51 x 28 mm, pin headers underneath, WROOM module with shield can and PCB antenna
    pz = 62.0
    box("ESP32_PCB", col, pcb_black, (-27, -24.5, pz), (24, 3.5, pz + 1.6), bevel=0.4)
    hdr = [((-24.5, -24.2, pz - 2.5), (23.5, -21.8, pz)), ((-24.5, 1.0, pz - 2.5), (23.5, 3.4, pz))]
    boxes("ESP32_Headers", col, header, hdr)
    boxes("ESP32_Pins", col, gold, [((-24 + 2.54 * k, y - 0.32, pz + 1.6), (-24 + 2.54 * k + 0.64, y + 0.32, pz + 2.1))
                                     for k in range(19) for y in (-23.0, 2.2)])
    box("ESP32_Module", col, module_pcb, (-1.5, -19.5, pz + 1.6), (24, -1.5, pz + 2.4))
    box("ESP32_Shield", col, tin, (-0.8, -18.6, pz + 2.4), (16.6, -2.4, pz + 5.2), bevel=0.3)
    boxes("ESP32_Antenna", col, gold, [((17.5 + 1.2 * k, -18, pz + 2.4), (17.9 + 1.2 * k, -3, pz + 2.45)) for k in range(5)])
    box("ESP32_USB", col, tin, (-28.2, -14, pz + 1.6), (-23, -7, pz + 4.4), bevel=0.4)
    boxes("ESP32_ICs", col, chip, [((-17.5, -13, pz + 1.6), (-12.5, -8, pz + 2.5)), ((-9.5, -21, pz + 1.6), (-3.5, -17.5, pz + 3.2))])
    boxes("ESP32_Buttons", col, tin, [((-22, -22.5, pz + 1.6), (-18, -19.5, pz + 3.2)), ((-22, -1.5, pz + 1.6), (-18, 1.5, pz + 3.2))])
    boxes("ESP32_Button_Caps", col, chip, [((-21, -21.8, pz + 3.2), (-19, -20.2, pz + 3.8)), ((-21, -0.8, pz + 3.2), (-19, 0.8, pz + 3.8))])
    boxes("ESP32_Caps", col, ceramic, [((-6 + 3 * k, -0.2, pz + 1.6), (-5 + 3 * k, 0.6, pz + 2.3)) for k in range(4)])
    box("ESP32_LED", col, led_r, (-12, -1.2, pz + 1.6), (-10.8, -0.4, pz + 2.2))
    anchors["esp32"] = (8, -10.5, pz + 5.2)

    # TP4056 USB-C charger (26 x 17 mm) and the 3.3 V regulator
    box("TP4056_PCB", col, pcb_blue, (-24, 7, pz), (2, 24, pz + 1.4), bevel=0.3)
    box("TP4056_USBC", col, tin, (-25.6, 12.4, pz + 1.4), (-18.6, 18.6, pz + 4.6), bevel=0.8)
    boxes("TP4056_ICs", col, chip, [((-14.5, 13.5, pz + 1.4), (-9.5, 17.5, pz + 2.9)), ((-5.5, 18, pz + 1.4), (-2.5, 21, pz + 2.4)),
                                    ((-5.5, 10, pz + 1.4), (-2.5, 13, pz + 2.4))])
    box("TP4056_LED_R", col, led_r, (-17, 20, pz + 1.4), (-15.6, 21, pz + 2.0))
    box("TP4056_LED_B", col, led_b, (-17, 10, pz + 1.4), (-15.6, 11, pz + 2.0))
    boxes("TP4056_Pads", col, gold, [((-0.8, 8 + 4.2 * k, pz + 1.4), (1.6, 10 + 4.2 * k, pz + 1.5)) for k in range(4)])
    anchors["tp4056"] = (-11, 16, pz + 2.9)
    box("Regulator_PCB", col, pcb_green, (6, 9.5, pz), (15.5, 19, pz + 1.0), bevel=0.2)
    box("Regulator_Inductor", col, chip, (8.5, 12, pz + 1.0), (12.5, 16, pz + 3.0), bevel=0.4)
    boxes("Regulator_Pins", col, gold, [((14.2, 10.5 + 2.54 * k, pz + 1.0), (15.0, 11.3 + 2.54 * k, pz + 1.6)) for k in range(4)])
    anchors["regulator"] = (10.5, 14, pz + 3.0)

    # Slide switch on the +X wall, recentre button on the +Y wall, cable grommet
    box("Switch_Plate", col, chip, (31, 10.7, 57.8), (32.2, 19.3, 62.2), bevel=0.3)
    box("Switch_Lever", col, header, (32.2, 13.0, 59.3), (33.8, 15.0, 60.7), bevel=0.3)
    anchors["switch"] = (33.8, 14, 60)
    box("Button_Base", col, chip, (31, 0, 60.5), (32.2, 6, 66.5), bevel=0.3)
    cyl("Button_Cap", col, cap_red, (32.2, 3, 63.5), (33.8, 3, 63.5), 1.75)
    anchors["button"] = (33.8, 3, 63.5)
    cyl("Grommet", col, header, (30.6, -8, 57), (32.4, -8, 57), 3.2)

    # ---- ring with the GY-9250 board
    rx = 125.0
    ring_band("Ring_Band", col, pla_ring, (rx, 0, 11), r_in=9.0, thick=2.0, width=6.0)
    box("Ring_Neck", col, pla_ring, (rx - 3, -5.5, 19.5), (rx + 3, 5.5, 22.2), bevel=0.8)
    box("Ring_Pad", col, pla_ring, (rx - 14, -8.8, 21.6), (rx + 14, 8.8, 23.6), bevel=1.0)
    bz = 23.6
    box("GY9250_PCB", col, pcb_purple, (rx - 12.75, -7.75, bz), (rx + 12.75, 7.75, bz + 1.6), bevel=0.3)
    box("GY9250_MPU", col, chip, (rx + 0.5, -0.5, bz + 1.6), (rx + 3.5, 2.5, bz + 2.5), bevel=0.15)
    box("GY9250_LDO", col, chip, (rx + 7, 2.5, bz + 1.6), (rx + 10, 4.1, bz + 2.7))
    boxes("GY9250_Caps", col, ceramic, [((rx - 6 + 2.4 * k, 3.5, bz + 1.6), (rx - 5 + 2.4 * k, 4.1, bz + 2.2)) for k in range(4)])
    pads = [rx + (k - 4.5) * 2.54 for k in range(10)]
    boxes("GY9250_Pads", col, gold, [((x - 0.8, -7.25, bz + 1.6), (x + 0.8, -5.65, bz + 1.68)) for x in pads])
    anchors["sensor"] = (rx + 2, 1, bz + 2.5)
    anchors["ring"] = (rx, -11, 9)

    # ---- the four wires: board pads -> along the table -> into the pod through the grommet
    for k in range(4):
        o = (k - 1.5) * 1.15
        x = pads[k]
        pts = [(x, -6.45, bz + 1.75), (x, -8.0, bz + 3.4), (x - 2, -11.5, bz + 2.8), (x - 9, -16 + o, 19),
               (97, -19 + o, 7), (86, -20 + o, 2.2), (75, -19.5 + o, 1.8), (64, -18 + o, 2.4), (52, -15 + o, 12), (40, -10 + o, 44),
               (34, -8 + o * 0.6, 56), (30.5, -8 + o * 0.6, 57), (26, -8 + o * 0.6, 58)]
        wire(f"Wire_{k}", col, wire_mats[k], pts)
    anchors["cable"] = (70, -18.5, 1.5)

    # ---- studio, camera, render
    studio(rig, target_mm=(55, 0, 38), floor_z_mm=0.0, overhead=True, distance_scale=4.2, energy_scale=0.011)
    cam = camera(rig, (255, -270, 220), (60, 6, 47), lens=47)
    setup_cycles(samples=SAMPLES, width=W, height=H)
    scene.cycles.use_denoising = True

    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    bpy.context.view_layer.update()
    px = {}
    for key, p in anchors.items():
        v = world_to_camera_view(scene, cam, Vector([c * MM for c in p]))
        px[key] = [round(v.x * W, 1), round((1 - v.y) * H, 1)]
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(ANCHORS, "w") as fh:
        json.dump({"size": [W, H], "anchors": px}, fh, indent=1)

    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    save_blend(BLEND)
    render(RAW)
    print("WROTE", RAW, ANCHORS)


build()
