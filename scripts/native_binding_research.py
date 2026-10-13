"""Read-only controller extraction and bounded version-45 transition inventory.

This cannot establish live state binding; it records the boundary explicitly.
"""
import collections
import json
from pathlib import Path
from common import ROOT, write_json
from extract_assets import official_paks, build_lookup, extract
from inspect_motion_metadata import inspect
from native_mot import read, wstring

OUTPUT=ROOT/'build/animation_v0.2.0/native_binding'

def parse_controller(path):
    data=path.read_bytes();version,magic=read(data,'<II',0)
    if (version,magic)!=(45,0x3273666d):raise ValueError('Unsupported controller header')
    tree,map_offset,data_offset,unknown,info=read(data,'<5Q',16)
    maps,count,start=read(data,'<3i',56)
    if min(maps,count)<0 or max(maps,count)>100000:raise ValueError('Implausible controller count')
    entries=[read(data,'<Ii',map_offset+i*8) for i in range(maps)]
    if any(index<0 or index>=count for id_,index in entries):raise ValueError('Bad transition reference')
    transitions=[]
    for i in range(count):
        id_,flags,exit_,rsz,start_,interpolation,speed,timeout,layer,mask,zero=read(data,'<IIfI4fHHI',data_offset+i*40)
        transitions.append({'id':id_,'flags':flags,'exit_frame':exit_,'rsz_or_unknown_id':rsz,
            'start_frame':start_,'interpolation_frames':interpolation,'continuation_speed':speed,
            'continuation_timeout':timeout,'continuation_layer':layer,'continuation_joint_mask':mask,
            'continuation_flag':bool((flags>>18)&1),'padding_bits':zero})
    return {'path':path.relative_to(ROOT).as_posix(),'version':version,'bytes':len(data),'tree_offset':tree,
        'unknown_offset':unknown,'tree_info_offset':info,'start_transition_index':start,
        'transition_map':entries,'transition_data':transitions,
        'scope':'Header, transition references, flags, timing, continuation layers/masks decoded. BHVT node actions and RSZ motion bindings not decoded; no live state observed.'}

def main():
    project=json.loads((ROOT/'config/project.json').read_text())
    candidates=json.loads((ROOT/'reports/animation_research/re9_controller_candidates.json').read_text())['candidates']
    wanted=[p for p in candidates if '.motfsm2.' in p]
    if OUTPUT.exists():raise ValueError('Preserve extracted controller evidence; choose a new research output before rerunning')
    OUTPUT.mkdir(parents=True)
    matches,archives=build_lookup(official_paks(Path(project['games']['re9'])),wanted)
    records=extract(matches,OUTPUT/'extracted')
    controllers=[parse_controller(OUTPUT/'extracted'/r['path']) for r in records]
    banks=[inspect(p) for p in sorted((ROOT/'assets/extracted/re9').rglob('*.motbank.4'))]
    lists=[inspect(p) for p in sorted((ROOT/'assets/extracted/re9/natives/stm/animation/ch/ch02/ch0200/motlist').glob('*.motlist.1047'))]
    report={'status':'PARTIAL_STATIC_BINDING_RESEARCH_COMPLETE','requested_controllers':len(wanted),'extracted_controllers':len(records),
        'missing':sorted(set(wanted)-set(matches)),'extraction':records,'original_archives_read_only':archives,
        'controllers':controllers,'banks':banks,
        'idle_candidates':[{'resource':r['path'],'name':m['name'],'offset':m['offset'],'frames':m['frame_count'],'indices':m['index_entries']}
            for r in lists for m in r['motions'] if 'idle' in str(m['name']).lower()],
        'actual_runtime_state_binding_verified':False,'game_or_controller_writes':0,
        'remaining_dependencies':['BHVT/RSZ node-action decoding with the matching RE9 type schema',
            'Read-only live Grace layer, bank type/mask, bank ID, motion ID, switch and joint-mask capture in the intended test state',
            'Resolve native joint-map resource, mask content, event/IK requirements and runtime acceptance of full XYZW rotation tracks']}
    write_json(ROOT/'reports/native_animation_v0.2.0/binding_analysis.json',report)
    print(f'Read-only research: {len(records)} controllers extracted, {sum(len(c["transition_data"]) for c in controllers)} transitions; live state binding remains unverified')

if __name__=='__main__':main()

