"""Read-only Milestone D evidence collection and capture analysis. No installer."""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path
from common import ROOT, confined, write_json
from source_animation_workflow import sha
from native_animation_protection import protect as protect_previous
from extract_assets import official_paks, load_names, build_lookup, extract
from native_mot import decode_float_mot

CHECKPOINT = '91ee9fe'
REPORTS = ROOT / 'reports/runtime_binding_v0.2.0'
OUTPUT = ROOT / 'build/animation_v0.2.0/runtime_stage1'
NATIVE = ROOT / 'build/animation_v0.2.0/native_idle_canonical/native'
C_ZIP_SHA = 'dac44bd1b37af7febcdf46754a84475994708386a59b810098553e7a6bd93b44'
FRAMEWORK_COMMIT = 'd1461375aee4ec3f313170f8eaad12064eb542d9'


def protect_checkpoint():
    previous = protect_previous()
    phase = json.loads((ROOT / 'reports/native_animation_v0.2.0/phase_results.json').read_text())
    records = phase['local_artifacts'] + phase['source_code_hashes']
    for row in records:
        if sha(confined(ROOT, row['path'])) != row['sha256']:
            raise ValueError('Accepted Milestone C file changed: ' + row['path'])
    tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', CHECKPOINT,
        'reports/native_animation_v0.2.0', 'docs/NATIVE_ANIMATION_V0.2.0.md'], cwd=ROOT, text=True).splitlines()
    for name in tracked:
        expected = subprocess.check_output(['git', 'show', CHECKPOINT + ':' + name], cwd=ROOT)
        # Git stores normalized text; the accepted checkout deliberately uses CRLF JSON.
        eol = subprocess.check_output(['git', 'check-attr', 'eol', '--', name], cwd=ROOT, text=True).strip().split(': ')[-1]
        if eol == 'crlf': expected = expected.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        if confined(ROOT, name).read_bytes() != expected:
            raise ValueError('Milestone C checkpoint report changed: ' + name)
    archive = ROOT / phase['package']
    if sha(archive) != C_ZIP_SHA:
        raise ValueError('Milestone C archive changed')
    return {'status': 'PASSED', 'checkpoint': CHECKPOINT, 'native_runtime_tested': False,
        'milestone_C_artifacts_and_sources': len(records), 'checkpoint_reports_and_document': len(tracked),
        'archive_sha256': C_ZIP_SHA, 'previous': previous}


def snapshot_files(folder, prefix):
    if not folder.exists():
        return []
    return [{'path': prefix + '/' + p.relative_to(folder).as_posix(), 'bytes': p.stat().st_size,
        'sha256': sha(p)} for p in sorted(folder.rglob('*')) if p.is_file()]


