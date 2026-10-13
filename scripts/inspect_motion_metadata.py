"""Read-only MOT/MOTLIST header inventory, NOT an animation decoder/converter.

Field offsets checked against ReeLib ceb0d2f MotHeader/Header. No keyframes,
compression, clip semantics, controller behaviour, or retargeting is decoded.
"""
import argparse
import hashlib
import struct
from common import ROOT, confined, write_json


def unpack(data, fmt, offset):
    size = struct.calcsize(fmt)
    if offset < 0 or offset + size > len(data):
        raise ValueError(f"Out-of-bounds metadata read: {offset}+{size}/{len(data)}")
    return struct.unpack_from(fmt, data, offset)


def wstring(data, offset):
    if offset == 0:
        return None
    if offset < 0 or offset >= len(data):
        raise ValueError(f"Invalid string pointer: {offset}")
    end = offset
    while end + 2 <= len(data) and data[end:end + 2] != b"\0\0":
        end += 2
    if end + 2 > len(data):
        raise ValueError("Unterminated UTF16 metadata string")
    return data[offset:end].decode("utf-16-le")


def motion(data, base=0):
    version, magic = unpack(data, "<II", base)
    if version not in {458, 983} or magic != 0x20746F6D:
        raise ValueError(f"Unsupported MOT header: {version}/{magic:x}")
    name_offset, = unpack(data, "<Q", base + 88)
    frames, blending, start, end = unpack(data, "<4f", base + 96)
    bones, bone_tracks = unpack(data, "<HH", base + 112)
    fps, = unpack(data, "<H", base + 120)
    name = wstring(data, base + name_offset) if name_offset else None
    bone_header, = unpack(data, "<Q", base + 16)
    size, = unpack(data, "<I", base + 12)
    rest_bones = []
    if bone_header and (size == 0 or bone_header < size):
        _, count = unpack(data, "<QQ", base + bone_header)
        if count > 10000:
            raise ValueError("Implausible rest-bone table")
        for index in range(count):
            offset = base + bone_header + 16 + index * 80
            pointer, parent, child, sibling = unpack(data, "<QQQQ", offset)
            index_value, hash_value = unpack(data, "<II", offset + 64)
            rest_bones.append({"name": wstring(data, base + pointer), "index": index_value,
                               "name_hash": hash_value, "parent_record_offset": parent,
                               "translation_header": list(unpack(data, "<3f", offset + 32)),
                               "quaternion_xyzw_header": list(unpack(data, "<4f", offset + 48))})
    return {"offset": base, "mot_version": version, "name": name, "frame_count": frames,
            "start_frame": start, "end_frame": end, "fps": fps,
            "duration_seconds_from_frame_count": frames / fps if fps else None,
            "skeleton_bone_count_header": bones, "bone_track_count_header": bone_tracks,
            "blending_header": blending, "keyframes_decoded": False,
            "own_rest_bones": rest_bones,
            "rest_table_scope": "Raw MOT metadata; coordinate semantics not experimentally confirmed"}


def inspect(path):
    data = path.read_bytes()
    version, magic = unpack(data, "<II", 0)
    row = {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data),
           "sha256": hashlib.sha256(data).hexdigest(), "header_version": version,
           "magic_hex": hex(magic), "scope": "Header metadata only"}
    if ".motlist." in path.name:
        if version not in {486, 1047} or magic != 0x74736C6D:
            raise ValueError("Unsupported MOTLIST header")
        pointers, indices, name = unpack(data, "<QQQ", 16)
        count, = unpack(data, "<I", 56 if version >= 1036 else 48)
        if count > 100000:
            raise ValueError("Implausible motion count")
        row.update({"list_name": wstring(data, name), "motion_slot_count": count,
                    "index_table_offset": indices, "motions": [], "non_mot_slots": []})
        if version >= 1036:
            ptr, = unpack(data, "<Q", 48)
            pack = unpack(data, "<Q", ptr)[0] if ptr else 0
            row["motpack_reference"] = wstring(data, pack)
        seen = {}
        for slot in range(count):
            off, = unpack(data, "<Q", pointers + slot * 8)
            record_size = 24 if version == 486 else 72
            values = unpack(data, "<QHHIIBBBB", indices + slot * record_size)
            descriptor = {"slot": slot, "motion_id": values[1], "switch": values[2],
                          "joint_mask_id": values[3], "tag_hash": values[4], "type": values[5],
                          "flags": values[6], "physics_flags": values[7], "override_clip_count": values[8]}
            if not off:
                continue
            if off in seen:
                seen[off]["index_entries"].append(descriptor)
                continue
            ver, tag = unpack(data, "<II", off)
            if tag == 0x20746F6D:
                m = motion(data, off)
                m["first_slot"] = slot
                m["index_entries"] = [descriptor]
                seen[off] = m
                row["motions"].append(m)
            else:
                m = {"slot": slot, "offset": off, "version": ver, "magic": hex(tag), "index_entries": [descriptor]}
                seen[off] = m
                row["non_mot_slots"].append(m)
    elif ".mot." in path.name:
        row["motions"] = [motion(data)]
    elif ".motbank." in path.name:
        if version not in {3, 4} or magic != 0x6B6E626D:
            raise ValueError("Unsupported MOTBANK header")
        table, uvar, jmap = unpack(data, "<QQQ", 16)
        count, = unpack(data, "<I", 40)
        if count > 100000:
            raise ValueError("Implausible bank entry count")
        entries = []
        for index in range(count):
            pointer, bank_id, bank_type, mask = unpack(data, "<QiIQ", table + index * 24)
            entries.append({"list_reference": wstring(data, pointer), "bank_id": bank_id,
                            "bank_type": bank_type, "type_mask_bits": mask})
        row.update({"uvar_reference": wstring(data, uvar), "joint_map_reference": wstring(data, jmap),
                    "list_entries": entries, "scope": "Bank references and IDs only; runtime registration not verified"})
    else:
        row["scope"] = "Header identity only; semantic parsing not performed"
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", choices=["re8", "re9"], required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    paths = sorted(p for p in (ROOT / "assets/extracted" / args.game).rglob("*") if p.is_file() and
                   any(x in p.name for x in [".motlist.", ".mot.", ".motbank.", ".jmap.", ".gpuc."]))
    results, errors = [], []
    for path in paths:
        try:
            results.append(inspect(path))
        except (ValueError, UnicodeError, struct.error) as exc:
            errors.append({"path": path.relative_to(ROOT).as_posix(), "error": str(exc)})
    write_json(confined(ROOT, args.report), {"reader_reference": "ReeLib ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef",
               "scope": "Research inventory, no keyframe decoding or writing", "resources": results, "errors": errors})
    print(f"Inspected {len(results)} resource headers; {len(errors)} errors")


if __name__ == "__main__":
    main()

