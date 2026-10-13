"""Export only original RE8 motion/geometry to glTF; no target animation writer."""
import argparse
from collections import Counter
import hashlib
import io
import json
import struct
import numpy as np
from PIL import Image
from common import ROOT, confined, reader, write_json
from analyze_assets import parsed_mesh
from animation_math import compose, decompose, sample, hierarchy_globals, motion_globals, reference_samples


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def validate_decoded(d, config):
    for key, expected in [('name',config['clip']),('resource_sha256',config['sha256']),
                          ('offset',config['offset']),('fps',config['fps']),('frame_count',config['frames']),
                          ('rest_bone_count',config['rest_bones']),('bone_track_count',config['bone_tracks'])]:
        if d[key]!=expected: raise ValueError(f"Source identity mismatch: {key}")
    names=[b['name'] for b in d['bones']]; hashes=[b['hash'] for b in d['bones']]
    if len(names)!=len(set(names)) or len(hashes)!=len(set(hashes)): raise ValueError('Duplicate MOT bones')
    if len(d['tracks'])!=d['bone_track_count']: raise ValueError('Missing tracks')
    seen=set(); modes=Counter(); channels=Counter(); keys=0
    for t in d['tracks']:
        if t['bone'] in seen or t['bone'] not in names or hashes[names.index(t['bone'])]!=t['hash']:
            raise ValueError('Invalid track association')
        seen.add(t['bone'])
        if t['weight']!=1: raise ValueError('Weighted layer blending is outside this decoder preview')
        for kind,flag,size in [('translation',1,3),('rotation',2,4),('scale',4,3)]:
            c=t[kind]
            if bool(c)!=bool(t['flags']&flag): raise ValueError('Channel flags disagree')
            if not c: continue
            values=np.asarray(c['values'])
            if values.shape!=(c['key_count'],size) or not np.isfinite(values).all(): raise ValueError('Invalid channel values')
            times=c['frames']
            if times is None:
                if len(values)!=1: raise ValueError('Unsupported implicit timing')
            elif len(times)!=len(values) or any(b<=a for a,b in zip(times,times[1:])) or min(times)<0 or max(times)>d['frame_count']:
                raise ValueError('Invalid sparse frame timing')
            if kind=='rotation' and np.max(np.abs(np.linalg.norm(values,axis=1)-1))>1e-5: raise ValueError('Invalid quaternion')
            modes[(kind,c['compression_hex'],c['compression_mode'])]+=1; channels[kind]+=1; keys+=len(values)
    if d['property_track_count'] or d['vertex_animation_present'] or d['property_tree_present']:
        raise ValueError('Additional authored animation channels require explicit support')
    motion_globals(d,0)  # Validate actual parent chain, not only names.
    return {'channels':dict(channels),'decoded_keys':keys,'compression_modes':[{'channel':k[0],'hex':k[1],'mode':k[2],'track_count':v,'decoded':True} for k,v in sorted(modes.items())],
            'unsupported_transform_channels':[], 'non_transform_behavior_metadata':d['behavior_clips'],
            'runtime_behavior_events_ik_physics_executed':False}


class GLB:
    def __init__(self):
        self.data=bytearray(); self.doc={'asset':{'version':'2.0','generator':'Bela source-animation reconstruction v0.2.0'},
            'buffers':[{'byteLength':0}],'bufferViews':[],'accessors':[],'nodes':[],'meshes':[],
            'skins':[],'materials':[],'images':[],'textures':[],'samplers':[{'magFilter':9729,'minFilter':9729}],
            'animations':[],'scenes':[{'nodes':[]}],'scene':0}
    def view(self,data):
        self.data.extend(b'\0'*((-len(self.data))%4)); offset=len(self.data); self.data.extend(data)
        i=len(self.doc['bufferViews']); self.doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(data)})
        return i
    def accessor(self,values,kind,position=False):
        a=np.ascontiguousarray(values); c={('f',4):5126,('u',2):5123,('u',4):5125,('u',1):5121}[(a.dtype.kind,a.dtype.itemsize)]
        record={'bufferView':self.view(a.tobytes()),'componentType':c,'count':len(a),'type':kind}
        if position or kind=='SCALAR': record.update(min=a.min(axis=0).reshape(-1).tolist(),max=a.max(axis=0).reshape(-1).tolist())
        i=len(self.doc['accessors']); self.doc['accessors'].append(record); return i
    def write(self,path):
        self.doc['buffers'][0]['byteLength']=len(self.data)
        header=json.dumps(self.doc,separators=(',',':')).encode(); header+=b' '*((-len(header))%4)
        data=bytes(self.data)+b'\0'*((-len(self.data))%4)
        payload=struct.pack('<III',0x46546c67,2,12+8+len(header)+8+len(data))+struct.pack('<II',len(header),0x4e4f534a)+header+struct.pack('<II',len(data),0x004e4942)+data
        if path.exists(): raise ValueError('Preserve previous GLB; use a fresh output name')
        path.write_bytes(payload)


