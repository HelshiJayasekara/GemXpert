"""
GemXpert ring settings.

Every ring is built with the same reusable hierarchy (names are the contract with Unity):

    Ring_<Design>              empty, ring origin = centre of the band
      Band                     metal
      Cathedral                metal (prong design only)
      GemMount_Center          empty at the centre stone's GIRDLE CENTRE; +Z = out of the table
        Head_Center            metal prongs + gallery rails (scaled with the stone in Unity)
        Halo_Frame             metal (halo design)          Accent_NN   fixed accent stones (halo design)
        Bezel                  metal (bezel design)
      GemMount_SideL/SideR     three-stone side mounts, each with Head_SideL/R

The gemstone itself is NOT part of the setting export. Unity instantiates the chosen gem under the mount,
so stones are swapped without touching the ring.

All dimensions here are millimetres. Blender axes: Z up, finger along Y.
"""
import math

import numpy as np

import gx_common as gx
import gx_gems as gems


class GemSpec:
    """A gemstone at a given size, with depth/crown/pavilion taken from the generated cut geometry."""

    def __init__(self, cut, length_mm, width_mm):
        self.cut = cut
        self.length = length_mm
        self.width = width_mm
        _, _, info = gems.build_cut_cached(cut)
        self.depth = width_mm * info["depth_ratio"]
        self.crown = self.depth * info["crown_fraction"]
        self.pavilion = self.depth * info["pavilion_fraction"]
        self.outline = gems.cut_outline(cut)
        # The outline is normalised to width 1 x length `aspect`; scale X and Y separately so a stone
        # whose length/width differs from the cut's default (e.g. a 9 x 6 oval) still gets an exact head.
        self._sx = width_mm
        self._sy = length_mm / self.outline.aspect

    def _scaled(self, p, n):
        pp = np.array([p[0] * self._sx, p[1] * self._sy])
        nn = np.array([n[0] / self._sx, n[1] / self._sy])  # normals transform with the inverse scale
        return pp, nn / np.linalg.norm(nn)

    def at(self, azimuth_deg):
        """Girdle point (mm, XY) and outward normal at a polar angle."""
        p, n = gems.outline_at_angle(self.outline, math.radians(azimuth_deg))
        return self._scaled(p, n)

    def loop(self, count=96):
        ts = np.linspace(0.0, 2.0 * math.pi, count, endpoint=False)
        out = [self._scaled(self.outline.point(t), self.outline.normal(t)) for t in ts]
        return np.array([o[0] for o in out]), np.array([o[1] for o in out])


# ----------------------------------------------------------------------------------------- band

def band(inner_diameter, width, thickness, segments=144, profile=24, exponent=3.2):
    """Comfort-fit band swept around the finger axis (Y). Slightly wider and thicker under the head.
    Returns (verts, faces, outer_top_z)."""
    r_in = inner_diameter / 2.0
    e = 2.0 / exponent
    verts, faces = [], []
    for i in range(segments):
        phi = 2.0 * math.pi * i / segments
        top = ((1.0 + math.cos(phi)) / 2.0) ** 2
        w = width * (0.9 + 0.25 * top)
        th = thickness * (0.9 + 0.22 * top)
        for j in range(profile):
            s = 2.0 * math.pi * j / profile
            c, sn = math.cos(s), math.sin(s)
            u = (w / 2.0) * math.copysign(abs(c) ** e, c)
            v = th / 2.0 + (th / 2.0) * math.copysign(abs(sn) ** e, sn)
            r = r_in + v
            verts.append([r * math.sin(phi), u, r * math.cos(phi)])
    for i in range(segments):
        i2 = (i + 1) % segments
        for j in range(profile):
            j2 = (j + 1) % profile
            faces.append([i * profile + j, i2 * profile + j, i2 * profile + j2, i * profile + j2])
    return np.array(verts), faces, r_in + thickness * 1.12


# ----------------------------------------------------------------------------------------- heads

