"""Summarize real saved observations and exact static name matches; never bind/play."""
import argparse
import json
from collections import Counter
from common import ROOT,write_json
from inspect_motion_metadata import inspect
from runtime_capture import load_capture,analyze
from source_animation_workflow import sha


def summarize(document):
    validation=analyze(document)
    if validation['status']=='INVALID_CAPTURE' or document.get('synthetic_fixture'):
        raise ValueError('Real valid capture required')
    nodes=Counter();frames={};fsm={};bank_ids=set();assets=set();target_types=set();selected=set();fsm_resources={}
    for sample in document.get('samples') or []:
        for watch in sample.get('watches') or []:
            selection=watch.get('selection') or {}
            selected.add((selection.get('name'),selection.get('joint_count'),(selection.get('object') or {}).get('address')))
            path=(watch.get('motion_bank_asset') or {}).get('resource_string')
            if path:assets.add(path)
            value=((watch.get('motion') or {}).get('observed') or {}).get('get_TargetBankType')
            if type(value) is int:target_types.add(value)
            for entry in watch.get('merged_motion_bank_ids') or []:
                value=entry.get('value')
                if type(value) is int and 0<=value<=0xffffffff:bank_ids.add(value)
            for layer in watch.get('layers') or []:
                lv=layer.get('observed') or {}
                for node in layer.get('nodes') or []:
                    nv=node.get('observed') or {}
                    key=(layer['index'],node['index'],nv.get('get_MotionName'),nv.get('get_MotionBankID'),nv.get('get_MotionID'),
                        nv.get('get_MotionBankType'),nv.get('get_MotionResourceDataId'),nv.get('get_MotionResourceDataLongId'),
                        lv.get('get_JointMaskID'),nv.get('get_MotionWrapMode'))
                    nodes[key]+=1;frames.setdefault(key,[]).append(nv.get('get_Frame'))
            for component in watch.get('components') or []:
                if (component.get('object') or {}).get('type')!='via.motion.MotionFsm2':continue
                for layer in component.get('layers') or []:
                    values=layer.get('observed') or {}
                    for kind in ('fsm_resource','behavior_tree_resource'):
                        path=(layer.get(kind) or {}).get('resource_string')
                        if path:fsm_resources.setdefault(layer['index'],set()).add(path)
                    if values.get('getCurrentNodeName') is not None:
                        key=(layer['index'],values.get('getCurrentNodeName'),values.get('getCurrentNodeID'),values.get('getCurrentNodeNameHash'),values.get('current_node_id_exact_integer'))
                        row=fsm.setdefault(key,{'samples':0,'phases':set()});row['samples']+=1;row['phases'].add(sample['marker'])
    return {'probe_version':document.get('probe_version'),'context':document.get('context'),
        'runtime_identity':document.get('runtime_identity'),'discovery':document.get('discovery'),
        'samples':len(document.get('samples') or []),'stop_reason':document.get('stop_reason'),
        'peak_sample_ms':document.get('peak_sample_ms'),'truncated':document.get('truncation'),
        'api_errors':document.get('api_errors') or [],'markers':document.get('markers') or [],
        'selected_components':[{'name':n,'controller_joint_count':c,'address':a} for n,c,a in sorted(selected)],
        'motion_bank_assets':sorted(assets),'merged_bank_ids':sorted(bank_ids),'target_bank_types':sorted(target_types),
        'observed_fsm_resources':[{'fsm_layer':i,'resource_strings':sorted(v)} for i,v in sorted(fsm_resources.items())],
        'motion_observations':[{'layer':k[0],'node':k[1],'name':k[2],'bank_id':k[3],'motion_id':k[4],
            'observed_node_bank_type':k[5],'resource_data_id':k[6],'resource_data_long_id':k[7],
            'layer_joint_mask':k[8],'node_wrap_mode':k[9],'samples':count,
            'frame_min':min(v for v in frames[k] if type(v) in (int,float)) if any(type(v) in (int,float) for v in frames[k]) else None,
            'frame_max':max(v for v in frames[k] if type(v) in (int,float)) if any(type(v) in (int,float) for v in frames[k]) else None}
            for k,count in nodes.items()],
        'fsm_states':[{'fsm_layer':k[0],'observed_node_name':k[1],'observed_node_id_decimal':k[2],
            'observed_name_hash':k[3],'id_integer_precision_preserved':k[4],'samples':row['samples'],'phases':sorted(row['phases'])} for k,row in fsm.items()],
        'analysis_state_changes':validation['observed_state_changes'],'missing_evidence':validation['missing_evidence'],
        'engine_full_quaternion_tested':False,'animation_activation_performed':False}


