"""Analyze local meshes/skeletons/material dependencies with pinned format readers."""
import json
from pathlib import Path
import numpy as np
from common import ROOT, reader, write_json


def parsed_mesh(path):
    file_module = reader("RE-Mesh-Editor", "remesh", "modules.mesh.file_re_mesh")
    parse_module = reader("RE-Mesh-Editor", "remesh", "modules.mesh.re_mesh_parse")
    raw = file_module.readREMesh(str(path), 0)
    parsed = parse_module.ParsedREMesh()
    parsed.ParseREMesh(raw)
    return raw, parsed


def mesh_summary(path):
    raw, mesh = parsed_mesh(path)
    positions = [s.vertexPosList for lod in mesh.mainMeshLODList for g in lod.visconGroupList for s in g.subMeshList]
    points = np.concatenate(positions) if positions else np.empty((0, 3))
    bones = []
    if mesh.skeleton:
        for b in mesh.skeleton.boneList:
            bones.append({"name": b.boneName, "index": b.boneIndex, "parent_index": b.parentIndex,
                          "world_matrix": b.worldMatrix.matrix, "local_matrix": b.localMatrix.matrix,
                          "inverse_matrix": b.inverseMatrix.matrix})
    return {"path": str(path.relative_to(ROOT)), "file_version": int(path.suffix[1:]),
            "internal_version": raw.fileHeader.version, "vertices_lod0": len(points),
            "bounds": [points.min(axis=0).tolist(), points.max(axis=0).tolist()] if len(points) else None,
            "materials": mesh.materialNameList, "weighted_bones": mesh.skeleton.weightedBones if mesh.skeleton else [],
            "bones": bones}


def main():
    mdf_module = reader("RE-Mesh-Editor", "remesh", "modules.mdf.file_re_mdf")
    summaries = {}
    materials = {}
    for game in ["re8", "re9"]:
        summaries[game] = [mesh_summary(p) for p in sorted((ROOT / f"assets/extracted/{game}").rglob("*.mesh.*"))
                           if "streaming" not in p.parts]
        materials[game] = []
        for path in sorted((ROOT / f"assets/extracted/{game}").rglob("*.mdf2.*")):
            mdf = mdf_module.readMDF(str(path))
            if mdf is None:
                raise RuntimeError(f"Failed to read {path}")
            materials[game].append({"path": str(path.relative_to(ROOT)), "materials": [
                {"name": m.materialName, "shader": m.mmtrPath,
                 "textures": [{"type": t.textureType, "path": t.texturePath} for t in m.textureList],
                 "properties": {p.propName: p.propValue for p in m.propertyList}}
                for m in mdf.materialList]})
    write_json(ROOT / "reports/mesh_analysis.json", summaries)
    write_json(ROOT / "reports/material_analysis.json", materials)
    for game, rows in summaries.items():
        for row in rows:
            print(game, Path(row["path"]).name, row["vertices_lod0"], len(row["bones"]), row["materials"][:4])


if __name__ == "__main__":
    main()