def prong_head(spec, azimuths, base_z, prong_r=0.45, tip_lean=0.3, rails=True):
    """Claw prongs that grip the girdle and fold over the crown, joined by two gallery rails.
    Built in mount-local space (z = 0 at the girdle)."""
    mb = gx.MeshBuilder()
    for az in azimuths:
        p, n = spec.at(az)
        radius = np.linalg.norm(p)
        u = p / radius
        ctrl = [
            [*(u * min(1.2, radius * 0.25)), base_z],
            [*(p * 0.5), -spec.pavilion * 0.88],
            [*(p * 0.86 + n * prong_r * 0.9), -spec.pavilion * 0.42],
            [*(p + n * prong_r * 0.75), 0.0],
            [*(p - u * tip_lean + n * prong_r * 0.2), spec.crown * 0.55 + prong_r * 0.35],
        ]
        path = gx.catmull_rom(ctrl, 8)
        mb.add(*gx.tube(path, np.linspace(prong_r * 1.15, prong_r * 0.92, len(path)), 12))
        mb.add(*gx.sphere(path[-1], prong_r, 14, 10))
    if rails:
        pts, nrm = spec.loop(96)
        for depth_f, scale, push, r in ((0.42, 0.86, prong_r * 0.9, prong_r * 0.72), (0.86, 0.5, 0.0, prong_r * 0.62)):
            ring = pts * scale + nrm * push
            path = np.column_stack([ring, np.full(len(ring), -spec.pavilion * depth_f)])
            mb.add(*gx.tube(path, r, 10, closed=True))
    return mb


