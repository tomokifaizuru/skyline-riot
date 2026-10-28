#!/usr/bin/env python3
"""v0.4 skater: open jacket, sheet-accurate spikes, 2-wheel skate shoes, gloves, belt, idle."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix, Euler, Quaternion
from pathlib import Path

ASSETS = Path("/workspace/skyline-riot/assets/character")
TEX = ASSETS / "textures"
BASE_VRM = "/tmp/vroid_cc0/base_male/Base_Male.vrm"
OUT_BLEND = str(ASSETS / "skater.blend")
OUT_GLB = str(ASSETS / "skater.glb")

HAIR = (0.04, 0.07, 0.16, 1.0)
HAIR_HI = (0.18, 0.32, 0.55, 1.0)
BLACK = (0.03, 0.03, 0.04, 1.0)
ORANGE = (1.0, 0.36, 0.07, 1.0)
WHITE = (0.93, 0.93, 0.96, 1.0)
RED = (0.82, 0.1, 0.1, 1.0)
SILVER = (0.72, 0.74, 0.78, 1.0)
NAVY_STRIPE = (0.15, 0.25, 0.55, 1.0)

rng = random.Random(42)


def mat(name, color, rough=0.55, metallic=0.0, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if "Emission Strength" in bsdf.inputs and emit:
        bsdf.inputs["Emission Strength"].default_value = emit
        bsdf.inputs["Emission Color"].default_value = color
    # Prefer emission-ish anime look for cloth
    return m


def mat_emit_tex(name, img_path, fallback=(0.1,0.1,0.1,1)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    try:
        tex.image = bpy.data.images.load(img_path)
    except Exception:
        em.inputs["Color"].default_value = fallback
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
        return m
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


def swap_tex(mat_obj, path):
    if not mat_obj or not mat_obj.use_nodes:
        return
    img = bpy.data.images.load(path)
    for n in mat_obj.node_tree.nodes:
        if n.type == "TEX_IMAGE":
            n.image = img
            return


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def join_objs(objs, name):
    objs = [o for o in objs if o]
    if not objs:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def apply_scale(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def bone_world(arm, name, tip=False):
    pb = arm.pose.bones.get(name)
    if not pb:
        return None
    return arm.matrix_world @ (pb.tail if tip else pb.head)


def add_spike(origin, direction, length, radius, name, material):
    """Elongated cone spike along direction."""
    direction = Vector(direction).normalized()
    bpy.ops.mesh.primitive_cone_add(
        vertices=6,
        radius1=radius,
        radius2=0.002,
        depth=length,
        location=origin + direction * (length * 0.45),
    )
    o = bpy.context.active_object
    o.name = name
    # orient +Z of cone to direction (cone points +Z by default from base to tip... actually Blender cone points +Z with tip at +depth/2)
    quat = direction.to_track_quat("Z", "Y")
    o.rotation_euler = quat.to_euler()
    apply_scale(o)
    if o.data.materials:
        o.data.materials[0] = material
    else:
        o.data.materials.append(material)
    return o


def build_spiky_hair(arm, head_loc):
    """Match sheet: tall crown spikes, side spikes, bangs, nape tufts, navy+highlights."""
    mats = [
        mat("HairNavy", HAIR, 0.45),
        mat("HairHi", HAIR_HI, 0.4),
    ]
    spikes = []
    # Crown: many tall spikes radiating up/out/back
    crown = head_loc + Vector((0, 0.02, 0.06))
    specs = []
    # Tall top spikes (jagged crown) — up and slightly back
    for i in range(14):
        ang = -0.4 + i * 0.12 + rng.uniform(-0.05, 0.05)
        elev = 0.75 + rng.uniform(-0.15, 0.2)
        d = Vector((math.sin(ang) * 0.55, -math.cos(ang) * 0.35 - 0.15, elev)).normalized()
        specs.append((crown + Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.02, 0.04), rng.uniform(0, 0.03))),
                      d, rng.uniform(0.22, 0.38), rng.uniform(0.028, 0.048)))
    # Side spikes L/R
    for side in (-1, 1):
        for i in range(6):
            d = Vector((side * (0.7 + 0.2 * i / 6), -0.2 + rng.uniform(-0.2, 0.1), 0.35 + rng.uniform(-0.1, 0.25))).normalized()
            origin = crown + Vector((side * 0.06, 0.0, -0.02 + i * 0.01))
            specs.append((origin, d, rng.uniform(0.14, 0.26), rng.uniform(0.022, 0.04)))
    # Back radial spikes
    for i in range(10):
        ang = math.pi * 0.6 + i * 0.14
        d = Vector((math.sin(ang) * 0.4, -math.cos(ang) * 0.85, 0.35 + rng.uniform(0, 0.3))).normalized()
        specs.append((crown + Vector((0, -0.02, -0.01)), d, rng.uniform(0.12, 0.24), rng.uniform(0.02, 0.036)))
    # Bangs: pointed falling over forehead (forward + down)
    for i in range(9):
        x = -0.08 + i * 0.02
        d = Vector((x * 1.2 + rng.uniform(-0.05, 0.05), 0.75 + rng.uniform(-0.1, 0.1), -0.35 + rng.uniform(-0.15, 0.05))).normalized()
        origin = head_loc + Vector((x * 0.5, 0.07, 0.04))
        specs.append((origin, d, rng.uniform(0.10, 0.16), rng.uniform(0.016, 0.028)))
    # Nape tufts short
    for i in range(7):
        x = -0.06 + i * 0.02
        d = Vector((x * 0.5, -0.6, -0.55 + rng.uniform(-0.1, 0.1))).normalized()
        origin = head_loc + Vector((x, -0.06, -0.04))
        specs.append((origin, d, rng.uniform(0.06, 0.10), rng.uniform(0.012, 0.022)))

    for i, (origin, d, length, radius) in enumerate(specs):
        m = mats[0] if rng.random() > 0.22 else mats[1]
        spikes.append(add_spike(origin, d, length, radius, f"Spike_{i}", m))

    hair = join_objs(spikes, "HairSpikes")
    # Parent to head bone keeping world
    if hair and arm:
        mw = hair.matrix_world.copy()
        hair.parent = arm
        hair.parent_type = "BONE"
        hair.parent_bone = "J_Bip_C_Head"
        # Reset so bone-local keeps world: compute inverse
        # Simpler: object-parent to armature and use copy location via constraint — 
        # For export, armature-parent with keep transform:
        hair.parent_type = "OBJECT"
        hair.parent = arm
        hair.matrix_world = mw
        # Also add armature modifier? Spikes aren't weighted — parent to armature object is OK for idle;
        # for head turn we'd need bone parent. Use CHILD_OF constraint to head bone.
        c = hair.constraints.new("CHILD_OF")
        c.target = arm
        c.subtarget = "J_Bip_C_Head"
        # set inverse
        bpy.context.view_layer.update()
        c.inverse_matrix = (arm.matrix_world @ arm.pose.bones["J_Bip_C_Head"].matrix).inverted()
    return hair


def build_jacket(arm):
    """Open black zip jacket: torso panels, long sleeves, high collar, crest, orange lining."""
    parts = []
    m_out = mat("JacketOut", BLACK, 0.5)
    m_in = mat("JacketIn", ORANGE, 0.55)
    m_pipe = mat("JacketPipe", WHITE, 0.4)
    m_crest = mat("JacketCrest", RED, 0.4)

    # --- Torso open front: left & right panels (boxes shaped) ---
    for side, sx in (("L", -1), ("R", 1)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(sx * 0.11, 0.02, 1.28))
        p = bpy.context.active_object
        p.name = f"JacketPanel_{side}"
        p.scale = (0.14, 0.10, 0.28)
        apply_scale(p)
        # Open front: shift outward slightly, thin
        p.scale = (0.95, 0.85, 1.0)
        apply_scale(p)
        p.data.materials.append(m_out)
        parts.append(p)
        # Inner orange lining strip at front edge
        bpy.ops.mesh.primitive_cube_add(size=1, location=(sx * 0.035, 0.095, 1.28))
        inn = bpy.context.active_object
        inn.name = f"JacketLining_{side}"
        inn.scale = (0.025, 0.02, 0.26)
        apply_scale(inn)
        inn.data.materials.append(m_in)
        parts.append(inn)

    # Back panel
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, -0.08, 1.30))
    back = bpy.context.active_object
    back.name = "JacketBack"
    back.scale = (0.22, 0.06, 0.27)
    apply_scale(back)
    back.data.materials.append(m_out)
    parts.append(back)

    # Crest on back
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.055, depth=0.012, location=(0.0, -0.145, 1.40))
    crest = bpy.context.active_object
    crest.name = "Crest"
    crest.rotation_euler = (math.pi / 2, 0, 0)
    apply_scale(crest)
    crest.data.materials.append(m_crest)
    parts.append(crest)
    # White wing ring
    bpy.ops.mesh.primitive_torus_add(major_radius=0.065, minor_radius=0.008, location=(0.0, -0.145, 1.40))
    ring = bpy.context.active_object
    ring.name = "CrestRing"
    ring.rotation_euler = (math.pi / 2, 0, 0)
    apply_scale(ring)
    ring.data.materials.append(m_pipe)
    parts.append(ring)

    # High stand collar
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0.02, 1.52))
    collar = bpy.context.active_object
    collar.name = "Collar"
    collar.scale = (0.12, 0.08, 0.07)
    apply_scale(collar)
    collar.data.materials.append(m_out)
    parts.append(collar)
    # Orange inside collar
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0.06, 1.52))
    col_in = bpy.context.active_object
    col_in.name = "CollarIn"
    col_in.scale = (0.10, 0.03, 0.055)
    apply_scale(col_in)
    col_in.data.materials.append(m_in)
    parts.append(col_in)

    # White piping hem
    bpy.ops.mesh.primitive_torus_add(major_radius=0.20, minor_radius=0.006, location=(0.0, 0.0, 1.12))
    hem = bpy.context.active_object
    hem.name = "HemPipe"
    hem.scale = (1.0, 0.7, 1.0)
    apply_scale(hem)
    hem.data.materials.append(m_pipe)
    parts.append(hem)

    # Long sleeves along arm bones (tubes) — placed in REST pose then weighted
    sleeve_parts = []
    for side, b_up, b_low, b_hand in (
        ("L", "J_Bip_L_UpperArm", "J_Bip_L_LowerArm", "J_Bip_L_Hand"),
        ("R", "J_Bip_R_UpperArm", "J_Bip_R_LowerArm", "J_Bip_R_Hand"),
    ):
        a = bone_world(arm, b_up)
        b = bone_world(arm, b_low)
        c = bone_world(arm, b_hand)
        if not a or not b or not c:
            continue
        for seg_name, p0, p1, r in (
            (f"SleeveUpper_{side}", a, b, 0.055),
            (f"SleeveLower_{side}", b, c, 0.045),
        ):
            mid = (p0 + p1) / 2
            length = (p1 - p0).length
            direction = (p1 - p0).normalized()
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=r, depth=max(length * 0.95, 0.05), location=mid)
            s = bpy.context.active_object
            s.name = seg_name
            s.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
            apply_scale(s)
            s.data.materials.append(m_out)
            sleeve_parts.append(s)
            parts.append(s)
            # Orange cuff lining at lower end of lower sleeve
            if "Lower" in seg_name:
                bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=r * 1.05, depth=0.035, location=p1 - direction * 0.02)
                cf = bpy.context.active_object
                cf.name = f"CuffOrange_{side}"
                cf.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
                apply_scale(cf)
                cf.data.materials.append(m_in)
                parts.append(cf)
                sleeve_parts.append(cf)
            # White piping stripe along sleeve
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.008, depth=max(length * 0.9, 0.04), location=mid + Vector((0, 0.04, 0)))
            pipe = bpy.context.active_object
            pipe.name = f"SleevePipe_{side}_{seg_name}"
            pipe.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
            apply_scale(pipe)
            pipe.data.materials.append(m_pipe)
            parts.append(pipe)
            sleeve_parts.append(pipe)

    jacket = join_objs(parts, "Jacket")
    # Skin to armature: automatic weights from nearby bones
    if jacket:
        jacket.parent = arm
        mod = jacket.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        # Manual vertex groups for torso vs sleeves
        bpy.context.view_layer.objects.active = jacket
        bpy.ops.object.mode_set(mode="EDIT")
        bm = bmesh.from_edit_mesh(jacket.data)
        bm.verts.ensure_lookup_table()
        # Create groups
        bpy.ops.object.mode_set(mode="OBJECT")
        for bname in ("J_Bip_C_Spine", "J_Bip_C_Chest", "J_Bip_C_UpperChest",
                      "J_Bip_L_UpperArm", "J_Bip_L_LowerArm", "J_Bip_R_UpperArm", "J_Bip_R_LowerArm",
                      "J_Bip_L_Shoulder", "J_Bip_R_Shoulder", "J_Bip_C_Neck"):
            if bname not in jacket.vertex_groups:
                jacket.vertex_groups.new(name=bname)
        # Weight by proximity to bone heads
        bones = {b.name: b for b in arm.data.bones}
        for vi, v in enumerate(jacket.data.vertices):
            wco = jacket.matrix_world @ v.co
            best = []
            for bname, b in bones.items():
                if bname not in jacket.vertex_groups:
                    continue
                bh = arm.matrix_world @ b.head_local
                bt = arm.matrix_world @ b.tail_local
                # dist to segment
                ab = bt - bh
                t = max(0, min(1, (wco - bh).dot(ab) / (ab.length_squared + 1e-9)))
                closest = bh + ab * t
                d = (wco - closest).length
                best.append((d, bname))
            best.sort()
            # assign top 2
            total = 0
            assigns = []
            for d, bn in best[:2]:
                w = 1.0 / (d + 0.05)
                assigns.append((bn, w))
                total += w
            for bn, w in assigns:
                jacket.vertex_groups[bn].add([vi], w / total, "REPLACE")
    return jacket


def build_loose_tee(arm):
    """Loose untucked white tee hanging below jacket hem."""
    m = mat("Tee", WHITE, 0.6)
    parts = []
    # Torso shirt
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0.01, 1.22))
    tee = bpy.context.active_object
    tee.name = "TeeBody"
    tee.scale = (0.18, 0.10, 0.26)
    apply_scale(tee)
    tee.data.materials.append(m)
    parts.append(tee)
    # Hanging hem below jacket (~z 1.05-1.12)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.15, depth=0.12, location=(0.0, 0.01, 1.05))
    hem = bpy.context.active_object
    hem.name = "TeeHem"
    hem.scale = (1.05, 0.85, 1.0)
    apply_scale(hem)
    hem.data.materials.append(m)
    parts.append(hem)
    # Short sleeves peeking under jacket (optional)
    obj = join_objs(parts, "LooseTee")
    if obj:
        obj.parent = arm
        mod = obj.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        for bn in ("J_Bip_C_Spine", "J_Bip_C_Chest", "J_Bip_C_Hips"):
            obj.vertex_groups.new(name=bn)
        for vi, v in enumerate(obj.data.vertices):
            z = (obj.matrix_world @ v.co).z
            if z > 1.25:
                obj.vertex_groups["J_Bip_C_Chest"].add([vi], 1.0, "REPLACE")
            elif z > 1.1:
                obj.vertex_groups["J_Bip_C_Spine"].add([vi], 1.0, "REPLACE")
            else:
                obj.vertex_groups["J_Bip_C_Hips"].add([vi], 1.0, "REPLACE")
    return obj


def build_gloves(arm):
    m = mat("Glove", BLACK, 0.5)
    parts = []
    for side, hand, fingers in (
        ("L", "J_Bip_L_Hand", ["J_Bip_L_Index1", "J_Bip_L_Middle1", "J_Bip_L_Ring1", "J_Bip_L_Little1", "J_Bip_L_Thumb1"]),
        ("R", "J_Bip_R_Hand", ["J_Bip_R_Index1", "J_Bip_R_Middle1", "J_Bip_R_Ring1", "J_Bip_R_Little1", "J_Bip_R_Thumb1"]),
    ):
        h = bone_world(arm, hand)
        if not h:
            continue
        # Palm shell
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.038, location=h)
        g = bpy.context.active_object
        g.name = f"GlovePalm_{side}"
        g.scale = (1.1, 0.7, 1.25)
        apply_scale(g)
        g.data.materials.append(m)
        # Wrist strap
        bpy.ops.mesh.primitive_torus_add(major_radius=0.035, minor_radius=0.006, location=h + Vector((0, 0, 0.02)))
        strap = bpy.context.active_object
        strap.name = f"GloveStrap_{side}"
        apply_scale(strap)
        strap.data.materials.append(m)
        # Fingerless: short tubes toward first knuckle bones
        for fi, fb in enumerate(fingers):
            tip = bone_world(arm, fb)
            if not tip:
                # fallback offset
                tip = h + Vector(((-1 if side == "L" else 1) * 0.02, 0.03, -0.02 * fi))
            mid = h.lerp(tip, 0.45)
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.012, depth=0.028, location=mid)
            f = bpy.context.active_object
            f.name = f"GloveFinger_{side}_{fi}"
            d = (tip - h).normalized()
            f.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
            apply_scale(f)
            f.data.materials.append(m)
            parts.append(f)
        parts.extend([g, strap])
    gloves = join_objs(parts, "Gloves")
    if gloves:
        mw = gloves.matrix_world.copy()
        gloves.parent = arm
        gloves.matrix_world = mw
    return gloves


def build_belt(arm):
    m_w = mat("Belt", WHITE, 0.45)
    m_b = mat("BeltStripe", NAVY_STRIPE, 0.45)
    parts = []
    bpy.ops.mesh.primitive_torus_add(major_radius=0.13, minor_radius=0.012, location=(0.0, 0.01, 1.00))
    belt = bpy.context.active_object
    belt.name = "BeltRing"
    belt.scale = (1.05, 0.75, 1.0)
    apply_scale(belt)
    belt.data.materials.append(m_w)
    parts.append(belt)
    # Blue stripes on belt (thin toruses)
    for dz in (-0.008, 0.008):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.131, minor_radius=0.0035, location=(0.0, 0.01, 1.00 + dz))
        s = bpy.context.active_object
        s.scale = (1.05, 0.75, 1.0)
        apply_scale(s)
        s.data.materials.append(m_b)
        parts.append(s)
    # Dangling strap down left thigh
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.08, 0.06, 0.82))
    strap = bpy.context.active_object
    strap.name = "BeltDangle"
    strap.scale = (0.018, 0.01, 0.18)
    apply_scale(strap)
    strap.data.materials.append(m_w)
    parts.append(strap)
    # Buckle
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0.11, 1.00))
    buckle = bpy.context.active_object
    buckle.scale = (0.04, 0.015, 0.03)
    apply_scale(buckle)
    buckle.data.materials.append(mat("Buckle", SILVER, 0.3, 0.6))
    parts.append(buckle)
    obj = join_objs(parts, "Belt")
    if obj:
        obj.parent = arm
    return obj


def build_skate_shoes(arm):
    """2-wheel skate shoes: chunky black sneaker, toe + heel silver wheels."""
    m_boot = mat("SkateBoot", BLACK, 0.45)
    m_frame = mat("SkateFrame", (0.08, 0.08, 0.1, 1), 0.4, 0.2)
    m_wheel = mat("SkateWheel", SILVER, 0.35, 0.35)
    m_lace = mat("SkateLace", (0.25, 0.25, 0.28, 1), 0.5)
    parts = []
    for side, foot in (("L", "J_Bip_L_Foot"), ("R", "J_Bip_R_Foot")):
        f = bone_world(arm, foot)
        if not f:
            f = Vector(((-0.1 if side == "L" else 0.1), 0.0, 0.05))
        # Place shoe on ground under foot
        base = Vector((f.x, f.y + 0.02, 0.0))
        # Chunky sneaker boot
        bpy.ops.mesh.primitive_cube_add(size=1, location=(base.x, base.y + 0.02, 0.075))
        boot = bpy.context.active_object
        boot.name = f"ShoeBoot_{side}"
        boot.scale = (0.075, 0.145, 0.07)
        apply_scale(boot)
        boot.modifiers.new("Sub", "SUBSURF").levels = 1
        boot.data.materials.append(m_boot)
        parts.append(boot)
        # Toe cap rounder
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.055, location=(base.x, base.y + 0.10, 0.055))
        toe = bpy.context.active_object
        toe.name = f"ShoeToe_{side}"
        toe.scale = (1.0, 1.1, 0.75)
        apply_scale(toe)
        toe.data.materials.append(m_boot)
        parts.append(toe)
        # Short frame under sole
        bpy.ops.mesh.primitive_cube_add(size=1, location=(base.x, base.y + 0.02, 0.022))
        frame = bpy.context.active_object
        frame.name = f"ShoeFrame_{side}"
        frame.scale = (0.035, 0.12, 0.012)
        apply_scale(frame)
        frame.data.materials.append(m_frame)
        parts.append(frame)
        # TWO large wheels: toe + heel
        for wi, oy in enumerate((0.075, -0.04)):  # toe, heel
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=20, radius=0.042, depth=0.032,
                location=(base.x, base.y + 0.02 + oy, 0.042),
                rotation=(0, math.pi / 2, 0),
            )
            wh = bpy.context.active_object
            wh.name = f"ShoeWheel_{side}_{wi}"
            apply_scale(wh)
            wh.data.materials.append(m_wheel)
            parts.append(wh)
            # axle hub
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=10, radius=0.01, depth=0.038,
                location=(base.x, base.y + 0.02 + oy, 0.042),
                rotation=(0, math.pi / 2, 0),
            )
            hub = bpy.context.active_object
            hub.data.materials.append(m_frame)
            parts.append(hub)
        # Laces strip
        bpy.ops.mesh.primitive_cube_add(size=1, location=(base.x, base.y + 0.04, 0.12))
        lace = bpy.context.active_object
        lace.scale = (0.035, 0.06, 0.01)
        apply_scale(lace)
        lace.data.materials.append(m_lace)
        parts.append(lace)

    shoes = join_objs(parts, "SkateShoes")
    if shoes:
        mw = shoes.matrix_world.copy()
        shoes.parent = arm
        shoes.matrix_world = mw
    return shoes


def hide_original_shoes_and_tops(body):
    """Hide original VRoid tops/shoes/tie faces so jacket/tee/skates show cleanly."""
    if not body:
        return
    hide_idx = []
    for i, s in enumerate(body.material_slots):
        if not s.material:
            continue
        n = s.material.name
        if any(k in n for k in ("Tops", "Shoes", "Tie", "Accessory")):
            hide_idx.append(i)
    if not hide_idx:
        return
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(body.data)
    for f in list(bm.faces):
        if f.material_index in hide_idx:
            bm.faces.remove(f)
    bmesh.update_edit_mesh(body.data)
    bpy.ops.object.mode_set(mode="OBJECT")


def set_idle_pose(arm):
    """Relaxed standing: arms down, slight contrapposto — NOT T-pose."""
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")

    def rot(name, xyz_deg):
        b = arm.pose.bones.get(name)
        if not b:
            return
        b.rotation_mode = "XYZ"
        b.rotation_euler = Euler(tuple(math.radians(a) for a in xyz_deg))

    # Arms hang down at sides (VRoid T-pose arms along +X/-X; rotate around Z/Y)
    # Empirically for VRoid: UpperArm Z ±80~90 brings arms down
    rot("J_Bip_L_UpperArm", (10, 5, 75))
    rot("J_Bip_R_UpperArm", (10, -5, -75))
    rot("J_Bip_L_LowerArm", (0, -15, 5))
    rot("J_Bip_R_LowerArm", (0, 15, -5))
    rot("J_Bip_L_Hand", (0, 0, 10))
    rot("J_Bip_R_Hand", (0, 0, -10))
    # Contrapposto
    rot("J_Bip_C_Hips", (0, 0, 4))
    rot("J_Bip_L_UpperLeg", (6, 0, 3))
    rot("J_Bip_R_UpperLeg", (2, 0, -5))
    rot("J_Bip_L_LowerLeg", (-4, 0, 0))
    rot("J_Bip_R_LowerLeg", (-2, 0, 0))
    rot("J_Bip_C_Spine", (2, 0, -2))
    rot("J_Bip_C_Chest", (3, 0, 0))
    rot("J_Bip_C_Head", (-2, 0, -3))
    # Firm brow via slight brow bones if present — skip

    # Build idle action with subtle breathe
    if arm.animation_data:
        arm.animation_data_clear()
    arm.animation_data_create()
    action = bpy.data.actions.new("idle")
    arm.animation_data.action = action

    for b in arm.pose.bones:
        b.keyframe_insert(data_path="rotation_euler", frame=1)
        b.keyframe_insert(data_path="location", frame=1)

    chest = arm.pose.bones.get("J_Bip_C_UpperChest") or arm.pose.bones.get("J_Bip_C_Chest")
    if chest:
        chest.rotation_mode = "XYZ"
        base = tuple(chest.rotation_euler)
        chest.rotation_euler = Euler((base[0] + math.radians(2), base[1], base[2]))
        chest.keyframe_insert(data_path="rotation_euler", frame=1)
        chest.rotation_euler = Euler((base[0] - math.radians(1.5), base[1], base[2]))
        chest.keyframe_insert(data_path="rotation_euler", frame=60)
        chest.rotation_euler = Euler((base[0] + math.radians(2), base[1], base[2]))
        chest.keyframe_insert(data_path="rotation_euler", frame=120)

    # Weight shift subtle
    hips = arm.pose.bones.get("J_Bip_C_Hips")
    if hips:
        hips.rotation_mode = "XYZ"
        base = tuple(hips.rotation_euler)
        hips.rotation_euler = Euler((base[0], base[1], base[2] + math.radians(1.5)))
        hips.keyframe_insert(data_path="rotation_euler", frame=1)
        hips.rotation_euler = Euler((base[0], base[1], base[2] - math.radians(1.5)))
        hips.keyframe_insert(data_path="rotation_euler", frame=90)
        hips.rotation_euler = Euler((base[0], base[1], base[2] + math.radians(1.5)))
        hips.keyframe_insert(data_path="rotation_euler", frame=180)

    bpy.ops.object.mode_set(mode="OBJECT")
    track = arm.animation_data.nla_tracks.new()
    track.name = "idle"
    track.strips.new("idle", 1, action)
    # Also create stub skate/grind/air as copies for viewer buttons
    for name, frames in (("skate", 40), ("grind", 40), ("air", 40)):
        a2 = action.copy()
        a2.name = name
        t2 = arm.animation_data.nla_tracks.new()
        t2.name = name
        t2.strips.new(name, 1, a2)


def apply_face_upgrade():
    face_mat = bpy.data.materials.get("M00_000_00_Face_00_SKIN")
    brow_mat = bpy.data.materials.get("M00_000_00_FaceBrow_00_FACE")
    eyeline = bpy.data.materials.get("M00_000_00_FaceEyeline_00_FACE")
    if (TEX / "face_mature.png").exists():
        swap_tex(face_mat, str(TEX / "face_mature.png"))
    if (TEX / "face_brow_firm.png").exists():
        swap_tex(brow_mat, str(TEX / "face_brow_firm.png"))
    if (TEX / "face_eyeline_firm.png").exists():
        swap_tex(eyeline, str(TEX / "face_eyeline_firm.png"))
    # Tint hair material on body to navy
    hair_mat = bpy.data.materials.get("M00_000_HairBack_00_HAIR")
    if hair_mat and hair_mat.use_nodes:
        for n in hair_mat.node_tree.nodes:
            if n.type == "MIX":
                try:
                    n.inputs[7].default_value = HAIR
                except Exception:
                    pass


def recolor_bottoms():
    # Keep existing bottoms stripe tex if present
    bot = bpy.data.materials.get("M00_001_01_Bottoms_01_CLOTH")
    p = TEX / "bottoms_stripe.png"
    if bot and p.exists():
        swap_tex(bot, str(p))


def main():
    clear()
    bpy.ops.import_scene.gltf(filepath=BASE_VRM)
    for o in list(bpy.data.objects):
        if "Ico" in o.name:
            bpy.data.objects.remove(o, do_unlink=True)

    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    arm.name = "SkaterArmature"
    body = bpy.data.objects.get("Body")
    face = bpy.data.objects.get("Face")

    hide_original_shoes_and_tops(body)
    apply_face_upgrade()
    recolor_bottoms()

    # IMPORTANT: build gear in REST pose first so sleeve/glove alignment matches T-pose bones,
    # then apply idle pose (jacket skinned will follow).
    print("Building jacket…")
    build_jacket(arm)
    print("Building tee…")
    build_loose_tee(arm)
    print("Building gloves…")
    build_gloves(arm)
    print("Building belt…")
    build_belt(arm)
    print("Building 2-wheel skate shoes…")
    build_skate_shoes(arm)

    # Head location for hair (rest pose)
    head = bone_world(arm, "J_Bip_C_Head") or Vector((0, 0, 1.58))
    print("Building spiky hair…", head)
    build_spiky_hair(arm, head)

    print("Setting idle pose…")
    set_idle_pose(arm)
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    scene.frame_set(1)

    # Ground feet: shift so lowest mesh at z=0
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    print("BBOX", mn, mx)
    arm.location.z -= mn.z
    bpy.context.view_layer.update()

    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.data.objects:
        if o.type in ("MESH", "ARMATURE"):
            o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=OUT_GLB,
        export_format="GLB",
        use_selection=True,
        export_animations=True,
        export_skins=True,
        export_morph=True,
        export_apply=False,
    )
    print("Wrote", OUT_GLB, os.path.getsize(OUT_GLB))


if __name__ == "__main__":
    main()
