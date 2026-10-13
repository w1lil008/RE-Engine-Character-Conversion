"""Compare weight diffusion and explicit clearance on a retained field baseline."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import numpy as np
from mathutils import Quaternion, Vector
from common import ROOT, write_json
from blender_scene import look_at
from rigging import sanitize_weights


def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "assets/work/BelaGrace_field_baseline.blend"))
    scene = bpy.context.scene
    rig = bpy.data.objects["GraceOriginalBindRig"]
    skirts = [o for o in bpy.data.collections["Bela_on_Grace_Prototype"].objects
              if o.type == "MESH" and o.data.materials[0].name.split(".")[0] in {"Dress_Mat", "DressBack_Mat"}]
    names = sorted({o.vertex_groups[g.group].name for o in skirts for v in o.data.vertices for g in v.groups})
    palette = {n: i for i, n in enumerate(names)}
    points, originals, lookups, node_lookup, edges = [], [], {}, {}, []
    for obj in skirts:
        mapping = []
        for v in obj.data.vertices:
            key = tuple(np.rint(np.asarray(v.co) / .00005).astype(int))
            if key not in node_lookup:
                node_lookup[key] = len(points)
                points.append(v.co[:])
                originals.append([])
            node = node_lookup[key]
            row = np.zeros(len(names))
            for group in v.groups:
                row[palette[obj.vertex_groups[group.group].name]] = group.weight
            originals[node].append(row)
            mapping.append(node)
        edges += [(mapping[e.vertices[0]], mapping[e.vertices[1]]) for e in obj.data.edges]
        lookups[obj.name] = mapping
    points = np.asarray(points)
    weights = np.asarray([np.mean(rows, axis=0) for rows in originals])
    edges = np.unique(np.sort(np.asarray(edges), axis=1), axis=0)
    edges = edges[edges[:, 0] != edges[:, 1]]
    a = np.r_[edges[:, 0], edges[:, 1]]
    b = np.r_[edges[:, 1], edges[:, 0]]
    degree = np.bincount(a, minlength=len(points)).clip(1)
    hip = rig.data.bones["Hip"].head_local.z
    mask = np.clip((hip + .02 - points[:, 2]) / .15, 0, 1)[:, None]
    candidates, current = {0: weights}, weights.copy()
    for iteration in range(1, 41):
        neighbour = np.zeros_like(current)
        np.add.at(neighbour, a, current[b])
        current += .5 * mask * (neighbour / degree[:, None] - current)
        if iteration == 40:
            candidates[iteration] = current.copy()
    fixtures = [
        ("rest", [], (0, -5, 1.4)),
        ("stride", [("L_Leg_Upper", (1, 0, 0), -.55), ("L_Leg_Lower", (1, 0, 0), .6),
                     ("R_Leg_Upper", (1, 0, 0), .35), ("R_Leg_Lower", (1, 0, 0), .35)], (2.5, -5, 1.4)),
        ("abduction", [("L_Leg_Upper", (0, 1, 0), -.35), ("R_Leg_Upper", (0, 1, 0), .35)], (0, -5, 1.4)),
        ("flex_rear", [("L_Leg_Upper", (1, 0, 0), -.65), ("R_Leg_Upper", (1, 0, 0), -.65),
                       ("L_Leg_Lower", (1, 0, 0), 1.1), ("R_Leg_Lower", (1, 0, 0), 1.1)], (0, 5, 1.4)),
        ("crouch_side", [("L_Leg_Upper", (1, 0, 0), -1.1), ("R_Leg_Upper", (1, 0, 0), -1.1),
                         ("L_Leg_Lower", (1, 0, 0), 1.8), ("R_Leg_Lower", (1, 0, 0), 1.8)], (5, 0, 1.4)),
    ]
    out = ROOT / "reports/skirt_smoothing"
    out.mkdir(parents=True, exist_ok=True)
    scene.render.resolution_x = scene.render.resolution_y = 900
    scene.eevee.taa_render_samples = 24
    scene.camera.data.ortho_scale = 1.9
    results = []
    original_positions = {obj.name: np.asarray([v.co[:] for v in obj.data.vertices]) for obj in skirts}
    variants = [(40, .025), (40, .045)]
    for iteration, clearance in variants:
        candidate = candidates[iteration]
        for obj in skirts:
            for vertex, position in zip(obj.data.vertices, original_positions[obj.name]):
                delta = position.copy()
                radius = np.array([position[0], position[1]])
                length = np.linalg.norm(radius)
                rise = np.clip((position[2] - .60) / .20, 0, 1)
                fall = np.clip((1.02 - position[2]) / .14, 0, 1)
                band = min(rise, fall)
                band = band*band*(3-2*band)
                if length > .02:
                    delta[:2] += radius/length * clearance * band
                vertex.co = delta
            obj.data.update()
            obj.vertex_groups.clear()
            groups = {n: obj.vertex_groups.new(name=n) for n in names}
            for vi, node in enumerate(lookups[obj.name]):
                for name, weight in sanitize_weights(list(zip(names, candidate[node]))):
                    groups[name].add([vi], weight, "REPLACE")
        for fixture, rotations, camera_position in fixtures:
            for pb in rig.pose.bones:
                pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = Quaternion()
            for bone, axis, angle in rotations:
                pb = rig.pose.bones[bone]
                local = pb.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
                pb.rotation_quaternion = Quaternion(local.normalized(), angle)
            bpy.context.view_layer.update()
            scene.camera.location = camera_position
            look_at(scene.camera, (0, 0, .8))
            scene.render.filepath = str(out / f"diffusion_{iteration}_clearance_{int(clearance*1000)}_{fixture}.png")
            bpy.ops.render.render(write_still=True)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            measurements = []
            for obj in skirts:
                evaluated = obj.evaluated_get(depsgraph)
                data = evaluated.to_mesh()
                posed = np.asarray([v.co[:] for v in data.vertices])
                rest = np.asarray([v.co[:] for v in obj.data.vertices])
                geometry_edges = np.asarray([e.vertices[:] for e in obj.data.edges])
                lengths = np.linalg.norm(rest[geometry_edges[:, 0]] - rest[geometry_edges[:, 1]], axis=1)
                valid = lengths > .0001
                ratio = np.linalg.norm(posed[geometry_edges[:, 0]]-posed[geometry_edges[:, 1]], axis=1)[valid] / lengths[valid]
                measurements.append({"object": obj.name, "edge_ratio_p01": float(np.quantile(ratio, .01)), "edge_ratio_p99": float(np.quantile(ratio, .99))})
                evaluated.to_mesh_clear()
            results.append({"iterations": iteration, "clearance_m": clearance, "fixture": fixture, "measurements": measurements})
    write_json(ROOT / "reports/skirt_smoothing.json", {"status": "EXPERIMENT_ONLY", "merged_weight_nodes": len(points),
               "geometry_welded": False, "results": results})


if __name__ == "__main__":
    main()

