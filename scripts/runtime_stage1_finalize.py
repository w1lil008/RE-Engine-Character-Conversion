"""Build an inert, reproducible D1 preparation ZIP; contains no activation script."""
import hashlib
import io
import json
import shutil
import subprocess
import unittest
import zipfile
from pathlib import Path
from common import ROOT, write_json
from source_animation_workflow import sha
from runtime_stage1 import REPORTS, OUTPUT, NATIVE, FRAMEWORK_COMMIT, protect_checkpoint, environment

PACKAGE = ROOT / 'dist/BelaGrace_RuntimePreparation_0.2.0_Stage1.zip'


def main():
    before = protect_checkpoint()
    previous = json.loads((REPORTS / 'environment_before.json').read_text())
    current = environment()
    for key in ('protected_installed_files', 'steam_save_files', 'official_archives'):
        if current[key] != previous[key]: raise ValueError('Protected installed environment changed: ' + key)
    log = io.StringIO(); suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (REPORTS / 'automated_tests.log').write_text(log.getvalue(), encoding='utf-8')
    tests = {'status': 'PASSED' if result.wasSuccessful() else 'FAILED', 'tests_run': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors), 'skips': len(result.skipped),
        'runtime_probe_test_scope': 'Lua 5.4 mocked SDK only; no claim of RE9 API availability or engine playback'}
    write_json(REPORTS / 'automated_tests.json', tests)
    if not result.wasSuccessful() or result.skipped:
        raise ValueError('Validation failed; inspect D1 automated_tests.log')
    evidence = []
    for repo, commit, names in [
        ('REFramework', FRAMEWORK_COMMIT, ['src/mods/bindings/Sdk.cpp', 'src/mods/bindings/Json.cpp',
            'src/mods/ScriptRunner.cpp', 'src/mods/tools/ObjectExplorer.cpp']),
        ('EMV-Engine', 'a8a89961fde640d542afc72bd66fd8e12f3b82b3', ['EMV Engine/reframework/autorun/EMV Engine/init.lua']),
        ('RE-Engine-Lib', 'ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef', ['REE-Lib/OtherFiles/JmapFile.cs'])]:
        folder = ROOT / 'tools/research' / repo
        actual = subprocess.check_output(['git', '-C', str(folder), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != commit: raise ValueError('Research tool revision differs')
        for name in names:
            evidence.append({'repository': repo, 'commit': commit, 'path': name, 'sha256': sha(folder / name)})
    write_json(REPORTS / 'sdk_source_evidence.json', {'status': 'PINNED_LOCAL_SOURCES_REVIEWED',
        'files': evidence, 'lua_mock_runtime': 'Lupa 2.6 / Lua 5.4',
        'live_game_api_availability_verified': False, 'raw_memory_offsets_used': False})
    native_rows = [{'file': name, 'bytes': (NATIVE / name).stat().st_size, 'sha256': sha(NATIVE / name)}
        for name in ('bela_idle.mot.983', 'bela_idle.motlist.1047')]
    for row in native_rows:
        repeat = ROOT / 'build/animation_v0.2.0/native_idle_canonical_repeat/native' / row['file']
        if sha(repeat) != row['sha256']: raise ValueError('Accepted native repeat differs')
    plan = {'stage': 'D_STAGE1_PREPARATION', 'activation_authorized': False,
        'actual_runtime_binding_verified': False, 'manual_capture_required': True,
        'target_steam_build': previous['steam_build_id'], 'target_exe_version': previous['exe_versions'],
        'target_exe_sha256': next(r['sha256'] for r in previous['protected_installed_files'] if r['path'] == 're9.exe'),
        'target_reframework_commit': FRAMEWORK_COMMIT,
        'accepted_native_checkpoint': '91ee9fe', 'native_resources': native_rows,
        'proposed_runtime_resource_path': 'Animation/bela_prototype/v020/bela_idle.motlist',
        'prospective_new_loose_path': 'natives/stm/animation/bela_prototype/v020/bela_idle.motlist.1047',
        'joint_map_reference': 'GameAssets/Character/CharacterPrefab/cp_A1/cp_A100/JointMap/cp_A1JointMap_ForConvert.jmap',
        'local_descriptor': {'motion_id': 0, 'switch': 0, 'runtime_binding_established': False},
        'verified_live_binding': {'body_object': None, 'fps_object': None, 'idle_list': None, 'bank_id': None,
            'bank_type': None, 'bank_type_mask': None, 'motion_id': None, 'switch': None, 'layer': None, 'joint_mask': None},
        'chosen_test_scene': None, 'unused_dynamic_bank_id': None, 'verified_registration_api': None,
        'verified_playback_api': None, 'verified_abort_and_release_api': None,
        'preferred_method': 'Fresh path and component-local dynamic MOTLIST bank, if live RE9 APIs and layer ownership permit',
        'full_xyzw_tracks': ['R_Arm_Clavicle', 'L_Leg_Upper'], 'full_xyzw_runtime_support_verified': False,
        'cycle': {'start_frame': 0, 'end_frame': 300, 'fps': 60, 'seconds': 5, 'play_count': 1,
            'force_loop': False, 'repeat_forced_requests': False, 'new_accumulated_root_motion': False},
        'stages': ['A resource load without play', 'B actual engine track decode or separately authorized isolated sampler',
            'C exactly one five-second cycle', 'D controller resumes protected actions', 'E process exit/remove fresh overlay/restart'],
        'runtime_integration_harness_generated': False,
        'blockers': ['Live binding tuple and scene/camera/weapon confirmation',
            'RE9 registration/play/abort APIs and safe FSM/layer ownership',
            'Full XYZW engine decoding evidence', 'Mask/helper/IK/blending and cache lifetime'],
        'rollback': 'Close RE9, discard the future manual harness, remove only its newly added MOTLIST, restart; character/controller/PAK/save untouched'}
    write_json(REPORTS / 'runtime_experiment.json', plan)
    folder = OUTPUT / 'preparation'
    files = {
        'diagnostics/bela_binding_probe.lua': (ROOT / 'scripts/runtime/bela_binding_probe.lua').read_bytes(),
        'docs/RUNTIME_ANIMATION_STAGE1_V0.2.0.md': (ROOT / 'docs/RUNTIME_ANIMATION_STAGE1_V0.2.0.md').read_bytes(),
        'README.txt': ('Milestone D Stage 1 — INERT runtime preparation package\n'
            'Extract to a workspace folder, never into the game directory or mod manager.\n'
            'Run only diagnostics/bela_binding_probe.lua manually with REFramework ScriptRunner.\n'
            'No native animation activation, resource registration or idle replacement is authorized.\n'
            'Resources are accepted Milestone C bytes, not mapped to any verified live idle.\n'
            'Read docs/RUNTIME_ANIMATION_STAGE1_V0.2.0.md for capture and future gated experiment steps.\n'
            'No runtime installer, controller, bank, playback harness or autorun is included.\n').encode(),
    }
    for row in native_rows: files['resources/' + row['file']] = (NATIVE / row['file']).read_bytes()
    for name in ('runtime_experiment.json', 'binding_status.json', 'baseline_protection.json',
        'joint_map_reimport.json', 'sdk_source_evidence.json', 'automated_tests.json'):
        files['reports/' + name] = (REPORTS / name).read_bytes()
    files['reports/accepted_native_reimport.json'] = (ROOT / 'reports/native_animation_v0.2.0/reimport_report.json').read_bytes()
    manifest = {'scope': 'Inert read-only diagnostics and gated first-playback preparation',
        'native_activation_performed': False, 'runtime_binding_verified': False,
        'files': [{'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            for name, data in sorted(files.items())], 'self_excluded': True}
    files['MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    for name, data in files.items():
        path = folder / name
        if path.exists() and path.read_bytes() != data: raise ValueError('Preserve prior preparation payload: ' + str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists(): path.write_bytes(data)
    def archive_bytes():
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 10, 10, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o644 << 16
                archive.writestr(info, data, compresslevel=9)
        return stream.getvalue()
    payload = archive_bytes()
    if archive_bytes() != payload: raise ValueError('Preparation ZIP is not repeatable')
    if PACKAGE.exists() and PACKAGE.read_bytes() != payload: raise ValueError('Preserve existing Stage 1 ZIP')
    PACKAGE.parent.mkdir(exist_ok=True)
    if not PACKAGE.exists(): PACKAGE.write_bytes(payload)
    with zipfile.ZipFile(PACKAGE) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(files): raise ValueError('Package integrity failure')
        for name, data in files.items():
            if archive.read(name) != data: raise ValueError('Package payload changed')
        if any(n.startswith(('natives/', 'reframework/autorun/')) or n.endswith('.motbank.4') for n in archive.namelist()):
            raise ValueError('Unexpected active mod package content')
    write_json(REPORTS / 'package_manifest.json', dict(manifest, archive=PACKAGE.relative_to(ROOT).as_posix(),
        sha256=sha(PACKAGE), bytes=PACKAGE.stat().st_size, repeat_byte_identical=True))
    if protect_checkpoint() != before: raise ValueError('Accepted inputs changed during preparation')
    write_json(REPORTS / 'phase_results.json', {'status': 'STAGE1_PREPARATION_READY_LIVE_CAPTURE_REQUIRED',
        'tests': tests, 'protected': before, 'native_candidate_byte_identical_to_accepted_C': True,
        'live_runtime_binding_verified': False, 'runtime_probe_executed_in_RE9': False,
        'activation_or_installation_performed': False, 'package': PACKAGE.relative_to(ROOT).as_posix(),
        'package_sha256': sha(PACKAGE), 'preparation_folder': folder.relative_to(ROOT).as_posix(),
        'report': 'docs/RUNTIME_ANIMATION_STAGE1_V0.2.0.md',
        'completion_scope': 'Exact remaining live instrumentation requirements identified; reproducible gated experiment prepared. Executable playback setup waits for live evidence and separate authorization.',
        'source_code_hashes': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p)} for p in
            [ROOT / 'scripts/runtime_stage1.py', ROOT / 'scripts/runtime_stage1_finalize.py',
             ROOT / 'scripts/runtime/bela_binding_probe.lua', ROOT / 'tests/test_runtime_stage1.py',
             ROOT / 'tests/runtime_probe_fixture.lua'] + sorted((ROOT / 'scripts/animation/ReeRuntimeInspect').glob('*.*'))]})
    print(f'{result.testsRun} tests passed; {len(files)} inert package members verified; ZIP repeat byte-identical. Live capture required; no activation.')


if __name__ == '__main__': main()

