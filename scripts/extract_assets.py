"""Read-only selective extraction using RE Asset Library's PAK parser.

Never opens game files for writing. Keeps highest official patch per resource,
records provenance, validates decompressed lengths and rejects unsafe paths.
"""
import argparse
import hashlib
import json
import re
import zlib
import io
import struct
from collections import defaultdict
from pathlib import Path
from common import ROOT, reader, write_json, confined


def official_paks(game):
    # Exclude pak_mods and other installed user mods from the original baseline.
    base = [p for p in game.glob("re_chunk_*.pak") if ".patch_" not in p.name]
    patches = [p for p in game.glob("re_chunk_*.pak") if ".patch_" in p.name]
    patches.sort(key=lambda p: (int(re.search(r"\.patch_(\d+)\.pak$", p.name)[1]), p.name))
    dlc = sorted((game / "dlc").rglob("re_dlc*.pak")) if (game / "dlc").exists() else []
    return sorted(base) + patches + dlc


def load_names(game):
    folder = next((ROOT / "tools").glob("REE.PAK.Tool-*/Projects"))
    return [line.strip() for line in (folder / f"{game.upper()}_STM_Release.list").read_text(encoding="utf-8-sig").splitlines() if line.startswith("natives/")]


def build_lookup(paths, wanted):
    pak_module = reader("RE-Asset-Library", "reasset", "modules.pak.file_re_pak")
    fast = reader("RE-Asset-Library", "reasset", "modules.hashing.mmh3.fastmmh3").FastMMH3()
    hash_to_names = defaultdict(list)
    for name in wanted:
        hash_to_names[fast.pakHash(name)].append(name)
    matches = {}
    inventory = []
    for path in paths:
        with path.open("rb") as stream:
            pak = pak_module.PakFile()
            pak.readTOC(stream)  # Fail visibly rather than silently skipping broken archives.
        inventory.append({"path": str(path), "bytes": path.stat().st_size,
                          "mtime_ns": path.stat().st_mtime_ns, "header": vars(pak.header),
                          "entries": len(pak.toc.entryList)})
        found = 0
        for entry in pak.toc.entryList:
            key = (entry.hashNameLower << 32) | entry.hashNameUpper
            for name in hash_to_names.get(key, []):
                matches[name] = (path, entry)
                found += 1
        print(f"{path.name}: {len(pak.toc.entryList)} entries; {found} requested matches", flush=True)
    return matches, inventory


