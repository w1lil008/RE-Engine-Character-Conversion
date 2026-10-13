"""Check native-export Blender geometry against the retained pre-revision scene."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import numpy as np
import hashlib
import json
from common import ROOT, write_json


def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects["GraceOriginalBindRig"]
    bones = [(b.name, [tuple(row) for row in b.matrix_local]) for b in rig.data.bones]
    objects = {}
    for obj in bpy.data.collections["Bela_on_Grace_Prototype"].objects:
        if obj.type != "MESH":
            continue
        objects[obj.name] = {"material": obj.data.materials[0].name.split(".")[0],
            "positions": np.asarray([v.co[:] for v in obj.data.vertices]),
            "topology_sha256": hashlib.sha256(np.asarray([p.vertices[:] for p in obj.data.polygons], dtype=np.uint32).tobytes()).hexdigest()}
    return bones, objects


def main():
    old_bones, old = snapshot(ROOT / "assets/work/BelaGrace_surface_baseline.blend")
    new_bones, new = snapshot(ROOT / "assets/work/BelaGrace_preparation.blend")
    if set(old) != set(new):
        raise ValueError("Assembly object set changed")
    settings = json.loads((ROOT / "config/prototype.json").read_text())
    limit = settings["garment_clearance"]["amount_m"] + .000001
    rows = []
    for name in sorted(old):
        before, after = old[name], new[name]
        same_topology = before["topology_sha256"] == after["topology_sha256"] and before["positions"].shape == after["positions"].shape
        if not same_topology:
            raise ValueError(f"Unexpected topology change: {name}")
        distance = np.linalg.norm(after["positions"] - before["positions"], axis=1)
        maximum = float(distance.max())
        garment = after["material"] in {"Dress_Mat", "DressBack_Mat"}
        permitted = maximum <= limit if garment else maximum == 0
        rows.append({"object": name, "material": after["material"], "topology_unchanged": same_topology,
                     "maximum_rest_displacement_m": maximum, "vertices_moved_over_1um": int(sum(distance > .000001)),
                     "change_within_declared_scope": permitted})
    passed = old_bones == new_bones and all(r["change_within_declared_scope"] for r in rows)
    write_json(ROOT / "reports/geometry_revision_audit.json", {"status": "DECLARED_GARMENT_CLEARANCE_CONFIRMED" if passed else "UNEXPECTED_CHANGE",
         "Grace_bind_matrices_unchanged": old_bones == new_bones, "maximum_permitted_garment_displacement_m": limit,
         "all_other_geometry_unchanged": all(r["maximum_rest_displacement_m"] == 0 for r in rows if r["material"] not in {"Dress_Mat", "DressBack_Mat"}),
         "objects": rows})
    if not passed:
        raise ValueError("Geometry revision exceeded its declared scope")
    print("Only Dress/DressBack clearance changed: <=25 mm; all other geometry and Grace bind matrices unchanged.")


if __name__ == "__main__":
    main()

