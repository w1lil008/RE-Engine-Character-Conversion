"""Compare engine-returned local channels with protected offline decodes.

Sampling a MotionInfo does not establish live layer/joint-map or visible playback.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from common import ROOT,write_json
from native_mot import decode_float_mot
from animation_math import sample,unit_quaternion
from runtime_capture import load_capture
from runtime_experiment import sample_plan
from source_animation_workflow import sha


def compare(document):
    plan=sample_plan();evidence=document.get('samples') or {}
    if evidence.get('schema')!='bela-engine-samples-v1' or evidence.get('plan')!=plan:
        raise ValueError('Sampling plan differs from protected inputs')
    original=json.loads((ROOT/'build/animation_v0.2.0/native_idle_canonical/original_grace_idle.json').read_text())
    native=decode_float_mot((ROOT/'build/animation_v0.2.0/native_idle_canonical/native/bela_idle.mot.983').read_bytes())
    observed=evidence.get('arms') or []
    if len(observed)!=2:raise ValueError('Both engine sampling arms are required')
    result={}
    for arm,actual,motion in zip(plan['arms'],observed,[original,native]):
        if actual.get('label')!=arm['label']:raise ValueError('Sampling order differs')
        tracks={t['hash']:t for t in motion['tracks']}
        expected={(t['hash'],f) for t in arm['tracks'] for f in arm['frames']}
        seen=set();errors={};norm_error=0
        for row in actual.get('rows',[]):
            key=(row.get('hash'),row.get('frame'))
            if key not in expected or key in seen:raise ValueError('Unknown, duplicate or missing-timing engine row')
            seen.add(key);track=tracks[key[0]]
            totals=errors.setdefault(track['bone'],{'maximum_position_error_m':0.,'maximum_rotation_error_deg':0.,'maximum_scale_error':0.})
            for channel,field in [('translation','position'),('rotation','rotation'),('scale','scale')]:
                valid=bool(track.get(channel))
                if type(row.get('valid_'+field)) is not bool or row['valid_'+field]!=valid:
                    raise ValueError('Channel validity differs from protected decode')
                if not valid:
                    if field in row:raise ValueError('Data present for invalid channel')
                    continue
                value=np.asarray(row.get(field),dtype=float)
                width=4 if channel=='rotation' else 3
                if value.shape!=(width,) or not np.isfinite(value).all():raise ValueError('Invalid decoded vector')
                reference=sample(track[channel],key[1],channel=='rotation')
                if channel=='rotation':
                    norm_error=max(norm_error,abs(float(np.linalg.norm(value))-1))
                    error=float(np.rad2deg(2*np.arccos(np.clip(abs(np.dot(unit_quaternion(value),reference)),0,1))))
                    metric='maximum_rotation_error_deg'
                else:
                    error=float(np.linalg.norm(value-reference));metric='maximum_position_error_m' if channel=='translation' else 'maximum_scale_error'
                totals[metric]=max(totals[metric],error)
        if seen!=expected:raise ValueError('Incomplete engine sampling: '+arm['label'])
        result[arm['label']]={'samples':len(seen),'tracks':len(tracks),'quaternion_norm_error':norm_error,
            'bones':errors,**{k:max(v[k] for v in errors.values()) for k in next(iter(errors.values()))}}
    bela=result['BELA'];control=result['CONTROL']
    passed=not document.get('errors') and control['maximum_rotation_error_deg']<=.05 and control['maximum_position_error_m']<=1e-4
    passed=passed and bela['maximum_rotation_error_deg']<=.001 and bela['maximum_position_error_m']<=1e-6 and bela['quaternion_norm_error']<=1e-4
    return {'schema':'bela-engine-sample-comparison-v1','session':document['session'],'engine_channel_comparison_passed':passed,
        'native_sha256':plan['native_sha256'],'arms':result,
        'full_XYZW_tracks':{name:bela['bones'][name] for name in ('R_Arm_Clavicle','L_Leg_Upper')},
        'tolerances':{'control_rotation_deg':.05,'control_position_m':1e-4,'candidate_rotation_deg':.001,'candidate_position_m':1e-6,'quaternion_norm':1e-4},
        'scene_pose_modified':False,'playback_verified':False,
        'scope':'Actual engine channel samples; hierarchy, procedural layers and visible playback require separate checks'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('capture');parser.add_argument('--output',required=True);args=parser.parse_args()
    result=compare(load_capture(args.capture));result['capture_sha256']=sha(Path(args.capture))
    output=Path(args.output)
    if output.exists():raise ValueError('Preserve existing sample comparison')
    write_json(output,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('arms','full_XYZW_tracks')},indent=2))

