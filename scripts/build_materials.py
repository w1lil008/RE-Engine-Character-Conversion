"""Build RE9-native prototype MDFs and convert Bela textures using proven tools.

RE8 shaders are replaced with RE9 presets. ATOC -> ACOT swaps G and A.
Specialized eyes, wrinkle controls and wetness are intentionally approximate.
"""
import copy
import hashlib
import json
import ctypes
import io
import struct
from pathlib import Path
from PIL import Image
from common import ROOT, reader, write_json
from extract_assets import load_names

MOD = ROOT / "mod/BelaGrace_RE9"
CACHE = ROOT / "assets/work/textures"
REPORTS = ROOT / "reports"
DEPENDENCIES_OUTPUT = ROOT / "config/re9_material_dependencies.txt"


def acot_from_atoc(image):
    r, g, b, a = image.convert("RGBA").split()
    return Image.merge("RGBA", (r, a, b, g))


def decode_dds(path):
    data = bytearray(Path(path).read_bytes())
    if data[84:88] == b"DX10":
        fmt = struct.unpack_from("<I", data, 128)[0]
        # Pillow decodes the corresponding UNORM block formats; sRGB block data
        # is identical, and PNG retains the encoded color values for display.
        struct.pack_into("<I", data, 128, {72: 71, 75: 74, 78: 77, 99: 98}.get(fmt, fmt))
    return Image.open(io.BytesIO(data)).convert("RGBA")


def make_preset(module, name, source):
    path = next((ROOT / "tools").glob(f"RE-Mesh-Editor-*/Presets/RE9/{name}.json"))
    preset = json.loads(path.read_text())
    mat = module.Material()
    mat.materialName = source.materialName
    mat.mmtrPath = preset["Material Header"]["Master Material Path"]
    mat.shaderType = int(preset["Material Header"]["Material Shader Type"])
    mat.flags.asInt32 = preset["Flags"]["FlagBitFlag"]
    mat.flagsB.asInt32 = preset["Flags"]["FlagBitFlagB"]
    props = source.getPropertyDict()
    aliases = {"Occlusion_Color": "OcclusionColor", "Primaly_SpecularColor": "PrimalySpecularColor",
               "Secondary_SpecularColor": "SecondarySpecularColor", "CutScene_BaseColor": "BaseColor"}
    for entry in preset["Property List"]:
        p = module.Property()
        p.propName = entry["Property Name"]
        value = entry["Value"]
        p.propValue = list(value) if isinstance(value, list) else [float(value)]
        original = props.get(aliases.get(p.propName, p.propName))
        # Only copy color/tint properties whose dimensionality agrees.
        if original and "color" in p.propName.lower() and len(original.propValue) == len(p.propValue):
            p.propValue = list(original.propValue)
        p.paramCount = len(p.propValue)
        p.padding = entry.get("Padding", 0)
        mat.propertyList.append(p)
    for entry in preset["Texture Bindings"]:
        t = module.TextureBinding()
        t.textureType, t.texturePath = entry["Texture Type"], entry["Texture Path"]
        mat.textureList.append(t)
    return mat


