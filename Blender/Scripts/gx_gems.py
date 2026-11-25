"""
GemXpert faceted gemstone generator.

Gems are built the way real cutting software (e.g. GemCad) describes them: as the intersection of
facet half-spaces. Every facet plane is defined by a girdle position, a direction and a cutting angle,
so every facet is exactly planar and the solid is watertight and convex.

Coordinate frame (Blender, millimetre-free / normalised):
    girdle centre = origin, table faces +Z, width along X, length along Y.
    The pear tip points to -Y (which becomes Unity +Z, towards the fingertip).

`build_cut(cut_id)` returns (verts, faces, info) where verts are NORMALISED so that the bounding box is
exactly 1 x 1 x 1 (width x length x total depth) with the girdle centre at the origin. Scaling the mesh by
(width_mm, length_mm, depth_mm) therefore gives exact physical dimensions without rebuilding geometry.
"""
import math
from itertools import combinations

import numpy as np

TOL = 1e-7


# ----------------------------------------------------------------------------------------- outlines

class Outline:
    """Closed convex girdle outline, normalised to width 1 (X) and length `aspect` (Y), centred on its bbox."""

    def __init__(self, fn, aspect=1.0, samples=1440):
        ts = np.linspace(0.0, 2.0 * math.pi, samples, endpoint=False)
        pts = np.array([fn(t) for t in ts], dtype=float)
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        self._fn = fn
        self._centre = (lo + hi) / 2.0
        self._scale = np.array([1.0 / (hi[0] - lo[0]), aspect / (hi[1] - lo[1])])
        self.aspect = aspect

    def point(self, t):
        return (np.asarray(self._fn(t), dtype=float) - self._centre) * self._scale

    def normal(self, t, h=1e-4):
        p = self.point(t)
        d = self.point(t + h) - self.point(t - h)
        n = np.array([d[1], -d[0]])
        if np.linalg.norm(n) < 1e-12:
            n = p.copy()
        n /= np.linalg.norm(n)
        return n if np.dot(n, p) >= 0 else -n


def circle_fn(t):
    return (math.cos(t), math.sin(t))


def superellipse_fn(exponent):
    e = 2.0 / exponent

    def fn(t):
        c, s = math.cos(t), math.sin(t)
        return (math.copysign(abs(c) ** e, c), math.copysign(abs(s) ** e, s))

    return fn


def teardrop_fn(fullness=1.0):
    """Pear outline: rounded end at +Y, point at -Y."""

    def fn(t):
        return (math.sin(t) * abs(math.sin(t / 2.0)) ** fullness, -math.cos(t))

    return fn


def polygon_fn(poly):
    """Polar ray-cast outline for a convex polygon (list of 2D vertices around the origin)."""
    poly = [np.asarray(p, float) for p in poly]

    def fn(t):
        d = np.array([math.cos(t), math.sin(t)])
        best = None
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            e = b - a
            m = np.array([[d[0], -e[0]], [d[1], -e[1]]])
            if abs(np.linalg.det(m)) < 1e-12:
                continue
            r, u = np.linalg.solve(m, a)
            if r > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or r < best):
                best = r
        return tuple(d * best)

    return fn


def chamfered_rect(width, length, chamfer):
    """CCW octagon: a width x length rectangle with 45-degree corner chamfers."""
    w, l, c = width / 2.0, length / 2.0, chamfer
    return [(w, -l + c), (w, l - c), (w - c, l), (-w + c, l), (-w, l - c), (-w, -l + c), (-w + c, -l), (w - c, -l)]


# ----------------------------------------------------------------------------------------- planes

def _facet(normal2, point2, angle_deg, z, crown):
    a = math.radians(angle_deg)
    n = np.array([normal2[0] * math.sin(a), normal2[1] * math.sin(a), math.cos(a) if crown else -math.cos(a)])
    p = np.array([point2[0], point2[1], z])
    return n, float(n @ p)


