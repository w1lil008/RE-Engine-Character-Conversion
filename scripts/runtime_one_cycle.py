"""Freeze, gate and analyze the bounded live experiment; never controls the UI.

prepare creates workspace files only. An existing staged, hash-matched resource
and observed live proofs are required; no original animation slot is replaced.
"""
import argparse,json,math,re
from pathlib import Path
from common import ROOT,write_json,confined
from runtime_capture import load_capture
from runtime_experiment import BUILD,REPORTS,lua_value,sample_plan,stage,remove_owned
from runtime_preflight import check,NATIVE,PROBE
from source_animation_workflow import sha

NATIVE_SHA='48505359a3dd5411dc98582649964cce07c10a7114229d0a60db96dd5467c477'
RESOURCE_SESSION='engine_decode_20261011_c'
RESOURCE_PATH=f'Animation/bela_prototype/v020/{RESOURCE_SESSION}/bela_idle.motlist'
NAME='Bela_Approved_Idle_Offline_300f_60fps'

def session_name(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z0-9_]{8,64}',value):raise ValueError('Invalid session')
    return value

def finite(value):return type(value) in (int,float) and math.isfinite(value)

def validate_environment(preflight):
    if preflight['changed_protected_files'] or preflight['missing_protected_files']:raise ValueError('Protected files changed')
    if preflight['steam_build_id']!='23634047' or preflight['exe_versions']['FileVersion']!='1.3.1.0':raise ValueError('Game build differs')
    if not preflight['official_archive_size_mtime_unchanged']:
        raise ValueError('Official archives changed')

def verify_steam_identity(game):
    # Steam's whole ACF changes with LastPlayed during normal launches. Verify
    # its installation/build identifiers rather than requiring a stale hash.
    manifest=Path(game).parents[1]/'appmanifest_3764200.acf'
    if manifest.stat().st_size>1024*1024:raise ValueError('Unexpected Steam manifest size')
    text=manifest.read_text();identity={}
    for key,expected in [('appid','3764200'),('buildid','23634047'),('TargetBuildID','23634047')]:
        found=re.findall(r'"'+key+r'"\s+"([^"]*)"',text)
        if found!=[expected]:raise ValueError('Steam build identity differs: '+key)
        identity[key]=found[0]
    return {'identifiers':identity,'current_manifest_sha256':sha(manifest),
        'scope':'Current installed and target build IDs; volatile LastPlayed/whole-manifest byte equality is not required.'}

def restage_resource(game,source,test_session):
    session_name(test_session)
    if sha(source)!=NATIVE_SHA:raise ValueError('Only the accepted native resource may be restaged')
    record=stage(game,source,RESOURCE_SESSION)
    record['test_session']=test_session
    record['scope']='Recreate only the previously validated, removed experiment path. Never overwrite an existing file.'
    return record

def resource_operation(operation,session):
    session_name(session);preflight=check();validate_environment(preflight)
    if preflight['game_running']:raise ValueError('Exit RE9 before resource staging or rollback')
    game=Path(preflight['game_directory'])
    verify_steam_identity(game)
    relative=f'natives/stm/animation/bela_prototype/v020/{RESOURCE_SESSION}/bela_idle.motlist.1047'
    target=confined(game,relative)
    manifest=REPORTS/(session+'_restage_ownership.json')
    if operation=='preview_resource':
        return {'writes_performed':0,'file_to_add':relative,'destination_exists':target.exists(),
            'source_sha256':sha(NATIVE/'bela_idle.motlist.1047'),'original_files_to_replace':[],
            'explicit_stage_operation_required':True}
    if operation=='stage_resource':
        if manifest.exists():raise ValueError('Preserve previous resource ownership record')
        record=restage_resource(game,NATIVE/'bela_idle.motlist.1047',session)
        write_json(manifest,record);return record
    if operation=='rollback_resource':
        out=REPORTS/(session+'_restage_rollback.json')
        if out.exists():raise ValueError('Preserve previous rollback record')
        record=json.loads(manifest.read_text())
        if record.get('test_session')!=session or record.get('sha256')!=NATIVE_SHA:raise ValueError('Restage ownership differs')
        result=remove_owned(game,record,False);write_json(out,result);return result
    raise ValueError('Unknown resource operation')

