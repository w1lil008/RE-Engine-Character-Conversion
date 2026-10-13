import copy
import json
from pathlib import Path
import struct
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import ROOT
from animation_math import compose,decompose,quaternion_matrix,hierarchy_globals,sample,reference_samples,motion_globals
from source_animation_export import validate_decoded,GLB
from glb_read import load,accessor,sample_globals
from source_video_metadata import video_metadata


class AnimationMathTests(unittest.TestCase):
    def test_quaternion_TRS_roundtrip_at_large_rotations(self):
        for q in [[1,0,0,0],[0,1,0,0],[0,0,1,0],[.1,-.4,.3,.8]]:
            m=compose([.2,1.2,-.3],q,[1,2,3]); t,r,s=decompose(m)
            np.testing.assert_allclose(compose(t,r,s),m,atol=1e-12)
    def test_root_intermediary_composition(self):
        a=compose([1,0,0],[0,0,0,1]); b=compose([0,2,0],[0,0,0,1]); c=compose([0,0,3],[0,0,0,1])
        result=hierarchy_globals([a,b,c],[-1,0,1]);np.testing.assert_allclose(result[2,:3,3],[1,2,3])
    def test_cycle_and_invalid_parent_fail(self):
        for parents in [[1,0],[-1,3]]:
            with self.assertRaises(ValueError):hierarchy_globals([np.eye(4)]*2,parents)
    def test_axis_conversion_is_rotation_not_scale(self):
        a=compose([0,0,0],[np.sqrt(.5),0,0,np.sqrt(.5)])
        np.testing.assert_allclose(a[:3,:3]@[0,1,0],[0,0,1],atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(a[:3,:3]),1)
    def test_sparse_constant_and_endpoint_sampling(self):
        c={'frames':[0,10,30],'values':[[0,0,0],[1,0,0],[3,0,0]]}
        np.testing.assert_allclose(sample(c,20),[2,0,0]);np.testing.assert_allclose(sample(c,31),[3,0,0])
        np.testing.assert_allclose(sample({'frames':None,'values':[[2,3,4]]},77),[2,3,4])
    def test_quaternion_sign_continuity(self):
        c={'frames':[0,10],'values':[[0,0,0,1],[0,0,0,-1]]}
        np.testing.assert_allclose(quaternion_matrix(sample(c,5,True)),np.eye(3),atol=1e-12)
    def test_invalid_quaternion_fails(self):
        for q in [[0,0,0,0],[float('nan'),0,0,1]]:
            with self.assertRaises(ValueError):quaternion_matrix(q)


class OriginalIdleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((ROOT/'config/source_idle_v0.2.0.json').read_text())
        cls.output=ROOT/cls.config['output'];path=cls.output/'decoded_reference.json'
        if not path.exists():raise unittest.SkipTest('Run source reconstruction before integration tests')
        cls.decoded=json.loads(path.read_text())
    def test_exact_resource_and_no_missing_channels(self):
        result=validate_decoded(self.decoded,self.config)
        self.assertEqual(result['channels'],{'translation':57,'rotation':116})
        self.assertEqual(result['decoded_keys'],2824);self.assertEqual(len(result['compression_modes']),13)
        self.assertEqual(result['unsupported_transform_channels'],[])
    def test_full_loop_video_timing(self):
        result=video_metadata(self.output/'source_idle_60fps.mp4')
        self.assertEqual(result['frame_count'],300)
        self.assertEqual(result['duration_seconds'],5)
        self.assertEqual(result['fps'],60)
        self.assertTrue(result['constant_frame_timing'])
    def test_native_track_headers_and_sparse_frame_times(self):
        raw=(ROOT/self.config['source']).read_bytes();base=self.config['offset'];clip_table=base+struct.unpack_from('<Q',raw,base+24)[0]
        for i,t in enumerate(self.decoded['tracks']):
            index,flags,weight,bhash,pointer=struct.unpack_from('<HBBII',raw,clip_table+i*12)
            self.assertEqual((index,flags,bhash),(t['index'],t['flags'],t['hash']));self.assertEqual(weight,255)
            pos=base+pointer
            for key in ['translation','rotation','scale']:
                c=t[key]
                if not c:continue
                f,count,times,data,unpack=struct.unpack_from('<5I',raw,pos);pos+=20
                self.assertEqual((f,count),(c['flags'],c['key_count']))
                if times:
                    fmt={2:'B',4:'h',5:'i'}[f>>20]
                    self.assertEqual(list(struct.unpack_from('<'+fmt*count,raw,base+times)),c['frames'])
                else:self.assertIsNone(c['frames'])
    def test_unsupported_or_missing_channels_fail(self):
        for mutation in ['missing','invalid_timing','zero_quaternion','property_channel']:
            d=copy.deepcopy(self.decoded)
            if mutation=='missing':d['tracks'][0]['rotation']=None
            elif mutation=='invalid_timing':d['tracks'][0]['translation']['frames'][1]=0
            elif mutation=='zero_quaternion':d['tracks'][0]['rotation']['values'][0]=[0,0,0,0]
            else:d['property_track_count']=1
            with self.assertRaises(ValueError):validate_decoded(d,self.config)
    def test_reference_sampler_and_loop_boundary(self):
        times,reference=reference_samples(self.output/'decoded_reference.reference.bin')
        for i in [0,1,150,300,599,600]:np.testing.assert_allclose(motion_globals(self.decoded,float(times[i])),reference[i],atol=1e-6)
        a=motion_globals(self.decoded,0);b=motion_globals(self.decoded,300)
        self.assertLess(np.max(np.linalg.norm(a[:,:3,3]-b[:,:3,3],axis=1)),.001)
    def test_GLB_preserves_all_bones_channels_and_inverse_binds(self):
        doc,data=load(self.output/'source_idle.glb');self.assertEqual(len(doc['animations'][0]['channels']),258)
        names=[n['name'] for n in doc['nodes']]
        self.assertTrue(all(b['name'] in names for b in self.decoded['bones']))
        bind=sample_globals(doc,data,None);skin=doc['skins'][0];ibm=accessor(doc,data,skin['inverseBindMatrices']).reshape(-1,4,4).swapaxes(-1,-2)
        np.testing.assert_allclose(bind[skin['joints']]@ibm,np.broadcast_to(np.eye(4),ibm.shape),atol=1e-5)
    def test_GLB_sampling_matches_source(self):
        doc,data=load(self.output/'source_idle.glb');names=[n['name'] for n in doc['nodes']];indices=[names.index(b['name']) for b in self.decoded['bones']]
        for f in [0,.5,25.5,150,299.5,300]:
            np.testing.assert_allclose(sample_globals(doc,data,f/60)[indices],motion_globals(self.decoded,f),atol=1e-5)


if __name__=='__main__':unittest.main()