def brilliant_planes(outline, n_main=8, table=0.57, crown_angle=34.5, pav_angle=40.8, girdle=0.03,
                     star_angle=22.0, upper_girdle_angle=42.0, lower_girdle_angle=42.0, girdle_planes=64):
    """Modified brilliant (57/58 facets on a round) laid out on any convex outline."""
    g2 = girdle / 2.0
    z_top = g2 + (0.5 - table / 2.0) * math.tan(math.radians(crown_angle))
    planes = [(np.array([0.0, 0.0, 1.0]), z_top)]
    step = 2.0 * math.pi / n_main
    star_inset = table * math.cos(step / 2.0)
    for k in range(n_main):
        t = k * step
        planes.append(_facet(outline.normal(t), outline.point(t), crown_angle, g2, True))     # bezel (kite)
        planes.append(_facet(outline.normal(t), outline.point(t), pav_angle, -g2, False))     # pavilion main
        ts = t + step / 2.0
        planes.append(_facet(outline.normal(ts), outline.point(ts) * star_inset, star_angle, z_top, True))  # star
        for h in (0.25, 0.75):
            tu = t + step * h
            planes.append(_facet(outline.normal(tu), outline.point(tu), upper_girdle_angle, g2, True))
            planes.append(_facet(outline.normal(tu), outline.point(tu), lower_girdle_angle, -g2, False))
    for k in range(girdle_planes):
        t = (k + 0.5) * 2.0 * math.pi / girdle_planes
        n2, p2 = outline.normal(t), outline.point(t)
        planes.append((np.array([n2[0], n2[1], 0.0]), float(n2 @ p2)))
    return planes


def step_planes(poly, crown_rows, pavilion_rows, girdle=0.025, pavilion_override=None):
    """Step cut (emerald cut / princess crown): rows of facets parallel to every side of a polygon.
    rows = [(horizontal_inset, angle_deg), ...] from the girdle inwards."""
    poly = [np.asarray(p, float) for p in poly]
    g2 = girdle / 2.0
    planes = []
    z_top = None
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        e = b - a
        n = np.array([e[1], -e[0]]) / np.linalg.norm(e)  # outward for a CCW polygon
        planes.append((np.array([n[0], n[1], 0.0]), float(n @ a)))  # girdle
        z, inset = g2, 0.0
        for d_inset, angle in crown_rows:
            planes.append(_facet(n, a - n * inset, angle, z, True))
            z += d_inset * math.tan(math.radians(angle))
            inset += d_inset
        z_top = z
        if pavilion_override is None:
            z, inset = -g2, 0.0
            for d_inset, angle in pavilion_rows:
                planes.append(_facet(n, a - n * inset, angle, z, False))
                z -= d_inset * math.tan(math.radians(angle))
                inset += d_inset
    planes.append((np.array([0.0, 0.0, 1.0]), z_top))
    if pavilion_override is not None:
        planes.extend(pavilion_override)
    return planes


PRINCESS_TIERS = (
    # (horizontal inset to the next tier, facet angle, chevron turn in degrees)
    # Convex rule: tiers nearer the girdle are steeper, tiers nearer the culet shallower.
    (0.07, 62.0, 12.0),
    (0.12, 50.0, 18.0),
    (0.0, 41.0, 24.0),
)


def princess_pavilion(half=0.5, girdle=0.025, tiers=PRINCESS_TIERS):
    """Chevron pavilion for a square princess cut: on every side, each tier is a pair of facets whose
    normals are turned +/- a few degrees, which produces the characteristic V-shaped chevrons; each tier
    also gets a corner facet so the corners stay crisp."""
    g2 = girdle / 2.0
    planes = []
    for k in range(4):
        az = k * math.pi / 2.0
        n = np.array([math.cos(az), math.sin(az)])
        along = np.array([-n[1], n[0]])
        mid = n * half
        z, inset = -g2, 0.0
        for d_inset, angle, turn in tiers:
            for sgn in (-1.0, 1.0):
                t = math.radians(turn) * sgn
                nn = n * math.cos(t) + along * math.sin(t)
                planes.append(_facet(nn, mid - n * inset + along * sgn * half * 0.5, angle, z, False))
            cn = (n + along) / math.sqrt(2.0)
            corner = (n + along) * half
            planes.append(_facet(cn, corner - cn * (inset * math.sqrt(2.0) + 0.03), angle - 2.0, z, False))
            z -= d_inset * math.tan(math.radians(angle))
            inset += d_inset
    return planes


# ----------------------------------------------------------------------------------------- solid

def polyhedron_from_planes(planes):
    """Intersects half-spaces n.x <= d. Returns (verts (V,3), faces [list of index lists])."""
    normals = np.array([p[0] for p in planes], dtype=float)
    dists = np.array([p[1] for p in planes], dtype=float)
    idx = np.array(list(combinations(range(len(planes)), 3)))
    a = normals[idx]
    b = dists[idx]
    det = np.linalg.det(a)
    ok = np.abs(det) > 1e-10
    x = np.linalg.solve(a[ok], b[ok][..., None])[..., 0]
    inside = np.all(x @ normals.T <= dists + 1e-7, axis=1)
    candidates = x[inside]

    verts = []
    for p in candidates:
        if not any(np.linalg.norm(p - q) < 1e-6 for q in verts):
            verts.append(p)
    verts = np.array(verts)

    faces = []
    for n, d in zip(normals, dists):
        on = np.where(np.abs(verts @ n - d) < 1e-6)[0]
        if len(on) < 3:
            continue
        u = np.cross(n, [1.0, 0.0, 0.0] if abs(n[0]) < 0.9 else [0.0, 1.0, 0.0])
        u /= np.linalg.norm(u)
        v = np.cross(n, u)
        c = verts[on].mean(axis=0)
        ang = [math.atan2((verts[i] - c) @ v, (verts[i] - c) @ u) for i in on]
        ordered = [int(i) for _, i in sorted(zip(ang, on))]
        # u x v = n, so increasing angle is counter-clockwise seen from outside -> outward winding.
        faces.append(ordered)
    return verts, faces


