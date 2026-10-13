"""Reproduce an offline retarget in a fresh build directory; never installs assets."""
import argparse
import json
import subprocess
import sys
from common import ROOT, confined, write_json
from retarget_protection import protect


def run(command, path):
    with path.open('w', encoding='utf-8') as stream:
        subprocess.run([str(a) for a in command], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    p.add_argument('--video', action='store_true'); p.add_argument('--report-name', default='retarget_idle_repeat')
    args = p.parse_args(); output = confined(ROOT / 'build', args.output.removeprefix('build/'))
    if output.exists(): raise ValueError('Use a fresh build directory')
    protected = protect(); logs = ROOT / 'build/animation_v0.2.0/logs'; logs.mkdir(parents=True, exist_ok=True)
    run([sys.executable, 'scripts/retarget_idle_export.py', '--output', args.output, '--report-name', args.report_name], logs / f'{args.report_name}_export.log')
    blender = ROOT / 'tools/blender-4.3.2-windows-x64/blender.exe'
    command = [blender, '-b', '--factory-startup', '--python', 'scripts/retarget_idle_blender.py', '--',
               '--output', args.output, '--report-name', args.report_name]
    if args.video: command.append('--video')
    run(command, output / 'blender.log')
    run([blender, '-b', '--factory-startup', '--python', 'scripts/retarget_idle_blender.py', '--', '--output', args.output,
         '--report-name', args.report_name, '--glb', 'retarget_idle_roundtrip.glb', '--validate-only'], output / 'roundtrip.log')
    run([sys.executable, 'scripts/retarget_idle_validate.py', '--output', args.output, '--report-name', args.report_name], output / 'numerical.log')
    run([blender, '-b', '--factory-startup', '--python', 'scripts/retarget_idle_skinning.py', '--',
         '--output', args.output, '--report-name', args.report_name], output / 'skinning.log')
    if protect() != protected: raise ValueError('Protected assets changed')
    write_json(ROOT / f'reports/retarget_v0.2.0/{args.report_name}_workflow.json', {
        'status': 'PASSED', 'output': args.output, 'source_reference_and_native_packages_unchanged': protected,
        'video_rendered': args.video, 'native_RE9_outputs_written': False, 'runtime_tested': False,
    })
    print('Offline retarget workflow passed')


if __name__ == '__main__':
    main()

