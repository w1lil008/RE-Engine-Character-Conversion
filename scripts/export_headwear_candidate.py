"""Export a separate, uninstalled native hair-weight candidate.

Consumes the Blender diagnostic sidecar, uses the pinned RE Mesh Editor writer,
then reopens both RE9 hair variants. No active staging/game/package writes.
"""
import argparse
import copy
import hashlib
import json
import numpy as np
from analyze_assets import parsed_mesh
from common import ROOT, reader, write_json, confined
from rigging import sanitize_weights


def normal_tangent_bytes(raw):
    elements = raw.meshBufferHeader.vertexElementList
    index = next(i for i, element in enumerate(elements) if element.typing == 1)
    start = elements[index].posStartOffset
    end = elements[index + 1].posStartOffset
    return start, end, bytes(raw.meshBufferHeader.vertexBuffer[start:end])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="headwear")
    parser.add_argument("--source-root", default="mod/BelaGrace_RE9")
    parser.add_argument("--output-root")
    parser.add_argument("--report")
    args = parser.parse_args()
    if not args.tag.replace("_", "").isalnum():
        raise ValueError("Invalid candidate tag")
    work = ROOT / "assets/work" if args.tag == "headwear" else confined(ROOT, "assets/work/" + args.tag)
    output_root = confined(ROOT, args.output_root or ("build/headwear_candidate" if args.tag == "headwear" else "build/" + args.tag))
    source_root = confined(ROOT, args.source_root)
    if output_root == source_root:
        raise ValueError("Hair rebuild output must differ from its input")
    sidecar = json.loads((work / "headwear_candidate_weights.json").read_text())
    if sidecar["status"] != "DRAFT_BLENDER_ONLY_NOT_NATIVE_EXPORTED" or sidecar["position_changes"]:
        raise ValueError("Unexpected candidate recipe")
    candidates = {r["object"].split("_", 2)[2]: r for r in sidecar["objects"]}
    module = reader("RE-Mesh-Editor", "remesh", "modules.mesh.file_re_mesh")
    reports = []
    for slot in ["20", "21"]:
        relative = f"natives/stm/character/ch/ch02/0200/{slot}/00/ch0200_{slot}_00.mesh.250925211"
        source = source_root / relative
        source_raw, baseline = parsed_mesh(source)
        source_start, _, original_normal_tangents = normal_tangent_bytes(source_raw)
        result = copy.deepcopy(baseline)
        palette = sorted({n for row in candidates.values() for pairs in row["weights"] for n, w in pairs},
                         key={b.boneName: b.boneIndex for b in result.skeleton.boneList}.get)
        if len(palette) > 256:
            raise ValueError("Candidate bone palette exceeds mesh limit")
        indices = {n: i for i, n in enumerate(palette)}
        result.skeleton.weightedBones = palette
        for bone in result.skeleton.boneList:
            if bone.boneName in palette:
                bone.boundingBox = copy.deepcopy(result.boundingBox)
        seen = set()
        for lod in result.mainMeshLODList:
            for group in lod.visconGroupList:
                for sub in group.subMeshList:
                    material = result.materialNameList[sub.materialIndex]
                    row = candidates[material]
                    if material in seen or len(row["weights"]) != len(sub.vertexPosList):
                        raise ValueError("Hair sidecar/native topology mismatch")
                    seen.add(material)
                    weight_rows, index_rows = [], []
                    for values in row["weights"]:
                        pairs = sanitize_weights(values)
                        weight_rows.append([w for n, w in pairs] + [0.] * (8 - len(pairs)))
                        index_rows.append([indices[n] for n, w in pairs] + [0] * (8 - len(pairs)))
                    sub.weightList = np.asarray(weight_rows)
                    sub.weightIndicesList = np.asarray(index_rows, dtype=np.uint16)
                    # The parsed reader discards tangent W; recover all four
                    # signed bytes directly from this unchanged native buffer.
                    offset = source_start + sub.meshVertexOffset * 8
                    encoded = np.frombuffer(source_raw.meshBufferHeader.vertexBuffer,
                                            dtype=np.int8, count=len(sub.vertexPosList) * 8,
                                            offset=offset).reshape((-1, 2, 4))
                    sub.tangentList = encoded[:, 1, :].copy()
        assert seen == set(candidates)
        output = output_root / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        rebuilt_raw = module.ParsedREMeshToREMesh(result, 250925211)
        start, end, _ = normal_tangent_bytes(rebuilt_raw)
        assert end - start == len(original_normal_tangents)
        buffer = bytearray(rebuilt_raw.meshBufferHeader.vertexBuffer)
        buffer[start:end] = original_normal_tangents
        rebuilt_raw.meshBufferHeader.vertexBuffer = buffer
        module.writeREMesh(rebuilt_raw, str(output))
        raw, check = parsed_mesh(output)
        assert normal_tangent_bytes(raw)[2] == original_normal_tangents
        assert raw.fileHeader.version == 250904410
        assert check.materialNameList == baseline.materialNameList
        assert len(check.skeleton.boneList) == len(baseline.skeleton.boneList) == 611
        for original, rebuilt in zip(baseline.skeleton.boneList, check.skeleton.boneList):
            assert original.boneName == rebuilt.boneName and original.parentIndex == rebuilt.parentIndex
            for attr in ["worldMatrix", "localMatrix", "inverseMatrix"]:
                assert np.array_equal(getattr(original, attr).matrix, getattr(rebuilt, attr).matrix)
        rows_before = [s for lod in baseline.mainMeshLODList for g in lod.visconGroupList for s in g.subMeshList]
        rows_after = [s for lod in check.mainMeshLODList for g in lod.visconGroupList for s in g.subMeshList]
        assert len(rows_before) == len(rows_after)
        max_error = 0.
        for before, after in zip(rows_before, rows_after):
            assert np.array_equal(before.vertexPosList, after.vertexPosList)
            assert np.array_equal(before.faceList, after.faceList)
            assert np.array_equal(before.uvList, after.uvList)
            for attr in ["normalList", "tangentList"]:
                assert np.array_equal(getattr(before, attr), getattr(after, attr))
            material = check.materialNameList[after.materialIndex]
            expected_rows = candidates[material]["weights"]
            for expected, slots, values in zip(expected_rows, after.weightIndicesList, after.weightList):
                actual = {}
                for index, value in zip(slots, values):
                    if value > 0:
                        name = check.skeleton.weightedBones[index]
                        actual[name] = actual.get(name, 0.) + value
                assert actual and len(actual) <= 8 and abs(sum(actual.values()) - 1) <= 1.1 / 255
                for name in set(dict(expected)) | set(actual):
                    max_error = max(max_error, abs(dict(expected).get(name, 0.) - actual.get(name, 0.)))
        assert max_error < 8 / 255
        with source.open("rb") as stream:
            source_sha = hashlib.file_digest(stream, "sha256").hexdigest()
        with output.open("rb") as stream:
            output_sha = hashlib.file_digest(stream, "sha256").hexdigest()
        reports.append({"source": str(source.relative_to(ROOT)), "source_sha256": source_sha,
                        "path": str(output.relative_to(ROOT)), "sha256": output_sha,
                        "palette_bones": len(palette), "max_roundtrip_weight_error": max_error,
                        "geometry_topology_uvs_and_Grace_bind_matrices_unchanged": True,
                        "packed_normal_tangent_bytes_unchanged": True})
    write_json(confined(ROOT, args.report or ("reports/" + args.tag + "/native_candidate_validation.json")), {
        "status": "TWO_NATIVE_HAIR_FILES_ROUNDTRIP_VALIDATED_NOT_IN_GAME_TESTED",
        "weights_sidecar": str((work / "headwear_candidate_weights.json").relative_to(ROOT)),
        "native_files": reports, "materials_textures_changed": False,
        "original_staging_changed": False, "installed_build_changed": False,
        "packaged": False, "limits": "Two replacement meshes only; not a full mod validation or runtime test."})
    print("Two separate native hair candidates validated; no installation or package.")


if __name__ == "__main__":
    main()

