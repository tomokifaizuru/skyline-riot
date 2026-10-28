#!/usr/bin/env python3
"""Sky Trek skater v3 — thicker continuous body, jacket sleeves, fitted clothes, armature, GLB."""
import bpy, bmesh, math, os
from mathutils import Vector, Euler

OUT = "/workspace/skyline-riot/assets/character"
GLB = f"{OUT}/skater.glb"
BLEND = f"{OUT}/skater.blend"

bpy.ops.wm.read_factory_settings(use_empty=True)

def wipe():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures,
                 bpy.data.actions, bpy.data.images, bpy.data.metaballs):
        for b in list(coll):
            coll.remove(b)
wipe()

def mat(name, col, rough=0.5, metal=0.0, emit=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Emission Color" in b.inputs:
        b.inputs["Emission Color"].default_value = (*col, 1)
        b.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = (*col, 1)
    return m

M = {
    "skin": mat("skin", (0.96, 0.80, 0.68), 0.55),
    "hair": mat("hair", (0.045, 0.065, 0.13), 0.4),
    "hair2": mat("hair2", (0.08, 0.11, 0.2), 0.4),
    "jacket": mat("jacket", (0.03, 0.03, 0.045), 0.5),
    "lining": mat("lining", (1.0, 0.40, 0.08), 0.45, emit=0.08),
    "piping": mat("piping", (0.95, 0.95, 0.97), 0.4),
    "tee": mat("tee", (0.97, 0.97, 0.97), 0.6),
    "pants": mat("pants", (0.035, 0.035, 0.05), 0.5),
    "stripe": mat("stripe", (0.93, 0.93, 0.96), 0.4),
    "glove": mat("glove", (0.04, 0.04, 0.06), 0.55),
    "skate": mat("skate", (0.03, 0.03, 0.05), 0.45),
    "wheel": mat("wheel", (0.82, 0.86, 0.92), 0.22, metal=0.65),
    "crest": mat("crest", (0.9, 0.1, 0.12), 0.4, emit=0.35),
    "wing": mat("wing", (0.9, 0.92, 0.95), 0.3, metal=0.35),
    "belt": mat("belt", (0.06, 0.06, 0.08), 0.5),
    "buckle": mat("buckle", (0.78, 0.8, 0.86), 0.22, metal=0.7),
    "eye_w": mat("eye_w", (1,1,1), 0.25),
    "eye_i": mat("eye_i", (0.14, 0.09, 0.09), 0.35),
    "eye_p": mat("eye_p", (0.02, 0.02, 0.03), 0.3),
    "brow": mat("brow", (0.05, 0.05, 0.09), 0.5),
}

def assign(o, m):
    o.data.materials.clear(); o.data.materials.append(m)

def smooth(o, lv=1):
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth()
    if lv:
        s = o.modifiers.new("S", 'SUBSURF'); s.levels = lv; s.render_levels = lv+1

def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    for mod in list(o.modifiers):
        try: bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception: pass
    o.select_set(False)

def xf(o):
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    o.select_set(False)

def join_selected(name):
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0015)
    bpy.ops.object.mode_set(mode='OBJECT')
    return o

def capsule(name, r, h, loc, matl, rot=(0,0,0), scale=(1,1,1), segs=16, sub=1):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=segs, location=loc)
    c = bpy.context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=segs, ring_count=10,
                                         location=(loc[0], loc[1], loc[2]+h/2))
    s1 = bpy.context.active_object
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=segs, ring_count=10,
                                         location=(loc[0], loc[1], loc[2]-h/2))
    s2 = bpy.context.active_object
    for o in (c, s1, s2):
        o.rotation_euler = rot
        o.scale = scale
        o.select_set(True)
    bpy.context.view_layer.objects.active = c
    o = join_selected(name)
    xf(o)
    assign(o, matl)
    smooth(o, sub)
    apply_mods(o)
    return o

# ===================== BODY via thicker metaballs =====================
# Create meta at origin so mesh coords are world-ish
bpy.ops.object.metaball_add(type='BALL', location=(0, 0, 0))
meta = bpy.context.active_object
meta.name = "BodyMeta"
mb = meta.data
mb.resolution = 0.035
mb.render_resolution = 0.025
mb.threshold = 0.35