def analyze(document):
    if not isinstance(document,dict) or document.get('schema')!='bela-one-cycle-v1':raise ValueError('Wrong one-cycle schema')
    session=session_name(document.get('session'));config=document.get('config') or {}
    if config.get('session')!=session or config.get('native_sha256')!=NATIVE_SHA or config.get('resource_path')!=RESOURCE_PATH:
        raise ValueError('Accepted resource/config identity differs')
    mode=config.get('mode')
    if mode not in ('dry_run','one_cycle'):raise ValueError('Unknown mode')
    events=document.get('events') or [];poses=document.get('poses') or [];errors=document.get('errors') or []
    if not isinstance(events,list) or len(events)>120 or not isinstance(poses,list) or len(poses)>180 or not isinstance(errors,list):
        raise ValueError('Malformed or unbounded evidence')
    stages=[e['stage'] for e in events]
    baseline=document.get('baseline') or {};cleanup=document.get('cleanup') or {}
    expected={t['name']:t for t in sample_plan()['arms'][1]['tracks']}
    problems=[]
    if document.get('phase')!='COMPLETE' or document.get('bound') is not False:problems.append('Not completely detached')
    if document.get('controller_state_changed_directly') is not False or document.get('existing_layers_replaced') is not False:
        problems.append('Protected controller/layer mutation reported')
    if mode=='dry_run' and document.get('playback_requested') is not False:problems.append('Dry run activated playback')
    required=['BASELINE_VERIFIED','ZERO_WEIGHT_BINDING_TEST','ZERO_WEIGHT_VALIDATED','CLEANUP_BEGIN','OBSERVING_RESTORED_IDLE','COMPLETE']
    if mode=='one_cycle':required[3:3]=['ARMED_FOR_ONE_CYCLE','PLAYBACK_ONE_CYCLE']
    if any(s not in stages for s in required) or [stages.index(s) for s in required if s in stages]!=sorted(stages.index(s) for s in required if s in stages):
        problems.append('Required phases missing or out of order')
    if baseline.get('dynamic_bank_count')!=3 or not 9<=baseline.get('layer_count',0)<=32:problems.append('Unexpected baseline layout')
    if cleanup.get('layer_count')!=baseline.get('layer_count') or cleanup.get('bank_count')!=3 or cleanup.get('original_references_preserved') is not True:
        problems.append('Original layout/references not restored')
    initial=baseline.get('layer0') or {};restored=cleanup.get('after_five_seconds') or {}
    for key in ('address','bank','motion','enabled','mask','weight','joint_count'):
        if initial.get(key)!=restored.get(key) or key not in initial:problems.append('Restored idle differs: '+key)
    if initial.get('bank')!=0 or initial.get('motion')!=1 or initial.get('joint_count')!=80:problems.append('Unverified idle baseline')
    frames={'ZERO_WEIGHT_BINDING_TEST':[],'PLAYBACK_ONE_CYCLE':[]};norm_error=0.
    for pose in poses:
        layer=pose.get('layer') or {};phase=pose.get('phase')
        if layer.get('bank')!=65000 or layer.get('motion')!=0 or layer.get('ending')!=300 or layer.get('joint_count')!=80:
            problems.append('Candidate layer identity differs')
        if not finite(layer.get('frame')) or not 0<=layer['frame']<=300:raise ValueError('Invalid candidate time')
        if phase in frames:frames[phase].append(layer['frame'])
        if layer.get('weight')!=(1.0 if phase=='PLAYBACK_ONE_CYCLE' else 0.0):problems.append('Incorrect layer weight')
        if pose.get('motion_info')!={'found':True,'name':NAME}:problems.append('Layer resource not verified')
        joints=pose.get('joints') or []
        if len(joints)!=24 or {j['name'] for j in joints}!=set(expected):raise ValueError('Incomplete/duplicate joint set')
        indices=set()
        for joint in joints:
            if joint.get('hash')!=expected[joint['name']]['hash']:raise ValueError('Joint hash differs')
            index=joint.get('index')
            if type(index) is not int or not 0<=index<80 or index in indices:raise ValueError('Invalid/duplicate joint index')
            indices.add(index)
            for field,width in [('rotation',4),('position',3)]:
                v=joint.get(field)
                if not isinstance(v,list) or len(v)!=width or not all(finite(x) for x in v):raise ValueError('Malformed pose vector')
            norm_error=max(norm_error,abs(math.sqrt(sum(x*x for x in joint['rotation']))-1))
    if len(frames['ZERO_WEIGHT_BINDING_TEST'])<2 or max(frames['ZERO_WEIGHT_BINDING_TEST'],default=0)<=4:problems.append('No advancing zero-weight evidence')
    if norm_error>1e-4:problems.append('Nonunit live quaternion')
    complete_cycle=False
    if mode=='one_cycle':
        if document.get('playback_requested') is not True:problems.append('No visible playback requested')
        endings=[e['data'] for e in events if e['stage']=='CLEANUP_BEGIN']
        complete_cycle=any(e.get('reason') in ('One native cycle complete','One native cycle completed at first loop wrap') for e in endings)
        if not complete_cycle or len(frames['PLAYBACK_ONE_CYCLE'])<10 or max(frames['PLAYBACK_ONE_CYCLE'],default=0)<290:
            problems.append('Full native cycle not demonstrated')
    return {'schema':'bela-one-cycle-analysis-v1','session':session,'mode':mode,
        'status':'PASSED' if not problems and not errors else 'FAILED','validation_errors':sorted(set(problems)),
        'runtime_errors':errors,'sample_counts':{k:len(v) for k,v in frames.items()},
        'sampled_frame_ranges':{k:[min(v),max(v)] if v else None for k,v in frames.items()},
        'maximum_quaternion_norm_error':norm_error,'original_layout_restored':not any('restore' in p.lower() for p in problems),
        'playback_cycle_observed':complete_cycle,'visual_acceptance_verified':False,
        'scope':'Live layer timing and explicit joint lookup/cleanup. Visual motion and procedural composition require separate evidence.'}