# ----------------------------------------------------------------------------------------- cuts

EMERALD_POLY = chamfered_rect(1.0, 1.4, 0.15)
PRINCESS_POLY = chamfered_rect(1.0, 1.0, 0.03)


def cut_outline(cut_id):
    """Girdle outline of a cut at its default proportions, normalised to width 1 (used for settings)."""
    return {
        "round": lambda: Outline(circle_fn, 1.0),
        "oval": lambda: Outline(circle_fn, 8.0 / 6.0),
        "cushion": lambda: Outline(superellipse_fn(3.4), 1.0),
        "pear": lambda: Outline(teardrop_fn(1.0), 9.0 / 6.0),
        "emerald": lambda: Outline(polygon_fn(EMERALD_POLY), 1.4),
        "princess": lambda: Outline(polygon_fn(PRINCESS_POLY), 1.0),
    }[cut_id]()


def _cut_planes(cut_id):
    if cut_id == "round":
        return brilliant_planes(cut_outline("round"))
    if cut_id == "oval":
        return brilliant_planes(cut_outline("oval"), table=0.56, crown_angle=33.5, pav_angle=41.0)
    if cut_id == "cushion":
        return brilliant_planes(cut_outline("cushion"), table=0.58, crown_angle=35.0, pav_angle=42.5, girdle_planes=72)
    if cut_id == "pear":
        return brilliant_planes(cut_outline("pear"), table=0.55, crown_angle=34.0, pav_angle=41.0, girdle_planes=72)
    if cut_id == "emerald":
        poly = EMERALD_POLY
        return step_planes(poly,
                           crown_rows=[(0.07, 50.0), (0.065, 40.0), (0.055, 30.0)],
                           pavilion_rows=[(0.12, 52.0), (0.12, 42.0), (0.2, 34.0)])
    if cut_id == "princess":
        return step_planes(PRINCESS_POLY, crown_rows=[(0.08, 40.0), (0.08, 28.0)], pavilion_rows=[],
                           pavilion_override=princess_pavilion())
    raise ValueError(f"unknown cut '{cut_id}'")


CUTS = ["round", "oval", "cushion", "pear", "emerald", "princess"]
_CACHE = {}


def outline_at_angle(outline, angle_rad, samples=1440):
    """Point/normal on a normalised outline whose polar angle is closest to angle_rad."""
    ts = np.linspace(0.0, 2.0 * math.pi, samples, endpoint=False)
    pts = np.array([outline.point(t) for t in ts])
    ang = np.arctan2(pts[:, 1], pts[:, 0])
    diff = np.abs((ang - angle_rad + math.pi) % (2 * math.pi) - math.pi)
    t = ts[int(np.argmin(diff))]
    return outline.point(t), outline.normal(t)


def build_cut_cached(cut_id):
    if cut_id not in _CACHE:
        _CACHE[cut_id] = build_cut(cut_id)
    return _CACHE[cut_id]


def build_cut(cut_id):
    """Returns (verts normalised to a 1x1x1 bbox with girdle centre at origin, faces, info dict)."""
    verts, faces = polyhedron_from_planes(_cut_planes(cut_id))
    lo, hi = verts.min(axis=0), verts.max(axis=0)
    size = hi - lo
    # Keep z = 0 at the girdle centre; centre X/Y on the bbox.
    centre = np.array([(lo[0] + hi[0]) / 2.0, (lo[1] + hi[1]) / 2.0, 0.0])
    norm = (verts - centre) / size
    info = {
        "cut": cut_id,
        "facets": len(faces),
        "vertices": int(len(verts)),
        "length_to_width": float(size[1] / size[0]),
        "depth_ratio": float(size[2] / size[0]),          # total depth / width
        "crown_fraction": float(hi[2] / size[2]),          # of total depth, above the girdle centre
        "pavilion_fraction": float(-lo[2] / size[2]),
    }
    return norm, faces, info


if __name__ == "__main__":
    for c in CUTS:
        _, f, i = build_cut(c)
        print(i)
