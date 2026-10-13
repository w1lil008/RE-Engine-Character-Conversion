"""Decode original Grace boot base textures for an honest assembled preview."""
import hashlib
import json
from common import ROOT, reader, write_json
from extract_assets import load_names
from build_materials import decode_dds


def main():
    module = reader("RE-Mesh-Editor", "remesh", "modules.mdf.file_re_mdf")
    convert = reader("RE-Mesh-Editor", "remesh", "modules.tex.re_tex_utils")
    native_names = {n.lower(): n for n in load_names("re9")}
    original = next((ROOT / "assets/extracted/re9").rglob("ch0200_50_00_00.mdf2.51"))
    materials = module.readMDF(str(original)).materialList
    cache = ROOT / "assets/work/baseline_textures"
    cache.mkdir(parents=True, exist_ok=True)
    records = {}
    for material in materials:
        if "_Boots_" not in material.materialName:
            continue
        for texture in material.textureList:
            if texture.textureType not in {"BaseDielectricMap", "BaseShiftMap"}:
                continue
            resource = texture.texturePath.lower()
            if resource in records:
                continue
            native = "natives/stm/" + resource.lstrip("@") + ".250813143"
            source = ROOT / "assets/extracted/re9" / native_names[native]
            streaming = ROOT / "assets/extracted/re9" / native_names[native].replace("natives/stm/", "natives/stm/streaming/", 1)
            if streaming.is_file():
                source = streaming
            if not source.is_file():
                raise ValueError("Extract RE9 material dependencies before previewing original boots")
            identifier = hashlib.sha1(resource.encode()).hexdigest()[:12]
            dds = cache / (identifier + ".dds")
            info = convert.convertTexFileToDDS(str(source), str(dds))
            if info["isArray"]:
                raise ValueError("Boot base texture unexpectedly uses an array; preview needs a layer selection")
            png = dds.with_suffix(".png")
            decode_dds(dds).save(png)
            records[resource] = str(png.relative_to(ROOT))
    write_json(ROOT / "reports/baseline_previews.json", {"resources": records, "in_game_tested": False})
    print(f"Decoded {len(records)} original boot base textures for preview only.")


if __name__ == "__main__":
    main()

