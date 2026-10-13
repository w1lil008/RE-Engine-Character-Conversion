"""Fit Bela to the original Grace rest rig and export RE9 prototype meshes.

Uses the existing RE Mesh Editor binary writer. This is an offline build, not
evidence of successful in-game rendering or animation.
"""
import copy
import json
import hashlib
from pathlib import Path
import numpy as np
from common import ROOT, reader, write_json
from analyze_assets import parsed_mesh
from rigging import bone_mapping, sanitize_weights, landmark_transform, fit_vertices, packed_tangents

OUTPUT = ROOT / "mod/BelaGrace_RE9"
REPORTS = ROOT / "reports"


def find_mesh(game, name):
    candidates = [p for p in (ROOT / f"assets/extracted/{game}").rglob(name + ".mesh.*") if "streaming" not in p.parts]
    if len(candidates) != 1:
        raise ValueError(f"Expected one mesh for {name}: {candidates}")
    return candidates[0]


def merge_skeleton(parts):
    skeleton = copy.deepcopy(parts[0].skeleton)
    bones, definitions = [], {}
    for part in parts:
        for b in part.skeleton.boneList:
            names = part.skeleton.boneList
            parent = names[b.parentIndex].boneName if b.parentIndex >= 0 else None
            if b.boneName in definitions:
                old, old_parent = definitions[b.boneName]
                if parent != old_parent or not np.allclose(old.worldMatrix.matrix, b.worldMatrix.matrix, atol=1e-5):
                    raise ValueError(f"Conflicting target bind definition: {b.boneName}")
            else:
                definitions[b.boneName] = (copy.deepcopy(b), parent)
    pending = dict(definitions)
    while pending:
        progressed = False
        for name, (bone, parent) in list(pending.items()):
            placed = {b.boneName: i for i, b in enumerate(bones)}
            if parent is None or parent in placed:
                bone.boneIndex = len(bones)
                bone.parentIndex = placed[parent] if parent else -1
                bone.nextSiblingIndex = bone.nextChildIndex = -1
                bones.append(bone)
                del pending[name]
                progressed = True
        if not progressed:
            raise ValueError("Target skeleton cycle or missing parent")
    by_name = {b.boneName: i for i, b in enumerate(bones)}
    for b in bones:
        twin = ("R_" + b.boneName[2:]) if b.boneName.startswith("L_") else (("L_" + b.boneName[2:]) if b.boneName.startswith("R_") else b.boneName)
        b.symmetryBoneIndex = by_name.get(twin, b.boneIndex)
        children = [c.boneIndex for c in bones if c.parentIndex == b.boneIndex]
        b.nextChildIndex = children[0] if children else -1
        for i, child in enumerate(children):
            bones[child].nextSiblingIndex = children[i + 1] if i + 1 < len(children) else -1
    skeleton.boneList = bones
    skeleton.weightedBones = []
    return skeleton


