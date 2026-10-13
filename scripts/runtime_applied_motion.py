"""Compare live layer rotations at their actual engine frame with the native clip.

Layer positions are reported separately: engine root extraction/composition is
not the raw MotionInfo channel. This tool does not certify final mesh deformation.
"""
import argparse, json
from pathlib import Path
import numpy as np
from animation_math import sample, unit_quaternion
from common import ROOT, write_json
from native_mot import decode_float_mot
from runtime_capture import load_capture
from runtime_one_cycle import analyze
from source_animation_workflow import sha


def compare(document):
    evidence = analyze(document)
    if evidence['status'] != 'PASSED' or evidence['mode'] != 'one_cycle':
        raise ValueError('Complete, validated visible cycle required')
    native = ROOT/'build/animation_v0.2.0/native_idle_canonical/native/bela_idle.mot.983'
    motion = decode_float_mot(native.read_bytes())
    tracks = {track['bone']: track for track in motion['tracks']}
    maximum = {name: 0. for name in tracks}
    roots = []
    count = 0
    for pose in document['poses']:
        if pose['phase'] != 'PLAYBACK_ONE_CYCLE':
            continue
        frame = pose['layer']['frame']
        for joint in pose['joints']:
            track = tracks[joint['name']]
            reference = sample(track['rotation'], frame, True)
            live = unit_quaternion(joint['rotation'])
            angle = float(np.rad2deg(2*np.arccos(np.clip(abs(np.dot(reference, live)), 0, 1))))
            maximum[joint['name']] = max(maximum[joint['name']], angle)
            if joint['name'] == 'root':
                roots.append(joint['position'])
        count += 1
    root = np.asarray(roots)
    native_root = sample(tracks['root']['translation'], 0, False)
    error = max(maximum.values())
    return {
        'schema': 'bela-applied-motion-comparison-v1', 'session': document['session'],
        'live_rotation_comparison_passed': error <= .001,
        'rotation_tolerance_deg': .001, 'sampled_poses': count, 'rotation_tracks': len(maximum),
        'maximum_rotation_error_deg': error, 'per_joint_rotation_error_deg': maximum,
        'full_XYZW_rotation_error_deg': {name: maximum[name] for name in ('R_Arm_Clavicle', 'L_Leg_Upper')},
        'native_sha256': sha(native),
        'root_position_observation': {
            'native_channel_at_frame_zero_m': native_root.tolist(),
            'live_layer_component_minimum_m': root.min(axis=0).tolist(),
            'live_layer_component_maximum_m': root.max(axis=0).tolist(),
            'live_layer_horizontal_span_m': float(np.linalg.norm(np.ptp(root[:, [0, 2]], axis=0))),
            'maximum_difference_from_raw_native_channel_m': float(np.max(np.linalg.norm(root-native_root, axis=1))),
            'raw_channel_equals_layer_position': bool(np.allclose(root, native_root, atol=1e-6, rtol=0)),
            'interpretation': 'Observed layer root differs from raw channel. Root extraction/procedural composition has not been isolated; this is not a world-space foot-drift measurement.'},
        'final_controller_transforms_verified': False,
        'visual_acceptance_verified': False,
        'scope': 'Actual enabled weight-one layer rotations, measured at captured native frame; final controller, IK, root composition and visible feet require separate validation.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('capture'); parser.add_argument('--output', required=True)
    args = parser.parse_args(); result = compare(load_capture(args.capture))
    result['capture_sha256'] = sha(Path(args.capture))
    output = Path(args.output)
    if output.exists(): raise ValueError('Preserve existing comparison')
    write_json(output, result)
    print(json.dumps(result, indent=2))