def mel(typ, co, radius, sx=1, sy=1, sz=1):
    el = mb.elements.new() if len(mb.elements) and mb.elements[0].radius > 0.001 and mb.elements[0].co.length > 0.001 else mb.elements[0]
    # always new except first reuse
    return el

# Clear and rebuild elements properly
# First element exists
e = mb.elements[0]
e.type = 'BALL'
e.co = Vector((0, 0, 1.56))
e.radius = 0.125  # head

elems = [
    ('BALL', (0, -0.02, 1.48), 0.09, 1, 1, 1),       # jaw
    ('BALL', (0, 0, 1.40), 0.06, 1, 1, 1),            # neck
    ('ELLIPSOID', (0, 0, 1.26), 0.16, 1.2, 0.95, 1.15), # chest — deeper Y
    ('ELLIPSOID', (0, 0, 1.08), 0.145, 1.1, 0.9, 1.0), # belly
    ('ELLIPSOID', (0, 0, 0.94), 0.15, 1.15, 0.9, 0.85), # hips
]
# arms — thicker, connected
for sx in (-1, 1):
    elems += [
        ('BALL', (sx*0.18, 0, 1.34), 0.065, 1,1,1),
        ('ELLIPSOID', (sx*0.30, 0, 1.20), 0.055, 0.9, 0.9, 1.7),
        ('BALL', (sx*0.34, 0, 1.05), 0.048, 1,1,1),
        ('ELLIPSOID', (sx*0.36, 0, 0.90), 0.045, 0.9, 0.9, 1.6),
        ('BALL', (sx*0.37, 0, 0.76), 0.052, 1,1,1),
    ]
# legs — long
for sx in (-1, 1):
    elems += [
        ('ELLIPSOID', (sx*0.10, 0, 0.72), 0.08, 0.95, 0.95, 1.8),
        ('BALL', (sx*0.10, 0.01, 0.48), 0.06, 1,1,1),
        ('ELLIPSOID', (sx*0.10, 0, 0.28), 0.06, 0.95, 0.95, 1.7),
        ('BALL', (sx*0.10, 0, 0.11), 0.045, 1,1,1),
    ]

for typ, co, radius, sx, sy, sz in elems:
    el = mb.elements.new(type=typ)
    el.co = Vector(co)
    el.radius = radius
    if typ == 'ELLIPSOID':
        el.size_x = sx; el.size_y = sy; el.size_z = sz

bpy.ops.object.convert(target='MESH')
body = bpy.context.active_object
body.name = "Body"
# Ensure origin at world origin
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')  # cursor at 0
# Actually set origin to geometry center then move — simpler: apply and fix
body.location = (0, 0, 0)
xf(body)
# Remesh
rm = body.modifiers.new("R", 'REMESH')
rm.mode = 'VOXEL'; rm.voxel_size = 0.016
apply_mods(body)
sm = body.modifiers.new("Sm", 'SMOOTH'); sm.factor = 0.7; sm.iterations = 12
apply_mods(body)
try:
    lap = body.modifiers.new("L", 'LAPLACIAN_SMOOTH'); lap.iterations = 5; lap.lambda_factor = 0.35
    apply_mods(body)
except Exception:
    pass
assign(body, M["skin"])
smooth(body, 0)
print("Body verts", len(body.data.vertices),
      "X", min(v.co.x for v in body.data.vertices), max(v.co.x for v in body.data.vertices),
      "Y", min(v.co.y for v in body.data.vertices), max(v.co.y for v in body.data.vertices),
      "Z", min(v.co.z for v in body.data.vertices), max(v.co.z for v in body.data.vertices))

extras = []

# Face — front is -Y
def disc(name, r, loc, matl, sy=1.0, rz=0.0):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=0.01, vertices=24, location=loc)
    o = bpy.context.active_object; o.name = name
    o.rotation_euler = (math.pi/2, 0, rz)
    o.scale = (1, sy, 1); xf(o); assign(o, matl); smooth(o, 0); return o

