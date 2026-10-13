"""Export the accepted native model plus an offline retargeted idle to GLB."""
import argparse
import io
import json
import numpy as np
from PIL import Image
from common import ROOT, confined, reader, write_json
from analyze_assets import parsed_mesh
from animation_math import decompose, quaternion_matrix, hierarchy_globals, motion_globals
from glb_read import load, sample_globals
from retarget_math import Retarget, rotation
from retarget_protection import protect
from source_animation_export import GLB, validate_decoded
from source_animation_workflow import sha


def target_parts(config):
    reference = json.loads((ROOT / 'reports/stabilization/native_scene.json').read_text())
    result = []
    for row in reference['parts']:
        relative = row['native'].split('/natives/')[1]
        path = ROOT / config['target_native_root'] / 'natives' / relative
        result.append((row['part'], path, parsed_mesh(path)[1]))
    return result


def skeleton(mesh):
    records = []
    for bone in mesh.skeleton.boneList:
        parent = mesh.skeleton.boneList[bone.parentIndex].boneName if bone.parentIndex >= 0 else None
        records.append({'name': bone.boneName, 'parent': parent, 'local': np.asarray(bone.localMatrix.matrix).T,
                        'world': np.asarray(bone.worldMatrix.matrix).T, 'inverse': np.asarray(bone.inverseMatrix.matrix).T})
    if len(records) != 611: raise ValueError('Target rig is not the accepted 611-bone skeleton')
    return records


def materials(glb, path, mesh, cache):
    module = reader('RE-Mesh-Editor', 'remesh', 'modules.mdf.file_re_mdf')
    mdf = next(path.parent.glob(path.name.split('.mesh')[0] + '*.mdf2.51'))
    indices = {}
    for mat in module.readMDF(str(mdf)).materialList:
        key = mat.materialName
        if key not in cache:
            bindings = {t.textureType: t.texturePath.lower() for t in mat.textureList}
            properties = {p.propName: p.propValue for p in mat.propertyList}
            tint = properties.get('BaseColor', [1, 1, 1, 1])
            if len(tint) != 4: tint = [1, 1, 1, 1]
            output = {'name': key, 'doubleSided': True,
                      'pbrMetallicRoughness': {'baseColorFactor': tint, 'metallicFactor': 0, 'roughnessFactor': .6}}
            report = json.loads((ROOT / 'reports/material_build.json').read_text())
            previews = {'character/mods/belagrace/textures/' + (ROOT / r['path']).name.split('.tex')[0] + '.tex': ROOT / r['preview']
                        for r in report['textures']}
            previews.update({k.lower(): ROOT / v for k, v in json.loads((ROOT / 'reports/baseline_previews.json').read_text())['resources'].items()})
            base = previews.get(bindings.get('BaseDielectricMap', bindings.get('BaseShiftMap')))
            if base:
                im = Image.open(base).convert('RGBA')
                if any(token in key.lower() for token in ['hair', 'eyelash', 'eyebrow']):
                    alpha = previews.get(bindings.get('AlphaCavityOcclusionTranslucentMap'))
                    if alpha:
                        im.putalpha(Image.open(alpha).getchannel('R').resize(im.size))
                        output.update(alphaMode='MASK', alphaCutoff=.35)
                stream = io.BytesIO(); im.save(stream, format='PNG')
                image = len(glb.doc['images']); glb.doc['images'].append({'bufferView': glb.view(stream.getvalue()), 'mimeType': 'image/png'})
                texture = len(glb.doc['textures']); glb.doc['textures'].append({'source': image, 'sampler': 0})
                output['pbrMetallicRoughness']['baseColorTexture'] = {'index': texture}
            cache[key] = len(glb.doc['materials']); glb.doc['materials'].append(output)
        indices[key] = cache[key]
    return indices


