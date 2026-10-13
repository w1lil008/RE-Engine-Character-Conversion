"""Measure a preliminary body mapping; does not retarget or write animations."""
import json
import numpy as np
from common import ROOT,write_json
from analyze_assets import parsed_mesh
from build_meshes import find_mesh,merge_skeleton
from animation_math import compose,hierarchy_globals,decompose,quaternion_matrix

config=json.loads((ROOT/'config/source_idle_v0.2.0.json').read_text());d=json.loads((ROOT/config['output']/'decoded_reference.json').read_text())
settings=json.loads((ROOT/'config/prototype.json').read_text())
target=merge_skeleton([parsed_mesh(find_mesh('re9',n))[1] for n in settings['target_rig_parts']])
assert len(target.boneList)==611
t={b.boneName:b for b in target.boneList};s={b['name']:b for b in d['bones']};names=list(s)
source_globals=hierarchy_globals([compose(b['translation'],b['quaternion_xyzw']) for b in d['bones']],
    [names.index(b['parent']) if b['parent'] else -1 for b in d['bones']])
mapping={n:n for n in ['root','Hip','Spine_0','Spine_1','Spine_2','Neck_0','Neck_1']};mapping['Head']='Head_0'
for side in ['L','R']:
    for a,b in [('Shoulder','Arm_Clavicle'),('UpperArm','Arm_Upper'),('Forearm','Arm_Lower'),('Hand','Arm_Hand'),
                ('Thigh','Leg_Upper'),('Shin','Leg_Lower'),('Foot','Leg_Foot'),('Toe','Leg_Toes')]:mapping[f'{side}_{a}']=f'{side}_{b}'
rows=[]
for source,dest in mapping.items():
    if source not in s or dest not in t:raise ValueError(f'Missing planned body correspondence: {source} to {dest}')
    sb=s[source];tb=t[dest];target_world=np.array(tb.worldMatrix.matrix).T;target_local=np.array(tb.localMatrix.matrix).T
    rows.append({'source':source,'target':dest,'source_parent':sb['parent'],'target_parent':target.boneList[tb.parentIndex].boneName if tb.parentIndex>=0 else None,
        'source_MOT_rest_local_translation_m':sb['translation'],'source_MOT_rest_local_quaternion_xyzw':sb['quaternion_xyzw'],
        'target_bind_local_translation_m':target_local[:3,3].tolist(),'target_bind_local_quaternion_xyzw':decompose(target_local)[1].tolist(),
        'source_world_rest_axes_columns':source_globals[names.index(source)][:3,:3].tolist(),
        'target_world_bind_axes_columns':quaternion_matrix(decompose(target_world)[1]).tolist(),
        'policy':'Retarget reviewed body rotations through calibrated bases; preserve target local offsets. Name pairing is not a validated animation transform.'})
write_json(ROOT/'reports/animation_dev/source_to_grace_mapping_plan.json',{'status':'PRELIMINARY_CORRESPONDENCE_MEASURED_NO_RETARGET_IMPLEMENTED',
    'target_bones':611,'reviewed_core_correspondences':rows,'source_helpers':['Null_Offset','R_Foot_Offset','L_Foot_Offset','R_Hand_Offset','L_Hand_Offset'],
    'helper_policy':'Compose root and Null_Offset transforms before target root mapping. Preserve four native offset tracks in source; identify IK meanings before using them on Grace.',
    'finger_weapon_policy':'Keep Grace finger, weapon attachment, recoil, aim, reload and IK layers; do not copy the source clenched fist onto live weapon controls.',
    'unmapped_tracks':[t['bone'] for t in d['tracks'] if t['bone'] not in mapping],
    'unresolved':['Basis calibration for differing local bone rolls','Muscle/twist distribution','Source skirt tracks versus retained Grace skirt/cloth contract',
        'Target layer masks and live controller binding','In-place root with pelvis sway and verified foot contacts'],
    'basis_validation_gate':'Rest reconstruction first; zero delta must preserve target bind exactly. Test one known-axis rotation and limb length before an actual offline retarget.',
    'native_RE9_animation_outputs_written':False})
print(f'Measured {len(rows)} explicit core body correspondences against unchanged Grace 611-bone bind')