def static_matches(observations,resources):
    matches=[]
    for row in observations:
        for resource in resources:
            for clip in resource['motions']:
                if clip['name']!=row['name']:continue
                matching=[ix for ix in clip['index_entries'] if ix['motion_id']==row['motion_id']]
                if not matching:continue
                matches.append({'observed_name':row['name'],'observed_layer':row['layer'],
                    'observed_bank_id':row['bank_id'],'static_resource':resource['path'],'static_resource_sha256':resource['sha256'],
                    'static_list_name':resource.get('list_name'),'static_frames':clip['frame_count'],
                    'static_fps':clip['fps'],'static_bone_count':clip['skeleton_bone_count_header'],
                    'static_track_count':clip['bone_track_count_header'],'static_indices':matching,
                    'method':'Exact observed full motion name and motion ID match; file mapping corroborated offline',
                    'live_motlist_reference_exposed':False,'live_switch_observed':False})
    return matches


def match_fsm_state(state,resource_strings,controllers):
    """Require the observed resource, hierarchy, ID and hash; labels alone collide."""
    paths=set()
    for value in resource_strings:
        if isinstance(value,str) and value.startswith('Resource[') and value.endswith(']'):
            path=value[len('Resource['):-1].replace('\\','/').lower()
            if path.startswith('appsystem/') and path.endswith('.motfsm2') and '..' not in path.split('/'):
                paths.add(path)
    matches=[]
    for controller in controllers:
        path=controller['path'].replace('\\','/').lower()
        resource=path.split('/natives/stm/',1)[-1].removesuffix('.45')
        if resource not in paths:continue
        for node in controller['nodes']:
            hierarchy=node['hierarchy'].removeprefix('root/').replace('/','.')
            name_hash=(node.get('fsm') or {}).get('name_hash')
            if (hierarchy==state['observed_node_name'] and name_hash==state['observed_name_hash']
                and node['id'][1]==0 and str(node['id'][0])==state['observed_node_id_decimal']):
                matches.append({'controller':controller['path'],'hierarchy':node['hierarchy'],'id_pair':node['id'],
                    'resource_name_hierarchy_id_and_name_hash_equal':True,
                    'scope':'This observed state in this loaded controller; no transition condition, switch or MOTLIST binding inferred'})
    return matches


def main():
    parser=argparse.ArgumentParser();parser.add_argument('captures',nargs='+');args=parser.parse_args()
    reports=[]
    for name in args.captures:
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT/'build/animation_v0.2.0/runtime_hardening/captures'):raise ValueError('Use preserved workspace captures')
        row=summarize(load_capture(path));row.update({'capture':path.relative_to(ROOT).as_posix(),'sha256':sha(path)});reports.append(row)
    names={n['name'] for report in reports for n in report['motion_observations']}
    list_names={n.split('_',2)[1].lower() for n in names if n and n.startswith('ch0200_')}
    files=set()
    for folder in (ROOT/'assets/extracted/re9',ROOT/'build/animation_v0.2.0/runtime_hardening/live_sources'):
        files.update(p for p in folder.rglob('*.motlist.1047') if p.name.lower().split('.')[0].removeprefix('ch0200_') in list_names)
    resources=[inspect(p) for p in sorted(files)]
    for report in reports:report['static_clip_matches']=static_matches(report['motion_observations'],resources)
    graph=json.loads((ROOT/'build/animation_v0.2.0/runtime_hardening/controller_graphs.json').read_text(encoding='utf-8'))
    for report in reports:
        for state in report['fsm_states']:
            paths=[p for r in report['observed_fsm_resources'] if r['fsm_layer']==state['fsm_layer'] for p in r['resource_strings']]
            state['verified_static_state_matches']=match_fsm_state(state,paths,graph['controllers'])
            state['loaded_controller_and_current_state_corroborated']=len(state['verified_static_state_matches'])==1
    result={'status':'LIVE_GETTER_EVIDENCE_WITH_EXPLICIT_GAPS','captures':reports,
        'verified':'Actual scene, selected Grace component, bank asset, layers, motion names/IDs/frames, exposed numeric masks/types and current FSM getters where present',
        'inferred':'Exact named clip matches corroborate extracted MOTLIST candidates; static switch and bank masks remain static metadata',
        'remaining':['Repeat marked walk/aim sequence with v7 to retain all twelve blended nodes and indexed FSM states',
            'Live switch / MOTLIST reference not directly exposed by current getter route; v7 TPS controller resources and six current states are observed',
            '80-joint controller to 611-joint rendered skeleton / helper / IK association needs further live evidence',
            'Dynamic bank holder loading, ownership, single-cycle abort and cache lifetime unexercised',
            'Full XYZW runtime decoding remains untested; no converted animation was loaded'],
        'automation_limit':'Supported graphical tool has no sustained key/right-mouse hold. Short game-input taps were not reliably detected; no input injection or settings workaround used',
        'protected_scope':'No manual save, archive write, character asset update, experimental resource installation or runtime controller write'}
    write_json(ROOT/'reports/runtime_preparation_v0.2.0/live_binding_evidence.json',result)
    print(json.dumps({'captures':len(reports),'samples':sum(r['samples'] for r in reports),'fsm_states':sum(len(r['fsm_states']) for r in reports),'output':'reports/runtime_preparation_v0.2.0/live_binding_evidence.json'}))


if __name__=='__main__':main()

