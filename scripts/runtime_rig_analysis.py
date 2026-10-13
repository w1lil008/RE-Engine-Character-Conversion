"""Validate explicit live constraint references; never infer all-joint binding."""
import argparse,json
from pathlib import Path
import numpy as np
from common import write_json
from runtime_capture import load_capture
from source_animation_workflow import sha


def analyze_rig(document):
    if document.get('schema')!='bela-rig-evidence-v1' or document.get('read_only') is not True:
        raise ValueError('Wrong rig evidence schema')
    objects=document.get('objects') or []
    controllers=[o for o in objects if o['name']=='cp_A100' and o['motion_values'].get('get_JointCount')==80]
    if len(controllers)!=1:raise ValueError('Unique Grace controller is required')
    cp=controllers[0];joints={j['requested_name']:j for j in cp['joints']}
    rows=[]
    for body in [o for o in objects if o['name'] in ('40','20')]:
        if body['motion_values'].get('get_JointCount')!=611:raise ValueError('Renderer joint count differs')
        row={'name':body['name'],'game_object':body['game_object'],'verified_constraints':[],'unavailable_joints':[],
             'maximum_world_position_difference_m':0.,'maximum_world_quaternion_component_difference':0.}
        if len(body['ancestry'])<2 or body['ancestry'][1]['game_object']!=cp['game_object']:
            raise ValueError('Renderer does not have the observed controller parent')
        for joint in body['joints']:
            name=joint['requested_name'];target=joints.get(name)
            if not target or target['object'].get('unavailable') or joint['object'].get('unavailable'):
                row['unavailable_joints'].append(name);continue
            if joint['constraint']!=target['object'] or joint['constraint_owner']!=cp['transform']:
                raise ValueError('Constraint reference differs: '+name)
            if joint['values'].get('get_Constrainted') is not True:raise ValueError('Constraint not active: '+name)
            for getter,axes,metric in [('get_Position','xyz','maximum_world_position_difference_m'),
                                      ('get_Rotation','xyzw','maximum_world_quaternion_component_difference')]:
                a=np.asarray([joint['values'][getter][axis] for axis in axes]);b=np.asarray([target['values'][getter][axis] for axis in axes])
                if not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('Nonfinite world pose')
                distance=float(np.linalg.norm(a-b)) if axes=='xyz' else float(min(np.max(abs(a-b)),np.max(abs(a+b))))
                row[metric]=max(row[metric],distance)
            row['verified_constraints'].append(name)
        rows.append(row)
    if len(rows)!=2:raise ValueError('Both visible renderer objects are required')
    return {'schema':'bela-rig-association-v1','session':document['session'],'controller':cp['game_object'],
        'joint_map':cp['joint_map'],'renderers':rows,'runtime_errors':document.get('errors') or [],
        'all_611_joint_mapping_verified':False,'playback_verified':False,
        'interpretation':'Explicit active constraints link sampled renderer joints to the exact cp_A100 joints. Renderer local getters remain bind values; world values reflect the constrained pose.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('capture');parser.add_argument('--output',required=True);args=parser.parse_args()
    result=analyze_rig(load_capture(args.capture));result['capture_sha256']=sha(Path(args.capture))
    if Path(args.output).exists():raise ValueError('Preserve existing rig analysis')
    write_json(args.output,result);print(json.dumps(result,indent=2))

