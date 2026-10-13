"""Collect verified offline retarget deliverables without promoting runtime acceptance."""
import contextlib
import json
import unittest
from common import ROOT, write_json
from retarget_protection import protect
from source_animation_workflow import sha
from source_video_metadata import video_metadata


def main():
    reports = ROOT / 'reports/retarget_v0.2.0'
    output = ROOT / 'build/animation_v0.2.0/retarget_idle'
    repeat = ROOT / 'build/animation_v0.2.0/retarget_idle_repeat'
    evidence = {}
    for name in ['retarget_idle_numerical', 'retarget_idle_blender', 'retarget_idle_roundtrip', 'retarget_idle_skinning',
                 'retarget_repeat_numerical', 'retarget_repeat_blender', 'retarget_repeat_roundtrip',
                 'retarget_repeat_skinning', 'retarget_repeat_workflow']:
        value = json.loads((reports / f'{name}.json').read_text())
        if value['status'] != 'PASSED': raise ValueError(f'Incomplete verification: {name}')
        evidence[name] = value
    if sha(output / 'retarget_idle.glb') != sha(repeat / 'retarget_idle.glb'):
        raise ValueError('Retarget GLB is not reproducible')
    videos = {}
    for name in ['retarget_idle_60fps.mp4', 'comparison_60fps.mp4']:
        metadata = video_metadata(output / name)
        if (metadata['frame_count'], metadata['fps'], metadata['duration_seconds']) != (300, 60, 5):
            raise ValueError('Incomplete preview timing')
        videos[name] = metadata
    protected = protect()
    log = output / 'tests.log'
    with log.open('w', encoding='utf-8') as stream, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
    tests = {'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
             'skips': len(result.skipped), 'status': 'PASSED' if result.wasSuccessful() and not result.skipped else 'FAILED'}
    write_json(reports / 'test_results.json', tests)
    if tests['status'] != 'PASSED': raise ValueError(tests)
    artifacts = []
    for directory in [output, repeat]:
        for path in sorted(directory.iterdir()):
            if path.suffix in ['.glb', '.blend', '.mp4', '.png', '.npz', '.json']:
                artifacts.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)})
    sources = list((ROOT / 'scripts').glob('retarget*.py')) + [ROOT / 'tests/test_retarget_idle.py', ROOT / 'config/retarget_idle_v0.2.0.json']
    write_json(reports / 'phase_results.json', {
        'status': 'OFFLINE_RETARGET_PASSED_READY_FOR_USER_VISUAL_REVIEW',
        'source_user_visually_accepted': True, 'retarget_user_visually_accepted': False,
        'source_checkpoint': '44eb9e1', 'branch': 'codex/v0.2.0-source-animation',
        'output': output.relative_to(ROOT).as_posix(), 'target_bones': 611,
        'mapped_body_bones': 24, 'animation_channels': 25, 'sample_count_per_channel': 301,
        'evidence': [f'reports/retarget_v0.2.0/{name}.json' for name in evidence],
        'tests': tests, 'protected_inputs': protected, 'byte_identical_repeated_GLB': True,
        'videos': videos, 'geometry_weights_binds_and_hierarchy_preserved': True,
        'source_track_policies': 'reports/retarget_v0.2.0/retarget_idle_export.json',
        'residuals': [
            'Neutral Grace finger locals retained: the source clenched left fist is deliberately not transferred.',
            'Target limb proportions and unscaled source root sway produce up to approximately 5.8 mm horizontal foot range; source range is up to 3.6 mm.',
            'Native sole contact patch dips up to approximately 0.75 mm below the review floor at the five sampled geometry poses; no IK/collision solver added.',
            'Lower dress retains rigid folds and uneven hem under the original staggered stance. Small bind edges show high static strain; detailed motion strain is recorded. Accepted weights remain unchanged.',
            'Source garment/hair/IK/weapon/finger tracks are explicitly classified, not copied into this body layer.',
        ],
        'native_RE9_animation_outputs_written': False, 'game_save_or_controller_modified': False, 'runtime_tested': False,
        'next_gate': 'User reviews full retarget/comparison videos. Native MOT 983 / MOTLIST 1047 writer and body-layer binding proof require authorization after acceptance.',
        'source_code_hashes': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p)} for p in sorted(sources)],
        'local_artifacts': artifacts,
    })
    print(f'Offline retarget ready for manual visual review: {result.testsRun} tests, zero skips; source and v0.1.x protected')


if __name__ == '__main__':
    main()

