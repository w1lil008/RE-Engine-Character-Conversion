"""Numerical retarget validation and independent preservation checks."""
import argparse
import json
import numpy as np
from common import ROOT, confined, write_json
from animation_math import motion_globals, hierarchy_globals, decompose
from glb_read import load, accessor, sample_globals
from retarget_math import Retarget, rotation
from retarget_idle_export import target_parts, skeleton
from retarget_protection import protect


def motion_metrics(points):
    displacement = points - points[0]
    return {'start_m': points[0].tolist(), 'axis_range_m': np.ptp(points, axis=0).tolist(),
            'maximum_distance_from_start_m': float(np.linalg.norm(displacement, axis=1).max()),
            'horizontal_range_diagonal_m': float(np.linalg.norm(np.ptp(points[:, [0, 2]], axis=0))),
            'endpoint_distance_m': float(np.linalg.norm(points[-1] - points[0]))}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    p.add_argument('--report-name', default='retarget_idle'); args = p.parse_args()
    out = confined(ROOT, args.output); config = json.loads((out / 'retarget_config.json').read_text())
    protected = protect(); decoded = json.loads((ROOT / config['decoded']).read_text())
    sd, sb = load(ROOT / config['source_glb']); sw = sample_globals(sd, sb, None)
    source_bind = {n['name']: sw[i] for i, n in enumerate(sd['nodes'])}
    parts = target_parts(config); target = skeleton(parts[0][2]); names = [b['name'] for b in target]
    sn = [b['name'] for b in decoded['bones']]; doc, data = load(out / 'retarget_idle.glb')
    adapter = Retarget(decoded, source_bind, target, config)
    reference = np.load(out / 'retarget_matrices.npz')
    # Exact accepted native geometry and all eight original influences.
    native_corner_count = 0; primitives = 0
    for (part, path, mesh), gm in zip(parts, doc['meshes']):
        expected = [s for g in mesh.mainMeshLODList[0].visconGroupList for s in g.subMeshList]
        if len(expected) != len(gm['primitives']): raise ValueError('Native components missing/duplicated')
        for sub, primitive in zip(expected, gm['primitives']):
            attrs = primitive['attributes']
            if not np.array_equal(accessor(doc, data, attrs['POSITION']), np.asarray(sub.vertexPosList, dtype='<f4')):
                raise ValueError('Accepted native geometry changed')
            actual_w = np.c_[accessor(doc, data, attrs['WEIGHTS_0']),
                             accessor(doc, data, attrs['WEIGHTS_1']) if 'WEIGHTS_1' in attrs else np.zeros((len(sub.vertexPosList), 4))]
            actual_j = np.c_[accessor(doc, data, attrs['JOINTS_0']),
                             accessor(doc, data, attrs['JOINTS_1']) if 'JOINTS_1' in attrs else np.zeros((len(sub.vertexPosList), 4), dtype=int)]
            native_w = np.asarray(sub.weightList, dtype='<f4')
            if not np.array_equal(actual_w, native_w): raise ValueError('Accepted skin weights changed')
            palette = np.asarray([names.index(n) for n in mesh.skeleton.weightedBones])
            expected_j = palette[np.asarray(sub.weightIndicesList)]
            if not np.array_equal(actual_j[actual_w > 0], expected_j[native_w > 0]): raise ValueError('Weighted bone associations changed')
            if not np.array_equal(accessor(doc, data, primitive['indices']).ravel(), np.asarray(sub.faceList).ravel()):
                raise ValueError('Accepted topology changed')
            native_corner_count += len(sub.faceList) * 3; primitives += 1
    local_error = 0.; global_error = 0.; quaternion_error = 0.; source_segment_error = 0.
    frames = np.arange(0, 300.001, .5); gt = []; source = []
    protected_indices = [i for i, name in enumerate(names) if name not in adapter.reverse]
    protected_local_error = 0.; target_translation_error = 0.; length_error = 0.
    for frame in frames:
        local, world = adapter.pose(float(frame)); gltf = sample_globals(doc, data, frame / 60)[:611]
        global_error = max(global_error, float(np.abs(gltf - world).max()))
        length_error = max(length_error, float(np.abs(np.linalg.norm(local[1:, :3, 3], axis=1) - np.linalg.norm(adapter.bind_local[1:, :3, 3], axis=1)).max()))
        protected_local_error = max(protected_local_error, float(np.abs(local[protected_indices] - adapter.bind_local[protected_indices]).max()))
        target_translation_error = max(target_translation_error, float(np.abs(local[1:, :3, 3] - adapter.bind_local[1:, :3, 3]).max()))
        src = motion_globals(decoded, float(frame)); source.append(src); gt.append(world)
        for sname, (se, te) in config['segment_ends'].items():
            a = src[sn.index(se), :3, 3] - src[sn.index(sname), :3, 3]
            b = world[names.index(te), :3, 3] - world[names.index(config['mapping'][sname]), :3, 3]
            angle = float(np.degrees(np.arccos(np.clip(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)), -1, 1))))
            source_segment_error = max(source_segment_error, angle)
        if frame % 1 == 0:
            global_error = max(global_error, float(np.abs(world - reference['globals'][int(frame)]).max()))
            local_error = max(local_error, float(np.abs(local - reference['locals'][int(frame)]).max()))
    for sampler in doc['animations'][0]['samplers']:
        values = accessor(doc, data, sampler['output'])
        if values.shape[1] == 4: quaternion_error = max(quaternion_error, float(np.abs(np.linalg.norm(values, axis=1) - 1).max()))
    gt = np.asarray(gt); source = np.asarray(source)
    foot = {}; lengths = {}
    for side in ['L', 'R']:
        for sname, tname in [('Foot', 'Leg_Ankle'), ('Toe', 'Leg_Toes')]:
            foot[f'{side}_{tname}'] = {'target': motion_metrics(gt[:, names.index(f'{side}_{tname}'), :3, 3]),
                                      'source': motion_metrics(source[:, sn.index(f'{side}_{sname}'), :3, 3])}
        for start, end, ts, te in [('Thigh', 'Shin', 'Leg_Upper', 'Leg_Lower'), ('Shin', 'Foot', 'Leg_Lower', 'Leg_Ankle')]:
            sl = np.linalg.norm(source_bind[f'{side}_{end}'][:3, 3] - source_bind[f'{side}_{start}'][:3, 3])
            tl = np.linalg.norm(adapter.bind_world[names.index(f'{side}_{te}'), :3, 3] - adapter.bind_world[names.index(f'{side}_{ts}'), :3, 3])
            lengths[f'{side}_{ts}'] = {'source_mesh_bind_length_m': float(sl), 'target_bind_length_m': float(tl), 'target_source_ratio': float(tl / sl)}
    loop = np.linalg.norm(gt[-1, :, :3, 3] - gt[0, :, :3, 3], axis=1)
    angles = np.degrees(np.arccos(np.clip((np.einsum('nij,nij->n', gt[0, :, :3, :3], gt[-1, :, :3, :3]) - 1) / 2, -1, 1)))
    report = {'status': 'PASSED', 'samples': len(frames), 'sampling_fps': 120, 'target_bones': 611,
              'maximum_glTF_vs_retargeter_world_matrix_error': global_error, 'maximum_saved_local_matrix_error': local_error,
              'maximum_nonroot_translation_change_m': target_translation_error, 'maximum_bone_length_change_m': length_error,
              'maximum_protected_local_transform_change': protected_local_error, 'protected_local_bones': len(protected_indices),
              'maximum_quaternion_norm_error': quaternion_error, 'maximum_anatomical_segment_direction_error_degrees': source_segment_error,
              'root': motion_metrics(gt[:, names.index('root'), :3, 3]), 'foot_motion': foot, 'limb_proportions': lengths,
              'loop': {'maximum_joint_endpoint_distance_m': float(loop.max()), 'worst_joint': names[int(loop.argmax())],
                       'maximum_rotation_endpoint_angle_degrees': float(angles.max())},
              'native_geometry_topology_and_eight_weights_exactly_preserved': True, 'native_triangle_corners_checked': native_corner_count,
              'native_primitives_checked': primitives, 'protected_state': protected, 'native_RE9_outputs_written': False,
              'runtime_tested': False,
              'residual_foot_motion_explanation': 'Source already has millimetre foot movement. Target limb proportions and retained hip/limb offsets differ while root sway is copied unscaled; no IK or foot-lock correction was inserted.'}
    if global_error > 2e-4 or target_translation_error > 1e-10 or protected_local_error > 1e-10 or source_segment_error > .01:
        report['status'] = 'FAILED'
    write_json(ROOT / f'reports/retarget_v0.2.0/{args.report_name}_numerical.json', report)
    if report['status'] != 'PASSED': raise ValueError(report)
    print(f'Offline retarget validated at {len(frames)} poses; all accepted geometry/weights exact; protected controls unchanged')


if __name__ == '__main__':
    main()

