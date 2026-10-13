"""Read-only checks for the user-accepted Milestone B and previous releases."""
import json
from common import ROOT, write_json
from retarget_protection import protect as protect_source
from source_animation_workflow import sha

ACCEPTANCE = ROOT / 'reports/native_animation_v0.2.0/retarget_reference_acceptance.json'

def protect():
    previous = protect_source()
    phase_path = ROOT / 'reports/retarget_v0.2.0/phase_results.json'
    phase = json.loads(phase_path.read_text())
    records = phase['local_artifacts'] + phase['source_code_hashes']
    records = records + [{'path': phase_path.relative_to(ROOT).as_posix(), 'sha256': sha(phase_path)}]
    for row in records:
        if sha(ROOT / row['path']) != row['sha256']:
            raise ValueError(f"Accepted Milestone B file changed: {row['path']}")
    if ACCEPTANCE.exists():
        if json.loads(ACCEPTANCE.read_text())['protected_artifacts'] != records:
            raise ValueError('Milestone B acceptance manifest changed')
    else:
        write_json(ACCEPTANCE, {'checkpoint': 'e579c25b3685aec9736b0dfbb5c020e9ffbd7c3a',
            'user_visual_acceptance': True,
            'statement': 'User reviewed synchronized source and target, approves offline retarget and the recorded finger, foot, proportion and dress differences.',
            'protected_artifacts': records})
    return {'milestone_B_files': len(records), 'milestone_B_user_accepted': True, 'previous': previous}

if __name__ == '__main__':
    print(protect())

