#!/usr/bin/env python3
"""v0.4b: fix tee coverage, jacket fit, sheet hair, 2-wheel shoes on posed feet, idle."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix, Euler
from pathlib import Path

ASSETS = Path("/workspace/skyline-riot/assets/character")
TEX = ASSETS / "textures"
BASE_VRM = "/tmp/vroid_cc0/base_male/Base_Male.vrm"
OUT_BLEND = str(ASSETS / "skater.blend")
OUT_GLB = str(ASSETS / "skater.glb")

HAIR = (0.035, 0.06, 0.14, 1)
HAIR_HI = (0.22, 0.38, 0.62, 1)
BLACK = (0.025, 0.025, 0.03, 1)
ORANGE = (1.0, 0.36, 0.07, 1)
WHITE = (0.94, 0.94, 0.97, 1)
RED = (0.85, 0.1, 0.1, 1)
SILVER = (0.75, 0.77, 0.82, 1)
NAVY = (0.12, 0.2, 0.45, 1)
rng = random.Random(7)


def mat(name, color, rough=0.5, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    return m


def swap_tex(m, path):
    if not m or not m.use_nodes: return
    img = bpy.data.images.load(str(path))
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE":
            n.image = img
            return


def apply_transforms(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def join(objs, name):
    objs = [o for o in objs if o]
    if not objs: return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def bone_head(arm, name):
    pb = arm.pose.bones.get(name)
    if not pb: return None
    return arm.matrix_world @ pb.head


def bone_tail(arm, name):
    pb = arm.pose.bones.get(name)
    if not pb: return None
    return arm.matrix_world @ pb.tail


def bone_matrix(arm, name):
    pb = arm.pose.bones.get(name)
    if not pb: return None
    return arm.matrix_world @ pb.matrix


def parent_to_bone(obj, arm, bone_name):
    """Parent object to bone keeping current world transform."""
    mw = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    # After bone parent, local matrix is relative to bone tip in Blender...
    # Use CHILD_OF instead for reliable keep-world
    obj.parent = arm
    obj.parent_type = "OBJECT"
    obj.matrix_world = mw
    # Remove old childofs
    for c in list(obj.constraints):
        if c.type == "CHILD_OF":
            obj.constraints.remove(c)
    c = obj.constraints.new("CHILD_OF")
    c.target = arm
    c.subtarget = bone_name
    bpy.context.view_layer.update()
    c.inverse_matrix = bone_matrix(arm, bone_name).inverted()


def set_idle_and_apply_rest(arm, body, face):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")

    def rot(name, deg):
        b = arm.pose.bones.get(name)
        if not b: return
        b.rotation_mode = "XYZ"
        b.rotation_euler = Euler(tuple(math.radians(a) for a in deg))

    rot("J_Bip_L_UpperArm", (8, 8, 78))
    rot("J_Bip_R_UpperArm", (8, -8, -78))
    rot("J_Bip_L_LowerArm", (5, -20, 8))
    rot("J_Bip_R_LowerArm", (5, 20, -8))
    rot("J_Bip_L_Hand", (0, 0, 5))
    rot("J_Bip_R_Hand", (0, 0, -5))
    rot("J_Bip_C_Hips", (0, 0, 5))
    rot("J_Bip_L_UpperLeg", (5, 0, 4))
    rot("J_Bip_R_UpperLeg", (3, 0, -6))
    rot("J_Bip_L_LowerLeg", (-6, 0, 0))
    rot("J_Bip_R_LowerLeg", (-3, 0, 0))
    rot("J_Bip_C_Spine", (3, 0, -2))
    rot("J_Bip_C_Chest", (4, 0, 0))
    rot("J_Bip_C_Head", (-3, 0, -4))
    bpy.context.view_layer.update()

    # Apply armature deformation to body/face meshes, then apply pose as rest
    bpy.ops.object.mode_set(mode="OBJECT")
    for mesh_obj in (body, face):
        if not mesh_obj: continue
        bpy.ops.object.select_all(action="DESELECT")
        mesh_obj.select_set(True)
        bpy.context.view_layer.objects.active = mesh_obj
        # Ensure armature modifier exists
        amod = None
        for m in mesh_obj.modifiers:
            if m.type == "ARMATURE":
                amod = m
                break
        if amod:
            # Clear shape keys so modifier can apply
            if mesh_obj.data.shape_keys:
                mesh_obj.shape_key_clear()
            bpy.ops.object.modifier_apply(modifier=amod.name)
            mesh_obj["_needs_arm"] = True

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    # Rebind armature modifiers
    for mesh_obj in (body, face):
        if not mesh_obj: continue
        mod = mesh_obj.modifiers.new("Armature", "ARMATURE")
        mod.object = arm


def hide_mats(body, keys):
    if not body: return
    idxs = [i for i,s in enumerate(body.material_slots) if s.material and any(k in s.material.name for k in keys)]
    if not idxs: return
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(body.data)
    for f in list(bm.faces):
        if f.material_index in idxs:
            bm.faces.remove(f)
    bmesh.update_edit_mesh(body.data)
    bpy.ops.object.mode_set(mode="OBJECT")


def build_tee(arm):
    """Closed white crew tee covering torso, hem hanging below jacket."""
    m = mat("TeeMat", WHITE, 0.65)
    parts = []
    # Main torso — solid, not open
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.145, depth=0.42, location=(0, 0.02, 1.28))
    t = bpy.context.active_object
    t.name = "TeeTorso"
    t.scale = (1.0, 0.78, 1.0)
    apply_transforms(t)
    t.data.materials.append(m)
    parts.append(t)
    # Soft shoulders
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(sx * 0.14, 0.02, 1.42))
        s = bpy.context.active_object
        s.scale = (1.1, 0.9, 0.7)
        apply_transforms(s)
        s.data.materials.append(m)
        parts.append(s)
    # Short sleeves
    for sx, bn in ((-1, "J_Bip_L_UpperArm"), (1, "J_Bip_R_UpperArm")):
        a = bone_head(arm, bn)
        if not a: continue
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.055, depth=0.12, location=a + Vector((sx*0.05, 0, -0.02)))
        sl = bpy.context.active_object
        d = Vector((sx, 0.1, -0.2)).normalized()
        sl.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        apply_transforms(sl)
        sl.data.materials.append(m)
        parts.append(sl)
    # Hanging hem (untucked)
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.155, depth=0.14, location=(0, 0.02, 1.02))
    h = bpy.context.active_object
    h.scale = (1.05, 0.82, 1.0)
    apply_transforms(h)
    h.data.materials.append(m)
    parts.append(h)
    # Crew neck ring
    bpy.ops.mesh.primitive_torus_add(major_radius=0.055, minor_radius=0.012, location=(0, 0.03, 1.48))
    n = bpy.context.active_object
    apply_transforms(n)
    n.data.materials.append(m)
    parts.append(n)
    obj = join(parts, "LooseTee")
    if obj:
        obj.parent = arm
        mod = obj.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        # Simple weights
        for bn in ("J_Bip_C_Hips", "J_Bip_C_Spine", "J_Bip_C_Chest", "J_Bip_C_UpperChest"):
            obj.vertex_groups.new(name=bn)
        for i, v in enumerate(obj.data.vertices):
            z = (obj.matrix_world @ v.co).z
            if z > 1.40: obj.vertex_groups["J_Bip_C_UpperChest"].add([i], 1, "REPLACE")
            elif z > 1.25: obj.vertex_groups["J_Bip_C_Chest"].add([i], 1, "REPLACE")
            elif z > 1.10: obj.vertex_groups["J_Bip_C_Spine"].add([i], 1, "REPLACE")
            else: obj.vertex_groups["J_Bip_C_Hips"].add([i], 1, "REPLACE")
    return obj


def build_jacket(arm):
    m_out = mat("JOut", BLACK, 0.48)
    m_in = mat("JIn", ORANGE, 0.55)
    m_pipe = mat("JPipe", WHITE, 0.4)
    m_crest = mat("JCrest", RED, 0.4)
    parts = []

    # Fitted torso shell via icosphere/cylinder hybrid — open front gap
    # Left & right fronts
    for side, sx in (("L", -1), ("R", 1)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.16, depth=0.38, location=(sx * 0.04, 0.03, 1.30))
        p = bpy.context.active_object
        p.name = f"JPanel_{side}"
        p.scale = (0.55, 0.72, 1.0)
        # Rotate slightly open
        p.rotation_euler.z = math.radians(sx * -8)
        apply_transforms(p)
        # Delete inner-front faces approx by boolean — simpler: scale X smaller toward center
        p.data.materials.append(m_out)
        parts.append(p)
        # Orange lining visible at open front
        bpy.ops.mesh.primitive_cube_add(size=1, location=(sx * 0.02, 0.12, 1.30))
        lin = bpy.context.active_object
        lin.scale = (0.02, 0.03, 0.34)
        apply_transforms(lin)
        lin.data.materials.append(m_in)
        parts.append(lin)

    # Back
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.17, depth=0.38, location=(0, -0.04, 1.30))
    back = bpy.context.active_object
    back.scale = (1.0, 0.55, 1.0)
    apply_transforms(back)
    back.data.materials.append(m_out)
    parts.append(back)

    # Crest
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.058, depth=0.015, location=(0, -0.14, 1.42))
    crest = bpy.context.active_object
    crest.rotation_euler = (math.pi/2, 0, 0)
    apply_transforms(crest)
    crest.data.materials.append(m_crest)
    parts.append(crest)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.068, minor_radius=0.007, location=(0, -0.14, 1.42))
    ring = bpy.context.active_object
    ring.rotation_euler = (math.pi/2, 0, 0)
    apply_transforms(ring)
    ring.data.materials.append(m_pipe)
    parts.append(ring)

    # High stand collar
    bpy.ops.mesh.primitive_torus_add(major_radius=0.075, minor_radius=0.028, location=(0, 0.02, 1.52))
    collar = bpy.context.active_object
    collar.scale = (1.0, 0.85, 1.3)
    apply_transforms(collar)
    collar.data.materials.append(m_out)
    parts.append(collar)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.068, minor_radius=0.018, location=(0, 0.045, 1.52))
    cin = bpy.context.active_object
    cin.scale = (1.0, 0.8, 1.1)
    apply_transforms(cin)
    cin.data.materials.append(m_in)
    parts.append(cin)

    # White hem piping
    bpy.ops.mesh.primitive_torus_add(major_radius=0.175, minor_radius=0.006, location=(0, 0.01, 1.12))
    hem = bpy.context.active_object
    hem.scale = (1.0, 0.72, 1.0)
    apply_transforms(hem)
    hem.data.materials.append(m_pipe)
    parts.append(hem)

    # Sleeves along POSED arm bones
    for side, up, low, hand in (
        ("L", "J_Bip_L_UpperArm", "J_Bip_L_LowerArm", "J_Bip_L_Hand"),
        ("R", "J_Bip_R_UpperArm", "J_Bip_R_LowerArm", "J_Bip_R_Hand"),
    ):
        a, b, c = bone_head(arm, up), bone_head(arm, low), bone_head(arm, hand)
        if not a or not b or not c: continue
        for name, p0, p1, r in ((f"SU_{side}", a, b, 0.058), (f"SL_{side}", b, c, 0.048)):
            mid = (p0 + p1) * 0.5
            length = (p1 - p0).length * 0.92
            d = (p1 - p0).normalized()
            bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=r, depth=max(length, 0.04), location=mid)
            s = bpy.context.active_object
            s.name = name
            s.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
            apply_transforms(s)
            s.data.materials.append(m_out)
            parts.append(s)
            # white piping
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.007, depth=max(length*0.85, 0.03),
                                                location=mid + Vector((0, 0.035, 0)))
            pipe = bpy.context.active_object
            pipe.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
            apply_transforms(pipe)
            pipe.data.materials.append(m_pipe)
            parts.append(pipe)
        # orange cuff at wrist
        bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=0.052, depth=0.04, location=c - (c-b).normalized()*0.02)
        cf = bpy.context.active_object
        cf.rotation_euler = (c-b).normalized().to_track_quat("Z", "Y").to_euler()
        apply_transforms(cf)
        cf.data.materials.append(m_in)
        parts.append(cf)

    jacket = join(parts, "Jacket")
    if jacket:
        jacket.parent = arm
        mod = jacket.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        # Weight by nearest bone
        bone_names = ["J_Bip_C_Spine","J_Bip_C_Chest","J_Bip_C_UpperChest","J_Bip_C_Neck",
                      "J_Bip_L_Shoulder","J_Bip_R_Shoulder",
                      "J_Bip_L_UpperArm","J_Bip_L_LowerArm","J_Bip_R_UpperArm","J_Bip_R_LowerArm"]
        for bn in bone_names:
            if bn not in jacket.vertex_groups:
                jacket.vertex_groups.new(name=bn)
        bones = {b.name: b for b in arm.data.bones if b.name in jacket.vertex_groups}
        for vi, v in enumerate(jacket.data.vertices):
            wco = jacket.matrix_world @ v.co
            scored = []
            for bn, b in bones.items():
                bh = arm.matrix_world @ b.head_local
                bt = arm.matrix_world @ b.tail_local
                ab = bt - bh
                t = max(0, min(1, (wco - bh).dot(ab) / (ab.length_squared + 1e-9)))
                d = (wco - (bh + ab * t)).length
                scored.append((d, bn))
            scored.sort()
            total = sum(1.0/(d+0.04) for d,_ in scored[:2])
            for d, bn in scored[:2]:
                jacket.vertex_groups[bn].add([vi], (1.0/(d+0.04))/total, "REPLACE")
    return jacket


def build_hair(arm):
    """Sheet-accurate: tall crown spikes, side spikes, bangs over forehead (not eyes), nape tufts."""
    m1 = mat("HairNavy", HAIR, 0.42)
    m2 = mat("HairHi", HAIR_HI, 0.38)
    head = bone_head(arm, "J_Bip_C_Head") or Vector((0, 0, 1.58))
    # Cap base (hides scalp / original hairback)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.11, location=head + Vector((0, 0.01, 0.02)))
    cap = bpy.context.active_object
    cap.scale = (1.05, 1.1, 0.95)
    apply_transforms(cap)
    cap.data.materials.append(m1)
    spikes = [cap]
    crown = head + Vector((0, 0.0, 0.05))

    def spike(origin, direction, length, r1, name, material):
        d = Vector(direction).normalized()
        bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=r1, radius2=0.0015, depth=length,
                                        location=origin + d * (length * 0.42))
        o = bpy.context.active_object
        o.name = name
        o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        apply_transforms(o)
        o.data.materials.append(material)
        return o

    # Tall jagged crown — up and back (character faces +Y)
    for i in range(16):
        ang = -0.55 + i * 0.09
        elev = 0.85 + rng.uniform(-0.12, 0.18)
        d = Vector((math.sin(ang)*0.5, -0.25 - abs(math.cos(ang))*0.2, elev))
        spikes.append(spike(crown + Vector((rng.uniform(-0.025,0.025), rng.uniform(-0.01,0.03), 0)),
                            d, rng.uniform(0.26, 0.42), rng.uniform(0.03, 0.05),
                            f"C{i}", m1 if rng.random()>0.25 else m2))
    # Side wings
    for side in (-1, 1):
        for i in range(7):
            d = Vector((side*(0.85+0.1*i/7), -0.15+rng.uniform(-0.15,0.1), 0.25+rng.uniform(0,0.35)))
            spikes.append(spike(crown+Vector((side*0.07,0,-0.01)), d,
                                rng.uniform(0.16,0.28), rng.uniform(0.022,0.04),
                                f"S{side}_{i}", m1 if rng.random()>0.3 else m2))
    # Back radial
    for i in range(12):
        ang = 0.3 + i * 0.2
        d = Vector((math.sin(ang)*0.45, -0.9, 0.25+rng.uniform(0,0.4)))
        spikes.append(spike(crown+Vector((0,-0.03,0)), d,
                            rng.uniform(0.14,0.26), rng.uniform(0.02,0.038),
                            f"B{i}", m1))
    # Bangs — pointed, over forehead, STOP above eyes (forward +Y, slightly down, short)
    for i in range(8):
        x = -0.07 + i * 0.02
        d = Vector((x*0.8, 0.9, -0.15 + rng.uniform(-0.08, 0.05)))
        origin = head + Vector((x*0.4, 0.08, 0.03))
        spikes.append(spike(origin, d, rng.uniform(0.08, 0.13), rng.uniform(0.014, 0.024),
                            f"Bang{i}", m1 if i % 2 == 0 else m2))
    # Nape tufts — short, down-back
    for i in range(8):
        x = -0.07 + i * 0.02
        d = Vector((x*0.4, -0.55, -0.7))
        spikes.append(spike(head+Vector((x,-0.07,-0.05)), d,
                            rng.uniform(0.05,0.09), rng.uniform(0.01,0.02),
                            f"Nape{i}", m1))

    hair = join(spikes, "HairSpikes")
    if hair:
        parent_to_bone(hair, arm, "J_Bip_C_Head")
    return hair


def build_gloves(arm):
    m = mat("GloveMat", BLACK, 0.5)
    parts_by_hand = {"L": [], "R": []}
    for side, hand in (("L", "J_Bip_L_Hand"), ("R", "J_Bip_R_Hand")):
        h = bone_head(arm, hand)
        if not h: continue
        bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=10, radius=0.04, location=h)
        g = bpy.context.active_object
        g.scale = (1.15, 0.75, 1.3)
        apply_transforms(g)
        g.data.materials.append(m)
        parts_by_hand[side].append(g)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.036, minor_radius=0.007, location=h)
        st = bpy.context.active_object
        apply_transforms(st)
        st.data.materials.append(m)
        parts_by_hand[side].append(st)
        # Short finger stubs (fingerless)
        for fi, off in enumerate([(-0.015,0.03,-0.01),(0,0.035,-0.005),(0.015,0.03,-0.01),(0.028,0.02,-0.015),(-0.028,0.015,0.0)]):
            ox, oy, oz = off
            if side == "R": ox = -ox
            loc = h + Vector((ox, oy, oz))
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.011, depth=0.025, location=loc)
            f = bpy.context.active_object
            f.rotation_euler = Vector((ox, oy+0.05, oz)).normalized().to_track_quat("Z","Y").to_euler()
            apply_transforms(f)
            f.data.materials.append(m)
            parts_by_hand[side].append(f)
    objs = []
    for side, plist in parts_by_hand.items():
        if not plist: continue
        o = join(plist, f"Glove_{side}")
        bone = "J_Bip_L_Hand" if side == "L" else "J_Bip_R_Hand"
        parent_to_bone(o, arm, bone)
        objs.append(o)
    return objs


def build_belt(arm):
    mw = mat("BeltW", WHITE, 0.45)
    mb = mat("BeltB", NAVY, 0.45)
    ms = mat("Buckle", SILVER, 0.3, 0.55)
    parts = []
    bpy.ops.mesh.primitive_torus_add(major_radius=0.125, minor_radius=0.014, location=(0, 0.02, 1.01))
    b = bpy.context.active_object
    b.scale = (1.05, 0.78, 1.0)
    apply_transforms(b)
    b.data.materials.append(mw)
    parts.append(b)
    for dz in (-0.009, 0.009):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.126, minor_radius=0.004, location=(0, 0.02, 1.01+dz))
        s = bpy.context.active_object
        s.scale = (1.05, 0.78, 1.0)
        apply_transforms(s)
        s.data.materials.append(mb)
        parts.append(s)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.07, 0.08, 0.85))
    dangle = bpy.context.active_object
    dangle.scale = (0.016, 0.008, 0.16)
    apply_transforms(dangle)
    dangle.data.materials.append(mw)
    parts.append(dangle)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.12, 1.01))
    buckle = bpy.context.active_object
    buckle.scale = (0.035, 0.012, 0.028)
    apply_transforms(buckle)
    buckle.data.materials.append(ms)
    parts.append(buckle)
    obj = join(parts, "Belt")
    if obj:
        obj.parent = arm
    return obj


def build_skate_shoes(arm):
    """Chunky black sneaker + short frame + toe wheel + heel wheel (silver)."""
    m_boot = mat("Boot", BLACK, 0.45)
    m_frame = mat("Frame", (0.07,0.07,0.09,1), 0.4, 0.25)
    m_wheel = mat("Wheel", SILVER, 0.32, 0.4)
    m_lace = mat("Lace", (0.3,0.3,0.33,1), 0.5)
    for side, foot in (("L", "J_Bip_L_Foot"), ("R", "J_Bip_R_Foot")):
        fh = bone_head(arm, foot)
        ft = bone_tail(arm, foot)
        if not fh: continue
        # Foot points roughly along bone (tail - head); shoes sit under foot on ground
        forward = (ft - fh) if ft else Vector((0, 1, 0))
        forward.z = 0
        if forward.length < 1e-4:
            forward = Vector((0, 1, 0))
        forward.normalize()
        # Character faces +Y; feet may point slightly out
        base = Vector((fh.x, fh.y, 0.0))
        # Orient shoe along forward
        parts = []
        # Boot body
        bpy.ops.mesh.primitive_cube_add(size=1, location=base + forward*0.02 + Vector((0,0,0.07)))
        boot = bpy.context.active_object
        boot.scale = (0.07, 0.13, 0.065)
        # rotate to face forward
        boot.rotation_euler = forward.to_track_quat("Y", "Z").to_euler()
        apply_transforms(boot)
        boot.modifiers.new("Sub", "SUBSURF").levels = 1
        boot.data.materials.append(m_boot)
        parts.append(boot)
        # Rounded toe
        toe_loc = base + forward * 0.10 + Vector((0,0,0.05))
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=toe_loc)
        toe = bpy.context.active_object
        toe.scale = (1.05, 1.15, 0.7)
        apply_transforms(toe)
        toe.data.materials.append(m_boot)
        parts.append(toe)
        # Short frame under sole
        bpy.ops.mesh.primitive_cube_add(size=1, location=base + forward*0.02 + Vector((0,0,0.018)))
        frame = bpy.context.active_object
        frame.scale = (0.032, 0.11, 0.012)
        frame.rotation_euler = forward.to_track_quat("Y", "Z").to_euler()
        apply_transforms(frame)
        frame.data.materials.append(m_frame)
        parts.append(frame)
        # TWO wheels: toe + heel — cylinders axis along X (sideways)
        right = forward.cross(Vector((0,0,1))).normalized()
        for name, along in (("Toe", 0.08), ("Heel", -0.045)):
            wloc = base + forward * along + Vector((0,0,0.04))
            bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.04, depth=0.03, location=wloc)
            w = bpy.context.active_object
            # Axis along right (sideways)
            w.rotation_euler = right.to_track_quat("Z", "Y").to_euler()
            apply_transforms(w)
            w.data.materials.append(m_wheel)
            parts.append(w)
            # hub
            bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.012, depth=0.036, location=wloc)
            hub = bpy.context.active_object
            hub.rotation_euler = right.to_track_quat("Z", "Y").to_euler()
            apply_transforms(hub)
            hub.data.materials.append(m_frame)
            parts.append(hub)
        # Lace
        bpy.ops.mesh.primitive_cube_add(size=1, location=base + forward*0.04 + Vector((0,0,0.115)))
        lace = bpy.context.active_object
        lace.scale = (0.03, 0.05, 0.01)
        lace.rotation_euler = forward.to_track_quat("Y", "Z").to_euler()
        apply_transforms(lace)
        lace.data.materials.append(m_lace)
        parts.append(lace)

        shoe = join(parts, f"SkateShoe_{side}")
        parent_to_bone(shoe, arm, foot)
    return True


def make_idle_action(arm):
    if arm.animation_data:
        arm.animation_data_clear()
    arm.animation_data_create()
    action = bpy.data.actions.new("idle")
    arm.animation_data.action = action
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
        b.keyframe_insert(data_path="rotation_euler", frame=1)
        b.keyframe_insert(data_path="location", frame=1)
    chest = arm.pose.bones.get("J_Bip_C_UpperChest") or arm.pose.bones.get("J_Bip_C_Chest")
    if chest:
        base = list(chest.rotation_euler)
        chest.rotation_euler = Euler((base[0]+math.radians(2), base[1], base[2]))
        chest.keyframe_insert(data_path="rotation_euler", frame=1)
        chest.rotation_euler = Euler((base[0]-math.radians(1.5), base[1], base[2]))
        chest.keyframe_insert(data_path="rotation_euler", frame=60)
        chest.rotation_euler = Euler((base[0]+math.radians(2), base[1], base[2]))
        chest.keyframe_insert(data_path="rotation_euler", frame=120)
    hips = arm.pose.bones.get("J_Bip_C_Hips")
    if hips:
        base = list(hips.rotation_euler)
        hips.rotation_euler = Euler((base[0], base[1], base[2]+math.radians(1.2)))
        hips.keyframe_insert(data_path="rotation_euler", frame=1)
        hips.rotation_euler = Euler((base[0], base[1], base[2]-math.radians(1.2)))
        hips.keyframe_insert(data_path="rotation_euler", frame=90)
        hips.rotation_euler = Euler((base[0], base[1], base[2]+math.radians(1.2)))
        hips.keyframe_insert(data_path="rotation_euler", frame=180)
    bpy.ops.object.mode_set(mode="OBJECT")
    tr = arm.animation_data.nla_tracks.new(); tr.name = "idle"; tr.strips.new("idle", 1, action)
    for nm in ("skate", "grind", "air"):
        a2 = action.copy(); a2.name = nm
        t2 = arm.animation_data.nla_tracks.new(); t2.name = nm; t2.strips.new(nm, 1, a2)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=BASE_VRM)
    for o in list(bpy.data.objects):
        if "Ico" in o.name:
            bpy.data.objects.remove(o, do_unlink=True)

    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    arm.name = "SkaterArmature"
    body = bpy.data.objects.get("Body")
    face = bpy.data.objects.get("Face")

    # Face upgrade
    if (TEX/"face_mature.png").exists():
        swap_tex(bpy.data.materials.get("M00_000_00_Face_00_SKIN"), TEX/"face_mature.png")
    if (TEX/"face_brow_firm.png").exists():
        swap_tex(bpy.data.materials.get("M00_000_00_FaceBrow_00_FACE"), TEX/"face_brow_firm.png")
    if (TEX/"face_eyeline_firm.png").exists():
        swap_tex(bpy.data.materials.get("M00_000_00_FaceEyeline_00_FACE"), TEX/"face_eyeline_firm.png")
    hair_mat = bpy.data.materials.get("M00_000_HairBack_00_HAIR")
    if hair_mat and hair_mat.use_nodes:
        for n in hair_mat.node_tree.nodes:
            if n.type == "MIX":
                try: n.inputs[7].default_value = HAIR
                except: pass
    if (TEX/"bottoms_stripe.png").exists():
        swap_tex(bpy.data.materials.get("M00_001_01_Bottoms_01_CLOTH"), TEX/"bottoms_stripe.png")

    # Remove original tops/shoes/tie (replaced)
    hide_mats(body, ("Tops", "Shoes", "Tie", "Accessory"))
    # Also hide original short hairback volume a bit — keep for scalp fill under spikes
    # (leave HairBack)

    print("Apply idle as rest…")
    set_idle_and_apply_rest(arm, body, face)
    bpy.context.view_layer.update()

    print("Tee…"); build_tee(arm)
    print("Jacket…"); build_jacket(arm)
    print("Hair…"); build_hair(arm)
    print("Gloves…"); build_gloves(arm)
    print("Belt…"); build_belt(arm)
    print("Skate shoes…"); build_skate_shoes(arm)
    print("Idle action…"); make_idle_action(arm)

    # Floor align
    mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
    for o in bpy.data.objects:
        if o.type != "MESH": continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mn[i]=min(mn[i],w[i]); mx[i]=max(mx[i],w[i])
    print("BBOX", mn, mx)
    arm.location.z -= mn.z
    bpy.context.view_layer.update()

    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.data.objects:
        if o.type in ("MESH","ARMATURE"):
            o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True,
                              export_animations=True, export_skins=True, export_morph=True)
    print("Wrote", OUT_GLB, os.path.getsize(OUT_GLB))


if __name__ == "__main__":
    main()
