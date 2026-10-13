import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from runtime_capture import load_capture
from runtime_applied_motion import compare

class AppliedMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.live=load_capture(ROOT/'build/animation_v0.2.0/runtime_experiment/grace_one_cycle_20261011_b/grace_one_cycle_20261011_b_9.json')

    def test_live_rotations_match_but_root_and_final_pose_are_not_certified(self):
        result=compare(self.live)
        self.assertTrue(result['live_rotation_comparison_passed'])
        self.assertEqual(result['sampled_poses'],82)
        self.assertLess(result['maximum_rotation_error_deg'],.0001)
        self.assertFalse(result['root_position_observation']['raw_channel_equals_layer_position'])
        self.assertFalse(result['final_controller_transforms_verified'])

    def test_normalized_wrong_rotation_fails_numerical_comparison(self):
        doc=copy.deepcopy(self.live)
        pose=next(p for p in doc['poses'] if p['phase']=='PLAYBACK_ONE_CYCLE')
        joint=next(j for j in pose['joints'] if j['name']=='R_Arm_Clavicle')
        joint['rotation']=[0,0,0,1]
        self.assertFalse(compare(doc)['live_rotation_comparison_passed'])

    def test_wrong_frame_fails_even_when_structure_and_quaternions_are_valid(self):
        doc=copy.deepcopy(self.live)
        pose=next(p for p in doc['poses'] if p['phase']=='PLAYBACK_ONE_CYCLE')
        pose['layer']['frame']=150
        self.assertFalse(compare(doc)['live_rotation_comparison_passed'])

    def test_failed_cleanup_cannot_be_hidden_by_matching_rotations(self):
        doc=copy.deepcopy(self.live);doc['cleanup']['original_references_preserved']=False
        with self.assertRaises(ValueError):compare(doc)

if __name__=='__main__':unittest.main()