def environment():
    """Inventory only specified game/mod/Steam save paths. Never opens files for writing."""
    game = Path(json.loads((ROOT / 'config/project.json').read_text())['games']['re9'])
    steam = game.parents[1]
    appmanifest = steam / 'appmanifest_3764200.acf'
    acf = appmanifest.read_text()
    def vdf(name):
        match = re.search(r'"' + name + r'"\s+"([^"]*)"', acf)
        return match[1] if match else None
    log = (game / 're2_framework_log.txt').read_text(errors='replace')
    commit = re.search(r'Commit hash: ([0-9a-f]+)', log)
    tdb = re.search(r'TDB Version: (\d+)', log)
    def file_record(p):
        return {'path': p.relative_to(game).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)}
    protected = [file_record(game / name) for name in ('re9.exe', 'dinput8.dll', 'dxgi.dll',
        'renodx-dlss.addon64', 'BUILD_MANIFEST.json', 'ModdedByFluffyModManager.txt') if (game / name).is_file()]
    protected += snapshot_files(game / 'natives', 'natives') + snapshot_files(game / 'pak_mods', 'pak_mods')
    protected += snapshot_files(game / 'reframework/autorun', 'reframework/autorun')
    protected += snapshot_files(game / 'reframework/plugins', 'reframework/plugins')
    # Existing unrelated mod configuration is protected, generated diagnostics are excluded.
    protected += [r for r in snapshot_files(game / 'reframework/data', 'reframework/data') if not r['path'].startswith('reframework/data/bela_d1/')]
    saves = []
    for account in sorted((steam.parent / 'userdata').glob('*')):
        alias = hashlib.sha256(account.name.encode()).hexdigest()[:12]
        saves += snapshot_files(account / '3764200', 'steam-save-account-' + alias + '/3764200')
    current = {r['path']: r for r in protected}
    installed = []
    for version in ('0.1.2', '0.1.3'):
        files = json.loads((ROOT / f'reports/releases/{version}/mod_validation.json').read_text())['files']
        matches = sum(current.get(r['path'], {}).get('sha256') == r['sha256'] for r in files)
        installed.append({'version': version, 'matching_loose_native_files': matches, 'expected_files': len(files),
            'runtime_acceptance': 'Recorded ADS hair/hood scope only' if version == '0.1.2' else 'Explicit in-game confirmation pending'})
    ps = "Get-Process -Name re9 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName | ConvertTo-Json -Compress"
    running = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout.strip()
    escaped = str(game / 're9.exe').replace("'", "''")
    versions = subprocess.check_output(['powershell', '-NoProfile', '-Command',
        f"(Get-Item -LiteralPath '{escaped}').VersionInfo | Select-Object FileVersion,ProductVersion | ConvertTo-Json -Compress"], text=True)
    return {'game_directory': str(game), 'steam_app_id': vdf('appid'), 'steam_build_id': vdf('buildid'),
        'target_build_id': vdf('TargetBuildID'), 'exe_versions': json.loads(versions),
        'appmanifest_sha256': sha(appmanifest),
        'framework_log_commit': commit[1] if commit else None, 'framework_log_tdb_version': int(tdb[1]) if tdb else None,
        'framework_log_is_historical_not_live_binding': True, 'game_process': json.loads(running) if running else None,
        'protected_installed_files': protected, 'installed_release_comparison': installed,
        'steam_save_files': saves, 'save_scope': 'Existing Steam userdata/*/3764200 only; other possible save locations not asserted',
        'official_archives': [{'name': p.relative_to(game).as_posix(), 'bytes': p.stat().st_size,
            'mtime_ns': p.stat().st_mtime_ns} for p in official_paks(game)],
        'official_archive_content_hashes_taken': False, 'game_or_save_write_operations': 0}


def parse_joint_map(path):
    """JMAP28 bounded mask/IK reader, from pinned ReeLib JmapFile.cs. No writer."""
    raw = path.read_bytes()
    def read(fmt, offset):
        if offset < 0 or offset + struct.calcsize(fmt) > len(raw):
            raise ValueError('Joint-map pointer outside file')
        return struct.unpack_from(fmt, raw, offset)
    if read('<II', 0) != (28, 0x70616D6A):
        raise ValueError('Expected RE9 JMAP28')
    mask_offset, expr, extra, pad, ik_offset, symmetry, symmetry2 = read('<7Q', 16)
    if pad or any(read('<4Q', 72)):
        raise ValueError('Unknown JMAP28 reserved fields')
    skeleton = read('<Q', 104)[0]
    flags, groups, ik_count = read('<IHB', 112)
    if groups > 256 or ik_count > 128:
        raise ValueError('Implausible map counts')
    native = decode_float_mot((NATIVE / 'bela_idle.mot.983').read_bytes())
    names = {b['hash']: b['name'] for b in native['bones']}
    masks = []
    for i in range(groups):
        hashes, mask, weights, group_id, count = read('<QQQIH', mask_offset + i * 32)
        if count > 10000 or not hashes or not mask:
            raise ValueError('Invalid joint-mask group')
        rows = []
        for j in range(count):
            h = read('<I', hashes + j * 4)[0]
            rows.append({'hash': h, 'name_from_native_rest_table': names.get(h),
                'mask_byte': read('<B', mask + j)[0],
                'weight': read('<f', weights + j * 4)[0] if weights else None})
        masks.append({'group_id': group_id, 'joints': rows})
    ik = []
    for i in range(ik_count):
        a, b, kind, level, direction, up = read('<IIBBBB', ik_offset + i * 12)
        ik.append({'ik_joint_hash': a, 'fk_joint_hash': b, 'ik_joint_name': names.get(a),
            'fk_joint_name': names.get(b), 'type': kind, 'descendant_level': level, 'direction': direction, 'up_vector': up})
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'version': 28,
        'attribute_flags': flags, 'joint_mask_groups': masks, 'ik_definitions': ik,
        'other_sections_retained_not_decoded': {'expressions': expr, 'extra_joints': extra,
            'symmetry': symmetry, 'symmetry2': symmetry2, 'skeleton_mask': skeleton},
        'mask_bit_semantics_runtime_unverified': True, 'joint_names_only_resolved_from_native_70_bone_table': True}


