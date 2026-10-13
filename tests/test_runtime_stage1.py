"""D1 instrumentation tests use Lua 5.4 mocks, never assert engine compatibility."""
import copy
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tools/runtime-probe-deps'))
from lupa.lua54 import LuaRuntime
from runtime_stage1 import protect_checkpoint, parse_joint_map, normalize_resource, summarize_capture


def capture_fixture():
    sample = {'marker': 'idle', 'elapsed_clock': 0, 'watches': [{'role': 'body',
        'selection': {'name': 'fixture Grace', 'object': {'address': '42'}},
        'banks': [{'observed': {'get_BankID': 0, 'get_BankType': 0, 'get_BankTypeMask': 0},
            'motion_list': {'resource_string': 'Animation/ch/ch02/ch0200/motlist/ch0200_GeneralM.motlist'}}],
        'layers': [{'index': 0, 'observed': {}, 'nodes': [{'index': 0, 'observed': {
            'get_MotionBankID': 0, 'get_MotionID': 0, 'get_SwitchValue': 0,
            'get_Frame': 0, 'get_JointMaskID': 0}}]}]}]}
    samples = []
    for i, marker in enumerate(('idle', 'idle', 'walk', 'idle_after_walk', 'aim', 'idle_after_aim')):
        row = copy.deepcopy(sample); row['marker'] = marker; row['elapsed_clock'] = i
        values = row['watches'][0]['layers'][0]['nodes'][0]['observed']
        values['get_Frame'] = i * 12
        values['get_MotionID'] = {'walk': 2, 'aim': 3}.get(marker, 0)
        samples.append(row)
    return {'schema': 'bela-runtime-binding-v1', 'read_only': True, 'synthetic_fixture': True,
        'runtime_identity': {'game': 're9', 'tdb_version': 83, 'reframework_commit': 'd1461375aee4ec3f313170f8eaad12064eb542d9'},
        'grace_identity_user_confirmed': True, 'context': 'test fixture', 'samples': samples,
        'truncation': False, 'api_errors': []}