def retarget(source, target_skeleton, settings, mode):
    bones = source.skeleton.boneList
    target = {b.boneName: b for b in target_skeleton.boneList}
    mapping, methods = bone_mapping(bones, set(target), settings["bone_overrides"])
    by_source = {b.boneName: b for b in bones}
    ends = {"Spine_0": "Spine_1", "Spine_1": "Spine_2", "Spine_2": "Neck_0", "Neck_0": "Neck_1", "Neck_1": "Head"}
    for side in ["L", "R"]:
        for a, b in [("Shoulder", "UpperArm"), ("UpperArm", "Forearm"), ("Forearm", "Hand"),
                     ("Hand", "MiddleF1"), ("Thigh", "Shin"), ("Shin", "Foot"), ("Foot", "Toe")]:
            ends[f"{side}_{a}"] = f"{side}_{b}"
        for finger in ["Thumb", "IndexF", "MiddleF", "RingF", "PinkyF"]:
            ends[f"{side}_{finger}1"] = f"{side}_{finger}2"
            ends[f"{side}_{finger}2"] = f"{side}_{finger}3"
    anchors = set(ends) | set(ends.values()) | {"Hip", "root", "Head"}
    transforms, fit_audit = {}, {}
    for name, target_name in mapping.items():
        anchor = name
        # Keep the neutral facial likeness/hair shape intact in the first build.
        if methods[name].startswith("prototype_rigid_head"):
            anchor = "Head"
        if methods[name] == "prototype_rigid_skirt":
            anchor = "Hip"
        if methods[name] == "ancestor_fallback":
            b = by_source[name]
            while methods[b.boneName] == "ancestor_fallback" and b.parentIndex >= 0:
                b = bones[b.parentIndex]
            anchor = b.boneName
        if anchor not in anchors:
            b = by_source[anchor]
            while b.boneName not in anchors and b.parentIndex >= 0:
                b = bones[b.parentIndex]
            anchor = b.boneName
        target_anchor = mapping[anchor]
        end = ends.get(anchor)
        def origin(b):
            return np.asarray(b.worldMatrix.matrix)[3, :3]
        transforms[name] = landmark_transform(origin(by_source[anchor]), origin(target[target_anchor]),
                                             origin(by_source[end]) if end in by_source else None,
                                             origin(target[mapping[end]]) if end in by_source else None,
                                             settings["local_scale"])
        fitted_origin = (transforms[name] @ np.r_[origin(by_source[anchor]), 1])[:3]
        end_error = None
        if end in by_source:
            fitted_end = (transforms[name] @ np.r_[origin(by_source[end]), 1])[:3]
            end_error = float(np.linalg.norm(fitted_end - origin(target[mapping[end]])))
        fit_audit[name] = {"fit_anchor": anchor, "origin_error_m": float(np.linalg.norm(fitted_origin - origin(target[target_anchor]))),
                           "segment_end_error_m": end_error}
    result = copy.deepcopy(source)
    if mode == "face":
        # RE8 eye wetness/AO overlays require a different RE9 shader setup.
        # Exclude them from the first prototype so opaque placeholder shaders
        # cannot cover the eyeballs. Keep material indices stable.
        for lod in result.mainMeshLODList:
            for group in lod.visconGroupList:
                group.subMeshList = [s for s in group.subMeshList if source.materialNameList[s.materialIndex]
                                     not in {"shader_eyeWet_shader", "shader_eyeAO_shader"}]
    weighted = sorted({mapping[n] for n in source.skeleton.weightedBones}, key=lambda n: target[n].boneIndex)
    index = {n: i for i, n in enumerate(weighted)}
    for lod in result.mainMeshLODList:
        for group in lod.visconGroupList:
            for sub in group.subMeshList:
                old_indices, old_weights = sub.weightIndicesList, sub.weightList
                positions = fit_vertices(sub.vertexPosList, getattr(sub, "geometryWeightIndicesList", old_indices),
                                         getattr(sub, "geometryWeightList", old_weights),
                                         getattr(source.skeleton, "geometryWeightedBones", source.skeleton.weightedBones), transforms)
                if hasattr(sub, "restCorrectionList"):
                    positions += np.asarray(sub.restCorrectionList)
                new_weights, new_indices = [], []
                for indices, weights in zip(old_indices, old_weights):
                    pairs = sanitize_weights([(mapping[source.skeleton.weightedBones[i]], w) for i, w in zip(indices, weights)])
                    new_indices.append([index[n] for n, _ in pairs] + [index[pairs[-1][0]]] * (8 - len(pairs)))
                    new_weights.append([w for _, w in pairs] + [0.0] * (8 - len(pairs)))
                sub.vertexPosList = positions.tolist()
                # Recompute geometric normals after fitting, preserving tangent handedness.
                normals = np.zeros_like(positions)
                for f in sub.faceList:
                    n = np.cross(positions[f[1]] - positions[f[0]], positions[f[2]] - positions[f[0]])
                    normals[f] += n
                lens = np.linalg.norm(normals, axis=1)
                normals[lens > 1e-10] /= lens[lens > 1e-10, None]
                sub.normalList = normals.tolist()
                tangents = np.zeros_like(positions)
                bitangents = np.zeros_like(positions)
                uv = np.asarray(sub.uvList)
                for f in sub.faceList:
                    edge1, edge2 = positions[f[1]] - positions[f[0]], positions[f[2]] - positions[f[0]]
                    delta1, delta2 = uv[f[1]] - uv[f[0]], uv[f[2]] - uv[f[0]]
                    determinant = delta1[0] * delta2[1] - delta1[1] * delta2[0]
                    if abs(determinant) > 1e-10:
                        tangents[f] += (edge1 * delta2[1] - edge2 * delta1[1]) / determinant
                        bitangents[f] += (edge2 * delta1[0] - edge1 * delta2[0]) / determinant
                tangents -= normals * np.sum(normals * tangents, axis=1)[:, None]
                lengths = np.linalg.norm(tangents, axis=1)
                valid = lengths > 1e-10
                tangents[valid] /= lengths[valid, None]
                tangents[~valid] = np.asarray(sub.tangentList)[~valid, :3]
                signs = np.where(np.sum(np.cross(normals, tangents) * bitangents, axis=1) < 0, -1.0, 1.0)
                sub.tangentList = np.column_stack((tangents, signs)).tolist()
                sub.weightIndicesList, sub.weightList = new_indices, new_weights
                sub.isReusedMesh, sub.linkedSubMesh = False, None
    result.skeleton = copy.deepcopy(target_skeleton)
    result.skeleton.weightedBones = weighted
    result.shadowMeshLinkedLODList = []
    result.occlusionMeshLODList = []
    result.bufferHasExtraWeight = result.bufferHasSecondaryWeight = False
    return result, [{"source": n, "target": mapping[n], "method": methods[n], "weighted": n in source.skeleton.weightedBones, **fit_audit[n]}
                    for n in mapping]


