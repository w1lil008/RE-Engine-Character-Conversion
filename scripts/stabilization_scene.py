"""Reimport all accepted native parts into an isolated Blender QA scene."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
from common import ROOT, reader, write_json
from analyze_assets import parsed_mesh
from blender_scene import create_mesh, make_material


def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "assets/work/BelaGrace_preparation.blend"))
    collection = bpy.data.collections["Bela_on_Grace_Prototype"]
    rig = bpy.data.objects["GraceOriginalBindRig"]
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    for obj in list(collection.objects):
        if obj.type == "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)
    build = json.loads((ROOT / "reports/mesh_build.json").read_text())
    material_build = json.loads((ROOT / "reports/material_build.json").read_text())
    previews = {"character/mods/belagrace/textures/" + Path(r["path"]).name.split(".tex")[0] + ".tex": ROOT / r["preview"]
                for r in material_build["textures"]}
    previews.update({k: ROOT / v for k, v in json.loads((ROOT / "reports/baseline_previews.json").read_text())["resources"].items()})
    mdf = reader("RE-Mesh-Editor", "remesh", "modules.mdf.file_re_mdf")
    rows, objects = [], []
    stage = ROOT / "mod/BelaGrace_RE9_0.1.2"
    for row in build["outputs"]:
        if "ch0200_40_01" in row["path"] or "ch0200_21_00" in row["path"]:
            continue
        parts = Path(row["path"]).parts
        path = stage / Path(*parts[parts.index("natives"):])
        _, mesh = parsed_mesh(path)
        for b in mesh.skeleton.boneList:
            stored = rig.data.bones[b.boneName]["reMeshWorldMatrix"]
            import numpy as np
            assert np.allclose(stored, b.worldMatrix.matrix, atol=1e-6, rtol=0)
        materials_file = next(path.parent.glob(path.name.split(".mesh")[0] + "*.mdf2.51"))
        materials = {m.materialName: make_material(m, previews) for m in mdf.readMDF(str(materials_file)).materialList}
        created = create_mesh(row["part"], mesh, rig, materials, collection)
        objects.extend(created)
        rows.append({"part": row["part"], "native": path.relative_to(ROOT).as_posix(), "objects": len(created)})
    scene_path = ROOT / "build/stabilization/BelaGrace_accepted_native.blend"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.scene["PROJECT_STATUS"] = "Current v0.1.2 natives reimported; synthetic QA only"
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))
    write_json(ROOT / "reports/stabilization/native_scene.json", {"scene": scene_path.relative_to(ROOT).as_posix(),
               "source": "Current accepted v0.1.2 binaries", "objects": len(objects), "parts": rows,
               "original_bind_matrices_verified": True, "native_payloads_changed": False})
    print(f"Reimported {len(objects)} objects from accepted native assets")


if __name__ == "__main__":
    main()