class RuntimeStage1Tests(unittest.TestCase):
    def lua(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ROOT / 'tests/runtime_probe_fixture.lua').read_text(encoding='utf-8'))
        lua.execute((ROOT / 'scripts/runtime/bela_binding_probe.lua').read_text(encoding='utf-8'))
        return lua

    def test_lua_discovery_and_capture_do_not_write_engine_or_create_resources(self):
        lua = self.lua()
        lua.execute('BelaBindingProbe.discover(); assert(#BelaBindingProbe.candidates == 1); BelaBindingProbe.watch(1, "body"); BelaBindingProbe.start(); fixture_advance(0.21, 12); BelaBindingProbe.stop()')
        result = lua.eval('fixture_result()')
        self.assertEqual(result['writes'], 1)  # Diagnostic JSON only.
        names = list(result['calls'].values())
        self.assertIn('get_MotionID', names); self.assertIn('findComponents', names)
        self.assertFalse(any(n.startswith(('set_', 'change', 'add', 'create', 'register')) for n in names))
        self.assertNotIn('get_State', names); self.assertNotIn('get_Speed', names)
        self.assertEqual(lua.eval('#BelaBindingProbe.samples'), 1)

    def test_sampling_is_bounded_and_stops_without_repeated_dumping(self):
        lua = self.lua()
        lua.execute('BelaBindingProbe.discover(); BelaBindingProbe.watch(1); BelaBindingProbe.max_samples = 2; BelaBindingProbe.start(); fixture_advance(0.21); fixture_advance(0.21); fixture_advance(0.21); fixture_advance(0.21)')
        self.assertEqual(lua.eval('#BelaBindingProbe.samples'), 2)
        self.assertEqual(lua.eval('fixture_result().writes'), 1)
        self.assertFalse(lua.eval('BelaBindingProbe.running'))

    def test_capture_records_motion_and_action_markers(self):
        lua = self.lua()
        lua.execute('BelaBindingProbe.discover(); BelaBindingProbe.watch(1, "body"); BelaBindingProbe.start(); fixture_advance(0.21, 12, 0); BelaBindingProbe.mark("walk"); fixture_advance(0.21, 24, 2)')
        self.assertEqual(lua.eval('BelaBindingProbe.samples[2].marker'), 'walk')
        self.assertEqual(lua.eval('BelaBindingProbe.samples[2].watches[1].layers[1].nodes[1].observed.get_MotionID'), 2)

    def test_loading_twice_does_not_duplicate_callbacks(self):
        lua = self.lua()
        lua.execute((ROOT / 'scripts/runtime/bela_binding_probe.lua').read_text(encoding='utf-8'))
        self.assertEqual(lua.eval('fixture_result().registrations'), 1)

    def test_wrong_game_blocks_scene_queries(self):
        lua = self.lua()
        lua.execute('reframework.get_game_name = function() return "re8" end; BelaBindingProbe.discover()')
        self.assertEqual(lua.eval('#BelaBindingProbe.candidates'), 0)
        self.assertEqual(lua.eval('#fixture_result().calls'), 0)

    def test_changed_framework_or_tdb_blocks_scene_queries(self):
        for code in ('reframework.get_commit_hash = function() return "other" end', 'sdk.get_tdb_version = function() return 82 end'):
            lua = self.lua(); lua.execute(code + '; BelaBindingProbe.discover()')
            self.assertEqual(lua.eval('#fixture_result().calls'), 0)

    def test_live_identity_is_distinct_from_expected_exe_build(self):
        lua = self.lua(); lua.execute('BelaBindingProbe.discover()')
        doc = lua.eval('BelaBindingProbe.document()')
        self.assertEqual(doc['runtime_identity']['game'], 're9')
        self.assertEqual(doc['runtime_identity']['tdb_version'], 83)
        self.assertTrue(doc['build_identifiers_are_expectations_not_runtime_measurements'])

    def test_failing_engine_getter_is_disabled_after_one_attempt(self):
        lua = self.lua()
        lua.execute('BelaBindingProbe.discover(); BelaBindingProbe.watch(1); fixture_fail_getter(); BelaBindingProbe.start(); fixture_advance(0.21); fixture_advance(0.21)')
        calls = list(lua.eval('fixture_result().calls').values())
        self.assertEqual(calls.count('get_MotionName'), 1)
        self.assertEqual(lua.eval('#BelaBindingProbe.errors'), 1)

    def test_wall_timeout_stops_capture_without_further_reads(self):
        lua = self.lua()
        lua.execute('BelaBindingProbe.discover(); BelaBindingProbe.watch(1); BelaBindingProbe.start(); fixture_advance(121)')
        self.assertEqual(lua.eval('#BelaBindingProbe.samples'), 0)
        self.assertEqual(lua.eval('BelaBindingProbe.stop_reason'), 'capture limit')

    def test_missing_getters_are_reported_not_fabricated(self):
        lua = self.lua(); lua.execute('BelaBindingProbe.discover(); BelaBindingProbe.watch(1); BelaBindingProbe.start(); fixture_advance(0.21)')
        self.assertGreater(lua.eval('#BelaBindingProbe.catalog[1].missing_zero_getters'), 0)
        self.assertIsNone(lua.eval('BelaBindingProbe.samples[1].watches[1].motion.observed.get_MotionID'))

    def test_script_has_no_hooks_raw_memory_writes_or_resource_loading(self):
        text = (ROOT / 'scripts/runtime/bela_binding_probe.lua').read_text(encoding='utf-8')
        for token in ('sdk.hook', 'sdk.create', ':set_field(', ':write_', ':add_ref(', ':release(', 'io.open', 'set_PuppetMode'):
            self.assertNotIn(token, text)

    def test_resource_paths_normalize_without_confusing_ids(self):
        self.assertEqual(normalize_resource('Resource[Animation/ch/ch02/ch0200/MOTLIST/ch0200_GeneralM.motlist]'),
            'animation/ch/ch02/ch0200/motlist/ch0200_generalm.motlist')
        self.assertIsNone(normalize_resource('bank 0'))

    def test_synthetic_capture_cannot_establish_live_binding(self):
        result = summarize_capture(capture_fixture())
        self.assertFalse(result['actual_runtime_binding_verified'])
        self.assertIn('A real engine capture; this input is synthetic', result['missing_evidence'])
        self.assertGreater(len(result['observed_changes']), 0)

    def test_missing_switch_mask_and_bank_path_block_binding(self):
        data = capture_fixture(); data['synthetic_fixture'] = False
        for row in data['samples']:
            w = row['watches'][0]; w['banks'] = []
            n = w['layers'][0]['nodes'][0]['observed']; del n['get_SwitchValue']; del n['get_JointMaskID']
        result = summarize_capture(data)
        self.assertIn('Observed scalar switch', result['missing_evidence'])
        self.assertIn('Unambiguous loaded MOTLIST path and bank descriptor', result['missing_evidence'])

    def test_undecoded_switch_reference_stays_unresolved(self):
        data = capture_fixture()
        for row in data['samples']:
            row['watches'][0]['layers'][0]['nodes'][0]['observed']['get_SwitchValue'] = {'reference': {'type': 'unknown'}}
        result = summarize_capture(data)
        self.assertIn('Observed scalar switch', result['missing_evidence'])

    def test_non_diagnostic_document_rejected(self):
        with self.assertRaises(ValueError): summarize_capture({'schema': 'other', 'read_only': True})
        with self.assertRaises(ValueError): summarize_capture({'schema': 'bela-runtime-binding-v1', 'read_only': False})

    def test_protected_accepted_checkpoint_unchanged(self):
        result = protect_checkpoint(); self.assertEqual(result['status'], 'PASSED')
        self.assertEqual(result['milestone_C_artifacts_and_sources'], 69)

    def test_joint_map_bounds_and_original_map_decode(self):
        files = list((ROOT / 'build/animation_v0.2.0/runtime_stage1/joint_maps').rglob('*.jmap.28'))
        self.assertEqual(len(files), 2)
        for p in files:
            result = parse_joint_map(p); self.assertEqual(result['version'], 28)
            ids = [r['group_id'] for r in result['joint_mask_groups']]
            self.assertEqual(len(ids), len(set(ids)))
        with self.assertRaises(ValueError): parse_joint_map(ROOT / 'config/project.json')

    def test_independent_original_mask_hashes_bytes_and_weights_agree(self):
        result = json.loads((ROOT / 'reports/runtime_binding_v0.2.0/joint_map_reimport.json').read_text())
        self.assertEqual(result['status'], 'PASSED')
        self.assertEqual([m['joint_mask_groups'] for m in result['maps']], [60, 4])
        self.assertTrue(all(m['all_decoded_mask_hashes_bytes_weights_equal'] for m in result['maps']))


if __name__ == '__main__': unittest.main()

