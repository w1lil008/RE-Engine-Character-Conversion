"""Assemble and validate a complete release in a separate local staging tree.

All baseline payloads are hash checked, then the two reviewed native hair files
replace their counterparts. No game/manager or baseline staging writes.
"""
import argparse
import hashlib
import json
from pathlib import Path
from common import ROOT, confined, write_json
from validate_mod import validate


def sha_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-config", required=True)
    args = parser.parse_args()
    recipe = json.loads(confined(ROOT, args.release_config).read_text())
    baseline = json.loads((ROOT / "reports/mod_validation.json").read_text())
    original_review = json.loads((ROOT / "reports/alignment_review.json").read_text())
    overlay = json.loads(confined(ROOT, recipe.get("hair_validation", "reports/headwear/native_candidate_validation.json")).read_text())
    overlay_review = json.loads(confined(ROOT, recipe.get("hair_review", "reports/headwear/candidate_review.json")).read_text())
    scope = json.loads(confined(ROOT, recipe.get("hair_scope", "reports/headwear/assembly_scope_audit.json")).read_text())
    assert baseline["status"] == "OFFLINE_VALIDATION_PASSED" and not baseline["errors"]
    assert len(baseline["files"]) == 80
    assert original_review["packaging_allowed"] and not original_review["major_unresolved_issues"]
    assert original_review["reviewed_native_files_signature"] == signature(baseline["files"])
    assert overlay["status"] == "TWO_NATIVE_HAIR_FILES_ROUNDTRIP_VALIDATED_NOT_IN_GAME_TESTED"
    assert overlay_review["status"] == "OFFLINE_HAIR_CORRECTION_REVIEWED_RUNTIME_RETEST_PENDING"
    assert not overlay_review.get("major_unresolved_issues", [])
    assert overlay_review["reviewed_native_files_signature"] == signature(overlay["native_files"])
    assert scope["all_rest_geometry_topology_uvs_materials_unchanged"]
    assert scope["all_body_clothing_face_boot_weights_unchanged"]
    assert scope["Grace_611_bind_matrices_and_hierarchy_unchanged"]
    inputs = {}
    for row in baseline["files"]:
        source = confined(ROOT / "mod/BelaGrace_RE9", row["path"])
        assert sha_file(source) == row["sha256"], f"Baseline changed: {row['path']}"
        inputs[row["path"]] = (source, row["sha256"])
    changed = []
    for row in overlay["native_files"]:
        parts = Path(row["source"]).parts
        relative = Path(*parts[parts.index("natives"):]).as_posix()
        assert relative in inputs and inputs[relative][1] == row["source_sha256"]
        source = confined(ROOT, row["path"])
        assert sha_file(source) == row["sha256"], f"Hair candidate changed: {relative}"
        inputs[relative] = (source, row["sha256"])
        changed.append(relative)
    assert len(changed) == 2
    stage = confined(ROOT, recipe["staging"])
    for relative, (source, expected) in inputs.items():
        output = confined(stage, relative)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            assert sha_file(output) == expected, f"Existing release differs: {relative}"
        else:
            output.write_bytes(source.read_bytes())
        assert sha_file(output) == expected
    actual = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
    assert actual == set(inputs), "Release tree has unexpected/missing files"
    validation = validate(stage)
    assert all(Path(row["path"]).is_relative_to(Path(recipe["staging"]))
               for row in validation["meshes"]), "Validator parsed a different staging tree"
    write_json(confined(ROOT, recipe["validation"]), validation)
    if validation["errors"]:
        raise ValueError(validation["errors"])
    review = {
        "status": "FULL_RELEASE_OFFLINE_ACCEPTED_FOR_CONTROLLED_ADS_RETEST",
        "version": recipe["version"], "packaging_allowed": True,
        "major_unresolved_issues": [], "in_game_tested": False,
        "reviewed_native_files_signature": signature(validation["files"]),
        "basis": ["14 original joint fixtures apply to unchanged body/clothing geometry and weights.",
                  f"{overlay_review['native_fixtures_evaluated']} reopened-native headwear fixtures and {len(overlay_review['reviewed_native_images'])} reviewed renders.",
                  "34-object assembly audit preserves geometry, materials and all non-hair weights.",
                  "Complete 80-file native validation of this release, not the baseline directory."],
        "decision": "User requests a complete next test build; separate integration is now complete.",
        "remaining_limits": overlay_review["remaining_limits"] + [
            "Locomotion, crouching, stairs and feet/floor contact remain unconfirmed.",
            "Static face; no Bela hair/cloth physics, authentic heels or full other-scene/outfit coverage."],
        "only_changed_native_files": changed, "complete_mod": True,
        "baseline_version_required": False, "installed_build_changed": False}
    write_json(confined(ROOT, recipe["review"]), review)
    write_json(confined(ROOT, recipe["changes"]), {
        "version": recipe["version"], "complete_mod": True,
        "native_files_created_in_new_staging": [row["path"] for row in validation["files"]],
        "native_files_changed_from_0.1.0": changed,
        "other_native_files_byte_identical_to_0.1.0": len(inputs) - len(changed),
        "authored_files": recipe.get("authored_files", ["scripts/assemble_release.py", "scripts/package_mod.py", "scripts/validate_mod.py",
                           args.release_config, recipe["readme"], "README.md", "docs/STATUS.md",
                           "docs/HEADWEAR.md", "docs/PIPELINE.md", "docs/RUNTIME_TESTS.md"]),
        "package_metadata_files": ["modinfo.ini", "README.txt", "screenshot.png"],
        "installed_game_or_manager_files_written": False, "baseline_staging_changed": False,
        "previous_zip_changed": False, "staging": recipe["staging"], "output": recipe["output"]})
    print(f"Complete v{recipe['version']} staged: 80 validated native files, only 2 changed; 0 errors.")


if __name__ == "__main__":
    main()