def collect(session):
    session_name(session)
    game=Path(json.loads((ROOT/'config/project.json').read_text())['games']['re9'])
    paths=sorted([p for p in (game/'reframework/data/bela_runtime_test').glob(session+'_*.json')
        if re.fullmatch(re.escape(session)+r'_\d+',p.stem)],key=lambda p:int(p.stem.rsplit('_',1)[1]))
    if not paths:raise ValueError('No live capture')
    result=analyze(load_capture(paths[-1]));result['capture_sha256']=sha(paths[-1]);result['capture_count']=len(paths)
    folder=BUILD/session;folder.mkdir(parents=True,exist_ok=True);files=[]
    for p in [*paths,game/'re2_framework_log.txt']:
        out=folder/p.name
        if out.exists() and sha(out)!=sha(p):raise ValueError('Evidence conflict; preserve the previous collection')
        if not out.exists():
            with out.open('xb') as f:f.write(p.read_bytes())
        files.append({'path':out.relative_to(ROOT).as_posix(),'sha256':sha(out),'bytes':out.stat().st_size})
    result['files']=files;result['raw_capture']=str(folder/paths[-1].name)
    out=REPORTS/(session+'_analysis.json')
    if out.exists():raise ValueError('Preserve existing analysis')
    write_json(out,result);return result

