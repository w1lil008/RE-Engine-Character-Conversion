"""Fail closed on broken binaries, rig weights, dependencies and package paths."""
import hashlib
import json
from pathlib import Path
import numpy as np
from common import ROOT, reader, write_json, confined
from analyze_assets import parsed_mesh
from extract_assets import load_names


def validate(mod, mesh_report=None):
    errors, outputs = [], []
    baseline = {n.lower() for n in load_names("re9")}
    mdf = reader("RE-Mesh-Editor", "remesh", "modules.mdf.file_re_mdf")
    texture = reader("RE-Mesh-Editor", "remesh", "modules.tex.file_re_tex")
    mesh_build = json.loads(Path(mesh_report or ROOT / "reports/mesh_build.json").read_text())
    from build_meshes import merge_skeleton, find_mesh
    settings = json.loads((ROOT / "config/prototype.json").read_text())
    reference = merge_skeleton([parsed_mesh(find_mesh("re9", n))[1] for n in settings["target_rig_parts"]])
    for row in mesh_build["outputs"]:
        # Resolve reported asset slots inside the supplied staging directory.
        # Otherwise validating a new release would silently parse the old one.
        parts = Path(row["path"]).parts
        relative = Path(*parts[parts.index("natives"):])
        path = confined(mod, relative)
        raw, mesh = parsed_mesh(path)
        if int(path.suffix[1:]) != 250925211 or raw.fileHeader.version != 250904410:
            errors.append(f"Unexpected RE9 mesh version: {path.name}")
        skeleton = mesh.skeleton
        if not skeleton or len(skeleton.weightedBones) > 256:
            errors.append(f"Invalid weighted bone palette: {path.name}")
            continue
        names = {b.boneName for b in skeleton.boneList}
        if len(skeleton.boneList) != 611 or len(skeleton.boneList) != len(reference.boneList):
            errors.append(f"Runtime skeleton bone count changed: {path.name}")
        for actual, expected in zip(skeleton.boneList, reference.boneList):
            if actual.boneName != expected.boneName or actual.parentIndex != expected.parentIndex or any(
                not np.allclose(getattr(actual, attr).matrix, getattr(expected, attr).matrix, atol=1e-6, rtol=0)
                for attr in ["localMatrix", "worldMatrix", "inverseMatrix"]
            ):
                errors.append(f"Original Grace bind definition changed: {path.name}/{actual.boneName}")
        if not set(skeleton.weightedBones).issubset(names) or len(set(skeleton.weightedBones)) != len(skeleton.weightedBones):
            errors.append(f"Invalid or duplicate bone palette names: {path.name}")
        if len(names) != len(skeleton.boneList):
            errors.append(f"Duplicate bone names: {path.name}")
        for b in skeleton.boneList:
            if b.parentIndex >= b.boneIndex or b.parentIndex < -1:
                errors.append(f"Non-topological bone hierarchy {b.boneName}")
            world = np.array(b.worldMatrix.matrix)
            inverse = np.array(b.inverseMatrix.matrix)
            if not np.allclose(world @ inverse, np.eye(4), atol=1e-3):
                errors.append(f"Bind/inverse mismatch: {b.boneName}")
        vertices = 0
        for lod in mesh.mainMeshLODList:
            for group in lod.visconGroupList:
                for sub in group.subMeshList:
                    positions = np.asarray(sub.vertexPosList)
                    weights = np.asarray(sub.weightList)
                    indices = np.asarray(sub.weightIndicesList)
                    tangents = np.asarray(sub.tangentList)
                    normals, uv = np.asarray(sub.normalList), np.asarray(sub.uvList)
                    vertices += len(positions)
                    if not np.isfinite(positions).all() or np.max(np.abs(positions)) > 5:
                        errors.append(f"Nonfinite or implausible vertices: {path.name}")
                    if not np.isfinite(tangents).all() or np.mean(np.linalg.norm(tangents[:, :3], axis=1) >= .9) < .99:
                        errors.append(f"Invalid packed tangent directions: {path.name}")
                    if not np.allclose(weights.sum(axis=1), 1.0, atol=1.1 / 255):
                        errors.append(f"Unnormalized or unweighted vertices: {path.name}")
                    if not np.isfinite(weights).all() or np.any(weights < 0) or np.any(indices < 0) or np.any(indices >= len(skeleton.weightedBones)):
                        errors.append(f"Invalid bone weight indices: {path.name}")
                    if uv.shape != (len(positions), 2) or not np.isfinite(uv).all():
                        errors.append(f"Invalid UV stream: {path.name}")
                    if normals.shape != (len(positions), 3) or not np.isfinite(normals).all():
                        errors.append(f"Invalid normal stream: {path.name}")
                    if np.any(np.asarray(sub.faceList) >= len(positions)) or np.any(np.asarray(sub.faceList) < 0):
                        errors.append(f"Invalid triangle indices: {path.name}")
        variants = list(path.parent.glob(path.name.split(".mesh")[0] + "*.mdf2.51"))
        if not variants:
            errors.append(f"Missing MDF: {path.name}")
        for variant in variants:
            materials = mdf.readMDF(str(variant))
            if set(mesh.materialNameList) != {m.materialName for m in materials.materialList}:
                errors.append(f"MDF/mesh name mismatch: {variant.name}")
            for material in materials.materialList:
                for t in material.textureList:
                    native = "natives/stm/" + t.texturePath.lstrip("@").lower() + ".250813143"
                    if not (mod / native).is_file() and native not in baseline:
                        errors.append(f"Unresolved texture: {t.texturePath}")
        outputs.append({"path": str(path.relative_to(ROOT)), "vertices": vertices, "bones": len(names)})
    files = []
    for path in sorted(mod.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(mod).as_posix()
        if path.is_symlink() or path.suffix.lower() in [".exe", ".dll", ".lua"]:
            errors.append(f"Unexpected executable or symlink in asset package: {relative}")
        if ".tex." in path.name:
            tex = texture.RE_TexFile()
            tex.read(str(path))
            if tex.tex.header.version != 250813143:
                errors.append(f"Unexpected texture version: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return {"status": "FAILED" if errors else "OFFLINE_VALIDATION_PASSED", "in_game_tested": False,
            "errors": errors, "meshes": outputs, "files": files}


def main():
    report = validate(ROOT / "mod/BelaGrace_RE9")
    write_json(ROOT / "reports/mod_validation.json", report)
    print(report["status"], f"{len(report['files'])} files, {len(report['errors'])} errors")
    for error in report["errors"]:
        print(error)
    raise SystemExit(bool(report["errors"]))


if __name__ == "__main__":
    main()

