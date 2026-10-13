"""Validate/render the retarget and a synchronized original-source comparison."""
import argparse
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import numpy as np
from mathutils import Matrix, Vector
from common import ROOT, confined, write_json
from glb_read import load, sample_globals


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def movie(scene, path, width, height):
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = width; scene.render.resolution_y = height
    scene.display.shading.light = 'STUDIO'; scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = False
    for material in bpy.data.materials:
        image = next((n.image for n in material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None) if material.use_nodes else None
        if image:
            pixels = np.asarray(image.pixels[:]).reshape(-1, 4)[::97]
            colour = pixels[pixels[:, 3] > .5, :3].mean(axis=0) if np.any(pixels[:, 3] > .5) else np.array([.1] * 3)
            factor = material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value[:3]
            material.diffuse_color = (*np.clip(colour * factor, 0, 1), 1)
    scene.render.image_settings.file_format = 'FFMPEG'; scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'; scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    scene.render.filepath = str(path); bpy.ops.render.render(animation=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True); parser.add_argument('--video', action='store_true')
    parser.add_argument('--validate-only', action='store_true'); parser.add_argument('--glb', default='retarget_idle.glb')
    parser.add_argument('--report-name', default='retarget_idle')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    out = confined(ROOT, args.output); config = json.loads((out / 'retarget_config.json').read_text())
    doc, data = load(out / 'retarget_idle.glb'); names = [n['name'] for n in doc['nodes']]
    skeleton = json.loads((out / 'target_rig.json').read_text()); bn = [b['name'] for b in skeleton]
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene; scene.render.fps = 60; scene.render.fps_base = 1
    bpy.ops.import_scene.gltf(filepath=str(out / args.glb), merge_vertices=False)
    rig = next(o for o in scene.objects if o.type == 'ARMATURE'); rig.name = 'Grace_611_Bela_Retarget'
    if len(rig.data.bones) != 611 or set(rig.data.bones.keys()) != set(bn): raise ValueError('Target hierarchy lost bones')
    if not np.allclose(rig.animation_data.action.frame_range, [0, 300]): raise ValueError('Incorrect animation timing')
    for b in skeleton:
        parent = rig.data.bones[b['name']].parent
        if (parent.name if parent else None) != b['parent']: raise ValueError('Target parent changed')
    axis = np.asarray(Matrix.Rotation(math.pi / 2, 4, 'X'))
    bind = sample_globals(doc, data, None); indices = [names.index(n) for n in bn]
    correction = {n: np.linalg.inv(np.asarray(rig.matrix_world @ rig.data.bones[n].matrix_local)) @ axis @ bind[names.index(n)] for n in bn}
    max_matrix = 0.; max_joint = 0.; worst = None
    for frame in np.arange(0, 300.001, .5):
        scene.frame_set(int(frame), subframe=float(frame % 1)); bpy.context.view_layer.update()
        expected = axis @ sample_globals(doc, data, frame / 60)[indices]
        for i, name in enumerate(bn):
            actual = np.asarray(rig.matrix_world @ rig.pose.bones[name].matrix) @ correction[name]
            component = float(np.abs(actual - expected[i]).max()); joint = float(np.linalg.norm(actual[:3, 3] - expected[i, :3, 3]))
            if component > max_matrix: max_matrix = component; worst = {'bone': name, 'frame': float(frame)}
            max_joint = max(max_joint, joint)
    report = {'status': 'PASSED' if max_matrix < .0002 and max_joint < .0002 else 'FAILED',
              'target_bones': 611, 'samples': 601, 'sampling_fps': 120, 'maximum_matrix_component_error': max_matrix,
              'maximum_joint_error_m': max_joint, 'worst': worst, 'input_glb': args.glb,
              'target_parent_names_unchanged': True, 'native_RE9_runtime_tested': False}
    write_json(ROOT / f'reports/retarget_v0.2.0/{args.report_name}_{"roundtrip" if args.validate_only else "blender"}.json', report)
    if report['status'] != 'PASSED': raise ValueError(report)
    if args.validate_only: print('Retarget GLB export/reimport validated'); return
    scene.frame_start = 0; scene.frame_end = 300; scene.frame_set(0)
    bpy.ops.export_scene.gltf(filepath=str(out / 'retarget_idle_roundtrip.glb'), export_format='GLB', export_skins=True,
                            export_animations=True, export_all_influences=True, export_force_sampling=True, export_frame_range=False)
    scene.frame_end = 299; scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = 640; scene.render.resolution_y = 800; scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'; scene.world.color = (.055, .055, .055)
    scene.view_settings.view_transform = 'AgX'; scene.eevee.taa_render_samples = 32
    bpy.ops.object.camera_add(location=(2.4, -5, 2.1)); camera = bpy.context.object
    camera.data.type = 'ORTHO'; camera.data.ortho_scale = 2.1; aim(camera, (0, 0, .95)); scene.camera = camera
    for name, position, power in [('Key', (3, -3, 4), 800), ('Fill', (-3, -2, 3), 550), ('Rim', (1, 3, 4), 650)]:
        bpy.ops.object.light_add(type='AREA', location=position); light = bpy.context.object; light.name = name
        light.data.energy = power; light.data.size = 3; aim(light, (0, 0, 1))
    scene['SCOPE'] = 'Offline body retarget; accepted geometry, weights and 611-bone runtime hierarchy preserved'
    scene['CONTROL_POLICY'] = 'No target finger, weapon or IK local channels replaced; target translations preserved except source root trajectory'
    scene.frame_set(0); bpy.ops.wm.save_as_mainfile(filepath=str(out / 'retarget_idle.blend'))
    for view, location, target, scale in [('three_quarter', (2.4, -5, 2.1), (0, 0, .95), 2.1),
                                         ('side', (5, 0, 1.9), (0, 0, .9), 2.1),
                                         ('head_shoulders', (1.4, -5, 1.65), (0, 0, 1.38), .75),
                                         ('feet', (1.5, -5, .5), (0, 0, .18), .6)]:
        camera.location = location; camera.data.ortho_scale = scale; aim(camera, target)
        for label, frame in [('start', 0), ('middle', 150), ('end', 300)]:
            scene.frame_set(frame); scene.render.filepath = str(out / f'{view}_{label}.png'); bpy.ops.render.render(write_still=True)
    # A floor guide is review-only and remains outside the rig/GLB export.
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -.0005))
    floor = bpy.context.object; floor.name = 'Review_floor_at_native_boot_contact'
    material = bpy.data.materials.new('Review_floor'); material.diffuse_color = (.07, .07, .07, 1)
    floor.data.materials.append(material)
    camera.location = (2.4, -5, 2.1); camera.data.ortho_scale = 2.1; aim(camera, (0, 0, .95))
    if args.video: movie(scene, out / 'retarget_idle_60fps.mp4', 480, 600)
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / config['source_glb']), merge_vertices=False)
    added = set(scene.objects) - before
    original = next(o for o in added if o.type == 'ARMATURE'); original.name = 'Approved_RE8_Source_Reference'
    right = camera.rotation_euler.to_matrix() @ Vector((1, 0, 0))
    # Translate entire reference/target scenes only for comparison placement.
    for obj in added:
        if obj.parent is None: obj.location -= right * .7
    target_objects = [o for o in before if o.type in ['MESH', 'ARMATURE'] and o != floor]
    for obj in target_objects:
        if obj.parent is None: obj.location += right * .7
    scene['COMPARISON'] = 'Left: approved original RE8. Right: Grace-based Bela retarget. Same camera, native proportions, synchronized 60 FPS timing.'
    scene.render.engine = 'BLENDER_EEVEE_NEXT'; scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = 1000; scene.render.resolution_y = 640
    camera.data.ortho_scale = 2.2 * 1000 / 640  # Blender fits the width for landscape output.
    scene.frame_set(0); bpy.ops.wm.save_as_mainfile(filepath=str(out / 'comparison.blend'))
    for label, frame in [('start', 0), ('middle', 150), ('end', 300)]:
        scene.frame_set(frame); scene.render.filepath = str(out / f'comparison_{label}.png'); bpy.ops.render.render(write_still=True)
    if args.video:
        camera.data.ortho_scale = 2.2 * 960 / 600
        movie(scene, out / 'comparison_60fps.mp4', 960, 600)
    print('Retarget 611-bone playback and synchronized source comparison rendered')


if __name__ == '__main__':
    main()