def extract(matches, destination):
    import zstandard
    decrypt = reader("RE-Asset-Library", "reasset", "modules.encryption.re_pak_encryption").decryptResource
    records = []
    streams = {}
    try:
        for name, (pak_path, entry) in sorted(matches.items()):
            path = confined(destination, name)
            size = pak_path.stat().st_size
            stored_size = entry.compressedSize if entry.compressedSize else entry.decompressedSize
            if entry.offset < 16 or entry.offset + stored_size > size:
                raise ValueError(f"Invalid PAK extent: {name}")
            if entry.decompressedSize > 512 * 1024 * 1024:
                raise ValueError(f"Resource exceeds selective extraction limit: {name}")
            if pak_path not in streams:
                streams[pak_path] = pak_path.open("rb")
            stream = streams[pak_path]
            stream.seek(entry.offset)
            data = stream.read(stored_size)
            if len(data) != stored_size:
                raise ValueError(f"Truncated resource: {name}")
            if entry.encryptionType:
                data = decrypt(data)
            if entry.compressionType == 1:
                data = zlib.decompress(data, wbits=-15)
            elif entry.compressionType == 2:
                data = zstandard.ZstdDecompressor().decompress(data, max_output_size=entry.decompressedSize)
            elif entry.compressionType != 0:
                raise ValueError(f"Unknown compression {entry.compressionType}: {name}")
            size_validation = "exact"
            decoded_texture_bytes = None
            if len(data) != entry.decompressedSize:
                # RE9 can store an internally GDeflated TEX with outer PAK
                # compression=0. The TOC's decompressed size describes the
                # logical TEX including decoded mips, not the encoded file.
                if entry.compressionType == 0 and name.endswith(".tex.250813143") and len(data) >= 40 and struct.unpack_from("<II", data) == (5784916, 250813143):
                    module = reader("RE-Mesh-Editor", "remesh", "modules.tex.file_re_tex")
                    texture = module.Tex()
                    texture.read(io.BytesIO(data))  # Decode every GDeflate mip; fail on invalid payloads.
                    header_stream = io.BytesIO(data)
                    texture.header.read(header_stream)
                    logical_size = header_stream.tell() + 24 * texture.header.imageCount * texture.header.mipCount
                    logical_size += sum(m.uncompressedSize for image in texture.imageMipDataList for m in image)
                    if logical_size != entry.decompressedSize:
                        raise ValueError(f"GDeflate TEX logical size mismatch: {name}: {logical_size} vs {entry.decompressedSize}")
                    decoded_texture_bytes = sum(len(m.textureData) for image in texture.imageMipDataList for m in image)
                    size_validation = "gdeflate_texture_logical_size_and_mip_decode"
                else:
                    raise ValueError(f"Decompressed length mismatch: {name}: {len(data)} vs {entry.decompressedSize}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            records.append({"path": name, "pak": str(pak_path), "offset": entry.offset,
                            "bytes": len(data), "pak_logical_bytes": entry.decompressedSize, "size_validation": size_validation,
                            "decoded_texture_bytes": decoded_texture_bytes, "sha256": hashlib.sha256(data).hexdigest()})
    finally:
        for stream in streams.values():
            stream.close()
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", choices=["re8", "re9"])
    parser.add_argument("--prefix", action="append", default=[])
    parser.add_argument("--paths", type=Path, help="Newline-delimited exact native resource paths")
    parser.add_argument("--extensions", default="mesh,mdf2,tex,fbxskel,chain,chain2,clsp,jntexprgraph,jcns,pfb,user")
    parser.add_argument("--scan-only", action="store_true")
    parser.add_argument("--report-name", help="Separate report stem for dependency/diagnostic runs")
    args = parser.parse_args()
    report_name = args.report_name or args.game
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", report_name):
        parser.error("Report name must contain only letters, numbers, underscore or hyphen")
    config = json.loads((ROOT / "config/project.json").read_text())
    names = load_names(args.game)
    extensions = args.extensions.split(",")
    prefixes = args.prefix or [config["source_prefix" if args.game == "re8" else "target_prefix"]]
    wanted = [n for n in names if any(n.lower().startswith(p.lower()) for p in prefixes)
              and any(f".{ext}." in n for ext in extensions)]
    if args.paths:
        wanted = sorted(set(wanted) | {n.strip() for n in args.paths.read_text().splitlines() if n.strip()})
    # Streaming companions contain vertex/texture data required by main resources.
    all_names = set(names)
    wanted += [companion for n in list(wanted)
               if (companion := n.replace("natives/stm/", "natives/stm/streaming/", 1)) in all_names]
    if not wanted:
        raise SystemExit("No paths selected; review prefixes/list version")
    write_json(ROOT / f"reports/{report_name}_selection.json", wanted)
    matches, inventory = build_lookup(official_paks(Path(config["games"][args.game])), wanted)
    report = {"game": args.game, "requested": len(wanted), "found": len(matches),
              "missing": sorted(set(wanted) - set(matches)), "archives": inventory}
    write_json(ROOT / f"reports/{report_name}_inventory.json", report)
    if not args.scan_only:
        records = extract(matches, ROOT / f"assets/extracted/{args.game}")
        write_json(ROOT / f"reports/{report_name}_extraction.json", records)
        print(f"Extracted {len(records)} files ({sum(r['bytes'] for r in records):,} bytes)")
    print(f"Missing {len(report['missing'])} requested resources; see inventory report")


if __name__ == "__main__":
    main()