for sx, t in ((-0.042, "L"), (0.042, "R")):
    extras += [
        disc(f"EW_{t}", 0.032, (sx, -0.125, 1.575), M["eye_w"], 1.3),
        disc(f"EI_{t}", 0.019, (sx, -0.131, 1.572), M["eye_i"], 1.35),
        disc(f"EP_{t}", 0.01, (sx, -0.135, 1.572), M["eye_p"], 1.2),
        disc(f"EH_{t}", 0.006, (sx - 0.009, -0.137, 1.583), M["eye_w"]),
        disc(f"BR_{t}", 0.034, (sx, -0.128, 1.618), M["brow"], 0.28, 0.28 if t=="L" else -0.28),
    ]
extras.append(disc("Mouth", 0.018, (0, -0.12, 1.505), M["brow"], 0.25))

# Hair cap smaller so face shows
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, location=(0, 0.02, 1.64), segments=24, ring_count=16)
cap = bpy.context.active_object; cap.name = "HairCap"
cap.scale = (1.08, 1.15, 0.65); xf(cap); assign(cap, M["hair"]); smooth(cap, 1); apply_mods(cap)
extras.append(cap)

def spike(i, loc, d, ln, r0, r1, matl):
    bpy.ops.mesh.primitive_cone_add(radius1=r0, radius2=r1, depth=ln, vertices=12)
    o = bpy.context.active_object; o.name = f"Spike_{i}"
    dd = Vector(d).normalized()
    o.rotation_euler = dd.to_track_quat('Z', 'Y').to_euler()
    o.location = Vector(loc) + dd * (ln * 0.42)
    xf(o); assign(o, matl); smooth(o, 1); apply_mods(o)
    return o

spikespec = [
    ((0,-0.03,1.70),(0.0,-0.25,1),0.28,0.075,0.006),
    ((-0.07,-0.02,1.68),(-0.5,-0.2,1),0.25,0.065,0.006),
    ((0.07,-0.02,1.68),(0.5,-0.2,1),0.25,0.065,0.006),
    ((-0.11,0.02,1.64),(-0.85,0.15,0.7),0.22,0.055,0.005),
    ((0.11,0.02,1.64),(0.85,0.15,0.7),0.22,0.055,0.005),
    ((-0.09,0.07,1.62),(-0.55,0.55,0.55),0.19,0.05,0.005),
    ((0.09,0.07,1.62),(0.55,0.55,0.55),0.19,0.05,0.005),
    ((0,0.09,1.65),(0,0.75,0.55),0.18,0.055,0.005),
    ((0,-0.09,1.66),(0,-0.85,0.45),0.17,0.05,0.004),
    ((-0.05,-0.07,1.60),(-0.35,-0.65,0.5),0.16,0.045,0.004),
    ((0.05,-0.07,1.60),(0.35,-0.65,0.5),0.16,0.045,0.004),
    ((-0.13,0,1.57),(-1,0,0.25),0.15,0.042,0.004),
    ((0.13,0,1.57),(1,0,0.25),0.15,0.042,0.004),
    ((0,0.02,1.76),(0.05,0.1,1),0.30,0.065,0.005),
    ((-0.04,0.03,1.73),(-0.25,0.2,1),0.24,0.055,0.005),
    ((0.04,0.03,1.73),(0.25,0.2,1),0.24,0.055,0.005),
    ((-0.08,-0.04,1.72),(-0.4,-0.35,0.9),0.20,0.05,0.004),
    ((0.08,-0.04,1.72),(0.4,-0.35,0.9),0.20,0.05,0.004),
]
for i, (loc,d,ln,r0,r1) in enumerate(spikespec):
    extras.append(spike(i, loc, d, ln, r0, r1, M["hair"] if i%3 else M["hair2"]))

# Tee
extras.append(capsule("Tee", 0.16, 0.34, (0,0,1.14), M["tee"], scale=(1.08, 0.88, 1), segs=20, sub=1))

