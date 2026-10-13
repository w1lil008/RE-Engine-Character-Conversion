"""Record native geometry before a weight-only change and verify its invariants."""
import argparse
import json
import hashlib
import numpy as np
from common import ROOT, write_json
from analyze_assets import parsed_mesh


def digest(value, dtype=np.float32):
    return hashlib.sha256(np.asarray(value, dtype=dtype).tobytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["snapshot", "compare"])
    mode = parser.parse_args().mode
    build = json.loads((ROOT / "reports/mesh_build.json").read_text())
    rows = []
    for output in build["outputs"]:
        _, mesh = parsed_mesh(ROOT / output["path"])
        submeshes = []
        for group in mesh.mainMeshLODList[0].visconGroupList:
            for sub in group.subMeshList:
                skin = [[(mesh.skeleton.weightedBones[i], w) for i, w in zip(indices, weights) if w > 0]
                        for indices, weights in zip(sub.weightIndicesList, sub.weightList)]
                submeshes.append({"material": mesh.materialNameList[sub.materialIndex], "vertices": len(sub.vertexPosList),
                                  "position_sha256": digest(sub.vertexPosList), "faces_sha256": digest(sub.faceList, np.uint32),
                                  "bone_named_weights_sha256": hashlib.sha256(json.dumps(skin, separators=(",", ":")).encode()).hexdigest()})
        rows.append({"path": output["path"], "submeshes": submeshes,
                     "bind_matrices_sha256": digest([b.worldMatrix.matrix for b in mesh.skeleton.boneList])})
    if mode == "snapshot":
        write_json(ROOT / "reports/mesh_weight_baseline.json", {"native_meshes": rows})
        print("Recorded native topology, positions, named weights and bind matrices.")
        return
    baseline = json.loads((ROOT / "reports/mesh_weight_baseline.json").read_text())["native_meshes"]
    if [r["path"] for r in rows] != [r["path"] for r in baseline]:
        raise ValueError("Native output set changed")
    results = []
    for old, new in zip(baseline, rows):
        old_geometry = [{k: v for k, v in s.items() if k != "bone_named_weights_sha256"} for s in old["submeshes"]]
        new_geometry = [{k: v for k, v in s.items() if k != "bone_named_weights_sha256"} for s in new["submeshes"]]
        results.append({"path": new["path"], "geometry_and_topology_unchanged": old_geometry == new_geometry,
                        "bind_matrices_unchanged": old["bind_matrices_sha256"] == new["bind_matrices_sha256"],
                        "named_weights_changed": old["submeshes"] != new["submeshes"]})
    passed = all(r["geometry_and_topology_unchanged"] and r["bind_matrices_unchanged"] for r in results)
    write_json(ROOT / "reports/mesh_weight_comparison.json", {"status": "WEIGHT_ONLY_CHANGE_CONFIRMED" if passed else "UNEXPECTED_GEOMETRY_CHANGE",
               "meshes": results})
    if not passed:
        raise ValueError("Weight-only rebuild changed topology, positions or target bind matrices")
    print("All eight native meshes retain identical positions, topology and Grace bind matrices.")


if __name__ == "__main__":
    main()

