#!/usr/bin/env python3
"""Genshin-tier anime skater from VRoid CC0 Base_Male + concept-sheet textures/skates."""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix, Euler
from pathlib import Path

ROOT = Path("/workspace/skyline-riot")
ASSETS = ROOT / "assets" / "character"
TEX_DIR = ASSETS / "textures"
BASE_VRM = "/tmp/vroid_cc0/base_male/Base_Male.vrm"
OUT_BLEND = str(ASSETS / "skater.blend")
OUT_GLB = str(ASSETS / "skater.glb")

HAIR_NAVY = (0.05, 0.08, 0.20, 1.0)
BLACK = (0.04, 0.04, 0.05, 1.0)
ORANGE = (1.0, 0.38, 0.08, 1.0)
WHITE = (0.92, 0.92, 0.95, 1.0)


def make_mat(name, color, rough=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if not bsdf:
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def swap_image(mat, path):
    if not mat or not mat.use_nodes:
        return
    img = bpy.data.images.load(path)
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE":
            n.image = img
            return


def bone_world_head(arm, bone_name):
    pb = arm.pose.bones.get(bone_name)
    if not pb:
        return None
    # pose bone head in armature space → world
    return arm.matrix_world @ pb.head


def bone_world_matrix(arm, bone_name):
    pb = arm.pose.bones.get(bone_name)
    if not pb:
        return None
    return arm.matrix_world @ pb.matrix


def add_skate_at(loc, side, collection_objs):
    """Place skate in WORLD space at foot location (no bone parent)."""
    parts = []
    # Boot
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc.x, loc.y + 0.03, loc.z + 0.055))
    boot = bpy.context.active_object
    boot.name = f"SkateBoot_{side}"
    boot.scale = (0.065, 0.125, 0.065)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    boot.modifiers.new("Sub", "SUBSURF").levels = 1
    boot.data.materials.append(make_mat(f"Boot_{side}", BLACK, 0.45))
    parts.append(boot)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc.x, loc.y + 0.03, loc.z + 0.015))
    frame = bpy.context.active_object
    frame.name = f"SkateFrame_{side}"
    frame.scale = (0.022, 0.15, 0.016)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    frame.data.materials.append(make_mat(f"Frame_{side}", (0.18, 0.18, 0.2, 1), 0.35, 0.35))
    parts.append(frame)

    wmat = make_mat(f"Wheel_{side}", (0.8, 0.8, 0.82, 1), 0.4)
    for i, oy in enumerate((-0.05, -0.017, 0.016, 0.049)):
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=16, radius=0.026, depth=0.02,
            location=(loc.x, loc.y + 0.03 + oy, loc.z + 0.026),
            rotation=(0, math.pi / 2, 0),
        )
        w = bpy.context.active_object
        w.name = f"Wheel_{side}_{i}"
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        w.data.materials.append(wmat)
        parts.append(w)

    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.042, minor_radius=0.009,
        location=(loc.x, loc.y + 0.03, loc.z + 0.11),
    )
    cuff = bpy.context.active_object
    cuff.name = f"SkateCuff_{side}"
    cuff.scale = (1.0, 1.1, 0.55)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    cuff.data.materials.append(make_mat(f"Cuff_{side}", ORANGE, 0.5))
    parts.append(cuff)
    collection_objs.extend(parts)
    return parts


