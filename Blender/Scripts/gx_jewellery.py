"""
GemXpert pendants, necklaces, bracelets and earring pairs.

Built with the same contract as the rings (gx_rings.py), so the web app and Unity treat them the same way:

    <Piece_Name>               empty at the origin
      Chain / Links / Clasp    metal (fixed, not scaled)
      Collet / Station         metal settings for the fixed accent stones
      Accent_*                 fixed accent stones (one merged mesh each)
      Band                     bangle body (bracelets)
      GemMount_Center          empty at the centre stone's GIRDLE CENTRE; local +Z = out of the table
        Head_Center / Halo_Frame / Bezel / Accent_Halo   scaled with the stone by the app
        Attach_Bail            bail around the chain. NOT scaled: the app keeps it fixed and scales the head
                               about this object's origin, so a bigger stone simply hangs lower
      GemMount_SideL/SideR     fixed side stones (bangle)
      GemMount_Pair            the second earring of a pair: same heads, follows the Center stone
        Attach_Post / Attach_Back   stud post and butterfly or screw back (not scaled)
        Drop_Center / Drop_Pair     a chain and a claw-set drop hanging from the head. NOT scaled: the app moves it
                                    so it stays on the bottom of the head as the stone grows
          AccentMatch_Drop          the drop stone; the app gives it the same gemstone as the centre stone
      AccentPink_*             fixed accent stones the app shows as pink sapphire (catalogue "accentGems")

Pendants and necklaces are modelled in "bust space": they lie on the velvet display bust (Display_Bust) exactly as
they would in a shop window (a classic white display bust). Blender axes: Z up, the bust faces -Y. Bracelets use ring axes: the wrist runs along
Y and the centre stone is at the top (+Z). All helpers take millimetres.
"""
import math

import numpy as np

import gx_common as gx
import gx_gems as gems
from gx_rings import GemSpec, bezel_cup, halo, prong_head

# Gem materials by gemstone id, set by build_jewellery.py, for accents that are not diamond (pink pave, matching drops).
GEM_MATS = {}


def gem_mat(gem_id, fallback):
    return GEM_MATS.get(gem_id, fallback)


def center_spec(piece, shapes):
    """The centre stone a piece is modelled around: the piece's own default size if it has one, else the cut's."""
    shape = shapes[piece["defaultShapeId"]]
    return GemSpec(shape["id"], piece.get("defaultStoneLengthMm", shape["defaultLengthMm"]),
                   piece.get("defaultStoneWidthMm", piece.get("defaultStoneLengthMm", shape["defaultWidthMm"])))


def pave_stone(size, sides=8):
    """Low-poly round accent for pave work (33 faces at 8 sides, 19 at 6): reads as a brilliant at 1 mm, and a flower
    carries ~150 of them."""
    r, rt, zc, zp = size / 2, size * 0.28, size * 0.16, -size * 0.42
    st = 360.0 / sides
    g = [[r * math.cos(math.radians(st * k)), r * math.sin(math.radians(st * k)), 0.0] for k in range(sides)]
    t = [[rt * math.cos(math.radians(st * k + st / 2)), rt * math.sin(math.radians(st * k + st / 2)), zc] for k in range(sides)]
    faces = [list(range(sides, 2 * sides))]
    for k in range(sides):
        k2 = (k + 1) % sides
        faces += [[k, k2, sides + k], [sides + k, k2, sides + k2], [k2, k, 2 * sides]]
    return np.array(g + t + [[0.0, 0.0, zp]]), faces


# ----------------------------------------------------------------------------------------- small helpers


def arrays(mb):
    return np.concatenate(mb.verts), list(mb.faces)


def frame(z_axis, x_hint):
    """Rotation matrix whose columns are (x, y, z) with z = z_axis and x as close to x_hint as possible."""
    z = np.asarray(z_axis, float)
    z = z / np.linalg.norm(z)
    x = np.asarray(x_hint, float) - z * (np.asarray(x_hint, float) @ z)
    x /= np.linalg.norm(x)
    return np.column_stack([x, np.cross(z, x), z])


def place(mb_out, verts, faces, R, t):
    mb_out.add(np.asarray(verts) @ R.T + np.asarray(t), faces)


def unit_gem(cut, w, l, d):
    v, f, _ = gems.build_cut_cached(cut)
    return v * [w, l, d], f


