"""Protect the user-approved source reconstruction and accepted native packages."""
import json
from common import ROOT, write_json
from source_animation_workflow import protect_baseline, sha


ACCEPTANCE = ROOT / 'reports/retarget_v0.2.0/source_reference_acceptance.json'


def protect():
    phase = json.loads((ROOT / 'reports/animation_dev/phase_results.json').read_text())
    records = [row for row in phase['local_artifacts'] if row['path'].startswith(phase['accepted_output'] + '/')]
    for row in records:
        if sha(ROOT / row['path']) != row['sha256']:
            raise ValueError(f"Approved source artifact changed: {row['path']}")
    if ACCEPTANCE.exists():
        accepted = json.loads(ACCEPTANCE.read_text())
        if accepted['protected_artifacts'] != records:
            raise ValueError('Approved source reference manifest changed')
    else:
        write_json(ACCEPTANCE, {
            'source_checkpoint': '44eb9e139ae647a5ed3d52e6ce50cba79f120a14',
            'user_visual_acceptance': True,
            'acceptance_statement': 'User reviewed source_idle_60fps.mp4 and confirms appearance and movement are visually correct.',
            'protected_artifacts': records,
        })
    return {'source_reference_files': len(records), 'source_visual_acceptance': True,
            'source_checkpoint': '44eb9e1', 'baseline': protect_baseline()}


if __name__ == '__main__':
    print(protect())