def add_glove_at(loc, side, collection_objs):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.04, location=loc)
    g = bpy.context.active_object
    g.name = f"Glove_{side}"
    g.scale = (1.05, 0.75, 1.2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    g.data.materials.append(make_mat(f"GloveMat_{side}", BLACK, 0.5))
    collection_objs.append(g)
    return g


def set_idle_pose(arm):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")

    def rot(name, euler):
        b = arm.pose.bones.get(name)
        if not b:
            return
        b.rotation_mode = "XYZ"
        b.rotation_euler = Euler(euler)

    rot("J_Bip_L_UpperArm", (0, 0, math.radians(40)))
    rot("J_Bip_R_UpperArm", (0, 0, math.radians(-40)))
    rot("J_Bip_L_LowerArm", (0, math.radians(-10), math.radians(5)))
    rot("J_Bip_R_LowerArm", (0, math.radians(10), math.radians(-5)))
    rot("J_Bip_L_UpperLeg", (math.radians(3), 0, math.radians(2)))
    rot("J_Bip_R_UpperLeg", (math.radians(3), 0, math.radians(-2)))

    arm.animation_data_create()
    action = bpy.data.actions.new("idle")
    arm.animation_data.action = action
    for b in arm.pose.bones:
        b.keyframe_insert(data_path="rotation_euler", frame=1)
        b.keyframe_insert(data_path="location", frame=1)
    chest = arm.pose.bones.get("J_Bip_C_UpperChest") or arm.pose.bones.get("J_Bip_C_Chest")
    if chest:
        chest.rotation_mode = "XYZ"
        chest.rotation_euler = Euler((math.radians(2), 0, 0))
        chest.keyframe_insert(data_path="rotation_euler", frame=1)
        chest.rotation_euler = Euler((math.radians(-1), 0, 0))
        chest.keyframe_insert(data_path="rotation_euler", frame=60)
        chest.rotation_euler = Euler((math.radians(2), 0, 0))
        chest.keyframe_insert(data_path="rotation_euler", frame=120)
    bpy.ops.object.mode_set(mode="OBJECT")
    # Apply visual pose as rest? No — keep as animated idle for export
    track = arm.animation_data.nla_tracks.new()
    track.name = "idle"
    track.strips.new("idle", 1, action)


def mesh_bbox(objs):
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for i in range(3):
                mn[i] = min(mn[i], w[i])
                mx[i] = max(mx[i], w[i])
    return mn, mx


def main():
    paths = {
        "tops": str(TEX_DIR / "tops_jacket.png"),
        "bottoms": str(TEX_DIR / "bottoms_stripe.png"),
        "shoes": str(TEX_DIR / "shoes_dark.png"),
    }
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=BASE_VRM)
    for o in list(bpy.data.objects):
        if "Ico" in o.name:
            bpy.data.objects.remove(o, do_unlink=True)

    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    arm.name = "SkaterArmature"
    body = bpy.data.objects.get("Body")
    face = bpy.data.objects.get("Face")

    # Delete tie faces
    if body:
        tie_idx = next((i for i, s in enumerate(body.material_slots) if s.material and "Tie" in s.material.name), None)
        if tie_idx is not None:
            bpy.context.view_layer.objects.active = body
            bpy.ops.object.mode_set(mode="EDIT")
            bm = bmesh.from_edit_mesh(body.data)
            for f in list(bm.faces):
                if f.material_index == tie_idx:
                    bm.faces.remove(f)
            bmesh.update_edit_mesh(body.data)
            bpy.ops.object.mode_set(mode="OBJECT")

    swap_image(bpy.data.materials.get("M00_001_01_Tops_01_CLOTH"), paths["tops"])
    swap_image(bpy.data.materials.get("M00_001_01_Bottoms_01_CLOTH"), paths["bottoms"])
    swap_image(bpy.data.materials.get("M00_001_01_Shoes_01_CLOTH"), paths["shoes"])

    hair_mat = bpy.data.materials.get("M00_000_HairBack_00_HAIR")
    if hair_mat and hair_mat.use_nodes:
        for n in hair_mat.node_tree.nodes:
            if n.type == "MIX":
                try:
                    n.inputs[7].default_value = HAIR_NAVY
                except Exception:
                    pass

    # Pose FIRST so foot/hand locations are correct for gear placement
    set_idle_pose(arm)
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.context.view_layer.update()

    gear = []
    # Foot bones after pose
    for side, bname in (("L", "J_Bip_L_Foot"), ("R", "J_Bip_R_Foot")):
        loc = bone_world_head(arm, bname)
        print("Foot", side, bname, loc)
        if loc:
            # drop slightly so wheels near ground
            add_skate_at(Vector((loc.x, loc.y, 0.0)), side, gear)

    for side, bname in (("L", "J_Bip_L_Hand"), ("R", "J_Bip_R_Hand")):
        loc = bone_world_head(arm, bname)
        print("Hand", side, bname, loc)
        if loc:
            add_glove_at(loc, side, gear)

    # Parent gear to armature object (object parent, keep transform) so they move with root
    for g in gear:
        mw = g.matrix_world.copy()
        g.parent = arm
        g.matrix_world = mw

    core = [o for o in bpy.data.objects if o.type == "MESH" and o.name in ("Body", "Face")]
    mn, mx = mesh_bbox(core + gear)
    print("BBOX core+gear", mn, mx)
    # Shift armature so lowest point ~ 0
    dz = -mn.z
    arm.location.z += dz
    bpy.context.view_layer.update()
    mn, mx = mesh_bbox([o for o in bpy.data.objects if o.type == "MESH"])
    print("BBOX final", mn, mx, "H", mx.z - mn.z)

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
        export_apply=False,
        export_skins=True,
        export_morph=True,
    )
    print("Wrote", OUT_GLB, os.path.getsize(OUT_GLB))


if __name__ == "__main__":
    main()
