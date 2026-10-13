"""Engine-independent skeleton matching, rest fitting and weight sanitation.

Matrices here use column vectors. RE Engine file matrices must be transposed
at the adapter boundary. Suggestions never imply animation compatibility.
"""
import numpy as np

CORE_ALIASES = {"Head": "Head_0", "Null_Offset": "root"}
for side in ["L", "R"]:
    for old, new in {"Shoulder": "Arm_Clavicle", "UpperArm": "Arm_Upper", "Forearm": "Arm_Lower",
                     "Hand": "Arm_Hand", "Palm": "Hand_Palm", "Thigh": "Leg_Upper", "Shin": "Leg_Lower",
                     "Foot": "Leg_Foot", "Toe": "Leg_Toes", "ToeEnd": "Leg_Toes"}.items():
        CORE_ALIASES[f"{side}_{old}"] = f"{side}_{new}"
    for old, new in {"UpperArm": "Arm_Upper", "Forearm": "Arm_Lower", "Thigh": "Leg_Upper", "Shin": "Leg_Lower"}.items():
        for i in range(4):
            CORE_ALIASES[f"{side}_{old}_Twist_{i}"] = f"{side}_{new}_Twist_{min(i, 2) if old == 'UpperArm' else i}"
    for finger in ["Thumb", "IndexF", "MiddleF", "RingF", "PinkyF"]:
        for i in range(1, 4):
            new = "ThumbF" if finger == "Thumb" else finger
            CORE_ALIASES[f"{side}_{finger}{i}"] = f"{side}_Hand_{new}_{i}"
    for old, new in {"trapA": "Trap_A", "latA": "Lat_A", "serratusA": "Serratus_A", "pecA": "Pec_A",
                     "pecB": "Pec_B", "deltFront": "Delt_Front_A", "deltBack": "Delt_Rear_A", "deltUp": "Delt_Side_A"}.items():
        CORE_ALIASES[f"{side}_{old}_muscle"] = f"{side}_{new}"
        CORE_ALIASES[f"{side}_{old}_muscleOffset"] = f"{side}_{new}Offset"


def bone_mapping(source_bones, target_names, overrides=None):
    overrides = overrides or {}
    mapping, methods = {}, {}
    for index, bone in enumerate(source_bones):
        name = bone.boneName
        if name in overrides:
            target, method = overrides[name], "explicit"
        elif name.startswith("FACIAL_") or name.startswith("Hair"):
            target, method = "Head_0", "prototype_rigid_head"
        elif name.startswith("skirt_"):
            target, method = "Hip", "prototype_rigid_skirt"
        elif name in target_names:
            target, method = name, "exact_name"
        elif name in CORE_ALIASES:
            target, method = CORE_ALIASES[name], "anatomical_alias"
        else:
            parent = bone.parentIndex
            target = mapping.get(source_bones[parent].boneName) if parent >= 0 else None
            method = "ancestor_fallback"
        if target not in target_names:
            raise ValueError(f"Unresolved bone {name}: candidate {target}")
        mapping[name], methods[name] = target, method
    return mapping, methods


def sanitize_weights(pairs, maximum=8, threshold=1e-7):
    combined = {}
    for bone, weight in pairs:
        if not np.isfinite(weight) or weight < 0:
            raise ValueError("Nonfinite or negative skin weight")
        if weight > threshold:
            combined[bone] = combined.get(bone, 0.0) + float(weight)
    ranked = sorted(combined.items(), key=lambda pair: (-pair[1], pair[0]))[:maximum]
    total = sum(weight for _, weight in ranked)
    if total <= threshold:
        raise ValueError("Vertex has no usable weights")
    return [(bone, weight / total) for bone, weight in ranked]


def fit_vertices(positions, indices, weights, source_names, transforms):
    positions = np.asarray(positions, dtype=float)
    homogeneous = np.column_stack((positions, np.ones(len(positions))))
    result = np.zeros_like(positions)
    for i in range(len(positions)):
        total = 0.0
        for bone_index, weight in zip(indices[i], weights[i]):
            if weight > 0:
                result[i] += weight * (transforms[source_names[bone_index]] @ homogeneous[i])[:3]
                total += weight
        if total <= 0:
            raise ValueError(f"Unweighted vertex {i}")
        result[i] /= total
    if not np.isfinite(result).all():
        raise ValueError("Rest fitting produced nonfinite coordinates")
    return result


def rest_transform(source_world, target_world, local_scale=1.0):
    scale = np.diag([local_scale, local_scale, local_scale, 1.0])
    return np.asarray(target_world) @ scale @ np.linalg.inv(np.asarray(source_world))


def packed_tangents(tangents):
    """RE Mesh Editor's writer requires prequantized XYZ and handedness bytes."""
    values = np.asarray(tangents, dtype=float)
    if values.ndim != 2 or values.shape[1] != 4 or not np.isfinite(values).all():
        raise ValueError("Tangents must be finite Nx4 direction/handedness values")
    if np.any(np.abs(values) > 1.01):
        raise ValueError("Tangents must be normalized before packing")
    return np.clip(np.rint(values * 127), -127, 127).astype(np.int8)


def landmark_transform(source_origin, target_origin, source_end=None, target_end=None, radial_scale=1.0):
    """Fit homologous anatomical segments without assuming compatible bone roll.

    Direction is derived from joint positions, not engine-specific joint axes.
    Length scales along the segment; radial_scale controls cross-section size.
    """
    source_origin, target_origin = np.asarray(source_origin), np.asarray(target_origin)
    linear = np.eye(3) * radial_scale
    if source_end is not None and target_end is not None:
        a, b = np.asarray(source_end) - source_origin, np.asarray(target_end) - target_origin
        alen, blen = np.linalg.norm(a), np.linalg.norm(b)
        if alen > 1e-5 and blen > 1e-5:
            a, b = a / alen, b / blen
            cross = np.cross(a, b)
            cosine = float(np.dot(a, b))
            skew = np.array([[0, -cross[2], cross[1]], [cross[2], 0, -cross[0]], [-cross[1], cross[0], 0]])
            if cosine < -.99999:
                axis = np.cross(a, [1, 0, 0] if abs(a[0]) < .8 else [0, 1, 0])
                axis /= np.linalg.norm(axis)
                rotation = 2 * np.outer(axis, axis) - np.eye(3)
            else:
                rotation = np.eye(3) + skew + skew @ skew / (1 + cosine)
            linear = rotation @ (radial_scale * np.eye(3) + (blen / alen - radial_scale) * np.outer(a, a))
    result = np.eye(4)
    result[:3, :3] = linear
    result[:3, 3] = target_origin - linear @ source_origin
    return result

