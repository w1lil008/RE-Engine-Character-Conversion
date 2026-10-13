"""Resolve material texture paths against the game-specific filename lists."""
import json
from common import ROOT, write_json
from extract_assets import load_names


def main():
    data = json.loads((ROOT / "reports/material_analysis.json").read_text())
    names = {n.lower(): n for n in load_names("re8")}
    wanted, missing = set(), set()
    for row in data["re8"]:
        for mat in row["materials"]:
            for tex in mat["textures"]:
                resource = "natives/stm/" + tex["path"].lower() + ".30"
                if resource in names:
                    wanted.add(names[resource])
                else:
                    missing.add(resource)
    (ROOT / "config/re8_dependencies.txt").write_text("\n".join(sorted(wanted)) + "\n")
    write_json(ROOT / "reports/source_dependencies.json", {"textures": sorted(wanted), "missing": sorted(missing)})
    print(f"Resolved {len(wanted)} texture dependencies; {len(missing)} missing")


if __name__ == "__main__":
    main()