def relocated_native_material(source):
    result = copy.deepcopy(source)
    # With no GPBF entries, the upstream writer only relocates this field when
    # it is zero. Keeping a read-time offset makes its string table overwrite
    # unrelated headers after materials are combined into a different MDF.
    result.GPUBufferOffset = 0
    return result


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    ctypes.windll.ole32.CoInitializeEx(None, 0)  # Texconv's WIC codecs require COM.
    mdf_module = reader("RE-Mesh-Editor", "remesh", "modules.mdf.file_re_mdf")
    tex_utils = reader("RE-Mesh-Editor", "remesh", "modules.tex.re_tex_utils")
    tex_file = reader("RE-Mesh-Editor", "remesh", "modules.tex.file_re_tex")
    converter = reader("RE-Mesh-Editor", "remesh", "modules.ddsconv.directx.texconv").Texconv()
    old_names = {n.lower(): n for n in load_names("re8")}
    new_names = {n.lower(): n for n in load_names("re9")}
    converted, records = {}, []

    def convert_texture(resource, swizzle=False):
        key = (resource.lower(), swizzle)
        if key in converted:
            return converted[key]
        old_path = "natives/stm/" + resource.lower() + ".30"
        if old_path not in old_names:
            raise ValueError(f"Missing source texture name {resource}")
        source = ROOT / "assets/extracted/re8" / old_names[old_path]
        high_resolution = ROOT / "assets/extracted/re8" / old_names[old_path].replace("natives/stm/", "natives/stm/streaming/", 1)
        if high_resolution.is_file():
            source = high_resolution
        identifier = hashlib.sha1(resource.lower().encode()).hexdigest()[:8] + "_" + Path(resource).stem
        dds_path = CACHE / (identifier + ".dds")
        info = tex_utils.convertTexFileToDDS(str(source), str(dds_path))
        if info["isArray"]:
            raise ValueError(f"Prototype expects single-image texture: {resource}")
        png_path = dds_path.with_suffix(".png")
        decode_dds(dds_path).save(png_path)
        if swizzle:
            identifier += "_acot"
            png_path = CACHE / (identifier + ".png")
            with decode_dds(dds_path) as original:
                acot_from_atoc(original).save(png_path)
            dds_path = Path(converter.convert_to_dds(str(png_path), "BC7_UNORM", out=str(CACHE), verbose=False))
        relative = f"Character/Mods/BelaGrace/Textures/{identifier}.tex"
        output = MOD / ("natives/stm/" + relative.lower() + ".250813143")
        output.parent.mkdir(parents=True, exist_ok=True)
        tex_utils.DDSToTex([str(dds_path)], 250813143, str(output))
        check = tex_file.RE_TexFile()
        check.read(str(output))
        if check.tex.header.version != 250813143:
            raise ValueError("Texture header version mismatch")
        # Reopen the GDeflate payload, proving it decompresses to identical DDS.
        roundtrip = CACHE / (identifier + "_roundtrip.dds")
        tex_utils.convertTexFileToDDS(str(output), str(roundtrip))
        before, after = dds_path.read_bytes(), roundtrip.read_bytes()
        # DDS metadata such as DDSCAPS_COMPLEX is canonicalized by the reader.
        # Verify dimensions/mip count/DXGI format and every encoded mip byte.
        if before[12:32] != after[12:32] or before[128:132] != after[128:132] or before[148:] != after[148:]:
            raise ValueError(f"DDS/TEX pixel payload roundtrip differed: {resource}")
        converted[key] = relative
        records.append({"source": resource, "path": str(output.relative_to(ROOT)), "preview": str(png_path.relative_to(ROOT)),
                        "swizzle": "RABG" if swizzle else "unchanged", "width": check.tex.header.width,
                        "height": check.tex.header.height, "dds_payload_roundtrip_equal": True,
                        "used_streaming_source": source == high_resolution})
        return relative

    source_groups = {}
    for name, hint in [("ch02_0000_body", "Character"), ("ch02_0201_gpucloth", "Character"),
                       ("ch02_0020_face", "Character"), ("ch02_0040_bela_hair", "Hair")]:
        source_path = next((ROOT / "assets/extracted/re8").rglob(name + ".mdf2.19"))
        source_mdf = mdf_module.readMDF(str(source_path))
        result = mdf_module.MDFFile()
        for source in source_mdf.materialList:
            preset = "Hair" if hint == "Hair" or "eyelash" in source.materialName or "eyebrow" in source.materialName else "Character"
            mat = make_preset(mdf_module, preset, source)
            bindings = {t.textureType: t for t in source.textureList}
            for t in mat.textureList:
                source_type = t.textureType
                if source_type == "AlphaCavityOcclusionTranslucentMap":
                    source_type = "AlphaTranslucentOcclusionCavityMap"
                if source_type == "BaseShiftMap" and source_type not in bindings:
                    source_type = "BaseDielectricMap"
                if source_type in bindings and source_type in {"BaseDielectricMap", "BaseShiftMap", "NormalRoughnessMap", "AlphaTranslucentOcclusionCavityMap"}:
                    t.texturePath = convert_texture(bindings[source_type].texturePath,
                                                    source_type == "AlphaTranslucentOcclusionCavityMap")
            result.materialList.append(mat)
        key = "hair" if hint == "Hair" else ("face" if "face" in name else "body")
        if key in source_groups:
            source_groups[key].materialList += result.materialList
        else:
            source_groups[key] = result

    settings = json.loads((ROOT / "config/prototype.json").read_text())
    if settings.get("footwear_fit") == "original_Grace_boots":
        original_boot_mdf = next((ROOT / "assets/extracted/re9/natives/stm/character/ch/ch02/0200/50/00").glob("ch0200_50_00_00.mdf2.51"))
        original_materials = mdf_module.readMDF(str(original_boot_mdf))
        source_groups["body"].materialList += [relocated_native_material(m) for m in original_materials.materialList if "_Boots_" in m.materialName]

    build = json.loads((REPORTS / "mesh_build.json").read_text())
    written = []
    baseline_dependencies = set()
    for row in build["outputs"]:
        source = source_groups[row["part"] if row["part"] in ["face", "hair"] else "body"]
        mesh_path = ROOT / row["path"]
        stem = mesh_path.name.split(".mesh")[0]
        target_dir = ROOT / "assets/extracted/re9" / mesh_path.parent.relative_to(MOD)
        variants = sorted(target_dir.glob(stem + "*.mdf2.51"))
        if not variants:
            raise ValueError(f"No original MDF variants for {stem}")
        for original in variants:
            path = mesh_path.parent / original.name
            mdf_module.writeMDF(copy.deepcopy(source), str(path))
            checked = mdf_module.readMDF(str(path))
            if {m.materialName for m in checked.materialList} != set(row["materials"]):
                raise ValueError(f"MDF/mesh material names disagree: {path}")
            written.append(str(path.relative_to(ROOT)))
        for mat in source.materialList:
            for t in mat.textureList:
                if "/Mods/BelaGrace/" not in t.texturePath:
                    wanted = "natives/stm/" + t.texturePath.lstrip("@").lower() + ".250813143"
                    if wanted not in new_names:
                        raise ValueError(f"Preset references unknown RE9 texture: {t.texturePath}")
                    baseline_dependencies.add(new_names[wanted])
    write_json(REPORTS / "material_build.json", {"status": "OFFLINE_BINARY_ROUNDTRIP_ONLY", "mdfs": written,
               "textures": records, "baseline_dependencies": sorted(baseline_dependencies),
               "limitations": ["Approximate eyes and skin using RE9 Character shader", "Neutral face only", "Static hair; Strands OFF"]})
    DEPENDENCIES_OUTPUT.write_text("\n".join(sorted(baseline_dependencies)) + "\n")
    print(f"Built {len(written)} MDFs and {len(records)} RE9 textures. No in-game test performed.")


if __name__ == "__main__":
    main()