# Jacket shell (open front)
def make_jacket():
    mesh = bpy.data.meshes.new("Jacket")
    obj = bpy.data.objects.new("Jacket", mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    nz, na = 14, 32
    z0, z1 = 0.96, 1.40
    gap = math.radians(30)
    for iz in range(nz+1):
        t = iz/nz
        z = z0+(z1-z0)*t
        # waist pinch
        flare = 1.0 - 0.08*math.sin(t*math.pi)
        rx, ry = 0.185*flare, 0.155*flare
        a0 = -math.pi/2 + gap
        a1 = -math.pi/2 - gap + 2*math.pi
        for ia in range(na+1):
            a = a0 + (a1-a0)*(ia/na)
            bm.verts.new((math.cos(a)*rx, math.sin(a)*ry, z))
    bm.verts.ensure_lookup_table()
    for iz in range(nz):
        for ia in range(na):
            i0 = iz*(na+1)+ia
            try:
                bm.faces.new([bm.verts[i0], bm.verts[i0+1], bm.verts[i0+1+(na+1)], bm.verts[i0+(na+1)]])
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh); bm.free()
    sol = obj.modifiers.new("Sol", 'SOLIDIFY'); sol.thickness = 0.02; sol.offset = 1
    apply_mods(obj); assign(obj, M["jacket"]); smooth(obj, 1); apply_mods(obj)
    return obj
extras.append(make_jacket())

# Lining strips
for sx in (-1, 1):
    extras.append(capsule(f"Lining_{sx}", 0.022, 0.38, (sx*0.06, -0.14, 1.16), M["lining"], scale=(0.55, 0.45, 1), segs=12))

# Collar
bpy.ops.mesh.primitive_torus_add(major_radius=0.11, minor_radius=0.04, major_segments=28, minor_segments=12,
                                 location=(0, -0.02, 1.405))
col = bpy.context.active_object; col.name = "Collar"; xf(col); assign(col, M["jacket"]); smooth(col, 1); apply_mods(col)
extras.append(col)
bpy.ops.mesh.primitive_torus_add(major_radius=0.1, minor_radius=0.026, major_segments=24, minor_segments=10,
                                 location=(0, -0.04, 1.41))
coli = bpy.context.active_object; coli.name = "CollarIn"; xf(coli); assign(coli, M["lining"]); smooth(coli, 0)
extras.append(coli)

# Crest
bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.03, vertices=24, location=(0, 0.16, 1.22))
cr = bpy.context.active_object; cr.name = "Crest"; cr.rotation_euler=(math.pi/2,0,0); xf(cr); assign(cr, M["crest"]); smooth(cr,1); apply_mods(cr)
extras.append(cr)
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.035, vertices=16, location=(0, 0.17, 1.22))
cri = bpy.context.active_object; cri.name = "CrestIn"; cri.rotation_euler=(math.pi/2,0,0); xf(cri); assign(cri, M["piping"])
extras.append(cri)
for sx in (-1, 1):
    bpy.ops.mesh.primitive_cone_add(radius1=0.028, radius2=0.006, depth=0.15, vertices=12,
                                    location=(sx*0.13, 0.16, 1.24))
    w = bpy.context.active_object; w.name=f"Wing_{sx}"
    w.rotation_euler=(0, sx*math.pi/2, sx*0.45); xf(w); assign(w, M["wing"]); extras.append(w)

# JACKET SLEEVES — critical
for sx, tag in ((-1,"L"), (1,"R")):
    extras.append(capsule(f"SleeveU_{tag}", 0.058, 0.20, (sx*0.30, 0, 1.20), M["jacket"], scale=(1,1,1), segs=16))
    extras.append(capsule(f"SleeveF_{tag}", 0.05, 0.18, (sx*0.36, 0, 0.96), M["jacket"], segs=16))
    extras.append(capsule(f"Pipe_{tag}", 0.011, 0.32, (sx*0.27, -0.045, 1.12), M["piping"], segs=8, sub=0))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.052, minor_radius=0.02, major_segments=18, minor_segments=10,
                                     location=(sx*0.37, 0, 0.85))
    cuff = bpy.context.active_object; cuff.name=f"ArmCuff_{tag}"
    cuff.rotation_euler=(math.pi/2,0,0); xf(cuff); assign(cuff, M["lining"]); smooth(cuff,1); apply_mods(cuff)
    extras.append(cuff)
    extras.append(capsule(f"Glove_{tag}", 0.05, 0.07, (sx*0.38, 0.0, 0.76), M["glove"], scale=(0.9,1.2,1), segs=14))
    for fi, fox in enumerate((-0.02,0,0.02)):
        extras.append(capsule(f"Finger_{tag}_{fi}", 0.01, 0.04, (sx*0.38+fox, -0.035, 0.69), M["skin"], segs=8, sub=0))

