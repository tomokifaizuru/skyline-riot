import bpy, os
from mathutils import Vector

BLEND = "/workspace/skyline-riot/assets/character/skater.blend"
OUT = "/workspace/skyline-riot/shots"
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 900
scene.render.resolution_y = 1400
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
scene.eevee.taa_render_samples = 48

# Solid backdrop
world = bpy.data.worlds.new("W") if "W" not in bpy.data.worlds else bpy.data.worlds["W"]
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.12, 0.14, 0.20, 1)
bg.inputs[1].default_value = 0.7

def light(name, typ, loc, energy, color=(1,1,1), size=2.0):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    d = bpy.data.lights.new(name, typ)
    d.energy = energy
    d.color = color
    if typ == 'AREA':
        d.size = size
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = loc
    return o

light("Key", 'AREA', (2.0, 2.5, 2.6), 160, (1.0, 0.97, 0.93), 3)
light("Fill", 'AREA', (-2.2, 1.5, 1.8), 50, (0.6, 0.75, 1.0), 4)
light("Rim", 'AREA', (0.2, -2.8, 2.0), 130, (0.55, 0.8, 1.0), 2.5)
light("Hair", 'AREA', (-1.2, 1.0, 3.0), 45, (0.75, 0.85, 1), 1.5)

mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
for o in bpy.data.objects:
    if o.type != "MESH": continue
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i]=min(mn[i],w[i]); mx[i]=max(mx[i],w[i])
center = (mn+mx)/2
height = mx.z - mn.z
print("BBOX", mn, mx, "H", height)

# ground
bpy.ops.mesh.primitive_plane_add(size=6, location=(center.x, center.y, mn.z))
g = bpy.context.active_object
mat = bpy.data.materials.new("Ground")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.08, 0.09, 0.12, 1)
mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
g.data.materials.append(mat)

if "PreviewCam" in bpy.data.objects:
    cam = bpy.data.objects["PreviewCam"]
else:
    cd = bpy.data.cameras.new("PreviewCam")
    cam = bpy.data.objects.new("PreviewCam", cd)
    bpy.context.collection.objects.link(cam)
scene.camera = cam
cam.data.lens = 45

arm = bpy.data.objects.get("SkaterArmature")
if arm and arm.animation_data:
    for t in arm.animation_data.nla_tracks:
        if t.name == "idle" and t.strips:
            arm.animation_data.action = t.strips[0].action
            break
scene.frame_set(1)
target = Vector((center.x, center.y, center.z + height * 0.02))

def shoot(name, loc, res=None, look=None):
    if res:
        scene.render.resolution_x, scene.render.resolution_y = res
    cam.location = Vector(loc)
    tgt = look or target
    cam.rotation_euler = (Vector(tgt) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print("Wrote", scene.render.filepath)

dist = max(height * 1.55, 2.6)
# Character faces +Y → front camera on +Y
shoot("blender_front.png", (center.x, center.y + dist, center.z + height*0.02), (900, 1400))
shoot("blender_back.png", (center.x, center.y - dist, center.z + height*0.02), (900, 1400))
shoot("blender_threequarter.png", (center.x - dist*0.65, center.y + dist*0.8, center.z + height*0.05), (900, 1400))
face_look = Vector((center.x, center.y, mx.z - height * 0.06))
shoot("blender_face.png", (center.x, center.y + 0.65, face_look.z), (900, 900), look=face_look)
print("done")
