"""Measure known source-coincident skin boundaries on the exported Blender rig.

Uses evaluated native-export geometry, including quantized skin weights. Only
known source-coincident vertices are audited; garment edges are not auto-welded.
"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import json
import numpy as np
from mathutils import Vector, Quaternion
from mathutils.kdtree import KDTree
from common import ROOT, write_json, confined
from blender_scene import ROTATE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", default="assets/work/BelaGrace_preparation.blend")
    parser.add_argument("--report", default="reports/assembled_seam_audit.json")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    bpy.ops.wm.open_mainfile(filepath=str(confined(ROOT, args.scene)))
    rig = bpy.data.objects["GraceOriginalBindRig"]
    candidates = json.loads((ROOT / "reports/source_seam_audit.json").read_text())["all_candidates"]
    objects = [o for o in bpy.data.collections["Bela_on_Grace_Prototype"].objects if o.type == "MESH"]
    trees, references = {}, {}
    for part, material in [("body", "Body_Mat"), ("face", "shader_head_shader")]:
        selected = [o for o in objects if o.data.materials[0].name.split(".")[0] == material]
        points = [(o.name, v.index, o.matrix_world @ v.co) for o in selected for v in o.data.vertices]
        if not points:
            raise ValueError(f"Missing assembled skin material {material}")
        tree = KDTree(len(points))
        for index, (_, _, point) in enumerate(points):
            tree.insert(point, index)
        tree.balance()
        trees[part], references[part] = tree, points
    resolved = []
    maximum_lookup_error = 0
    for group in candidates:
        entries = []
        for row in group["vertices"]:
            query = ROTATE @ Vector(row["fitted"])
            _, index, distance = trees[row["part"]].find(query)
            maximum_lookup_error = max(maximum_lookup_error, distance)
            if distance > .000005:
                raise ValueError(f"Native scene no longer matches source audit: {distance} m")
            name, vertex, _ = references[row["part"]][index]
            entries.append({"object": name, "vertex": vertex, "source_part": row["part"]})
        resolved.append(entries)

    fixtures = [
        ("rest", []),
        ("neck_head_turn", [("Head_0", (0, 0, 1), .45), ("Neck_1", (1, 0, 0), .15)]),
        ("bilateral_arm_flex", [("L_Arm_Lower", (0, 1, 0), -.9), ("R_Arm_Lower", (0, 1, 0), .9),
                                 ("L_Arm_Hand", (0, 0, 1), .3), ("R_Arm_Hand", (0, 0, 1), -.3)]),
        ("shoulder_elbow_wrist_flex", [("L_Arm_Upper", (0, 1, 0), -.5), ("L_Arm_Lower", (0, 1, 0), -1),
                                       ("L_Arm_Hand", (0, 0, 1), .25)]),
        ("pelvis_knee_ankle_step", [("L_Leg_Upper", (1, 0, 0), -.5), ("L_Leg_Lower", (1, 0, 0), .8),
                                   ("L_Leg_Foot", (1, 0, 0), -.2)]),
        ("bilateral_leg_flex", [("L_Leg_Upper", (1, 0, 0), -.65), ("R_Leg_Upper", (1, 0, 0), -.65),
                                ("L_Leg_Lower", (1, 0, 0), 1.1), ("R_Leg_Lower", (1, 0, 0), 1.1)]),
    ]
    results = []
    for name, rotations in fixtures:
        for pb in rig.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion()
        for bone, axis, angle in rotations:
            pb = rig.pose.bones[bone]
            local_axis = pb.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
            pb.rotation_quaternion = Quaternion(local_axis.normalized(), angle)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated_points = {}
        for obj in objects:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            evaluated_points[obj.name] = np.asarray([tuple(evaluated.matrix_world @ v.co) for v in mesh.vertices])
            evaluated.to_mesh_clear()
        rows = []
        for entries in resolved:
            points = np.asarray([evaluated_points[e["object"]][e["vertex"]] for e in entries])
            spread = float(np.max(np.linalg.norm(points[:, None] - points[None, :], axis=2)))
            rows.append({"spread_m": spread, "references": entries})
        rows.sort(key=lambda r: r["spread_m"], reverse=True)
        maximum = rows[0]["spread_m"]
        results.append({"fixture": name, "pose": rotations, "maximum_spread_m": maximum,
                        "groups_above_2mm": sum(r["spread_m"] > .002 for r in rows), "worst_candidates": rows[:8]})
        print(f"{name}: maximum known skin-boundary spread {maximum * 1000:.3f} mm")
    write_json(confined(ROOT, args.report), {
        "status": "POSED_SEAM_REVIEW_REQUIRED" if any(r["groups_above_2mm"] for r in results) else "TESTED_SKIN_COINCIDENCE_PASSED",
        "source_groups": len(resolved), "native_vertex_lookup_max_error_m": maximum_lookup_error,
        "review_threshold_m": .002, "fixtures": results, "in_game_tested": False,
        "limits": "Known source-coincident skin boundaries only, limited synthetic poses. No automatic hole detection, cloth collision or runtime proof."})


if __name__ == "__main__":
    main()