# Belt / strap
bpy.ops.mesh.primitive_torus_add(major_radius=0.15, minor_radius=0.022, major_segments=28, minor_segments=12,
                                 location=(0,0,0.96))
belt = bpy.context.active_object; belt.name="Belt"; belt.rotation_euler=(math.pi/2,0,0); xf(belt); assign(belt, M["belt"]); smooth(belt,1); apply_mods(belt)
extras.append(belt)
extras.append(capsule("Buckle", 0.03, 0.02, (0,-0.155,0.96), M["buckle"], rot=(math.pi/2,0,0), segs=10, sub=0))
extras.append(capsule("Strap", 0.015, 0.32, (-0.12,-0.05,0.78), M["belt"], rot=(0.25,0,0.2), segs=10))
extras.append(capsule("StrapTip", 0.02, 0.025, (-0.14,-0.08,0.60), M["piping"], segs=10, sub=0))

# Pants + stripe + cuff + skates
for sx, tag in ((-1,"L"), (1,"R")):
    extras.append(capsule(f"PantThigh_{tag}", 0.09, 0.36, (sx*0.10, 0, 0.70), M["pants"], scale=(1,0.95,1), segs=18))
    extras.append(capsule(f"PantShin_{tag}", 0.07, 0.30, (sx*0.10, 0, 0.28), M["pants"], segs=16))
    extras.append(capsule(f"Stripe_{tag}", 0.014, 0.62, (sx*0.175, 0, 0.50), M["stripe"], segs=8, sub=0))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.072, minor_radius=0.024, major_segments=18, minor_segments=10,
                                     location=(sx*0.10, 0, 0.13))
    lc = bpy.context.active_object; lc.name=f"LegCuff_{tag}"
    lc.rotation_euler=(math.pi/2,0,0); xf(lc); assign(lc, M["lining"]); smooth(lc,1); apply_mods(lc)
    extras.append(lc)
    # Skate boot
    extras.append(capsule(f"Boot_{tag}", 0.06, 0.18, (sx*0.10, -0.04, 0.065), M["skate"],
                          rot=(math.pi/2,0,0), scale=(1.1,0.9,1.25), segs=16))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.055, location=(sx*0.10, -0.15, 0.05), segments=16, ring_count=10)
    toe = bpy.context.active_object; toe.name=f"Toe_{tag}"; toe.scale=(1.05,1.35,0.75); xf(toe); assign(toe, M["skate"]); smooth(toe,1); apply_mods(toe)
    extras.append(toe)
    extras.append(capsule(f"Frame_{tag}", 0.018, 0.26, (sx*0.10, -0.02, 0.01), M["buckle"], rot=(math.pi/2,0,0), segs=8, sub=0))
    for wi, wy in enumerate((-0.10, -0.01, 0.08, 0.16)):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.042, minor_radius=0.015, major_segments=16, minor_segments=8,
                                         location=(sx*0.10, wy, -0.01))
        wh = bpy.context.active_object; wh.name=f"Wheel_{tag}_{wi}"
        wh.rotation_euler=(0, math.pi/2, 0); xf(wh); assign(wh, M["wheel"]); extras.append(wh)
    extras.append(capsule(f"SkateBuckle_{tag}", 0.025, 0.055, (sx*0.10, 0.0, 0.12), M["buckle"], rot=(math.pi/2,0,0), segs=8, sub=0))

print("extras", len(extras))

# ===================== ARMATURE =====================
bpy.ops.object.armature_add(enter_editmode=True, location=(0,0,0))
arm_obj = bpy.context.active_object; arm_obj.name = "SkaterArmature"
eb = arm_obj.data.edit_bones
for b in list(eb): eb.remove(b)

def B(name, head, tail, parent=None):
    b = eb.new(name); b.head=Vector(head); b.tail=Vector(tail)
    if parent: b.parent = eb[parent]
    return b