def resample(path, step, closed):
    """Points every `step` mm of arc length along a polyline, plus their unit tangents."""
    P = np.vstack([path, path[:1]]) if closed else np.asarray(path, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    n = max(int(round(total / step)), 2)
    ds = np.linspace(0.0, total, n, endpoint=not closed)
    pts, tans = [], []
    for d in ds:
        k = min(int(np.searchsorted(cum, d, side="right") - 1), len(seg) - 1)
        f = (d - cum[k]) / max(seg[k], 1e-9)
        pts.append(P[k] * (1 - f) + P[k + 1] * f)
        t = P[k + 1] - P[k]
        tans.append(t / max(np.linalg.norm(t), 1e-9))
    return np.array(pts), np.array(tans), total


def arc_point(path, dist):
    """Point and tangent at a signed arc distance from path[0] along a closed path."""
    P = np.vstack([path, path[:1]])
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    dist %= cum[-1]
    k = min(int(np.searchsorted(cum, dist, side="right") - 1), len(seg) - 1)
    f = (dist - cum[k]) / max(seg[k], 1e-9)
    t = P[k + 1] - P[k]
    return P[k] * (1 - f) + P[k + 1] * f, t / np.linalg.norm(t)


# ----------------------------------------------------------------------------------------- display bust

# Classic jewellery display bust: short neck with a flat oval top, rounded shoulders, a flattened body tapering to a
# rounded point, on a short post and a hexagonal base. Heights in mm (Blender Z).
BUST_TOP, NECK_BASE, SHOULDER, BUST_BOTTOM = 72.0, 46.0, -6.0, -250.0
POST_BOTTOM, BASE_BOTTOM = -288.0, -302.0


def _smooth(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def bust_section(z):
    """Cross-section of the display bust at height z: superellipse radii (x, y), forward offset and exponent."""
    if z >= NECK_BASE:                                   # neck, with a slight lip and a rounded edge on the top cap
        lip = 1.4 * _smooth((z - (BUST_TOP - 6.0)) / 1.2)
        rx, ry = 44.0 + lip, 33.0 + lip
        edge = 2.6
        if z > BUST_TOP - edge:
            k = (z - (BUST_TOP - edge)) / edge
            cut = edge * (1.0 - math.sqrt(max(1.0 - k * k, 0.0)))
            rx, ry = rx - cut, ry - cut
        return rx, ry, 0.0, 2.0
    if z >= SHOULDER:                                    # shoulders: flat on top, rounding down to the sides
        t = (NECK_BASE - z) / (NECK_BASE - SHOULDER)
        g = math.sin(t * math.pi / 2) * (0.35 + 0.65 * _smooth(t / 0.3))   # sloping shoulders, soft fillet at the neck
        return 44.0 + 56.0 * g, 33.0 + 8.0 * g, -5.0 * _smooth(t), 2.0 + 0.5 * _smooth(t)
    u = min((SHOULDER - z) / (SHOULDER - BUST_BOTTOM), 1.0)   # body: tapers to a rounded point
    rx = max(100.0 * (1.0 - u ** 2.3) ** 0.5, 0.4)
    ry = max(41.0 * (1.0 - u ** 3.0) ** 0.5, 0.4)
    return rx, ry, -5.0, 2.5


def bust_point(theta, z):
    """Surface point. theta = 0 at the back of the neck (+Y), pi at the front (-Y)."""
    rx, ry, yc, e = bust_section(z)
    s, c, p = math.sin(theta), math.cos(theta), 2.0 / e
    return np.array([rx * math.copysign(abs(s) ** p, s), yc + ry * math.copysign(abs(c) ** p, c), z])


def bust_normal(theta, z):
    dt = bust_point(theta + 1e-3, z) - bust_point(theta - 1e-3, z)
    dz = bust_point(theta, z + 0.05) - bust_point(theta, z - 0.05)
    n = np.cross(dt, dz)
    p, yc = bust_point(theta, z), bust_section(z)[2]
    if n @ np.array([p[0], p[1] - yc, 0.0]) < 0:
        n = -n
    return n / np.linalg.norm(n)


def bust_mesh(nt=128):
    """The bust surface (flat top cap), plus the post and hexagonal base as separate parts."""
    zs = np.concatenate([np.linspace(BUST_BOTTOM + 0.6, SHOULDER, 64, endpoint=False),
                         np.linspace(SHOULDER, NECK_BASE, 40, endpoint=False),
                         np.linspace(NECK_BASE, BUST_TOP - 6.0, 8, endpoint=False),
                         np.linspace(BUST_TOP - 6.0, BUST_TOP, 22)])
    nz = len(zs)
    verts = [bust_point(2 * math.pi * i / nt, z) for z in zs for i in range(nt)]
    faces = [[j * nt + i, j * nt + (i + 1) % nt, (j + 1) * nt + (i + 1) % nt, (j + 1) * nt + i]
             for j in range(nz - 1) for i in range(nt)]
    bc = len(verts)
    verts.append([0.0, -5.0, BUST_BOTTOM])
    faces += [[bc, (i + 1) % nt, i] for i in range(nt)]
    tc, base = len(verts), (nz - 1) * nt
    verts.append([0.0, 0.0, BUST_TOP])
    faces += [[tc, base + i, base + (i + 1) % nt] for i in range(nt)]
    return np.array(verts), faces


def _prism(outline, z0, z1):
    n = len(outline)
    verts = [[x, y, z0] for x, y in outline] + [[x, y, z1] for x, y in outline]
    faces = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    faces += [list(range(n))[::-1], list(range(n, 2 * n))]
    return np.array(verts, float), faces


def stand_meshes():
    """Post (a slim rectangular upright) and hexagonal base under the bust."""
    post = _prism([(-7.5, -10.0), (7.5, -10.0), (7.5, 0.0), (-7.5, 0.0)], POST_BOTTOM, BUST_BOTTOM + 14.0)
    hexagon = [(64.0 * math.cos(math.radians(a)) * 1.12, 64.0 * math.sin(math.radians(a)) * 0.92 - 5.0)
               for a in range(0, 360, 60)]
    base = _prism(hexagon, BASE_BOTTOM, POST_BOTTOM)
    return post, base


def necklace_path(length_mm, z_back=NECK_BASE - 3.0, lift=0.5, samples=900, power=2.6):
    """Closed curve lying on the bust: around the back of the neck, dropping to a point on the chest.
    The drop is solved so the curve is `length_mm` long. Returns (points, drop_mm); points[samples//2] is the
    front centre."""
    def build(drop):
        pts = []
        for k in range(samples):
            th = 2 * math.pi * k / samples
            z = z_back - drop * ((1 - math.cos(th)) / 2) ** power
            pts.append(bust_point(th, z) + bust_normal(th, z) * lift)
        return np.array(pts)

    lo, hi = 2.0, 200.0
    for _ in range(40):
        mid = (lo + hi) / 2
        P = build(mid)
        if np.linalg.norm(np.roll(P, -1, axis=0) - P, axis=1).sum() < length_mm:
            lo = mid
        else:
            hi = mid
    return build((lo + hi) / 2), (lo + hi) / 2


def surface_normal_near(p):
    """Bust normal under a world point (mm)."""
    yc = bust_section(p[2])[2]
    th = math.atan2(p[0], p[1] - yc)
    return bust_normal(th % (2 * math.pi), p[2])


# ----------------------------------------------------------------------------------------- chain

def cable_link(length, width, wire, seg_u=10, seg_v=5):
    """One oval cable-chain link in its own frame: long axis X, link plane XY."""
    rc = width / 2 - wire
    hs = max(length / 2 - wire - rc, 0.0)
    cl, nl = [], []                     # centreline points and in-plane outward normals
    for k in range(seg_u):
        a = 2 * math.pi * k / seg_u
        c, s = math.cos(a), math.sin(a)
        cl.append([math.copysign(hs, c) + rc * c, rc * s])
        nl.append([c, s])
    verts, faces = [], []
    for k in range(seg_u):
        for j in range(seg_v):
            b = 2 * math.pi * j / seg_v
            verts.append([cl[k][0] + wire * math.cos(b) * nl[k][0], cl[k][1] + wire * math.cos(b) * nl[k][1],
                          wire * math.sin(b)])
    for k in range(seg_u):
        k2 = (k + 1) % seg_u
        for j in range(seg_v):
            j2 = (j + 1) % seg_v
            faces.append([k * seg_v + j, k2 * seg_v + j, k2 * seg_v + j2, k * seg_v + j2])
    return np.array(verts), faces


def cable_chain(path, closed=True, link=2.3, wire=0.28, surface=True):
    """Interlocking cable chain along a polyline. Links alternate flat (lying on the bust) and upright."""
    pitch = link - 2.25 * wire
    pts, tans, _ = resample(path, pitch, closed)
    lv, lf = cable_link(link, link * 0.72, wire)
    mb = gx.MeshBuilder()
    for i in range(len(pts) - (0 if closed else 1)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        c, t = (a + b) / 2, b - a
        n = surface_normal_near(c) if surface else np.array([0.0, 0.0, 1.0])
        R = frame(n, t) if i % 2 else frame(np.cross(t, n), t)   # columns: x along the chain
        place(mb, lv, lf, R, c)
    return mb


def spring_clasp(centre, tangent, normal, wire=0.4, radius=1.7):
    R = frame(np.cross(tangent, normal), tangent)
    ring = [[radius * math.cos(a), radius * math.sin(a), 0.0] for a in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
    mb = gx.MeshBuilder()
    v, f = gx.tube(np.array(ring), wire, 8, closed=True)
    place(mb, v, f, R, centre)
    v, f = gx.tube(np.array([[radius * 0.7, -0.4, 0], [radius * 1.6, -0.4, 0]]), wire * 0.7, 8)
    place(mb, v, f, R, centre)
    return mb


# ----------------------------------------------------------------------------------------- drop pendant

def _arc_sampler(path):
    """f(fraction) -> (point, unit outward normal) at an equal-arc-length fraction round a closed 2D offset path."""
    seg = np.linalg.norm(np.roll(path, -1, axis=0) - path, axis=1)
    cum, total = np.concatenate([[0.0], np.cumsum(seg)]), seg.sum()

    def at(frac):
        d = (frac % 1.0) * total
        k = min(int(np.searchsorted(cum, d, side="right") - 1), len(path) - 1)
        f = (d - cum[k]) / max(seg[k], 1e-9)
        a, b = path[k], path[(k + 1) % len(path)]
        t = (b - a) / max(np.linalg.norm(b - a), 1e-9)
        return a * (1 - f) + b * f, np.array([t[1], -t[0]])
    return at


def claw_halo(spec, base_z, accent_size=1.4, clearance=0.4, claw_r=0.27):
    """Halo whose accents are parted by pointed claws reaching outward, the starburst look of a classic cluster."""
    frame_mb, centres, z_acc, acc = halo(spec, base_z, accent_size=accent_size, clearance=clearance)
    pts, nrm = spec.loop(240)
    offset = clearance + accent_size / 2.0
    path = pts + nrm * offset
    at, n = _arc_sampler(path), len(centres)
    t0 = path[1] - path[0]
    sign = 1.0 if t0[0] * path[0][1] - t0[1] * path[0][0] <= 0 else -1.0     # make the sampler's normal point outward
    for i in range(n):
        c, nn = at((i + 0.5) / n)
        nn = nn * sign
        base = [*(c + nn * (accent_size * 0.18)), z_acc - 0.15]
        mid = [*(c + nn * (accent_size * 0.45)), z_acc + 0.16]
        tip = [*(c + nn * (accent_size * 0.68 + 0.08)), z_acc + 0.04]
        line = gx.catmull_rom([base, base, mid, tip, tip], 5)
        frame_mb.add(*gx.tube(line, np.linspace(claw_r * 1.15, 0.1, len(line)), 8))
    return frame_mb, centres, z_acc, acc


def flower_head(spec, piece, base_drop=0.6):
    """Five pave-set petals round a claw-set centre stone (mount-local, girdle at z = 0, top petal along +Y).
    Returns (petal metal MeshBuilder, {accent mesh name: MeshBuilder}, z of the petal backs, tip of the top petal)."""
    L, W = piece.get("petalLengthMm", 6.5), piece.get("petalWidthMm", 5.2)
    size = piece.get("paveStoneMm", 0.8)
    pitch = size + 0.08
    r_in = max(1.2, spec.width / 2 - 0.45)
    c, z0, tilt, slab = r_in + L / 2, -0.55, 0.07, 0.6
    hw = lambda cu: (W / 2) * math.sqrt(max(1 - cu * cu, 0.0)) * (0.78 + 0.16 * (1 + cu))
    zf = lambda u: z0 + tilt * (u - r_in)
    rng = np.random.default_rng(piece.get("paveSeed", 11))
    pv, pf = pave_stone(size)
    metal, white, pink = gx.MeshBuilder(), gx.MeshBuilder(), gx.MeshBuilder()
    for k in range(5):
        phi = math.radians(90 + 72 * k)
        a, b = np.array([math.cos(phi), math.sin(phi)]), np.array([-math.sin(phi), math.cos(phi)])
        ts = np.linspace(0, 2 * math.pi, 72, endpoint=False)
        uv = [(c + (L / 2) * math.cos(t), math.copysign(hw(math.cos(t)), math.sin(t))) for t in ts]
        top = np.array([[*(u * a + v * b), zf(u)] for u, v in uv])
        bot = top - [0, 0, slab]
        cen = np.array([*(c * a), zf(c)])
        n = len(top)
        verts = np.vstack([top, bot, [cen, cen - [0, 0, slab]]])
        faces = [[2 * n, i, (i + 1) % n] for i in range(n)] + [[2 * n + 1, n + (i + 1) % n, n + i] for i in range(n)]
        faces += [[i, n + i, n + (i + 1) % n, (i + 1) % n] for i in range(n)]
        metal.add(verts, faces)
        metal.add(*gx.tube(top + [0, 0, 0.12], 0.27, 8, closed=True))               # raised rim round the petal
        # pave on a hex grid, inset from the rim and clear of the centre claws
        normal = np.array([*(-tilt * a), 1.0])
        normal /= np.linalg.norm(normal)
        R = frame(normal, [*a, 0.0])
        for j in range(-12, 13):
            v = j * pitch * 0.866
            for i in range(-2, 40):
                u = r_in + 0.35 + i * pitch + (pitch / 2 if j % 2 else 0.0)
                cu = (u - c) / (L / 2)
                if abs(cu) > 1 - 0.55 / (L / 2) or abs(v) > hw(cu) - 0.5 or math.hypot(u, v) < spec.width / 2 + 0.75:
                    continue
                side = abs(v) / max(hw(cu), 1e-6)
                is_pink = rng.random() < 0.18 + 0.62 * (1 - side ** 1.4) * (1 - 0.35 * (u - r_in) / L)
                place(pink if is_pink else white, pv, pf, R, [*(u * a + v * b), zf(u) + 0.1])
    plate = [[(r_in + 0.7) * math.cos(t), (r_in + 0.7) * math.sin(t)] for t in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    metal.add(*_prism(plate, z0 - slab, z0))                                          # fills between the petal roots
    for mb in (white, pink):
        mb.count, mb.size = sum(len(v) for v in mb.verts) // 17, size
    tip = np.array([0.0, r_in + L + 0.25, zf(r_in + L) - 0.3])
    return metal, {"Accent_Pave": white, "AccentPink_Pave": pink}, z0 - slab, tip


def _anchor_and_head(style, spec, prong_r, top=1, piece=None):
    """Head MeshBuilders (mount-local) for a pendant or earring head, its accent meshes ({name: MeshBuilder}), its
    anchor point A on the top of the head, the depth of its back, and `rim(az)`: a point on the outer edge of the head
    at a polar angle. top = -1 hangs the stone the other way up (a pear with its point to the bail)."""
    pav = spec.pavilion
    base_z = -(pav + 0.9)
    heads, accents = {}, {}

    def edge(out, z):
        def rim(az):
            p, n = spec.at(az)
            return np.array([*(p + n * out), z])
        return rim
    if style == "solitaire":
        mb = prong_head(spec, [45, 135, 225, 315], base_z, prong_r=prong_r)
        mb.add(*gx.tube(np.array([[1.15 * math.cos(a), 1.15 * math.sin(a), base_z]
                                  for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]), 0.36, 8, closed=True))
        heads["Head_Center"] = mb
        A = np.array([0.0, 0.43 * spec.length + 0.9 * prong_r + 0.15, -0.42 * pav])
        rim = edge(0.9 * prong_r + 0.15, -0.42 * pav)
    elif style in ("halo", "claw_halo", "double_halo"):
        prongs = [45, 135, 225, 315] if spec.cut != "pear" else [270, 15, 165, 65, 115]
        heads["Head_Center"] = prong_head(spec, prongs, base_z, prong_r=0.36 if style == "halo" else 0.34,
                                          tip_lean=0.25)
        if style == "halo":
            frame_mb, centres, z_acc, acc = halo(spec, base_z)
            rows = [(frame_mb, centres, z_acc, acc)]
            offset = 0.35 + acc.width / 2
        elif style == "claw_halo":
            rows = [claw_halo(spec, base_z, accent_size=piece.get("haloStoneMm", 1.4))]
            offset = 0.4 + rows[0][3].width / 2
        else:
            a1, a2 = piece.get("haloStoneMm", [1.1, 1.25])
            inner = halo(spec, base_z, accent_size=a1, clearance=0.35)
            c2 = 0.35 + a1 + 0.32
            rows = [inner, halo(spec, base_z, accent_size=a2, clearance=c2)]
            offset = c2 + a2 / 2
        frame_all, accents_mb = gx.MeshBuilder(), gx.MeshBuilder()
        accents_mb.count, accents_mb.size = 0, rows[0][3].width
        for frame_mb, centres, z_acc, acc in rows:
            frame_all.add(*arrays(frame_mb))
            av, af = unit_gem("round", acc.width, acc.length, acc.depth)
            for c in centres:
                accents_mb.add(av + [c[0], c[1], z_acc], af)
            accents_mb.count += len(centres)
        heads["Halo_Frame"] = frame_all
        accents["Accent_Halo"] = accents_mb
        acc, z_acc = rows[-1][3], rows[-1][2]
        half = acc.width / 2 + 0.22
        bottom, top_z = z_acc - acc.pavilion - 0.15, z_acc - 0.06
        rim = edge(offset + half - 0.2, (bottom + top_z) / 2)
        A = np.array([0.0, spec.length / 2 + offset + half - 0.2, (bottom + top_z) / 2]) if style == "halo" \
            else rim(90 if top > 0 else 270)
    elif style == "bezel":
        heads["Bezel"] = bezel_cup(spec, base_z)
        A = np.array([0.0, spec.length / 2 + 0.7, -0.6])
        rim = edge(0.7, -0.6)
    elif style == "flower":
        petals, accents, back, A = flower_head(spec, piece)
        base_z = min(back, -pav) - 0.05
        heads["Head_Center"] = prong_head(spec, [0, 60, 120, 180, 240, 300], back + 0.1, prong_r=0.32, tip_lean=0.2)
        heads["Halo_Petals"] = petals
        rim = lambda az: np.array([*(np.array([math.cos(math.radians(az)), math.sin(math.radians(az))]) * (A[1] - 0.3)), A[2]])
    else:
        raise ValueError(style)
    return heads, accents, A, base_z, rim


def build_accents(accents, col, accent_mat, parent, gems=None):
    """Builds each accent mesh: Accent_* in diamond; a name matching a prefix in `gems` (the catalogue's accentGems,
    default AccentPink -> pink sapphire) in that gemstone."""
    gems = gems or {"AccentPink": "pink_sapphire"}
    for name, mb in accents.items():
        if not mb.verts:
            continue
        key = next((k for k in gems if name.startswith(k) and gems[k] != "center"), None)
        mb.build(name, col, gem_mat(gems[key], accent_mat) if key else accent_mat, smooth=False, parent=parent)
    return sum(getattr(mb, "count", 0) for mb in accents.values()), max([getattr(mb, "size", 0.0) for mb in accents.values()] or [0.0])


def hanging_drop(col, parent, B, drop, metal, stone_mat, name):
    """A jump ring, a short cable chain and a claw-set drop stone hanging from point B (parent-local) along local -Y,
    in its own empty at B so the app can keep it on the bottom of the head without scaling it."""
    spec = GemSpec(drop["shapeId"], drop["lengthMm"], drop["widthMm"])
    holder = gx.empty(name, col, B, parent=parent)
    mb = gx.MeshBuilder()
    rr, wire = 0.72, 0.26
    ring_c = np.array([0.0, -rr * 0.55, 0.0])
    mb.add(*gx.tube(np.array([ring_c + [0, rr * math.cos(a), rr * math.sin(a)]
                              for a in np.linspace(0, 2 * math.pi, 18, endpoint=False)]), wire, 8, closed=True))
    start, end = ring_c - [0, rr * 0.9, 0], ring_c - [0, rr * 0.9 + drop["chainMm"], 0]
    mb.add(*arrays(cable_chain(np.array([start, end]), closed=False, link=1.7, wire=0.22, surface=False)))
    low_c = end - [0, 0.45, 0]
    mb.add(*gx.tube(np.array([low_c + [rr * 0.8 * math.cos(a), rr * 0.8 * math.sin(a), 0]
                              for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]), wire, 8, closed=True))
    p_top, _ = spec.at(90)
    loop_c = low_c - [0, rr * 0.8 + 0.25, 0]
    mb.add(*gx.tube(np.array([loop_c + [0, 0.55 * math.cos(a), 0.55 * math.sin(a)]
                              for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]), 0.24, 8, closed=True))
    S = loop_c - [0, 0.55 + p_top[1] + 0.35, 0]
    hv, hf = arrays(prong_head(spec, [45, 135, 225, 315], -(spec.pavilion + 0.5), prong_r=0.34, tip_lean=0.22))
    mb.add(hv + S, hf)
    mb.add(*gx.tube(np.array([loop_c - [0, 0.5, 0.15], S + [0, p_top[1] + 0.1, -spec.pavilion * 0.4]]), 0.26, 8))
    mb.build(name.replace("Drop_", "Drop_Chain_"), col, metal, parent=holder)
    gv, gf = unit_gem(spec.cut, spec.width, spec.length, spec.depth)
    gx.MeshBuilder().add(gv + S, gf).build(name.replace("Drop_", "AccentMatch_Drop_"), col, stone_mat, smooth=False, parent=holder)
    return holder


def _chest_frame(P, spec_len, top=1):
    """Rotation for a pendant lying on the slope of the chest below P: columns = mount local axes in world.
    top = -1 turns it upside down about its own table normal."""
    zf = lambda z: bust_point(math.pi, z)[1]
    slope = (zf(P[2]) - zf(P[2] - 14.0)) / 14.0               # how far the chest leans forward per mm down
    theta = math.pi / 2 - math.atan(slope)
    up = np.array([0.0, math.cos(theta), math.sin(theta)])     # pendant "up" in world
    nz = np.array([0.0, -math.sin(theta), math.cos(theta)])    # local +Z (out of the table) in world
    R = np.column_stack([[float(top), 0.0, 0.0], up * top, nz])
    S0 = np.array([0.0, zf(P[2] - spec_len * 0.6), P[2] - spec_len * 0.6])
    return R, up, nz, S0


def _euler_deg(R):
    from mathutils import Matrix
    return tuple(math.degrees(a) for a in Matrix(np.asarray(R).tolist()).to_euler("XYZ"))


def drop_pendant(col, root, style, spec, P, metal, accent_mat, prong_r=0.45, bail_r=1.15, bail_wire=0.48,
                 top=1, piece=None):
    """Hangs a stone pendant from a bail around the chain at world point P (front centre of the necklace).
    The pendant lies on the slope of the chest below P. Returns (mount object, mount position mm)."""
    heads, accents, A, back, _rim = _anchor_and_head(style, spec, prong_r, top, piece or {})
    R, up, nz, S0 = _chest_frame(P, spec.length, top)
    m_up = P @ up - (bail_r + bail_wire + 1.1) - (R @ A) @ up
    m_n = S0 @ nz + 0.35 - back                                 # the pendant's back rests on the velvet
    M = m_up * up + m_n * nz
    mount = gx.empty("GemMount_Center", col, M, _euler_deg(R), parent=root)
    for name, mb in heads.items():
        mb.build(name, col, metal, parent=mount)
    count, size = build_accents(accents, col, accent_mat, mount)

    _build_bail(col, mount, M, R, A, P, up, nz, metal, bail_r, bail_wire)
    mount["accentStones"] = count
    mount["accentSizeMm"] = size
    return mount, M


def _build_bail(col, mount, M, R, A, P, up, nz, metal, bail_r=1.15, bail_wire=0.48, origin=None):
    """Bail: a teardrop loop from A on the head (mount-local), round the chain at P and back (built in world,
    stored local). `origin` is the Attach_Bail object's origin, which the app scales the head about: A by default."""
    origin = A if origin is None else np.asarray(origin, float)
    Aw = M + R @ A
    rr = bail_r + bail_wire
    ctrl = [Aw + up * 0.2 - nz * 0.35,
            Aw + up * 1.0 + nz * 0.45,
            P + nz * rr * 0.9 - up * rr * 0.55,
            P + nz * rr * 0.35 + up * rr * 0.95,
            P - nz * rr * 0.55 + up * rr * 0.75,
            P - nz * rr * 0.95 - up * rr * 0.35,
            Aw + up * 0.9 - nz * 1.1]
    loop = gx.catmull_rom(ctrl + [ctrl[0], ctrl[1], ctrl[2]], 8)[8: 8 + 7 * 8]
    bail = gx.MeshBuilder()
    bail.add(*gx.tube(loop, bail_wire, 10, closed=True))
    bail.add(*gx.sphere(Aw, bail_wire * 1.25, 12, 8))
    local = lambda v: (np.asarray(v) - M) @ R                  # world -> mount-local
    bail.verts = [local(v) - origin for v in bail.verts]
    bail.build("Attach_Bail", col, metal, parent=mount, location_mm=origin)


# ----------------------------------------------------------------------------------------- pendants & necklaces

def front_index(path):
    return len(path) // 2


def build_pendant(piece, shapes, metal, accent_mat, col):
    """Pendant on a fine 18-inch cable chain, on the bust."""
    root = gx.empty(piece["modelFile"], col, size_mm=6)
    path, _drop = necklace_path(piece.get("chainLengthMm", 450))
    cable_chain(path, link=piece.get("chainLinkMm", 2.3), wire=piece.get("chainWireMm", 0.28)).build("Chain", col, metal, parent=root)
    p0, t0 = path[0], path[1] - path[0]
    spring_clasp(p0 + np.array([0, 1.2, 0]), t0, surface_normal_near(p0)).build("Clasp", col, metal, parent=root)
    spec = center_spec(piece, shapes)
    P = path[front_index(path)]
    mount, M = drop_pendant(col, root, piece["pendantStyle"], spec, P, metal, accent_mat,
                            top=-1 if piece.get("pointUp") else 1, piece=piece)
    meta = _meta(piece, spec, M, [math.degrees(a) for a in mount.rotation_euler])
    if mount["accentStones"]:
        meta["accentStones"], meta["accentSizeMm"] = mount["accentStones"], round(mount["accentSizeMm"], 2)
    return root, meta, [("Center", spec)]


def _collet(spec, prong_r=0.27):
    """Light four-claw collet for a small round accent (local frame, girdle at z=0). Same shape as
    gx_rings.prong_head with far fewer polygons, because a line bracelet or riviera repeats it dozens of times."""
    pav, base_z, mb = spec.pavilion, -(spec.pavilion + 0.3), gx.MeshBuilder()
    for az in (45, 135, 225, 315):
        p, n = spec.at(az)
        u = p / np.linalg.norm(p)
        ctrl = [[*(u * 0.35), base_z], [*(p * 0.62), -pav * 0.8], [*(p + n * prong_r * 0.75), 0.0],
                [*(p - u * 0.12 + n * prong_r * 0.2), spec.crown * 0.55 + prong_r * 0.35]]
        path = gx.catmull_rom(ctrl, 4)
        mb.add(*gx.tube(path, np.linspace(prong_r * 1.1, prong_r * 0.92, len(path)), 6))
        mb.add(*gx.sphere(path[-1], prong_r, 6, 4))
    pts, nrm = spec.loop(28)
    ring = pts * 0.86 + nrm * prong_r * 0.9
    mb.add(*gx.tube(np.column_stack([ring, np.full(len(ring), -pav * 0.42)]), prong_r * 0.7, 6, closed=True))
    return arrays(mb)


def build_riviera(piece, shapes, metal, accent_mat, col):
    """Graduated line of claw-set accents across the collarbone, a centre drop and a cable chain behind."""
    root = gx.empty(piece["modelFile"], col, size_mm=6)
    path, _ = necklace_path(piece.get("chainLengthMm", 430))
    n_side, big, small, gap = piece.get("accentsPerSide", 11), 3.4, 2.1, 0.55
    fi = front_index(path)
    seg = np.linalg.norm(np.roll(path, -1, axis=0) - path, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    d_front = cum[fi]

    collets, stones, links = gx.MeshBuilder(), gx.MeshBuilder(), gx.MeshBuilder()
    side_ends = {}
    for side in (-1, 1):
        d = 2.8                                           # first stone clears the bail
        prev = None
        for k in range(n_side):
            size = big + (small - big) * k / max(n_side - 1, 1)
            d += size / 2
            p, t = arc_point(path, d_front + side * d)
            n = surface_normal_near(p)
            spec = GemSpec("round", size, size)
            c = p + n * (spec.pavilion + 0.3 - 0.4)
            R = frame(n, t)
            cv, cf = _collet(spec)
            place(collets, cv, cf, R, c)
            gv, gf = unit_gem("round", size, size, spec.depth)
            place(stones, gv, gf, R, c)
            left = c - R[:, 0] * side * (size / 2 + 0.15) - n * spec.pavilion * 0.55
            right = c + R[:, 0] * side * (size / 2 + 0.15) - n * spec.pavilion * 0.55
            if prev is not None:
                links.add(*gx.tube(np.array([prev, left]), 0.33, 8))
            else:
                side_ends[(side, "inner")] = left
            prev = right
            d += size / 2 + gap
        side_ends[(side, "outer")] = prev
        side_ends[(side, "d")] = d

    # Centre bar through the bail, joining the two innermost collets.
    P = path[fi]
    links.add(*gx.tube(gx.catmull_rom([side_ends[(-1, "inner")], P, side_ends[(1, "inner")]], 8), 0.36, 8))
    collets.build("Collet", col, metal, parent=root)
    stones.build("Accent_Line", col, accent_mat, smooth=False, parent=root)

    # Chain from the outermost collets round the back of the neck.
    d_start, d_end = d_front + side_ends[(1, "d")], d_front - side_ends[(-1, "d")] + cum[-1]
    back = np.array([arc_point(path, d)[0] for d in np.linspace(d_start, d_end, 400)])
    back = np.vstack([side_ends[(1, "outer")], back, side_ends[(-1, "outer")]])
    cable_chain(back, closed=False, link=2.3, wire=0.3).build("Chain", col, metal, parent=root)
    links.build("Links", col, metal, parent=root)
    p0 = path[0]
    spring_clasp(p0 + np.array([0, 1.2, 0]), path[1] - p0, surface_normal_near(p0)).build("Clasp", col, metal, parent=root)

    shape = shapes[piece["defaultShapeId"]]
    spec = GemSpec(shape["id"], shape["defaultLengthMm"], shape["defaultWidthMm"])
    mount, M = drop_pendant(col, root, "solitaire", spec, P, metal, accent_mat, prong_r=0.42, bail_r=1.0, bail_wire=0.45)
    meta = _meta(piece, spec, M, (math.degrees(mount.rotation_euler.x), 0, 0))
    meta["accentStones"] = 2 * n_side
    return root, meta, [("Center", spec)]


def build_station(piece, shapes, metal, accent_mat, col):
    """Cable chain with bezel-set stations either side and a bezel centre drop."""
    root = gx.empty(piece["modelFile"], col, size_mm=6)
    path, _ = necklace_path(piece.get("chainLengthMm", 450))
    cable_chain(path).build("Chain", col, metal, parent=root)
    p0 = path[0]
    spring_clasp(p0 + np.array([0, 1.2, 0]), path[1] - p0, surface_normal_near(p0)).build("Clasp", col, metal, parent=root)
    fi = front_index(path)
    seg = np.linalg.norm(np.roll(path, -1, axis=0) - path, axis=1)
    d_front = np.concatenate([[0.0], np.cumsum(seg)])[fi]

    stations, stones = gx.MeshBuilder(), gx.MeshBuilder()
    size = piece.get("stationStoneMm", 3.5)
    spec = GemSpec("round", size, size)
    for d in piece.get("stationOffsetsMm", [28, 58, 90]):
        for side in (-1, 1):
            p, t = arc_point(path, d_front + side * d)
            n = surface_normal_near(p)
            R = frame(n, t)
            c = p + n * (1.95 + 0.5)          # bezel bottom sits on the chain
            bv, bf = arrays(bezel_cup(spec, -1.9))
            place(stations, bv, bf, R, c)
            for s2 in (-1, 1):                # little rings gripping the chain either side
                q = p + t * s2 * (size / 2 + 0.9)
                ring = [q + 0.75 * (math.cos(a) * n + math.sin(a) * np.cross(t, n)) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
                stations.add(*gx.tube(np.array(ring), 0.3, 8, closed=True))
                stations.add(*gx.tube(np.array([q + n * 0.75, c - n * 1.2 + t * s2 * (size / 2 - 0.2)]), 0.3, 8))
            gv, gf = unit_gem("round", size, size, spec.depth)
            place(stones, gv, gf, R, c)
    stations.build("Station", col, metal, parent=root)
    stones.build("Accent_Stations", col, accent_mat, smooth=False, parent=root)

    shape = shapes[piece["defaultShapeId"]]
    cspec = GemSpec(shape["id"], shape["defaultLengthMm"], shape["defaultWidthMm"])
    mount, M = drop_pendant(col, root, "bezel", cspec, path[fi], metal, accent_mat)
    meta = _meta(piece, cspec, M, (math.degrees(mount.rotation_euler.x), 0, 0))
    meta["accentStones"] = 2 * len(piece.get("stationOffsetsMm", [28, 58, 90]))
    meta["accentSizeMm"] = size
    return root, meta, [("Center", cspec)]


def build_lariat(piece, shapes, metal, accent_mat, col):
    """Y necklace: the chain meets at a halo-set centre stone, and a second chain hangs a claw-set drop below it."""
    root = gx.empty(piece["modelFile"], col, size_mm=6)
    path, _ = necklace_path(piece.get("chainLengthMm", 450))
    fi = front_index(path)
    seg = np.linalg.norm(np.roll(path, -1, axis=0) - path, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    d_front, P = cum[fi], path[fi]
    spec = center_spec(piece, shapes)
    heads, accents, A, back, rim = _anchor_and_head("halo", spec, 0.42, 1, piece)
    R, up, nz, S0 = _chest_frame(P, spec.length)
    m_up = P @ up - 0.9 - A[1]                                  # the top of the halo sits just under the chain line
    m_n = S0 @ nz + 0.35 - back
    M = m_up * up + m_n * nz
    mount = gx.empty("GemMount_Center", col, M, _euler_deg(R), parent=root)
    for name, mb in heads.items():
        mb.build(name, col, metal, parent=mount)
    count, size = build_accents(accents, col, accent_mat, mount)

    # Jump rings on the halo's shoulders take the two chain ends (fixed: the app scales the head about A).
    rings, ends = gx.MeshBuilder(), []
    for az in (90 - piece.get("shoulderDeg", 52), 90 + piece.get("shoulderDeg", 52)):
        p, n = spec.at(az)
        q = rim(az)
        c = q + np.array([*(n * 0.55), 0.0])
        t = np.array([-n[1], n[0], 0.0])
        rings.add(*gx.tube(np.array([c + 0.72 * (math.cos(a) * np.array([*n, 0.0]) + math.sin(a) * np.array([0, 0, 1.0]))
                                     for a in np.linspace(0, 2 * math.pi, 18, endpoint=False)]), 0.27, 8, closed=True))
        ends.append(M + R @ (c + np.array([*(n * 0.6), 0.0])))
    rings.verts = [v - A for v in rings.verts]
    rings.build("Attach_Bail", col, metal, parent=mount, location_mm=A)

    # Chain: round the back of the neck, then down to each ring.
    cut = max(abs((e - P) @ np.array([1.0, 0, 0])) for e in ends) + 6.0
    back_pts = np.array([arc_point(path, d)[0] for d in np.linspace(d_front + cut, d_front - cut + cum[-1], 500)])
    e_plus = min(ends, key=lambda e: np.linalg.norm(e - back_pts[0]))
    e_minus = max(ends, key=lambda e: np.linalg.norm(e - back_pts[0]))
    cable_chain(np.vstack([e_plus, back_pts, e_minus]), closed=False).build("Chain", col, metal, parent=root)
    p0 = path[0]
    spring_clasp(p0 + np.array([0, 1.2, 0]), path[1] - p0, surface_normal_near(p0)).build("Clasp", col, metal, parent=root)

    hanging_drop(col, mount, rim(270) + [0, -0.3, 0.15], piece["drop"], metal,
                 gem_mat(piece["defaultGemstoneId"], accent_mat), "Drop_Center")
    meta = _meta(piece, spec, M, [math.degrees(a) for a in mount.rotation_euler])
    meta["accentStones"], meta["accentSizeMm"] = count, round(size, 2)
    return root, meta, [("Center", spec)]


# ----------------------------------------------------------------------------------------- starburst pendant

def _radial(phi):
    return np.array([math.cos(phi), math.sin(phi), 0.0]), np.array([-math.sin(phi), math.cos(phi), 0.0])


def starburst_parts(spec, piece):
    """A firework of coloured sprays round a centre stone (mount-local, girdle at z = 0, +Y up).
    Returns (scaled head meshes, scaled accent meshes, fixed burst metal, fixed burst accent meshes, back z, top z)."""
    # Centre: six claws and a ring of small pink accents, scaled with the stone by the app.
    heads = {"Head_Center": prong_head(spec, [0, 60, 120, 180, 240, 300], -(spec.pavilion + 0.6), prong_r=0.36, tip_lean=0.22)}
    halo_metal, halo_pink = gx.MeshBuilder(), gx.MeshBuilder()
    hs = piece.get("haloStoneMm", 1.2)
    hspec = GemSpec("round", hs, hs)
    r_h = spec.width / 2 + 0.3 + hs / 2
    hv, hf = unit_gem("round", hs, hs, hspec.depth)
    cv, cf = _collet(hspec, prong_r=0.22)
    n_h = int(2 * math.pi * r_h // (hs + 0.45))
    for k in range(n_h):
        a, t = _radial(2 * math.pi * k / n_h)
        R = frame([0, 0, 1], t)
        c = a * r_h + [0, 0, -0.35]
        place(halo_pink, hv, hf, R, c)
        place(halo_metal, cv, cf, R, c)
    halo_metal.add(*gx.tube(np.array([[r_h * math.cos(u), r_h * math.sin(u), -0.35 - hspec.pavilion * 0.6]
                                      for u in np.linspace(0, 2 * math.pi, 48, endpoint=False)]), 0.32, 8, closed=True))
    heads["Halo_Frame"] = halo_metal
    halo_pink.count, halo_pink.size = n_h, hs

    # Burst: fixed, so a bigger centre stone does not blow the whole pendant up.
    metal, pave = gx.MeshBuilder(), gx.MeshBuilder()
    sprays = {}
    L, W = piece.get("sprayStoneMm", [3.2, 2.2])
    ospec = GemSpec("oval", L, W)
    ov, of = unit_gem("oval", W, L, ospec.depth)
    ocv, ocf = _collet(ospec, prong_r=0.25)
    zs = lambda r: -0.35 - 0.045 * (r - 5.0)                    # a gentle dome, lower towards the tips
    r0 = piece.get("sprayInnerMm", 6.2)
    for sector in piece["sprays"]:                               # [{"name": "AccentGarnet_Spray", "deg": 60, "stones": [3, 2]}]
        mb = sprays.setdefault(sector["name"], gx.MeshBuilder())
        for arm, (n, da, start) in enumerate(zip(sector.get("stones", [3, 2]), (-13, 13), (r0, r0 + 1.5))):
            phi = math.radians(sector["deg"] + da)
            a, t = _radial(phi)
            for k in range(n):
                r = start + k * (L + 0.15)
                R = frame([0, 0, 1], t)
                c = a * r + [0, 0, zs(r)]
                place(mb, ov, of, R, c)
                place(metal, ocv, ocf, R, c)
            r_end = start + (n - 1) * (L + 0.15)
            metal.add(*gx.tube(np.array([a * 4.2 + [0, 0, zs(4.2) - ospec.pavilion * 0.75],
                                         a * r_end + [0, 0, zs(r_end) - ospec.pavilion * 0.75]]), 0.38, 8))
        # a slim gold ray between the two arms
        a, t = _radial(math.radians(sector["deg"]))
        ray = [a * r + t * 0.35 * math.sin(math.pi * (r - 8) / 6) + [0, 0, zs(r) - 0.1] for r in np.linspace(8.0, 14.0, 14)]
        metal.add(*gx.tube(np.array(ray), np.linspace(0.32, 0.12, 14), 8))
    for k, b in enumerate(piece.get("rays", [])):                # {"deg": 90, "kind": "gold"|"pave", "to": 16}
        a, t = _radial(math.radians(b["deg"]))
        r1 = b.get("to", 15.5)
        if b["kind"] == "gold":
            ray = [a * r + t * 0.6 * math.sin(math.pi * (r - 4.5) / (r1 - 4.5)) * (1 if k % 2 else -1) + [0, 0, zs(r) - 0.05]
                   for r in np.linspace(4.5, r1, 24)]
            metal.add(*gx.tube(np.array(ray), np.linspace(0.5, 0.14, 24), 10))
        else:                                                    # a tapering strip set with a line of small accents
            ps = 0.9
            pspec = GemSpec("round", ps, ps)
            pv, pf = unit_gem("round", ps, ps, pspec.depth)
            strip, rr = [], np.linspace(5.5, r1, 12)
            for r in rr:
                w = 0.75 - 0.25 * (r - 5.5) / (r1 - 5.5)
                strip.append((a * r + t * w)[:2])
            for r in rr[::-1]:
                w = 0.75 - 0.25 * (r - 5.5) / (r1 - 5.5)
                strip.append((a * r - t * w)[:2])
            sv, sf = _prism(strip, -0.9, -0.25)
            sv[:, 2] += [zs(np.hypot(x, y)) + 0.35 for x, y in sv[:, :2]]
            metal.add(sv, sf)
            R = frame([0, 0, 1], t)
            for r in np.arange(7.0, r1 - 0.4, ps + 0.18):
                place(pave, pv, pf, R, a * r + [0, 0, zs(r) + 0.05])
                for sgn in (-1, 1):                              # bead prongs either side
                    metal.add(*gx.sphere(a * (r + ps / 2 + 0.09) + t * sgn * 0.42 + [0, 0, zs(r) + 0.12], 0.14, 6, 4))
            pave.count = getattr(pave, "count", 0) + len(np.arange(7.0, r1 - 0.4, ps + 0.18))
    plate = [[5.2 * math.cos(u), 5.2 * math.sin(u)] for u in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    pv_, pf_ = _prism(plate, -2.0, -1.4)
    metal.add(pv_, pf_)
    pave.size = 0.9
    for name, mb in sprays.items():
        mb.count, mb.size = len(mb.verts), L
    burst_acc = dict(sprays, Accent_PaveRays=pave)
    top = max(b.get("to", 15.5) for b in piece.get("rays", []) if abs(b["deg"] - 90) < 1)
    return heads, {"AccentPink_Halo": halo_pink}, metal, burst_acc, min(-2.0, -spec.pavilion) - 0.05, top


def build_starburst(piece, shapes, metal, accent_mat, col):
    """Firework pendant on a heavier chain: the bail sits behind the top ray, and the app scales the centre head about
    the centre (the bail and the burst stay fixed)."""
    root = gx.empty(piece["modelFile"], col, size_mm=6)
    path, _ = necklace_path(piece.get("chainLengthMm", 450))
    cable_chain(path, link=piece.get("chainLinkMm", 2.3), wire=piece.get("chainWireMm", 0.28)).build("Chain", col, metal, parent=root)
    p0 = path[0]
    spring_clasp(p0 + np.array([0, 1.2, 0]), path[1] - p0, surface_normal_near(p0)).build("Clasp", col, metal, parent=root)
    spec = center_spec(piece, shapes)
    heads, accents, burst_metal, burst_acc, back, top = starburst_parts(spec, piece)
    P = path[front_index(path)]
    A = np.array([0.0, top - 3.0, -1.2])                        # bail fixing, behind the top ray
    bail_r, bail_wire = 1.3, 0.55
    R, up, nz, S0 = _chest_frame(P, 30.0)
    m_up = P @ up - (bail_r + bail_wire + 1.1) - A[1]
    m_n = S0 @ nz + 0.35 - back
    M = m_up * up + m_n * nz
    mount = gx.empty("GemMount_Center", col, M, _euler_deg(R), parent=root)
    for name, mb in heads.items():
        mb.build(name, col, metal, parent=mount)
    gems = piece.get("accentGems")
    count, _ = build_accents(accents, col, accent_mat, mount, gems)
    burst = gx.empty("Attach_Burst", col, (0, 0, 0), parent=mount)   # Attach_*: not scaled by the app
    burst_metal.build("Halo_Rays", col, metal, parent=burst)
    n_burst, _ = build_accents(burst_acc, col, accent_mat, burst, gems)
    _build_bail(col, mount, M, R, A, P, up, nz, metal, bail_r, bail_wire, origin=(0.0, 0.0, 0.0))
    meta = _meta(piece, spec, M, [math.degrees(a) for a in mount.rotation_euler])
    meta["accentStones"], meta["accentSizeMm"] = count + n_burst, 0.9
    return root, meta, [("Center", spec)]


# ----------------------------------------------------------------------------------------- bracelets

def oval_band(a, b, width, thickness, segments=220, profile=24, exponent=3.2, top_boost=0.3):
    """Rigid oval bangle around the Y axis (inner semi-axes a along X, b along Z). Thicker under the head."""
    e = 2.0 / exponent
    verts, faces = [], []
    for i in range(segments):
        phi = 2 * math.pi * i / segments
        top = ((1 + math.cos(phi)) / 2) ** 3
        w, th = width * (0.9 + top_boost * top), thickness * (0.9 + 0.25 * top)
        px, pz = a * math.sin(phi), b * math.cos(phi)
        n = np.array([math.sin(phi) / a, math.cos(phi) / b])
        n /= np.linalg.norm(n)
        for j in range(profile):
            s = 2 * math.pi * j / profile
            c, sn = math.cos(s), math.sin(s)
            u = (w / 2) * math.copysign(abs(c) ** e, c)
            v = th / 2 + (th / 2) * math.copysign(abs(sn) ** e, sn)
            verts.append([px + n[0] * v, u, pz + n[1] * v])
    for i in range(segments):
        i2 = (i + 1) % segments
        for j in range(profile):
            j2 = (j + 1) % profile
            faces.append([i * profile + j, i2 * profile + j, i2 * profile + j2, i * profile + j2])
    return np.array(verts), faces, b + thickness * 1.15


def build_bangle(piece, shapes, metal, accent_mat, col):
    root = gx.empty(piece["modelFile"], col, size_mm=6)
    a, b = piece["innerWidthMm"] / 2, piece["innerHeightMm"] / 2
    th = piece.get("thicknessMm", 2.2)
    v, f, band_top = oval_band(a, b, piece.get("widthMm", 3.6), th)
    gx.MeshBuilder().add(v, f).build("Band", col, metal, parent=root)
    shape = shapes[piece["defaultShapeId"]]
    center = GemSpec(shape["id"], shape["defaultLengthMm"], shape["defaultWidthMm"])
    mount_z = band_top + 1.0 + center.pavilion
    mount = gx.empty("GemMount_Center", col, (0, 0, mount_z), parent=root)
    prong_head(center, [45, 135, 225, 315], band_top - mount_z - 0.35).build("Head_Center", col, metal, parent=mount)
    meta = _meta(piece, center, [0.0, 0.0, mount_z], (0, 0, 0))
    previews = [("Center", center)]
    a_out, b_out = a + th * 0.95, band_top
    for m in piece["mounts"]:
        if m["role"] != "side":
            continue
        side = GemSpec(m["fixedShapeId"], m["fixedLengthMm"], m["fixedLengthMm"])
        sign = 1.0 if m["id"] == "SideL" else -1.0
        x = sign * (center.width / 2 + side.width / 2 + 1.0)
        zb = b_out * math.sqrt(max(1 - (x / a_out) ** 2, 0.0))
        slope = -(b_out / a_out) * (x / a_out) / math.sqrt(max(1 - (x / a_out) ** 2, 1e-6))
        tilt = math.degrees(math.atan(-slope)) + 6.0 * sign
        z = zb + 0.6 + side.pavilion
        sm = gx.empty(f"GemMount_{m['id']}", col, (x, 0, z), (0, tilt, 0), parent=root)
        base = -(side.pavilion + 0.6 + 0.4) / math.cos(math.radians(abs(tilt)))
        prong_head(side, [45, 135, 225, 315], base, prong_r=0.3, tip_lean=0.16).build(f"Head_{m['id']}", col, metal, parent=sm)
        meta["mounts"][m["id"]] = {"blenderPositionMm": [x, 0.0, z], "blenderRotationDeg": [0.0, tilt, 0.0],
                                   "headDefaultLengthMm": side.length, "headDefaultWidthMm": side.width,
                                   "defaultShape": side.cut}
        previews.append((m["id"], side))
    return root, meta, previews


def build_tennis(piece, shapes, metal, accent_mat, col):
    """Line bracelet: claw-set boxes hinged round an oval, a raised centre stone on top, a box clasp underneath."""
    root = gx.empty(piece["modelFile"], col, size_mm=6)
    a, b = piece["innerWidthMm"] / 2, piece["innerHeightMm"] / 2
    size = piece.get("accentStoneMm", 3.0)
    acc = GemSpec("round", size, size)
    lift = acc.pavilion + 0.55                         # girdle height above the inner surface
    ga, gb = a + lift, b + lift
    # equal arc-length positions on the girdle ellipse
    ell = np.array([[ga * math.sin(p), 0.0, gb * math.cos(p)] for p in np.linspace(0, 2 * math.pi, 2000, endpoint=False)])
    pitch = size + 0.85
    pts, tans, total = resample(ell, pitch, True)
    n_box = len(pts)

    boxes, stones, links = gx.MeshBuilder(), gx.MeshBuilder(), gx.MeshBuilder()
    gv, gf = unit_gem("round", size, size, acc.depth)
    cv, cf = _collet(acc, prong_r=0.3)
    half = size / 2 + 0.25
    sq = [[half, -half], [half, half], [-half, half], [-half, -half]]
    box_ring = []
    for k in range(4):                                 # rounded square frame under the stone
        p0, p1 = np.array(sq[k]), np.array(sq[(k + 1) % 4])
        for f in np.linspace(0, 1, 6, endpoint=False):
            q = p0 * (1 - f) + p1 * f
            box_ring.append([q[0], q[1], -acc.pavilion * 0.55])
    bv, bf = gx.tube(np.array(box_ring), 0.32, 6, closed=True)
    clasp_k = n_box // 2
    skip = {n_box - 1, 0, 1}                           # the centre head replaces three boxes
    for k in range(n_box):
        c, t = pts[k], tans[k]
        n = np.array([c[0] / ga ** 2, 0.0, c[2] / gb ** 2])
        n /= np.linalg.norm(n)
        R = frame(n, t)
        if k in skip:
            continue
        if k == clasp_k:
            box = np.array([[sx * half * 1.05, sy * half, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-acc.pavilion - 0.2, 0.5)])
            hull = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
            place(boxes, box, hull, R, c)
        else:
            place(boxes, cv, cf, R, c)
            place(boxes, bv, bf, R, c)
            place(stones, gv, gf, R, c)
        # hinge to the next box
        nxt = (k + 1) % n_box
        if k not in skip or nxt not in skip:
            c2 = pts[nxt]
            for yy in (-size * 0.28, size * 0.28):
                p = c - n * acc.pavilion * 0.55 + np.array([0, yy, 0])
                q = c2 - n * acc.pavilion * 0.55 + np.array([0, yy, 0])
                links.add(*gx.tube(np.array([p, q]), 0.3, 8))
    boxes.build("Box", col, metal, parent=root)
    stones.build("Accent_Line", col, accent_mat, smooth=False, parent=root)
    links.build("Links", col, metal, parent=root)

    # Raised centre head on a plate spanning the three skipped boxes.
    shape = shapes[piece["defaultShapeId"]]
    center = GemSpec(shape["id"], shape["defaultLengthMm"], shape["defaultWidthMm"])
    plate_top = gb - acc.pavilion * 0.55 + 0.35
    pw = pitch * 1.4
    plate = [[x, y, plate_top - 0.4] for x, y in
             [(pw, -half), (pw, half), (-pw, half), (-pw, -half)]]
    ring = []
    for k in range(4):
        p0, p1 = np.array(plate[k]), np.array(plate[(k + 1) % 4])
        for f in np.linspace(0, 1, 8, endpoint=False):
            ring.append(p0 * (1 - f) + p1 * f)
    gx.MeshBuilder().add(*gx.tube(np.array(ring), 0.42, 8, closed=True)).build("Box_Center", col, metal, parent=root)
    mount_z = plate_top + 0.9 + center.pavilion
    mount = gx.empty("GemMount_Center", col, (0, 0, mount_z), parent=root)
    prong_head(center, [45, 135, 225, 315], plate_top - mount_z - 0.3, prong_r=0.4).build("Head_Center", col, metal, parent=mount)
    meta = _meta(piece, center, [0.0, 0.0, mount_z], (0, 0, 0))
    meta["accentStones"] = n_box - len(skip) - 1
    meta["accentSizeMm"] = size
    return root, meta, [("Center", center)]


# ----------------------------------------------------------------------------------------- earrings
# A matched pair: both earrings face -Y, with the plane y = 0 just behind the heads (where an ear lobe or earring card
# would be; the app shows the pair on its own, without a stand). GemMount_Center is the right
# earring as you look at it, GemMount_Pair its mirror twin; the app scales both heads with the one stone you choose.

EAR_X = 14.0           # each earring's centre, either side of the stand's centre line
EAR_PANEL_T = 5.0      # ear lobe thickness: how far posts and hooks reach back
EAR_ROT = (90.0, 0.0, 0.0)   # mount local +Z (out of the table) -> world -Y, local +Y (stone length) -> world +Z


def _ear_world(M):
    """Mount-local -> world for an earring mount at M with EAR_ROT."""
    return lambda v: np.asarray(M) + np.array([v[0], -v[2], v[1]])


def _ear_local(M):
    return lambda w: np.array([w[0] - M[0], w[2] - M[2], -(w[1] - M[1])])


def butterfly_back(z0):
    """Butterfly (scroll) back on the post, mount-local, behind the stand."""
    mb = gx.MeshBuilder()
    mb.add(*gx.tube(np.array([[0, 0, z0], [0, 0, z0 - 0.5]]), 2.7, 20))
    for sx in (-1.0, 1.0):
        loop = [[sx * 1.15 + 1.05 * math.cos(a), 1.05 * math.sin(a), z0 + 0.65] for a in np.linspace(0, 2 * math.pi, 18, endpoint=False)]
        mb.add(*gx.tube(np.array(loop), 0.32, 8, closed=True))
    mb.add(*gx.tube(np.array([[0, 0, z0 + 0.1], [0, 0, z0 - 1.2]]), 0.9, 12))
    return mb


def screw_back(z0):
    """Screw back: a broad dished disc on a threaded barrel (mount-local, behind the lobe)."""
    mb = gx.MeshBuilder()
    disc = [[3.3 * math.cos(a), 3.3 * math.sin(a)] for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    mb.add(*_prism(disc, z0 - 0.45, z0))
    mb.add(*gx.tube(np.column_stack([np.array(disc) * 0.985, np.full(len(disc), z0 + 0.02)]), 0.22, 8, closed=True))
    mb.add(*gx.tube(np.array([[0, 0, z0 + 0.1], [0, 0, z0 - 2.4]]), 0.85, 14))
    for k in range(5):                                      # thread rings on the barrel
        mb.add(*gx.tube(np.array([[0.86 * math.cos(a), 0.86 * math.sin(a), z0 - 0.75 - 0.32 * k]
                                  for a in np.linspace(0, 2 * math.pi, 14, endpoint=False)]), 0.09, 6, closed=True))
    return mb


def _ear_meta(piece, spec, positions, count, size, rot=EAR_ROT):
    meta = _meta(piece, spec, positions["Center"], rot)
    meta["pair"] = True
    meta["mounts"]["Pair"] = dict(meta["mounts"]["Center"], blenderPositionMm=[float(c) for c in positions["Pair"]])
    if count:
        meta["accentStones"], meta["accentSizeMm"] = count * 2, round(size, 2)
    return meta


def build_stud(piece, shapes, metal, accent_mat, col):
    """A pair of studs (solitaire, halo, claw halo or flower) on posts with butterfly or screw backs, optionally
    with a chain and a claw-set drop hanging from the bottom of each head."""
    root = gx.empty(piece["modelFile"], col, size_mm=6)
    spec = center_spec(piece, shapes)
    top = -1 if piece.get("pointUp") else 1
    rot = EAR_ROT if top > 0 else (-90.0, 0.0, 180.0)      # pointUp: also half a turn about the table normal
    style, positions, count, size = piece["earringStyle"], {}, 0, 0.0
    drop_mat = gem_mat(piece["defaultGemstoneId"], accent_mat)
    for mount_id, sx in (("Center", 1.0), ("Pair", -1.0)):
        heads, accents, _A, base_z, rim = _anchor_and_head(style, spec, 0.42, top, piece)
        M = (sx * EAR_X, base_z - 0.35, 0.0)            # the back of the head sits just in front of the lobe
        mount = gx.empty(f"GemMount_{mount_id}", col, M, rot, parent=root)
        for name, mb in heads.items():
            mb.build(name, col, metal, parent=mount)
        count, size = build_accents(accents, col, accent_mat, mount)
        gx.MeshBuilder().add(*gx.tube(np.array([[0, 0, base_z + 0.3], [0, 0, base_z - EAR_PANEL_T - 2.6]]), 0.42, 10)) \
            .build("Attach_Post", col, metal, parent=mount)
        back_z = base_z - 0.35 - EAR_PANEL_T - 0.45
        (screw_back(back_z) if piece.get("earringBack") == "screw" else butterfly_back(back_z)) \
            .build("Attach_Back", col, metal, parent=mount)
        if piece.get("drop"):                           # drops hang along local -Y, so not with pointUp
            hanging_drop(col, mount, rim(270) + [0, -0.3, 0.15], piece["drop"], metal, drop_mat, f"Drop_{mount_id}")
        positions[mount_id] = M
    return root, _ear_meta(piece, spec, positions, count, size, rot), [("Center", spec), ("Pair", spec)]


def build_drop(piece, shapes, metal, accent_mat, col):
    """A pair of bezel drops, each on a jump ring and a French hook."""
    root = gx.empty(piece["modelFile"], col, size_mm=6)
    shape = shapes[piece["defaultShapeId"]]
    spec = GemSpec(shape["id"], shape["defaultLengthMm"], shape["defaultWidthMm"])
    style, positions, count, size = piece["earringStyle"], {}, 0, 0.0
    for mount_id, sx in (("Center", 1.0), ("Pair", -1.0)):
        heads, accents, A, base_z, _rim = _anchor_and_head(style, spec, 0.42, 1, piece)
        M = (sx * EAR_X, base_z - 0.6, 0.0)
        mount = gx.empty(f"GemMount_{mount_id}", col, M, EAR_ROT, parent=root)
        for name, mb in heads.items():
            mb.build(name, col, metal, parent=mount)
        count, size = build_accents(accents, col, accent_mat, mount)
        world, local = _ear_world(M), _ear_local(M)
        Aw = world(A)
        # Jump ring through the top of the head, then the hook: up, over and back, then down behind the lobe.
        ring_c = Aw + np.array([0.0, 0.0, 1.05])
        ring = [ring_c + np.array([0.0, 1.0 * math.cos(a), 1.0 * math.sin(a)]) for a in np.linspace(0, 2 * math.pi, 20, endpoint=False)]
        T = ring_c + np.array([0.0, 0.0, 1.0])
        y0 = -T[1]                                       # distance from the hook's foot back to the stand face
        hook_pts = [T, T + [0, -0.5, 3.0], T + [0, -0.4, 7.5], T + [0, 0.6, 11.0], T + [0, y0 * 0.75, 13.2],
                    T + [0, y0 + EAR_PANEL_T * 0.5, 14.0], T + [0, y0 + EAR_PANEL_T + 1.2, 12.6],
                    T + [0, y0 + EAR_PANEL_T + 1.6, 7.0], T + [0, y0 + EAR_PANEL_T + 1.3, 2.5]]
        hook = gx.catmull_rom([hook_pts[0]] + hook_pts + [hook_pts[-1]], 8)
        mb = gx.MeshBuilder()
        mb.add(*gx.tube(np.array(ring), 0.34, 8, closed=True))
        mb.add(*gx.tube(hook, 0.36, 10))
        mb.add(*gx.sphere(T + [0, -0.5, 3.0], 0.75, 12, 8))   # small bead on the front of the hook
        mb.add(*gx.sphere(Aw, 0.5, 10, 6))
        mb.verts = [np.array([local(v) for v in block]) - A for block in mb.verts]
        mb.build("Attach_Bail", col, metal, parent=mount, location_mm=A)
        positions[mount_id] = M
    meta = _ear_meta(piece, spec, positions, count, size)
    return root, meta, [("Center", spec), ("Pair", spec)]


# ----------------------------------------------------------------------------------------- dispatch

def _meta(piece, spec, M, rot):
    return {"id": piece["id"], "object": piece["modelFile"], "category": piece["category"], "accentStones": 0,
            "mounts": {"Center": {"blenderPositionMm": [float(c) for c in M], "blenderRotationDeg": list(rot),
                                  "headDefaultLengthMm": spec.length, "headDefaultWidthMm": spec.width,
                                  "defaultShape": spec.cut}}}


BUILDERS = {"pendant": build_pendant, "riviera": build_riviera, "station": build_station,
            "bangle": build_bangle, "tennis": build_tennis, "stud": build_stud, "drop": build_drop,
            "lariat": build_lariat, "starburst": build_starburst}


def build_piece(piece, shapes, metal, accent_mat, col):
    return BUILDERS[piece["builder"]](piece, shapes, metal, accent_mat, col)
