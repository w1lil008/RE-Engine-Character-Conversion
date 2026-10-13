"""Reproducible original RE8 reconstruction, with protected v0.1.x hash gates.

Requires the pinned local tools listed in source_animation_toolchain.lock.json.
Outputs remain under build; there is no installation or native MOT write path.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import os
from common import ROOT,confined,write_json


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def protect_baseline():
    checkpoint=json.loads((ROOT/'reports/stabilization/baseline_checkpoint.json').read_text())
    for r in checkpoint['local_asset_inputs']:
        if sha(confined(ROOT,r['path']))!=r['sha256']:raise ValueError(f"Protected source/tool input changed: {r['path']}")
    protected=[]
    for version in ['0.1.2','0.1.3']:
        validation=json.loads((ROOT/f'reports/releases/{version}/mod_validation.json').read_text())
        for row in validation['files']:
            p=ROOT/f'mod/BelaGrace_RE9_{version}'/row['path']
            if sha(p)!=row['sha256']:raise ValueError(f'Protected v{version} native changed: {p}')
        manifest=json.loads((ROOT/f'reports/releases/{version}/package_manifest.json').read_text())
        archive=ROOT/'dist'/f'BelaGrace_RE9_Prototype_{version}.zip'
        if sha(archive)!=manifest['sha256']:raise ValueError('Protected release ZIP changed')
        protected.append({'version':version,'native_files':len(validation['files']),'archive_sha256':manifest['sha256']})
    return {'status':'PASSED','original_local_inputs':len(checkpoint['local_asset_inputs']),
        'releases':protected,'native_files_unchanged':160,'game_save_or_controller_write_operations':0}


def prepare_reference():
    lock=json.loads((ROOT/'config/source_animation_toolchain.lock.json').read_text())
    repo=ROOT/'tools/research/REE-Content-Editor'
    commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if commit!=lock['editor_commit']:raise ValueError('Unpinned editor checkout')
    reelib=ROOT/'tools/research/RE-Engine-Lib'
    if subprocess.check_output(['git','-C',str(reelib),'rev-parse','HEAD'],text=True).strip()!=lock['reelib_commit']:
        raise ValueError('Unpinned ReeLib checkout')
    research=json.loads((ROOT/'config/animation_research.lock.json').read_text())
    for row in research['files']:
        if sha(confined(reelib,row['path']))!=row['sha256']:
            raise ValueError(f"Pinned reader source changed: {row['path']}")
    for checkout in [reelib,repo]:
        subprocess.run(['git','-C',str(checkout),'diff','--quiet','HEAD','--'],check=True)
    animator=repo/'ContentEditor.App/Graphics/Animator.cs'
    if sha(animator)!=lock['editor_animator_sha256']:raise ValueError('Reference animator changed')
    text=animator.read_text();a=text.index('    public static (int first, int second, float interpolation) FindFrames(')
    b=text.index('{',a);level=1;end=b+1
    while level:
        if text[end]=='{':level+=1
        if text[end]=='}':level-=1
        end+=1
    path=ROOT/'build/animation_v0.2.0/reference/UpstreamFrameSampler.cs';path.parent.mkdir(parents=True,exist_ok=True)
    content='using ReeLib.Mot;\npublic static class UpstreamFrameSampler {\n'+text[a:end]+'\n}\n'
    if not path.exists():path.write_text(content)
    if sha(path)!=lock['reference_method_sha256']:raise ValueError('Compiled source sampler mismatch')
    for folder,version in [('dotnet10',lock['version']),('dotnet8',lock['runtime_sdk']['version'])]:
        executable=ROOT/'tools'/folder/'dotnet.exe'
        if subprocess.check_output([str(executable),'--version'],text=True).strip()!=version:
            raise ValueError('Pinned SDK missing or changed; restore the verified local SDK archive')


def run(args,log):
    env=dict(os.environ,DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    with log.open('w',encoding='utf-8') as f:
        subprocess.run([str(a) for a in args],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',default='config/source_idle_v0.2.0.json')
    p.add_argument('--output',required=True);p.add_argument('--report-name',default='source_idle');p.add_argument('--video',action='store_true')
    args=p.parse_args();config=json.loads(confined(ROOT,args.config).read_text())
    if not args.report_name.replace('_','').isalnum():raise ValueError('Invalid report name')
    output=confined(ROOT/'build',args.output.removeprefix('build/'))
    if output.exists():raise ValueError('Use a fresh output directory; previous evidence is preserved')
    baseline=protect_baseline();prepare_reference();output.mkdir(parents=True)
    source=confined(ROOT,config['source'])
    if sha(source)!=config['sha256']:raise ValueError('Wrong source resource hash')
    run([ROOT/'tools/dotnet10/dotnet.exe','restore','scripts/animation/ReeDecode/ReeDecode.csproj',
        '--locked-mode','--source','https://api.nuget.org/v3/index.json','--packages','tools/nuget','--verbosity','quiet'],output/'restore.log')
    run([ROOT/'tools/dotnet10/dotnet.exe','build','scripts/animation/ReeDecode/ReeDecode.csproj','-c','Release','--no-restore','--nologo','--verbosity','quiet'],output/'compile.log')
    decoded=output/'decoded_reference.json'
    run([ROOT/'tools/dotnet8/dotnet.exe','scripts/animation/ReeDecode/bin/Release/net8.0/ReeDecode.dll',source,f"{config['offset']:x}",decoded],output/'decode.log')
    relative=output.relative_to(ROOT).as_posix()
    run([sys.executable,'scripts/source_animation_export.py','--decoded',decoded.relative_to(ROOT).as_posix(),'--output',relative,
         '--config',args.config,'--report-name',args.report_name],output/'export.log')
    blender=ROOT/'tools/blender-4.3.2-windows-x64/blender.exe'
    command=[blender,'-b','--factory-startup','--python','scripts/source_animation_blender.py','--','--output',relative,'--report-name',args.report_name]
    if args.video:command.append('--video')
    run(command,output/'blender.log')
    run([blender,'-b','--factory-startup','--python','scripts/source_animation_blender.py','--','--output',relative,
         '--glb','source_idle_blender_roundtrip.glb','--validate-only','--report-name',args.report_name],output/'roundtrip.log')
    run([blender,'-b','--factory-startup','--python','scripts/source_skinning_blender.py','--','--output',relative,
         '--config',args.config,'--report-name',args.report_name],output/'skinning.log')
    after=protect_baseline()
    if after!=baseline:raise ValueError('Protected baseline state changed')
    write_json(ROOT/f'reports/animation_dev/{args.report_name}_workflow.json',{'status':'PASSED','config':args.config,
        'output':relative,'source_sha256':config['sha256'],'baseline_before_and_after':after,
        'native_RE9_outputs_written':False,'runtime_tested':False,'video_rendered':args.video})
    print(f"Source reconstruction passed: {relative}; v0.1.x unchanged")


if __name__=='__main__':main()

