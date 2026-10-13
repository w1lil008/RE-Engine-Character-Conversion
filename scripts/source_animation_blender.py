"""Import/measure the original idle GLB, save editable scene and review renders."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import argparse
import json
import math
import numpy as np
import bpy
from mathutils import Matrix, Vector
from common import ROOT, confined, write_json
from animation_math import motion_globals
from glb_read import load, sample_globals, accessor


def aim(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='build/animation_v0.2.0/source_idle_validated');p.add_argument('--video',action='store_true')
    p.add_argument('--glb',default='source_idle.glb');p.add_argument('--validate-only',action='store_true')
    p.add_argument('--report-name',default='source_idle')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=confined(ROOT,args.output); path=confined(out,args.glb); d=json.loads((out/'decoded_reference.json').read_text())
    if not args.report_name.replace('_','').isalnum():raise ValueError('Invalid report name')
    duration=int(d['frame_count']);fps=d['fps']
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.fps=fps;scene.render.fps_base=1
    bpy.ops.import_scene.gltf(filepath=str(path),merge_vertices=False)
    rig=next(o for o in scene.objects if o.type=='ARMATURE'); rig.name='Original_Bela_Source_Rig'
    doc,data=load(out/'source_idle.glb'); names=[n['name'] for n in doc['nodes']]; indices={n:i for i,n in enumerate(names)}
    motion_names=[b['name'] for b in d['bones']]
    if not all(n in rig.pose.bones for n in motion_names): raise ValueError('Blender omitted original animation bones')
    action=rig.animation_data.action
    if not np.allclose(action.frame_range,[0,duration],atol=.001): raise ValueError(f'Unexpected imported timing: {tuple(action.frame_range)}')
    axis=Matrix.Rotation(math.pi/2,4,'X'); rotate=np.asarray(axis)
    bind=sample_globals(doc,data,None); corrected={}
    for name in motion_names:
        b=np.asarray(rig.matrix_world @ rig.data.bones[name].matrix_local)
        corrected[name]=np.linalg.inv(b) @ rotate @ bind[indices[name]]
    frames=np.arange(0,duration+.001,.5); max_matrix=0.;max_pos=0.; worst=None; gltf_error=0.
    for frame in frames:
        scene.frame_set(int(frame),subframe=float(frame%1));bpy.context.view_layer.update()
        expected=rotate @ motion_globals(d,float(frame))
        expected_glb=rotate @ sample_globals(doc,data,float(frame)/fps)[[indices[n] for n in motion_names]]
        gltf_error=max(gltf_error,float(np.max(np.abs(expected_glb-expected))))
        for i,name in enumerate(motion_names):
            actual=np.asarray(rig.matrix_world @ rig.pose.bones[name].matrix) @ corrected[name]
            e=float(np.max(np.abs(actual-expected[i])));pe=float(np.linalg.norm(actual[:3,3]-expected[i,:3,3]))
            if e>max_matrix:max_matrix=e;worst={'bone':name,'frame':float(frame)}
            max_pos=max(max_pos,pe)
    finite=True;bounds=[]; deps=bpy.context.evaluated_depsgraph_get()
    for frame in sorted(set(int(duration*x) for x in [0,.25,.5,.75,1])):
        scene.frame_set(frame);bpy.context.view_layer.update();points=[]
        for obj in [o for o in scene.objects if o.type=='MESH']:
            mesh=obj.evaluated_get(deps).to_mesh();v=np.empty(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',v)
            v=v.reshape(-1,3);finite=finite and bool(np.isfinite(v).all());points.append(v)
            obj.evaluated_get(deps).to_mesh_clear()
        pts=np.concatenate(points);bounds.append({'frame':frame,'min':pts.min(axis=0).tolist(),'max':pts.max(axis=0).tolist()})
    report={'status':'PASSED' if max_matrix<2e-4 and max_pos<.0002 and finite else 'FAILED',
        'source_animated_bones':d['bone_track_count'],'imported_MOT_bones':len(motion_names),'assembled_rig_bones':len(rig.data.bones),
        'fps':fps,'frame_range':list(action.frame_range),'samples':len(frames),'sampling_fps':fps*2,
        'maximum_Blender_world_matrix_component_error':max_matrix,'maximum_Blender_joint_position_error_m':max_pos,
        'maximum_glTF_sample_matrix_error':gltf_error,'worst':worst,'finite_evaluated_geometry':finite,'evaluated_bounds':bounds,
        'comparison':'Blender bone orientation corrections calibrated from original glTF bind only; compared against source-editor absolute-local sampling at all integer and half frames.',
        'runtime_tested':False,'engine_physics_events_facial_morphs_not_reproduced':True}
    report['input_glb']=path.relative_to(ROOT).as_posix()
    write_json(ROOT/f"reports/animation_dev/{args.report_name}_{'roundtrip' if args.validate_only else 'blender'}.json",report)
    if report['status']!='PASSED': raise ValueError(f'Blender animation reconstruction mismatch: {report}')
    if args.validate_only:
        print(f'Blender export/reimport and {len(frames)} source-reference comparisons passed');return
    roundtrip=out/'source_idle_blender_roundtrip.glb'
    if not roundtrip.exists():
        scene.frame_start=0;scene.frame_end=duration;scene.frame_set(0)
        bpy.ops.export_scene.gltf(filepath=str(roundtrip),export_format='GLB',export_animations=True,
            export_skins=True,export_all_influences=True,export_force_sampling=True,export_frame_range=False)
    scene.frame_start=0;scene.frame_end=duration-1;scene.render.engine='BLENDER_EEVEE_NEXT'
    scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.world.color=(.055,.055,.055);scene.view_settings.view_transform='AgX'
    bpy.ops.object.camera_add(location=(2.4,-5,2.1));camera=bpy.context.object;camera.data.type='ORTHO';camera.data.ortho_scale=2.1
    aim(camera,(0,0,.95));scene.camera=camera
    for name,position,power in [('Key',(3,-3,4),800),('Fill',(-3,-2,3),550),('Rim',(1,3,4),650)]:
        bpy.ops.object.light_add(type='AREA',location=position);light=bpy.context.object;light.name=name;light.data.energy=power;light.data.shape='DISK';light.data.size=3;aim(light,(0,0,1))
    scene['SOURCE']='Original RE8 authored motion, not retargeted or runtime tested'
    scene['LIMITS']='No native GPU cloth, procedural look-at/IK, facial morphs, enemy events or engine shaders'
    scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(out/'source_idle.blend'))
    for label,frame in [('start',0),('middle',duration//2),('end',duration)]:
        scene.frame_set(frame);scene.render.filepath=str(out/f'review_{label}.png');bpy.ops.render.render(write_still=True)
    if args.video:
        # Full 60 FPS loop in inexpensive solid shading; textured EEVEE frames above.
        scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=480;scene.render.resolution_y=600
        scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=False
        for mat in bpy.data.materials:
            image=next((n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image),None) if mat.use_nodes else None
            if image:
                pix=np.asarray(image.pixels[:]).reshape(-1,4)[::97];colour=np.mean(pix[pix[:,3]>.5,:3],axis=0) if np.any(pix[:,3]>.5) else np.array([.1,.1,.1])
                mat.diffuse_color=(*np.clip(colour,0,1),1)
        scene.render.image_settings.file_format='FFMPEG';scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
        scene.render.ffmpeg.constant_rate_factor='HIGH';scene.render.filepath=str(out/'source_idle_60fps.mp4')
        bpy.ops.render.render(animation=True)
    print(f'Original-source Blender import and {len(frames)} sample comparisons passed')


if __name__=='__main__':main()