def channel_dispositions(decoded, mapping):
    rows = []
    for track in decoded['tracks']:
        name = track['bone']
        if name in mapping: reason = 'Body rotation retargeted; target limb translations retained. Root translation transferred relative to first frame.'
        elif name == 'Null_Offset': reason = 'Source leaf sibling of Hip; no weighted descendants. Not inserted into target pelvis chain.'
        elif name.endswith('_Offset'): reason = 'Source IK helper retained in approved reference; target IK local controls protected.'
        elif name.startswith('skirt_'): reason = 'Source garment controls lack target correspondence; accepted target body weights retained, no cloth animation added.'
        elif name.startswith('Hair'): reason = 'Source secondary hair tracks lack target correspondence; accepted hood/head/neck weights retained.'
        elif name.endswith('_Wep') or any(token in name for token in ['Thumb', 'IndexF', 'MiddleF', 'RingF', 'PinkyF', 'Palm']):
            reason = 'Explicitly excluded from body layer to preserve Grace weapon and finger controls.'
        else: raise ValueError(f'Unclassified source track: {name}')
        rows.append({'source_bone': name, 'target': mapping.get(name), 'policy': reason,
                     'channels': [kind for kind in ['translation', 'rotation', 'scale'] if track[kind]]})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config/retarget_idle_v0.2.0.json')
    parser.add_argument('--output'); parser.add_argument('--report-name', default='retarget_idle')
    args = parser.parse_args()
    config = json.loads(confined(ROOT, args.config).read_text())
    output = confined(ROOT / 'build', (args.output or config['output']).removeprefix('build/'))
    if output.exists(): raise ValueError('Use fresh output; retain previous experiments')
    protected = protect(); output.mkdir(parents=True)
    decoded = json.loads((ROOT / config['decoded']).read_text())
    validate_decoded(decoded, json.loads((ROOT / config['source_config']).read_text()))
    doc, data = load(ROOT / config['source_glb']); source_world = sample_globals(doc, data, None)
    source_bind = {n['name']: source_world[i] for i, n in enumerate(doc['nodes'])}
    parts = target_parts(config); target = skeleton(parts[0][2]); names = [b['name'] for b in target]
    index = {n: i for i, n in enumerate(names)}
    adapter = Retarget(decoded, source_bind, target, config)
    # Floor placement uses actual accepted footwear, not a nominal ankle origin.
    first_world = adapter.pose(0)[1]
    skin = first_world @ np.asarray([b['inverse'] for b in target])
    soles = []
    for part, native_path, mesh in parts:
        palette = np.asarray([index[n] for n in mesh.skeleton.weightedBones])
        for group in mesh.mainMeshLODList[0].visconGroupList:
            for sub in group.subMeshList:
                if 'Boots_Sole' not in mesh.materialNameList[sub.materialIndex]: continue
                p = np.asarray(sub.vertexPosList); bottom = p[:, 1] <= p[:, 1].min() + .003
                p = np.c_[p[bottom], np.ones(bottom.sum())]
                w = np.asarray(sub.weightList)[bottom]; j = palette[np.asarray(sub.weightIndicesList)[bottom]]
                deformed = sum(np.einsum('nij,nj->ni', skin[j[:, k]], p) * w[:, k, None] for k in range(w.shape[1]))
                soles.extend(deformed[:, 1].tolist())
    if not soles: raise ValueError('Accepted footwear contact surface not found')
    config['root_floor_offset_m'] = -float(min(soles))
    glb = GLB(); g = glb.doc; g['asset']['generator'] = 'Bela offline Grace retarget v0.2.0'
    for i, b in enumerate(target):
        t, q, s = decompose(b['local']); node = {'name': b['name'], 'translation': t.tolist(), 'rotation': q.tolist(), 'scale': s.tolist()}
        children = [j for j, child in enumerate(target) if child['parent'] == b['name']]
        if children: node['children'] = children
        g['nodes'].append(node)
    g['scenes'][0]['nodes'] = [i for i, b in enumerate(target) if b['parent'] is None]
    inverse = np.asarray([b['inverse'] for b in target], dtype='<f4').swapaxes(-1, -2).reshape(-1, 16)
    g['skins'].append({'name': 'Accepted_Grace_611_bind', 'joints': list(range(611)), 'inverseBindMatrices': glb.accessor(inverse, 'MAT4'), 'skeleton': index['root']})
    rows = []; cache = {}; vertices = 0; triangles = 0
    for part, path, mesh in parts:
        check = skeleton(mesh)
        if [b['name'] for b in check] != names or any(not np.allclose(b['local'], target[i]['local'], atol=1e-7, rtol=0) for i, b in enumerate(check)):
            raise ValueError('Accepted component skeleton differs')
        mat = materials(glb, path, mesh, cache); primitives = []
        for group in mesh.mainMeshLODList[0].visconGroupList:
            for sub in group.subMeshList:
                position = np.asarray(sub.vertexPosList, dtype='<f4'); weights = np.asarray(sub.weightList, dtype='<f4')
                palette = np.asarray([index[n] for n in mesh.skeleton.weightedBones], dtype='<u2')
                joints = palette[np.asarray(sub.weightIndicesList)]
                if np.any(weights < 0) or not np.allclose(weights.sum(axis=1), 1, atol=1e-6): raise ValueError('Native weights invalid')
                uv = np.asarray(sub.uvList, dtype='<f4').copy(); uv[:, 1] = 1 - uv[:, 1]
                attrs = {'POSITION': glb.accessor(position, 'VEC3', True), 'NORMAL': glb.accessor(np.asarray(sub.normalList, dtype='<f4'), 'VEC3'),
                         'TEXCOORD_0': glb.accessor(uv, 'VEC2'), 'JOINTS_0': glb.accessor(joints[:, :4], 'VEC4'),
                         'WEIGHTS_0': glb.accessor(np.ascontiguousarray(weights[:, :4]), 'VEC4')}
                if weights.shape[1] > 4 and np.any(weights[:, 4:] > 0):
                    attrs['JOINTS_1'] = glb.accessor(joints[:, 4:8], 'VEC4'); attrs['WEIGHTS_1'] = glb.accessor(np.ascontiguousarray(weights[:, 4:8]), 'VEC4')
                faces = np.asarray(sub.faceList, dtype='<u4').reshape(-1)
                primitives.append({'attributes': attrs, 'indices': glb.accessor(faces, 'SCALAR'), 'material': mat[mesh.materialNameList[sub.materialIndex]]})
                vertices += len(position); triangles += len(faces) // 3
        mi = len(g['meshes']); g['meshes'].append({'name': part, 'primitives': primitives})
        g['scenes'][0]['nodes'].append(len(g['nodes'])); g['nodes'].append({'name': 'Accepted_' + part, 'mesh': mi, 'skin': 0})
        rows.append({'part': part, 'native': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)})
    frames = np.arange(301, dtype=float); poses = [adapter.pose(f) for f in frames]
    locals_ = np.asarray([pose[0] for pose in poses]); globals_ = np.asarray([pose[1] for pose in poses])
    time = glb.accessor((frames / 60).astype('<f4'), 'SCALAR')
    animation = {'name': 'Bela_RE8_Idle_on_Grace_611_Offline', 'samplers': [], 'channels': []}
    for dest in adapter.reverse:
        bone = index[dest]
        q = np.asarray([decompose(m)[1] for m in locals_[:, bone]], dtype='<f4')
        for i in range(1, len(q)):
            if np.dot(q[i - 1], q[i]) < 0: q[i] *= -1
        sampler = len(animation['samplers']); animation['samplers'].append({'input': time, 'output': glb.accessor(q, 'VEC4'), 'interpolation': 'LINEAR'})
        animation['channels'].append({'sampler': sampler, 'target': {'node': bone, 'path': 'rotation'}})
    root = index['root']; sampler = len(animation['samplers'])
    animation['samplers'].append({'input': time, 'output': glb.accessor(np.asarray(locals_[:, root, :3, 3], dtype='<f4'), 'VEC3'), 'interpolation': 'LINEAR'})
    animation['channels'].append({'sampler': sampler, 'target': {'node': root, 'path': 'translation'}})
    g['animations'].append(animation); g['extras'] = {'scope': 'Offline body retarget only; target native controls and all binds/weights unchanged', 'source_checkpoint': '44eb9e1', 'target_bones': 611}
    path = output / 'retarget_idle.glb'; glb.write(path)
    np.savez_compressed(output / 'retarget_matrices.npz', locals=locals_, globals=globals_, bind_local=adapter.bind_local, bind_world=adapter.bind_world)
    write_json(output / 'target_rig.json', [{k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in b.items()} for b in target])
    write_json(output / 'retarget_config.json', config)
    report = {'status': 'EXPORTED_OFFLINE_AWAITING_BLENDER_REVIEW', 'source_visual_acceptance': True, 'mapping': adapter.mapping_rows,
              'source_channel_dispositions': channel_dispositions(decoded, config['mapping']),
              'source_hierarchy_correction': 'Hip and Null_Offset are sibling children of root. Null_Offset is a leaf and is not composed into Hip.',
              'foot_mapping_correction': 'Source Foot maps to Grace Leg_Ankle; the target Leg_Foot intermediate retains its bind local.',
              'target_native_inputs': rows, 'vertices': vertices, 'triangles': triangles, 'target_bones': 611,
              'constant_root_floor_offset_m': config['root_floor_offset_m'],
              'output': output.relative_to(ROOT).as_posix(), 'glb_sha256': sha(path), 'protected_before_and_after': protected,
              'target_nonroot_translation_changes': float(np.max(np.abs(locals_[:, 1:, :3, 3] - adapter.bind_local[None, 1:, :3, 3]))),
              'native_RE9_animation_written': False, 'runtime_tested': False}
    if protect() != protected: raise ValueError('Protected state changed')
    write_json(ROOT / f'reports/retarget_v0.2.0/{args.report_name}_export.json', report)
    print(f'Offline retarget exported: {len(config["mapping"])} reviewed bones; {triangles} accepted triangles; all 611 binds unchanged')


if __name__ == '__main__':
    main()

