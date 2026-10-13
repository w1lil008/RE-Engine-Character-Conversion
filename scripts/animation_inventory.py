"""Create a structured research inventory from original animation metadata.

Suitability labels are hypotheses from names and references, never a claim of
decoded movement, verified uniqueness, or animation conversion implementation.
"""
import csv
import hashlib
import json
import re
from collections import Counter
from common import ROOT, write_json
from inspect_motion_metadata import inspect


def classify(path, name):
    text = name.lower()
    facial = 'facial' in path or 'facegallery' in path
    if facial:
        return (6, 'facial expression/pose (name-based)', 'Separate facial workstream; no body-MVP use', 'high')
    if any(w in text for w in ['attack', 'damage', 'dying', 'dead', 'grapple', 'break']):
        return (99, 'enemy combat/injury (name-based)', 'Excluded from playable MVP', 'research-dependent')
    if 'idle_loop' in text and 'freeze' not in text:
        return (1, 'idle posture (name-based)', 'Primary body prototype candidate; visual characterisation not yet verified', 'high')
    if any(w in text for w in ['idleto', 'runtoidle', 'turn', 'start', 'end']):
        return (7, 'transition (name-based)', 'Defer until one idle and blending are validated', 'high')
    if any(w in text for w in ['walk', 'run', 'move']):
        return (5, 'locomotion (name-based)', 'Later; needs root motion, foot contact and controller compatibility', 'high')
    if any(w in text for w in ['emotion', 'laugh', 'gesture', 'look']):
        return (3, 'gesture/upper body (name-based)', 'Inspect after idle; isolate safe joint mask', 'high')
    return (99, 'unclassified; requires visual inspection', 'Not selected for MVP', 'research-dependent')


def main():
    output = ROOT / 'reports/animation_research'
    output.mkdir(parents=True, exist_ok=True)
    games = {}
    for game in ['re8', 're9']:
        resources, errors = [], []
        for path in sorted((ROOT / 'assets/extracted' / game).rglob('*')):
            if path.is_file() and any(ext in path.name for ext in ['.mot.', '.motlist.', '.motbank.', '.jmap.', '.gpuc.']):
                try:
                    resources.append(inspect(path))
                except (ValueError, UnicodeError) as error:
                    errors.append({'path': path.relative_to(ROOT).as_posix(), 'error': str(error)})
        games[game] = {'resources': resources, 'errors': errors}
        write_json(output / (game + '_headers.json'), games[game])
    reverse = {}
    for resource in games['re8']['resources']:
        for entry in resource.get('list_entries', []):
            reverse.setdefault((entry['list_reference'] or '').lower(), []).append({'bank': resource['path'], **entry})
    rows = []
    for resource in games['re8']['resources']:
        if not resource.get('motions'):
            continue
        path = resource['path'].split('assets/extracted/re8/')[-1]
        short_reference = path.removeprefix('natives/stm/').rsplit('.', 1)[0]
        dependencies = reverse.get(short_reference.lower(), [])
        first_bones = next((m['own_rest_bones'] for m in resource['motions'] if m['own_rest_bones']), [])
        rest_hash = hashlib.sha256(json.dumps(first_bones, sort_keys=True).encode()).hexdigest() if first_bones else None
        for m in resource['motions']:
            priority, behavior, suitability, complexity = classify(path, m['name'] or '')
            indices = m.get('index_entries', [])
            asset_id = f"{path}::offset=0x{m['offset']:x}"
            if indices:
                asset_id += f"::motion_id={indices[0]['motion_id']}::switch={indices[0]['switch']}"
            if 'ch02_0020' in path or 'ch02_0000' in path:
                ownership = 'Bela-associated naming; uniqueness to Bela not proven'
            elif 'ch02_0500' in path:
                ownership = 'Daughters shared-family resource candidate; per-character invocation not proven'
            else:
                ownership = 'Other daughter/related resource; exclude until association proven'
            rows.append({'asset_path': path, 'asset_identifier': asset_id, 'clip_name': m['name'],
                         'index_entries': indices, 'associated_skeleton': {'bone_count_header': m['skeleton_bone_count_header'],
                             'own_or_inherited_list_rest_table_sha256': rest_hash, 'verified_mesh_skeleton_binding': False},
                         'frame_count': m['frame_count'], 'fps': m['fps'], 'duration_seconds_header': m['duration_seconds_from_frame_count'],
                         'bone_track_count': m['bone_track_count_header'], 'relevant_behavior': behavior,
                         'priority': priority, 'ownership': ownership, 'dependencies': dependencies,
                         'dependency_scope': 'Decoded bank references only; constraints, masks, events and physics need further inspection',
                         'suitability': suitability, 'extraction_status': 'EXTRACTED_FROM_LOCAL_OFFICIAL_PAK; header metadata inspected; keyframes not decoded',
                         'conversion_complexity': complexity, 'complexity_reason': 'Cross-generation rest axes, track mapping and native resource binding must be validated',
                         'resource_sha256': resource['sha256'], 'source_variant': '_ge additional-game-mode candidate' if '/_ge/' in path else 'base resource'})
    rows.sort(key=lambda r: (r['priority'], r['asset_path'], r['asset_identifier']))
    write_json(output / 'bela_animation_inventory.json', {'scope': 'Selected related resources, not every RE8 animation. Per-clip usage/uniqueness and keyframes are unverified.',
               'clip_records': len(rows), 'resource_files_with_motion_headers': sum(bool(r.get('motions')) for r in games['re8']['resources']),
               'reader_errors': games['re8']['errors'], 'clips': rows})
    with (output / 'bela_animation_inventory.csv').open('w', newline='', encoding='utf-8') as stream:
        keys = list(rows[0])
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in r.items()} for r in rows)
    write_json(output / 'summary.json', {'re8_motion_records': len(rows), 'priority_counts': dict(Counter(r['priority'] for r in rows)),
               'resources': {g: len(v['resources']) for g, v in games.items()}, 'errors': {g: v['errors'] for g, v in games.items()},
               'formats': {g: dict(Counter(r['header_version'] for r in v['resources'] if '.motlist.' in r['path'])) for g, v in games.items()},
               'native_payloads_or_animation_keyframes_written': False})
    print(f"Inventory: {len(rows)} RE8 related clip records; metadata only; no converted animations")
    for resource in games['re8']['resources']:
        if resource['path'].endswith('motbank/ch02_0500.motbank.3') or resource['path'].endswith('motbank/ch02_0000_facial.motbank.3'):
            print(resource['path'], 'joint map', resource.get('joint_map_reference'), 'lists', resource.get('list_entries'))


if __name__ == '__main__':
    main()

