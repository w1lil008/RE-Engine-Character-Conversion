"""Bounded MOT 983 / MOTLIST 1047 serializer; no game or controller writes.

Original compressed payloads and opaque metadata are retained losslessly. New
body tracks use C0000 XYZ quaternions where stable, full XYZW near half turns,
and full float translations. Both rotation modes are explicit MOT decoder modes.
This is intentionally not a general event authoring or compression editor.
"""
import base64
import json
import struct
import numpy as np
from animation_math import unit_quaternion

MOT_MAGIC = 0x20746f6d
LIST_MAGIC = 0x74736c6d

def read(data, fmt, offset):
    size = struct.calcsize(fmt)
    if offset < 0 or offset + size > len(data): raise ValueError('Native pointer out of bounds')
    return struct.unpack_from(fmt, data, offset)

def wstring(data, offset):
    if not offset: return None
    if offset < 0 or offset >= len(data) or offset % 2: raise ValueError('Invalid UTF16 pointer')
    end = offset
    while end + 2 <= len(data) and data[end:end+2] != b'\0\0': end += 2
    if end + 2 > len(data): raise ValueError('Unterminated UTF16 string')
    return data[offset:end].decode('utf-16-le')

def lossless_decode(data):
    """Decode control fields and preserve a complete ordered binary partition.

    Packed values are encoded codes, not decoded floats. Preserving their exact
    representation avoids re-quantization. Events/properties/unknown data remain
    explicit opaque partitions; no claim of their semantic authoring support.
    ReeLib independently decodes all bone tracks before and after this roundtrip.
    """
    if read(data,'<II',0) != (1047,LIST_MAGIC): raise ValueError('Expected MOTLIST 1047')
    pointers, indices = read(data,'<QQ',16); count, = read(data,'<I',56)
    if count > 100000: raise ValueError('Invalid slot count')
    fields = [(0, '<16I', 'list_header_bits')]
    offsets = read(data, '<'+'Q'*count, pointers)
    fields.append((pointers, '<'+'Q'*count, 'resource_offsets'))
    for i in range(count): fields.append((indices+i*72,'<QHHIIBBBB12I',f'index_{i}'))
    for off in sorted(set(offsets)-{0}):
        if read(data,'<II',off) != (983,MOT_MAGIC): raise ValueError('Unsupported embedded resource; preservation not certified')
        fields.append((off,'<32I',f'motion_header_bits_{off}'))
        n, = read(data,'<H',off+114); clip_ptr, = read(data,'<Q',off+24)
        for j in range(n):
            pos=off+clip_ptr+j*12
            bone,flags,weight,hash_,tracks=read(data,'<HBBII',pos)
            if flags & ~7: raise ValueError('Unsupported bone track flags')
            fields.append((pos,'<HBBII',f'bone_track_{off}_{j}'))
            for k in range(flags.bit_count()):
                fields.append((off+tracks+k*20,'<5I',f'track_header_{off}_{j}_{k}'))
    # Shared track headers are allowed only when their typed interpretation agrees.
    unique={}
    for offset,fmt,label in fields:
        value=list(read(data,fmt,offset)); key=(offset,struct.calcsize(fmt))
        if key in unique:
            if unique[key]['format']!=fmt or unique[key]['values']!=value: raise ValueError('Conflicting shared headers')
        else: unique[key]={'offset':offset,'format':fmt,'values':value,'label':label}
    segments=[]; cursor=0
    for f in sorted(unique.values(),key=lambda v:v['offset']):
        offset=f['offset']; size=struct.calcsize(f['format'])
        if offset < cursor: raise ValueError('Overlapping control headers')
        if offset>cursor: segments.append({'offset':cursor,'opaque_bytes_b64':base64.b64encode(data[cursor:offset]).decode()})
        segments.append(f); cursor=offset+size
    if cursor<len(data): segments.append({'offset':cursor,'opaque_bytes_b64':base64.b64encode(data[cursor:]).decode()})
    return {'schema':'RE9_LOSSLESS_CONTROL_AND_PACKED_PARTITIONS_V1','size':len(data),'slots':count,'motions':len(set(offsets)-{0}),'segments':segments}

