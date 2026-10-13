"""Milestone C: lossless original roundtrip, native body encoding and reimport.

Only new files under build/reports are written. No installation or registration.
"""
import argparse
import collections
import json
import sys
import numpy as np
from common import ROOT, confined, write_json
from source_animation_workflow import sha, run, prepare_reference
from native_animation_protection import protect
from native_mot import lossless_decode, lossless_encode, encode_mot, encode_single_list, decode_float_mot, read
from glb_read import load, accessor, sample_globals
from animation_math import compose, decompose, sample, hierarchy_globals

SOURCE = 'assets/extracted/re9/natives/stm/animation/ch/ch02/ch0200/motlist/ch0200_generalm.motlist.1047'
SOURCE_SHA = '41e875ab1fb08a4347dad2f4d3ea296de2cf1b7e0df205161057d457eaddcf20'
REFERENCE = ROOT / 'build/animation_v0.2.0/retarget_idle'

def summarize_difference(a,b):
    counts=collections.Counter();examples=[];numeric_max=0
    def walk(x,y,path):
        nonlocal numeric_max
        if isinstance(x,(int,float)) and isinstance(y,(int,float)):
            if x!=y:
                numeric_max=max(numeric_max,abs(x-y)); counts['numeric']+=1
                if len(examples)<12:examples.append({'path':path,'original':x,'encoded':y})
        elif type(x)!=type(y):counts['type']+=1
        elif isinstance(x,dict):
            if x.keys()!=y.keys():counts['keys']+=1
            for k in x.keys()&y.keys():walk(x[k],y[k],path+'/'+k)
        elif isinstance(x,list):
            if len(x)!=len(y):counts['length']+=1
            for i,(u,v) in enumerate(zip(x,y)):walk(u,v,path+'/'+str(i))
        elif x!=y:counts['other']+=1
    walk(a,b,'')
    return {'equal':not bool(counts),'differences':dict(counts),'maximum_numeric_difference':numeric_max,'examples':examples}

def compare_original_idle(original,encoded):
    # Known metadata must remain identical; relocation offsets and file size
    # are layout, not state metadata. All decoded channel values are compared.
    a=json.loads(json.dumps(original));b=json.loads(json.dumps(encoded))
    maximum=0;changed=0
    for ta,tb in zip(a['tracks'],b['tracks']):
        for kind in ('translation','rotation','scale'):
            ca,cb=ta[kind],tb[kind]
            if ca is None or cb is None:continue
            va=np.asarray(ca.pop('values'));vb=np.asarray(cb.pop('values'))
            if va.shape!=vb.shape:raise ValueError('Untouched original channel length changed')
            maximum=max(maximum,float(np.abs(va-vb).max()));changed+=int(np.count_nonzero(va!=vb))
    metadata=summarize_difference(a,b)
    if not metadata['equal'] or maximum>1e-6:raise ValueError('Original idle decoded-float roundtrip does not preserve animation/metadata')
    return {'status':'PASSED','all_known_metadata_equal':True,'all_tracks_modes_flags_times_preserved':True,
        'maximum_decoded_component_difference':maximum,'changed_float_components':changed,'component_tolerance':1e-6,
        'scope':'Actual ReeLib decode/encode/decode with recompression. Complete original bank opaque data additionally protected by the byte-identical partition roundtrip.'}

def sample_target(native,rig,frame):
    by={b['name']:i for i,b in enumerate(rig)}
    local=np.asarray([b['local'] for b in rig],dtype=float).copy()
    tracks={t['bone']:t for t in native['tracks']}
    for b in native['bones']:
        if b['name'] not in by:continue
        t=tracks.get(b['name'],{})
        translation=sample(t['translation'],frame) if t.get('translation') else b['translation']
        rotation=sample(t['rotation'],frame,True) if t.get('rotation') else b['rotation']
        scale=sample(t['scale'],frame) if t.get('scale') else [1,1,1]
        local[by[b['name']]]=compose(translation,rotation,scale)
    parents=[by[b['parent']] if b['parent'] is not None else -1 for b in rig]
    return local,hierarchy_globals(local,parents)

def metrics(points):
    return {'axis_range_m':np.ptp(points,axis=0).tolist(),
        'horizontal_range_diagonal_m':float(np.linalg.norm(np.ptp(points[:,[0,2]],axis=0))),
        'net_loop_translation_m':float(np.linalg.norm(points[-1]-points[0]))}

