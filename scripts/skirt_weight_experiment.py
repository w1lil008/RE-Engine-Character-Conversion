"""Compare broad skirt weight fields without changing the staged native build.

Experiments use the existing exported geometry. No cloth simulation is implied;
accepted fields must subsequently be exported and rechecked from native files.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import numpy as np
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree
from common import ROOT, write_json
from blender_scene import look_at


def smoothstep(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "assets/work/BelaGrace_surface_baseline.blend"))
    scene = bpy.context.scene
    rig = bpy.data.objects["GraceOriginalBindRig"]
    objects = [o for o in bpy.data.collections["Bela_on_Grace_Prototype"].objects if o.type == "MESH"]
    skirts = [o for o in objects if o.data.materials[0].name.split(".")[0] in {"Dress_Mat", "DressBack_Mat"}]
    original = {o.name: [[(o.vertex_groups[g.group].name, g.weight) for g in v.groups] for v in o.data.vertices] for o in skirts}
    hip_y = rig.data.bones["Hip"].head_local.z
    knee_y = rig.data.bones["L_Leg_Lower"].head_local.z
    models = [("baseline", None, .12), ("graft_knee_60", .60, .12), ("graft_knee_80", .80, .12)]
    fixtures = [("step", [("L_Leg_Upper", -.5), ("L_Leg_Lower", .8), ("L_Leg_Foot", -.2)]),
                ("flex", [("L_Leg_Upper", -.65), ("R_Leg_Upper", -.65), ("L_Leg_Lower", 1.1), ("R_Leg_Lower", 1.1)]),
                ("flex_rear", [("L_Leg_Upper", -.65), ("R_Leg_Upper", -.65), ("L_Leg_Lower", 1.1), ("R_Leg_Lower", 1.1)]),
                ("step_rear", [("L_Leg_Upper", -.5), ("L_Leg_Lower", .8), ("L_Leg_Foot", -.2)]),
                ("crouch_side", [("L_Leg_Upper", -1.1), ("R_Leg_Upper", -1.1), ("L_Leg_Lower", 1.8), ("R_Leg_Lower", 1.8)])]
    out = ROOT / "reports/skirt_experiments"
    out.mkdir(parents=True, exist_ok=True)
    scene.render.resolution_x = scene.render.resolution_y = 850
    scene.eevee.taa_render_samples = 24
    camera = scene.camera
    camera.data.ortho_scale = 1.9
    camera.location = (2.5, -5, 1.4)
    look_at(camera, (0, 0, .8))
    rows = []
    for label, knee_max, hip_width in models:
        for obj in skirts:
            obj.vertex_groups.clear()
            names = sorted({name for pairs in original[obj.name] for name, _ in pairs} |
                           {"Hip", "L_Leg_Upper", "R_Leg_Upper", "L_Leg_Lower", "R_Leg_Lower"})
            groups = {name: obj.vertex_groups.new(name=name) for name in names}
            for vertex, pairs in zip(obj.data.vertices, original[obj.name]):
                if knee_max is not None:
                    fraction = sum(w for n, w in pairs if n == "Hip" or n.startswith(("L_Leg_", "R_Leg_")))
                    if fraction > 1e-6:
                        keep = [(n, w) for n, w in pairs if n != "Hip" and not n.startswith(("L_Leg_", "R_Leg_"))]
                        hip = 1 - .95 * float(smoothstep((hip_y - vertex.co.z) / hip_width))
                        knee = knee_max * float(smoothstep((knee_y + .28 - vertex.co.z) / .60))
                        left = float(smoothstep((vertex.co.x + .16) / .32))
                        field = [("Hip", hip)]
                        for side, factor in [("L", left), ("R", 1-left)]:
                            field += [(f"{side}_Leg_Upper", (1-hip)*(1-knee)*factor),
                                      (f"{side}_Leg_Lower", (1-hip)*knee*factor)]
                        replacement = keep + [(n, w * fraction) for n, w in field]
                        graft = float(smoothstep((knee_y + .25 - vertex.co.z) / .32))
                        merged = {}
                        for n, w in [(n, w*(1-graft)) for n, w in pairs] + [(n, w*graft) for n, w in replacement]:
                            merged[n] = merged.get(n, 0) + w
                        pairs = list(merged.items())
                for name, weight in pairs:
                    if weight > 1e-7:
                        groups[name].add([vertex.index], weight, "REPLACE")
        for fixture, rotations in fixtures:
            for pb in rig.pose.bones:
                pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = Quaternion()
            for bone, angle in rotations:
                pb = rig.pose.bones[bone]
                axis = pb.bone.matrix_local.to_3x3().inverted() @ Vector((1, 0, 0))
                pb.rotation_quaternion = Quaternion(axis.normalized(), angle)
            bpy.context.view_layer.update()
            measurements = []
            depsgraph = bpy.context.evaluated_depsgraph_get()
            dress_points, dress_faces = [], []
            skin_samples = []
            for obj in objects:
                if obj.data.materials[0].name.split(".")[0] != "Body_Mat":
                    continue
                evaluated = obj.evaluated_get(depsgraph)
                data = evaluated.to_mesh()
                skin_samples += [v.co[:] for v, rest in zip(data.vertices, obj.data.vertices) if .35 < rest.co.z < hip_y - .10]
                evaluated.to_mesh_clear()
            for obj in skirts:
                evaluated = obj.evaluated_get(depsgraph)
                data = evaluated.to_mesh()
                posed = np.asarray([v.co[:] for v in data.vertices])
                rest = np.asarray([v.co[:] for v in obj.data.vertices])
                edges = np.asarray([e.vertices[:] for e in obj.data.edges])
                lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
                valid = lengths > .0001
                ratios = np.linalg.norm(posed[edges[:, 0]] - posed[edges[:, 1]], axis=1)[valid] / lengths[valid]
                measurements.append({"object": obj.name, "edge_ratio_p01": float(np.quantile(ratios, .01)),
                                     "edge_ratio_p99": float(np.quantile(ratios, .99)), "edge_ratio_max": float(ratios.max()),
                                     "bounds": [posed.min(0).tolist(), posed.max(0).tolist()]})
                if obj.data.materials[0].name.split(".")[0] == "Dress_Mat":
                    offset = len(dress_points)
                    dress_points += posed.tolist()
                    dress_faces += [[index+offset for index in p.vertices] for p in data.polygons]
                evaluated.to_mesh_clear()
            tree = BVHTree.FromPolygons(dress_points, dress_faces, all_triangles=True)
            distances = []
            for point in skin_samples:
                location, normal, _, _ = tree.find_nearest(Vector(point))
                distances.append(float((Vector(point)-location).dot(normal)))
            name = f"{label}_{fixture}"
            camera.location = (0, 5, 1.4) if "rear" in fixture else ((5, 0, 1.4) if "side" in fixture else (2.5, -5, 1.4))
            look_at(camera, (0, 0, .8))
            scene.render.filepath = str(out / f"{name}.png")
            bpy.ops.render.render(write_still=True)
            rows.append({"model": label, "fixture": fixture, "knee_max": knee_max, "hip_width": hip_width, "measurements": measurements,
                         "skin_samples": len(skin_samples), "skin_outside_nearest_dress_over_3mm": sum(d > .003 for d in distances),
                         "maximum_skin_outside_distance_m": max(distances),
                         "image": str((out / f"{name}.png").relative_to(ROOT))})
            print(f"Rendered {name}", flush=True)
    write_json(ROOT / "reports/skirt_experiments.json", {"status": "CANDIDATES_ONLY_NOT_NATIVE_EXPORTS", "models": rows,
               "limits": "Edge strain is diagnostic; it does not establish collision-free cloth or runtime compatibility."})


if __name__ == "__main__":
    main()

