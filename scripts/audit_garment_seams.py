"""Measure rest-coincident exported garment vertices in the rendered fixtures.

This checks UV/asset boundary continuity. It does not classify all garment edges
as holes and cannot prove absence of self-intersection or body penetration.
"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import json
import numpy as np
from mathutils import Quaternion, Vector
from common import ROOT, write_json, confined


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", default="assets/work/BelaGrace_preparation.blend")
    parser.add_argument("--fixtures", default="reports/alignment_qa.json")
    parser.add_argument("--report", default="reports/garment_seam_audit.json")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    bpy.ops.wm.open_mainfile(filepath=str(confined(ROOT, args.scene)))
    rig = bpy.data.objects["GraceOriginalBindRig"]
    objects = [o for o in bpy.data.collections["Bela_on_Grace_Prototype"].objects if o.type == "MESH"
               and o.data.materials[0].name.split(".")[0] in {"Dress_Mat", "DressBack_Mat"}]
    buckets = {}
    for obj in objects:
        for vertex in obj.data.vertices:
            key = tuple(np.rint(np.asarray(vertex.co) / .00005).astype(int))
            buckets.setdefault(key, []).append((obj.name, vertex.index))
    groups = [r for r in buckets.values() if len(r) > 1]
    fixtures = json.loads(confined(ROOT, args.fixtures).read_text())["fixtures"]
    results = []
    for fixture in fixtures:
        for pb in rig.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion()
        for name, axis, angle in fixture["pose"]:
            pb = rig.pose.bones[name]
            local = pb.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
            pb.rotation_quaternion = Quaternion(local.normalized(), angle)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        posed = {}
        for obj in objects:
            evaluated = obj.evaluated_get(depsgraph)
            data = evaluated.to_mesh()
            posed[obj.name] = np.asarray([v.co[:] for v in data.vertices])
            evaluated.to_mesh_clear()
        rows = []
        for group in groups:
            points = np.asarray([posed[name][index] for name, index in group])
            spread = float(np.max(np.linalg.norm(points[:, None]-points[None, :], axis=2)))
            rows.append({"spread_m": spread, "references": group})
        rows.sort(key=lambda r: r["spread_m"], reverse=True)
        results.append({"fixture": fixture["name"], "maximum_spread_m": rows[0]["spread_m"] if rows else None,
                        "groups_above_2mm": sum(r["spread_m"] > .002 for r in rows), "worst_candidates": rows[:5]})
    passed = bool(groups) and not any(r["groups_above_2mm"] for r in results)
    write_json(confined(ROOT, args.report), {"status": "TESTED_GARMENT_CONTINUITY_PASSED" if passed else "POSED_GARMENT_SEAM_REVIEW_REQUIRED",
        "rest_coincident_groups": len(groups), "rest_quantization_m": .00005, "review_threshold_m": .002,
        "fixtures": results, "in_game_tested": False,
        "limits": "Exported rest-coincident vertices only; no automatic hole detection, collision or game-physics proof."})
    print(f"Garment continuity: {len(groups)} groups, {len(fixtures)} poses, maximum spread {max(r['maximum_spread_m'] for r in results)*1000:.3f} mm.")


if __name__ == "__main__":
    main()

