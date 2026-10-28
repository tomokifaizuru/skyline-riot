#!/usr/bin/env python3
"""v0.4c: keep face intact, thicker sheet-matched hair, posed gear via CHILD_OF, 2-wheel shoes."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Euler
from pathlib import Path

ASSETS = Path("/workspace/skyline-riot/assets/character")
TEX = ASSETS / "textures"
BASE_VRM = "/tmp/vroid_cc0/base_male/Base_Male.vrm"
OUT_BLEND = str(ASSETS / "skater.blend")
OUT_GLB = str(ASSETS / "skater.glb")

HAIR = (0.03, 0.055, 0.13, 1)
HAIR_HI = (0.25, 0.42, 0.68, 1)
BLACK = (0.02, 0.02, 0.025, 1)
ORANGE = (1.0, 0.36, 0.07, 1)
WHITE = (0.94, 0.94, 0.97, 1)
RED = (0.85, 0.1, 0.1, 1)
SILVER = (0.78, 0.8, 0.85, 1)
NAVY = (0.12, 0.22, 0.48, 1)
rng = random.Random(11)


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


def xf(o):
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
    if len(objs) > 1: bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def bh(arm, n):
    pb = arm.pose.bones.get(n)
    return (arm.matrix_world @ pb.head) if pb else None


def bt(arm, n):
    pb = arm.pose.bones.get(n)
    return (arm.matrix_world @ pb.tail) if pb else None


def bm(arm, n):
    pb = arm.pose.bones.get(n)
    return (arm.matrix_world @ pb.matrix) if pb else None


def child_of(obj, arm, bone):
    mw = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = "OBJECT"
    obj.matrix_world = mw
    for c in list(obj.constraints):
        if c.type == "CHILD_OF":
            obj.constraints.remove(c)
    c = obj.constraints.new("CHILD_OF")
    c.target = arm
    c.subtarget = bone
    bpy.context.view_layer.update()
    c.inverse_matrix = bm(arm, bone).inverted()


def pose_idle(arm):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    def rot(n, d):
        b = arm.pose.bones.get(n)
        if not b: return
        b.rotation_mode = "XYZ"
        b.rotation_euler = Euler(tuple(math.radians(x) for x in d))
    rot("J_Bip_L_UpperArm", (8, 10, 80))
    rot("J_Bip_R_UpperArm", (8, -10, -80))
    rot("J_Bip_L_LowerArm", (5, -18, 10))
    rot("J_Bip_R_LowerArm", (5, 18, -10))
    rot("J_Bip_C_Hips", (0, 0, 5))
    rot("J_Bip_L_UpperLeg", (5, 0, 4))
    rot("J_Bip_R_UpperLeg", (3, 0, -6))
    rot("J_Bip_L_LowerLeg", (-5, 0, 0))
    rot("J_Bip_R_LowerLeg", (-3, 0, 0))
    rot("J_Bip_C_Spine", (3, 0, -2))
    rot("J_Bip_C_Chest", (4, 0, 0))
    rot("J_Bip_C_Head", (-2, 0, -3))
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def hide_mats(body, keys):
    idxs = [i for i,s in enumerate(body.material_slots) if s.material and any(k in s.material.name for k in keys)]
    if not idxs: return
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode="EDIT")
    bmsh = bmesh.from_edit_mesh(body.data)
    for f in list(bmsh.faces):
        if f.material_index in idxs:
            bmsh.faces.remove(f)
    bmesh.update_edit_mesh(body.data)
    bpy.ops.object.mode_set(mode="OBJECT")


def build_hair(arm):
    """Thicker wild spikes matching sheet silhouette."""
    m1, m2 = mat("HN", HAIR, 0.4), mat("HH", HAIR_HI, 0.35)
    head = bh(arm, "J_Bip_C_Head") or Vector((0,0,1.58))
    # Scalp cap — slightly larger, navy
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.105, location=head+Vector((0,0.01,0.015)))
    cap = bpy.context.active_object
    cap.scale = (1.08, 1.12, 0.92)
    xf(cap); cap.data.materials.append(m1)
    parts = [cap]
    crown = head + Vector((0, 0.0, 0.04))

    def spike(origin, direction, length, r1, material, v=8):
        d = Vector(direction).normalized()
        bpy.ops.mesh.primitive_cone_add(vertices=v, radius1=r1, radius2=0.002, depth=length,
                                        location=origin + d*(length*0.4))
        o = bpy.context.active_object
        o.rotation_euler = d.to_track_quat("Z","Y").to_euler()
        xf(o); o.data.materials.append(material)
        return o

    # BIG crown spikes — thick, jagged, up+back (sheet)
    crown_dirs = [
        (0.0, -0.2, 1.0, 0.40, 0.065),
        (0.15, -0.25, 0.95, 0.36, 0.055),
        (-0.15, -0.25, 0.95, 0.36, 0.055),
        (0.28, -0.15, 0.9, 0.32, 0.05),
        (-0.28, -0.15, 0.9, 0.32, 0.05),
        (0.1, -0.35, 0.85, 0.34, 0.048),
        (-0.1, -0.35, 0.85, 0.34, 0.048),
        (0.35, -0.05, 0.8, 0.28, 0.045),
        (-0.35, -0.05, 0.8, 0.28, 0.045),
        (0.05, -0.45, 0.75, 0.30, 0.042),
        (-0.05, -0.45, 0.75, 0.30, 0.042),
        (0.22, -0.3, 0.7, 0.26, 0.04),
        (-0.22, -0.3, 0.7, 0.26, 0.04),
    ]
    for i,(x,y,z,L,R) in enumerate(crown_dirs):
        j = Vector((x+rng.uniform(-0.03,0.03), y+rng.uniform(-0.03,0.03), z))
        parts.append(spike(crown, j, L+rng.uniform(-0.02,0.03), R, m1 if i%3 else m2))

    # Side spikes radiating out
    for side in (-1, 1):
        for i, (out, up, L, R) in enumerate([
            (0.95, 0.55, 0.26, 0.048),
            (1.0, 0.35, 0.22, 0.042),
            (0.9, 0.15, 0.20, 0.038),
            (0.85, 0.7, 0.24, 0.045),
            (0.75, 0.4, 0.18, 0.035),
        ]):
            d = Vector((side*out, -0.2+rng.uniform(-0.1,0.1), up))
            parts.append(spike(crown+Vector((side*0.06,0,0)), d, L, R, m1 if i%2 else m2))

    # Back spikes
    for i in range(10):
        ang = -0.6 + i*0.15
        d = Vector((math.sin(ang)*0.5, -0.95, 0.35+rng.uniform(0,0.35)))
        parts.append(spike(crown+Vector((0,-0.02,0)), d, rng.uniform(0.16,0.26), rng.uniform(0.03,0.045), m1))

    # Messy pointed bangs — over forehead BETWEEN eyes, not covering eyes
    bang_specs = [
        (-0.04, 0.08, 0.12, 0.028),
        (-0.02, 0.09, 0.13, 0.03),
        (0.0, 0.095, 0.14, 0.032),
        (0.02, 0.09, 0.13, 0.03),
        (0.04, 0.08, 0.12, 0.028),
        (-0.06, 0.07, 0.10, 0.024),
        (0.06, 0.07, 0.10, 0.024),
    ]
    for i,(x,L,up_bias,R) in enumerate(bang_specs):
        # forward (+Y), slightly down
        d = Vector((x*2.5, 1.0, -0.25+up_bias*0.1))
        origin = head + Vector((x, 0.085, 0.02))
        parts.append(spike(origin, d, L, R, m2 if i in (2,3) else m1, v=6))

    # Nape tufts
    for i in range(7):
        x = -0.06 + i*0.02
        d = Vector((x*0.5, -0.5, -0.75))
        parts.append(spike(head+Vector((x,-0.08,-0.05)), d, rng.uniform(0.06,0.10), rng.uniform(0.015,0.025), m1, v=6))

    hair = join(parts, "HairSpikes")
    if hair:
        child_of(hair, arm, "J_Bip_C_Head")
    return hair


def build_tee(arm):
    m = mat("Tee", WHITE, 0.62)
    parts = []
    bpy.ops.mesh.primitive_cylinder_add(vertices=22, radius=0.14, depth=0.40, location=(0, 0.025, 1.26))
    t = bpy.context.active_object; t.scale=(1.0,0.8,1); xf(t); t.data.materials.append(m); parts.append(t)
    bpy.ops.mesh.primitive_cylinder_add(vertices=22, radius=0.15, depth=0.13, location=(0, 0.025, 1.00))
    h = bpy.context.active_object; h.scale=(1.06,0.84,1); xf(h); h.data.materials.append(m); parts.append(h)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.052, minor_radius=0.012, location=(0,0.04,1.46))
    n = bpy.context.active_object; xf(n); n.data.materials.append(m); parts.append(n)
    for sx in (-1,1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.065, location=(sx*0.13,0.02,1.40))
        s=bpy.context.active_object; s.scale=(1.1,0.85,0.7); xf(s); s.data.materials.append(m); parts.append(s)
    obj = join(parts, "LooseTee")
    if obj:
        obj.parent = arm
        mod = obj.modifiers.new("Armature","ARMATURE"); mod.object = arm
        for bn in ("J_Bip_C_Hips","J_Bip_C_Spine","J_Bip_C_Chest","J_Bip_C_UpperChest"):
            obj.vertex_groups.new(name=bn)
        for i,v in enumerate(obj.data.vertices):
            z=(obj.matrix_world@v.co).z
            g = "J_Bip_C_UpperChest" if z>1.38 else "J_Bip_C_Chest" if z>1.22 else "J_Bip_C_Spine" if z>1.08 else "J_Bip_C_Hips"
            obj.vertex_groups[g].add([i],1,"REPLACE")
    return obj


def build_jacket(arm):
    mo, mi, mp, mc = mat("JO",BLACK,0.48), mat("JI",ORANGE,0.55), mat("JP",WHITE,0.4), mat("JC",RED,0.4)
    parts=[]
    # Open front panels
    for sx in (-1,1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.155, depth=0.36, location=(sx*0.05,0.04,1.28))
        p=bpy.context.active_object; p.scale=(0.5,0.75,1); p.rotation_euler.z=math.radians(sx*-10); xf(p)
        p.data.materials.append(mo); parts.append(p)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(sx*0.015,0.13,1.28))
        lin=bpy.context.active_object; lin.scale=(0.018,0.025,0.32); xf(lin); lin.data.materials.append(mi); parts.append(lin)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.165, depth=0.36, location=(0,-0.05,1.28))
    back=bpy.context.active_object; back.scale=(1.0,0.5,1); xf(back); back.data.materials.append(mo); parts.append(back)
    # Crest
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.055, depth=0.014, location=(0,-0.145,1.40))
    cr=bpy.context.active_object; cr.rotation_euler=(math.pi/2,0,0); xf(cr); cr.data.materials.append(mc); parts.append(cr)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.065, minor_radius=0.007, location=(0,-0.145,1.40))
    rg=bpy.context.active_object; rg.rotation_euler=(math.pi/2,0,0); xf(rg); rg.data.materials.append(mp); parts.append(rg)
    # High collar
    bpy.ops.mesh.primitive_torus_add(major_radius=0.072, minor_radius=0.03, location=(0,0.025,1.51))
    col=bpy.context.active_object; col.scale=(1,0.88,1.35); xf(col); col.data.materials.append(mo); parts.append(col)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.065, minor_radius=0.02, location=(0,0.05,1.51))
    coli=bpy.context.active_object; coli.scale=(1,0.82,1.15); xf(coli); coli.data.materials.append(mi); parts.append(coli)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.17, minor_radius=0.006, location=(0,0.01,1.11))
    hem=bpy.context.active_object; hem.scale=(1,0.72,1); xf(hem); hem.data.materials.append(mp); parts.append(hem)
    # Sleeves on posed arms + CHILD_OF later as part of joined jacket — weight instead
    sleeve_bones = []
    for side,up,low,hand in (("L","J_Bip_L_UpperArm","J_Bip_L_LowerArm","J_Bip_L_Hand"),
                             ("R","J_Bip_R_UpperArm","J_Bip_R_LowerArm","J_Bip_R_Hand")):
        a,b,c = bh(arm,up), bh(arm,low), bh(arm,hand)
        if not a or not b or not c: continue
        for p0,p1,r in ((a,b,0.06),(b,c,0.05)):
            mid=(p0+p1)*0.5; L=(p1-p0).length*0.9; d=(p1-p0).normalized()
            bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=r, depth=max(L,0.04), location=mid)
            s=bpy.context.active_object; s.rotation_euler=d.to_track_quat("Z","Y").to_euler(); xf(s)
            s.data.materials.append(mo); parts.append(s)
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.007, depth=max(L*0.8,0.03), location=mid+Vector((0,0.03,0)))
            pipe=bpy.context.active_object; pipe.rotation_euler=d.to_track_quat("Z","Y").to_euler(); xf(pipe)
            pipe.data.materials.append(mp); parts.append(pipe)
        bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=0.054, depth=0.038, location=c-(c-b).normalized()*0.02)
        cf=bpy.context.active_object; cf.rotation_euler=(c-b).normalized().to_track_quat("Z","Y").to_euler(); xf(cf)
        cf.data.materials.append(mi); parts.append(cf)

    jacket = join(parts, "Jacket")
    if jacket:
        jacket.parent = arm
        mod = jacket.modifiers.new("Armature","ARMATURE"); mod.object=arm
        bnames=["J_Bip_C_Spine","J_Bip_C_Chest","J_Bip_C_UpperChest","J_Bip_C_Neck",
                "J_Bip_L_Shoulder","J_Bip_R_Shoulder","J_Bip_L_UpperArm","J_Bip_L_LowerArm",
                "J_Bip_R_UpperArm","J_Bip_R_LowerArm"]
        for bn in bnames: jacket.vertex_groups.new(name=bn)
        bones={b.name:b for b in arm.data.bones if b.name in jacket.vertex_groups}
        for vi,v in enumerate(jacket.data.vertices):
            wco=jacket.matrix_world@v.co
            scored=[]
            for bn,b in bones.items():
                bhv=arm.matrix_world@b.head_local; btv=arm.matrix_world@b.tail_local
                ab=btv-bhv; t=max(0,min(1,(wco-bhv).dot(ab)/(ab.length_squared+1e-9)))
                scored.append(((wco-(bhv+ab*t)).length, bn))
            scored.sort(); tot=sum(1/(d+0.04) for d,_ in scored[:2])
            for d,bn in scored[:2]:
                jacket.vertex_groups[bn].add([vi], (1/(d+0.04))/tot, "REPLACE")
    return jacket


def build_gloves(arm):
    m=mat("Glv",BLACK,0.5)
    for side,hand in (("L","J_Bip_L_Hand"),("R","J_Bip_R_Hand")):
        h=bh(arm,hand)
        if not h: continue
        parts=[]
        bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=10, radius=0.038, location=h)
        g=bpy.context.active_object; g.scale=(1.15,0.72,1.25); xf(g); g.data.materials.append(m); parts.append(g)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.034, minor_radius=0.007, location=h)
        st=bpy.context.active_object; xf(st); st.data.materials.append(m); parts.append(st)
        for ox,oy,oz in [(-0.012,0.028,-0.008),(0,0.032,-0.004),(0.012,0.028,-0.008),(0.022,0.018,-0.012),(-0.022,0.014,0)]:
            if side=="R": ox=-ox
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.01, depth=0.022, location=h+Vector((ox,oy,oz)))
            f=bpy.context.active_object
            f.rotation_euler=Vector((ox,oy+0.04,oz)).normalized().to_track_quat("Z","Y").to_euler(); xf(f)
            f.data.materials.append(m); parts.append(f)
        obj=join(parts, f"Glove_{side}")
        child_of(obj, arm, hand)


def build_belt(arm):
    mw,mb,ms=mat("BW",WHITE,0.45),mat("BB",NAVY,0.45),mat("BK",SILVER,0.3,0.55)
    parts=[]
    bpy.ops.mesh.primitive_torus_add(major_radius=0.122, minor_radius=0.013, location=(0,0.02,1.00))
    b=bpy.context.active_object; b.scale=(1.05,0.78,1); xf(b); b.data.materials.append(mw); parts.append(b)
    for dz in (-0.008,0.008):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.123, minor_radius=0.0035, location=(0,0.02,1.00+dz))
        s=bpy.context.active_object; s.scale=(1.05,0.78,1); xf(s); s.data.materials.append(mb); parts.append(s)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.07,0.07,0.84))
    d=bpy.context.active_object; d.scale=(0.015,0.008,0.15); xf(d); d.data.materials.append(mw); parts.append(d)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0.115,1.00))
    k=bpy.context.active_object; k.scale=(0.032,0.012,0.026); xf(k); k.data.materials.append(ms); parts.append(k)
    obj=join(parts,"Belt")
    if obj: obj.parent=arm


def build_shoes(arm):
    m_boot,m_frame,m_wheel,m_lace = mat("Boot",BLACK,0.45), mat("Frame",(0.06,0.06,0.08,1),0.4,0.3), mat("Wheel",SILVER,0.3,0.45), mat("Lace",(0.28,0.28,0.3,1),0.5)
    for side,foot in (("L","J_Bip_L_Foot"),("R","J_Bip_R_Foot")):
        fh, ft = bh(arm,foot), bt(arm,foot)
        if not fh: continue
        forward = (ft-fh) if ft else Vector((0,1,0))
        forward.z=0
        if forward.length<1e-4: forward=Vector((0,1,0))
        forward.normalize()
        right = forward.cross(Vector((0,0,1))).normalized()
        base = Vector((fh.x, fh.y, 0.0))
        parts=[]
        bpy.ops.mesh.primitive_cube_add(size=1, location=base+forward*0.02+Vector((0,0,0.068)))
        boot=bpy.context.active_object; boot.scale=(0.068,0.125,0.062)
        boot.rotation_euler=forward.to_track_quat("Y","Z").to_euler(); xf(boot)
        boot.modifiers.new("Sub","SUBSURF").levels=1; boot.data.materials.append(m_boot); parts.append(boot)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.048, location=base+forward*0.095+Vector((0,0,0.048)))
        toe=bpy.context.active_object; toe.scale=(1.05,1.2,0.7); xf(toe); toe.data.materials.append(m_boot); parts.append(toe)
        bpy.ops.mesh.primitive_cube_add(size=1, location=base+forward*0.02+Vector((0,0,0.016)))
        fr=bpy.context.active_object; fr.scale=(0.03,0.105,0.011)
        fr.rotation_euler=forward.to_track_quat("Y","Z").to_euler(); xf(fr); fr.data.materials.append(m_frame); parts.append(fr)
        for along in (0.078, -0.042):
            wloc=base+forward*along+Vector((0,0,0.038))
            bpy.ops.mesh.primitive_cylinder_add(vertices=22, radius=0.038, depth=0.028, location=wloc)
            w=bpy.context.active_object; w.rotation_euler=right.to_track_quat("Z","Y").to_euler(); xf(w)
            w.data.materials.append(m_wheel); parts.append(w)
            bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.01, depth=0.034, location=wloc)
            hub=bpy.context.active_object; hub.rotation_euler=right.to_track_quat("Z","Y").to_euler(); xf(hub)
            hub.data.materials.append(m_frame); parts.append(hub)
        bpy.ops.mesh.primitive_cube_add(size=1, location=base+forward*0.04+Vector((0,0,0.11)))
        lace=bpy.context.active_object; lace.scale=(0.028,0.048,0.01)
        lace.rotation_euler=forward.to_track_quat("Y","Z").to_euler(); xf(lace); lace.data.materials.append(m_lace); parts.append(lace)
        shoe=join(parts, f"SkateShoe_{side}")
        child_of(shoe, arm, foot)


def idle_action(arm):
    if arm.animation_data: arm.animation_data_clear()
    arm.animation_data_create()
    action=bpy.data.actions.new("idle"); arm.animation_data.action=action
    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode="POSE")
    # re-apply pose values as keyframes (pose already set)
    for b in arm.pose.bones:
        b.rotation_mode="XYZ"
        b.keyframe_insert(data_path="rotation_euler", frame=1)
        b.keyframe_insert(data_path="location", frame=1)
    chest=arm.pose.bones.get("J_Bip_C_UpperChest") or arm.pose.bones.get("J_Bip_C_Chest")
    if chest:
        base=list(chest.rotation_euler)
        for fr,d in ((1,2),(60,-1.5),(120,2)):
            chest.rotation_euler=Euler((base[0]+math.radians(d),base[1],base[2]))
            chest.keyframe_insert(data_path="rotation_euler", frame=fr)
    hips=arm.pose.bones.get("J_Bip_C_Hips")
    if hips:
        base=list(hips.rotation_euler)
        for fr,d in ((1,1.2),(90,-1.2),(180,1.2)):
            hips.rotation_euler=Euler((base[0],base[1],base[2]+math.radians(d)))
            hips.keyframe_insert(data_path="rotation_euler", frame=fr)
    bpy.ops.object.mode_set(mode="OBJECT")
    tr=arm.animation_data.nla_tracks.new(); tr.name="idle"; tr.strips.new("idle",1,action)
    for nm in ("skate","grind","air"):
        a2=action.copy(); a2.name=nm
        t2=arm.animation_data.nla_tracks.new(); t2.name=nm; t2.strips.new(nm,1,a2)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=BASE_VRM)
    for o in list(bpy.data.objects):
        if "Ico" in o.name: bpy.data.objects.remove(o, do_unlink=True)
    arm=next(o for o in bpy.data.objects if o.type=="ARMATURE"); arm.name="SkaterArmature"
    body=bpy.data.objects.get("Body")

    if (TEX/"face_mature.png").exists():
        swap_tex(bpy.data.materials.get("M00_000_00_Face_00_SKIN"), TEX/"face_mature.png")
    if (TEX/"face_brow_firm.png").exists():
        swap_tex(bpy.data.materials.get("M00_000_00_FaceBrow_00_FACE"), TEX/"face_brow_firm.png")
    if (TEX/"face_eyeline_firm.png").exists():
        swap_tex(bpy.data.materials.get("M00_000_00_FaceEyeline_00_FACE"), TEX/"face_eyeline_firm.png")
    hm=bpy.data.materials.get("M00_000_HairBack_00_HAIR")
    if hm and hm.use_nodes:
        for n in hm.node_tree.nodes:
            if n.type=="MIX":
                try: n.inputs[7].default_value=HAIR
                except: pass
    if (TEX/"bottoms_stripe.png").exists():
        swap_tex(bpy.data.materials.get("M00_001_01_Bottoms_01_CLOTH"), TEX/"bottoms_stripe.png")

    hide_mats(body, ("Tops","Shoes","Tie","Accessory"))
    # Shrink original hairback so spikes dominate
    # (faces stay for scalp)

    print("Pose idle (keep shape keys)…")
    pose_idle(arm)
    print("Tee…"); build_tee(arm)
    print("Jacket…"); build_jacket(arm)
    print("Hair…"); build_hair(arm)
    print("Gloves…"); build_gloves(arm)
    print("Belt…"); build_belt(arm)
    print("Shoes…"); build_shoes(arm)
    print("Action…"); idle_action(arm)

    mn=Vector((1e9,)*3); mx=Vector((-1e9,)*3)
    for o in bpy.data.objects:
        if o.type!="MESH": continue
        for c in o.bound_box:
            w=o.matrix_world@Vector(c)
            for i in range(3):
                mn[i]=min(mn[i],w[i]); mx[i]=max(mx[i],w[i])
    print("BBOX", mn, mx)
    arm.location.z -= mn.z
    bpy.context.view_layer.update()

    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.data.objects:
        if o.type in ("MESH","ARMATURE"): o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True,
                              export_animations=True, export_skins=True, export_morph=True)
    print("Wrote", OUT_GLB, os.path.getsize(OUT_GLB))


if __name__=="__main__":
    main()
