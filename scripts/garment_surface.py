"""Garment weight diffusion and explicit rest clearance, independent of formats."""
import numpy as np
from rigging import sanitize_weights


def diffuse_weights(positions, faces, rows, iterations, freeze_height, fade_width, vertical_axis=1, quantum=.00005):
    positions = np.asarray(positions, dtype=float)
    if fade_width <= 0 or quantum <= 0 or iterations < 0:
        raise ValueError("Invalid garment diffusion parameters")
    keys = np.rint(positions / quantum).astype(np.int64)
    _, first, mapping = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    points = positions[first]
    names = sorted({name for row in rows for name, _ in row})
    palette = {name: i for i, name in enumerate(names)}
    current = np.zeros((len(points), len(names)))
    counts = np.bincount(mapping, minlength=len(points)).clip(1)
    for vertex, row in enumerate(rows):
        for name, weight in row:
            current[mapping[vertex], palette[name]] += weight
    current /= counts[:, None]
    edges = np.unique(np.sort(np.asarray([(mapping[a], mapping[b]) for face in faces
                                        for a, b in zip(list(face), list(face)[1:] + list(face)[:1])]), axis=1), axis=0)
    edges = edges[edges[:, 0] != edges[:, 1]]
    a = np.r_[edges[:, 0], edges[:, 1]]
    b = np.r_[edges[:, 1], edges[:, 0]]
    raw_degree = np.bincount(a, minlength=len(points))
    degree = raw_degree.clip(1)
    mask = np.clip((freeze_height - points[:, vertical_axis]) / fade_width, 0, 1)[:, None]
    mask[raw_degree == 0] = 0
    for _ in range(iterations):
        neighbour = np.zeros_like(current)
        np.add.at(neighbour, a, current[b])
        current += .5 * mask * (neighbour / degree[:, None] - current)
    result = [sanitize_weights(list(zip(names, current[node]))) for node in mapping]
    return result, {"weight_nodes": len(points), "input_vertices": len(positions), "geometry_welded": False,
                    "iterations": iterations, "quantization_m": quantum}


def clearance_offset(point, settings, vertical_axis=1):
    point = np.asarray(point, dtype=float)
    rise = np.clip((point[vertical_axis] - settings["lower_start"]) / settings["lower_fade_width"], 0, 1)
    fall = np.clip((settings["upper_end"] - point[vertical_axis]) / settings["upper_fade_width"], 0, 1)
    band = min(rise, fall)
    band = band * band * (3 - 2 * band)
    axes = [i for i in range(3) if i != vertical_axis]
    radius = point[axes]
    length = np.linalg.norm(radius)
    offset = np.zeros(3)
    if length > .02:
        offset[axes] = radius / length * settings["amount_m"] * band
    return offset

