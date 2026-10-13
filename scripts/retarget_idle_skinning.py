"""Independent eight-influence CPU skinning versus Blender's retarget geometry."""
import argparse
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import numpy as np
from mathutils import Matrix
from common import ROOT, confined, write_json
from glb_read import load, sample_globals, accessor


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    p.add_argument('--report-name', default='retarget_idle'); args = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    out = confined(ROOT, args.output); bpy.ops.wm.open_mainfile(filepath=str(out / 'retarget_idle.blend'))
    doc, data = load(out / 'retarget_idle.glb'); axis = np.asarray(Matrix.Rotation(math.pi / 2, 4, 'X'))
    skin = doc['skins'][0]; inverse = accessor(doc, data, skin['inverseBindMatrices']).reshape(-1, 4, 4).swapaxes(-1, -2)
    records = []; garment = []; soles = []; first_edges = {}
    for frame in [0, 75, 150, 225, 300]:
        bpy.context.scene.frame_set(frame); bpy.context.view_layer.update(); deps = bpy.context.evaluated_depsgraph_get()
        transforms = sample_globals(doc, data, frame / 60)[skin['joints']] @ inverse
        sole_heights = []
        for node in doc['nodes']:
            if 'mesh' not in node: continue
            expected = []
            for primitive_index, primitive in enumerate(doc['meshes'][node['mesh']]['primitives']):
                a = primitive['attributes']; v = accessor(doc, data, a['POSITION']); vh = np.c_[v, np.ones(len(v))]
                deformed = np.zeros((len(v), 4))
                for suffix in ['0', '1']:
                    if 'WEIGHTS_' + suffix not in a: continue
                    w = accessor(doc, data, a['WEIGHTS_' + suffix]); j = accessor(doc, data, a['JOINTS_' + suffix])
                    for k in range(4): deformed += np.einsum('nij,nj->ni', transforms[j[:, k]], vh) * w[:, k, None]
                points = (axis @ deformed.T).T[:, :3]
                faces = accessor(doc, data, primitive['indices']).reshape(-1, 3)
                expected.append(points[faces.ravel()])
                material = doc['materials'][primitive['material']]['name']
                if 'Boots_Sole' in material:
                    bottom = v[:, 1] <= v[:, 1].min() + .003
                    sole_heights.extend(deformed[bottom, 1].tolist())
                if any(token in material for token in ['Dress', 'Hood']):
                    edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [0, 2]]]), axis=1), axis=0)
                    rest = np.linalg.norm(v[edges[:, 0]] - v[edges[:, 1]], axis=1); valid = rest > .0001
                    lengths = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
                    ratios = lengths[valid] / rest[valid]
                    key = (node['name'], primitive_index)
                    if frame == 0: first_edges[key] = lengths.copy()
                    first = first_edges[key]; motion_valid = first > .0001
                    motion_ratios = lengths[motion_valid] / first[motion_valid]
                    worst = int(np.argmax(np.where(valid, lengths / np.maximum(rest, 1e-12), 0)))
                    garment.append({'frame': frame, 'component': node['name'], 'material': material,
                                    'edge_ratio_p01': float(np.quantile(ratios, .01)), 'edge_ratio_p99': float(np.quantile(ratios, .99)),
                                    'edge_ratio_max': float(ratios.max()),
                                    'worst_ratio_edge_bind_length_m': float(rest[worst]),
                                    'worst_ratio_edge_posed_length_m': float(lengths[worst]),
                                    'motion_from_first_frame_edge_ratio_p01': float(np.quantile(motion_ratios, .01)),
                                    'motion_from_first_frame_edge_ratio_p99': float(np.quantile(motion_ratios, .99)),
                                    'maximum_edge_length_change_from_first_frame_m': float(np.abs(lengths - first).max())})
            expected = np.concatenate(expected); obj = bpy.data.objects[node['name']]
            evaluated = obj.evaluated_get(deps); mesh = evaluated.to_mesh(); mesh.calc_loop_triangles()
            actual = np.array([(evaluated.matrix_world @ mesh.vertices[i].co).to_tuple() for triangle in mesh.loop_triangles for i in triangle.vertices])
            evaluated.to_mesh_clear()
            if actual.shape != expected.shape or not np.isfinite(actual).all(): raise ValueError('Retarget geometry topology/finite check failed')
            error = np.linalg.norm(actual - expected, axis=1)
            records.append({'frame': frame, 'component': node['name'], 'triangle_corners': len(error), 'maximum_error_m': float(error.max())})
            if error.max() > .00002: raise ValueError(f'Blender skinning mismatch: {records[-1]}')
        soles.append({'frame': frame, 'minimum_contact_patch_height_m': float(min(sole_heights)),
                      'maximum_contact_patch_height_m': float(max(sole_heights))})
    write_json(ROOT / f'reports/retarget_v0.2.0/{args.report_name}_skinning.json', {
        'status': 'PASSED', 'frames': [0, 75, 150, 225, 300], 'components': records,
        'maximum_triangle_corner_error_m': max(r['maximum_error_m'] for r in records),
        'garment_edge_strain': garment, 'native_boot_sole_contact_patches': soles,
        'contact_scope': 'Original bottom 3 mm of native boot sole material; numerical heights, not a collision/IK simulation.',
        'physics_or_skin_weight_changes': False, 'runtime_tested': False,
    })
    print('Retarget geometry matches independent CPU skinning; garment strain and sole contact measured')


if __name__ == '__main__':
    main()