def slice_submesh(sub, mask):
    faces = np.array(sub.faceList, dtype=int)[mask]
    if not len(faces):
        return None
    used = np.unique(faces)
    lookup = {old: new for new, old in enumerate(used)}
    result = copy.deepcopy(sub)
    result.faceList = [[lookup[i] for i in f] for f in faces]
    for attr in ["vertexPosList", "normalList", "tangentList", "uvList", "uv2List", "colorList", "weightList", "weightIndicesList"]:
        data = getattr(sub, attr)
        if data:
            setattr(result, attr, [data[i] for i in used])
    result.meshVertexOffset = 0
    result.isReusedMesh = False
    return result


def merge_meshes(first, second):
    """Combine geometry already bound to the same target rig, remapping palettes."""
    result = copy.deepcopy(first)
    order = {b.boneName: b.boneIndex for b in first.skeleton.boneList}
    weighted = sorted(set(first.skeleton.weightedBones) | set(second.skeleton.weightedBones), key=order.get)
    palette = {name: i for i, name in enumerate(weighted)}
    material_offset = len(first.materialNameList)
    if set(first.materialNameList) & set(second.materialNameList):
        raise ValueError("Combined meshes have ambiguous material names")
    result.materialNameList += second.materialNameList
    for lod_index, lod in enumerate(result.mainMeshLODList):
        for group in lod.visconGroupList:
            for sub in group.subMeshList:
                sub.weightIndicesList = [[palette[first.skeleton.weightedBones[i]] for i in row] for row in sub.weightIndicesList]
        addition = copy.deepcopy(second.mainMeshLODList[min(lod_index, len(second.mainMeshLODList) - 1)])
        group_offset = max(g.visconGroupNum for g in lod.visconGroupList) + 1
        for group in addition.visconGroupList:
            group.visconGroupNum += group_offset
            for sub in group.subMeshList:
                sub.materialIndex += material_offset
                sub.weightIndicesList = [[palette[second.skeleton.weightedBones[i]] for i in row] for row in sub.weightIndicesList]
        lod.visconGroupList += addition.visconGroupList
    result.skeleton.weightedBones = weighted
    return result


def apply_clothing_weights(source, path, settings):
    data = json.loads((ROOT / settings["clothing_weight_file"]).read_text())
    if (settings.get("skirt_weight_regularization") and
            settings["clothing_weight_file"] != settings.get("clothing_surface_weight_file")):
        for key, setting in [("parameters", "skirt_weight_regularization"),
                             ("garment_surface_smoothing", "garment_surface_smoothing"), ("garment_clearance", "garment_clearance")]:
            if data.get("regularization", {}).get(key) != settings.get(setting):
                raise ValueError("Clothing preparation parameters changed; regenerate the Prepare stage")
    if hashlib.sha256(path.read_bytes()).hexdigest() != data["clothing_sha256"]:
        raise ValueError("Clothing transfer input changed; regenerate weights")
    if hashlib.sha256(find_mesh("re8", settings["source_body"]).read_bytes()).hexdigest() != data["body_sha256"]:
        raise ValueError("Body transfer input changed; regenerate weights")
    palette = sorted({n for row in data["submeshes"] for pairs in row["weights"] for n, w in pairs})
    indices = {n: i for i, n in enumerate(palette)}
    source.skeleton.geometryWeightedBones = list(source.skeleton.weightedBones)
    for row in data["submeshes"]:
        sub = source.mainMeshLODList[row["lod"]].visconGroupList[row["group"]].subMeshList[row["sub"]]
        if source.materialNameList[sub.materialIndex] != row["material"] or len(sub.vertexPosList) != len(row["weights"]):
            raise ValueError("Clothing transfer topology changed")
        sub.geometryWeightIndicesList = copy.deepcopy(sub.weightIndicesList)
        sub.geometryWeightList = copy.deepcopy(sub.weightList)
        sub.restCorrectionList = row["rest_corrections"]
        sub.weightIndicesList = [[indices[n] for n, w in pairs] + [0] * (8 - len(pairs)) for pairs in row["weights"]]
        sub.weightList = [[w for n, w in pairs] + [0] * (8 - len(pairs)) for pairs in row["weights"]]
    source.skeleton.weightedBones = palette


