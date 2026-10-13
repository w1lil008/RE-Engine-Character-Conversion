import copy
import json
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import ROOT
from animation_math import compose, hierarchy_globals, motion_globals, quaternion_matrix
from glb_read import load, sample_globals, accessor
from retarget_math import Retarget, swing, rotation
from retarget_idle_export import channel_dispositions


class BasisTests(unittest.TestCase):
    def test_known_axis_swing(self):
        result = swing([1, 0, 0], [0, 1, 0])
        np.testing.assert_allclose(result @ [1, 0, 0], [0, 1, 0], atol=1e-12)
        np.testing.assert_allclose(result.T @ result, np.eye(3), atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(result), 1)

    def test_antiparallel_swing_and_invalid_segments(self):
        result = swing([0, 1, 0], [0, -1, 0])
        np.testing.assert_allclose(result @ [0, 1, 0], [0, -1, 0], atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(result), 1)
        with self.assertRaises(ValueError): swing([0, 0, 0], [0, 1, 0])


class IdleRetargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / 'config/retarget_idle_v0.2.0.json').read_text())
        cls.output = ROOT / cls.config['output']
        if not (cls.output / 'retarget_idle.glb').exists():
            raise unittest.SkipTest('Run offline retarget workflow first')
        cls.config = json.loads((cls.output / 'retarget_config.json').read_text())
        cls.decoded = json.loads((ROOT / cls.config['decoded']).read_text())
        sd, sb = load(ROOT / cls.config['source_glb']); sw = sample_globals(sd, sb, None)
        cls.source_bind = {n['name']: sw[i] for i, n in enumerate(sd['nodes'])}
        cls.target = json.loads((cls.output / 'target_rig.json').read_text())
        for bone in cls.target:
            for field in ['local', 'world', 'inverse']: bone[field] = np.asarray(bone[field])
        cls.adapter = Retarget(cls.decoded, cls.source_bind, cls.target, cls.config)
        cls.doc, cls.data = load(cls.output / 'retarget_idle.glb')

    def test_mapping_and_actual_helper_hierarchies(self):
        self.assertEqual(len(self.adapter.mapping), 24)
        bones = {b['name']: b for b in self.decoded['bones']}
        self.assertEqual(bones['Hip']['parent'], 'root')
        self.assertEqual(bones['Null_Offset']['parent'], 'root')
        self.assertFalse(any(b['parent'] == 'Null_Offset' for b in self.decoded['bones']))
        self.assertEqual(self.adapter.mapping['L_Foot'], 'L_Leg_Ankle')
        target = {b['name']: b for b in self.target}
        self.assertEqual(target['L_Leg_Foot']['parent'], 'L_Leg_Ankle')
        self.assertEqual(target['L_Leg_Toes']['parent'], 'L_Leg_Foot')
        invalid = copy.deepcopy(self.config); invalid['rotation_method'] = 'unsupported_space'
        with self.assertRaises(ValueError): Retarget(self.decoded, self.source_bind, self.target, invalid)

    def test_zero_rotation_delta_preserves_uncalibrated_target_bind(self):
        config = copy.deepcopy(self.config); config['anatomical_alignment'] = False
        adapter = Retarget(self.decoded, self.source_bind, self.target, config)
        source = np.asarray([self.source_bind[b['name']] for b in self.decoded['bones']])
        local, world = adapter.from_source_world(source)
        for i in range(611):
            # Native float32 bind matrices are slightly nonorthogonal; quaternion
            # projection is bounded by their precision, not double epsilon.
            np.testing.assert_allclose(rotation(local[i]), rotation(adapter.bind_local[i]), atol=2e-7, rtol=0)
            np.testing.assert_allclose(rotation(world[i]), rotation(adapter.bind_world[i]), atol=2e-7, rtol=0)

    def test_calibrated_segments_match_source_bind_directions(self):
        source = np.asarray([self.source_bind[b['name']] for b in self.decoded['bones']])
        _, world = self.adapter.from_source_world(source)
        for name, (se, te) in self.config['segment_ends'].items():
            a = self.source_bind[se][:3, 3] - self.source_bind[name][:3, 3]
            b = world[self.adapter.index[te], :3, 3] - world[self.adapter.index[self.config['mapping'][name]], :3, 3]
            np.testing.assert_allclose(a / np.linalg.norm(a), b / np.linalg.norm(b), atol=2e-7, rtol=0)

    def test_world_axis_rotation_survives_rest_roll_conversion(self):
        q = compose([0, 0, 0], [0, np.sin(.2), 0, np.cos(.2)])
        source = np.asarray([self.source_bind[b['name']] for b in self.decoded['bones']])
        _, initial = self.adapter.from_source_world(source)
        _, rotated = self.adapter.from_source_world(q @ source)
        for dest in self.adapter.reverse:
            i = self.adapter.index[dest]
            np.testing.assert_allclose(rotation(rotated[i]), q[:3, :3] @ rotation(initial[i]), atol=2e-7, rtol=0)

    def test_limb_offsets_and_protected_local_controls_remain_exact(self):
        unmapped = [i for i, n in enumerate(self.adapter.names) if n not in self.adapter.reverse]
        for frame in [0, .5, 75, 150, 225, 299.5, 300]:
            local, _ = self.adapter.pose(frame)
            np.testing.assert_array_equal(local[1:, :3, 3], self.adapter.bind_local[1:, :3, 3])
            np.testing.assert_array_equal(local[unmapped], self.adapter.bind_local[unmapped])

    def test_root_preserves_original_trajectory_and_floor_offset(self):
        sn = self.adapter.source_index['root']; start = motion_globals(self.decoded, 0)[sn, :3, 3]
        for frame in [0, 150, 300]:
            local, _ = self.adapter.pose(frame)
            expected = motion_globals(self.decoded, frame)[sn, :3, 3] - start
            expected[1] += self.config['root_floor_offset_m']
            np.testing.assert_allclose(local[0, :3, 3], expected, atol=1e-12)

    def test_no_source_tracks_silently_discarded(self):
        rows = channel_dispositions(self.decoded, self.config['mapping'])
        self.assertEqual(len(rows), 116)
        self.assertTrue(all(r['policy'] for r in rows))
        d = copy.deepcopy(self.decoded); d['tracks'][0]['bone'] = 'UnexpectedUnsupportedMotionBone'
        with self.assertRaises(ValueError): channel_dispositions(d, self.config['mapping'])

    def test_GLB_channel_mask_timing_and_original_inverse_binds(self):
        animation = self.doc['animations'][0]; names = [n['name'] for n in self.doc['nodes']]
        self.assertEqual(len(animation['channels']), 25)
        actual = {(names[c['target']['node']], c['target']['path']) for c in animation['channels']}
        self.assertEqual(actual, {(name, 'rotation') for name in self.adapter.reverse} | {('root', 'translation')})
        for sampler in animation['samplers']:
            times = accessor(self.doc, self.data, sampler['input']).ravel()
            self.assertEqual(len(times), 301); self.assertEqual(times[-1], 5)
        skin = self.doc['skins'][0]
        inverse = accessor(self.doc, self.data, skin['inverseBindMatrices']).reshape(-1, 4, 4).swapaxes(-1, -2)
        np.testing.assert_allclose(inverse, [b['inverse'] for b in self.target], atol=1e-7)

    def test_GLB_samples_and_small_explained_loop_seam(self):
        for frame in [0, .5, 150, 299.5, 300]:
            expected = self.adapter.pose(frame)[1]
            np.testing.assert_allclose(sample_globals(self.doc, self.data, frame / 60)[:611], expected, atol=1e-5)
        a = self.adapter.pose(0)[1]; b = self.adapter.pose(300)[1]
        self.assertLess(np.linalg.norm(a[:, :3, 3] - b[:, :3, 3], axis=1).max(), .002)


if __name__ == '__main__':
    unittest.main()

