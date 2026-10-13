"""Smooth a long garment's lower weight field without altering rest geometry.

Bone families and the vertical axis are adapter inputs. The field is a static
skinning approximation, not cloth simulation, collision or animation retargeting.
"""
import numpy as np
from rigging import sanitize_weights


def smoothstep(value):
    value = float(np.clip(value, 0, 1))
    return value * value * (3 - 2 * value)


def lower_garment_weights(point, pairs, hip_height, knee_height, parameters,
                         hip_name="Hip", upper_names=("L_Leg_Upper", "R_Leg_Upper"),
                         lower_names=("L_Leg_Lower", "R_Leg_Lower"),
                         leg_prefixes=("L_Leg_", "R_Leg_"), vertical_axis=1):
    point = np.asarray(point, dtype=float)
    if point.shape != (3,) or not np.isfinite(point).all():
        raise ValueError("Garment point must be a finite 3-vector")
    if not 0 <= parameters["knee_max"] <= 1:
        raise ValueError("Knee contribution must be between zero and one")
    for key in ("hip_width", "knee_width", "side_width", "transition_width"):
        if parameters[key] <= 0:
            raise ValueError(f"{key} must be positive")
    height = point[vertical_axis]
    graft = smoothstep((knee_height + parameters["transition_offset"] - height) / parameters["transition_width"])
    if graft < 1e-8:
        return sanitize_weights(pairs)
    is_leg = lambda name: name == hip_name or name.startswith(leg_prefixes)
    fraction = sum(w for n, w in pairs if is_leg(n))
    if fraction <= 1e-8:
        return sanitize_weights(pairs)
    hip = 1 - .95 * smoothstep((hip_height - height) / parameters["hip_width"])
    knee = parameters["knee_max"] * smoothstep((knee_height + parameters["knee_offset"] - height) / parameters["knee_width"])
    left = smoothstep((point[0] + parameters["side_width"] / 2) / parameters["side_width"])
    field = [(hip_name, hip)]
    for index, factor in [(0, left), (1, 1-left)]:
        field += [(upper_names[index], (1-hip)*(1-knee)*factor),
                  (lower_names[index], (1-hip)*knee*factor)]
    replacement = [(n, w) for n, w in pairs if not is_leg(n)] + [(n, w*fraction) for n, w in field]
    return sanitize_weights([(n, w*(1-graft)) for n, w in pairs] + [(n, w*graft) for n, w in replacement])