def normalize_resource(value):
    if not isinstance(value, str):
        return None
    match = re.search(r'([a-zA-Z0-9_./\\-]+\.motlist)(?:\.1047)?', value)
    if not match:
        return None
    path = match[1].replace('\\', '/').lower()
    return path.removeprefix('natives/stm/')


def independent_joint_maps(maps):
    results = []
    dll = ROOT / 'scripts/animation/ReeRuntimeInspect/bin/Release/net8.0/ReeRuntimeInspect.dll'
    if not dll.exists(): raise ValueError('Build pinned ReeRuntimeInspect first')
    for decoded in maps:
        p = ROOT / decoded['path']
        dest = OUTPUT / 'independent_joint_maps' / (p.name + '.json')
        if not dest.exists():
            subprocess.run([str(ROOT / 'tools/dotnet8/dotnet.exe'), str(dll), str(p), str(dest)], check=True)
        other = json.loads(dest.read_text())
        # System.Text.Json emits the shortest roundtripping float32 decimal.
        for group in other['joint_mask_groups']:
            for joint in group['joints']:
                joint['weight'] = struct.unpack('<f', struct.pack('<f', joint['weight']))[0]
        python_masks = [{'group_id': g['group_id'], 'joints': [
            {k: j[k] for k in ('hash', 'mask_byte')} | {'weight': j['weight'] or 0.0}
            for j in g['joints']]} for g in decoded['joint_mask_groups']]
        if python_masks != other['joint_mask_groups'] or decoded['ik_definitions'] != other['ik_definitions']:
            raise ValueError('Independent joint-map decoding differs')
        if other['sha256'] != decoded['sha256'] or other['attribute_flags'] != decoded['attribute_flags']:
            raise ValueError('Independent joint-map provenance differs')
        results.append({'path': decoded['path'], 'independent_report': dest.relative_to(ROOT).as_posix(),
            'joint_mask_groups': len(python_masks), 'ik_motion_definitions': len(other['ik_definitions']),
            'joint_expression_count': other['joint_expression_count'], 'extra_joint_count': other['extra_joint_count'],
            'all_decoded_mask_hashes_bytes_weights_equal': True})
    return {'status': 'PASSED', 'maps': results, 'unparsed_other_sections_are_not_claimed_equal': True}


