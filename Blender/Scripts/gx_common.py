"""
GemXpert Blender toolkit: scene setup, mesh construction helpers, PBR materials, export and preview rendering.

Units: geometry helpers take MILLIMETRES; meshes are written to Blender in METRES (1 BU = 1 m), so the FBX
imports into Unity at real-world size (a ring is ~20 mm). Blender axes: Z up, ring/finger axis along Y.
With the FBX settings below, Blender -Y -> Unity +Z, Blender +Z -> Unity +Y, Blender +X -> Unity -X.
"""
import json
import math
import os

import bpy
import numpy as np

MM = 0.001
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CATALOGUE = os.path.join(ROOT, "Assets", "GemXpert", "Configurations", "Resources", "Catalogue")


def load_catalogue(name):
    with open(os.path.join(CATALOGUE, f"{name}.json"), "r", encoding="utf-8") as fh:
        return {item["id"]: item for item in json.load(fh)["items"]}


# ----------------------------------------------------------------------------------------- scene

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "MILLIMETERS"
    return scene


def collection(name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col


def empty(name, col, location_mm=(0, 0, 0), rotation_deg=(0, 0, 0), parent=None, size_mm=1.5):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_type = "ARROWS"
    ob.empty_display_size = size_mm * MM
    ob.location = [c * MM for c in location_mm]
    ob.rotation_euler = [math.radians(a) for a in rotation_deg]
    col.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    return ob


# ----------------------------------------------------------------------------------------- mesh building

class MeshBuilder:
    """Accumulates vertex/face arrays (in mm) and writes one Blender mesh object (in metres)."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self._count = 0

    def add(self, verts, faces):
        verts = np.asarray(verts, dtype=float).reshape(-1, 3)
        self.verts.append(verts)
        self.faces.extend([[i + self._count for i in f] for f in faces])
        self._count += len(verts)
        return self

    def build(self, name, col, material=None, smooth=True, parent=None, location_mm=(0, 0, 0), auto_smooth_deg=None):
        verts = np.concatenate(self.verts) * MM
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts.tolist(), [], self.faces)
        me.validate(clean_customdata=False)
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])  # outward winding per closed part
        bm.to_mesh(me)
        bm.free()
        me.update()
        for p in me.polygons:
            p.use_smooth = smooth
        ob = bpy.data.objects.new(name, me)
        ob.location = [c * MM for c in location_mm]
        col.objects.link(ob)
        if parent is not None:
            ob.parent = parent
        if material is not None:
            me.materials.append(material)
        if smooth and auto_smooth_deg is not None:
            add_smooth_by_angle(ob, auto_smooth_deg)
        return ob


def add_smooth_by_angle(ob, angle_deg):
    """Sharp edges above angle_deg (keeps facet-like creases crisp on otherwise smooth metal)."""
    me = ob.data
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    limit = math.radians(angle_deg)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > limit:
            e.smooth = False
    bm.to_mesh(me)
    bm.free()


def catmull_rom(points, samples_per_segment=8):
    """Smooth curve through control points (centripetal-free uniform Catmull-Rom)."""
    p = np.asarray(points, float)
    ext = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(samples_per_segment):
            t = s / samples_per_segment
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(p[-1])
    return np.array(out)


def _frames(path, closed):
    """Rotation-minimising frames (double reflection) along a polyline."""
    n = len(path)
    tang = np.zeros_like(path)
    for i in range(n):
        a = path[(i - 1) % n] if (closed or i > 0) else path[i]
        b = path[(i + 1) % n] if (closed or i < n - 1) else path[i]
        d = b - a
        tang[i] = d / max(np.linalg.norm(d), 1e-12)
    ref = np.array([0.0, 0.0, 1.0]) if abs(tang[0][2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    nrm = np.zeros_like(path)
    nrm[0] = np.cross(np.cross(tang[0], ref), tang[0])
    nrm[0] /= np.linalg.norm(nrm[0])
    for i in range(n - 1):
        v1 = path[i + 1] - path[i]
        c1 = v1 @ v1
        if c1 < 1e-18:
            nrm[i + 1] = nrm[i]
            continue
        rl = nrm[i] - (2 / c1) * (v1 @ nrm[i]) * v1
        tl = tang[i] - (2 / c1) * (v1 @ tang[i]) * v1
        v2 = tang[i + 1] - tl
        c2 = v2 @ v2
        nrm[i + 1] = rl - (2 / c2) * (v2 @ rl) * v2 if c2 > 1e-18 else rl
        nrm[i + 1] /= np.linalg.norm(nrm[i + 1])
    binorm = np.cross(tang, nrm)
    return tang, nrm, binorm


def tube(path, radii, segments=12, closed=False, caps=True):
    """Circular tube along a polyline (mm). radii: scalar or per-point array."""
    path = np.asarray(path, float)
    n = len(path)
    radii = np.full(n, radii, dtype=float) if np.isscalar(radii) else np.asarray(radii, float)
    _, nrm, bin_ = _frames(path, closed)
    verts, faces = [], []
    for i in range(n):
        for s in range(segments):
            a = 2 * math.pi * s / segments
            verts.append(path[i] + radii[i] * (math.cos(a) * nrm[i] + math.sin(a) * bin_[i]))
    rings = n if closed else n - 1
    for i in range(rings):
        j = (i + 1) % n
        for s in range(segments):
            s2 = (s + 1) % segments
            faces.append([i * segments + s, i * segments + s2, j * segments + s2, j * segments + s])
    if caps and not closed:
        for idx, ring_start, flip in ((0, 0, True), (n - 1, (n - 1) * segments, False)):
            verts.append(path[idx])
            c = len(verts) - 1
            for s in range(segments):
                a, b = ring_start + s, ring_start + (s + 1) % segments
                faces.append([c, b, a] if flip else [c, a, b])
    return np.array(verts), faces


def sphere(centre, radius, u=12, v=8):
    centre = np.asarray(centre, float)
    verts = [centre + [0, 0, radius]]
    for i in range(1, v):
        th = math.pi * i / v
        for j in range(u):
            ph = 2 * math.pi * j / u
            verts.append(centre + radius * np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)]))
    verts.append(centre + [0, 0, -radius])
    faces = []
    for j in range(u):
        faces.append([0, 1 + j, 1 + (j + 1) % u])
    for i in range(v - 2):
        for j in range(u):
            a = 1 + i * u + j
            b = 1 + i * u + (j + 1) % u
            faces.append([a, a + u, b + u, b])
    last = len(verts) - 1
    base = 1 + (v - 2) * u
    for j in range(u):
        faces.append([last, base + (j + 1) % u, base + j])
    return np.array(verts), faces


def sweep_closed(path_pts, path_normals, profile, z_offset=0.0):
    """Sweeps a closed 2D profile [(outward_offset, z), ...] around a closed planar loop (XY) -> torus-like solid.
    path_normals are outward unit normals in XY. Profile is listed counter-clockwise in (offset, z)."""
    m, k = len(path_pts), len(profile)
    verts, faces = [], []
    for i in range(m):
        p, n = np.asarray(path_pts[i], float), np.asarray(path_normals[i], float)
        for off, z in profile:
            verts.append([p[0] + n[0] * off, p[1] + n[1] * off, z + z_offset])
    for i in range(m):
        i2 = (i + 1) % m
        for j in range(k):
            j2 = (j + 1) % k
            faces.append([i * k + j, i2 * k + j, i2 * k + j2, i * k + j2])
    return np.array(verts), faces


# ----------------------------------------------------------------------------------------- materials

def srgb_to_linear(hex_color):
    hex_color = hex_color.lstrip("#")
    out = []
    for i in range(0, 6, 2):
        c = int(hex_color[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out + [1.0]


def _set_input(bsdf, names, value):
    for n in names if isinstance(names, (list, tuple)) else [names]:
        if n in bsdf.inputs:
            bsdf.inputs[n].default_value = value
            return True
    return False


def principled(name, color, metallic=0.0, roughness=0.5, transmission=0.0, ior=1.5, coat=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    _set_input(bsdf, "Base Color", color)
    _set_input(bsdf, "Metallic", metallic)
    _set_input(bsdf, "Roughness", roughness)
    _set_input(bsdf, "IOR", ior)
    _set_input(bsdf, ["Transmission Weight", "Transmission"], transmission)
    _set_input(bsdf, ["Coat Weight", "Clearcoat"], coat)
    mat.diffuse_color = color  # viewport / solid-mode colour
    mat.metallic = metallic
    mat.roughness = roughness
    mat.use_fake_user = True
    return mat


def metal_material(metal):
    """metal: entry from metals.json. Roughness from Unity smoothness (1 - smoothness, softened)."""
    return principled(f"Metal_{_pascal(metal['id'])}", srgb_to_linear(metal["colorHex"]), metallic=1.0,
                      roughness=max(0.05, (1.0 - metal["smoothness"]) * 0.9))


def gem_material(gem):
    """gem: entry from gemstones.json. Physically based transmission with the stone's refractive index."""
    color = srgb_to_linear(gem["colorHex"])
    return principled(f"Gem_{_pascal(gem['id'])}", color, metallic=0.0, roughness=0.0,
                      transmission=1.0, ior=gem["refractiveIndex"])


def _pascal(s):
    return "".join(p.capitalize() for p in s.split("_"))


# ----------------------------------------------------------------------------------------- export

def select_only(objects):
    for ob in bpy.context.scene.objects:
        ob.select_set(False)
    for ob in objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0] if objects else None


