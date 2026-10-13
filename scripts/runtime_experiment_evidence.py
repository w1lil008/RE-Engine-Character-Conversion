"""Strict experiment capture collection. Never treats a holder as decoded playback."""
import argparse
import json
import re
from pathlib import Path
from common import ROOT, confined, write_json
from source_animation_workflow import sha
from runtime_capture import load_capture

def analyze(document):
    problems=[]
    if not isinstance(document,dict):raise ValueError('Capture must be an object')
    if document.get('schema')!='bela-runtime-test-v1':problems.append('Unknown experiment schema')
    session=document.get('session')
    if not isinstance(session,str) or not re.fullmatch(r'[a-z0-9_]{8,64}',session):
        problems.append('Invalid session');session='invalid'
    config=document.get('config') or {}
    if not isinstance(config,dict):problems.append('Invalid configuration');config={}
    candidate=f'Animation/bela_prototype/v020/{session}/bela_idle.motlist'
    control='Animation/ch/ch02/ch0200/motlist/ch0200_generalm.motlist'
    if config.get('session')!=session or config.get('resource_path')!=candidate:
        problems.append('Owned resource/session mismatch')
    if config.get('control_resource_path')!=control:problems.append('Control path mismatch')
    for flag in ('loaded','registered','playback_performed','native_XYZW_runtime_verified','holder_references_cleared'):
        if type(document.get(flag)) is not bool:problems.append('Missing or nonboolean '+flag)
    events=document.get('events') or []
    if not isinstance(events,list) or len(events)>150:problems.append('Unbounded events');events=[]
    stages=[]
    for event in events:
        if not isinstance(event,dict) or not isinstance(event.get('stage'),str):problems.append('Malformed event');continue
        stages.append(event['stage'])
    errors=document.get('errors') or []
    if not isinstance(errors,list) or len(errors)>100 or any(not isinstance(e,str) for e in errors):
        problems.append('Malformed errors');errors=[]
    frames=document.get('heartbeat_frames')
    if type(frames) is not int or frames<0:problems.append('Invalid heartbeat count')
    resources=document.get('resources') or {}
    if not isinstance(resources,dict):problems.append('Invalid resource evidence');resources={}
    holders={}
    for label,path in [('CONTROL',control),('BELA',candidate)]:
        row=resources.get(label) or {}
        values=row.get('values') or {} if isinstance(row,dict) else {}
        observed=values.get('get_ResourcePath') if isinstance(values,dict) else None
        holders[label]=observed==path
        if observed is not None and observed!=path:problems.append(label+' holder path mismatch')
    queries=document.get('standalone_bank_queries') or {}
    if not isinstance(queries,dict):problems.append('Malformed bank queries');queries={}
    lookups={}
    motion_metadata={}
    for label,path in [('CONTROL',control),('BELA',candidate)]:
        row=queries.get(label)
        if row is None:lookups[label]=None;continue
        if not isinstance(row,dict):problems.append('Malformed '+label+' query');continue
        observed_path=row.get('holder_path')
        if not isinstance(observed_path,str) or observed_path.lower()!=path.lower() or row.get('arguments')!=[0,0,0]:
            problems.append(label+' query reference/arguments mismatch')
        if type(row.get('has_dynamic_motion')) is not bool:problems.append(label+' lookup result is not boolean')
        if row.get('attached_to_controller') is not False or row.get('pose_decoding_verified') is not False:
            problems.append('Standalone query overclaims '+label+' verification')
        lookups[label]=row.get('has_dynamic_motion')
        info=row.get('motion_info')
        if info is not None:
            if not isinstance(info,dict) or type(info.get('query_result')) is not bool or info.get('arguments')!=[0,0,0] or info.get('pose_decoding_verified') is not False:
                problems.append(label+' malformed MotionInfo evidence');continue
            data=info.get('info') or {}
            values=data.get('values') or {} if isinstance(data,dict) else {}
            if not isinstance(values,dict):problems.append(label+' malformed MotionInfo values');continue
            motion_metadata[label]=values
            if info['query_result']:
                if row.get('has_dynamic_motion') is not True:problems.append(label+' metadata contradicts lookup')
                if values.get('get_BankID')!=0 or values.get('get_MotionID')!=0:problems.append(label+' metadata IDs differ')
                end=values.get('get_MotionEndFrame')
                if type(end) not in (int,float) or end<0:problems.append(label+' invalid end frame')
                if label=='BELA' and (end!=300 or values.get('get_MotionName')!='Bela_Approved_Idle_Offline_300f_60fps'):
                    problems.append('BELA accepted name/duration differs')
    # The implemented harness has no decoder/sample or playback function.
    # A contradictory edited JSON cannot manufacture compatibility evidence.
    if any(document.get(k) is True for k in ('loaded','registered','playback_performed','native_XYZW_runtime_verified')):
        problems.append('Unsupported compatibility/activation claim for this harness revision')
    return {'status':'INVALID_CAPTURE' if problems else 'RUNTIME_ERRORS' if errors else 'PARTIAL_LOAD_EVIDENCE',
        'session':session,'phase':document.get('phase'),'validation_errors':problems,'runtime_errors':errors,
        'holder_path_matches':holders,'standalone_motion_lookup':lookups,'observed_phases':stages,
        'motion_metadata':motion_metadata,
        'candidate_catalog_verified':not problems and lookups.get('BELA') is True and
            motion_metadata.get('BELA',{}).get('get_MotionEndFrame')==300,
        'cleanup_callbacks_observed':'HOLDER_CLEANUP_CALLBACKS_OBSERVED' in stages,
        'holder_references_cleared':document.get('holder_references_cleared') is True,
        'heartbeat_frames':frames,'decoded_pose_verified':False,'playback_verified':False,
        'activation_ready':False,'gaps':['Engine track decoding and full XYZW not sampled',
            'Grace controller/render rig association and resume mechanism remain separate gates',
            'Normal process exit requires external evidence; heartbeat alone cannot prove it']}

