"""Owned fresh-path runtime experiment staging and rollback. Never overwrites assets."""
import argparse
import datetime
import json
import re
from pathlib import Path
from common import ROOT,confined,write_json
from source_animation_workflow import sha
from runtime_preflight import check,NATIVE
from runtime_resource_bridge import verify

REPORTS=ROOT/'reports/runtime_experiment_v0.2.0'
BUILD=ROOT/'build/animation_v0.2.0/runtime_experiment'

def lua_value(value):
    if value is True:return 'true'
    if value is False:return 'false'
    if isinstance(value,str):return json.dumps(value)
    if type(value) in (int,float):return str(value)
    if isinstance(value,list):return '{'+','.join(lua_value(v) for v in value)+'}'
    if isinstance(value,dict):return '{'+','.join('['+json.dumps(k)+']='+lua_value(v) for k,v in value.items())+'}'
    raise ValueError('Unsupported Lua plan value')

def staging_gate(game_running,live_fresh_path,mode,owned_scene,motion_info):
    if live_fresh_path and (mode!='resource_only' or not owned_scene or not motion_info):
        raise ValueError('Live fresh-path staging is restricted to isolated owned resource sampling')
    if game_running and not live_fresh_path:raise ValueError('Close RE9 before staging, or use the isolated live fresh-path gate')

def sample_plan():
    from native_mot import decode_float_mot
    original=json.loads((ROOT/'build/animation_v0.2.0/native_idle_canonical/original_grace_idle.json').read_text())
    native=decode_float_mot((NATIVE/'bela_idle.mot.983').read_bytes())
    def arm(label,motion,frames):
        return {'label':label,'end_frame':motion['end'],'frames':frames,'tracks':[
            {'name':t['bone'],'hash':t['hash'],'rotation':bool(t.get('rotation')),
             'translation':bool(t.get('translation')),'scale':bool(t.get('scale'))}
            for t in motion['tracks']]}
    return {'schema':'bela-engine-sample-plan-v1','native_sha256':sha(NATIVE/'bela_idle.motlist.1047'),
        'arms':[arm('CONTROL',original,[0,.5,150,300,814]),arm('BELA',native,[i*.5 for i in range(601)])]}


def stage(game,source,session):
    if not re.fullmatch(r'[a-z0-9_]{8,64}',session):raise ValueError('Invalid session')
    relative=f'natives/stm/animation/bela_prototype/v020/{session}/bela_idle.motlist.1047'
    target=confined(Path(game),relative)
    target.parent.mkdir(parents=True,exist_ok=True)
    data=Path(source).read_bytes()
    with target.open('xb') as stream:stream.write(data)
    if sha(target)!=sha(source):raise ValueError('Staged file differs')
    return {'session':session,'relative_path':relative,'sha256':sha(target),'bytes':len(data),
        'runtime_path':f'Animation/bela_prototype/v020/{session}/bela_idle.motlist',
        'new_file_only':True,'source_sha256':sha(source)}