def lossless_encode(document):
    if document['schema']!='RE9_LOSSLESS_CONTROL_AND_PACKED_PARTITIONS_V1': raise ValueError('Unsupported preservation schema')
    output=bytearray()
    for s in document['segments']:
        if s['offset']!=len(output): raise ValueError('Partition gap or overlap')
        output.extend(struct.pack(s['format'],*s['values']) if 'format' in s else base64.b64decode(s['opaque_bytes_b64'],validate=True))
    if len(output)!=document['size']: raise ValueError('Partition size changed')
    return bytes(output)

class Buffer:
    def __init__(self): self.data=bytearray()
    def align(self,n=16): self.data.extend(b'\0'*((-len(self.data))%n))
    def reserve(self,size): o=len(self.data);self.data.extend(b'\0'*size);return o
    def put(self,fmt,*values): o=len(self.data);self.data.extend(struct.pack(fmt,*values));return o
    def patch(self,offset,fmt,*values): struct.pack_into(fmt,self.data,offset,*values)
    def string(self,value): o=len(self.data);self.data.extend(value.encode('utf-16-le')+b'\0\0');return o

def encode_mot(bones,tracks,name,frame_count=300,fps=60,jmap=None):
    """Author a fresh body-only native MOT; all channel dispositions explicit."""
    if len(bones)>65535 or len(tracks)>65535: raise ValueError('Native count overflow')
    names={b['name']:i for i,b in enumerate(bones)}
    if len(names)!=len(bones): raise ValueError('Duplicate bones')
    if len({b['hash'] for b in bones})!=len(bones): raise ValueError('Bone hash collision')
    out=Buffer();out.reserve(128)
    clip_offset=out.reserve(12*len(tracks));out.align()
    for i,t in enumerate(tracks):
        if t['bone'] not in names: raise ValueError('Unbound track')
        if set(t)-{'bone','translation','rotation','scale'}:raise ValueError('Unsupported channel fields')
        channels=[(key,t[key]) for key in ('translation','rotation','scale') if key in t]
        flags=sum({'translation':1,'rotation':2,'scale':4}[k] for k,v in channels)
        if not channels: raise ValueError('Empty bone track')
        headers=out.reserve(20*len(channels))
        out.patch(clip_offset+i*12,'<HBBII',names[t['bone']],flags,255,bones[names[t['bone']]]['hash'],headers)
        for j,(kind,c) in enumerate(channels):
            values=np.asarray(c['values'],dtype=float); frames=c['frames']
            width=4 if kind=='rotation' else 3
            if values.shape!=(len(values),width) or not len(values) or not np.isfinite(values).all(): raise ValueError('Invalid channel')
            if frames is not None and (len(frames)!=len(values) or frames[0]<0 or frames[-1]>frame_count or any(b<=a for a,b in zip(frames,frames[1:]))): raise ValueError('Invalid timing')
            if frames is None and len(values)!=1: raise ValueError('Implicit multi-key timing')
            if frames is not None and any(int(f)!=f for f in frames): raise ValueError('Fractional native frame index')
            out.align(4); time_offset=0
            if frames is not None: time_offset=out.put('<'+'h'*len(frames),*frames)
            out.align(4); value_offset=len(out.data)
            if kind=='rotation':
                values=np.asarray([unit_quaternion(q) for q in values])
                # Native XYZ stores positive reconstructed W; equivalent signs
                # are canonicalized, never mistaken for new rotations.
                if np.min(np.abs(values[:,3])) < .1:
                    out.data.extend(values.astype('<f4').tobytes());native_flags=0x400112
                else:
                    values[values[:,3]<0]*=-1
                    out.data.extend(values[:,:3].astype('<f4').tobytes()); native_flags=0x4c0112
            else:
                out.data.extend(values.astype('<f4').tobytes());native_flags=0x4000f2
            out.patch(headers+j*20,'<5I',native_flags,len(values),time_offset,value_offset,0)
        out.align()
    data_offset=out.string(jmap) if jmap else 0
    out.align(); name_offset=out.string(name);motion_data_size=len(out.data);out.align()
    bone_offset=out.put('<QQ',len(out.data)+16,len(bones));first=len(out.data)
    out.reserve(80*len(bones))
    for i,b in enumerate(bones):
        parent=b['parent']; children=[j for j,c in enumerate(bones) if c['parent']==b['name']]
        siblings=[j for j,c in enumerate(bones) if c['parent']==parent];pos=siblings.index(i)
        if parent is not None and parent not in names: raise ValueError('Missing parent')
        parent_ptr=first+80*names[parent] if parent is not None else 0
        child_ptr=first+80*children[0] if children else 0
        sibling_ptr=first+80*siblings[pos+1] if pos+1<len(siblings) else 0
        string_offset=out.string(b['name']);q=unit_quaternion(b['rotation']);t=b['translation']
        out.patch(first+i*80,'<QQQQ3fI4fIIii',string_offset,parent_ptr,child_ptr,sibling_ptr,*t,0,*q,i,b['hash'],b['attributes1'],b['attributes2'])
    out.align()
    # As in MotFile.DoWrite, motSize excludes alignment and the rest table.
    out.patch(0,'<4I',983,MOT_MAGIC,0,motion_data_size)
    out.patch(16,'<10Q',bone_offset,clip_offset,0,0,0,data_offset,0,0,0,name_offset)
    out.patch(96,'<4fHHBBHHHH',frame_count,0,0,frame_count,len(bones),len(tracks),0,0,0,fps,0,0)
    return bytes(out.data)

