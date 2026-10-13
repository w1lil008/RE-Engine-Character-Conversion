"""Protect the accepted D1 checkpoint as well as every earlier accepted phase."""
import json
import subprocess
from common import ROOT, confined
from source_animation_workflow import sha
from runtime_stage1 import protect_checkpoint

CHECKPOINT = '48d139f'


def protect():
    previous = protect_checkpoint()
    phase = json.loads((ROOT / 'reports/runtime_binding_v0.2.0/phase_results.json').read_text())
    for row in phase['source_code_hashes']:
        if sha(confined(ROOT, row['path'])) != row['sha256']:
            raise ValueError('Accepted D1 source changed: ' + row['path'])
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', CHECKPOINT,
        'reports/runtime_binding_v0.2.0', 'docs/RUNTIME_ANIMATION_STAGE1_V0.2.0.md'], cwd=ROOT, text=True).splitlines()
    for name in names:
        expected = subprocess.check_output(['git', 'show', CHECKPOINT + ':' + name], cwd=ROOT)
        eol = subprocess.check_output(['git', 'check-attr', 'eol', '--', name], cwd=ROOT, text=True).strip().split(': ')[-1]
        if eol == 'crlf': expected = expected.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
        if confined(ROOT, name).read_bytes() != expected:
            raise ValueError('Accepted D1 evidence changed: ' + name)
    if sha(ROOT / phase['package']) != phase['package_sha256']:
        raise ValueError('Accepted D1 package changed')
    return {'status': 'PASSED', 'checkpoint': CHECKPOINT,
        'stage1_sources': len(phase['source_code_hashes']), 'stage1_evidence_files': len(names),
        'stage1_package_sha256': phase['package_sha256'], 'previous': previous}

