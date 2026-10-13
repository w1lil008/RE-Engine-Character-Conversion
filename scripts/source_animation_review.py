"""Render a previously validated source scene with a following review camera.

Only camera/light transforms change. Original animation and root motion remain.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import numpy as np
from common import ROOT, confined, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--report-name', required=True)
    parser.add_argument('--video', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if not args.report_name.replace('_', '').isalnum():
        raise ValueError('Invalid report name')
    output = confined(ROOT / 'build', args.output.removeprefix('build/'))
    source = output / 'source_idle.blend'
    review = output / 'source_review_follow_root.blend'
    if review.exists():
        raise ValueError('Preserve prior review; use a fresh output directory')
    decoded = json.loads((output / 'decoded_reference.json').read_text())
    duration = int(decoded['frame_count'])
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    rig = next(obj for obj in scene.objects if obj.type == 'ARMATURE')
    # Keep the original armature action exactly as imported and measured.
    original_action = rig.animation_data.action
    bpy.ops.object.empty_add()
    anchor = bpy.context.object
    anchor.name = 'Review_camera_follow_original_root'
    for obj in [scene.camera] + [obj for obj in scene.objects if obj.type == 'LIGHT']:
        obj.parent = anchor
    root_positions = []
    for frame in range(duration + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        anchor.location = (rig.matrix_world @ rig.pose.bones['root'].matrix).translation
        root_positions.append(list(anchor.location))
        anchor.keyframe_insert(data_path='location', frame=frame)
    for curve in anchor.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    assert rig.animation_data.action == original_action
    scene['REVIEW_CAMERA'] = 'Camera/lights follow original root translation. Source root and all bone keys unchanged.'
    scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(review))
    frames = [0, duration // 4, duration // 2, duration * 3 // 4, duration]
    for label, frame in zip(['start', 'quarter', 'middle', 'three_quarter', 'end'], frames):
        scene.frame_set(frame)
        scene.render.filepath = str(output / f'review_follow_root_{label}.png')
        bpy.ops.render.render(write_still=True)
    if args.video:
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.render.resolution_x = 480
        scene.render.resolution_y = 600
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'MATERIAL'
        scene.display.shading.show_shadows = False
        for material in bpy.data.materials:
            image = next((node.image for node in material.node_tree.nodes
                          if node.type == 'TEX_IMAGE' and node.image), None) if material.use_nodes else None
            if image:
                pixels = np.asarray(image.pixels[:]).reshape(-1, 4)[::97]
                colour = pixels[pixels[:, 3] > .5, :3].mean(axis=0) if np.any(pixels[:, 3] > .5) else np.array([.1] * 3)
                material.diffuse_color = (*np.clip(colour, 0, 1), 1)
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = 'HIGH'
        scene.render.filepath = str(output / 'source_follow_root_60fps.mp4')
        bpy.ops.render.render(animation=True)
    points = np.asarray(root_positions)
    write_json(ROOT / f'reports/animation_dev/{args.report_name}_review.json', {
        'status': 'RENDERED_WITH_ORIGINAL_ANIMATION_UNCHANGED',
        'source_scene': source.relative_to(ROOT).as_posix(),
        'review_scene': review.relative_to(ROOT).as_posix(),
        'camera_follows_root_translation': True,
        'original_bone_animation_modified': False,
        'review_frames': frames,
        'root_start_Blender_m': points[0].tolist(),
        'root_end_Blender_m': points[-1].tolist(),
        'root_endpoint_travel_m': float(np.linalg.norm(points[-1] - points[0])),
        'video_rendered': args.video,
        'runtime_tested': False,
    })


if __name__ == '__main__':
    main()

