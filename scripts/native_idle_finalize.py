"""Finalize the native-animation review package; never install or activate it."""
import io
import json
import shutil
import unittest
import zipfile
from common import ROOT, write_json
from source_animation_workflow import sha
from native_animation_protection import protect

PRIMARY=ROOT/'build/animation_v0.2.0/native_idle_canonical'
REPEAT=ROOT/'build/animation_v0.2.0/native_idle_canonical_repeat'
REPORTS=ROOT/'reports/native_animation_v0.2.0'
PACKAGE=ROOT/'dist/BelaGrace_NativeAnimation_0.2.0_MilestoneC.zip'

def main():
    protected=protect()
    for folder in (PRIMARY,REPEAT):
        for file in ('workflow_report.json','reimport_report.json','roundtrip_report.json'):
            if json.loads((folder/file).read_text())['status']!='PASSED':raise ValueError('A native validation gate failed')
    for name in ('bela_idle.mot.983','bela_idle.motlist.1047'):
        if (PRIMARY/'native'/name).read_bytes()!=(REPEAT/'native'/name).read_bytes():raise ValueError('Native repeat differs')
    roundtrip=json.loads((REPEAT/'roundtrip_report.json').read_text())
    if roundtrip['original_idle_decoded_float_roundtrip']['status']!='PASSED':raise ValueError('Original idle roundtrip incomplete')
    for file,source in [('roundtrip_report.json',REPEAT),('reimport_report.json',PRIMARY),('metadata_dispositions.json',PRIMARY)]:
        shutil.copyfile(source/file,REPORTS/file)
    output=io.StringIO();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    (REPORTS/'automated_tests.log').write_text(output.getvalue(),encoding='utf-8')
    tests={'status':'PASSED' if result.wasSuccessful() else 'FAILED','tests_run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),
        'includes':'Original 39 tests plus native regression tests, the full two-pass native workflow and sampled independent reimport gates.'}
    write_json(REPORTS/'automated_tests.json',tests)
    if not result.wasSuccessful() or result.skipped:raise ValueError('Tests failed or skipped; do not package')
    files={
        'resources/bela_idle.mot.983':(PRIMARY/'native/bela_idle.mot.983').read_bytes(),
        'resources/bela_idle.motlist.1047':(PRIMARY/'native/bela_idle.motlist.1047').read_bytes(),
        'NATIVE_ANIMATION_V0.2.0.md':(ROOT/'docs/NATIVE_ANIMATION_V0.2.0.md').read_bytes(),
        'README.txt':('Milestone C native-animation DEVELOPMENT REVIEW package\n'
            'Not installed or runtime-tested. User authorization is required for Milestone D.\n'
            'No original game archives, controllers, bank registration, saves or active mod were changed.\n'
            'These resource filenames are unregistered development artifacts, not installation destinations.\n'
            'Read NATIVE_ANIMATION_V0.2.0.md and the reports before an isolated runtime experiment.\n'
            'Rollback: no active changes to undo. Retain the accepted v0.1.x package and Milestone B outputs.\n'
            'Delete only this optional review package to discard it.\n').encode(),
    }
    for name in ('roundtrip_report.json','reimport_report.json','metadata_dispositions.json','binding_analysis.json','automated_tests.json'):
        files['reports/'+name]=(REPORTS/name).read_bytes()
    import hashlib
    manifest={'scope':'Unregistered offline native-animation prototype; not a runtime release',
        'source_reference_checkpoint':'e579c25','runtime_tested':False,'installed_or_registered':False,
        'files':[{'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in sorted(files.items())],
        'manifest_self_excluded_from_payload_hashes':True}
    files['MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    target=io.BytesIO()
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16;archive.writestr(info,data,compresslevel=9)
    data=target.getvalue()
    if PACKAGE.exists() and PACKAGE.read_bytes()!=data:raise ValueError('Existing review ZIP differs; preserve it and choose a new package name')
    PACKAGE.parent.mkdir(exist_ok=True)
    if not PACKAGE.exists():PACKAGE.write_bytes(data)
    with zipfile.ZipFile(PACKAGE) as archive:
        if archive.testzip() is not None or set(archive.namelist())!=set(files):raise ValueError('Package integrity failed')
        for name,data in files.items():
            if archive.read(name)!=data:raise ValueError('Packaged payload differs')
    write_json(REPORTS/'package_manifest.json',dict(manifest,archive=PACKAGE.relative_to(ROOT).as_posix(),sha256=sha(PACKAGE),bytes=PACKAGE.stat().st_size,archive_members=len(files)))
    sources=[ROOT/'scripts/native_mot.py',ROOT/'scripts/native_idle_workflow.py',ROOT/'scripts/native_idle_finalize.py',
        ROOT/'scripts/native_animation_protection.py',ROOT/'scripts/native_binding_research.py',ROOT/'tests/test_native_animation.py']
    sources+=list((ROOT/'scripts/animation/ReeNative').glob('*.cs'))+list((ROOT/'scripts/animation/ReeNative').glob('*.csproj'))+list((ROOT/'scripts/animation/ReeNative').glob('*.json'))
    artifacts=[p for folder in (PRIMARY,REPEAT) for p in folder.rglob('*') if p.is_file()]
    write_json(REPORTS/'phase_results.json',{'status':'MILESTONE_C_STRUCTURAL_AND_ANIMATION_VALIDATION_PASSED',
        'milestone_B_user_visually_accepted':True,'native_runtime_tested':False,'installed_or_registered':False,
        'primary_output':PRIMARY.relative_to(ROOT).as_posix(),'repeat_output':REPEAT.relative_to(ROOT).as_posix(),
        'package':PACKAGE.relative_to(ROOT).as_posix(),'tests':tests,'protected_inputs':protected,
        'roundtrip':roundtrip,'reimport':json.loads((PRIMARY/'reimport_report.json').read_text()),
        'native_files_byte_identical_between_independent_runs':True,
        'next_gate':'User-authorized Milestone D: read-only live state capture, then reversible isolated loading/binding/playback experiment. Full XYZW engine support must be proven first.',
        'source_code_hashes':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in sources],
        'local_artifacts':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(artifacts)]})
    if protect()!=protected:raise ValueError('Protected baseline changed during finalization')
    print(f'{result.testsRun} tests passed; {len(files)} review-package members verified; native outputs repeat byte-identically')

if __name__=='__main__':main()

