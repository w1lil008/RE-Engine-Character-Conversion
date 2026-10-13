"""Milestone C regression gates; original and accepted references are read-only."""
import copy
import json
import struct
import sys
import unittest
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from native_mot import lossless_decode,lossless_encode,encode_mot,decode_float_mot,read
from native_idle_workflow import SOURCE,SOURCE_SHA,rotation_angles
from native_idle_workflow import compare_original_idle
from source_animation_workflow import sha
from native_animation_protection import protect

OUTPUT=ROOT/'build/animation_v0.2.0/native_idle_canonical'

def fixture(q=(0,0,0,1),times=None):
    bones=[{'name':'root','parent':None,'hash':123,'translation':[0,0,0],'rotation':[0,0,0,1],
        'attributes1':0,'attributes2':0}]
    channel={'frames':times,'values':[list(q)] if times is None else [list(q)]*len(times)}
    return bones,[{'bone':'root','rotation':channel}]

class NativeAnimationTests(unittest.TestCase):
    def test_original_complete_roundtrip(self):
        raw=(ROOT/SOURCE).read_bytes();document=lossless_decode(raw)
        self.assertEqual(lossless_encode(json.loads(json.dumps(document))),raw)
        self.assertEqual(document['motions'],211);self.assertEqual(document['slots'],270)

    def test_original_idle_decoded_float_roundtrip_preserves_metadata(self):
        folder=ROOT/'build/animation_v0.2.0/native_idle_canonical_repeat'
        a=json.loads((folder/'original_grace_idle.json').read_text())
        b=json.loads((folder/'roundtrip_grace_idle.json').read_text())
        r=compare_original_idle(a,b)
        self.assertTrue(r['all_known_metadata_equal']);self.assertLess(r['maximum_decoded_component_difference'],1e-6)
        b['clips'][0]['useFlags']^=1
        with self.assertRaises(ValueError):compare_original_idle(a,b)

    def test_native_list_references_standalone_motion_and_retained_descriptor(self):
        raw=(OUTPUT/'native/bela_idle.motlist.1047').read_bytes()
        self.assertEqual(read(raw,'<II',0),(1047,0x74736c6d));self.assertEqual(read(raw,'<I',56),(1,))
        pointer_table,index_offset=read(raw,'<QQ',16);offset,=read(raw,'<Q',pointer_table)
        standalone=(OUTPUT/'native/bela_idle.mot.983').read_bytes()
        embedded=bytearray(standalone);struct.pack_into('<I',embedded,12,0)
        self.assertEqual(raw[offset:offset+len(standalone)],embedded)
        self.assertEqual(decode_float_mot(raw,offset,embedded=True),decode_float_mot(standalone))
        values=read(raw,'<QHHIIBBBB12I',index_offset)
        self.assertEqual(values[1:9],(0,0,0,0,1,0,0,0))
        self.assertEqual(values[9:],(0,0,0,0,0,0,0,0,0,0,4278190080,4294967295))

    def test_canonical_motion_data_size_excludes_rest_table(self):
        bones,tracks=fixture();raw=encode_mot(bones,tracks,'size')
        size,=read(raw,'<I',12);bone_header,=read(raw,'<Q',16)
        self.assertLess(size,len(raw));self.assertEqual(bone_header,(size+15)//16*16)
        damaged=bytearray(raw);struct.pack_into('<I',damaged,12,len(raw))
        with self.assertRaises(ValueError):decode_float_mot(damaged)

    def test_typed_motion_id_edit_does_not_drop_opaque_metadata(self):
        raw=(ROOT/SOURCE).read_bytes();document=lossless_decode(raw)
        segment=next(s for s in document['segments'] if s.get('label')=='index_0')
        segment['values'][1]=32123;encoded=lossless_encode(document)
        expected=bytearray(raw);struct.pack_into('<H',expected,segment['offset']+8,32123)
        self.assertEqual(encoded,expected)

    def test_lossless_partition_gap_rejected(self):
        d=lossless_decode((ROOT/SOURCE).read_bytes());d['segments'][1]['offset']+=1
        with self.assertRaises(ValueError):lossless_encode(d)

    def test_broken_native_pointer_rejected(self):
        raw=bytearray((ROOT/SOURCE).read_bytes());struct.pack_into('<Q',raw,16,len(raw)+100)
        with self.assertRaises(ValueError):lossless_decode(raw)

    def test_native_parent_cycle_rejected(self):
        bones,tracks=fixture();raw=bytearray(encode_mot(bones,tracks,'cycle'))
        bone_header,=read(raw,'<Q',16);first,=read(raw,'<Q',bone_header)
        struct.pack_into('<Q',raw,first+8,first)
        with self.assertRaises(ValueError):decode_float_mot(raw)

    def test_near_half_turn_uses_four_components(self):
        q=[np.sqrt(1-1e-12),0,0,1e-6];bones,tracks=fixture(q)
        decoded=decode_float_mot(encode_mot(bones,tracks,'precision'))
        channel=decoded['tracks'][0]['rotation']
        self.assertEqual(channel['flags'],0x400112)
        self.assertAlmostEqual(channel['values'][0][3],q[3],places=12)

    def test_full_quaternion_keeps_continuous_signs(self):
        bones,tracks=fixture([np.sqrt(1-1e-8),0,0,-.0001])
        decoded=decode_float_mot(encode_mot(bones,tracks,'negative_w'))
        self.assertLess(decoded['tracks'][0]['rotation']['values'][0][3],0)

    def test_stable_rotation_uses_observed_three_component_mode(self):
        bones,tracks=fixture([0,.2,0,np.sqrt(.96)])
        decoded=decode_float_mot(encode_mot(bones,tracks,'stable'))
        self.assertEqual(decoded['tracks'][0]['rotation']['flags'],0x4c0112)
        self.assertTrue(np.allclose(decoded['tracks'][0]['rotation']['values'][0],tracks[0]['rotation']['values'][0],atol=1e-7))

    def test_nonmonotonic_or_fractional_timing_rejected(self):
        for times in ([0,0],[1,0],[0,.5]):
            bones,tracks=fixture(times=times)
            with self.assertRaises(ValueError):encode_mot(bones,tracks,'bad_timing')

    def test_unsupported_and_unbound_track_rejected(self):
        bones,tracks=fixture();tracks[0]['bone']='missing'
        with self.assertRaises(ValueError):encode_mot(bones,tracks,'unbound')
        bones,tracks=fixture();raw=bytearray(encode_mot(bones,tracks,'bad'))
        offset,=read(raw,'<Q',24);raw[offset+2]=8
        with self.assertRaises(ValueError):decode_float_mot(raw)

    def test_repeat_native_encoding_is_byte_identical(self):
        bones,tracks=fixture(times=[0,150,300])
        self.assertEqual(encode_mot(bones,tracks,'repeat'),encode_mot(bones,tracks,'repeat'))

    def test_rotation_error_ignores_bind_rounding_scale(self):
        a=np.eye(3)[None];b=a*(1-2e-8)
        self.assertLess(rotation_angles(a,b)[0],1e-10)
        angle=.01;r=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
        self.assertAlmostEqual(rotation_angles(a,r[None])[0],np.degrees(angle),places=8)

    def test_native_reimport_report_and_complete_channel_timing(self):
        r=json.loads((OUTPUT/'reimport_report.json').read_text());self.assertEqual(r['status'],'PASSED')
        self.assertLess(r['maximum_joint_position_error_m'],5e-5)
        self.assertLess(r['maximum_unmapped_target_local_matrix_error'],1e-6)
        m=decode_float_mot((OUTPUT/'native/bela_idle.mot.983').read_bytes())
        self.assertEqual(len(m['bones']),70);self.assertEqual(len(m['tracks']),24)
        channels=[t[k] for t in m['tracks'] for k in ('translation','rotation','scale') if k in t]
        self.assertEqual(len(channels),25)
        for c in channels:self.assertEqual(c['frames'],list(range(301)))
        for t in m['tracks']:
            if 'rotation' in t:
                q=np.asarray(t['rotation']['values']);self.assertLess(np.abs(np.linalg.norm(q,axis=1)-1).max(),1e-6)
                self.assertGreater(np.abs(np.sum(q[1:]*q[:-1],axis=1)).min(),.999)
                self.assertGreater(np.sum(q[1:]*q[:-1],axis=1).min(),.999)

    def test_root_translation_is_accepted_motion_without_added_locomotion(self):
        native=decode_float_mot((OUTPUT/'native/bela_idle.mot.983').read_bytes())
        t=next(t['translation'] for t in native['tracks'] if t['bone']=='root')
        reference=np.load(ROOT/'build/animation_v0.2.0/retarget_idle/retarget_matrices.npz')['locals'][:,0,:3,3]
        self.assertTrue(np.allclose(t['values'],reference,atol=2e-9,rtol=0))
        self.assertLess(np.linalg.norm(np.asarray(t['values'])[-1]-np.asarray(t['values'])[0]),1e-6)

    def test_protected_original_releases_and_accepted_retarget(self):
        self.assertEqual(sha(ROOT/SOURCE),SOURCE_SHA)
        self.assertTrue(protect()['milestone_B_user_accepted'])

if __name__=='__main__':unittest.main()

