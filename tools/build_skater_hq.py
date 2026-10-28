#!/usr/bin/env python3
"""High-quality anime skater (Genshin/GG Strive-inspired). Blender 4.2 headless."""
import bpy, bmesh, math, os
from mathutils import Vector, Euler, Matrix

OUT = "/workspace/skyline-riot/assets/character"
FACE_TEX = f"{OUT}/face_albedo.png"
GLB = f"{OUT}/skater.glb"
BLEND = f"{OUT}/skater.blend"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def wipe():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures,
                 bpy.data.actions, bpy.data.images, bpy.data.curves, bpy.data.textures):
        for b in list(coll):
            try: coll.remove(b)
            except Exception: pass
wipe()

# ---------- helpers ----------
def mat(name, col, rough=0.45, metal=0.0, emit=0.0, tex=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*col, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.35
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*col, 1)
        bsdf.inputs["Emission Strength"].default_value = emit
    if tex and os.path.exists(tex):
        img = bpy.data.images.load(tex)
        texnode = nodes.new("ShaderNodeTexImage")
        texnode.image = img
        links.new(texnode.outputs["Color"], bsdf.inputs["Base Color"])
    m.diffuse_color = (*col, 1)
    return m

def assign(o, m):
    if o.data.materials:
        o.data.materials[0] = m
    else:
        o.data.materials.append(m)

def smooth_obj(o, levels=2):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth()
    if levels:
        s = o.modifiers.new("Subsurf", 'SUBSURF')
        s.levels = levels
        s.render_levels = max(levels, 2)
        s.quality = 3

def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    for mod in list(o.modifiers):
        try: bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception as e: print("mod", mod.name, e)
    o.select_set(False)

def xf(o):
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.select_set(False)

