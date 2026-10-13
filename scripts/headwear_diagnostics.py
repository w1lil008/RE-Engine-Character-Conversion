"""Inspect headwear motion and draft a local hair-weight correction in Blender.

Always reads the retained v0.1.0 preparation scene. Writes a separate candidate
scene/sidecar; never exports native files, packages or installs. Fixtures are
synthetic, not captured ADS animations. Card/hood BVH overlaps ignore alpha and
are diagnostic candidates, not an automatic visual collision-free gate.
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import numpy as np
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree
from blender_scene import look_at
from common import ROOT, write_json, confined
from rigging import sanitize_weights


def weights(obj, vertex):
    return [(obj.vertex_groups[g.group].name, float(g.weight))
            for g in vertex.groups if g.weight > 0]


def barycentric(point, triangle):
    a, b, c = np.asarray(triangle)
    v0, v1, v2 = b - a, c - a, np.asarray(point) - a
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
    denominator = d00 * d11 - d01 * d01
    if abs(denominator) < 1e-14:
        return np.eye(3)[np.argmin(np.linalg.norm(triangle - point, axis=1))]
    v = (d11 * (v2 @ v0) - d01 * (v2 @ v1)) / denominator
    w = (d00 * (v2 @ v1) - d01 * (v2 @ v0)) / denominator
    result = np.maximum([1 - v - w, v, w], 0)
    return result / result.sum()


def triangles(obj, evaluated=False):
    owner = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else obj
    data = owner.to_mesh() if evaluated else obj.data
    data.calc_loop_triangles()
    points = [tuple(obj.matrix_world @ v.co) for v in data.vertices]
    faces = [tuple(t.vertices) for t in data.loop_triangles]
    if evaluated:
        owner.to_mesh_clear()
    return points, faces


def reset(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion()
    bpy.context.view_layer.update()


def set_pose(rig, rotations):
    reset(rig)
    for name, axis, degrees in rotations:
        bone = rig.pose.bones[name]
        local_axis = bone.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
        bone.rotation_quaternion = bone.rotation_quaternion @ Quaternion(local_axis.normalized(), math.radians(degrees))
    bpy.context.view_layer.update()


def draft_transfer(hair, hood, front_limit=.075, front_width=.040):
    hood_points, hood_faces, hood_weights = [], [], []
    for obj in hood:
        points, faces = triangles(obj)
        offset = len(hood_points)
        hood_points.extend(points)
        hood_faces.extend([tuple(i + offset for i in face) for face in faces])
        hood_weights.extend([weights(obj, v) for v in obj.data.vertices])
    tree = BVHTree.FromPolygons(hood_points, hood_faces, all_triangles=True)
    points = np.asarray(hood_points)
    changes = []
    for obj in hair:
        rows, altered = [], 0
        for vertex in obj.data.vertices:
            original = weights(obj, vertex)
            point = obj.matrix_world @ vertex.co
            # Engine +Z is the face/opening direction. This configurable fade
            # can include lower forward locks omitted by the first correction.
            front = -point.y
            blend = float(np.clip((front_limit - front) / front_width, 0, 1))
            location, _, index, distance = tree.find_nearest(point)
            blend *= float(np.clip((.075 - distance) / .025, 0, 1))
            if blend > 1e-7:
                face = hood_faces[index]
                bary = barycentric(location, points[list(face)])
                transferred = [(name, weight * factor * blend)
                               for v, factor in zip(face, bary)
                               for name, weight in hood_weights[v]]
                result = sanitize_weights([(n, w * (1 - blend)) for n, w in original] + transferred)
            else:
                result = original
            old, new = dict(original), dict(result)
            delta = sum(abs(old.get(n, 0) - new.get(n, 0)) for n in set(old) | set(new))
            if delta > 1e-6:
                altered += 1
                for group in obj.vertex_groups:
                    if group.index in {g.group for g in vertex.groups}:
                        group.remove([vertex.index])
                for name, value in result:
                    group = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
                    group.add([vertex.index], value, "REPLACE")
            if len(result) > 8 or abs(sum(w for _, w in result) - 1) > 1e-5:
                raise ValueError(f"Invalid candidate weights: {obj.name}/{vertex.index}")
            rows.append(result)
        changes.append({"object": obj.name, "vertices": len(rows), "changed_vertices": altered, "weights": rows})
    return changes


def load_native_candidate(hair, path=None):
    from analyze_assets import parsed_mesh
    path = path or ROOT / "build/headwear_candidate/natives/stm/character/ch/ch02/0200/20/00/ch0200_20_00.mesh.250925211"
    _, native = parsed_mesh(path)
    by_material = {native.materialNameList[sub.materialIndex]: sub
                   for group in native.mainMeshLODList[0].visconGroupList for sub in group.subMeshList}
    for obj in hair:
        sub = by_material[obj.name.split("_", 2)[2]]
        assert len(sub.vertexPosList) == len(obj.data.vertices)
        for group in obj.vertex_groups:
            group.remove(list(range(len(obj.data.vertices))))
        for vertex, slots, values in zip(obj.data.vertices, sub.weightIndicesList, sub.weightList):
            assert np.allclose(vertex.co, Vector((sub.vertexPosList[vertex.index][0],
                                                -sub.vertexPosList[vertex.index][2],
                                                sub.vertexPosList[vertex.index][1])), atol=1e-6)
            for index, weight in zip(slots, values):
                if weight > 0:
                    name = native.skeleton.weightedBones[index]
                    group = obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
                    group.add([vertex.index], weight, "REPLACE")


def main():
    parser = argparse.ArgumentParser()
    mode_options = parser.add_mutually_exclusive_group()
    mode_options.add_argument("--candidate", action="store_true")
    mode_options.add_argument("--native-candidate", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--tag", default="headwear")
    parser.add_argument("--native-input")
    parser.add_argument("--scene", default="assets/work/BelaGrace_preparation.blend")
    parser.add_argument("--front-limit", type=float, default=.075)
    parser.add_argument("--front-width", type=float, default=.040)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if not args.tag.replace("_", "").isalnum() or args.front_width <= 0:
        raise ValueError("Invalid diagnostic tag/transition")
    bpy.ops.wm.open_mainfile(filepath=str(confined(ROOT, args.scene)))
    rig = bpy.data.objects["GraceOriginalBindRig"]
    reset(rig)
    collection = bpy.data.collections["Bela_on_Grace_Prototype"]
    meshes = [o for o in collection.objects if o.type == "MESH"]
    hair = [o for o in meshes if o.name.startswith("hair_")]
    hood = [o for o in meshes if "HoodInner_Mat" in o.name]
    outside = [o for o in meshes if "HoodOutside_Mat" in o.name]
    assert len(hair) == 2 and len(hood) == 1 and len(outside) == 1
    mode = "native_candidate" if args.native_candidate else ("candidate" if args.candidate else "baseline")
    output = confined(ROOT, "reports/" + args.tag)
    work = ROOT / "assets/work" if args.tag == "headwear" else confined(ROOT, "assets/work/" + args.tag)
    work.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    if args.native_input:
        load_native_candidate(hair, confined(ROOT, args.native_input))
    if args.candidate:
        changes = draft_transfer(hair, hood, args.front_limit, args.front_width)
        write_json(work / "headwear_candidate_weights.json", {
            "status": "DRAFT_BLENDER_ONLY_NOT_NATIVE_EXPORTED",
            "source_scene": "assets/work/BelaGrace_preparation.blend",
            "method": "Distance-faded barycentric hood-inner weights with configurable front fade; geometry retained",
            "starting_native": args.native_input,
            "front_limit_m": args.front_limit, "front_width_m": args.front_width,
            "position_changes": False, "native_physics_added": False, "objects": changes})
        rig["HEADWEAR_STATUS"] = "Draft hair/hood weight alignment; not tested in game"
        bpy.ops.wm.save_as_mainfile(filepath=str(work / "BelaGrace_headwear_candidate.blend"))
        print("Candidate altered vertices:", [c["changed_vertices"] for c in changes], flush=True)
    elif args.native_candidate:
        if not args.native_input:
            load_native_candidate(hair)
        rig["HEADWEAR_STATUS"] = "Native roundtrip hair-weight candidate; not tested in game"
        bpy.ops.wm.save_as_mainfile(filepath=str(work / "BelaGrace_headwear_native_candidate.blend"))
    fixtures = [
        ("rest", []),
        ("head_yaw_left", [("Head_0", (0, 0, 1), 30)]),
        ("head_yaw_right", [("Head_0", (0, 0, 1), -30)]),
        ("head_pitch_up", [("Head_0", (1, 0, 0), -20)]),
        ("head_pitch_down", [("Head_0", (1, 0, 0), 20)]),
        ("aim_surrogate", [("Spine_2", (0, 0, 1), 25), ("Neck_1", (0, 0, 1), -10),
                            ("Head_0", (0, 0, 1), -30), ("Head_0", (1, 0, 0), 10)]),
        ("aim_opposite", [("Spine_2", (0, 0, 1), -25), ("Neck_1", (0, 0, 1), 10),
                           ("Head_0", (0, 0, 1), 30), ("Head_0", (1, 0, 0), 10)]),
        ("neck_pitch", [("Neck_1", (1, 0, 0), 20), ("Head_0", (1, 0, 0), -15)]),
        ("ads_arms_raised", [("Spine_2", (0, 0, 1), 20), ("Head_0", (0, 0, 1), -25),
                             ("L_Arm_Upper", (1, 0, 0), 70), ("R_Arm_Upper", (1, 0, 0), 70),
                             ("L_Arm_Upper", (0, 0, 1), -40), ("R_Arm_Upper", (0, 0, 1), 40),
                             ("L_Arm_Lower", (1, 0, 0), -40), ("R_Arm_Lower", (1, 0, 0), -40)]),
        ("ads_shoulders_up", [("Spine_2", (0, 0, 1), 25), ("Head_0", (0, 0, 1), -35),
                              ("L_Arm_Clavicle", (0, 1, 0), -15), ("R_Arm_Clavicle", (0, 1, 0), 15),
                              ("L_Arm_Upper", (1, 0, 0), 80), ("R_Arm_Upper", (1, 0, 0), 80),
                              ("L_Arm_Upper", (0, 0, 1), -40), ("R_Arm_Upper", (0, 0, 1), 40)]),
        ("shoulder_right", [("R_Arm_Clavicle", (0, 1, 0), 25), ("Head_0", (0, 0, 1), -30)]),
        ("shoulder_left", [("L_Arm_Clavicle", (0, 1, 0), -25), ("Head_0", (0, 0, 1), 30)]),
        ("head_yaw_extreme_right", [("Head_0", (0, 0, 1), -50)]),
        ("head_yaw_extreme_left", [("Head_0", (0, 0, 1), 50)]),
    ]
    results = []
    # The rest mask deliberately excludes the front opening/forward locks.
    rear_faces = {}
    for obj in hair:
        points, faces = triangles(obj)
        p = np.asarray(points)
        rear_faces[obj.name] = [f for f in faces if -p[list(f), 1].mean() < .055]
    scene = bpy.context.scene
    scene.render.resolution_x = scene.render.resolution_y = 720
    scene.eevee.taa_render_samples = 16
    for name, rotations in fixtures:
        set_pose(rig, rotations)
        hood_points, hood_faces = triangles(outside[0], evaluated=True)
        tree = BVHTree.FromPolygons(hood_points, hood_faces, all_triangles=True)
        counts, full_counts = {}, {}
        for obj in hair:
            points, faces = triangles(obj, evaluated=True)
            p = np.asarray(points)
            if not np.isfinite(p).all() or np.abs(p).max() > 5:
                raise ValueError("Nonfinite/exploding headwear")
            hair_tree = BVHTree.FromPolygons(points, rear_faces[obj.name], all_triangles=True)
            overlaps = hair_tree.overlap(tree)
            counts[obj.name] = {"overlap_pairs": len(overlaps), "affected_hair_triangles": len({a for a, _ in overlaps})}
            full_tree = BVHTree.FromPolygons(points, faces, all_triangles=True)
            full_overlaps = full_tree.overlap(tree)
            ids = sorted({a for a, _ in full_overlaps})
            full_counts[obj.name] = {"overlap_pairs": len(full_overlaps), "affected_hair_triangles": len(ids),
                                    "triangle_ids": ids}
        results.append({"fixture": name, "rotations_degrees": rotations, "rear_card_overlap_diagnostics": counts,
                        "full_hair_overlap_diagnostics": full_counts})
        print(mode, name, "full hair:", {n: c["affected_hair_triangles"] for n, c in full_counts.items()}, flush=True)
        if args.render and name in {"rest", "aim_surrogate", "ads_arms_raised", "ads_shoulders_up"}:
            camera = scene.camera
            camera.data.ortho_scale = .72
            camera.location = (1.2, 4, 1.7)
            look_at(camera, (0, .0, 1.5))
            scene.render.filepath = str(output / f"{mode}_{name}_rear.png")
            bpy.ops.render.render(write_still=True)
            if name in {"rest", "ads_shoulders_up"}:
                camera.location = (1.2, -4, 1.7)
                look_at(camera, (0, .0, 1.5))
                scene.render.filepath = str(output / f"{mode}_{name}_front.png")
                bpy.ops.render.render(write_still=True)
    reset(rig)
    write_json(output / f"{mode}_diagnostics.json", {
        "status": "SYNTHETIC_DIAGNOSTICS_REQUIRES_VISUAL_REVIEW",
        "blender": bpy.app.version_string, "mode": mode, "fixtures": results,
        "native_input": args.native_input,
        "limits": "Not captured game ADS. BVH card overlaps ignore alpha and do not prove visible penetration or collision-free motion. Rear-only diagnostics exclude the front opening; full-hair diagnostics include every card.",
        "native_files_changed": False, "installed_build_changed": False})


if __name__ == "__main__":
    main()

