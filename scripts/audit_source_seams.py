"""Trace coincident source skin vertices across segmentation through rest fitting.

This checks positional continuity without treating all mesh boundaries as holes.
Only body skin and head skin are compared; garment overlap is a separate issue.
"""
import json
import numpy as np
from common import ROOT, write_json
from build_meshes import find_mesh, merge_skeleton, retarget
from analyze_assets import parsed_mesh


def main():
    settings = json.loads((ROOT / "config/prototype.json").read_text())
    rig = merge_skeleton([parsed_mesh(find_mesh("re9", n))[1] for n in settings["target_rig_parts"]])
    buckets = {}
    tolerance = 0.00005
    for part, material in [("body", "Body_Mat"), ("face", "shader_head_shader")]:
        _, source = parsed_mesh(find_mesh("re8", settings["source_" + part]))
        fitted, _ = retarget(source, rig, settings, part)
        for gi, group in enumerate(source.mainMeshLODList[0].visconGroupList):
            for si, sub in enumerate(group.subMeshList):
                if source.materialNameList[sub.materialIndex] != material:
                    continue
                candidates = [s for s in fitted.mainMeshLODList[0].visconGroupList[gi].subMeshList
                              if fitted.materialNameList[s.materialIndex] == material and len(s.vertexPosList) == len(sub.vertexPosList)]
                if len(candidates) != 1:
                    raise ValueError("Ambiguous skin submesh correspondence")
                output = candidates[0]
                for vi, (a, b) in enumerate(zip(sub.vertexPosList, output.vertexPosList)):
                    key = tuple(np.rint(np.asarray(a) / tolerance).astype(int))
                    buckets.setdefault(key, []).append({"part": part, "group": gi, "sub": si, "vertex": vi,
                                                        "source": a, "fitted": b})
    rows = []
    for entries in buckets.values():
        identities = {(e["part"], e["group"], e["sub"]) for e in entries}
        if len(identities) < 2:
            continue
        source = np.asarray([e["source"] for e in entries])
        fitted = np.asarray([e["fitted"] for e in entries])
        source_spread = float(np.max(np.linalg.norm(source[:, None] - source[None, :], axis=2)))
        fitted_spread = float(np.max(np.linalg.norm(fitted[:, None] - fitted[None, :], axis=2)))
        rows.append({"source_spread_m": source_spread, "fitted_spread_m": fitted_spread, "vertices": entries})
    rows.sort(key=lambda row: row["fitted_spread_m"], reverse=True)
    maximum = rows[0]["fitted_spread_m"] if rows else None
    write_json(ROOT / "reports/source_seam_audit.json", {"status": "NO_COINCIDENT_CANDIDATES" if not rows else
               ("REST_COINCIDENCE_PASSED" if maximum < .002 else "REST_SEAM_REVIEW_REQUIRED"),
               "source_quantization_m": tolerance, "coincident_cross_submesh_groups": len(rows),
               "maximum_fitted_spread_m": maximum, "worst_candidates": rows[:20], "all_candidates": rows,
               "limits": "Coincident skin vertices in rest fit only; no welding, no automatic hole detection, no pose or cloth-collision proof."})
    print(f"Skin seam candidates: {len(rows)}; maximum fitted positional spread: {maximum} metres.")


if __name__ == "__main__":
    main()

