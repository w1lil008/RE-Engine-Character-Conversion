"""Confined staging, rollback ownership and executable Lua syntax/gate checks."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tools/runtime-probe-deps'))
from lupa.lua54 import LuaRuntime
from runtime_experiment import stage,remove_owned,staging_gate,sample_plan
from runtime_experiment_evidence import analyze
from test_runtime_preparation import to_python

class ExperimentTests(unittest.TestCase):
    def mocked(self):
        lua=LuaRuntime();lua.globals().fixture_encode=lambda v,indent:json.dumps(to_python(v),sort_keys=True,indent=indent)
        lua.execute((ROOT/'tests/runtime_experiment_fixture.lua').read_text(encoding='utf-8'))
        module=lua.execute((ROOT/'scripts/runtime/bela_runtime_test.lua').read_text(encoding='utf-8'))
        module(lua.globals().fixture_config)
        return lua

    def test_cleanup_after_poll_retains_evidence_and_never_claims_decode(self):
        lua=self.mocked();lua.execute('fixture_advance(0);assert(fixture_native_calls==2);fixture_advance(3.1)')
        self.assertTrue(lua.eval('BelaRuntimeTest.holder_references_cleared'))
        self.assertEqual(lua.eval('#BelaRuntimeTest.resources'),0)
        lua.execute('fixture_advance(5.1)')
        self.assertEqual(lua.eval('BelaRuntimeTest.phase'),'HOLDER_CLEANUP_CALLBACKS_OBSERVED')
        docs=[json.loads(v) for _,v in lua.globals().fixture_files.items()]
        self.assertTrue(all(not d['loaded'] and not d['playback_performed'] and not d['registered'] for d in docs))
        self.assertEqual(len({d['phase'] for d in docs}),len(docs))

    def test_prerequisite_and_missing_loader_failures_are_bounded(self):
        for setup,expected_calls in [('fixture_config.resource_bridge_build_checked=false',0),
            ('fixture_missing_manager=true',0),('fixture_missing_resource=true',1),('fixture_bad_write=true',0),
            ('fixture_config.mode="playback"',0)]:
            lua=self.mocked();lua.execute(setup+';fixture_advance(0);fixture_advance(10)')
            self.assertEqual(lua.eval('BelaRuntimeTest.phase'),'BLOCKED')
            self.assertEqual(lua.eval('fixture_native_calls'),expected_calls)
            self.assertEqual(lua.eval('#BelaRuntimeTest.errors'),1)

    def test_control_arm_and_collision_preservation(self):
        lua=self.mocked();lua.execute('fixture_config.mode="control_only";fixture_files["bela_runtime_test/fixture_test_01_1.json"]="previous";fixture_advance(0)')
        self.assertEqual(lua.eval('fixture_native_calls'),1)
        self.assertEqual(lua.eval('fixture_files["bela_runtime_test/fixture_test_01_1.json"]'),'previous')

    def test_cleanup_blocks_resources_bound_to_playback(self):
        lua=self.mocked();lua.execute('fixture_advance(0);BelaRuntimeTest.registered=true;fixture_cleanup_ok=pcall(BelaRuntimeTest.cleanup)')
        self.assertFalse(lua.eval('fixture_cleanup_ok'))
        self.assertIsNotNone(lua.eval('BelaRuntimeTest.resources.BELA'))

    def test_standalone_queries_never_register_and_failed_control_skips_candidate(self):
        lua=self.mocked();lua.execute('fixture_config.query_standalone=true;fixture_advance(0);fixture_advance(3.1)')
        self.assertEqual(lua.eval('#fixture_bank_queries'),2)
        self.assertTrue(lua.eval('BelaRuntimeTest.bank_queries.BELA.has_dynamic_motion'))
        self.assertFalse(lua.eval('BelaRuntimeTest.registered'))
        self.assertTrue(lua.eval('BelaRuntimeTest.holder_references_cleared'))
        lua=self.mocked();lua.execute('fixture_config.query_standalone=true;fixture_control_query_fails=true;fixture_advance(0);fixture_advance(3.1)')
        self.assertEqual(lua.eval('#fixture_bank_queries'),1)
        self.assertIsNone(lua.eval('BelaRuntimeTest.bank_queries.BELA'))
        self.assertTrue(lua.eval('BelaRuntimeTest.holder_references_cleared'))
        self.assertEqual(lua.eval('#BelaRuntimeTest.errors'),1)

    def test_invalid_factory_session_or_resource_path_is_rejected_before_callbacks(self):
        for value in ('fixture_config.session="../save"','fixture_config.resource_path="Animation/ch/official.motlist"'):
            lua=LuaRuntime();lua.globals().fixture_encode=lambda v,indent:json.dumps(to_python(v),indent=indent)
            lua.execute((ROOT/'tests/runtime_experiment_fixture.lua').read_text(encoding='utf-8'))
            module=lua.execute((ROOT/'scripts/runtime/bela_runtime_test.lua').read_text(encoding='utf-8'))
            lua.execute(value)
            with self.assertRaises(Exception):module(lua.globals().fixture_config)
            self.assertIsNone(lua.globals().BelaRuntimeTest)

    def test_live_rejected_ownerless_route_is_disabled_before_callbacks(self):
        lua=LuaRuntime();lua.globals().fixture_encode=lambda v,indent:json.dumps(to_python(v),indent=indent)
        lua.execute((ROOT/'tests/runtime_experiment_fixture.lua').read_text(encoding='utf-8'))
        module=lua.execute((ROOT/'scripts/runtime/bela_runtime_test.lua').read_text(encoding='utf-8'))
        lua.execute('fixture_config.setup_unattached=true')
        with self.assertRaises(Exception):module(lua.globals().fixture_config)
        self.assertIsNone(lua.globals().BelaRuntimeTest)
        self.assertIsNone(lua.globals().fixture_frame)
        self.assertEqual(lua.eval('#fixture_scratch_mutations'),0)
        self.assertEqual(lua.eval('#fixture_bank_queries'),0)

    def test_runtime_owner_exception_releases_unbound_scratch_without_repeating_getter(self):
        lua=self.mocked();lua.execute('fixture_config.query_standalone=true;fixture_config.setup_owned_scene=true;fixture_owner_throws=true;fixture_advance(0);fixture_advance(3.1)')
        self.assertEqual(lua.eval('#fixture_scratch_mutations'),0)
        self.assertEqual(lua.eval('#fixture_bank_queries'),0)
        self.assertTrue(lua.eval('BelaRuntimeTest.holder_references_cleared'))
        self.assertTrue(lua.eval('fixture_owned_objects[1].destroyed'))
        self.assertEqual(lua.eval('#BelaRuntimeTest.errors'),1)

    def test_failed_diagnostic_write_does_not_prevent_unattached_reference_cleanup(self):
        lua=self.mocked();lua.execute('fixture_advance(0);fixture_bad_write=true;pcall(BelaRuntimeTest.cleanup)')
        self.assertTrue(lua.eval('BelaRuntimeTest.holder_references_cleared'))
        self.assertEqual(lua.eval('#BelaRuntimeTest.resources'),0)

    def test_owned_scene_component_requires_removal_api_and_destroys_only_its_objects(self):
        lua=self.mocked();lua.execute('fixture_config.query_standalone=true;fixture_config.setup_owned_scene=true;fixture_advance(0);fixture_advance(3.1)')
        self.assertEqual(lua.eval('#fixture_owned_objects'),2)
        self.assertTrue(lua.eval('fixture_owned_objects[1].destroyed and fixture_owned_objects[2].destroyed'))
        self.assertFalse(lua.eval('BelaRuntimeTest.registered'))
        self.assertTrue(lua.eval('BelaRuntimeTest.holder_references_cleared'))
        lua=self.mocked();lua.execute('fixture_config.query_standalone=true;fixture_config.setup_owned_scene=true;fixture_missing_destroy=true;fixture_advance(0);fixture_advance(3.1)')
        self.assertEqual(lua.eval('#fixture_owned_objects'),0)
        self.assertTrue(lua.eval('BelaRuntimeTest.holder_references_cleared'))

    def test_partial_owned_component_creation_failure_still_destroys_owned_object(self):
        lua=self.mocked();lua.execute('fixture_config.query_standalone=true;fixture_config.setup_owned_scene=true;fixture_component_failure=true;fixture_advance(0);fixture_advance(3.1)')
        self.assertEqual(lua.eval('#fixture_owned_objects'),1)
        self.assertTrue(lua.eval('fixture_owned_objects[1].destroyed'))
        self.assertEqual(lua.eval('#fixture_scratch_mutations'),0)

    def test_motion_info_on_owned_component_records_duration_without_decoding_claim(self):
        lua=self.mocked();lua.execute('fixture_config.query_standalone=true;fixture_config.setup_owned_scene=true;fixture_config.query_motion_info=true;fixture_advance(0);fixture_advance(3.1)')
        row=to_python(lua.eval('BelaRuntimeTest.bank_queries.BELA.motion_info'))
        self.assertTrue(row['query_result'])
        self.assertEqual(row['info']['values']['get_MotionEndFrame'],300)
        self.assertFalse(row['pose_decoding_verified'])
        self.assertTrue(lua.eval('fixture_owned_objects[1].destroyed and fixture_owned_objects[2].destroyed'))

    def test_sampling_is_bounded_control_first_and_cleans_new_containers(self):
        lua=self.mocked();lua.execute('fixture_config.query_standalone=true;fixture_config.setup_owned_scene=true;fixture_config.query_motion_info=true;fixture_config.sample_plan_path="fixture";fixture_config.native_sha256="fixture_hash";fixture_advance(0);fixture_advance(3.1);fixture_advance(.1)')
        rows=to_python(lua.eval('fixture_sample_calls'))
        self.assertEqual([r['hash'] for r in rows],[1,1,1,2,2,2])
        self.assertEqual(lua.eval('BelaRuntimeTest.sample_calls'),6)
        self.assertTrue(lua.eval('BelaRuntimeTest.holder_references_cleared'))
        self.assertTrue(lua.eval('fixture_owned_objects[1].destroyed and fixture_owned_objects[2].destroyed'))
        self.assertFalse(lua.eval('BelaRuntimeTest.playback'))

    def test_isolated_layer_growth_selection_and_cleanup_preserve_references(self):
        lua=self.mocked();lua.execute('fixture_config.mode="control_only";fixture_config.isolated_layer_test=true;fixture_config.query_standalone=true;fixture_config.setup_owned_scene=true;fixture_config.query_motion_info=true;fixture_advance(0);fixture_advance(3.1)')
        evidence=to_python(lua.eval('BelaRuntimeTest.layer_evidence'))
        self.assertEqual(evidence['bank_id'],65000)
        self.assertTrue(evidence['grow_preserved_references'] and evidence['shrink_preserved_reference'])
        self.assertFalse(evidence['character_changed'])
        self.assertTrue(lua.eval('fixture_owned_objects[1].destroyed and BelaRuntimeTest.holder_references_cleared'))
        self.assertEqual(lua.eval('#BelaRuntimeTest.errors'),0)

    def test_layer_array_reset_blocks_selection_and_cleans_owned_object(self):
        lua=self.mocked();lua.execute('fixture_config.mode="control_only";fixture_config.isolated_layer_test=true;fixture_config.query_standalone=true;fixture_config.setup_owned_scene=true;fixture_config.query_motion_info=true;fixture_layers_reset=true;fixture_advance(0);fixture_advance(3.1)')
        self.assertIsNone(lua.eval('BelaRuntimeTest.layer_evidence'))
        self.assertEqual(lua.eval('#BelaRuntimeTest.errors'),1)
        self.assertTrue(lua.eval('fixture_owned_objects[1].destroyed and BelaRuntimeTest.holder_references_cleared'))

    def test_failed_control_decoding_prevents_candidate_decoding_and_cleans(self):
        lua=self.mocked();lua.execute('fixture_config.query_standalone=true;fixture_config.setup_owned_scene=true;fixture_config.query_motion_info=true;fixture_config.sample_plan_path="fixture";fixture_config.native_sha256="fixture_hash";fixture_sample_failure=true;fixture_advance(0);fixture_advance(3.1);fixture_advance(.1)')
        self.assertEqual(lua.eval('#fixture_sample_calls'),1)
        self.assertEqual(lua.eval('fixture_sample_calls[1].hash'),1)
        self.assertTrue(lua.eval('BelaRuntimeTest.holder_references_cleared'))
        self.assertEqual(lua.eval('#BelaRuntimeTest.errors'),1)

    def test_live_staging_cannot_attach_to_grace_or_skip_metadata_gate(self):
        staging_gate(True,True,'resource_only',True,True)
        staging_gate(False,False,'load_only',False,False)
        for args in [(True,False,'resource_only',True,True),(True,True,'load_only',True,True),
                     (False,True,'resource_only',False,True),(True,True,'resource_only',True,False)]:
            with self.assertRaises(ValueError):staging_gate(*args)

    def test_sample_plan_covers_all_native_channels_and_fractional_timing(self):
        plan=sample_plan();arm=plan['arms'][1]
        self.assertEqual(len(arm['tracks']),24)
        self.assertEqual(arm['frames'],[i*.5 for i in range(601)])
        self.assertEqual(len({t['hash'] for t in arm['tracks']}),24)
        self.assertEqual(sum(t['rotation'] for t in arm['tracks']),24)
        self.assertEqual(sum(t['translation'] for t in arm['tracks']),1)
        self.assertFalse(any(t['scale'] for t in arm['tracks']))

    def test_analysis_preserves_partial_evidence_and_rejects_false_compatibility_claims(self):
        lua=self.mocked();lua.execute('fixture_advance(0);fixture_advance(3.1);fixture_advance(5.1)')
        docs=[json.loads(v) for _,v in lua.globals().fixture_files.items()]
        doc=next(d for d in docs if d['phase']=='HOLDER_CLEANUP_CALLBACKS_OBSERVED')
        result=analyze(doc)
        self.assertEqual(result['status'],'PARTIAL_LOAD_EVIDENCE')
        self.assertTrue(result['cleanup_callbacks_observed'])
        self.assertFalse(result['activation_ready'])
        for key,value in [('loaded',True),('playback_performed',True),('registered',1),('heartbeat_frames',True)]:
            modified=dict(doc);modified[key]=value
            self.assertEqual(analyze(modified)['status'],'INVALID_CAPTURE')
        modified=dict(doc);modified['resources']={'BELA':{'values':{'get_ResourcePath':'Animation/ch/other.motlist'}}}
        self.assertEqual(analyze(modified)['status'],'INVALID_CAPTURE')
        modified=dict(doc);modified['events']=[{}]*151
        self.assertEqual(analyze(modified)['status'],'INVALID_CAPTURE')
    def test_fresh_owned_file_and_exact_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.write_bytes(b'animation')
            protected=root/'official.pak';protected.write_bytes(b'protected')
            record=stage(root,source,'test_session_01')
            with self.assertRaises(FileExistsError):stage(root,source,'test_session_01')
            result=remove_owned(root,record,False)
            self.assertEqual(result['preexisting_files_removed'],0)
            self.assertFalse((root/record['relative_path']).exists())
            self.assertEqual(protected.read_bytes(),b'protected')

    def test_running_game_or_changed_owned_file_blocks_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.write_bytes(b'animation')
            record=stage(root,source,'test_session_02')
            with self.assertRaises(ValueError):remove_owned(root,record,True)
            (root/record['relative_path']).write_bytes(b'changed')
            with self.assertRaises(ValueError):remove_owned(root,record,False)
            self.assertTrue((root/record['relative_path']).exists())

    def test_scope_traversal_and_original_paths_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.write_bytes(b'animation')
            for session in ('../save','test/a','TEST_SESSION'):
                with self.assertRaises(ValueError):stage(root,source,session)
            record=stage(root,source,'test_session_03');record['relative_path']='official.pak'
            with self.assertRaises(ValueError):remove_owned(root,record,False)

    def test_lua_module_compiles_without_runtime_side_effects(self):
        lua=LuaRuntime();module=lua.execute((ROOT/'scripts/runtime/bela_runtime_test.lua').read_text(encoding='utf-8'))
        self.assertTrue(callable(module));self.assertIsNone(lua.globals().BelaRuntimeTest)
        text=(ROOT/'scripts/runtime/bela_runtime_test.lua').read_text(encoding='utf-8')
        for token in ('sdk.hook',':write_',':set_field(','changeMotion(','setDynamicMotionBank('):
            self.assertNotIn(token,text)

if __name__=='__main__':unittest.main()