def encode_single_list(mot,name,index):
    """Fresh unregistered list. Copies the selected descriptor, not controllers."""
    out=Buffer();out.reserve(64);name_offset=out.string(name);out.align()
    pointer_offset=out.put('<Q',0);out.align();mot_offset=len(out.data);out.data.extend(mot);out.align()
    # As in MotlistFile.DoWrite, the first motion owns the shared rest table.
    out.patch(mot_offset+12,'<I',0)
    index_offset=out.put('<QHHIIBBBB12I',0,index['motion_id'],index['switch'],index['joint_mask'],index['tag'],
        index['type'],index['flags'],index['physics_flags'],0,*index['data'])
    out.patch(0,'<4I',1047,LIST_MAGIC,0,0)
    out.patch(16,'<5Q',pointer_offset,index_offset,name_offset,0,0)
    out.patch(56,'<IH',1,0);out.patch(pointer_offset,'<Q',mot_offset)
    return bytes(out.data)

def decode_float_mot(data,base=0,embedded=False):
    """Independent strict parser for the freshly authored native subset."""
    if read(data,'<II',base)!=(983,MOT_MAGIC): raise ValueError('Expected MOT 983')
    size,=read(data,'<I',base+12)
    data=data[base:]
    if size>len(data) or (not embedded and not size) or (embedded and size):raise ValueError('Invalid MOT size/shared-table marker')
    pointers=read(data,'<10Q',16)
    if any(pointers[i] for i in (2,3,4,6,7,8)): raise ValueError('Unexpected metadata in body-only clip')
    name=wstring(data,pointers[9]);motion_data_end=pointers[9]+len(name.encode('utf-16-le'))+2
    if (not embedded and size!=motion_data_end) or pointers[0]!=(motion_data_end+15)//16*16:raise ValueError('Noncanonical motion-data/rest-table boundary')
    frames,blend,start,end=read(data,'<4f',96)
    count,track_count,clips,ends,attr2,fps,properties,attrs=read(data,'<HHBBHHHH',112)
    if clips or ends or properties or attrs or attr2: raise ValueError('Unexpected body-only header flags')
    first,bone_count=read(data,'<QQ',pointers[0]);bones=[]
    if bone_count!=count or first!=pointers[0]+16: raise ValueError('Invalid rest table')
    def relation(ptr):
        if ptr==0:return None
        if ptr<first or (ptr-first)%80 or (ptr-first)//80>=count:raise ValueError('Invalid bone relation')
        return int((ptr-first)//80)
    for i in range(count):
        values=read(data,'<QQQQ3fI4fIIii',first+i*80)
        if values[12]!=i: raise ValueError('Nonsequential rest index')
        bones.append({'name':wstring(data,values[0]),'parent_index':relation(values[1]),'child_index':relation(values[2]),
            'sibling_index':relation(values[3]),'translation':list(values[4:7]),'rotation':list(values[8:12]),
            'index':values[12],'hash':values[13],'attributes1':values[14],'attributes2':values[15]})
    for b in bones:b['parent']=bones[b['parent_index']]['name'] if b['parent_index'] is not None else None
    if len({b['name'] for b in bones})!=count or len({b['hash'] for b in bones})!=count: raise ValueError('Duplicate binding')
    for i,b in enumerate(bones):
        ancestors={i};parent=b['parent_index']
        while parent is not None:
            if parent in ancestors:raise ValueError('Cyclic native hierarchy')
            ancestors.add(parent);parent=bones[parent]['parent_index']
        children=[j for j,c in enumerate(bones) if c['parent_index']==i]
        siblings=[j for j,c in enumerate(bones) if c['parent_index']==b['parent_index']];position=siblings.index(i)
        if b['child_index']!=(children[0] if children else None):raise ValueError('Inconsistent child relation')
        if b['sibling_index']!=(siblings[position+1] if position+1<len(siblings) else None):raise ValueError('Inconsistent sibling relation')
    tracks=[]
    for i in range(track_count):
        index,flags,weight,hash_,offset=read(data,'<HBBII',pointers[1]+i*12)
        if index>=count or hash_!=bones[index]['hash'] or flags & ~7 or not flags:raise ValueError('Invalid bone binding')
        t={'bone':bones[index]['name'],'index':index,'hash':hash_,'flags':flags,'weight':weight/255}
        k=0
        for flag,kind in ((1,'translation'),(2,'rotation'),(4,'scale')):
            if not flags & flag: continue
            tf,n,fo,vo,uo=read(data,'<5I',offset+k*20);k+=1
            if tf not in ((0x4c0112,0x400112) if kind=='rotation' else (0x4000f2,)) or uo or not n: raise ValueError('Unsupported new encoding')
            times=list(read(data,'<'+'h'*n,fo)) if fo else None
            if times is None and n!=1:raise ValueError('Invalid implicit timing')
            if times is not None and (times[0]<0 or times[-1]>frames or any(b<=a for a,b in zip(times,times[1:]))):raise ValueError('Invalid timestamps')
            width=4 if tf==0x400112 else 3
            if offset+k*20>motion_data_end or (fo and fo+n*2>motion_data_end) or vo+width*n*4>motion_data_end:raise ValueError('Track data crosses motion-data boundary')
            values=np.asarray(read(data,'<'+'f'*(width*n),vo),dtype=np.float32).reshape(n,width)
            if not np.isfinite(values).all():raise ValueError('Nonfinite keys')
            if kind=='rotation' and width==3:
                # Match RE9 reader float32 sqrt, including its tiny negative clamp.
                remainder=np.float32(1)-values[:,0]*values[:,0]-values[:,1]*values[:,1]-values[:,2]*values[:,2]
                w=np.sqrt(np.maximum(np.float32(0),remainder));values=np.column_stack((values,w))
            t[kind]={'flags':tf,'frames':times,'values':values.tolist()}
        tracks.append(t)
    return {'name':name,'frame_count':frames,'start':start,'end':end,'fps':fps,
        'jmap':wstring(data,pointers[5]),'bones':bones,'tracks':tracks}