def fit_footwear_floor(mesh, original_lower):
    """Keep Grace's ankle pivots and bring heel tips to her original sole plane.

    High-heel bone height differs from Grace's boots. Compressing the geometry
    below the ankle is a visual compromise; it does not change runtime IK bones.
    """
    floor = min(v[1] for g in original_lower.mainMeshLODList[0].visconGroupList for s in g.subMeshList for v in s.vertexPosList)
    bones = {b.boneName: b for b in mesh.skeleton.boneList}
    # Determine side from actual bone position rather than assuming L means -X.
    records = []
    for side in ["L", "R"]:
        anchor = np.asarray(bones[f"{side}_Leg_Foot"].worldMatrix.matrix)[3, :3]
        negative = anchor[0] < 0
        minimum = min(v[1] for lod in mesh.mainMeshLODList for g in lod.visconGroupList for s in g.subMeshList
                      if mesh.materialNameList[s.materialIndex] == "Heel_Mat" for v in s.vertexPosList if (v[0] < 0) == negative)
        scale = (anchor[1] - floor) / (anchor[1] - minimum)
        if not 0 < scale <= 1:
            raise ValueError("Unexpected footwear floor correction; inspect original bind pose")
        for lod in mesh.mainMeshLODList:
            for group in lod.visconGroupList:
                for sub in group.subMeshList:
                    points = np.asarray(sub.vertexPosList)
                    mask = ((points[:, 0] < 0) == negative) & (points[:, 1] < anchor[1])
                    points[mask, 1] = anchor[1] + scale * (points[mask, 1] - anchor[1])
                    sub.vertexPosList = points.tolist()
                    normals, tangents = np.asarray(sub.normalList), np.asarray(sub.tangentList)
                    normals[mask, 1] /= scale
                    tangents[mask, 1] *= scale
                    normals[mask] /= np.maximum(np.linalg.norm(normals[mask], axis=1)[:, None], 1e-10)
                    tangents[mask, :3] /= np.maximum(np.linalg.norm(tangents[mask, :3], axis=1)[:, None], 1e-10)
                    sub.normalList, sub.tangentList = normals.tolist(), tangents.tolist()
        records.append({"side": side, "original_Grace_floor_y": floor, "ankle_y_preserved": float(anchor[1]),
                        "heel_min_before_y": minimum, "heel_min_after_y": floor, "vertical_scale_below_ankle": float(scale)})
    write_json(REPORTS / "footwear_fit.json", {"method": "geometry_compression_below_preserved_Grace_ankle",
               "changes_runtime_skeleton": False, "authentic_high_heel_silhouette_preserved": False, "sides": records})


