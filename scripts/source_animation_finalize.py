"""Check final source-phase evidence, run targeted tests, and hash local artifacts."""
import contextlib
import json
import subprocess
import unittest
import numpy as np
from common import ROOT, write_json
from animation_math import motion_globals
from glb_read import load
from source_animation_workflow import protect_baseline, prepare_reference, sha
from source_video_metadata import video_metadata


def main():
    reports = ROOT / 'reports/animation_dev'
    config = json.loads((ROOT / 'config/source_idle_v0.2.0.json').read_text())
    idle = ROOT / config['output']
    repeat = ROOT / 'build/animation_v0.2.0/source_idle_repeat'
    optional = ROOT / 'build/animation_v0.2.0/source_provocative'
    baseline = protect_baseline()
    prepare_reference()
    evidence = {}
    for name in ['source_idle_blender', 'source_idle_roundtrip', 'source_idle_workflow',
                 'source_idle_repeat_blender', 'source_idle_repeat_roundtrip',
                 'source_idle_repeat_skinning', 'source_idle_repeat_workflow',
                 'source_provocative_blender', 'source_provocative_roundtrip']:
        report = json.loads((reports / f'{name}.json').read_text())
        if report['status'] != 'PASSED':
            raise ValueError(f'Failed evidence: {name}')
        evidence[name] = report
    if sha(idle / 'source_idle.glb') != sha(repeat / 'source_idle.glb'):
        raise ValueError('Current exporter is not byte-reproducible')
    # Historical output differed only in JSON numeric spelling, not payload.
    original_doc, original_bin = load(ROOT / 'build/animation_v0.2.0/source_idle_validated/source_idle.glb')
    current_doc, current_bin = load(idle / 'source_idle.glb')
    if original_doc != current_doc or bytes(original_bin) != bytes(current_bin):
        raise ValueError('Initial validated geometry/animation payload changed')
    video = video_metadata(idle / 'source_idle_60fps.mp4')
    optional_video = video_metadata(optional / 'source_follow_root_60fps.mp4')
    if (video['frame_count'], video['fps'], video['duration_seconds']) != (300, 60, 5):
        raise ValueError('Incomplete idle preview')
    if (optional_video['frame_count'], optional_video['fps']) != (222, 60):
        raise ValueError('Incomplete optional preview')
    log = ROOT / 'build/animation_v0.2.0/unit_tests_final.log'
    with log.open('w', encoding='utf-8') as stream, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    test_report = {'status': 'PASSED' if result.wasSuccessful() and not result.skipped else 'FAILED',
                   'tests_run': result.testsRun, 'failures': len(result.failures),
                   'errors': len(result.errors), 'skips': len(result.skipped),
                   'log': log.relative_to(ROOT).as_posix()}
    write_json(reports / 'test_results.json', test_report)
    if test_report['status'] != 'PASSED':
        raise ValueError(f'Test suite incomplete: {test_report}')
    decoded = json.loads((idle / 'decoded_reference.json').read_text())
    start = motion_globals(decoded, 0)
    end = motion_globals(decoded, 300)
    position = np.linalg.norm(end[:, :3, 3] - start[:, :3, 3], axis=1)
    angle = np.degrees(np.arccos(np.clip((np.einsum('nij,nij->n', start[:, :3, :3], end[:, :3, :3]) - 1) / 2, -1, 1)))
    artifacts = []
    for directory in [idle, repeat, optional]:
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() in ['.glb', '.blend', '.mp4', '.png', '.json', '.bin']:
                artifacts.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
                                  'sha256': sha(path)})
    source_paths = list((ROOT / 'scripts').glob('source_*.py')) + [ROOT / 'scripts/animation_math.py', ROOT / 'scripts/glb_read.py']
    source_paths += list((ROOT / 'scripts/animation/ReeDecode').glob('*.cs*'))
    source_paths += [ROOT / 'scripts/animation/ReeDecode/packages.lock.json', ROOT / 'tests/test_source_animation.py']
    source_paths += list((ROOT / 'config').glob('source_*.json'))
    source_hashes = [{'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)} for path in sorted(source_paths)]
    record = {
        'status': 'SOURCE_SKELETAL_RECONSTRUCTION_PASSED',
        'date': '2026-10-10',
        'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
        'protected_start_commit': '058bea7490e9f6f626de361efe52dda366e0b5d6',
        'accepted_output': idle.relative_to(ROOT).as_posix(),
        'source_resource_sha256': config['sha256'],
        'idle_decode_report': 'reports/animation_dev/source_idle_decode.json',
        'validation_evidence': [f'reports/animation_dev/{name}.json' for name in evidence],
        'tests': test_report, 'baseline': baseline,
        'byte_reproducible_current_glb': True,
        'initial_validated_geometry_and_animation_payload_unchanged': True,
        'idle_video': video, 'optional_video': optional_video,
        'loop': {'max_joint_endpoint_difference_m': float(position.max()),
                 'worst_position_bone': decoded['bones'][int(position.argmax())]['name'],
                 'max_rotation_endpoint_difference_degrees': float(angle.max()),
                 'worst_rotation_bone': decoded['bones'][int(angle.argmax())]['name'],
                 'source_boundary_preserved_without_smoothing': True},
        'comparison_scope': 'Independent sampling/hierarchy/export/skinning vs pinned source-editor math. Shared ReeLib decoder; no graphical-tool or RE8 runtime playback comparison.',
        'excluded_engine_behaviors': ['enemy events', 'procedural IK/look-at', 'GPU cloth',
                                      'hair physics', 'facial morphs/expressions/lip-sync', 'native engine shaders'],
        'grace_retarget_implemented': False, 'native_RE9_animation_written': False,
        'game_installation_or_save_modified': False, 'runtime_tested': False,
        'mapping_plan': 'reports/animation_dev/source_to_grace_mapping_plan.json',
        'source_code_and_config_hashes': source_hashes,
        'local_artifacts': artifacts,
    }
    write_json(reports / 'baseline_protection.json', baseline)
    write_json(reports / 'phase_results.json', record)
    print(f"Source phase passed; {result.testsRun} tests, zero skips; current GLB byte-reproducible; v0.1.x protected")


if __name__ == '__main__':
    main()

