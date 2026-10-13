"""Create and verify a local Fluffy test ZIP after the explicit alignment gate.

Never installs or changes the game/manager. A passing archive check does not
establish RE9 runtime compatibility.
"""
import json
import hashlib
import zipfile
import argparse
from pathlib import PurePosixPath
from common import ROOT, confined, write_json


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-config")
    args = parser.parse_args()
    recipe = json.loads(confined(ROOT, args.release_config).read_text()) if args.release_config else {}
    validation = json.loads(confined(ROOT, recipe.get("validation", "reports/mod_validation.json")).read_text())
    review = json.loads(confined(ROOT, recipe.get("review", "reports/alignment_review.json")).read_text())
    if validation["status"] != "OFFLINE_VALIDATION_PASSED" or validation["errors"]:
        raise ValueError("Native validation has not passed")
    if not review.get("packaging_allowed") or review.get("major_unresolved_issues"):
        raise ValueError("Assembled alignment review withholds packaging")
    signature = sha(json.dumps(validation["files"], sort_keys=True).encode())
    if review.get("reviewed_native_files_signature") != signature:
        raise ValueError("Native files changed since assembled review")
    base = confined(ROOT, recipe.get("staging", "mod/BelaGrace_RE9"))
    files = {}
    for row in validation["files"]:
        relative = PurePosixPath(row["path"])
        if relative.is_absolute() or ".." in relative.parts or relative.parts[0] != "natives":
            raise ValueError("Invalid native archive path")
        path = confined(base, relative)
        if path.is_symlink():
            raise ValueError("Package cannot include symlinks")
        data = path.read_bytes()
        if sha(data) != row["sha256"]:
            raise ValueError(f"Native validation stale: {relative}")
        files[relative.as_posix()] = data
    expected = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    if expected != set(files):
        raise ValueError("Staging directory contains unvalidated files")
    files["modinfo.ini"] = (
        "name=Bela for Grace - Experimental v0.1.0\n"
        "description=Base Grace replacement. Offline validated only; NO in-game test yet. Static face/hair, skinned dress, original Grace boots. Hair Strands OFF.\n"
        "version=v0.1.0-test\n"
        "author=Local BelaGrace project\n"
        "screenshot=screenshot.png\n"
        "category=!Characters > Grace\n"
    ).encode("utf-8")
    files["README.txt"] = (
        "BELA FOR GRACE - EXPERIMENTAL FIRST TEST BUILD\n"
        "This build has NOT been tested in Resident Evil Requiem.\n\n"
        "INSTALL\n"
        "1. Exit the game. Select RE9 in Fluffy Mod Manager.\n"
        "2. Place this ZIP in Fluffy's Games/RE9/Mods folder. Refresh the mod list.\n"
        "3. Enable 'Bela for Grace - Experimental v0.1.0'.\n"
        "4. Keep Grace's hair mod disabled. Use the standard base outfit and Hair Strands OFF.\n"
        "5. Restart the game. Existing REFramework loose-file/texture loading is required.\n\n"
        "FIRST TEST\n"
        "Check third-person idle/front/back, walking/turning, then aiming/reloading and crouching.\n"
        "Check neck/wrists, grip, foot contact, skin/materials, and dress clipping.\n"
        "If the game fails to load, disable this mod in Fluffy and send REFramework logs.\n"
        "If only some parts change, record outfit, camera mode and active mods.\n\n"
        "KNOWN LIMITS\n"
        "Neutral Bela face; facial animation is not retargeted. Hair is static.\n"
        "Dress uses smoothed skin weights, not native cloth simulation; creases/clipping remain.\n"
        "Original Grace boots are retained. Bela heels, stitches and animated cloak are omitted.\n"
        "Alternate outfits, damage variants, strands hair and dedicated cutscene assets are not covered.\n"
        "Blender screenshots are approximate material previews, not gameplay evidence.\n\n"
        "ROLLBACK\n"
        "Exit the game and disable the mod in Fluffy. Original official archives are not replaced.\n"
        "Generated from locally owned games; keep this prototype local.\n"
    ).encode("utf-8")
    if recipe:
        files["modinfo.ini"] = (
            f"name={recipe['name']}\n"
            f"description={recipe['description']}\n"
            f"version=v{recipe['version']}-test\n"
            "author=Local BelaGrace project\n"
            "screenshot=screenshot.png\n"
            "category=!Characters > Grace\n"
        ).encode("utf-8")
        files["README.txt"] = confined(ROOT, recipe["readme"]).read_bytes()
        for name, source in recipe.get("package_documents", {}).items():
            relative = PurePosixPath(name)
            if relative.name != name or "\\" in name or relative.suffix not in {".txt", ".json"} or name in files:
                raise ValueError(f"Invalid supplemental release document: {name}")
            files[name] = confined(ROOT, source).read_bytes()
    files["screenshot.png"] = confined(ROOT, recipe.get("screenshot", "reports/preview_front.png")).read_bytes()
    output = confined(ROOT, recipe.get("output", "dist/BelaGrace_RE9_Prototype_0.1.0.zip"))
    if output.exists():
        raise ValueError("Release ZIP already exists; preserve it and use a new version")
    output.parent.mkdir(parents=True, exist_ok=True)
    root_name = recipe.get("root_name", "BelaGrace_RE9_Prototype_0.1.0")
    if PurePosixPath(root_name).name != root_name or "\\" in root_name or root_name in {".", ".."}:
        raise ValueError("Invalid package root folder")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(root_name + "/" + name, date_time=tuple(recipe.get("archive_date", [2026, 10, 9, 0, 0, 0])))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    manifest = []
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP CRC check failed")
        expected_paths = {root_name + "/" + name for name in files}
        if set(archive.namelist()) != expected_paths:
            raise ValueError("ZIP file set changed")
        for name, data in sorted(files.items()):
            actual = archive.read(root_name + "/" + name)
            if actual != data:
                raise ValueError(f"ZIP payload changed: {name}")
            manifest.append({"path": root_name + "/" + name, "bytes": len(data), "sha256": sha(data)})
    write_json(confined(ROOT, recipe.get("manifest", "reports/package_manifest.json")), {"status": "ARCHIVE_VALIDATED_NOT_IN_GAME_TESTED", "in_game_tested": False,
               "installed": False, "path": str(output.relative_to(ROOT)), "bytes": output.stat().st_size,
               "sha256": sha(output.read_bytes()), "files": manifest, "native_validation_signature": signature,
               "version": recipe.get("version", "0.1.0"), "complete_mod": True})
    print(f"Created and verified {output.name}: {len(files)} files, {output.stat().st_size/1048576:.1f} MiB. Not installed or game-tested.")


if __name__ == "__main__":
    main()

