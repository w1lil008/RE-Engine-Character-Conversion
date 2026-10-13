"""Create an editable native-rig preparation scene and offline QA renders.

Run portable Blender -b --factory-startup --python scripts/blender_scene.py.
Uses project adapter data, with no global addon installation or preference writes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import json
import math
import numpy as np
from mathutils import Matrix, Vector
from common import ROOT, reader, write_json
from analyze_assets import parsed_mesh

ROTATE = Matrix.Rotation(math.pi / 2, 4, "X")


def make_rig(skeleton, collection):
    data = bpy.data.armatures.new("GraceOriginalBindRig")
    obj = bpy.data.objects.new("GraceOriginalBindRig", data)
    collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in skeleton.boneList:
        edit = data.edit_bones.new(bone.boneName)
        edit.matrix = ROTATE @ Matrix(bone.worldMatrix.matrix).transposed()
        edit.length = .025
        edit["reMeshWorldMatrix"] = bone.worldMatrix.matrix
        edit["reMeshLocalMatrix"] = bone.localMatrix.matrix
        edit["reMeshInverseMatrix"] = bone.inverseMatrix.matrix
    for bone in skeleton.boneList:
        if bone.parentIndex >= 0:
            data.edit_bones[bone.boneName].parent = data.edit_bones[skeleton.boneList[bone.parentIndex].boneName]
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    obj.show_in_front = True
    return obj


def make_material(mat, previews):
    material = bpy.data.materials.new(mat.materialName)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = .6
    bindings = {t.textureType: t.texturePath.lower() for t in mat.textureList}
    base_path = bindings.get("BaseDielectricMap", bindings.get("BaseShiftMap"))
    if base_path in previews:
        image_node = nodes.new("ShaderNodeTexImage")
        image_node.image = bpy.data.images.load(str(previews[base_path]), check_existing=True)
        multiply = nodes.new("ShaderNodeMixRGB")
        multiply.blend_type = "MULTIPLY"
        multiply.inputs[0].default_value = 1
        tint = next((p.propValue for p in mat.propertyList if p.propName == "BaseColor"), [1, 1, 1, 1])
        multiply.inputs[2].default_value = tint
        links.new(image_node.outputs["Color"], multiply.inputs[1])
        links.new(multiply.outputs[0], bsdf.inputs["Base Color"])
    if "Hair" in mat.materialName or "eyelash" in mat.materialName or "eyebrow" in mat.materialName:
        alpha_path = bindings.get("AlphaCavityOcclusionTranslucentMap")
        if alpha_path in previews:
            mask = nodes.new("ShaderNodeTexImage")
            mask.image = bpy.data.images.load(str(previews[alpha_path]), check_existing=True)
            mask.image.colorspace_settings.name = "Non-Color"
            separate = nodes.new("ShaderNodeSeparateColor")
            links.new(mask.outputs["Color"], separate.inputs[0])
            links.new(separate.outputs["Red"], bsdf.inputs["Alpha"])
            material.surface_render_method = "DITHERED"
    return material


def create_mesh(part, mesh, rig, materials, collection):
    created = []
    for group in mesh.mainMeshLODList[0].visconGroupList:
        for index, sub in enumerate(group.subMeshList):
            name = f"{part}_{index}_{mesh.materialNameList[sub.materialIndex]}"
            data = bpy.data.meshes.new(name)
            positions = [(ROTATE @ Vector(p)).to_tuple() for p in sub.vertexPosList]
            data.from_pydata(positions, [], sub.faceList)
            data.update()
            uv = data.uv_layers.new(name="UVMap0")
            for loop in data.loops:
                # The upstream parser has already converted UVs for Blender.
                value = sub.uvList[loop.vertex_index]
                uv.data[loop.index].uv = value
            data.polygons.foreach_set("use_smooth", [True] * len(data.polygons))
            normals = [(ROTATE.to_3x3() @ Vector(n)).normalized().to_tuple() for n in sub.normalList]
            data.normals_split_custom_set_from_vertices(normals)
            data.materials.append(materials[mesh.materialNameList[sub.materialIndex]])
            obj = bpy.data.objects.new(name, data)
            collection.objects.link(obj)
            obj.parent = rig
            modifier = obj.modifiers.new("GraceSkin", "ARMATURE")
            modifier.object = rig
            groups = [obj.vertex_groups.new(name=name) for name in mesh.skeleton.weightedBones]
            for i, (indices, weights) in enumerate(zip(sub.weightIndicesList, sub.weightList)):
                for bone, weight in zip(indices, weights):
                    if weight > 0:
                        groups[bone].add([i], weight, "REPLACE")
            created.append(obj)
    return created


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (.08, .08, .08)
    scene.view_settings.view_transform = "AgX"
    collection = bpy.data.collections.new("Bela_on_Grace_Prototype")
    scene.collection.children.link(collection)
    build = json.loads((ROOT / "reports/mesh_build.json").read_text())
    material_build = json.loads((ROOT / "reports/material_build.json").read_text())
    previews = {Path(r["path"]).name.split(".tex")[0]: ROOT / r["preview"] for r in material_build["textures"]}
    by_resource = {"character/mods/belagrace/textures/" + name + ".tex": path for name, path in previews.items()}
    baseline = ROOT / "reports/baseline_previews.json"
    if baseline.is_file():
        by_resource.update({resource: ROOT / path for resource, path in json.loads(baseline.read_text())["resources"].items()})
    mdf_reader = reader("RE-Mesh-Editor", "remesh", "modules.mdf.file_re_mdf")
    rows = [row for row in build["outputs"] if "ch0200_40_01" not in row["path"] and "ch0200_21_00" not in row["path"]]
    rig = None
    objects = []
    for row in rows:
        path = ROOT / row["path"]
        _, mesh = parsed_mesh(path)
        if rig is None:
            rig = make_rig(mesh.skeleton, collection)
        mdf = mdf_reader.readMDF(str(next(path.parent.glob(path.name.split(".mesh")[0] + "*.mdf2.51"))))
        materials = {m.materialName: make_material(m, by_resource) for m in mdf.materialList}
        objects += create_mesh(row["part"], mesh, rig, materials, collection)
    bpy.ops.object.camera_add(location=(2.8, -5, 2.1))
    camera = bpy.context.object
    camera.name = "QA_Camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.1
    look_at(camera, (0, 0, .9))
    scene.camera = camera
    for name, position, power, size in [("Key", (2, -3, 4), 700, 3), ("Fill", (-3, -2, 2), 450, 3), ("Rim", (0, 3, 3), 650, 2)]:
        bpy.ops.object.light_add(type="AREA", location=position)
        light = bpy.context.object
        light.name = name
        light.data.energy, light.data.shape, light.data.size = power, "DISK", size
        look_at(light, (0, 0, 1))
    scene["PROJECT_STATUS"] = "Offline prototype; NO in-game test"
    scene["FACIAL_STATUS"] = "Rigid neutral Bela head; facial retargeting pending"
    scene["PHYSICS_STATUS"] = "Static hair; skirt uses body-surface skinning; native cloth pending"
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "assets/work/BelaGrace_preparation.blend"))
    for name, camera_position in [("front", (0, -5, 1.8)), ("rear", (0, 5, 1.8))]:
        camera.location = camera_position
        look_at(camera, (0, 0, .9))
        scene.render.filepath = str(ROOT / f"reports/preview_{name}.png")
        bpy.ops.render.render(write_still=True)
    # A deliberately simple local pose catches weighting explosions. This is not
    # an imported gameplay animation and is never presented as in-game evidence.
    rig.pose.bones["L_Arm_Upper"].rotation_mode = "XYZ"
    rig.pose.bones["L_Arm_Upper"].rotation_euler.z = .45
    rig.pose.bones["R_Arm_Upper"].rotation_mode = "XYZ"
    rig.pose.bones["R_Arm_Upper"].rotation_euler.z = -.45
    bpy.context.view_layer.update()
    validation = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        points = np.array([v.co[:] for v in mesh.vertices])
        if not np.isfinite(points).all() or np.max(np.abs(points)) > 5:
            raise ValueError(f"Invalid deformation in {obj.name}")
        validation.append({"object": obj.name, "vertices": len(points), "bounds": [points.min(0).tolist(), points.max(0).tolist()]})
        evaluated.to_mesh_clear()
    camera.location = (2.8, -5, 2.1)
    look_at(camera, (0, 0, .9))
    scene.render.filepath = str(ROOT / "reports/preview_pose.png")
    bpy.ops.render.render(write_still=True)
    write_json(ROOT / "reports/blender_qa.json", {"blender": bpy.app.version_string, "status": "OFFLINE_SYNTHETIC_POSE_ONLY", "objects": validation})


if __name__ == "__main__":
    main()