B("root",(0,0,0),(0,0,0.08))
B("hips",(0,0,0.92),(0,0,1.02),"root")
B("spine",(0,0,1.02),(0,0,1.20),"hips")
B("chest",(0,0,1.20),(0,0,1.38),"chest" and "spine")  # fix below
# recreate chest properly
if "chest" in eb: pass
B("chest",(0,0,1.20),(0,0,1.38),"spine")
B("neck",(0,0,1.38),(0,0,1.48),"chest")
B("head",(0,0,1.48),(0,0,1.72),"neck")
for s,sx in (("L",-1),("R",1)):
    B(f"shoulder_{s}",(sx*0.14,0,1.34),(sx*0.22,0,1.34),"chest")
    B(f"upper_arm_{s}",(sx*0.22,0,1.34),(sx*0.34,0,1.06),f"shoulder_{s}")
    B(f"forearm_{s}",(sx*0.34,0,1.06),(sx*0.38,0,0.82),f"upper_arm_{s}")
    B(f"hand_{s}",(sx*0.38,0,0.82),(sx*0.39,0,0.70),f"forearm_{s}")
    B(f"thigh_{s}",(sx*0.10,0,0.94),(sx*0.10,0,0.48),"hips")
    B(f"shin_{s}",(sx*0.10,0,0.48),(sx*0.10,0,0.12),f"thigh_{s}")
    B(f"foot_{s}",(sx*0.10,0,0.12),(sx*0.10,-0.15,0.03),f"shin_{s}")
# remove accidental duplicate chest if any
names = [b.name for b in eb]
print("bones", names)
bpy.ops.object.mode_set(mode='OBJECT')

def bone_for(n):
    n=n.lower()
    if n.startswith(("ew_","ei_","ep_","eh_","br_","mouth","spike","hair")): return "head"
    if n.startswith(("sleeveu_l","pipe_l")): return "upper_arm_L"
    if n.startswith(("sleeveu_r","pipe_r")): return "upper_arm_R"
    if n.startswith("sleevef_l") or n.startswith("armcuff_l"): return "forearm_L"
    if n.startswith("sleevef_r") or n.startswith("armcuff_r"): return "forearm_R"
    if n.startswith(("glove_l","finger_l")): return "hand_L"
    if n.startswith(("glove_r","finger_r")): return "hand_R"
    if n.startswith(("pantthigh_l","stripe_l")): return "thigh_L"
    if n.startswith(("pantthigh_r","stripe_r")): return "thigh_R"
    if n.startswith(("pantshin_l","legcuff_l")): return "shin_L"
    if n.startswith(("pantshin_r","legcuff_r")): return "shin_R"
    if any(n.startswith(p) for p in ("boot_l","toe_l","frame_l","wheel_l","skatebuckle_l")): return "foot_L"
    if any(n.startswith(p) for p in ("boot_r","toe_r","frame_r","wheel_r","skatebuckle_r")): return "foot_R"
    if n in ("belt","buckle","strap","straptip"): return "hips"
    if n in ("jacket","tee","collar","collarin","crest","crestin") or n.startswith(("lining","wing")): return "chest"
    return "spine"

def skin(obj, bname):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.vertex_groups.clear()
    vg = obj.vertex_groups.new(name=bname)
    vg.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')
    for mod in list(obj.modifiers):
        if mod.type=='ARMATURE': obj.modifiers.remove(mod)
    mod = obj.modifiers.new("Armature", 'ARMATURE'); mod.object = arm_obj
    obj.parent = arm_obj
    obj.select_set(False)

# Auto-weight body
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True); arm_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
try:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except Exception as e:
    print("autoweight", e); skin(body, "spine")

for o in extras:
    skin(o, bone_for(o.name))

# ===================== ANIMS =====================
arm_obj.animation_data_create()

def kf(bn, fr, loc=None, rot=None):
    pb = arm_obj.pose.bones.get(bn)
    if not pb: return
    pb.rotation_mode='XYZ'
    if loc is not None:
        pb.location=loc; pb.keyframe_insert("location", frame=fr)
    if rot is not None:
        pb.rotation_euler=Euler(rot); pb.keyframe_insert("rotation_euler", frame=fr)

def reset(fr):
    for pb in arm_obj.pose.bones:
        pb.rotation_mode='XYZ'; pb.location=(0,0,0); pb.rotation_euler=(0,0,0)
        pb.keyframe_insert("location", frame=fr); pb.keyframe_insert("rotation_euler", frame=fr)

