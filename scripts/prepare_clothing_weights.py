"""Portable-Blender surface weight transfer for the RE8 skirt.

Replace only cloth-only skirt influences using barycentric weights from Bela's
underlying body. Other original clothing influences remain. This is an initial
skinned garment approximation, not a replacement for native cloth simulation.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import json
import hashlib
import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils import Vector
from common import ROOT, write_json
from build_meshes import find_mesh, merge_skeleton, retarget
from analyze_assets import parsed_mesh
from rigging import sanitize_weights, landmark_transform


def main():
    settings = json.loads((ROOT / "config/prototype.json").read_text())
    body_path = find_mesh("re8", settings["source_body"])
    cloth_path = find_mesh("re8", settings["source_clothing"])
    _, body = parsed_mesh(body_path)
    _, cloth = parsed_mesh(cloth_path)
    target_rig = merge_skeleton([parsed_mesh(find_mesh("re9", name))[1] for name in settings["target_rig_parts"]])
    fitted_body, _ = retarget(body, target_rig, settings, "body")
    vertices, fitted_vertices, faces, vertex_weights = [], [], [], []
    for group_index, group in enumerate(body.mainMeshLODList[0].visconGroupList):
        for sub_index, sub in enumerate(group.subMeshList):
            if body.materialNameList[sub.materialIndex] != "Body_Mat":
                continue
            offset = len(vertices)
            vertices += sub.vertexPosList
            fitted_vertices += fitted_body.mainMeshLODList[0].visconGroupList[group_index].subMeshList[sub_index].vertexPosList
            faces += [[i + offset for i in f] for f in sub.faceList]
            vertex_weights += [[(body.skeleton.weightedBones[i], w) for i, w in zip(indices, weights) if w > 0]
                               for indices, weights in zip(sub.weightIndicesList, sub.weightList)]
    points = np.asarray(vertices)
    fitted_points = np.asarray(fitted_vertices)
    source_hip = next(b for b in body.skeleton.boneList if b.boneName == "Hip")
    target_hip = next(b for b in target_rig.boneList if b.boneName == "Hip")
    hip_fit = landmark_transform(np.asarray(source_hip.worldMatrix.matrix)[3, :3],
                                np.asarray(target_hip.worldMatrix.matrix)[3, :3], radial_scale=settings["local_scale"])
    # Side-specific projection prevents abrupt left/right weight switching at
    # the skirt centre. A narrow centre band blends both body sides smoothly.
    sides = {}
    for side in [-1, 1]:
        selection = [f for f in faces if (points[f].mean(0)[0] < 0) == (side < 0)]
        sides[side] = (BVHTree.FromPolygons(vertices, selection, all_triangles=True), selection)

    def projected_weights(point, side):
        tree, triangles = sides[side]
        location, normal, index, distance = tree.find_nearest(Vector(point))
        if index is None:
            raise ValueError("No body surface for clothing transfer")
        face = triangles[index]
        a, b, c = points[face]
        v0, v1, v2 = b - a, c - a, np.asarray(location) - a
        d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
        denominator = d00 * d11 - d01 * d01
        if abs(denominator) < 1e-14:
            bary = np.eye(3)[np.argmin(np.linalg.norm(points[face] - location, axis=1))]
        else:
            v = (d11 * (v2 @ v0) - d01 * (v2 @ v1)) / denominator
            w = (d00 * (v2 @ v1) - d01 * (v2 @ v0)) / denominator
            bary = np.maximum([1 - v - w, v, w], 0)
            bary /= sum(bary)
        transferred = [(name, weight * fraction) for vertex, fraction in zip(face, bary)
                       for name, weight in vertex_weights[vertex]]
        fitted_surface = np.sum(fitted_points[face] * bary[:, None], axis=0)
        original_surface_fit = (hip_fit @ np.r_[np.asarray(location), 1])[:3]
        return transferred, fitted_surface - original_surface_fit

    rows, changed = [], 0
    for lod_index, lod in enumerate(cloth.mainMeshLODList):
        for group_index, group in enumerate(lod.visconGroupList):
            for sub_index, sub in enumerate(group.subMeshList):
                values, corrections = [], []
                for point, indices, weights in zip(sub.vertexPosList, sub.weightIndicesList, sub.weightList):
                    pairs = [(cloth.skeleton.weightedBones[i], w) for i, w in zip(indices, weights) if w > 0]
                    fraction = sum(w for n, w in pairs if n.startswith("skirt_"))
                    correction = np.zeros(3)
                    if fraction > 1e-6:
                        keep = [(n, w) for n, w in pairs if not n.startswith("skirt_")]
                        blend = float(np.clip((point[0] + .06) / .12, 0, 1))
                        transfer = []
                        for side, factor in [(-1, 1 - blend), (1, blend)]:
                            if factor > 1e-7:
                                projected, displacement = projected_weights(point, side)
                                transfer += [(n, w * factor * fraction) for n, w in projected]
                                # Follow the body's proportion change around the pelvis,
                                # fading to zero below it to preserve the original bell hem.
                                correction += displacement * factor * fraction * float(np.clip((point[1] - .55) / .45, 0, 1))
                        pairs = keep + transfer
                        changed += 1
                    values.append(sanitize_weights(pairs))
                    corrections.append(correction.tolist())
                rows.append({"lod": lod_index, "group": group_index, "sub": sub_index,
                             "material": cloth.materialNameList[sub.materialIndex], "weights": values, "rest_corrections": corrections})
    data = {"body_sha256": hashlib.sha256(body_path.read_bytes()).hexdigest(),
            "clothing_sha256": hashlib.sha256(cloth_path.read_bytes()).hexdigest(), "submeshes": rows}
    write_json(ROOT / settings["clothing_surface_weight_file"], data)
    write_json(ROOT / settings["clothing_weight_file"], data)
    write_json(ROOT / "reports/clothing_weights.json", {"method": "barycentric_body_surface_transfer_of_skirt_influences",
               "changed_vertices": changed, "centre_blend_width_m": .12, "native_cloth_simulation": False,
               "rest_geometry": "Original garment fitting weights retained; body displacement added near pelvis, faded out below",
               "status": "REQUIRES_POSE_AND_VISUAL_VALIDATION"})
    print(f"Transferred skirt influences on {changed} vertices; native cloth simulation remains pending.")


if __name__ == "__main__":
    main()

