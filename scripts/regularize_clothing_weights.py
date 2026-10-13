"""Apply the reviewed lower-skirt field to the reproducible source sidecar.

The surface-transfer sidecar and original geometry fitting weights stay intact.
The active sidecar records runtime weight changes and explicit garment clearance
added to the existing pelvis displacement correction.
"""
import json
import hashlib
from common import ROOT, write_json
from analyze_assets import parsed_mesh
from build_meshes import find_mesh, merge_skeleton, retarget, apply_clothing_weights
from garment_weights import lower_garment_weights
from garment_surface import diffuse_weights, clearance_offset
from rigging import bone_mapping
import numpy as np


def main():
    settings = json.loads((ROOT / "config/prototype.json").read_text())
    input_path = ROOT / settings["clothing_surface_weight_file"]
    data = json.loads(input_path.read_text())
    cloth_path = find_mesh("re8", settings["source_clothing"])
    _, cloth = parsed_mesh(cloth_path)
    rig = merge_skeleton([parsed_mesh(find_mesh("re9", n))[1] for n in settings["target_rig_parts"]])
    raw_settings = dict(settings, clothing_weight_file=settings["clothing_surface_weight_file"])
    apply_clothing_weights(cloth, cloth_path, raw_settings)
    fitted, _ = retarget(cloth, rig, raw_settings, "clothing")
    bones = {b.boneName: b for b in rig.boneList}
    hip = bones["Hip"].worldMatrix.matrix[3][1]
    knee = bones["L_Leg_Lower"].worldMatrix.matrix[3][1]
    modified = 0
    parameters = settings["skirt_weight_regularization"]
    positions, faces, weight_rows, row_ranges = [], [], [], []
    for row in data["submeshes"]:
        if row["material"] not in {"Dress_Mat", "DressBack_Mat"}:
            continue
        fitted_sub = fitted.mainMeshLODList[row["lod"]].visconGroupList[row["group"]].subMeshList[row["sub"]]
        if len(fitted_sub.vertexPosList) != len(row["weights"]):
            raise ValueError("Garment topology changed")
        updated = []
        for point, pairs in zip(fitted_sub.vertexPosList, row["weights"]):
            value = lower_garment_weights(point, pairs, hip, knee, parameters,
                       upper_names=("L_Thigh", "R_Thigh"), lower_names=("L_Shin", "R_Shin"),
                       leg_prefixes=("L_Thigh", "R_Thigh", "L_Shin", "R_Shin", "L_Foot", "R_Foot", "L_Toe", "R_Toe"))
            if dict(value) != dict(pairs):
                modified += 1
            updated.append(value)
        row["weights"] = updated
        offset = len(positions)
        positions += fitted_sub.vertexPosList
        faces += [[index + offset for index in face] for face in fitted_sub.faceList]
        weight_rows += updated
        row_ranges.append((row, offset, len(updated)))
    mapping, methods = bone_mapping(cloth.skeleton.boneList, set(bones), settings["bone_overrides"])
    canonical = {}
    rank = {"explicit": 0, "exact_name": 1, "anatomical_alias": 2, "ancestor_fallback": 3,
            "prototype_rigid_skirt": 4, "prototype_rigid_head": 4}
    for source, target in sorted(mapping.items(), key=lambda pair: (rank[methods[pair[0]]], pair[0])):
        canonical.setdefault(target, source)
    named = [[(mapping[n], w) for n, w in row] for row in weight_rows]
    smoothing = settings["garment_surface_smoothing"]
    smoothed, smoothing_stats = diffuse_weights(positions, faces, named, smoothing["iterations"],
         hip + smoothing["freeze_offset_from_hip"], smoothing["fade_width"], quantum=smoothing["quantization_m"])
    maximum_clearance = 0.0
    for row, start, count in row_ranges:
        row["weights"] = [[(canonical[n], w) for n, w in values] for values in smoothed[start:start+count]]
        corrections = []
        for point, correction in zip(positions[start:start+count], row["rest_corrections"]):
            added = clearance_offset(point, settings["garment_clearance"])
            maximum_clearance = max(maximum_clearance, float(np.linalg.norm(added)))
            corrections.append((np.asarray(correction) + added).tolist())
        row["rest_corrections"] = corrections
    data["regularization"] = {"method": "preserve_pelvis_surface_weights_blend_lower_garment_field",
        "parameters": parameters, "surface_sidecar_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "geometry_weights_unchanged": True, "rest_corrections_unchanged": False,
        "garment_surface_smoothing": smoothing, "smoothing_stats": smoothing_stats,
        "garment_clearance": settings["garment_clearance"], "maximum_added_clearance_m": maximum_clearance}
    write_json(ROOT / settings["clothing_weight_file"], data)
    write_json(ROOT / "reports/clothing_regularization.json", {**data["regularization"], "modified_vertices": modified,
        "native_cloth_simulation": False, "status": "REQUIRES_NATIVE_EXPORT_AND_POSE_REVIEW"})
    print(f"Regularized lower garment weights; {smoothing['iterations']} diffusion steps; maximum added garment clearance {maximum_clearance*1000:.1f} mm.")


if __name__ == "__main__":
    main()