def make_action(name, fn):
    for pb in arm_obj.pose.bones:
        pb.location=(0,0,0); pb.rotation_euler=(0,0,0); pb.rotation_mode='XYZ'
    act = bpy.data.actions.new(name)
    arm_obj.animation_data.action = act
    fn()
    tr = arm_obj.animation_data.nla_tracks.new(); tr.name=name
    tr.strips.new(name, int(act.frame_range[0]), act)
    arm_obj.animation_data.action = None

def anim_idle():
    reset(1)
    for f,b,az in ((1,0,0.1),(30,0.012,0.14),(60,0,0.1)):
        kf("hips",f,loc=(0,0,b*0.35)); kf("spine",f,rot=(b,0,0)); kf("chest",f,rot=(b*0.5,0,0))
        kf("head",f,rot=(0,math.sin(f/60*math.pi*2)*0.06,0))
        kf("upper_arm_L",f,rot=(0.12,0,az)); kf("upper_arm_R",f,rot=(0.12,0,-az))

def anim_skate():
    for f,ph in ((1,0),(15,1),(30,0),(45,-1),(60,0)):
        sw=ph*0.6
        kf("thigh_L",f,rot=(sw,0,0)); kf("thigh_R",f,rot=(-sw,0,0))
        kf("shin_L",f,rot=(-abs(sw)*0.45,0,0)); kf("shin_R",f,rot=(-abs(sw)*0.45,0,0))
        kf("upper_arm_L",f,rot=(-sw*0.75,0,0.2)); kf("upper_arm_R",f,rot=(sw*0.75,0,-0.2))
        kf("spine",f,rot=(0.15,0,-sw*0.1)); kf("hips",f,loc=(0,0,abs(ph)*0.025))
        kf("head",f,rot=(-0.05,sw*0.08,0))

def anim_grind():
    for f in (1,30,60):
        bal=math.sin(f/60*math.pi*2)*0.04
        kf("hips",f,loc=(0,0,-0.1),rot=(0.4,0,bal)); kf("spine",f,rot=(0.3,0,0)); kf("head",f,rot=(-0.2,0,0))
        kf("thigh_L",f,rot=(-0.25,0.2,0.15)); kf("thigh_R",f,rot=(0.45,-0.1,-0.08))
        kf("shin_L",f,rot=(0.55,0,0)); kf("shin_R",f,rot=(0.25,0,0))
        kf("foot_L",f,rot=(0.35,0.5,0)); kf("upper_arm_L",f,rot=(-0.35,0,1.05)); kf("upper_arm_R",f,rot=(-0.35,0,-1.05))

def anim_air():
    for f in (1,30,60):
        kf("hips",f,loc=(0,0,0.02),rot=(-0.12,0,0)); kf("spine",f,rot=(-0.25,0,0))
        kf("thigh_L",f,rot=(1.0,0.1,0)); kf("thigh_R",f,rot=(0.75,-0.25,0))
        kf("shin_L",f,rot=(-1.3,0,0)); kf("shin_R",f,rot=(-1.05,0,0))
        kf("upper_arm_L",f,rot=(-0.9,0,0.35)); kf("forearm_L",f,rot=(-0.7,0,0))
        kf("upper_arm_R",f,rot=(0.25,0,-0.85)); kf("head",f,rot=(0.2,0,0))

make_action("idle", anim_idle)
make_action("skate", anim_skate)
make_action("grind", anim_grind)
make_action("air", anim_air)
for t in arm_obj.animation_data.nla_tracks:
    if t.name=="idle" and t.strips:
        arm_obj.animation_data.action = t.strips[0].action; break

scene = bpy.context.scene
scene.frame_start=1; scene.frame_end=60; scene.frame_set(1)

# Export
bpy.ops.object.select_all(action='DESELECT')
arm_obj.select_set(True); body.select_set(True)
for o in extras: o.select_set(True)
bpy.context.view_layer.objects.active = arm_obj
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.export_scene.gltf(filepath=GLB, export_format='GLB', use_selection=True,
    export_animations=True, export_nla_strips=True, export_skins=True, export_apply=False, export_yup=True)
print("GLB", GLB, os.path.getsize(GLB))