def collect(session):
    if not re.fullmatch(r'[a-z0-9_]{8,64}',session):raise ValueError('Invalid session')
    game=Path(json.loads((ROOT/'config/project.json').read_text(encoding='utf-8'))['games']['re9'])
    folder=game/'reframework/data/bela_runtime_test'
    captures=sorted((p for p in folder.glob(session+'_*.json')
        if re.fullmatch(re.escape(session)+r'_\d+',p.stem)),key=lambda p:int(p.stem.rsplit('_',1)[1]))
    if not captures:raise ValueError('No diagnostic capture for session')
    target=ROOT/'build/animation_v0.2.0/runtime_experiment'/session
    rows=[];analyses=[]
    for p in [*captures,game/'re2_framework_log.txt']:
        if p.suffix=='.json':
            result=analyze(load_capture(p))
            if result['session']!=session:raise ValueError('Captured session differs')
            analyses.append(result)
        out=target/p.name;out.parent.mkdir(parents=True,exist_ok=True)
        if out.exists():
            if sha(out)!=sha(p):raise ValueError('Existing evidence differs; preserve and use a new session')
        else:
            with out.open('xb') as stream:stream.write(p.read_bytes())
        rows.append({'path':out.relative_to(ROOT).as_posix(),'sha256':sha(out),'bytes':out.stat().st_size})
    result={'session':session,'files':rows,'capture_count':len(captures),'last_capture':analyses[-1],
        'invalid_capture_count':sum(a['status']=='INVALID_CAPTURE' for a in analyses),
        'normal_exit_verified_by_collector':False,'provenance':'Live REFramework files; no simulation'}
    output=ROOT/'reports/runtime_experiment_v0.2.0'/(session+'_capture_analysis.json')
    if output.exists():raise ValueError('Analysis already exists; preserve it')
    write_json(output,result)
    return {'analysis':str(output),'captures':len(captures),'status':analyses[-1]['status']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--session',required=True)
    print(json.dumps(collect(parser.parse_args().session),indent=2))