def select_only(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o

# Materials
M = {
    "skin": mat("skin", (0.96, 0.82, 0.72), 0.55),
    "skin_face": mat("skin_face", (0.96, 0.82, 0.72), 0.5, tex=FACE_TEX),
    "hair": mat("hair", (0.04, 0.06, 0.12), 0.35),
    "hair2": mat("hair2", (0.07, 0.10, 0.18), 0.35),
    "jacket": mat("jacket", (0.025, 0.025, 0.035), 0.55),
    "lining": mat("lining", (1.0, 0.42, 0.10), 0.4, emit=0.04),
    "piping": mat("piping", (0.94, 0.94, 0.96), 0.4),
    "tee": mat("tee", (0.96, 0.96, 0.96), 0.65),
    "pants": mat("pants", (0.03, 0.03, 0.045), 0.55),
    "stripe": mat("stripe", (0.92, 0.92, 0.95), 0.4),
    "glove": mat("glove", (0.04, 0.04, 0.055), 0.6),
    "skate": mat("skate", (0.03, 0.03, 0.04), 0.4),
    "wheel": mat("wheel", (0.85, 0.88, 0.92), 0.2, metal=0.7),
    "crest": mat("crest", (0.88, 0.08, 0.10), 0.35, emit=0.25),
    "wing": mat("wing", (0.88, 0.90, 0.94), 0.3, metal=0.4),
    "belt": mat("belt", (0.05, 0.05, 0.07), 0.5),
    "buckle": mat("buckle", (0.8, 0.82, 0.88), 0.2, metal=0.75),
}

# ===================== BODY MESH (mirrored anime proportions) =====================
# ~1.75m tall, 8-head anime-ish (slightly larger head), long legs

def add_ring(bm, z, rx, ry, n=24, y_off=0.0):
    verts = []
    for i in range(n):
        a = (i / n) * math.tau
        v = bm.verts.new((math.cos(a) * rx, math.sin(a) * ry + y_off, z))
        verts.append(v)
    return verts

def bridge_rings(bm, a, b):
    n = len(a)
    for i in range(n):
        j = (i + 1) % n
        try:
            bm.faces.new([a[i], a[j], b[j], b[i]])
        except ValueError:
            pass

def make_body():
    mesh = bpy.data.meshes.new("Body")
    obj = bpy.data.objects.new("Body", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    n = 28
    # Profile: (z, rx, ry) — anime male teen, slim
    profile = [
        (0.02, 0.045, 0.055),   # sole placeholder (will be under skates)
        (0.08, 0.05, 0.06),     # ankle
        (0.22, 0.055, 0.065),   # shin mid — wait, this is torso builder; limbs separate
    ]
    # Actually build torso+head+hips as one, limbs separate for cleaner skinning
    # TORSO profile
    torso = [
        (0.90, 0.12, 0.10),   # crotch/hips bottom
        (0.96, 0.15, 0.12),   # hips
        (1.05, 0.13, 0.11),   # waist
        (1.15, 0.145, 0.12),  # lower ribs
        (1.28, 0.17, 0.135),  # chest
        (1.36, 0.155, 0.12),  # upper chest
        (1.42, 0.08, 0.07),   # neck base
        (1.48, 0.055, 0.055), # neck
        (1.52, 0.07, 0.075),  # chin
        (1.56, 0.09, 0.095),  # mouth
        (1.60, 0.10, 0.105),  # nose/eyes
        (1.66, 0.10, 0.10),   # forehead
        (1.72, 0.07, 0.075),  # crown
        (1.76, 0.02, 0.02),   # top
    ]
    rings = [add_ring(bm, z, rx, ry, n) for z, rx, ry in torso]
    for i in range(len(rings) - 1):
        bridge_rings(bm, rings[i], rings[i + 1])
    # Cap top
    top = bm.verts.new((0, 0, 1.77))
    for i in range(n):
        j = (i + 1) % n
        try: bm.faces.new([rings[-1][i], rings[-1][j], top])
        except ValueError: pass
    # Cap bottom
    bot = bm.verts.new((0, 0, 0.88))
    for i in range(n):
        j = (i + 1) % n
        try: bm.faces.new([bot, rings[0][j], rings[0][i]])
        except ValueError: pass

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    assign(obj, M["skin"])
    smooth_obj(obj, 2)
    apply_mods(obj)
    return obj

def make_limb(name, points, radii, matl, segs=16):
    """Loft a limb through points with radii. points are Vectors."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    rings = []
    for i, (p, r) in enumerate(zip(points, radii)):
        # local ring facing along path
        if i < len(points) - 1:
            direction = (points[i + 1] - p).normalized()
        else:
            direction = (p - points[i - 1]).normalized()
        # build orthonormal basis
        up = Vector((0, 0, 1))
        if abs(direction.dot(up)) > 0.9:
            up = Vector((1, 0, 0))
        x_axis = direction.cross(up).normalized()
        y_axis = direction.cross(x_axis).normalized()
        ring = []
        for k in range(segs):
            a = (k / segs) * math.tau
            offset = x_axis * math.cos(a) * r + y_axis * math.sin(a) * r
            ring.append(bm.verts.new(p + offset))
        rings.append(ring)
    for i in range(len(rings) - 1):
        bridge_rings(bm, rings[i], rings[i + 1])
    # end caps
    for ring, p, inward in ((rings[0], points[0], points[1] - points[0]),
                            (rings[-1], points[-1], points[-2] - points[-1])):
        c = bm.verts.new(p)
        for i in range(segs):
            j = (i + 1) % segs
            try:
                if inward.dot(points[-1] - points[0]) > 0 and ring is rings[-1]:
                    bm.faces.new([c, ring[j], ring[i]])
                elif ring is rings[0]:
                    bm.faces.new([c, ring[i], ring[j]])
                else:
                    bm.faces.new([c, ring[j], ring[i]])
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    assign(obj, matl)
    smooth_obj(obj, 2)
    apply_mods(obj)
    return obj

body = make_body()
print("Body", len(body.data.vertices))

limbs = []
# Arms
for sx, tag in ((-1, "L"), (1, "R")):
    arm_pts = [
        Vector((sx * 0.17, 0.0, 1.34)),
        Vector((sx * 0.25, 0.0, 1.32)),
        Vector((sx * 0.32, 0.02, 1.18)),
        Vector((sx * 0.35, 0.02, 1.04)),
        Vector((sx * 0.37, 0.0, 0.90)),
        Vector((sx * 0.38, 0.0, 0.80)),
    ]
    arm_r = [0.055, 0.05, 0.045, 0.042, 0.038, 0.035]
    limbs.append(make_limb(f"Arm_{tag}", arm_pts, arm_r, M["skin"]))
    # Legs
    leg_pts = [
        Vector((sx * 0.09, 0.0, 0.94)),
        Vector((sx * 0.095, 0.01, 0.78)),
        Vector((sx * 0.10, 0.02, 0.58)),
        Vector((sx * 0.10, 0.01, 0.40)),
        Vector((sx * 0.10, 0.0, 0.22)),
        Vector((sx * 0.10, 0.0, 0.10)),
    ]
    leg_r = [0.08, 0.075, 0.065, 0.055, 0.05, 0.045]
    limbs.append(make_limb(f"Leg_{tag}", leg_pts, leg_r, M["skin"]))

# Hands with fingers
def make_hand(tag, sx):
    parts = []
    # Palm
    palm = make_limb(f"Palm_{tag}",
                     [Vector((sx*0.38, 0.01, 0.78)), Vector((sx*0.39, -0.01, 0.70))],
                     [0.04, 0.035], M["skin"], segs=12)
    parts.append(palm)
    # Thumb + 4 fingers
    finger_data = [
        # (base offset, dir, lengths, radii)
        ((sx*0.02, 0.02, 0.0), (sx*0.3, 0.6, -0.4), [0.035, 0.03], [0.012, 0.01]),  # thumb
        ((sx*0.015, -0.01, -0.005), (sx*0.05, -0.3, -1), [0.04, 0.035, 0.03], [0.01, 0.009, 0.008]),
        ((0.0, -0.015, -0.002), (0, -0.25, -1), [0.045, 0.038, 0.032], [0.01, 0.009, 0.008]),
        ((-sx*0.015, -0.01, -0.005), (-sx*0.05, -0.3, -1), [0.04, 0.035, 0.03], [0.01, 0.009, 0.008]),
        ((-sx*0.028, -0.005, -0.008), (-sx*0.15, -0.2, -1), [0.03, 0.025], [0.009, 0.007]),
    ]
    base = Vector((sx*0.39, -0.01, 0.70))
    for fi, (off, direc, lens, rads) in enumerate(finger_data):
        d = Vector(direc).normalized()
        pts = [base + Vector(off)]
        for L in lens:
            pts.append(pts[-1] + d * L)
        # radii list length = len(pts)
        while len(rads) < len(pts):
            rads.append(rads[-1])
        parts.append(make_limb(f"Finger_{tag}_{fi}", pts, rads, M["skin"], segs=8))
    return parts

hand_parts = make_hand("L", -1) + make_hand("R", 1)

# ===================== FACE (project texture onto front of head) =====================
# UV-unwrap head front: create a face plane slightly in front, subdivided, with face texture
bpy.ops.mesh.primitive_plane_add(size=0.22, location=(0, -0.11, 1.60))
face = bpy.context.active_object
face.name = "FaceDecal"
face.rotation_euler = (math.pi/2, 0, 0)
face.scale = (1.0, 1.15, 1)
xf(face)
# Subdivide for slight curve
select_only(face)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=4)
bpy.ops.object.mode_set(mode='OBJECT')
# Bend slightly around head (proportional)
for v in face.data.vertices:
    # push center forward a bit less at edges — wrap
    x = v.co.x
    v.co.y = -0.11 - 0.04 * (1 - (x / 0.12) ** 2) if abs(x) < 0.12 else v.co.y
face.data.update()
assign(face, M["skin_face"])
smooth_obj(face, 1)
apply_mods(face)

# ===================== HAIR (curve strands) =====================
def hair_strand(i, root, tip, weight, matl):
    curve = bpy.data.curves.new(f"HairC_{i}", 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 8
    curve.bevel_depth = weight
    curve.bevel_resolution = 3
    curve.fill_mode = 'FULL'
    spline = curve.splines.new('BEZIER')
    mid = (Vector(root) + Vector(tip)) * 0.5 + Vector((0, 0, 0.05))
    spline.bezier_points.add(2)
    pts = [Vector(root), mid, Vector(tip)]
    for bp, p in zip(spline.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
        bp.radius = 1.0
    # taper tip
    spline.bezier_points[0].radius = 1.2
    spline.bezier_points[-1].radius = 0.15
    obj = bpy.data.objects.new(f"Hair_{i}", curve)
    bpy.context.collection.objects.link(obj)
    assign(obj, matl)
    # convert to mesh
    select_only(obj)
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.active_object
    obj.name = f"Hair_{i}"
    smooth_obj(obj, 1)
    apply_mods(obj)
    return obj

hair_roots = []
# Layered spikes from scalp
scalp = Vector((0, 0.0, 1.68))
strand_defs = []
import random
random.seed(7)
# Main crown spikes
for i in range(28):
    a = (i / 28) * math.tau
    tilt = 0.35 + 0.25 * math.sin(i * 1.7)
    r = 0.06
    root = Vector((math.cos(a) * r * 0.5, math.sin(a) * r * 0.4 + 0.01, 1.66 + 0.02 * math.sin(i)))
    tip = root + Vector((math.cos(a) * (0.12 + 0.08 * (i % 3)),
                         math.sin(a) * (0.10 + 0.06 * (i % 2)) - 0.05,
                         0.18 + 0.12 * ((i * 3) % 5) / 5 + tilt * 0.15))
    w = 0.018 - 0.004 * (i % 4)
    strand_defs.append((root, tip, w, M["hair"] if i % 3 else M["hair2"]))
# Front bangs / side spikes toward face
for i, sx in enumerate([-1, -0.5, 0.5, 1, -0.75, 0.75]):
    root = Vector((sx * 0.06, -0.04, 1.65))
    tip = Vector((sx * 0.12, -0.14, 1.55 + 0.08 * (i % 2)))
    strand_defs.append((root, tip, 0.016, M["hair"]))
# Extra volume on top
for i in range(12):
    a = (i / 12) * math.tau
    root = Vector((math.cos(a) * 0.03, math.sin(a) * 0.03, 1.70))
    tip = root + Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.28 + 0.05 * (i % 3)))
    strand_defs.append((root, tip, 0.02, M["hair"]))

hair_objs = [hair_strand(i, *sd[:3], sd[3]) for i, sd in enumerate(strand_defs)]
print("Hair strands", len(hair_objs))

# Hair cap under strands
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.115, location=(0, 0.01, 1.65), segments=24, ring_count=16)
hcap = bpy.context.active_object
hcap.name = "HairCap"
hcap.scale = (1.05, 1.1, 0.72)
xf(hcap)
assign(hcap, M["hair"])
smooth_obj(hcap, 2)
apply_mods(hcap)

# ===================== CLOTHES =====================
clothes = []

def cloth_capsule(name, r, h, loc, matl, rot=(0,0,0), scale=(1,1,1), segs=20):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=segs, location=loc)
    c = bpy.context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=segs, ring_count=12, location=(loc[0], loc[1], loc[2]+h/2))
    s1 = bpy.context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=segs, ring_count=12, location=(loc[0], loc[1], loc[2]-h/2))
    s2 = bpy.context.active_object
    for o in (c, s1, s2):
        o.rotation_euler = rot
        o.scale = scale
        o.select_set(True)
    bpy.context.view_layer.objects.active = c
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    bpy.ops.object.mode_set(mode='OBJECT')
    xf(o)
    assign(o, matl)
    smooth_obj(o, 2)
    apply_mods(o)
    return o

# Tee with slight folds via displace
tee = cloth_capsule("Tee", 0.165, 0.36, (0, 0, 1.14), M["tee"], scale=(1.1, 0.92, 1), segs=24)
# Displace folds
tex = bpy.data.textures.new("ClothFold", 'CLOUDS')
tex.noise_scale = 0.35
disp = tee.modifiers.new("Fold", 'DISPLACE')
disp.texture = tex
disp.strength = 0.012
apply_mods(tee)
clothes.append(tee)

# Open jacket via bmesh shell + solidify + displace
def make_jacket():
    mesh = bpy.data.meshes.new("Jacket")
    obj = bpy.data.objects.new("Jacket", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    nz, na = 16, 36
    gap = math.radians(32)
    for iz in range(nz + 1):
        t = iz / nz
        z = 0.95 + 0.46 * t
        # sculpted volume: wider chest, pinched waist
        waist = 1.0 - 0.12 * math.sin(t * math.pi)
        chest = 1.0 + 0.08 * math.sin(max(0, t - 0.4) * math.pi)
        flare = waist * chest
        rx, ry = 0.195 * flare, 0.165 * flare
        a0 = -math.pi / 2 + gap
        a1 = -math.pi / 2 - gap + 2 * math.pi
        for ia in range(na + 1):
            a = a0 + (a1 - a0) * (ia / na)
            # slight fold waves
            wave = 1.0 + 0.025 * math.sin(ia * 0.7 + t * 4)
            bm.verts.new((math.cos(a) * rx * wave, math.sin(a) * ry * wave, z))
    bm.verts.ensure_lookup_table()
    for iz in range(nz):
        for ia in range(na):
            i0 = iz * (na + 1) + ia
            try:
                bm.faces.new([bm.verts[i0], bm.verts[i0+1], bm.verts[i0+1+(na+1)], bm.verts[i0+(na+1)]])
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    sol = obj.modifiers.new("Sol", 'SOLIDIFY')
    sol.thickness = 0.022
    sol.offset = 1.0
    # folds
    tex2 = bpy.data.textures.new("JacketFold", 'CLOUDS')
    tex2.noise_scale = 0.45
    disp = obj.modifiers.new("Fold", 'DISPLACE')
    disp.texture = tex2
    disp.strength = 0.01
    apply_mods(obj)
    assign(obj, M["jacket"])
    smooth_obj(obj, 2)
    apply_mods(obj)
    return obj

clothes.append(make_jacket())

# Lining visibility
for sx in (-1, 1):
    clothes.append(cloth_capsule(f"Lining_{sx}", 0.024, 0.40, (sx*0.065, -0.15, 1.16), M["lining"], scale=(0.5, 0.4, 1), segs=12))

# Collar high
bpy.ops.mesh.primitive_torus_add(major_radius=0.115, minor_radius=0.042, major_segments=32, minor_segments=14,
                                 location=(0, -0.025, 1.41))
collar = bpy.context.active_object
collar.name = "Collar"
collar.scale = (1.0, 1.05, 1.15)
xf(collar)
assign(collar, M["jacket"])
smooth_obj(collar, 2)
apply_mods(collar)
clothes.append(collar)
bpy.ops.mesh.primitive_torus_add(major_radius=0.105, minor_radius=0.028, major_segments=28, minor_segments=12,
                                 location=(0, -0.045, 1.415))
ci = bpy.context.active_object
ci.name = "CollarIn"
xf(ci)
assign(ci, M["lining"])
smooth_obj(ci, 1)
apply_mods(ci)
clothes.append(ci)

# Crest
bpy.ops.mesh.primitive_cylinder_add(radius=0.085, depth=0.028, vertices=28, location=(0, 0.17, 1.22))
crest = bpy.context.active_object
crest.name = "Crest"
crest.rotation_euler = (math.pi/2, 0, 0)
xf(crest)
assign(crest, M["crest"])
smooth_obj(crest, 1)
apply_mods(crest)
clothes.append(crest)
bpy.ops.mesh.primitive_cylinder_add(radius=0.042, depth=0.032, vertices=16, location=(0, 0.18, 1.22))
crestin = bpy.context.active_object
crestin.name = "CrestIn"
crestin.rotation_euler = (math.pi/2, 0, 0)
xf(crestin)
assign(crestin, M["piping"])
clothes.append(crestin)
for sx in (-1, 1):
    bpy.ops.mesh.primitive_cone_add(radius1=0.03, radius2=0.005, depth=0.16, vertices=14,
                                    location=(sx*0.14, 0.17, 1.245))
    w = bpy.context.active_object
    w.name = f"Wing_{sx}"
    w.rotation_euler = (0, sx*math.pi/2, sx*0.5)
    xf(w)
    assign(w, M["wing"])
    smooth_obj(w, 1)
    apply_mods(w)
    clothes.append(w)

# Sleeves
for sx, tag in ((-1, "L"), (1, "R")):
    clothes.append(cloth_capsule(f"SleeveU_{tag}", 0.062, 0.22, (sx*0.30, 0.01, 1.18), M["jacket"], segs=18))
    clothes.append(cloth_capsule(f"SleeveF_{tag}", 0.052, 0.18, (sx*0.36, 0.0, 0.95), M["jacket"], segs=16))
    clothes.append(cloth_capsule(f"Pipe_{tag}", 0.01, 0.34, (sx*0.265, -0.05, 1.12), M["piping"], segs=8))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.055, minor_radius=0.02, major_segments=20, minor_segments=12,
                                     location=(sx*0.37, 0, 0.84))
    cuff = bpy.context.active_object
    cuff.name = f"ArmCuff_{tag}"
    cuff.rotation_euler = (math.pi/2, 0, 0)
    xf(cuff)
    assign(cuff, M["lining"])
    smooth_obj(cuff, 1)
    apply_mods(cuff)
    clothes.append(cuff)
    # Gloves fingerless
    clothes.append(cloth_capsule(f"Glove_{tag}", 0.042, 0.055, (sx*0.385, 0.0, 0.76), M["glove"], scale=(0.95, 1.15, 1), segs=14))

# Belt + strap
bpy.ops.mesh.primitive_torus_add(major_radius=0.155, minor_radius=0.02, major_segments=32, minor_segments=12,
                                 location=(0, 0, 0.96))
belt = bpy.context.active_object
belt.name = "Belt"
belt.rotation_euler = (math.pi/2, 0, 0)
xf(belt)
assign(belt, M["belt"])
smooth_obj(belt, 1)
apply_mods(belt)
clothes.append(belt)
clothes.append(cloth_capsule("Buckle", 0.032, 0.018, (0, -0.16, 0.96), M["buckle"], rot=(math.pi/2, 0, 0), segs=12))
clothes.append(cloth_capsule("Strap", 0.014, 0.34, (-0.12, -0.05, 0.76), M["belt"], rot=(0.3, 0, 0.15), segs=10))
clothes.append(cloth_capsule("StrapTip", 0.02, 0.03, (-0.145, -0.09, 0.58), M["piping"], segs=10))

# Pants with folds
for sx, tag in ((-1, "L"), (1, "R")):
    pt = cloth_capsule(f"PantThigh_{tag}", 0.095, 0.38, (sx*0.10, 0.0, 0.70), M["pants"], scale=(1.0, 0.95, 1), segs=20)
    texp = bpy.data.textures.new(f"PantFold_{tag}", 'CLOUDS')
    texp.noise_scale = 0.4
    d = pt.modifiers.new("Fold", 'DISPLACE')
    d.texture = texp
    d.strength = 0.008
    apply_mods(pt)
    clothes.append(pt)
    clothes.append(cloth_capsule(f"PantShin_{tag}", 0.072, 0.30, (sx*0.10, 0.0, 0.28), M["pants"], segs=18))
    clothes.append(cloth_capsule(f"Stripe_{tag}", 0.014, 0.64, (sx*0.18, 0.0, 0.50), M["stripe"], segs=8))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.078, minor_radius=0.025, major_segments=20, minor_segments=12,
                                     location=(sx*0.10, 0, 0.12))
    lc = bpy.context.active_object
    lc.name = f"LegCuff_{tag}"
    lc.rotation_euler = (math.pi/2, 0, 0)
    xf(lc)
    assign(lc, M["lining"])
    smooth_obj(lc, 1)
    apply_mods(lc)
    clothes.append(lc)
    # Believable skate boot
    boot = cloth_capsule(f"Boot_{tag}", 0.065, 0.20, (sx*0.10, -0.05, 0.07), M["skate"],
                         rot=(math.pi/2.2, 0, 0), scale=(1.15, 0.95, 1.3), segs=18)
    clothes.append(boot)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(sx*0.10, -0.17, 0.055), segments=18, ring_count=12)
    toe = bpy.context.active_object
    toe.name = f"Toe_{tag}"
    toe.scale = (1.1, 1.4, 0.8)
    xf(toe)
    assign(toe, M["skate"])
    smooth_obj(toe, 2)
    apply_mods(toe)
    clothes.append(toe)
    clothes.append(cloth_capsule(f"Frame_{tag}", 0.02, 0.28, (sx*0.10, -0.03, 0.005), M["buckle"],
                                 rot=(math.pi/2, 0, 0), segs=10))
    for wi, wy in enumerate((-0.12, -0.02, 0.08, 0.17)):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.016, major_segments=18, minor_segments=10,
                                         location=(sx*0.10, wy, -0.015))
        wh = bpy.context.active_object
        wh.name = f"Wheel_{tag}_{wi}"
        wh.rotation_euler = (0, math.pi/2, 0)
        xf(wh)
        assign(wh, M["wheel"])
        smooth_obj(wh, 0)
        clothes.append(wh)
    clothes.append(cloth_capsule(f"SkateBuckle_{tag}", 0.028, 0.06, (sx*0.10, 0.02, 0.13), M["buckle"],
                                 rot=(math.pi/2, 0, 0), segs=10))

print("Clothes", len(clothes))

# ===================== ARMATURE =====================
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
arm_obj = bpy.context.active_object
arm_obj.name = "SkaterArmature"
eb = arm_obj.data.edit_bones
for b in list(eb):
    eb.remove(b)

def B(name, head, tail, parent=None):
    b = eb.new(name)
    b.head = Vector(head)
    b.tail = Vector(tail)
    if parent:
        b.parent = eb[parent]
    return b

B("root", (0,0,0), (0,0,0.08))
B("hips", (0,0,0.92), (0,0,1.02), "root")
B("spine", (0,0,1.02), (0,0,1.20), "hips")
B("chest", (0,0,1.20), (0,0,1.38), "spine")
B("neck", (0,0,1.38), (0,0,1.50), "chest")
B("head", (0,0,1.50), (0,0,1.74), "neck")
for s, sx in (("L", -1), ("R", 1)):
    B(f"shoulder_{s}", (sx*0.14, 0, 1.34), (sx*0.22, 0, 1.34), "chest")
    B(f"upper_arm_{s}", (sx*0.22, 0, 1.34), (sx*0.34, 0, 1.05), f"shoulder_{s}")
    B(f"forearm_{s}", (sx*0.34, 0, 1.05), (sx*0.38, 0, 0.82), f"upper_arm_{s}")
    B(f"hand_{s}", (sx*0.38, 0, 0.82), (sx*0.39, -0.02, 0.70), f"forearm_{s}")
    B(f"thigh_{s}", (sx*0.09, 0, 0.94), (sx*0.10, 0.01, 0.48), "hips")
    B(f"shin_{s}", (sx*0.10, 0.01, 0.48), (sx*0.10, 0, 0.12), f"thigh_{s}")
    B(f"foot_{s}", (sx*0.10, 0, 0.12), (sx*0.10, -0.16, 0.03), f"shin_{s}")
bpy.ops.object.mode_set(mode='OBJECT')

def bone_for(n):
    n = n.lower()
    if n.startswith(("hair", "face", "spike")) or n == "haircap": return "head"
    if n.startswith(("sleeveu_l", "pipe_l")): return "upper_arm_L"
    if n.startswith(("sleeveu_r", "pipe_r")): return "upper_arm_R"
    if n.startswith(("sleevef_l", "armcuff_l")): return "forearm_L"
    if n.startswith(("sleevef_r", "armcuff_r")): return "forearm_R"
    if n.startswith(("glove_l", "finger_l", "palm_l", "arm_l")): return "hand_L" if "glove" in n or "finger" in n or "palm" in n else "upper_arm_L"
    if n.startswith("arm_l"): return "upper_arm_L"
    if n.startswith("arm_r"): return "upper_arm_R"
    if n.startswith(("glove_r", "finger_r", "palm_r")): return "hand_R"
    if n.startswith("leg_l"): return "thigh_L"
    if n.startswith("leg_r"): return "thigh_R"
    if n.startswith(("pantthigh_l", "stripe_l")): return "thigh_L"
    if n.startswith(("pantthigh_r", "stripe_r")): return "thigh_R"
    if n.startswith(("pantshin_l", "legcuff_l")): return "shin_L"
    if n.startswith(("pantshin_r", "legcuff_r")): return "shin_R"
    if any(n.startswith(p) for p in ("boot_l","toe_l","frame_l","wheel_l","skatebuckle_l")): return "foot_L"
    if any(n.startswith(p) for p in ("boot_r","toe_r","frame_r","wheel_r","skatebuckle_r")): return "foot_R"
    if n in ("belt","buckle","strap","straptip"): return "hips"
    if n in ("jacket","tee","collar","collarin","crest","crestin","body") or n.startswith(("lining","wing")): return "chest"
    return "spine"

def skin(obj, bname):
    if obj.type not in ('MESH',):
        return
    select_only(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.vertex_groups.clear()
    if bname not in [g.name for g in obj.vertex_groups]:
        vg = obj.vertex_groups.new(name=bname)
    else:
        vg = obj.vertex_groups[bname]
    idxs = [v.index for v in obj.data.vertices]
    if idxs:
        vg.add(idxs, 1.0, 'REPLACE')
    for mod in list(obj.modifiers):
        if mod.type == 'ARMATURE':
            obj.modifiers.remove(mod)
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm_obj
    obj.parent = arm_obj

# Auto-weight body + limbs
to_autoweight = [body] + limbs
bpy.ops.object.select_all(action='DESELECT')
for o in to_autoweight:
    o.select_set(True)
arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
try:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except Exception as e:
    print("autoweight fail", e)
    for o in to_autoweight:
        skin(o, "spine")

all_rest = [face, hcap] + hair_objs + clothes + hand_parts
for o in all_rest:
    # finer bone mapping for arms/hands
    bn = bone_for(o.name)
    if o.name.startswith("Arm_L"): bn = "upper_arm_L"
    if o.name.startswith("Arm_R"): bn = "upper_arm_R"
    if o.name.startswith("Leg_L"): bn = "thigh_L"
    if o.name.startswith("Leg_R"): bn = "thigh_R"
    if o.name.startswith("Palm_L") or o.name.startswith("Finger_L"): bn = "hand_L"
    if o.name.startswith("Palm_R") or o.name.startswith("Finger_R"): bn = "hand_R"
    skin(o, bn)

# ===================== ANIMATIONS =====================
arm_obj.animation_data_create()

def kf(bn, fr, loc=None, rot=None):
    pb = arm_obj.pose.bones.get(bn)
    if not pb: return
    pb.rotation_mode = 'XYZ'
    if loc is not None:
        pb.location = loc
        pb.keyframe_insert("location", frame=fr)
    if rot is not None:
        pb.rotation_euler = Euler(rot)
        pb.keyframe_insert("rotation_euler", frame=fr)

def reset(fr):
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.location = (0,0,0)
        pb.rotation_euler = (0,0,0)
        pb.keyframe_insert("location", frame=fr)
        pb.keyframe_insert("rotation_euler", frame=fr)

def make_action(name, fn):
    for pb in arm_obj.pose.bones:
        pb.location = (0,0,0)
        pb.rotation_euler = (0,0,0)
        pb.rotation_mode = 'XYZ'
    act = bpy.data.actions.new(name)
    arm_obj.animation_data.action = act
    fn()
    tr = arm_obj.animation_data.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, int(act.frame_range[0]), act)
    arm_obj.animation_data.action = None

def anim_idle():
    reset(1)
    for f, b, az in ((1, 0.0, 0.08), (40, 0.01, 0.12), (80, 0.0, 0.08)):
        kf("hips", f, loc=(0, 0, b * 0.3))
        kf("spine", f, rot=(b, 0, 0))
        kf("chest", f, rot=(b * 0.5, 0, 0))
        kf("head", f, rot=(0, math.sin(f / 80 * math.tau) * 0.05, 0))
        kf("upper_arm_L", f, rot=(0.15, 0, az + 0.05))
        kf("upper_arm_R", f, rot=(0.15, 0, -(az + 0.05)))

def anim_skate():
    for f, ph in ((1, 0), (20, 1), (40, 0), (60, -1), (80, 0)):
        sw = ph * 0.55
        kf("thigh_L", f, rot=(sw, 0, 0))
        kf("thigh_R", f, rot=(-sw, 0, 0))
        kf("shin_L", f, rot=(-abs(sw) * 0.5, 0, 0))
        kf("shin_R", f, rot=(-abs(sw) * 0.5, 0, 0))
        kf("upper_arm_L", f, rot=(-sw * 0.7, 0, 0.2))
        kf("upper_arm_R", f, rot=(sw * 0.7, 0, -0.2))
        kf("spine", f, rot=(0.18, 0, -sw * 0.08))
        kf("hips", f, loc=(0, 0, abs(ph) * 0.02))
        kf("head", f, rot=(-0.08, sw * 0.06, 0))

def anim_grind():
    for f in (1, 40, 80):
        bal = math.sin(f / 80 * math.tau) * 0.04
        kf("hips", f, loc=(0, 0, -0.08), rot=(0.35, 0, bal))
        kf("spine", f, rot=(0.28, 0, 0))
        kf("head", f, rot=(-0.18, 0, 0))
        kf("thigh_L", f, rot=(-0.2, 0.25, 0.12))
        kf("thigh_R", f, rot=(0.4, -0.1, -0.05))
        kf("shin_L", f, rot=(0.5, 0, 0))
        kf("shin_R", f, rot=(0.2, 0, 0))
        kf("foot_L", f, rot=(0.3, 0.55, 0))
        kf("upper_arm_L", f, rot=(-0.3, 0, 1.0))
        kf("upper_arm_R", f, rot=(-0.3, 0, -1.0))

def anim_air():
    for f in (1, 40, 80):
        kf("hips", f, loc=(0, 0, 0.02), rot=(-0.1, 0, 0))
        kf("spine", f, rot=(-0.22, 0, 0))
        kf("thigh_L", f, rot=(0.95, 0.1, 0))
        kf("thigh_R", f, rot=(0.7, -0.2, 0))
        kf("shin_L", f, rot=(-1.25, 0, 0))
        kf("shin_R", f, rot=(-1.0, 0, 0))
        kf("upper_arm_L", f, rot=(-0.85, 0, 0.3))
        kf("forearm_L", f, rot=(-0.65, 0, 0))
        kf("upper_arm_R", f, rot=(0.2, 0, -0.8))
        kf("head", f, rot=(0.15, 0, 0))

make_action("idle", anim_idle)
make_action("skate", anim_skate)
make_action("grind", anim_grind)
make_action("air", anim_air)
for t in arm_obj.animation_data.nla_tracks:
    if t.name == "idle" and t.strips:
        arm_obj.animation_data.action = t.strips[0].action
        break

scene.frame_start = 1
scene.frame_end = 80
scene.frame_set(1)

# Export
bpy.ops.object.select_all(action='DESELECT')
arm_obj.select_set(True)
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.export_scene.gltf(
    filepath=GLB, export_format='GLB', use_selection=True,
    export_animations=True, export_nla_strips=True, export_skins=True,
    export_apply=False, export_yup=True)
print("DONE GLB", GLB, os.path.getsize(GLB))