def use_original_boots(body, original_lower, settings):
    removed = 0
    for lod in body.mainMeshLODList:
        for group in lod.visconGroupList:
            kept = []
            for sub in group.subMeshList:
                material = body.materialNameList[sub.materialIndex]
                if material == "Heel_Mat":
                    removed += len(sub.faceList)
                    continue
                if material == "Body_Mat":
                    centres = np.asarray(sub.vertexPosList)[np.asarray(sub.faceList)].mean(axis=1)
                    mask = centres[:, 1] >= settings["boot_coverage_cutoff_y"]
                    removed += int(np.count_nonzero(~mask))
                    sub = slice_submesh(sub, mask)
                if sub:
                    kept.append(sub)
            group.subMeshList = kept
        lod.visconGroupList = [g for g in lod.visconGroupList if g.subMeshList]
    boots = copy.deepcopy(original_lower)
    selected_names = [name for name in original_lower.materialNameList if "_Boots_" in name]
    if not selected_names:
        raise ValueError("Original Grace lower mesh has no boot materials")
    for lod in boots.mainMeshLODList:
        for group in lod.visconGroupList:
            group.subMeshList = [s for s in group.subMeshList if original_lower.materialNameList[s.materialIndex] in selected_names]
            for sub in group.subMeshList:
                sub.materialIndex = selected_names.index(original_lower.materialNameList[sub.materialIndex])
                sub.isReusedMesh, sub.linkedSubMesh = False, None
                tangents = np.asarray(sub.tangentList)
                if tangents.shape[1] == 3:
                    positions, uv = np.asarray(sub.vertexPosList), np.asarray(sub.uvList)
                    bitangents = np.zeros_like(positions)
                    for f in sub.faceList:
                        e1, e2 = positions[f[1]] - positions[f[0]], positions[f[2]] - positions[f[0]]
                        u1, u2 = uv[f[1]] - uv[f[0]], uv[f[2]] - uv[f[0]]
                        determinant = u1[0] * u2[1] - u1[1] * u2[0]
                        if abs(determinant) > 1e-10:
                            bitangents[f] += (e2 * u1[0] - e1 * u2[0]) / determinant
                    signs = np.where(np.sum(np.cross(np.asarray(sub.normalList), tangents) * bitangents, axis=1) < 0, -1.0, 1.0)
                    sub.tangentList = np.column_stack((tangents, signs)).tolist()
        lod.visconGroupList = [g for g in lod.visconGroupList if g.subMeshList]
    boots.materialNameList = selected_names
    boots.shadowMeshLinkedLODList = []
    boots.occlusionMeshLODList = []
    boots.bufferHasExtraWeight = boots.bufferHasSecondaryWeight = False
    result = merge_meshes(body, boots)
    write_json(REPORTS / "footwear_fit.json", {"method": "original_Grace_boot_geometry_weights_and_materials",
               "changes_runtime_skeleton": False, "Bela_high_heels_ported": False,
               "original_Grace_floor_y": min(v[1] for g in boots.mainMeshLODList[0].visconGroupList for s in g.subMeshList for v in s.vertexPosList),
               "removed_Bela_triangles": removed, "boot_materials": selected_names,
               "coverage_cutoff_y": settings["boot_coverage_cutoff_y"],
               "limits": "Functional footwear fallback; original Bela heels need their own pose/IK solution."})
    return result


def split_body(body, part, height):
    result = copy.deepcopy(body)
    for lod in result.mainMeshLODList:
        for group in lod.visconGroupList:
            selected = []
            for sub in group.subMeshList:
                name = body.materialNameList[sub.materialIndex]
                centers = np.array(sub.vertexPosList)[np.array(sub.faceList)].mean(axis=1)
                if part in ["negative_x_hand", "positive_x_hand"]:
                    mask = ((centers[:, 0] < 0) if part == "negative_x_hand" else (centers[:, 0] >= 0)) & (name == "Gloves_Mat")
                elif part == "upper":
                    mask = (centers[:, 1] >= height) & (name != "Gloves_Mat")
                else:
                    mask = (centers[:, 1] < height) & (name != "Gloves_Mat")
                sliced = slice_submesh(sub, mask)
                if sliced:
                    selected.append(sliced)
            group.subMeshList = selected
        lod.visconGroupList = [g for g in lod.visconGroupList if g.subMeshList]
    return result


def bounds_and_bones(mesh, module):
    positions = np.array([v for lod in mesh.mainMeshLODList for g in lod.visconGroupList for s in g.subMeshList for v in s.vertexPosList])
    minimum, maximum = positions.min(axis=0), positions.max(axis=0)
    for axis, value in zip("xyz", minimum):
        setattr(mesh.boundingBox.min, axis, float(value))
    for axis, value in zip("xyz", maximum):
        setattr(mesh.boundingBox.max, axis, float(value))
    center = (minimum + maximum) * .5
    for axis, value in zip("xyz", center):
        setattr(mesh.boundingSphere, axis, float(value))
    mesh.boundingSphere.r = float(np.max(np.linalg.norm(positions - center, axis=1)))
    for bone in mesh.skeleton.boneList:
        if bone.boneName in mesh.skeleton.weightedBones:
            # Conservative global bind AABB avoids dropping deformed extremities.
            bone.boundingBox = copy.deepcopy(mesh.boundingBox)
    return len(positions)