def original_skeleton(meshes,decoded):
    bones={}; discrepancies=[]
    for part,mesh in meshes:
        for b in mesh.skeleton.boneList:
            parent=mesh.skeleton.boneList[b.parentIndex].boneName if b.parentIndex>=0 else None
            world=np.asarray(b.worldMatrix.matrix,dtype=float).T
            record={'name':b.boneName,'parent':parent,'local':np.asarray(b.localMatrix.matrix,dtype=float).T,
                    'world':world,'inverse':np.asarray(b.inverseMatrix.matrix,dtype=float).T}
            if b.boneName in bones:
                old=bones[b.boneName]
                residual=float(np.max(np.abs(old['world']-world)))
                if old['parent']!=parent or residual>1e-5: raise ValueError('Original component bind definitions disagree')
                discrepancies.append(residual)
            else: bones[b.boneName]=record
    missing=[]; rest_differences=[]
    for b in decoded['bones']:
        if b['name'] in bones:
            old=bones[b['name']]
            if old['parent']!=b['parent']: raise ValueError('MOT/mesh hierarchy needs an explicit adapter')
            rest_differences.append({'bone':b['name'],'translation_difference_m':float(np.linalg.norm(old['local'][:3,3]-b['translation']))})
        else:
            missing.append(b['name']); local=compose(b['translation'],b['quaternion_xyzw'])
            bones[b['name']]={'name':b['name'],'parent':b['parent'],'local':local}
    names=list(bones); parents=[names.index(bones[n]['parent']) if bones[n]['parent'] else -1 for n in names]
    globals=hierarchy_globals([bones[n]['local'] for n in names],parents)
    for i,n in enumerate(names):
        if 'inverse' not in bones[n]: bones[n]['inverse']=np.linalg.inv(globals[i])
        if not np.allclose(globals[i] @ bones[n]['inverse'],np.eye(4),atol=2e-5): raise ValueError('Bind/inverse inconsistency')
    return bones,{'assembled_original_rig_bones':len(names),'missing_mesh_helpers_added_from_MOT':missing,
        'common_parent_discrepancies':[], 'maximum_component_bind_residual':max(discrepancies,default=0),
        'largest_MOT_rest_vs_mesh_bind_translation_differences':sorted(rest_differences,key=lambda x:-x['translation_difference_m'])[:12],
        'binding_rule':'Original mesh inverse binds retained. MOT rest TRS replaces matching locals during animation; authored tracks replace individual components absolutely, as in the pinned source editor.'}


