"""Record exact workspace files and verify official archive metadata unchanged."""
from common import ROOT, write_json
import json
from datetime import datetime, timezone


def main():
    checks = []
    for game in ["re8", "re9"]:
        inventory = json.loads((ROOT / f"reports/{game}_inventory.json").read_text())
        for archive in inventory["archives"]:
            from pathlib import Path
            current = Path(archive["path"]).stat()
            checks.append({"path": archive["path"], "size_unchanged": current.st_size == archive["bytes"],
                           "mtime_unchanged": current.st_mtime_ns == archive["mtime_ns"]})
    write_json(ROOT / "reports/game_archive_metadata_check.json", {"all_metadata_unchanged": all(r["size_unchanged"] and r["mtime_unchanged"] for r in checks),
               "limits": "Size/mtime comparison, not whole-archive content hashing. Extraction code only opens originals rb.", "archives": checks})
    files = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(p in {".git", "__pycache__", "tools"} for p in relative.parts):
            continue
        if path.suffix in {".pyc", ".blend1"} or relative.as_posix() == "reports/workspace_file_manifest.json":
            continue
        files.append({"path": relative.as_posix(), "absolute_path": str(path), "bytes": path.stat().st_size})
    write_json(ROOT / "reports/workspace_file_manifest.json", {"root": str(ROOT), "generated_at_utc": datetime.now(timezone.utc).isoformat(),
               "scope": "Project file inventory, excluding this manifest, caches, backups and pinned tools. This is not a before/after diff. Tool downloads are recorded in config/toolchain.lock.json and tools/provenance.jsonl.",
               "files": files})
    print(f"Recorded {len(files)} workspace files and {len(checks)} original archive metadata checks.")


if __name__ == "__main__":
    main()

