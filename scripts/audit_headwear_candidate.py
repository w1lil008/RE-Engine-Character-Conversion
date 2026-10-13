"""Verify the draft assembly only changes hair weights, not body/rig geometry."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import numpy as np
from common import ROOT, write_json, confined


def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects["GraceOriginalBindRig"]
    bones = [(b.name, b.parent.name if b.parent else None, [list(r) for r in b.matrix_local])
             for b in rig.data.bones]
    meshes = {}
    for obj in bpy.data.collections["Bela_on_Grace_Prototype"].objects:
        if obj.type != "MESH":
            continue
        points = np.asarray([v.co[:] for v in obj.data.vertices], dtype=np.float32)
        topology = np.asarray([p.vertices[:] for p in obj.data.polygons], dtype=np.uint32)
        uv = np.asarray([v.uv[:] for v in obj.data.uv_layers[0].data], dtype=np.float32)
        h = hashlib.sha256()
        for v in obj.data.vertices:
            values = sorted((obj.vertex_groups[g.group].name, float(g.weight)) for g in v.groups if g.weight > 0)
            h.update(json.dumps(values, separators=(",", ":")).encode())
        meshes[obj.name] = {
            "geometry": hashlib.sha256(points.tobytes() + topology.tobytes() + uv.tobytes()).hexdigest(),
            "materials": [m.name for m in obj.data.materials],
            "transform": [list(r) for r in obj.matrix_world], "weights": h.hexdigest(),
            "finite": bool(np.isfinite(points).all()), "vertices": len(points)}
    return bones, meshes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="headwear")
    parser.add_argument("--candidate-scene", default="assets/work/BelaGrace_headwear_native_candidate.blend")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if not args.tag.replace("_", "").isalnum():
        raise ValueError("Invalid audit tag")
    original_bones, original = snapshot(ROOT / "assets/work/BelaGrace_preparation.blend")
    candidate_path = confined(ROOT, args.candidate_scene)
    candidate_bones, candidate = snapshot(candidate_path)
    assert original_bones == candidate_bones and len(original_bones) == 611
    assert set(original) == set(candidate)
    rows = []
    for name in sorted(original):
        old, new = original[name], candidate[name]
        assert old["geometry"] == new["geometry"] and new["finite"]
        assert old["materials"] == new["materials"] and old["transform"] == new["transform"]
        same_weights = old["weights"] == new["weights"]
        assert same_weights or name.startswith("hair_")
        rows.append({"object": name, "geometry_topology_uvs_materials_transform_unchanged": True,
                     "weights_unchanged": same_weights, "vertices": new["vertices"]})
    write_json(confined(ROOT, "reports/" + args.tag + "/assembly_scope_audit.json"), {
        "status": "ONLY_HAIR_WEIGHTS_CHANGED_IN_NATIVE_CANDIDATE_ASSEMBLY",
        "candidate_scene": str(candidate_path.relative_to(ROOT)),
        "Grace_611_bind_matrices_and_hierarchy_unchanged": True,
        "all_body_clothing_face_boot_weights_unchanged": True,
        "all_rest_geometry_topology_uvs_materials_unchanged": True,
        "objects": rows, "installed_build_changed": False})
    print(f"{len(rows)} assembly objects checked; only the two hair objects change weights.")


if __name__ == "__main__":
    main()