def halo(spec, base_z, accent_size=1.3, gap=0.14, clearance=0.35):
    """Metal halo frame + bead prongs + support struts, and the accent stone placements (mount-local).
    Returns (frame MeshBuilder, [accent centre points], accent girdle z)."""
    pts, nrm = spec.loop(240)
    offset = clearance + accent_size / 2.0
    path = pts + nrm * offset
    seg = np.linalg.norm(np.roll(path, -1, axis=0) - path, axis=1)
    perimeter = seg.sum()
    count = int(perimeter // (accent_size + gap))
    accent_spec = GemSpec("round", accent_size, accent_size)
    z_acc = -0.3

    # equal arc-length placement
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    def sample(dist):
        dist %= perimeter
        k = int(np.searchsorted(cum, dist, side="right") - 1)
        f = (dist - cum[k]) / max(seg[k], 1e-9)
        a, b = path[k], path[(k + 1) % len(path)]
        na, nb = nrm[k], nrm[(k + 1) % len(nrm)]
        n = na * (1 - f) + nb * f
        return a * (1 - f) + b * f, n / np.linalg.norm(n)

    step = perimeter / count
    centres = [sample(i * step)[0] for i in range(count)]

    mb = gx.MeshBuilder()
    half = accent_size / 2.0 + 0.22
    bottom = z_acc - accent_spec.pavilion - 0.15
    top = z_acc - 0.06
    profile = [(offset - half, bottom + 0.1), (offset - half + 0.1, bottom), (offset + half - 0.1, bottom),
               (offset + half, bottom + 0.1), (offset + half, top), (offset - half, top)]
    mb.add(*gx.sweep_closed(pts, nrm, profile))

    for i in range(count):  # beads between neighbouring stones, on both edges
        c, n = sample((i + 0.5) * step)
        for side in (-1.0, 1.0):
            mb.add(*gx.sphere([*(c + n * side * (accent_size / 2.0 + 0.02)), z_acc + 0.08], 0.2, 8, 6))

    for az in (45, 135, 225, 315):  # struts down to the band
        p, n = spec.at(az)
        start = np.array([*(p + n * offset), bottom + 0.05])
        end = np.array([*(p / np.linalg.norm(p) * 1.4), base_z])
        mid = (start + end) / 2.0 + np.array([*(n * 0.5), 0.0])
        mb.add(*gx.tube(gx.catmull_rom([start, mid, end], 8), np.linspace(0.42, 0.55, 17), 10))
    return mb, centres, z_acc, accent_spec


def bezel_cup(spec, base_z):
    """Full bezel: a collar around the girdle with a small lip over the crown, plus six support struts."""
    pts, nrm = spec.loop(160)
    profile = [(0.05, -1.35), (0.05, 0.22), (-0.12, 0.33), (0.15, 0.46), (0.75, 0.30),
               (0.80, -1.45), (0.45, -1.95), (-0.25, -1.95)]
    mb = gx.MeshBuilder()
    mb.add(*gx.sweep_closed(pts, nrm, profile))
    for az in range(0, 360, 60):
        p, n = spec.at(az + 30)
        start = np.array([*(p + n * 0.2), -1.85])
        end = np.array([*(p / np.linalg.norm(p) * 1.2), base_z])
        mb.add(*gx.tube(gx.catmull_rom([start, (start + end) / 2 + [0, 0, -0.2], end], 8), np.linspace(0.5, 0.6, 17), 10))
    return mb


def cathedral_arches(spec, mount_z, band_inner_radius, band_thickness):
    """Four slender arched shoulders rising out of the band into the head (ring space).
    Each arch starts buried inside the band (no visible end cap), stays within the band's width,
    tapers as it rises, and finishes tucked behind the upper gallery rail."""
    mb = gx.MeshBuilder()
    r_inside = band_inner_radius + band_thickness * 0.55
    for side in (-1.0, 1.0):
        p, n = spec.at(0 if side > 0 else 180)
        for y in (-1.0, 1.0):
            phi = math.radians(36.0) * side
            start = np.array([r_inside * math.sin(phi), y * 0.6, r_inside * math.cos(phi)])
            rise = np.array([r_inside * 1.08 * math.sin(phi * 0.82), y * 0.6, r_inside * 1.08 * math.cos(phi * 0.82)])
            end = np.array([p[0] * 0.72, y * 0.5, mount_z - spec.pavilion * 0.45])
            crest = np.array([(rise[0] + end[0]) * 0.5 + side * 0.85, y * 0.56, (rise[2] + end[2]) * 0.5 + 0.55])
            path = gx.catmull_rom([start, rise, crest, end], 10)
            mb.add(*gx.tube(path, np.linspace(0.52, 0.34, len(path)), 14))
    return mb


# ----------------------------------------------------------------------------------------- designs

DESIGNS = {
    # id: (object name, clearance above band in mm)
    "solitaire": ("Ring_Solitaire", 1.0),
    "halo": ("Ring_Halo", 0.9),
    "three_stone": ("Ring_ThreeStone", 0.8),
    "prong": ("Ring_Prong", 1.6),
    "bezel": ("Ring_Bezel", 0.45),
}


def build_ring(ring_def, shapes, metal_mat, accent_mat, col):
    """Builds one ring setting from its rings.json entry. Returns (root, metadata, preview_specs)."""
    rid = ring_def["id"]
    name, clearance = DESIGNS[rid]
    root = gx.empty(name, col, size_mm=4)

    bv, bf, band_top = band(ring_def["innerDiameterMm"], ring_def["bandWidthMm"], ring_def["bandThicknessMm"])
    gx.MeshBuilder().add(bv, bf).build("Band", col, metal_mat, parent=root)

    shape = shapes[ring_def["defaultShapeId"]]
    center = GemSpec(shape["id"], shape["defaultLengthMm"], shape["defaultWidthMm"])
    mount_z = band_top + clearance + center.pavilion
    mount = gx.empty("GemMount_Center", col, (0, 0, mount_z), parent=root)
    base_z = band_top - mount_z - 0.35  # slightly embedded in the band

    meta = {"id": rid, "object": name, "bandOuterTopMm": band_top, "mounts": {}, "accentStones": 0}
    meta["mounts"]["Center"] = {"blenderPositionMm": [0.0, 0.0, mount_z], "blenderRotationDeg": [0.0, 0.0, 0.0],
                                "headDefaultLengthMm": center.length, "headDefaultWidthMm": center.width,
                                "defaultShape": center.cut}
    previews = [("Center", mount, center)]

    if rid == "solitaire":
        prong_head(center, [45, 135, 225, 315], base_z).build("Head_Center", col, metal_mat, parent=mount)

    elif rid == "halo":
        prong_head(center, [45, 135, 225, 315], base_z, prong_r=0.36, tip_lean=0.25).build(
            "Head_Center", col, metal_mat, parent=mount)
        frame, centres, z_acc, accent_spec = halo(center, base_z)
        frame.build("Halo_Frame", col, metal_mat, parent=mount)
        av, af, _ = gems.build_cut_cached("round")
        shared = gx.MeshBuilder().add(av * [accent_spec.width, accent_spec.length, accent_spec.depth], af) \
            .build("Accent_00", col, accent_mat, smooth=False, parent=mount)
        shared.location = [centres[0][0] * gx.MM, centres[0][1] * gx.MM, z_acc * gx.MM]
        for i, c in enumerate(centres[1:], start=1):
            ob = shared.copy()  # linked duplicate: shares the mesh data
            ob.name = f"Accent_{i:02d}"
            ob.location = [c[0] * gx.MM, c[1] * gx.MM, z_acc * gx.MM]
            col.objects.link(ob)
            ob.parent = mount
        meta["accentStones"] = len(centres)
        meta["accentSizeMm"] = accent_spec.width

    elif rid == "three_stone":
        prong_head(center, [40, 140, 220, 320], base_z).build("Head_Center", col, metal_mat, parent=mount)
        for mount_def in ring_def["mounts"]:
            if mount_def["role"] != "side":
                continue
            side = GemSpec(mount_def["fixedShapeId"], mount_def["fixedLengthMm"], mount_def["fixedLengthMm"])
            # Unity "SideL" (x < 0) is Blender +X because the FBX conversion mirrors X.
            sign = 1.0 if mount_def["id"] == "SideL" else -1.0
            x = sign * (center.width / 2.0 + side.width / 2.0 + 1.1)
            tilt = 14.0 * sign
            z = mount_z - 1.2  # side stones sit a little lower than the centre stone
            side_mount = gx.empty(f"GemMount_{mount_def['id']}", col, (x, 0, z), (0, tilt, 0), parent=root)
            # Prong bases must reach the curved band surface below the (tilted) side mount.
            band_z_below = math.sqrt(max(band_top ** 2 - (abs(x) * 0.85) ** 2, 0.0)) - 0.4
            side_base = -(z - band_z_below) / math.cos(math.radians(abs(tilt)))
            prong_head(side, [45, 135, 225, 315], side_base, prong_r=0.33, tip_lean=0.18).build(
                f"Head_{mount_def['id']}", col, metal_mat, parent=side_mount)
            meta["mounts"][mount_def["id"]] = {"blenderPositionMm": [x, 0.0, z], "blenderRotationDeg": [0.0, tilt, 0.0],
                                               "headDefaultLengthMm": side.length, "headDefaultWidthMm": side.width,
                                               "defaultShape": side.cut}
            previews.append((mount_def["id"], side_mount, side))

    elif rid == "prong":
        prong_head(center, [0, 60, 120, 180, 240, 300], base_z, prong_r=0.4).build(
            "Head_Center", col, metal_mat, parent=mount)
        cathedral_arches(center, mount_z, ring_def["innerDiameterMm"] / 2.0, ring_def["bandThicknessMm"]).build(
            "Cathedral", col, metal_mat, parent=root)

    elif rid == "bezel":
        bezel_cup(center, base_z).build("Bezel", col, metal_mat, parent=mount)

    return root, meta, previews


# ----------------------------------------------------------------------------------------- custom (ring spec)

HEAD_CLEARANCE = {"low": 0.45, "medium": 1.0, "high": 1.6}
PRONG_LAYOUTS = {4: [45, 135, 225, 315], 6: [0, 60, 120, 180, 240, 300], 8: [22.5 + 45 * k for k in range(8)]}


def build_custom_ring(spec, metal_mat, accent_mat, col):
    """Builds a ring from a GemXpert ring spec (the JSON the "From a photo" screen produces).
    Mirrors the JavaScript generator in Prototype/Interface/index.html so both give the same ring.
    Returns (root, metadata, preview_specs)."""
    style = spec["style"]
    name = spec.get("objectName") or "Ring_Custom"
    root = gx.empty(name, col, size_mm=4)
    inner_d = spec.get("innerDiameterMm", 17.3)
    bv, bf, band_top = band(inner_d, spec["bandWidthMm"], spec["bandThicknessMm"])
    gx.MeshBuilder().add(bv, bf).build("Band", col, metal_mat, parent=root)

    st = spec["stone"]
    center = GemSpec(st["shapeId"], st["lengthMm"], st["widthMm"])
    clearance = HEAD_CLEARANCE.get(spec.get("headHeight", "medium"), 1.0)
    mount_z = band_top + clearance + center.pavilion
    mount = gx.empty("GemMount_Center", col, (0, 0, mount_z), parent=root)
    base_z = band_top - mount_z - 0.35
    meta = {"id": spec.get("id", "custom"), "object": name, "bandOuterTopMm": band_top, "mounts": {}, "accentStones": 0}
    meta["mounts"]["Center"] = {"blenderPositionMm": [0.0, 0.0, mount_z], "blenderRotationDeg": [0.0, 0.0, 0.0],
                                "headDefaultLengthMm": center.length, "headDefaultWidthMm": center.width,
                                "defaultShape": center.cut}
    previews = [("Center", mount, center)]
    prongs = PRONG_LAYOUTS.get(int(spec.get("prongs", 4)), PRONG_LAYOUTS[4])

    if style == "bezel":
        bezel_cup(center, base_z).build("Bezel", col, metal_mat, parent=mount)
    elif style == "halo":
        prong_head(center, PRONG_LAYOUTS[4], base_z, prong_r=0.36, tip_lean=0.25).build("Head_Center", col, metal_mat, parent=mount)
        accent = spec.get("halo", {}).get("accentSizeMm", 1.3)
        frame, centres, z_acc, accent_spec = halo(center, base_z, accent_size=accent)
        frame.build("Halo_Frame", col, metal_mat, parent=mount)
        av, af, _ = gems.build_cut_cached("round")
        shared = gx.MeshBuilder().add(av * [accent_spec.width, accent_spec.length, accent_spec.depth], af) \
            .build("Accent_00", col, accent_mat, smooth=False, parent=mount)
        shared.location = [centres[0][0] * gx.MM, centres[0][1] * gx.MM, z_acc * gx.MM]
        for i, c in enumerate(centres[1:], start=1):
            ob = shared.copy()
            ob.name = f"Accent_{i:02d}"
            ob.location = [c[0] * gx.MM, c[1] * gx.MM, z_acc * gx.MM]
            col.objects.link(ob)
            ob.parent = mount
        meta["accentStones"], meta["accentSizeMm"] = len(centres), accent
    else:
        prong_r = 0.45 if len(prongs) == 4 else 0.4
        prong_head(center, prongs, base_z, prong_r=prong_r).build("Head_Center", col, metal_mat, parent=mount)
        if style == "three_stone":
            size = spec.get("sideStones", {}).get("sizeMm", 4.0)
            side = GemSpec("round", size, size)
            for mid, sign in (("SideL", 1.0), ("SideR", -1.0)):
                x = sign * (center.width / 2.0 + size / 2.0 + 1.1)
                tilt = 14.0 * sign
                z = mount_z - 1.2
                sm = gx.empty(f"GemMount_{mid}", col, (x, 0, z), (0, tilt, 0), parent=root)
                band_z_below = math.sqrt(max(band_top ** 2 - (abs(x) * 0.85) ** 2, 0.0)) - 0.4
                side_base = -(z - band_z_below) / math.cos(math.radians(abs(tilt)))
                prong_head(side, PRONG_LAYOUTS[4], side_base, prong_r=0.33, tip_lean=0.18).build(
                    f"Head_{mid}", col, metal_mat, parent=sm)
                meta["mounts"][mid] = {"blenderPositionMm": [x, 0.0, z], "blenderRotationDeg": [0.0, tilt, 0.0],
                                       "headDefaultLengthMm": size, "headDefaultWidthMm": size, "defaultShape": "round"}
                previews.append((mid, sm, side))
        if spec.get("cathedral"):
            cathedral_arches(center, mount_z, inner_d / 2.0, spec["bandThicknessMm"]).build("Cathedral", col, metal_mat, parent=root)
    return root, meta, previews
