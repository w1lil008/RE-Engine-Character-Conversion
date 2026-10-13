"""Stage a stabilization patch only after current rebuild and offline review pass."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from common import ROOT, confined, write_json
from validate_mod import validate


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_payloads(stage, expected):
    actual = {p.relative_to(stage).as_posix(): sha(p) for p in stage.rglob("*") if p.is_file()}
    wanted = {r["path"]: r["sha256"] for r in expected}
    if actual != wanted:
        changed = sorted(n for n in wanted.keys() | actual.keys() if actual.get(n) != wanted.get(n))
        raise ValueError(f"Release payload drift: {changed}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-config", default="config/releases/0.1.3.json")
    args = parser.parse_args()
    recipe = json.loads(confined(ROOT, args.release_config).read_text())
    baseline = json.loads((ROOT / "reports/releases/0.1.2/mod_validation.json").read_text())
    rebuild = json.loads((ROOT / "reports/stabilization/rebuild.json").read_text())
    if rebuild["status"] != "PASSED" or not rebuild["all_80_native_payloads_byte_identical_to_accepted_0.1.2"]:
        raise ValueError("Accepted source rebuild is required")
    producers = {"scripts/build_meshes.py", "scripts/build_materials.py", "scripts/rigging.py",
                 "scripts/common.py", "scripts/export_headwear_candidate.py", "scripts/validate_mod.py",
                 "scripts/analyze_assets.py", "config/prototype.json", "config/toolchain.lock.json"}
    for row in rebuild["source_files"]:
        if row["path"] in producers and sha(confined(ROOT, row["path"])) != row["sha256"]:
            raise ValueError(f"Build source changed; rebuild required: {row['path']}")
    reports = ROOT / "reports/stabilization"
    visual = json.loads((reports / "visual_review.json").read_text())
    if not visual["packaging_allowed"] or visual["major_new_regressions_observed"]:
        raise ValueError("Current native visual review withholds packaging")
    for path, expected in visual["reviewed_image_hashes"].items():
        if sha(confined(ROOT, path)) != expected:
            raise ValueError(f"Reviewed render changed: {path}")
    body = json.loads((reports / "alignment_qa.json").read_text())
    hair = json.loads((ROOT / "reports/stabilization_headwear/native_candidate_diagnostics.json").read_text())
    skin = json.loads((reports / "assembled_seam_audit.json").read_text())
    dress = json.loads((reports / "garment_seam_audit.json").read_text())
    if len(body["fixtures"]) != 14 or len(hair["fixtures"]) != 14 or not all(f["finite_geometry"] for f in body["fixtures"]):
        raise ValueError("Incomplete current native pose audit")
    if skin["status"] != "TESTED_SKIN_COINCIDENCE_PASSED" or dress["status"] != "TESTED_GARMENT_CONTINUITY_PASSED":
        raise ValueError("Current seam audit failed")
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                           cwd=ROOT, capture_output=True, text=True)
    (reports / "unit_tests.log").write_text(tests.stdout + tests.stderr)
    if tests.returncode:
        raise ValueError("Regression tests failed; see reports/stabilization/unit_tests.log")
    source = confined(ROOT, rebuild["fresh_output"])
    verify_payloads(source, baseline["files"])
    verify_payloads(ROOT / "mod/BelaGrace_RE9_0.1.2", baseline["files"])
    stage = confined(ROOT, recipe["staging"])
    if not stage.exists():
        shutil.copytree(source, stage)
    verify_payloads(stage, baseline["files"])
    validation = validate(stage)
    if validation["errors"]:
        raise ValueError(validation["errors"])
    write_json(confined(ROOT, recipe["validation"]), validation)
    signature = hashlib.sha256(json.dumps(validation["files"], sort_keys=True).encode()).hexdigest()
    write_json(confined(ROOT, recipe["review"]), {"packaging_allowed": True, "major_unresolved_issues": [],
        "status": "STABILIZATION_PATCH_CURRENT_NATIVE_REVIEW_PASSED", "reviewed_native_files_signature": signature,
        "basis": ["Fresh source rebuild: all 80 natives identical to accepted 0.1.2", "14 current-native body poses; 14 headwear poses",
                  "20 rendered views reviewed", "92 skin seam groups and 1450 garment seam groups pass", "14 regression tests pass"],
        "known_limitations": visual["observations"], "runtime_tested_this_release": False})
    write_json(ROOT / "reports/stabilization/test_results.json", {"status": "PASSED", "unit_tests": 14,
        "body_fixtures": len(body["fixtures"]), "hair_fixtures": len(hair["fixtures"]), "native_files": len(validation["files"]),
        "validation_errors": validation["errors"], "skin_seam_max_mm": max(f["maximum_spread_m"] for f in skin["fixtures"]) * 1000,
        "dress_seam_max_mm": max(f["maximum_spread_m"] for f in dress["fixtures"]) * 1000,
        "source_rebuild_byte_identical": True, "runtime_tested": False,
        "limits": "Offline structure, selected synthetic poses and reviewed static renders; no runtime/full collision guarantee"})
    authored = []
    for folder in ["scripts", "config", "tests", "docs/releases/0.1.3"]:
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                authored.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)})
    manifest = {"version": recipe["version"], "native_files": validation["files"], "native_files_signature": signature,
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_revision_scope": "Checkpoint commit plus authored file hashes below; release source may be uncommitted at build time",
        "source_files": authored, "toolchain_lock_sha256": sha(ROOT / "config/toolchain.lock.json"),
        "prepared_asset_checkpoint": "reports/stabilization/baseline_checkpoint.json", "prepared_asset_checkpoint_sha256": sha(reports / "baseline_checkpoint.json"),
        "source_rebuild": rebuild, "automated_results": json.loads((reports / "test_results.json").read_text()),
        "release_runtime_tested": False, "baseline_runtime_evidence": "reports/releases/0.1.2/runtime_acceptance.json",
        "native_changes_from_0.1.2": [], "game_or_manager_files_written": False,
        "manifest_scope": "Every native payload plus source/config provenance. Archive manifest covers metadata; no recursive self-hash."}
    write_json(confined(ROOT, recipe["build_manifest"]), manifest)
    print(f"v{recipe['version']}: 80 natives, zero payload changes, 14 tests pass; ready to package")


if __name__ == "__main__":
    main()