def remove_owned(game,manifest,game_running):
    if game_running:raise ValueError('Exit RE9 before resource removal')
    expected=f"natives/stm/animation/bela_prototype/v020/{manifest['session']}/bela_idle.motlist.1047"
    if manifest.get('relative_path')!=expected or not re.fullmatch(r'[a-z0-9_]{8,64}',manifest['session']):
        raise ValueError('Ownership path mismatch')
    target=confined(Path(game),expected)
    if not target.is_file() or sha(target)!=manifest['sha256']:raise ValueError('Ownership hash mismatch')
    target.unlink()  # Single checked owned file. No directory, archive or save removal.
    return {'removed_owned_file':expected,'preexisting_files_removed':0,'directories_removed':0}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=['preview','stage','rollback']);parser.add_argument('--session',required=True)
    parser.add_argument('--mode',choices=['load_only','resource_only','control_only'],default='load_only')
    parser.add_argument('--query-standalone',action='store_true',help='Query newly constructed unattached banks; never plays')
    parser.add_argument('--setup-unattached',action='store_true',help='Rejected legacy option: ownerless Motion failed live validation')
    parser.add_argument('--setup-owned-scene',action='store_true',help='Initialize banks on a new owned scene object, then destroy it')
    parser.add_argument('--query-motion-info',action='store_true',help='Query metadata on the new initialized component; no pose sampling')
    parser.add_argument('--sample-engine',action='store_true',help='Sample loaded MotionInfo into new result containers; never plays')
    parser.add_argument('--live-fresh-path',action='store_true',help='Add only a never-requested path while running, for isolated owned sampling')
    args=parser.parse_args()
    if args.setup_unattached:raise ValueError('Ownerless Motion failed live validation; use --setup-owned-scene')
    if args.query_motion_info and not args.setup_owned_scene:raise ValueError('MotionInfo requires owned scene setup')
    if args.sample_engine and not args.query_motion_info:raise ValueError('Engine sampling requires MotionInfo')
    if not re.fullmatch(r'[a-z0-9_]{8,64}',args.session):raise ValueError('Invalid session')
    manifest_path=REPORTS/(args.session+'_ownership.json')
    before=check()
    if before['changed_protected_files'] or before['missing_protected_files']:raise ValueError('Protected installation changed')
    if before['steam_build_id']!='23634047' or before['exe_versions']['FileVersion']!='1.3.1.0':raise ValueError('Unexpected game build')
    if args.operation!='rollback':staging_gate(before['game_running'],args.live_fresh_path,args.mode,args.setup_owned_scene,args.query_motion_info)
    if args.operation=='preview':
        relative=f'natives/stm/animation/bela_prototype/v020/{args.session}/bela_idle.motlist.1047'
        print(json.dumps({'operation':'preview','files_to_add':[relative],
            'source':str(NATIVE/'bela_idle.motlist.1047'),'sha256':sha(NATIVE/'bela_idle.motlist.1047'),
            'destination_exists':confined(Path(before['game_directory']),relative).exists(),
            'game_running':before['game_running'],'mode':args.mode,'query_standalone':args.query_standalone or args.setup_unattached or args.setup_owned_scene,
            'setup_unattached':args.setup_unattached,
            'setup_owned_scene':args.setup_owned_scene,
            'query_motion_info':args.query_motion_info,
            'live_fresh_path':args.live_fresh_path,'sample_engine':args.sample_engine,
            'original_files_to_replace':[],'playback_implemented':False,'writes_performed':0},indent=2))
        return
    REPORTS.mkdir(parents=True,exist_ok=True)
    if args.operation=='stage':
        if manifest_path.exists():raise ValueError('Preserve previous ownership record')
        if (BUILD/args.session).exists():raise ValueError('Preserve existing build session')
        baseline=json.loads((ROOT/'reports/runtime_binding_v0.2.0/environment_before.json').read_text(encoding='utf-8'))
        expected=next(r['sha256'] for r in baseline['protected_installed_files'] if r['path']=='re9.exe')
        bridge=verify(before['game_directory'],expected)
        record=stage(before['game_directory'],NATIVE/'bela_idle.motlist.1047',args.session)
        record['preflight']=before;record['staged_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_json(manifest_path,record)
        config=BUILD/args.session/'session.json'
        parameters={'session':args.session,'resource_path':record['runtime_path'],'native_sha256':record['sha256'],
            'resource_bridge_build_checked':bridge['checked'],'mode':args.mode,'auto_start':True,'auto_cleanup':True,
            'query_standalone':args.query_standalone or args.setup_unattached or args.setup_owned_scene,
            'setup_unattached':args.setup_unattached,'setup_owned_scene':args.setup_owned_scene,
            'query_motion_info':args.query_motion_info,
            'context':'live_gameplay' if args.live_fresh_path else 'main_menu',
            'playback_authorized_conditionally':True,
            'resource_reference_offset_evidence':bridge,
            'control_resource_path':'Animation/ch/ch02/ch0200/motlist/ch0200_generalm.motlist'}
        write_json(config,parameters)
        if args.sample_engine:
            plan=sample_plan();write_json(config.parent/'sample_plan.json',plan)
            plan_path=config.parent/'sample_plan.lua'
            with plan_path.open('x',encoding='utf-8',newline='\n') as stream:stream.write('return '+lua_value(plan)+'\n')
            parameters['sample_plan_path']=plan_path.as_posix();write_json(config,parameters)
        harness=config.parent/'harness_used.lua'
        with harness.open('xb') as stream:stream.write((ROOT/'scripts/runtime/bela_runtime_test.lua').read_bytes())
        write_json(config.parent/'code_identity.json',{'harness_sha256':sha(harness),'stage_script_sha256':sha(Path(__file__)),
            'resource_bridge_script_sha256':sha(ROOT/'scripts/runtime_resource_bridge.py')})
        entry=config.parent/'run_test.lua'
        # All strings originate in validated paths/constants; no shell interpolation.
        fields=','.join(k+'='+('true' if v is True else 'false' if v is False else json.dumps(v))
            for k,v in parameters.items() if k!='resource_reference_offset_evidence')
        with entry.open('x',encoding='utf-8',newline='\n') as stream:
            stream.write('return dofile('+json.dumps(harness.as_posix())+')({'+fields+'})\n')
        print(json.dumps({'owned_resource':record['relative_path'],'config':str(config)}))
    else:
        record=json.loads(manifest_path.read_text(encoding='utf-8'))
        target=REPORTS/(args.session+'_rollback.json')
        if target.exists():raise ValueError('Preserve previous rollback report')
        result=remove_owned(before['game_directory'],record,before['game_running'])
        write_json(target,result);print(json.dumps(result))


if __name__=='__main__':main()

