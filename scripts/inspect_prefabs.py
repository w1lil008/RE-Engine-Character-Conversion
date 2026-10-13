"""Read prefab resource references without editing RSZ instances or game files."""
from common import ROOT, reader, write_json


def main():
    module = reader("RE-Asset-Library", "reasset", "modules.rszmini.re_rsz_utils")
    records, errors = [], []
    for path in sorted((ROOT / "assets/extracted/re9").rglob("*.pfb.*")):
        try:
            with path.open("rb") as stream:
                resources = sorted(module.getRSZResourcePaths(stream))
            records.append({"path": str(path.relative_to(ROOT)), "resources": resources,
                            "mesh_references": [r for r in resources if ".mesh" in r.lower()]})
        except Exception as error:
            errors.append({"path": str(path.relative_to(ROOT)), "error": str(error)})
    write_json(ROOT / "reports/prefab_resources.json", {"status": "RESOURCE_REFERENCES_ONLY", "prefabs": records, "errors": errors,
               "limits": "Resource presence does not establish simultaneous visibility, instance ownership or runtime switching."})
    print(f"Read {len(records)} prefab resource tables; {len(errors)} errors. No prefab modified.")


if __name__ == "__main__":
    main()

