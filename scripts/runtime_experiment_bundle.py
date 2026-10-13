"""Deterministic, non-installing archive of the tested development workflow.

This bundle belongs to the existing workspace, not a generic mod-manager installer.
Original game clips, character assets, SDK dependencies and saves are excluded.
"""
import argparse,json,zipfile
from pathlib import Path
from common import ROOT,write_json
from source_animation_workflow import sha

REPORTS=ROOT/'reports/runtime_experiment_v0.2.0'
OUTPUT=ROOT/'dist/BelaGrace_RuntimeExperiment_0.2.0_ValidatedPrototype.zip'

def bundle_files():
    native=ROOT/'build/animation_v0.2.0/native_idle_canonical/native/bela_idle.motlist.1047'
    if sha(native)!='48505359a3dd5411dc98582649964cce07c10a7114229d0a60db96dd5467c477':
        raise ValueError('Accepted native input differs')
    required={
        'engine_channel_comparison_corrected.json':('engine_channel_comparison_passed',True),
        'grace_zero_weight_20261011_c_analysis.json':('status','PASSED'),
        'grace_one_cycle_20261011_b_analysis.json':('status','PASSED'),
        'live_applied_rotation_comparison.json':('live_rotation_comparison_passed',True),
        'automated_tests_release.json':('successful',True),
        'final_protection_and_rollback.json':('owned_loose_animation_files_remaining',0)}
    for name,(key,value) in required.items():
        if json.loads((REPORTS/name).read_text()).get(key)!=value:raise ValueError('Evidence gate failed: '+name)
    files={'native/bela_idle.motlist.1047':native.read_bytes(),
        'README.md':(ROOT/'docs/RUNTIME_ANIMATION_EXPERIMENT_V0.2.0.md').read_bytes()}
    scripts=['runtime_one_cycle.py','runtime_applied_motion.py','runtime_engine_samples.py','runtime_experiment.py',
        'runtime_experiment_evidence.py','runtime_resource_bridge.py','runtime_rig_analysis.py','runtime_bank_api_analysis.py',
        'runtime_experiment_bundle.py','runtime/bela_one_cycle.lua','runtime/bela_runtime_test.lua',
        'runtime/bela_after_restore.lua','runtime/bela_bank_api_probe.lua','runtime/bela_rig_probe.lua','runtime/bela_binding_probe_v7.lua']
    for name in scripts:files['workspace_scripts/'+name]=(ROOT/'scripts'/name).read_bytes()
    for name in required:files['evidence/'+name]=(REPORTS/name).read_bytes()
    for name in ['live_all_animated_track_constraints.json','isolated_layer_lifecycle.json','one_cycle_b_screenshots.json']:
        files['evidence/'+name]=(REPORTS/name).read_bytes()
    # Reference the actual frozen live code, separately from later hardening.
    live=ROOT/'build/animation_v0.2.0/runtime_experiment/grace_one_cycle_20261011_b'
    for name in ['harness_used.lua','probe_used.lua','session.json','preparation_manifest.json']:
        files['successful_live_reference/'+name]=(live/name).read_bytes()
    return files

def create(output):
    files=bundle_files()
    import hashlib
    manifest={'schema':'bela-runtime-prototype-package-v1','workspace_required':True,'autorun':False,
        'mod_manager_installer':False,'original_asset_overrides':[],
        'scope':'Development archive for the existing pinned workspace; explicit preview/staging and frozen session preparation required.',
        'files':[{'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in sorted(files.items())]}
    files['MANIFEST.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3;info.external_attr=0o100644<<16
            archive.writestr(info,data,compresslevel=9)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise ValueError('Archive integrity failed')
        if set(archive.namelist())!=set(files):raise ValueError('Unexpected bundle contents')
        for name,data in files.items():
            if archive.read(name)!=data:raise ValueError('Bundle data differs: '+name)
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=OUTPUT);args=parser.parse_args()
    manifest=create(args.output)
    report=REPORTS/'prototype_package_manifest.json'
    if report.exists():raise ValueError('Preserve previous package manifest')
    write_json(report,{'package':args.output.relative_to(ROOT).as_posix(),'sha256':sha(args.output),
        'bytes':args.output.stat().st_size,**manifest})
    print(json.dumps({'package':str(args.output),'sha256':sha(args.output),'files':len(manifest['files'])+1}))