def prepare(session,mode):
    session_name(session)
    preflight=check()
    validate_environment(preflight)
    preflight['verified_current_steam_identity']=verify_steam_identity(preflight['game_directory'])
    evidence={
        'engine_decode':REPORTS/'engine_channel_comparison_corrected.json',
        'all_24_constraints':REPORTS/'live_all_animated_track_constraints.json',
        'isolated_layer_lifecycle':REPORTS/'isolated_layer_lifecycle.json'}
    engine=json.loads(evidence['engine_decode'].read_text());rig=json.loads(evidence['all_24_constraints'].read_text())
    lifecycle=json.loads(evidence['isolated_layer_lifecycle'].read_text())
    if engine.get('engine_channel_comparison_passed') is not True or engine.get('native_sha256')!=NATIVE_SHA:raise ValueError('Engine decode proof missing')
    expected={t['name'] for t in sample_plan()['arms'][1]['tracks']}
    if rig.get('runtime_errors') or len(rig.get('renderers',[]))!=2 or any(set(r['verified_constraints'])!=expected or r['unavailable_joints'] for r in rig['renderers']):
        raise ValueError('All 24 renderer constraints required')
    isolated=lifecycle.get('evidence') or {}
    if lifecycle.get('errors') or lifecycle.get('cleanup_verified') is not True or lifecycle.get('no_existing_character_modified') is not True or \
            isolated.get('grow_preserved_references') is not True or isolated.get('shrink_preserved_reference') is not True or \
            isolated.get('bank_id')!=65000 or isolated.get('blend_rate')!=0 or isolated.get('layer_enabled') is not False:
        raise ValueError('Isolated layer lifecycle proof missing')
    if mode=='one_cycle':
        evidence['live_zero_weight_cleanup']=REPORTS/'grace_zero_weight_20261011_c_analysis.json'
        dry=json.loads(evidence['live_zero_weight_cleanup'].read_text())
        if dry.get('status')!='PASSED' or dry.get('mode')!='dry_run':raise ValueError('Live zero-weight cleanup gate failed')
        if sha(Path(dry['raw_capture']))!=dry['capture_sha256'] or analyze(load_capture(dry['raw_capture']))['status']!='PASSED':
            raise ValueError('Live gate provenance differs')
    game=Path(preflight['game_directory']);ownership=json.loads((REPORTS/(RESOURCE_SESSION+'_ownership.json')).read_text())
    if ownership['sha256']!=NATIVE_SHA or sha(confined(game,ownership['relative_path']))!=NATIVE_SHA or sha(NATIVE/'bela_idle.motlist.1047')!=NATIVE_SHA:
        raise ValueError('Owned resource identity differs')
    target=BUILD/session
    if target.exists():raise ValueError('Preserve existing session')
    target.mkdir(parents=True)
    for source,name in [(ROOT/'scripts/runtime/bela_one_cycle.lua','harness_used.lua'),(PROBE,'probe_used.lua')]:
        with (target/name).open('xb') as f:f.write(source.read_bytes())
    config={'mode':mode,'session':session,'native_sha256':NATIVE_SHA,'resource_path':RESOURCE_PATH,
        'probe_path':(target/'probe_used.lua').as_posix(),'preview_delay_seconds':12 if mode=='one_cycle' else 0,
        'gates':{key:True for key in evidence},'tracks':sample_plan()['arms'][1]['tracks']}
    with (target/'run_test.lua').open('x',encoding='utf-8') as f:
        f.write('return dofile('+lua_value((target/'harness_used.lua').as_posix())+')('+lua_value(config)+')\n')
    write_json(target/'session.json',config)
    write_json(target/'preparation_manifest.json',{'preflight':preflight,'gate_files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in evidence.values()],
        'frozen_code':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in sorted(target.glob('*.lua'))],
        'installation_changes':[],'existing_resource_reused':ownership['relative_path']})
    return {'entry':str(target/'run_test.lua'),'mode':mode,'game_files_changed':0}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=['prepare','collect','preview_resource','stage_resource','rollback_resource']);p.add_argument('--session',required=True)
    p.add_argument('--mode',choices=['dry_run','one_cycle'],default='dry_run');args=p.parse_args()
    result=prepare(args.session,args.mode) if args.operation=='prepare' else collect(args.session) if args.operation=='collect' else resource_operation(args.operation,args.session)
    print(json.dumps({k:v for k,v in result.items() if k not in ('files','raw_capture')},indent=2))