def rotation_angles(a,b):
    # Mesh-bind matrices contain float32 residual scale. Project each basis to
    # SO(3); a trace comparison of unprojected bases reports a false ~.02 degrees.
    ua,_,va=np.linalg.svd(a);ub,_,vb=np.linalg.svd(b)
    ra=ua@va;rb=ub@vb;relative=np.swapaxes(ra,-1,-2)@rb
    sine=np.linalg.norm(np.stack((relative[:,2,1]-relative[:,1,2],relative[:,0,2]-relative[:,2,0],relative[:,1,0]-relative[:,0,1]),axis=1),axis=1)/2
    cosine=(np.trace(relative,axis1=1,axis2=2)-1)/2
    return np.degrees(np.arctan2(sine,cosine))

def validate(native,independent,rig,doc,binary):
    if native['name']!=independent['name'] or native['fps']!=independent['fps']:raise ValueError('Independent header mismatch')
    if len(native['bones'])!=len(independent['bones']) or len(native['tracks'])!=len(independent['tracks']):raise ValueError('Independent count mismatch')
    key_error=0
    for a,b in zip(native['bones'],independent['bones']):
        for k in ('name','parent','index','hash','translation','rotation','attributes1','attributes2'):
            if a[k]!=b[k]:
                if k in ('translation','rotation'):
                    if not np.allclose(a[k],b[k],rtol=0,atol=1e-7):raise ValueError('Independent rest mismatch')
                else:raise ValueError('Independent binding mismatch')
    for a,b in zip(native['tracks'],independent['tracks']):
        for k in ('bone','index','hash','flags','weight'):
            if a[k]!=b[k]:raise ValueError('Independent track mismatch')
        for kind in ('translation','rotation','scale'):
            if kind in a:
                if b[kind] is None or a[kind]['flags']!=b[kind]['flags'] or a[kind]['frames']!=b[kind]['frames']:raise ValueError('Independent timing/encoding mismatch')
                key_error=max(key_error,float(np.abs(np.asarray(a[kind]['values'])-b[kind]['values']).max()))
            elif b[kind] is not None:raise ValueError('Unexpected independent channel')
    if key_error>1e-7:raise ValueError('Independent decoder discrepancy')
    names=[b['name'] for b in rig];mapped={t['bone'] for t in native['tracks']}
    protected=[i for i,n in enumerate(names) if n not in mapped]
    bind=np.asarray([b['local'] for b in rig]);npz=np.load(REFERENCE/'retarget_matrices.npz')
    world_error=position_error=rotation_error=local_error=protected_error=translation_error=length_error=0
    poses=[];local_poses=[];worst=None
    for frame in np.arange(0,300.01,.5):
        local,world=sample_target(native,rig,float(frame));expected=sample_globals(doc,binary,frame/60)[:611]
        error=np.linalg.norm(world[:,:3,3]-expected[:,:3,3],axis=1)
        if error.max()>position_error:position_error=float(error.max());worst={'bone':names[int(error.argmax())],'frame':float(frame)}
        world_error=max(world_error,float(np.abs(world-expected).max()))
        angles=rotation_angles(world[:,:3,:3],expected[:,:3,:3])
        rotation_error=max(rotation_error,float(angles.max()))
        protected_error=max(protected_error,float(np.abs(local[protected]-bind[protected]).max()))
        translation_error=max(translation_error,float(np.abs(local[1:,:3,3]-bind[1:,:3,3]).max()))
        length_error=max(length_error,float(np.abs(np.linalg.norm(local[1:,:3,3],axis=1)-np.linalg.norm(bind[1:,:3,3],axis=1)).max()))
        if frame%1==0:local_error=max(local_error,float(np.abs(local-npz['locals'][int(frame)]).max()))
        poses.append(world);local_poses.append(local)
    poses=np.asarray(poses)
    norm_error=max(float(np.abs(np.linalg.norm(np.asarray(t['rotation']['values']),axis=1)-1).max()) for t in native['tracks'] if 'rotation' in t)
    signed_dots=[float(np.min(np.sum(np.asarray(t['rotation']['values'])[:-1]*np.asarray(t['rotation']['values'])[1:],axis=1))) for t in native['tracks'] if 'rotation' in t]
    dots=[float(np.min(np.abs(np.sum(np.asarray(t['rotation']['values'])[:-1]*np.asarray(t['rotation']['values'])[1:],axis=1)))) for t in native['tracks'] if 'rotation' in t]
    loop=np.linalg.norm(poses[-1,:,:3,3]-poses[0,:,:3,3],axis=1)
    loop_angles=rotation_angles(poses[0,:,:3,:3],poses[-1,:,:3,:3])
    report={'status':'PASSED','samples':601,'sampling_fps':120,'target_bones':611,'native_rest_bones':len(native['bones']),
        'body_channels':sum(sum(k in t for k in ('rotation','translation','scale')) for t in native['tracks']),
        'independent_decoders_maximum_key_component_difference':key_error,
        'maximum_joint_position_error_m':position_error,'worst_joint_sample':worst,
        'maximum_world_matrix_component_error':world_error,'maximum_world_rotation_error_degrees':rotation_error,
        'maximum_local_matrix_error_vs_accepted_npz':local_error,
        'maximum_unmapped_target_local_matrix_error':protected_error,
        'maximum_nonroot_translation_error_m':translation_error,'maximum_bone_length_error_m':length_error,
        'maximum_quaternion_norm_error':norm_error,'minimum_adjacent_absolute_quaternion_dot':min(dots),
        'minimum_adjacent_signed_quaternion_dot':min(signed_dots),
        'root':metrics(poses[:,names.index('root'),:3,3]),
        'feet':{n:metrics(poses[:,names.index(n),:3,3]) for n in ('L_Leg_Ankle','R_Leg_Ankle','L_Leg_Toes','R_Leg_Toes')},
        'loop':{'maximum_joint_endpoint_distance_m':float(loop.max()),'maximum_rotation_endpoint_degrees':float(loop_angles.max())},
        'tolerances':{'joint_position_m':0.00005,'world_rotation_degrees':0.01,'protected_local_matrix':1e-6,'quaternion_norm':1e-6},
        'interpolation_scope':'Native reader/editor NLERP compared with accepted GLB SLERP at every key and half frame. Actual RE9 interpolation awaits runtime proof.',
        'runtime_tested':False,'registered_or_installed':False}
    if position_error>5e-5 or rotation_error>.01 or protected_error>1e-6 or norm_error>1e-6 or translation_error>1e-7 or min(signed_dots)<.999:
        report['status']='FAILED'
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    out=confined(ROOT/'build',args.output.removeprefix('build/'))
    if out.exists():raise ValueError('Choose a fresh output; do not overwrite evidence')
    before=protect();prepare_reference();source=ROOT/SOURCE
    if sha(source)!=SOURCE_SHA:raise ValueError('Original Grace source changed')
    out.mkdir(parents=True)
    project=ROOT/'scripts/animation/ReeNative/ReeNative.csproj'
    run([ROOT/'tools/dotnet10/dotnet.exe','restore',project,'--locked-mode','--source','https://api.nuget.org/v3/index.json','--packages',ROOT/'tools/nuget','--verbosity','quiet'],out/'restore.log')
    run([ROOT/'tools/dotnet10/dotnet.exe','build',project,'-c','Release','--no-restore','--verbosity','quiet'],out/'compile.log')
    bridge=[ROOT/'tools/dotnet8/dotnet.exe',ROOT/'scripts/animation/ReeNative/bin/Release/net8.0/ReeNative.dll']
    run(bridge+['decode-list',source,out/'original.json'],out/'original_decode.log')
    run(bridge+['upstream-roundtrip',source,out/'upstream.motlist.1047'],out/'upstream_encode.log')
    run(bridge+['decode-list',out/'upstream.motlist.1047',out/'upstream.json'],out/'upstream_decode.log')
    original=json.loads((out/'original.json').read_text());upstream=json.loads((out/'upstream.json').read_text())
    # Also test a true decoded-float encode on the original, unedited Grace idle.
    # This first slot has its own 70-bone table, so the upstream list-wide bone
    # count normalization problem does not apply to this standalone resource.
    raw_source=source.read_bytes();pointer_table,=read(raw_source,'<Q',16);slot_count,=read(raw_source,'<I',56)
    offsets=read(raw_source,'<'+'Q'*slot_count,pointer_table)
    first=offsets[0];following=min(o for o in offsets if o>first)
    (out/'original_grace_idle.mot.983').write_bytes(raw_source[first:following])
    run(bridge+['decode-mot',out/'original_grace_idle.mot.983',out/'original_grace_idle.json'],out/'grace_idle_decode.log')
    run(bridge+['upstream-mot-roundtrip',out/'original_grace_idle.mot.983',out/'roundtrip_grace_idle.mot.983'],out/'grace_idle_encode.log')
    run(bridge+['decode-mot',out/'roundtrip_grace_idle.mot.983',out/'roundtrip_grace_idle.json'],out/'grace_idle_redecode.log')
    original_idle=json.loads((out/'original_grace_idle.json').read_text());encoded_idle=json.loads((out/'roundtrip_grace_idle.json').read_text())
    if original_idle!=original['motions'][0]:raise ValueError('Extracted original idle differs from embedded decode')
    idle_float_roundtrip=compare_original_idle(original_idle,encoded_idle)
    document=lossless_decode(source.read_bytes());write_json(out/'original_preservation_document.json',document)
    encoded=lossless_encode(json.loads((out/'original_preservation_document.json').read_text()))
    (out/'unchanged.motlist.1047').write_bytes(encoded)
    run(bridge+['decode-list',out/'unchanged.motlist.1047',out/'unchanged.json'],out/'unchanged_decode.log')
    unchanged=json.loads((out/'unchanged.json').read_text())
    if encoded!=source.read_bytes() or unchanged!=original:raise ValueError('Untouched roundtrip failed; stop before authoring')
    clip0=original['motions'][0]
    channels=[t[k] for m in original['motions'] for t in m['tracks'] for k in ('translation','rotation','scale') if t[k]]
    report={'status':'PASSED','original':SOURCE,'original_sha256':SOURCE_SHA,'encoded_sha256':sha(out/'unchanged.motlist.1047'),
        'byte_identical':True,'independent_decoded_documents_equal':True,'motion_slots':len(original['indices']),'unique_motions':len(original['motions']),
        'bone_tracks':sum(len(m['tracks']) for m in original['motions']),'channels':len(channels),'keys':sum(c['count'] for c in channels),
        'encoding_modes':dict(collections.Counter(c['mode'] for c in channels)),
        'preserves':'Every byte: native headers/counts, all packed codes and time arrays, indices, IDs, switch values, masks, flags, 12 unknown index words, aliases, references, events, properties, shared rest tables and trailing data.',
        'preservation_method':'Typed control-field reserialization plus complete opaque/packed binary partitions. Not a decoded-float compression roundtrip; original codes are retained.',
        'control_segments':sum('format' in s for s in document['segments']),
        'opaque_partitions':sum('opaque_bytes_b64' in s for s in document['segments']),
        'original_idle_decoded_float_roundtrip':idle_float_roundtrip,
        'upstream_general_writer':{'status':'REJECTED_FOR_UNTOUCHED_ROUNDTRIP','difference':summarize_difference(original,upstream),
            'changed_bone_count_headers':sum(a['bone_count_header']!=b['bone_count_header'] for a,b in zip(original['motions'],upstream['motions']))}}
    write_json(out/'roundtrip_report.json',report)
    # Only now, after the complete original roundtrip gate, author the accepted retarget.
    rig=json.loads((REFERENCE/'target_rig.json').read_text());by={b['name']:b for b in rig}
    doc,binary=load(REFERENCE/'retarget_idle.glb');tracks={};dispositions=[];bones=[]
    for b in clip0['bones']:
        c=dict(b)
        if b['name'] in by:
            t,q,s=decompose(by[b['name']]['local'])
            if b['parent']!=by[b['name']]['parent'] or not np.allclose(s,1,atol=1e-6):raise ValueError('Native rest relationship cannot represent target local')
            c['translation']=t.tolist();c['rotation']=q.tolist()
            dispositions.append({'bone':b['name'],'policy':'Accepted target bind local; animated component replaced by accepted GLB track where present'})
        else:dispositions.append({'bone':b['name'],'policy':'Native animation-only helper retains original rest; no new helper tracks or controller writes'})
        bones.append(c)
    native_names={b['name'] for b in bones}
    for channel in doc['animations'][0]['channels']:
        sampler=doc['animations'][0]['samplers'][channel['sampler']];kind=channel['target']['path'];name=doc['nodes'][channel['target']['node']]['name']
        if name not in native_names or kind not in ('rotation','translation','scale') or sampler.get('interpolation')!='LINEAR':raise ValueError('Unsupported accepted channel; stop instead of dropping')
        times=accessor(doc,binary,sampler['input']).ravel()*60
        if not np.allclose(times,np.arange(301),atol=3e-5):raise ValueError('Unexpected approved animation timing')
        values=accessor(doc,binary,sampler['output']).tolist()
        tracks.setdefault(name,{'bone':name})[kind]={'frames':list(range(301)),'values':values}
    if len(doc['animations'])!=1 or len(doc['animations'][0]['channels'])!=25:raise ValueError('Unexpected approved animation channels')
    ordered=[tracks[b['name']] for b in bones if b['name'] in tracks]
    name='Bela_Approved_Idle_Offline_300f_60fps'
    mot=encode_mot(bones,ordered,name,jmap=clip0['jmap']);list_bytes=encode_single_list(mot,'Bela_Offline_Prototype_Unregistered',original['indices'][0])
    native_dir=out/'native';native_dir.mkdir()
    (native_dir/'bela_idle.mot.983').write_bytes(mot);(native_dir/'bela_idle.motlist.1047').write_bytes(list_bytes)
    parsed=decode_float_mot(mot);write_json(out/'python_reimport.json',parsed)
    pointer_table,=read(list_bytes,'<Q',16);embedded_offset,=read(list_bytes,'<Q',pointer_table)
    if decode_float_mot(list_bytes,embedded_offset,embedded=True)!=parsed:raise ValueError('Independent embedded MOT differs from standalone motion')
    run(bridge+['decode-mot',native_dir/'bela_idle.mot.983',out/'reelib_reimport.json'],out/'native_decode.log')
    run(bridge+['decode-list',native_dir/'bela_idle.motlist.1047',out/'reelib_list_reimport.json'],out/'native_list_decode.log')
    independent=json.loads((out/'reelib_reimport.json').read_text())
    native_list=json.loads((out/'reelib_list_reimport.json').read_text())
    if len(native_list['motions'])!=1 or native_list['motions'][0]!=independent or native_list['indices'][0]!=dict(original['indices'][0],resource=0):raise ValueError('Native list/index reimport mismatch')
    validation=validate(parsed,independent,rig,doc,binary);write_json(out/'reimport_report.json',validation)
    if validation['status']!='PASSED':raise ValueError('Native reimport failed; see preserved numerical report')
    metadata={'source_descriptor':original['indices'][0],'source_idle_name':clip0['name'],'source_idle_frames':clip0['frame_count'],
        'source_idle_behavior_clips':clip0['clips'],'source_idle_end_clips':clip0['end_clips'],
        'prototype_policy':'Fresh unregistered body-only list. No original event/controller behavior claimed. Full original bank/list is preserved separately, byte-identically. Original idle events are documented, not transplanted into a new state.',
        'prototype_events':0,'prototype_properties':0,'prototype_gpu_motion':False,
        'index_policy':'Selected zero-mask, zero-tag, zero-flag descriptor and all 12 unknown words retained. Motion ID 0/switch 0 are local prototype identifiers only; no live binding established.',
        'rest_dispositions':dispositions,'accepted_channels_copied':25,
        'root_policy':'Copy the approved root translation unchanged: periodic sway and constant floor offset, no accumulated locomotion or new root motion.',
        'original_native_track_policy':'Original 68 idle tracks remain untouched in the original/list roundtrip. New resource contains only the 25 approved channels; every other target local remains accepted bind offline.'}
    write_json(out/'metadata_dispositions.json',metadata)
    repeated_mot=encode_mot(bones,ordered,name,jmap=clip0['jmap'])
    if repeated_mot!=mot or encode_single_list(repeated_mot,'Bela_Offline_Prototype_Unregistered',original['indices'][0])!=list_bytes:raise ValueError('Non-repeatable encoding')
    if protect()!=before:raise ValueError('Protected state changed')
    write_json(out/'workflow_report.json',{'status':'PASSED','roundtrip':report,'reimport':validation,'protected':before,
        'byte_identical_repeated_native_encoding':True,'native_outputs':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(native_dir.iterdir())],
        'game_or_controller_writes':0,'runtime_tested':False})
    print(f'Native roundtrip passed: {len(original["motions"])} motions / {len(original["indices"])} slots; native Bela reimport error {validation["maximum_joint_position_error_m"]*1e6:.3f} micrometres')

if __name__=='__main__':main()

