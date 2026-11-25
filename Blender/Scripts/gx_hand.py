"""
GemXpert simulated hand: a realistic adult LEFT hand, palm down, used to try rings on.

Frame (Blender, millimetres while building): fingers point to -Y, back of the hand (dorsal) is +Z,
thumb on the -X side. The ring finger's proximal phalanx lies along -Y through the origin, which is the
ring position: the RingAnchor_RingFinger empty sits at the origin with identity rotation, so a ring
(band axis Y, head +Z) placed at the anchor sits on the finger with its stone on the back of the hand.

Construction: anatomical parts (lofted fingers with knuckle bulges and fingertip pads, palm/back of hand,
thenar & hypothenar muscles, MCP knuckles, extensor tendons, thumb) are fused into one organic skin with a
voxel remesh, smoothed, decimated for real-time use, and given baked skin-tone variation. Nails are separate
glossy meshes fitted to the skin surface by ray casting.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import gx_common as gx

UP = np.array([0.0, 0.0, 1.0])

FINGERS = [
    # mcp (mm), segment lengths (proximal, middle, distal), widths at
    # (MCP, ring station, PIP, mid-middle, DIP, mid-distal), splay (deg, + towards +X), flex (MCP, PIP, DIP) deg
    dict(name="Index", mcp=(-39.5, 15.0, 0.0), seg=(44.0, 27.0, 22.0), w=(19.5, 18.0, 18.6, 16.6, 15.8, 14.6), splay=-6.0, flex=(3.0, 14.0, 9.0)),
    dict(name="Middle", mcp=(-20.0, 18.0, 0.5), seg=(48.0, 31.0, 24.0), w=(20.0, 18.5, 19.2, 17.2, 16.2, 15.0), splay=-2.0, flex=(2.0, 12.0, 8.0)),
    dict(name="Ring", mcp=(0.0, 13.5, 0.0), seg=(45.0, 28.0, 23.0), w=(18.6, 16.6, 17.8, 15.8, 15.0, 14.0), splay=0.0, flex=(0.0, 13.0, 8.0)),
    dict(name="Pinky", mcp=(18.5, 4.0, -1.5), seg=(34.0, 21.0, 20.0), w=(16.0, 14.6, 15.2, 13.6, 13.0, 12.0), splay=7.0, flex=(4.0, 15.0, 9.0)),
]
THUMB = dict(name="Thumb", mcp=(-44.0, 68.0, -11.0), seg=(36.0, 30.0, 26.0), w=(25.0, 22.5, 21.5, 20.0, 19.5, 18.0),
             direction=(-0.60, -0.76, -0.10), flex=(4.0, 10.0, 12.0), up_hint=(-0.62, 0.0, 0.78), inside=10.0)


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _rotate(v, axis, deg):
    """Rodrigues rotation of v about a unit axis."""
    a = math.radians(deg)
    k = _unit(axis)
    return v * math.cos(a) + np.cross(k, v) * math.sin(a) + k * np.dot(k, v) * (1 - math.cos(a))


def _pitch_down(d, deg):
    lateral = np.cross(d, UP)
    if np.linalg.norm(lateral) < 1e-6:
        return d
    return _unit(_rotate(d, lateral, -deg))


# ----------------------------------------------------------------------------------------- digit

def digit_geometry(spec, ring_station=False):
    """Returns (verts, faces, info) for one finger/thumb as a closed lofted solid (mm)."""
    p, m, dl = spec["seg"]
    w = spec["w"]
    if "direction" in spec:
        d0 = _unit(spec["direction"])
    else:
        a = math.radians(spec["splay"])
        d0 = np.array([math.sin(a), -math.cos(a), 0.0])
    up_hint = _unit(spec.get("up_hint", UP))
    mcp = np.array(spec["mcp"], float)
    d1 = _pitch_down(d0, spec["flex"][0])
    pip = mcp + d1 * p
    d2 = _pitch_down(d1, spec["flex"][1])
    dip = pip + d2 * m
    d3 = _pitch_down(d2, spec["flex"][2])
    tip = dip + d3 * dl
    inside = spec.get("inside", 14.0)
    start = mcp - d1 * inside

    # station table along the finger: (arc length from MCP, width, dorsal half-height, palmar half-height, knuckle bump)
    total = p + m + dl
    st = [
        (-inside, w[0] * 1.06, 0.42, 0.48, 0.0),
        (0.0, w[0], 0.42, 0.48, 0.0),
        (p * 0.30, w[1], 0.40, 0.45, 0.0),
        (p, w[2], 0.40, 0.45, 1.1),
        (p + m * 0.5, w[3], 0.38, 0.46, 0.0),
        (p + m, w[4], 0.38, 0.45, 0.7),
        (p + m + dl * 0.55, w[5], 0.36, 0.48, 0.0),
        (total, w[5] * 0.93, 0.34, 0.47, 0.0),
    ]
    if ring_station:
        # Ring position: rounder, slightly fuller on top so the 17.3 mm band rests on the back of the finger.
        st[2] = (p * 0.30, w[1], 8.1 / w[1], 7.3 / w[1], 0.0)

    ctrl = [start, mcp, pip, dip, tip]
    path = gx.catmull_rom(ctrl, 14)
    seg_len = np.linalg.norm(np.diff(path, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg_len)]) - inside
    # scale arc so the joints land on their nominal stations
    arc = (arc + inside) / (arc[-1] + inside) * (total + inside) - inside

    s_tab = np.array([x[0] for x in st])
    def interp(col, s):
        return float(np.interp(s, s_tab, np.array([x[col] for x in st])))

    ring_n = 28
    verts, faces = [], []
    tangents = []
    for i in range(len(path)):
        a_ = path[max(i - 1, 0)]
        b_ = path[min(i + 1, len(path) - 1)]
        tangents.append(_unit(b_ - a_))
    exponent = 2.0 / 2.25

    def section(centre, t, s, scale=1.0):
        lat = np.cross(t, up_hint)
        lat = lat / np.linalg.norm(lat)
        dor = np.cross(lat, t)
        width = interp(1, s)
        hd, hp = interp(2, s) * width, interp(3, s) * width
        # knuckle bumps as gaussian bulges on the back of the joint
        bump = sum(b * math.exp(-((s - js) / 3.2) ** 2) for js, b in ((p, st[3][4]), (p + m, st[5][4])))
        pts = []
        for j in range(ring_n):
            ang = 2 * math.pi * j / ring_n
            c, sn = math.cos(ang), math.sin(ang)
            x = (width / 2) * math.copysign(abs(c) ** exponent, c)
            y = (hd if sn > 0 else hp) * math.copysign(abs(sn) ** exponent, sn)
            if sn > 0:
                y += bump * sn ** 4
            pts.append(centre + (lat * x + dor * y) * scale)
        return pts

    for i, c in enumerate(path):
        verts.extend(section(c, tangents[i], arc[i]))
    rings = len(path)
    # fingertip pad: shrinking rings beyond the tip, palmar side fuller
    cap_len = 0.48 * w[5]
    t_end = tangents[-1]
    for k, f in enumerate((0.25, 0.48, 0.66, 0.8, 0.9, 0.96)):
        sc = math.sqrt(max(1 - f * f, 0.02))
        centre = path[-1] + t_end * cap_len * f - np.cross(np.cross(t_end, up_hint), t_end) / 1.0 * 0.6 * f
        verts.extend(section(centre, t_end, total, sc))
        rings += 1
    apex = path[-1] + t_end * cap_len - _unit(np.cross(np.cross(t_end, up_hint), t_end)) * 0.8
    for r in range(rings - 1):
        for j in range(ring_n):
            j2 = (j + 1) % ring_n
            faces.append([r * ring_n + j, (r + 1) * ring_n + j, (r + 1) * ring_n + j2, r * ring_n + j2])
    verts.append(apex)
    ai = len(verts) - 1
    base = (rings - 1) * ring_n
    for j in range(ring_n):
        faces.append([base + j, ai, base + (j + 1) % ring_n])
    verts.append(path[0])
    si = len(verts) - 1
    for j in range(ring_n):
        faces.append([(j + 1) % ring_n, si, j])

    info = {"name": spec["name"], "mcp": mcp, "pip": pip, "dip": dip, "tip": tip, "d3": d3, "w": w,
            "up": up_hint, "distal": dl, "cap": cap_len}
    return np.array(verts), faces, info


# ----------------------------------------------------------------------------------------- palm

def palm_geometry():
    """Back of the hand + palm + wrist stub, lofted along +Y (from the knuckles to the forearm)."""
    # (y, centre x, width, top z, bottom z)
    sections = [
        (2.0, -11.0, 74.0, 6.5, -13.0),
        (10.0, -11.5, 80.0, 8.5, -16.0),
        (40.0, -12.0, 84.0, 9.5, -20.0),
        (72.0, -11.0, 78.0, 10.0, -21.5),
        (98.0, -9.0, 62.0, 9.0, -17.5),
        (125.0, -8.5, 57.0, 9.5, -18.5),
        (150.0, -8.5, 61.0, 10.5, -20.0),
    ]
    n = 48
    e = 2.0 / 2.6
    verts, faces = [], []

    def ring(y, cx, w, top, bot, scale=1.0, dy=0.0):
        cz = (top + bot) / 2
        hh = (top - bot) / 2
        out = []
        for j in range(n):
            a = 2 * math.pi * j / n
            c, s = math.cos(a), math.sin(a)
            out.append([cx + (w / 2) * scale * math.copysign(abs(c) ** e, c), y + dy,
                        cz + hh * scale * math.copysign(abs(s) ** e, s)])
        return out

    y0 = sections[0]
    rows = []
    for f in (0.35, 0.62, 0.82, 0.94):  # rounded front edge under the knuckles
        rows.append(ring(y0[0], y0[1], y0[2], y0[3], y0[4], math.sqrt(1 - (1 - f) ** 2), -(1 - f) * 9))
    for sec in sections:
        rows.append(ring(*sec))
    for r in rows:
        verts.extend(r)
    for r in range(len(rows) - 1):
        for j in range(n):
            j2 = (j + 1) % n
            faces.append([r * n + j, r * n + j2, (r + 1) * n + j2, (r + 1) * n + j])
    for idx, row_i in ((0, 0), (1, len(rows) - 1)):
        c = np.mean(rows[row_i], axis=0)
        verts.append(c)
        ci = len(verts) - 1
        for j in range(n):
            a, b = row_i * n + j, row_i * n + (j + 1) % n
            faces.append([ci, a, b] if idx == 0 else [ci, b, a])
    return np.array(verts), faces


def ellipsoid(centre, radii, u=24, v=16):
    verts, faces = gx.sphere([0, 0, 0], 1.0, u, v)
    return verts * np.array(radii) + np.array(centre), faces


# ----------------------------------------------------------------------------------------- build

def _mesh_object(name, verts, faces, col):
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.asarray(verts).tolist(), [], faces)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


def _evaluated_copy(ob, name):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.name = name
    return me


def build_hand(col, skin_mat, nail_mat, voxel_mm=0.55, target_tris=48000):
    """Builds the hand in `col`. Returns (skin_object, nails_object, anchor_empty, metadata)."""
    parts = gx.MeshBuilder()
    infos = []
    for spec in FINGERS:
        v, f, info = digit_geometry(spec, ring_station=(spec["name"] == "Ring"))
        parts.add(v, f)
        infos.append(info)
        # MCP knuckle on the back of the hand
        w0 = spec["w"][0]
        parts.add(*ellipsoid(np.array(spec["mcp"]) + [0, 2.0, 0.24 * w0], (0.34 * w0, 0.36 * w0, 0.26 * w0)))
        # extensor tendon from the knuckle towards the wrist
        top = np.array(spec["mcp"]) + [0, 6.0, 0.30 * w0]
        wrist = np.array([-9.0 + spec["mcp"][0] * 0.25, 100.0, 7.2])
        path = gx.catmull_rom([top, (top + wrist) / 2 + [0, 0, 1.2], wrist], 10)
        parts.add(*gx.tube(path, np.linspace(1.9, 1.3, len(path)), 10))
    v, f, info = digit_geometry(THUMB)
    parts.add(v, f)
    infos.append(info)
    parts.add(*palm_geometry())
    parts.add(*ellipsoid((-37.0, 68.0, -13.0), (17.0, 27.0, 12.5)))   # thenar (thumb muscle)
    parts.add(*ellipsoid((19.0, 66.0, -12.5), (11.0, 30.0, 9.5)))     # hypothenar
    parts.add(*ellipsoid((-11.0, 30.0, -15.0), (34.0, 16.0, 7.0)))    # palm pads under the knuckles

    raw = _mesh_object("HandRaw", np.concatenate(parts.verts), parts.faces, col)
    rm = raw.modifiers.new("Remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel_mm
    rm.adaptivity = 0.0
    sm = raw.modifiers.new("Smooth", "SMOOTH")
    sm.factor = 0.55
    sm.iterations = 12
    fused = _evaluated_copy(raw, "Hand_Skin_Hi")
    bpy.data.objects.remove(raw, do_unlink=True)

    hi = bpy.data.objects.new("HandHi", fused)
    col.objects.link(hi)
    tris = sum(len(p.vertices) - 2 for p in fused.polygons)
    dec = hi.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = min(1.0, target_tris / max(tris, 1))
    low = _evaluated_copy(hi, "Hand_Skin")
    bpy.data.objects.remove(hi, do_unlink=True)
    bpy.data.meshes.remove(fused)

    skin = bpy.data.objects.new("Hand_Skin", low)
    col.objects.link(skin)
    for poly in low.polygons:
        poly.use_smooth = True
    _paint_skin(low, infos)

    nails = _build_nails(low, infos, col)

    # metres for export
    s = Matrix.Scale(gx.MM, 4)
    low.transform(s)
    nails.data.transform(s)
    low.materials.append(skin_mat)
    nails.data.materials.append(nail_mat)

    root = gx.empty("SimulatedHand_L", col, size_mm=20)
    skin.parent = root
    nails.parent = root
    anchor = gx.empty("RingAnchor_RingFinger", col, (0, 0, 0), parent=root, size_mm=6)
    meta = {"skinTriangles": sum(len(p.vertices) - 2 for p in low.polygons),
            "nailTriangles": sum(len(p.vertices) - 2 for p in nails.data.polygons),
            "ringFingerWidthAtRingMm": FINGERS[2]["w"][1], "handedness": "left", "anchor": "RingAnchor_RingFinger"}
    return root, skin, nails, anchor, meta


# ----------------------------------------------------------------------------------------- skin colour

def _srgb(hexcode):
    h = hexcode.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def _paint_skin(me, infos):
    """Bakes skin-tone variation as a vertex colour: warmer/redder over knuckles, joints and fingertips,
    paler on the back of the hand, pinker on the palm side, plus faint mottling."""
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    nrm = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("normal", nrm)
    nrm = nrm.reshape(-1, 3)

    base = _srgb("#D7A184")
    warm = _srgb("#C9806A")
    pale = _srgb("#E2B497")
    palm = _srgb("#DDA08C")

    red = np.zeros(len(co))
    for inf in infos:
        for pt, r, k in ((inf["mcp"], 9.0, 0.55), (inf["pip"], 6.5, 0.75), (inf["dip"], 5.0, 0.6), (inf["tip"], 8.0, 0.8)):
            d2 = np.sum((co - pt) ** 2, axis=1)
            red = np.maximum(red, k * np.exp(-d2 / (r * r)))
    back = np.clip((co[:, 1] - 20.0) / 60.0, 0, 1) * np.clip(nrm[:, 2], 0, 1)
    palmar = np.clip(-nrm[:, 2], 0, 1)
    rng = np.random.default_rng(7)
    mottling = (np.sin(co[:, 0] * 0.9) * np.sin(co[:, 1] * 0.7) * np.sin(co[:, 2] * 1.1)) * 0.02 + rng.normal(0, 0.006, len(co))

    col = base[None, :] * (1 - red[:, None]) + warm[None, :] * red[:, None]
    col = col * (1 - 0.6 * back[:, None]) + pale[None, :] * (0.6 * back[:, None])
    col = col * (1 - 0.5 * palmar[:, None]) + palm[None, :] * (0.5 * palmar[:, None])
    col = np.clip(col + mottling[:, None], 0, 1)
    rgba = np.concatenate([col, np.ones((len(col), 1))], axis=1).ravel()

    attr = me.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    attr.data.foreach_set("color_srgb", rgba)
    me.color_attributes.active_color = attr
    try:
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    except Exception:
        pass


# ----------------------------------------------------------------------------------------- nails

def _build_nails(skin_me, infos, col):
    """Glossy nails fitted to the skin: a thin curved plate on each distal phalanx, found by ray casting."""
    co = [v.co.copy() for v in skin_me.vertices]
    polys = [tuple(p.vertices) for p in skin_me.polygons]
    bvh = BVHTree.FromPolygons(co, polys)
    nu, nv = 13, 12
    all_v, all_f, colors = [], [], []
    nail_base, nail_edge, lunula = _srgb("#D9A396"), _srgb("#EDDDD1"), _srgb("#E6C1B5")

    for inf in infos:
        d3 = _unit(inf["d3"])
        lat = _unit(np.cross(d3, inf["up"]))
        dor = _unit(np.cross(lat, d3))
        dl, w5 = inf["distal"], inf["w"][5]
        hw0 = 0.335 * w5
        s0, s1 = dl * 0.32, dl + inf["cap"] * 0.18  # cuticle to a short natural free edge
        top, bot = [], []
        last_ok = None
        for iv in range(nv):
            v = iv / (nv - 1)
            s = s0 + (s1 - s0) * v
            if v > 0.7:      # oval free edge
                hw = hw0 * math.sqrt(max(1 - ((v - 0.7) / 0.3) ** 2 * 0.8, 0.1))
            elif v < 0.18:   # rounded cuticle
                hw = hw0 * math.sqrt(max(1 - ((0.18 - v) / 0.18) ** 2 * 0.55, 0.1))
            else:
                hw = hw0
            row_t, row_b, hits = [], [], []
            for iu in range(nu):
                u = -1 + 2 * iu / (nu - 1)
                axis_pt = inf["dip"] + d3 * s
                probe = axis_pt + lat * u * hw
                hit = None
                if v <= 0.8:
                    loc, _n, _i, _d = bvh.ray_cast(Vector(probe + dor * 25.0), Vector(-dor))
                    if loc is not None:
                        hit = np.array(loc)
                if hit is None:
                    # free edge: continue the plate straight past the fingertip
                    ref = last_ok[iu] if last_ok else probe + dor * (0.34 * w5)
                    hit = ref + d3 * ((s1 - s0) / (nv - 1))
                hits.append(hit)
                thick = 0.08 + 0.22 * (1 - u * u)  # domed, nearly flush with the skin at the side folds
                row_t.append(hit + dor * thick)
                row_b.append(hit - dor * (0.2 if v <= 0.8 else 0.12))
                c = nail_edge if v > 0.9 else (lunula if (v < 0.2 and abs(u) < 0.55) else nail_base)
                colors.append(c)
            last_ok = hits  # each free-edge row continues one step beyond the previous row
            top.append(row_t)
            bot.append(row_b)
        base_i = len(all_v)
        for row in top:
            all_v.extend(row)
        colors.extend(colors[-nu * nv:])
        for row in bot:
            all_v.extend(row)
        off = nu * nv
        for iv in range(nv - 1):
            for iu in range(nu - 1):
                a = base_i + iv * nu + iu
                all_f.append([a, a + 1, a + nu + 1, a + nu])                      # top
                all_f.append([off + a, off + a + nu, off + a + nu + 1, off + a + 1])  # bottom
        ring_idx = [iv * nu for iv in range(nv)] + [(nv - 1) * nu + iu for iu in range(1, nu)] + \
                   [iv * nu + nu - 1 for iv in range(nv - 2, -1, -1)] + [iu for iu in range(nu - 2, 0, -1)]
        for k in range(len(ring_idx)):
            a, b = base_i + ring_idx[k], base_i + ring_idx[(k + 1) % len(ring_idx)]
            all_f.append([a, off + a, off + b, b])

    me = bpy.data.meshes.new("Hand_Nails")
    me.from_pydata(np.array(all_v).tolist(), [], all_f)
    me.validate()
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    attr = me.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    rgba = np.concatenate([np.array(colors[:len(me.vertices)]), np.ones((len(me.vertices), 1))], axis=1).ravel()
    attr.data.foreach_set("color_srgb", rgba)
    me.color_attributes.active_color = attr
    ob = bpy.data.objects.new("Hand_Nails", me)
    col.objects.link(ob)
    return ob


# ----------------------------------------------------------------------------------------- materials

def skin_material():
    mat = gx.principled("Skin", (0.6, 0.38, 0.28, 1), roughness=0.47)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    gx._set_input(bsdf, ["Subsurface Weight", "Subsurface"], 0.35)
    gx._set_input(bsdf, "Subsurface Radius", (1.0, 0.35, 0.2))
    gx._set_input(bsdf, "Subsurface Scale", 0.0025)  # 2.5 mm in metres
    gx._set_input(bsdf, ["Specular IOR Level", "Specular"], 0.42)
    gx._set_input(bsdf, ["Coat Weight", "Clearcoat"], 0.06)
    return mat


def nail_material():
    mat = gx.principled("Nail", (0.85, 0.62, 0.57, 1), roughness=0.16, coat=0.7)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    gx._set_input(bsdf, ["Subsurface Weight", "Subsurface"], 0.2)
    gx._set_input(bsdf, "Subsurface Scale", 0.001)
    return mat
