"""Strict live-probe JSON analysis. Never approves or performs runtime activation."""
import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from common import ROOT, confined, write_json
from runtime_stage1 import FRAMEWORK_COMMIT

MAX_BYTES = 64 * 1024 * 1024


def uint(value): return type(value) is int and 0 <= value <= 0xffffffff
def number(value): return type(value) in (int, float) and math.isfinite(value)


def resource_path(value):
    if not isinstance(value, str) or len(value) > 1024: return None
    matches = re.findall(r'([A-Za-z0-9_./\\-]+\.motlist)(?:\.1047)?(?![A-Za-z0-9_.])', value)
    if len(matches) != 1: return None
    path = matches[0].replace('\\', '/').lower()
    if path.startswith('/') or '..' in path.split('/'): return None
    if 'animation/' not in path: return None
    return path[path.index('animation/'):]


def analyze(document, static=None):
    errors, warnings, gaps = [], [], []
    def error(path, message):
        if len(errors) < 200: errors.append({'path': path, 'message': message})
    def array(value, path, cap):
        if value is None: return []  # REFramework serializes an empty Lua table as null.
        if not isinstance(value, list): error(path, 'Expected array or SDK empty-table null'); return []
        if len(value) > cap: error(path, 'Capture exceeds bounded schema limit'); return value[:cap]
        return value
    def obj(value, path, required=True):
        if value is None and not required: return {}
        if not isinstance(value, dict): error(path, 'Expected object'); return {}
        return value
    def observed(value, path):
        out = obj(value, path, False)
        for k, v in out.items():
            if not isinstance(k, str): error(path, 'Invalid getter name')
            if isinstance(v, float) and not math.isfinite(v): error(path + '.' + k, 'Nonfinite value')
            if k in ('get_MotionBankID','get_BankID','get_MotionID','get_Switch','get_SwitchValue','get_BankType','get_BankTypeMask','get_JointMaskID'):
                if not uint(v): error(path + '.' + k, 'Identifier must be an unsigned integer, not a reference or boolean')
        return out
    def pick(values, keys):
        return next((values[k] for k in keys if k in values and uint(values[k])), None)
    def paths(value, path, depth=0):
        found = []
        if depth > 5: error(path, 'Resource reference nesting exceeds schema'); return found
        if isinstance(value, dict):
            for k, v in value.items():
                if k == 'resource_string':
                    normalized = resource_path(v)
                    if normalized: found.append(normalized)
                    elif isinstance(v, str) and 'motlist' in v.lower(): error(path, 'Malformed MOTLIST reference')
                elif isinstance(v, (dict, list)): found += paths(v, path + '.' + str(k), depth+1)
        elif isinstance(value, list):
            for v in value[:128]: found += paths(v, path, depth+1)
        return sorted(set(found))
    if not isinstance(document, dict): return {'status': 'INVALID_CAPTURE', 'errors': [{'path':'$','message':'Expected object'}], 'activation_ready':False}
    if document.get('schema') not in ('bela-runtime-binding-v1','bela-runtime-binding-v2'): error('schema','Unsupported probe schema')
    if document.get('read_only') is not True: error('read_only','Read-only provenance absent')
    runtime = obj(document.get('runtime_identity'), 'runtime_identity')
    if runtime.get('game') != 're9' or runtime.get('tdb_version') != 83 or runtime.get('reframework_commit') != FRAMEWORK_COMMIT:
        gaps.append('Live game/framework/TDB does not match pinned target')
    if document.get('synthetic_fixture'): gaps.append('Synthetic mock data cannot verify runtime binding')
    if document.get('grace_identity_user_confirmed') is not True: gaps.append('Grace object identity requires user confirmation')
    context = document.get('context')
    if not isinstance(context, str) or not context.strip() or context.startswith('Enter room'):
        gaps.append('Scene, camera and weapon context missing')
    if document.get('truncation') is True or document.get('errors_truncated') is True: gaps.append('Capture truncated; reduce watched objects or sampling scope')
    api_errors = array(document.get('api_errors'), 'api_errors', 100)
    for i,entry in enumerate(api_errors):
        entry=obj(entry,f'api_errors[{i}]')
        if not isinstance(entry.get('probe',entry.get('error')),str):error(f'api_errors[{i}]','Missing error text')
    if api_errors: gaps.append('Runtime API failures recorded; inspect before relying on missing values')
    for i, marker in enumerate(array(document.get('markers'), 'markers', 256)):
        marker = obj(marker, f'markers[{i}]')
        if not isinstance(marker.get('label'), str): error(f'markers[{i}]','Missing label')
        if not number(marker.get('elapsed_clock')) or marker.get('elapsed_clock',0) < 0: error(f'markers[{i}]','Invalid clock')
        if type(marker.get('sample_index')) is not int or marker.get('sample_index',-1) < 0: error(f'markers[{i}]','Invalid sample index')
    catalog=array(document.get('api_catalog'),'api_catalog',160)
    reflected_integration=[]
    for ci, entry in enumerate(catalog):
        cp=f'api_catalog[{ci}]';entry=obj(entry,cp)
        if not isinstance(entry.get('type'),str):error(cp,'Missing reflected type')
        for method in array(entry.get('integration_method_candidates'),cp+'.integration_method_candidates',100):
            method=obj(method,cp+'.method');params=array(method.get('parameters'),cp+'.parameters',20)
            if not isinstance(method.get('name'),str) or type(method.get('count')) is not int or method.get('count')!=len(params):
                error(cp,'Malformed method signature')
            elif not all(isinstance(v,str) for v in params) or type(method.get('static')) is not bool:
                error(cp,'Malformed signature type/static information')
            else:reflected_integration.append({'type':entry.get('type'),**method,'observed_call_success':False})
    rows, missing, unknown_banks = [], defaultdict(int), set(); last_time = -1
    component_inventory={};component_latest={};component_changes=[]
    samples = array(document.get('samples'), 'samples', 600)
    if not samples: gaps.append('No samples captured')
    for si, sample in enumerate(samples):
        sp = f'samples[{si}]'; sample = obj(sample, sp)
        t = sample.get('elapsed_clock'); phase = sample.get('marker')
        if not number(t) or t < last_time or t < 0: error(sp,'Invalid or decreasing elapsed clock'); continue
        last_time = t
        if not isinstance(phase, str) or len(phase) > 100: error(sp,'Missing/invalid action label'); phase = 'unlabelled'
        for wi, watch in enumerate(array(sample.get('watches'), sp+'.watches', 4)):
            wp = sp+f'.watches[{wi}]'; watch = obj(watch, wp)
            selection = obj(watch.get('selection'), wp+'.selection')
            identity = obj(selection.get('object'), wp+'.selection.object')
            address = identity.get('address'); role = watch.get('role')
            if not isinstance(address,str) or address in ('','unavailable'): error(wp,'Missing stable object address'); continue
            if role not in ('body','fps_arms','other','unconfirmed'): error(wp,'Unknown watch role'); continue
            observed(obj(watch.get('motion'),wp+'.motion',False).get('observed'),wp+'.motion.observed')
            for ci,component in enumerate(array(watch.get('components'),wp+'.components',48)):
                cp=wp+f'.components[{ci}]';component=obj(component,cp)
                descriptor=obj(component.get('object'),cp+'.object',False)
                ct=descriptor.get('type');ca=descriptor.get('address')
                values=observed(component.get('observed'),cp+'.observed')
                for layer in array(component.get('layers'),cp+'.layers',16):
                    layer=obj(layer,cp+'.layer');index=layer.get('index')
                    if not uint(index):error(cp,'Invalid component layer index')
                    for key,val in observed(layer.get('observed'),cp+'.layer.observed').items():
                        values={**values,f'layer[{index}]:{key}':val}
                if isinstance(ct,str) and isinstance(ca,str):
                    key=(address,ct,ca);inventory=component_inventory.setdefault(key,{'watch_object':address,'component_type':ct,'component_address':ca,'observed_fields':set()})
                    inventory['observed_fields'].update(values)
                    relevant={k:v for k,v in values.items() if any(h in k.lower() for h in ('state','currentnode','ik','weapon','attach','mask'))}
                    previous=component_latest.get(key)
                    if previous is not None and previous!=relevant:
                        if len(component_changes)<1000:
                            component_changes.append({'sample':si,'phase':phase,'component_type':ct,'component_address':ca,'before':previous,'after':relevant})
                        else: warnings.append('Component change output capped at 1000 entries') if 'Component change output capped at 1000 entries' not in warnings else None
                    component_latest[key]=relevant
            bank_lookup = defaultdict(list)
            for bi, bank in enumerate(array(watch.get('banks'),wp+'.banks',256)):
                bp=wp+f'.banks[{bi}]'; bank=obj(bank,bp); values=observed(bank.get('observed'),bp+'.observed')
                bank_id=pick(values,('get_BankID','get_MotionBankID')); refs=paths(bank,bp)
                if bank_id is not None:
                    bank_lookup[bank_id].append({'paths':refs,'bank_type':pick(values,('get_BankType',)),
                        'type_mask':pick(values,('get_BankTypeMask',))})
            seen_layers=set()
            for li, layer in enumerate(array(watch.get('layers'),wp+'.layers',16)):
                lp=wp+f'.layers[{li}]'; layer=obj(layer,lp); layer_index=layer.get('index')
                if not uint(layer_index) or layer_index in seen_layers: error(lp,'Invalid or duplicate layer index'); continue
                seen_layers.add(layer_index); lv=observed(layer.get('observed'),lp+'.observed')
                nodes=array(layer.get('nodes'),lp+'.nodes',16)
                if not nodes: missing['layers_without_nodes']+=1
                seen_nodes=set()
                for ni,node in enumerate(nodes):
                    np=lp+f'.nodes[{ni}]'; node=obj(node,np); node_index=node.get('index')
                    if not uint(node_index) or node_index in seen_nodes: error(np,'Invalid or duplicate node index'); continue
                    seen_nodes.add(node_index); nv=observed(node.get('observed'),np+'.observed')
                    values=dict(lv); values.update(nv)
                    bank_id=pick(values,('get_MotionBankID','get_BankID')); motion=pick(values,('get_MotionID',))
                    switch=pick(values,('get_SwitchValue','get_Switch')); mask=pick(values,('get_JointMaskID','get_JointMask'))
                    frame=values.get('get_Frame'); end_frame=values.get('get_EndFrame')
                    if frame is not None and not number(frame): error(np,'Invalid playback frame'); frame=None
                    if end_frame is not None and (not number(end_frame) or end_frame<0): error(np,'Invalid end frame'); end_frame=None
                    candidates=bank_lookup.get(bank_id,[])
                    # Exact exposed type/mask equality only; no guessed bit-mask dispatch rule.
                    node_type=pick(values,('get_MotionBankType','get_BankType'));node_type_mask=pick(values,('get_BankTypeMask',))
                    if node_type is not None and node_type_mask is not None:
                        candidates=[b for b in candidates if b['bank_type']==node_type and b['type_mask']==node_type_mask]
                    unique={(p, b['bank_type'],b['type_mask']) for b in candidates for p in b['paths']}
                    binding=next(iter(unique)) if len(unique)==1 else (None,None,None)
                    if bank_id is not None and not candidates: unknown_banks.add((address,bank_id))
                    for key,value in (('bank_id',bank_id),('motion_id',motion),('switch',switch),('joint_mask',mask),('resource',binding[0]),('frame',frame)):
                        if value is None: missing[key]+=1
                    rows.append(dict(sample=si,time=t,phase=phase,object=address,role=role,layer=layer_index,node=node_index,
                        bank_id=bank_id,motion_id=motion,switch=switch,joint_mask=mask,frame=frame,end_frame=end_frame,
                        resource=binding[0],bank_type=binding[1],type_mask=binding[2],ambiguous_bank=len(unique)>1,
                        state={k:v for k,v in lv.items() if 'state' in k.lower() or 'currentnode' in k.lower()},
                        weight=values.get('get_Weight'),play_state=values.get('get_PlayState'),
                        observed_bank_type=node_type,motion_name=values.get('get_MotionName'),
                        resource_data_id=values.get('get_MotionResourceDataId'),resource_data_long_id=values.get('get_MotionResourceDataLongId'),
                        motion_attribute=values.get('get_MotionAttribute'),wrap_mode=values.get('get_MotionWrapMode',values.get('get_WrapMode'))))
    grouped=defaultdict(list)
    for row in rows: grouped[(row['object'],row['role'],row['layer'],row['node'])].append(row)
    changes, wraps, candidates = [],[],[]
    # Weapon context can select a different resource for the same bank/motion ID.
    keys=('bank_id','motion_id','switch','joint_mask','state','resource','motion_name','observed_bank_type','resource_data_id','resource_data_long_id','wrap_mode')
    for identity, stream in grouped.items():
        for previous,current in zip(stream,stream[1:]):
            fields=[k for k in keys if current[k]!=previous[k]]
            if fields: changes.append(dict(object=identity[0],role=identity[1],layer=identity[2],node=identity[3],
                sample=current['sample'],from_phase=previous['phase'],to_phase=current['phase'],changed_fields=fields,
                before={k:previous[k] for k in keys},after={k:current[k] for k in keys}))
            elif number(previous['frame']) and number(current['frame']) and current['frame']<previous['frame']:
                wraps.append(dict(object=identity[0],layer=identity[2],node=identity[3],sample=current['sample'],
                    before_frame=previous['frame'],after_frame=current['frame'],end_frame=current['end_frame'],
                    interpretation='Possible loop or restart; wrap-mode/live state needed'))
        idle=defaultdict(list)
        for row in stream:
            if row['role']=='body' and row['phase'] in ('idle','idle_after_walk','idle_after_aim'):
                idle[(row['resource'],row['bank_id'],row['bank_type'],row['type_mask'],row['motion_id'],row['switch'],row['joint_mask'])].append(row)
        for binding, observations in idle.items():
            phases=sorted({r['phase'] for r in observations}); frames={r['frame'] for r in observations if number(r['frame']) and r['frame']>=0}
            complete=all(v is not None for v in binding)
            action_changes=[ch for ch in changes if ch['object']==identity[0] and ch['layer']==identity[2] and ch['node']==identity[3]
                and ch['to_phase'] in ('walk','aim','idle_after_walk','idle_after_aim')]
            if len(observations)>=2:
                matches=[]
                for clip in (static or {}).get('idle_candidates',[]):
                    if resource_path(clip['resource'])==binding[0] and any(ix['motion_id']==binding[4] and ix['switch']==binding[5] for ix in clip['indices']):
                        matches.append(clip['name'])
                candidates.append(dict(object=identity[0],layer=identity[2],node=identity[3],
                    resource=binding[0],bank_id=binding[1],bank_type=binding[2],type_mask=binding[3],motion_id=binding[4],switch=binding[5],joint_mask=binding[6],
                    phases=phases,frames_advance=len(frames)>1,observations=len(observations),static_label_matches=matches,
                    binding_tuple_complete=complete,action_change_count=len(action_changes),
                    observed_bank_types=sorted({r['observed_bank_type'] for r in observations if uint(r['observed_bank_type'])}),
                    motion_names=sorted({r['motion_name'] for r in observations if isinstance(r['motion_name'],str)}),
                    resource_data_ids=sorted({r['resource_data_id'] for r in observations if uint(r['resource_data_id'])}),
                    resource_data_long_ids=sorted({r['resource_data_long_id'] for r in observations if type(r['resource_data_long_id']) is int}),
                    wrap_modes=sorted({r['wrap_mode'] for r in observations if type(r['wrap_mode']) is int}),
                    review_candidate=complete and len(frames)>1 and len(phases)==3 and len(action_changes)>=4))
    if not candidates: gaps.append('No repeated body idle candidate captured')
    if candidates and not any(c['review_candidate'] for c in candidates): gaps.append('Idle evidence lacks complete binding tuple, playback, or marked walk/aim returns')
    if unknown_banks: warnings.append('Node bank IDs have no corresponding enumerated MOTLIST; no static substitution inferred')
    if any(r['ambiguous_bank'] for r in rows): gaps.append('Same bank ID resolves to multiple type/path entries; active bank selection unresolved')
    if not any(r['role']=='fps_arms' for r in rows): warnings.append('FPS arms not observed; TPS/FPS equivalence remains unverified')
    return dict(status='INVALID_CAPTURE' if errors else 'EVIDENCE_READY_FOR_REVIEW' if not gaps else 'INCOMPLETE_EVIDENCE',
        errors=errors,warnings=warnings,missing_evidence=gaps,missing_fields=dict(missing),sample_count=len(samples),node_observations=len(rows),
        observed_state_changes=changes,possible_loop_wraps=wraps,idle_candidates=candidates,
        component_inventory=[{**v,'observed_fields':sorted(v['observed_fields'])} for v in component_inventory.values()],
        component_state_helper_changes=component_changes,reflected_integration_signatures=reflected_integration,
        unknown_banks=[{'object':a,'bank_id':b} for a,b in sorted(unknown_banks)],
        runtime_binding_verified=False,activation_ready=False,
        scope='Sampled read-only getter observations. Review candidates are not runtime playback authorization.',
        unobserved='Actual frame-by-frame FSM events, effect of layers/IK, resource loader and engine quaternion decoding')


def load_capture(path):
    if Path(path).stat().st_size>MAX_BYTES: raise ValueError('Capture exceeds 64 MiB limit')
    def pairs(values):
        out={}
        for key,value in values:
            if key in out: raise ValueError('Duplicate JSON key: '+key)
            out[key]=value
        return out
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=pairs,
        parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON token: '+v)))


def main():
    p=argparse.ArgumentParser(); p.add_argument('capture'); p.add_argument('--output',required=True); args=p.parse_args()
    output=confined(ROOT,args.output)
    if not output.is_relative_to(ROOT/'reports/runtime_preparation_v0.2.0/captures') or output.exists():
        raise ValueError('Choose a fresh reports/runtime_preparation_v0.2.0/captures/*.json output')
    static=json.loads((ROOT/'reports/native_animation_v0.2.0/binding_analysis.json').read_text(encoding='utf-8'))
    result=analyze(load_capture(args.capture),static); write_json(output,result)
    print(json.dumps({k:result[k] for k in ('status','sample_count','activation_ready') if k in result}))


if __name__=='__main__': main()

