"""Strict reader for the uncompressed glTF subset emitted in this experiment."""
import json
import struct
import numpy as np
from animation_math import compose, unit_quaternion, hierarchy_globals


def load(path):
    raw=path.read_bytes()
    magic,version,total=struct.unpack_from('<III',raw)
    if magic!=0x46546c67 or version!=2 or total!=len(raw): raise ValueError('Invalid GLB')
    jlen,jtype=struct.unpack_from('<II',raw,12)
    if jtype!=0x4e4f534a: raise ValueError('Missing GLB JSON')
    doc=json.loads(raw[20:20+jlen]); start=20+jlen
    blen,btype=struct.unpack_from('<II',raw,start)
    if btype!=0x004e4942 or start+8+blen!=len(raw): raise ValueError('Invalid GLB binary extent')
    return doc,raw[start+8:]


def accessor(doc,data,index):
    a=doc['accessors'][index]; v=doc['bufferViews'][a['bufferView']]
    if 'sparse' in a or 'byteStride' in v: raise ValueError('Unsupported accessor encoding')
    dtype={5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']]
    width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
    offset=v.get('byteOffset',0)+a.get('byteOffset',0)
    size=a['count']*width*np.dtype(dtype).itemsize
    if offset<0 or offset+size>len(data): raise ValueError('Accessor bounds')
    return np.frombuffer(data,dtype=dtype,count=a['count']*width,offset=offset).reshape(-1,width).copy()


def slerp(a,b,w):
    a=unit_quaternion(a); b=unit_quaternion(b); dot=float(np.dot(a,b))
    if dot<0: b=-b; dot=-dot
    if dot>.9995: return unit_quaternion((1-w)*a+w*b)
    angle=np.arccos(np.clip(dot,-1,1)); return (np.sin((1-w)*angle)*a+np.sin(w*angle)*b)/np.sin(angle)


def sample_globals(doc,data,seconds):
    nodes=doc['nodes']; parents=[-1]*len(nodes)
    for i,n in enumerate(nodes):
        for c in n.get('children',[]):
            if parents[c]!=-1: raise ValueError('Multiple glTF parents')
            parents[c]=i
    trs=[{'translation':np.array(n.get('translation',[0,0,0]),dtype=float),
          'rotation':np.array(n.get('rotation',[0,0,0,1]),dtype=float),
          'scale':np.array(n.get('scale',[1,1,1]),dtype=float)} for n in nodes]
    if seconds is not None:
        animation=doc['animations'][0]
        for c in animation['channels']:
            sampler=animation['samplers'][c['sampler']]
            if sampler.get('interpolation','LINEAR')!='LINEAR': raise ValueError('Unhandled glTF interpolation')
            times=accessor(doc,data,sampler['input']).reshape(-1); vals=accessor(doc,data,sampler['output'])
            k=int(np.searchsorted(times,seconds,side='right')); path=c['target']['path']
            if k==0: value=vals[0]
            elif k==len(times): value=vals[-1]
            else:
                w=(seconds-times[k-1])/(times[k]-times[k-1])
                value=slerp(vals[k-1],vals[k],w) if path=='rotation' else (1-w)*vals[k-1]+w*vals[k]
            trs[c['target']['node']][path]=value
    return hierarchy_globals([compose(t['translation'],t['rotation'],t['scale']) for t in trs],parents)