def descendants(ob):
    out = [ob]
    for c in ob.children:
        out.extend(descendants(c))
    return out


def export_fbx(path, objects):
    """Unity-oriented FBX: metres, Y-up, -Z forward, transforms baked so Unity sees identity rotation/scale 1."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    select_only(objects)
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        object_types={"EMPTY", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        bake_space_transform=True,
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        use_tspace=False,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="STRIP",
    )


def export_glb(path, objects, vertex_colors=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    select_only(objects)
    kwargs = dict(filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True)
    if vertex_colors:
        try:
            bpy.ops.export_scene.gltf(**kwargs, export_vertex_color="ACTIVE")
            return
        except TypeError:
            pass  # older exporter: colours used by the material are exported by default
    bpy.ops.export_scene.gltf(**kwargs)


def save_blend(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)


# ----------------------------------------------------------------------------------------- preview render

def setup_cycles(samples=64, width=1000, height=760):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 16
    scene.cycles.transmission_bounces = 16
    scene.cycles.glossy_bounces = 8
    scene.cycles.caustics_reflective = True
    scene.cycles.caustics_refractive = True
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX" if "AgX" in [e.identifier for e in
                                                          scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    scene.view_settings.look = "None"
    # Try the Apple GPU (Metal); fall back to CPU silently.
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"


def studio(col, target_mm=(0, 0, 8), floor_z_mm=-11.0, overhead=True, distance_scale=1.0, energy_scale=1.0):
    """distance_scale/energy_scale adapt the same light rig to larger subjects (e.g. a hand): lights move
    further out and dim, keeping their size so polished metal still shows the same softbox highlights."""
    """Dark jewellery studio: black glossy floor, soft key/fill/rim area lights, dim warm world."""
    world = bpy.data.worlds.new("GX_Studio")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.0035, 0.0032, 0.0034, 1)
    bg.inputs["Strength"].default_value = 1.0
    bpy.context.scene.world = world

    # Black lacquer floor: low albedo and reduced specular so the softboxes don't wash it out to grey.
    floor_mat = principled("Studio_Floor", (0.0025, 0.0022, 0.0026, 1), roughness=0.3)
    _set_input(floor_mat.node_tree.nodes["Principled BSDF"], ["Specular IOR Level", "Specular"], 0.2)
    v, f = np.array([[-200, -200, 0], [200, -200, 0], [200, 200, 0], [-200, 200, 0]], float), [[0, 1, 2, 3]]
    floor = MeshBuilder().add(v, f).build("Studio_Floor", col, floor_mat, smooth=False, location_mm=(0, 0, floor_z_mm))
    # Shadow catcher + transparent film: the render keeps the contact shadow but no grey floor/horizon,
    # so previews sit cleanly on the dark GemXpert interface or any page background.
    floor.is_shadow_catcher = True

    # Large softboxes: polished metal shows what it reflects, so big sources give long, clean highlights.
    t = np.array(target_mm, float)
    for name, pos, energy, size, color in (
            ("Key", (70, -80, 95), 14.0, 110, (1.0, 0.94, 0.86)),
            ("Fill", (-95, -50, 45), 4.0, 120, (0.92, 0.95, 1.0)),
            ("Rim", (-25, 100, 75), 9.0, 70, (1.0, 0.98, 0.95)),
            ("Top", (0, 10, 130), 6.0, 90, (1.0, 0.97, 0.92))):
        if name == "Top" and not overhead:
            continue  # a light on the lens axis mirrors straight off gem tables in top-down shots
        light = bpy.data.lights.new(name, "AREA")
        light.energy = energy * energy_scale * distance_scale ** 2
        light.size = size * MM * distance_scale ** 0.5
        light.color = color
        ob = bpy.data.objects.new(name, light)
        ob.location = [(t[i] + (pos[i] - t[i]) * distance_scale) * MM for i in range(3)]
        col.objects.link(ob)
        _look_at(ob, t)


def camera(col, location_mm, target_mm, lens=90):
    cam = bpy.data.cameras.new("PreviewCamera")
    cam.lens = lens
    cam.clip_start = 1 * MM
    cam.clip_end = 2.0
    ob = bpy.data.objects.new("PreviewCamera", cam)
    ob.location = [c * MM for c in location_mm]
    col.objects.link(ob)
    _look_at(ob, np.array(target_mm, float))
    bpy.context.scene.camera = ob
    return ob


def _look_at(ob, target_mm):
    from mathutils import Vector
    direction = Vector([c * MM for c in target_mm]) - ob.location
    ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