def texture_previews():
    report=json.loads((ROOT/'reports/material_build.json').read_text()); result={}
    for row in report['textures']:
        result[row['source'].lower()]=ROOT/row['preview']
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--decoded',required=True); parser.add_argument('--output',required=True)
    parser.add_argument('--config',default='config/source_idle_v0.2.0.json');parser.add_argument('--report-name',default='source_idle')
    args=parser.parse_args(); config=json.loads(confined(ROOT,args.config).read_text())
    if not args.report_name.replace('_','').isalnum():raise ValueError('Invalid report name')
    decoded_path=confined(ROOT,args.decoded); d=json.loads(decoded_path.read_text()); audit=validate_decoded(d,config)
    if sha(ROOT/config['source'])!=config['sha256']: raise ValueError('Original MOTLIST changed')
    output=confined(ROOT/'build',args.output.removeprefix('build/')); output.mkdir(parents=True,exist_ok=True)
    meshes=[(path,parsed_mesh(ROOT/path)[1]) for path in config['source_meshes']]
    bones,skel=original_skeleton(meshes,d); names=list(bones); glb=GLB(); doc=glb.doc
    for name,b in bones.items():
        t,q,s=decompose(b['local']); node={'name':name,'translation':t.tolist(),'rotation':q.tolist(),'scale':s.tolist()}
        children=[i for i,n in enumerate(names) if bones[n]['parent']==name]
        if children: node['children']=children
        doc['nodes'].append(node)
    doc['scenes'][0]['nodes']=[i for i,n in enumerate(names) if bones[n]['parent'] is None]
    inverse=np.asarray([bones[n]['inverse'] for n in names],dtype='<f4').swapaxes(-1,-2).reshape(-1,16)
    doc['skins'].append({'name':'Original_Bela_bind_skin','joints':list(range(len(names))),
        'inverseBindMatrices':glb.accessor(inverse,'MAT4'),'skeleton':names.index('root')})
    previews=texture_previews(); mdfreader=reader('RE-Mesh-Editor','remesh','modules.mdf.file_re_mdf')
    used_materials={}; vertex_count=0; triangles=0; influenced=set(); source_inputs=[]
    for part,mesh in meshes:
        source_inputs.append({'path':part,'sha256':sha(ROOT/part)})
        mdf_path=next((ROOT/part).parent.glob((ROOT/part).name.split('.mesh')[0]+'*.mdf2.*'))
        materials=mdfreader.readMDF(str(mdf_path)).materialList
        for mat in materials:
            if mat.materialName in used_materials: continue
            material={'name':mat.materialName,'doubleSided':True,'pbrMetallicRoughness':{'metallicFactor':0,'roughnessFactor':0.65}}
            bindings={t.textureType:t.texturePath.lower() for t in mat.textureList}
            path=previews.get(bindings.get('BaseDielectricMap',bindings.get('BaseShiftMap')))
            if path and path.exists():
                im=Image.open(path).convert('RGBA')
                if any(w in mat.materialName.lower() for w in ['hair','eyelash','eyebrow','eyeao','cloak']):
                    mask=previews.get(bindings.get('AlphaTranslucentOcclusionCavityMap'))
                    if mask and mask.exists():
                        alpha=Image.open(mask).convert('RGBA').getchannel('R').resize(im.size); im.putalpha(alpha)
                        material.update(alphaMode='MASK',alphaCutoff=0.35)
                bio=io.BytesIO(); im.save(bio,format='PNG')
                image=len(doc['images']); doc['images'].append({'bufferView':glb.view(bio.getvalue()),'mimeType':'image/png'})
                texture=len(doc['textures']); doc['textures'].append({'source':image,'sampler':0})
                material['pbrMetallicRoughness']['baseColorTexture']={'index':texture}
            if 'eyewet' in mat.materialName.lower(): material.update(alphaMode='BLEND'); material['pbrMetallicRoughness']['baseColorFactor']=[1,1,1,.05]
            used_materials[mat.materialName]=len(doc['materials']); doc['materials'].append(material)
        primitives=[]
        for g in mesh.mainMeshLODList[0].visconGroupList:
            for sub in g.subMeshList:
                p=np.asarray(sub.vertexPosList,dtype='<f4'); uv=np.asarray(sub.uvList,dtype='<f4').copy(); uv[:,1]=1-uv[:,1]
                w=np.asarray(sub.weightList,dtype='<f4'); original_indices=np.asarray(sub.weightIndicesList)
                palette=np.asarray([names.index(n) for n in mesh.skeleton.weightedBones],dtype='<u2')
                joints=palette[original_indices]; sums=w.sum(axis=1)
                if np.any(sums<=0) or not np.isfinite(w).all() or np.any(w<0): raise ValueError('Invalid original skin weights')
                w=w/sums[:,None]; influenced.update(names[i] for i in np.unique(joints[w>0]))
                attrs={'POSITION':glb.accessor(p,'VEC3',True),'NORMAL':glb.accessor(np.asarray(sub.normalList,dtype='<f4'),'VEC3'),
                    'TEXCOORD_0':glb.accessor(uv,'VEC2'),'JOINTS_0':glb.accessor(joints[:,:4],'VEC4'),
                    'WEIGHTS_0':glb.accessor(np.ascontiguousarray(w[:,:4]),'VEC4')}
                if w.shape[1]>4 and np.any(w[:,4:]>0):
                    attrs['JOINTS_1']=glb.accessor(joints[:,4:8],'VEC4'); attrs['WEIGHTS_1']=glb.accessor(np.ascontiguousarray(w[:,4:8]),'VEC4')
                primitives.append({'attributes':attrs,'indices':glb.accessor(np.asarray(sub.faceList,dtype='<u4').reshape(-1),'SCALAR'),
                    'material':used_materials[mesh.materialNameList[sub.materialIndex]]})
                vertex_count+=len(p); triangles+=len(sub.faceList)
        index=len(doc['meshes']); doc['meshes'].append({'name':(ROOT/part).name,'primitives':primitives})
        doc['scenes'][0]['nodes'].append(len(doc['nodes'])); doc['nodes'].append({'name':'Source_'+(ROOT/part).stem,'mesh':index,'skin':0})
    tracks={t['bone']:t for t in d['tracks']}; animation={'name':d['name'],'samplers':[],'channels':[]}
    dense=np.arange(config['frames']+1,dtype=float); times=(dense/config['fps']).astype('<f4')
    time_accessor=glb.accessor(times,'SCALAR'); constant_time=glb.accessor(np.asarray([0],dtype='<f4'),'SCALAR')
    rest_channels=0
    for b in d['bones']:
        c=tracks.get(b['name'],{});
        for kind,fallback,typ in [('translation',b['translation'],'VEC3'),('rotation',b['quaternion_xyzw'],'VEC4'),('scale',[1,1,1],'VEC3')]:
            channel=c.get(kind)
            if kind=='scale' and not channel: continue
            if channel is None: rest_channels+=1
            constant=channel is None or channel['constant']
            values=np.asarray([sample(channel,f,kind=='rotation') if channel else fallback for f in ([0] if constant else dense)],dtype='<f4')
            if kind=='rotation':
                for i in range(1,len(values)):
                    if np.dot(values[i-1],values[i])<0: values[i]*=-1
            a=glb.accessor(values,typ); sampler=len(animation['samplers'])
            animation['samplers'].append({'input':constant_time if constant else time_accessor,'output':a,'interpolation':'LINEAR'})
            animation['channels'].append({'sampler':sampler,'target':{'node':names.index(b['name']),'path':kind}})
    doc['animations'].append(animation); doc['extras']={'source_sha256':config['sha256'],'source_fps':config['fps'],'source_duration_seconds':config['frames']/config['fps'],
        'native_animated_bones':d['bone_track_count'],'native_transform_channels':sum(audit['channels'].values()),'rest_fallback_channels':rest_channels,
        'limits':'Authored body channels only; enemy events, runtime look-at/IK, GPU cloth, facial morphs and engine shaders are not reproduced.'}
    glb_path=output/'source_idle.glb'; glb.write(glb_path)
    refs=decoded_path.with_suffix('.reference.bin'); frames,reference=reference_samples(refs)
    errors=[np.max(np.abs(motion_globals(d,float(f))-expected)) for f,expected in zip(frames,reference)]
    loop0=motion_globals(d,0); loop1=motion_globals(d,config['frames'])
    audit.update(source=config['source'],source_sha256=config['sha256'],clip=config['clip'],fps=config['fps'],duration_seconds=config['frames']/config['fps'],
        rest_bones=d['rest_bone_count'],animated_bones=d['bone_track_count'],skeleton=skel,geometry={'vertices':vertex_count,'triangles':triangles,'weighted_bone_count':len(influenced),
        'direct_animated_weighted_bones':sorted(influenced & set(tracks)),'animated_helpers_without_direct_vertex_weights':sorted(set(tracks)-influenced)},
        source_inputs=source_inputs,excluded_auxiliary_geometry=config.get('excluded_auxiliary_geometry',[]),glb={'path':glb_path.relative_to(ROOT).as_posix(),'sha256':sha(glb_path),'animation_channels':len(animation['channels']),
        'rest_fallback_channels':rest_channels,'keys_baked_at_60fps':True,'original_inverse_bind_matrices_preserved':True},
        python_vs_upstream_CSharp_reference={'sample_count':len(frames),'sampling_fps':120,'max_world_matrix_component_error':float(max(errors)),
            'source':'Pinned Animator.FindFrames compiled verbatim; System.Numerics absolute-local TRS, Vector3.Lerp and Quaternion.Lerp. Headless sampling, not a running RE8 game.'},
        loop={'max_joint_position_difference_m':float(np.max(np.linalg.norm(loop1[:,:3,3]-loop0[:,:3,3],axis=1))),
              'max_matrix_component_difference':float(np.max(np.abs(loop1-loop0)))},
        status='DECODE_AND_SOURCE_EDITOR_REFERENCE_PASSED_BLENDER_PENDING',runtime_tested=False)
    if max(errors)>1e-5: raise ValueError('Independent source-editor sampler disagreement')
    write_json(ROOT/f'reports/animation_dev/{args.report_name}_decode.json',audit)
    print(f"Exported {glb_path.name}: {len(bones)} assembled original bones, {len(animation['channels'])} channels; reference maximum {max(errors):.3g}")


if __name__=='__main__': main()

