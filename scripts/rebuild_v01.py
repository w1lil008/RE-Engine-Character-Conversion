"""Rebuild the accepted v0.1.2 payload from local source into a fresh directory.

Prepared sidecars are versioned build inputs; no prior native output is copied.
Never writes a release, installation, source asset, or historical report.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from common import ROOT, confined, write_json
import build_meshes
import build_materials
from validate_mod import validate


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="build/rebuild_0.1.2")
    args = parser.parse_args()
    output = confined(ROOT / "build", args.output.removeprefix("build/"))
    if output.exists():
        raise ValueError("Use a fresh rebuild output directory; existing evidence is preserved")
    checkpoint = json.loads((ROOT / "reports/stabilization/baseline_checkpoint.json").read_text())
    # All original extracted assets and prepared data used by these scripts must
    # still match the checkpoint, including the manually accepted deformation.
    for row in checkpoint["local_asset_inputs"]:
        if row["path"].startswith("assets/extracted/") or row["path"] in {
            "assets/work/clothing_weights.json", "assets/work/clothing_surface_weights.json",
            "assets/work/headwear_v2/headwear_candidate_weights.json"
        }:
            if sha(confined(ROOT, row["path"])) != row["sha256"]:
                raise ValueError(f"Source input changed: {row['path']}")
    stage, reports = output / "base", output / "reports"
    reports.mkdir(parents=True)
    build_meshes.OUTPUT, build_meshes.REPORTS = stage, reports
    build_meshes.main()
    build_materials.MOD, build_materials.CACHE = stage, output / "texture_cache"
    build_materials.REPORTS = reports
    build_materials.DEPENDENCIES_OUTPUT = reports / "re9_material_dependencies.txt"
    build_materials.main()
    hair = output / "hair"
    subprocess.run([sys.executable, str(ROOT / "scripts/export_headwear_candidate.py"),
                    "--tag", "headwear_v2", "--source-root", stage.relative_to(ROOT).as_posix(),
                    "--output-root", hair.relative_to(ROOT).as_posix(),
                    "--report", (reports / "hair_roundtrip.json").relative_to(ROOT).as_posix()], check=True)
    final = output / "natives_release"
    shutil.copytree(stage, final)
    for path in hair.rglob("*"):
        if path.is_file():
            shutil.copy2(path, final / path.relative_to(hair))
    baseline = json.loads((ROOT / "reports/releases/0.1.2/mod_validation.json").read_text())
    expected = {r["path"]: r["sha256"] for r in baseline["files"]}
    actual = {p.relative_to(final).as_posix(): sha(p) for p in final.rglob("*") if p.is_file()}
    differences = sorted(k for k in expected.keys() | actual.keys() if expected.get(k) != actual.get(k))
    validation = validate(final, reports / "mesh_build.json")
    write_json(reports / "mod_validation.json", validation)
    inputs = []
    for folder in ["scripts", "config", "tests"]:
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                inputs.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)})
    result = {"status": "PASSED" if not differences and not validation["errors"] else "FAILED",
              "rebuilt_native_files": len(actual), "all_80_native_payloads_byte_identical_to_accepted_0.1.2": not differences and len(actual) == 80,
              "differences": differences, "validation_errors": validation["errors"],
              "source_files": inputs, "prepared_input_checkpoint": "reports/stabilization/baseline_checkpoint.json",
              "fresh_output": final.relative_to(ROOT).as_posix(), "game_or_manager_files_written": False,
              "historical_staging_or_reports_written": False, "runtime_tested": False}
    write_json(ROOT / "reports/stabilization/rebuild.json", result)
    print(result["status"], f"{len(actual)} rebuilt natives; {len(differences)} payload differences; {len(validation['errors'])} validation errors")
    if result["status"] != "PASSED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