def main():
    settings = json.loads((ROOT / "config/prototype.json").read_text())
    module = reader("RE-Mesh-Editor", "remesh", "modules.mesh.file_re_mesh")
    rig = merge_skeleton([parsed_mesh(find_mesh("re9", name))[1] for name in settings["target_rig_parts"]])
    converted, mappings = {}, {}
    for part in ["body", "clothing", "face", "hair"]:
        source_path = find_mesh("re8", settings["source_" + part])
        _, source = parsed_mesh(source_path)
        if part == "clothing":
            apply_clothing_weights(source, source_path, settings)
            for lod in source.mainMeshLODList:
                for group in lod.visconGroupList:
                    group.subMeshList = [s for s in group.subMeshList if source.materialNameList[s.materialIndex]
                                         not in settings["excluded_clothing_materials"]]
        converted[part], mappings[part] = retarget(source, rig, settings, part)
    if settings.get("footwear_fit") == "compress_below_Grace_ankle_to_original_floor":
        fit_footwear_floor(converted["body"], parsed_mesh(find_mesh("re9", "ch0200_50_00"))[1])
    elif settings.get("footwear_fit") == "original_Grace_boots":
        converted["body"] = use_original_boots(converted["body"], parsed_mesh(find_mesh("re9", "ch0200_50_00"))[1], settings)
    converted["body"] = merge_meshes(converted["body"], converted["clothing"])
    outputs, partition_counts = [], {}
    def triangle_count(mesh):
        return sum(len(s.faceList) for g in mesh.mainMeshLODList[0].visconGroupList for s in g.subMeshList)
    for part, names in settings["target_meshes"].items():
        mesh = converted[part] if part in ["face", "hair"] else split_body(converted["body"], part, settings["split_height"])
        if part not in ["face", "hair"]:
            partition_counts[part] = triangle_count(mesh)
        vertex_count = bounds_and_bones(mesh, module)
        for name in names:
            target = find_mesh("re9", name)
            relative = target.relative_to(ROOT / "assets/extracted/re9")
            path = OUTPUT / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            export_mesh = copy.deepcopy(mesh)
            for lod in export_mesh.mainMeshLODList:
                for group in lod.visconGroupList:
                    for sub in group.subMeshList:
                        sub.weightList = np.asarray(sub.weightList, dtype=float)
                        sub.weightIndicesList = np.asarray(sub.weightIndicesList, dtype=np.uint16)
                        sub.tangentList = packed_tangents(sub.tangentList)
            raw = module.ParsedREMeshToREMesh(export_mesh, 250925211)
            module.writeREMesh(raw, str(path))
            # Reopen output using the independent parse stage, catching bad tables.
            _, check = parsed_mesh(path)
            if check.materialNameList != mesh.materialNameList:
                raise ValueError("Material names did not survive binary round trip")
            outputs.append({"part": part, "path": str(path.relative_to(ROOT)), "vertices": vertex_count,
                            "materials": mesh.materialNameList, "target_bones": len(rig.boneList)})
    write_json(REPORTS / "bone_mapping.json", mappings)
    source_triangles = triangle_count(converted["body"])
    if sum(partition_counts.values()) != source_triangles:
        raise ValueError("Body segmentation lost or duplicated source triangles")
    write_json(REPORTS / "segmentation.json", {"source_body_and_clothing_triangles_lod0": source_triangles,
               "unique_output_part_triangles": partition_counts, "all_triangles_partitioned_once": True,
               "notes": ["Original body cutouts under the clothing are intentional.",
                         "Upper/lower split duplicates shared seam vertices without changing their fitted coordinates.",
                         "Alternative outfit and hair filenames duplicate geometry for asset routing, not simultaneous assembly.",
                         "Joint landmark error is a positioning check; mesh boundaries alone are not.",
                         "No claim that seams remain closed through every animation or that clipping is absent."]})
    write_json(REPORTS / "mesh_build.json", {"status": "OFFLINE_BINARY_ROUNDTRIP_ONLY", "outputs": outputs})
    print(f"Built {len(outputs)} RE9 mesh replacements. No in-game test performed.")


if __name__ == "__main__":
    main()