def summarize_capture(document, static=None):
    """Never treats a static candidate or synthetic fixture as runtime proof."""
    if document.get('schema') != 'bela-runtime-binding-v1' or document.get('read_only') is not True:
        raise ValueError('Not a read-only D1 capture')
    rows, idle_keys, missing = [], set(), set()
    if document.get('runtime_identity') != {'game': 're9', 'reframework_commit': FRAMEWORK_COMMIT, 'tdb_version': 83}:
        missing.add('Observed RE9/REFramework/TDB identity matching the inspected installation')
    for sample in document.get('samples') or []:
        for watch in sample.get('watches') or []:
            for layer in watch.get('layers') or []:
                for node in layer.get('nodes') or []:
                    values = dict(layer.get('observed') or {}); values.update(node.get('observed') or {})
                    row = {'marker': sample['marker'], 'elapsed_clock': sample['elapsed_clock'],
                        'role': watch['role'], 'selection': watch['selection'], 'layer': layer['index'],
                        'node': node['index'], 'observed_getters': values, 'bank_candidates': []}
                    bid, mid = values.get('get_MotionBankID'), values.get('get_MotionID')
                    switch = values.get('get_SwitchValue', values.get('get_Switch'))
                    if not isinstance(switch, (int, float)): switch = None
                    if not isinstance(bid, (int, float)): bid = None
                    if not isinstance(mid, (int, float)): mid = None
                    for bank in watch.get('banks') or []:
                        bv = bank.get('observed') or {}
                        if bid is not None and bv.get('get_BankID') == bid:
                            path = normalize_resource((bank.get('motion_list') or {}).get('resource_string'))
                            row['bank_candidates'].append({'resource': path, 'bank_id': bid,
                                'bank_type': bv.get('get_BankType'), 'bank_type_mask': bv.get('get_BankTypeMask')})
                    # De-duplicate Active/Dynamic representations of the same descriptor.
                    row['bank_candidates'] = list({json.dumps(v, sort_keys=True): v for v in row['bank_candidates']}.values())
                    row['motion_id'] = mid; row['bank_id'] = bid; row['switch'] = switch
                    row['frame'] = values.get('get_Frame'); row['joint_mask'] = values.get('get_JointMaskID', values.get('get_JointMask'))
                    rows.append(row)
                    if sample['marker'] in ('idle', 'idle_after_walk', 'idle_after_aim') and watch['role'] == 'body':
                        idle_keys.add((layer['index'], node['index'], bid, mid, switch))
                        for key in ('motion_id', 'bank_id', 'switch', 'frame', 'joint_mask'):
                            if row[key] is None or isinstance(row[key], dict): missing.add('Observed scalar ' + key)
                        if len(row['bank_candidates']) != 1 or not row['bank_candidates'][0]['resource']:
                            missing.add('Unambiguous loaded MOTLIST path and bank descriptor')
                        elif row['bank_candidates'][0]['bank_type'] is None or row['bank_candidates'][0]['bank_type_mask'] is None:
                            missing.add('Observed bank type and type mask')
    if not rows: missing.add('Live Grace motion/layer/node getters')
    if not document.get('grace_identity_user_confirmed'): missing.add('User-confirmed Grace object identity')
    if not document.get('context') or document['context'].startswith('Enter '): missing.add('Exact room/save context and camera/weapon state')
    if document.get('truncation'): missing.add('Untruncated capture')
    if document.get('api_errors'): missing.add('Resolve reported API failures')
    if document.get('synthetic_fixture'): missing.add('A real engine capture; this input is synthetic')
    markers = {r['marker'] for r in rows}
    for marker in ('idle', 'walk', 'idle_after_walk', 'aim', 'idle_after_aim'):
        if marker not in markers: missing.add('Samples during ' + marker)
    frames = [r['frame'] for r in rows if r['marker'] == 'idle' and isinstance(r['frame'], (int, float))]
    if len(frames) < 2 or max(frames) == min(frames): missing.add('Advancing engine playback frames during stationary idle')
    if not idle_keys: missing.add('Observed body idle candidates')
    changes = []
    previous = {}
    for row in rows:
        key = (row['selection']['object']['address'], row['role'], row['layer'], row['node'])
        state = (row['bank_id'], row['motion_id'], row['switch'], row['joint_mask'])
        if key in previous and previous[key] != state:
            changes.append({'elapsed_clock': row['elapsed_clock'], 'marker': row['marker'],
                'layer': row['layer'], 'node': row['node'], 'from': previous[key], 'to': state})
        previous[key] = state
    if not changes: missing.add('Observed state/motion changes during protected actions')
    # Static association is explicitly a cross-check, never its own live proof.
    if static is None: missing.add('Cross-check captured paths/IDs against original bank and MOTLIST metadata')
    else:
        for row in rows:
            if not row['marker'].startswith('idle') or row['role'] != 'body': continue
            matched = []
            for bank in row['bank_candidates']:
                for candidate in static['idle_candidates']:
                    path = normalize_resource(candidate['resource'].removeprefix('assets/extracted/re9/natives/stm/'))
                    if path != bank['resource']: continue
                    for index in candidate['indices']:
                        if index.get('motion_id') == row['motion_id'] and index.get('switch') == row['switch']:
                            matched.append(candidate['name'])
            row['static_name_matches'] = sorted(set(matched))
            if len(set(matched)) != 1: missing.add('Unique original native idle descriptor match')
    return {'status': 'CAPTURE_EVIDENCE_READY_FOR_REVIEW' if not missing else 'LIVE_BINDING_NOT_YET_ESTABLISHED',
        'actual_runtime_binding_verified': False, 'automatic_activation_allowed': False,
        'note': 'Even a complete capture requires review of identity, layers, frame units, masks and transitions before playback authorization.',
        'sampled_motion_rows': rows, 'observed_changes': changes, 'idle_keys': sorted(idle_keys, key=str),
        'missing_evidence': sorted(missing), 'static_metadata_is_not_runtime_proof': True}


def prepare():
    protected = protect_checkpoint()
    env = environment()
    if env['framework_log_commit'] != FRAMEWORK_COMMIT:
        raise ValueError('Installed REFramework differs from investigated revision')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    extraction_folder = OUTPUT / 'joint_maps'
    extraction_report = OUTPUT / 'extraction.json'
    if not extraction_report.exists():
        if extraction_folder.exists(): raise ValueError('Partial extraction exists; preserve it and inspect')
        names = [n for n in load_names('re9') if '/cp_a100/jointmap/' in n.lower() and '.jmap.' in n]
        matches, archives = build_lookup(official_paks(Path(env['game_directory'])), names)
        if set(matches) != set(names): raise ValueError('Missing Grace joint-map source')
        records = extract(matches, extraction_folder)
        write_json(extraction_report, {'records': records, 'archives_read_only': archives})
    maps = [parse_joint_map(p) for p in sorted(extraction_folder.rglob('*.jmap.28'))]
    write_json(REPORTS / 'joint_map_reimport.json', independent_joint_maps(maps))
    write_json(REPORTS / 'joint_maps.json', {'status': 'STATIC_MASK_AND_IK_DATA_DECODED', 'maps': maps,
        'source_reader': 'ReeLib ceb0d2f / OtherFiles/JmapFile.cs; runtime mask interpretation remains unverified'})
    existing_env = REPORTS / 'environment_before.json'
    if existing_env.exists():
        original = json.loads(existing_env.read_text())
        for key in ('protected_installed_files', 'steam_save_files', 'official_archives'):
            if original[key] != env[key]: raise ValueError('Environment changed since D1 checkpoint: ' + key)
    else: write_json(existing_env, env)
    write_json(REPORTS / 'baseline_protection.json', protected)
    write_json(REPORTS / 'binding_status.json', {'status': 'AWAITING_MANUAL_READ_ONLY_GAME_CAPTURE',
        'actual_runtime_idle_bank': None, 'actual_runtime_idle_layer': None, 'actual_runtime_idle_motion': None,
        'actual_runtime_binding_verified': False, 'game_running_at_inspection': env['game_process'],
        'static_controllers': 9, 'static_transitions': 577,
        'required_evidence': ['Select confirmed Grace body and FPS arms motion components in the intended scene',
            'Loaded MOTLIST path, bank ID/type/type mask, layer, node motion ID/name/switch, joint mask and advancing frames',
            'Stationary idle, movement start/stop, aiming start/stop; correlate body/FPS layers',
            'Inspect missing method/field catalog with Object Explorer, including FSM node and IK/helper fields',
            'Confirm test room, existing save, camera mode, weapon and active mod versions'],
        'read_only_probe': 'scripts/runtime/bela_binding_probe.lua', 'activation_performed': False})
    print('Protected A/B/C/v0.1.x verified; installed files/saves snapshotted; joint-map masks/IK decoded; live capture pending.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--verify-environment', action='store_true')
    args = parser.parse_args()
    if args.prepare: prepare()
    if args.capture:
        if not args.report: parser.error('--capture requires a workspace --report path')
        dest = args.report.resolve()
        if not dest.is_relative_to(REPORTS.resolve()): raise ValueError('Capture analysis must stay in D1 reports')
        report = summarize_capture(json.loads(args.capture.read_text()),
            json.loads((ROOT / 'reports/native_animation_v0.2.0/binding_analysis.json').read_text()))
        write_json(dest, report); print(report['status'], report['missing_evidence'])
    if args.verify_environment:
        protect_checkpoint()
        before = json.loads((REPORTS / 'environment_before.json').read_text()); after = environment()
        differences = [key for key in ('protected_installed_files', 'steam_save_files', 'official_archives') if before[key] != after[key]]
        write_json(REPORTS / 'environment_verification.json', {'status': 'PASSED' if not differences else 'CHANGED',
            'different_categories': differences, 'engine_or_animation_activation_performed': False,
            'official_archive_check': 'Size/mtime inventory only; no claim of content hashing'})
        if differences: raise ValueError('Protected environment changed: ' + str(differences))
        print('Installed mods, known Steam saves and official archive metadata unchanged.')


if __name__ == '__main__': main()

