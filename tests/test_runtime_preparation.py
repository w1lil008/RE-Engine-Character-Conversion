"""Meaningful offline probe/analysis/conflict tests. Mocks are never live proof."""
import copy
import json
import math
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tools/runtime-probe-deps'))
from lupa.lua54 import LuaRuntime
from runtime_capture import analyze,load_capture,resource_path
from runtime_controller_graph import decode
from runtime_preflight import conflict_preview,rollback_preview,LOOSE
from runtime_preparation_protection import protect
from runtime_preparation_package import archive,with_manifest
from runtime_live_evidence import summarize,match_fsm_state
from source_animation_workflow import sha
from test_runtime_stage1 import capture_fixture


def to_python(value):
    if hasattr(value,'items'):
        items=dict(value.items())
        if not items: return None  # Match REFramework Json.cpp exactly for empty Lua tables.
        if set(items)==set(range(1,len(items)+1)): return [to_python(items[i]) for i in range(1,len(items)+1)]
        return {str(k):to_python(v) for k,v in items.items()}
    return value


class ProbeV2Tests(unittest.TestCase):
    def lua(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.globals().fixture_encode=lambda v,indent:json.dumps(to_python(v),ensure_ascii=False,indent=indent,sort_keys=True)
        def decode_json(text):
            try: return lua.table_from(json.loads(text),recursive=True)
            except (ValueError,TypeError): return None
        lua.globals().fixture_decode=decode_json
        lua.execute((ROOT/'tests/runtime_probe_v2_fixture.lua').read_text(encoding='utf-8'))
        lua.execute((ROOT/'scripts/runtime/bela_binding_probe_v7.lua').read_text(encoding='utf-8'))
        lua.execute('BelaBindingProbeV2=BelaBindingProbeV7')  # Fixture alias; exercises operational v7.
        return lua
    def start(self,lua):
        lua.execute('local p=BelaBindingProbeV2; p.prepare(); p.identity=true; assert(p.start())')

    def test_candidate_selection_and_verified_json_roundtrip(self):
        lua=self.lua(); self.start(lua)
        lua.execute('fixture_advance(0.21,12); assert(BelaBindingProbeV2.stop())')
        doc=to_python(lua.eval('fixture_result().doc'))
        result=analyze(doc)
        self.assertNotEqual(result['status'],'INVALID_CAPTURE',result)
        self.assertEqual(doc['schema'],'bela-runtime-binding-v2')
        self.assertEqual(lua.eval('#BelaBindingProbeV2.watches'),1)
        self.assertEqual(lua.eval('fixture_result().writes'),1)
        self.assertEqual(result['sample_count'],1)
        self.assertFalse(result['activation_ready'])

    def test_user_confirmation_is_required_before_start(self):
        lua=self.lua(); lua.execute('BelaBindingProbeV2.prepare(); assert(not BelaBindingProbeV2.start())')
        self.assertFalse(lua.eval('BelaBindingProbeV2.running'))

    def test_ambiguous_grace_candidate_is_not_auto_selected(self):
        lua=self.lua(); lua.execute('fixture_objects.scene:get_type_definition():get_method("findComponents").spec.fn=function() return fixture_array({fixture_objects.motion,fixture_objects.motion}) end; assert(not BelaBindingProbeV2.prepare())')
        self.assertEqual(lua.eval('#BelaBindingProbeV2.watches'),0)

    def test_missing_sdk_dependency_blocks_reads(self):
        lua=self.lua(); lua.execute('sdk.typeof=nil; BelaBindingProbeV2.prepare()')
        self.assertFalse(lua.eval('BelaBindingProbeV2.deps_ok'))
        self.assertEqual(lua.eval('#fixture_result().calls'),0)

    def test_absent_scene_and_empty_component_list_are_graceful(self):
        for code in ('sdk.call_native_func=function() return nil end',
            'fixture_objects.scene:get_type_definition():get_method("findComponents").spec.fn=function() return fixture_array({}) end'):
            lua=self.lua();lua.execute(code+'; BelaBindingProbeV2.prepare()')
            self.assertEqual(lua.eval('#BelaBindingProbeV2.candidates'),0)
            self.assertFalse(lua.eval('BelaBindingProbeV2.start()'))

    def test_null_layers_keep_actual_indices(self):
        lua=self.lua();lua.execute('local m=fixture_objects.motion:get_type_definition(); m:get_method("getLayerCount").spec.fn=function() return 2 end; m:get_method("getLayer").spec.fn=function(o,i) if i==1 then return fixture_objects.layer end end')
        self.start(lua);lua.execute('fixture_advance(0.21)')
        self.assertEqual(lua.eval('BelaBindingProbeV2.samples[1].watches[1].layers[2].index'),1)
        self.assertTrue(lua.eval('BelaBindingProbeV2.samples[1].watches[1].layers[1].object.unavailable'))

    def test_missing_node_count_does_not_guess_index_zero(self):
        lua=self.lua();lua.execute('fixture_objects.layer:get_type_definition():get_method("getMotionNodeCount").spec.fn=function() return nil end')
        self.start(lua);lua.execute('fixture_advance(0.21)')
        self.assertTrue(lua.eval('BelaBindingProbeV2.samples[1].watches[1].layers[1].node_count_unavailable'))
        self.assertNotIn('getMotionNode',list(lua.eval('fixture_result().calls').values()))

    def test_unchecked_sdk_save_failure_retains_capture_for_retry(self):
        lua=self.lua();self.start(lua)
        lua.execute('fixture_advance(0.21); fixture_save_failure=true; assert(not BelaBindingProbeV2.stop()); assert(not BelaBindingProbeV2.clear()); fixture_save_failure=false; assert(BelaBindingProbeV2.stop("retry"))')
        self.assertEqual(lua.eval('#BelaBindingProbeV2.samples'),1)
        self.assertTrue(lua.eval('BelaBindingProbeV2.saved_path:find("_2.json")~=nil'))

    def test_unsaved_capture_cannot_be_discarded_by_restart_or_rediscovery(self):
        lua=self.lua();self.start(lua)
        lua.execute('fixture_advance(0.21); fixture_save_failure=true; BelaBindingProbeV2.stop(); assert(not BelaBindingProbeV2.start()); BelaBindingProbeV2.discover(); assert(not BelaBindingProbeV2.prepare())')
        self.assertEqual(lua.eval('#BelaBindingProbeV2.samples'),1)
        self.assertEqual(lua.eval('#BelaBindingProbeV2.watches'),1)

    def test_corrupt_existing_capture_is_never_overwritten_and_stop_is_idempotent(self):
        lua=self.lua();lua.execute('fixture_files["bela_d2/20261010T000000Z_1.json"]="broken"')
        self.start(lua);lua.execute('fixture_advance(0.21); BelaBindingProbeV2.stop(); BelaBindingProbeV2.stop()')
        self.assertEqual(lua.eval('fixture_files["bela_d2/20261010T000000Z_1.json"]'),'broken')
        self.assertEqual(lua.eval('fixture_result().writes'),1)

    def test_glob_failure_does_not_attempt_save(self):
        lua=self.lua();self.start(lua)
        lua.execute('fixture_advance(0.21); fs.glob=function() error("filesystem unavailable") end; assert(not BelaBindingProbeV2.stop())')
        self.assertEqual(lua.eval('fixture_result().writes'),0)

    def test_keyboard_edge_markers_and_bounded_capture(self):
        lua=self.lua();lua.execute('BelaBindingProbeV2.prepare(); BelaBindingProbeV2.identity=true; BelaBindingProbeV2.keyboard=true; fixture_keys[0x75]=true; fixture_advance(0.21); fixture_keys[0x75]=false; fixture_keys[0x76]=true; fixture_advance(0.21); fixture_advance(0.21)')
        self.assertEqual(lua.eval('#BelaBindingProbeV2.markers'),2)
        self.assertEqual(lua.eval('BelaBindingProbeV2.samples[3].marker'),'walk')
        lua.execute('fixture_keys[0x76]=false; fixture_keys[0x77]=true; fixture_advance(0.21); fixture_advance(0.21)')
        self.assertFalse(lua.eval('BelaBindingProbeV2.running'))
        self.assertEqual(lua.eval('fixture_result().writes'),1)

    def test_cleanup_deduplication_and_failing_getter_bounds(self):
        lua=self.lua();self.start(lua);lua.execute('fixture_fail_getter(); fixture_advance(0.21); fixture_advance(0.21); BelaBindingProbeV2.stop(); assert(BelaBindingProbeV2.clear())')
        self.assertEqual(list(lua.eval('fixture_result().calls').values()).count('get_MotionName'),1)
        lua.execute((ROOT/'scripts/runtime/bela_binding_probe_v7.lua').read_text(encoding='utf-8'))
        self.assertEqual(lua.eval('fixture_result().registrations'),1)
        self.assertEqual(lua.eval('#BelaBindingProbeV2.watches'),0)

    def test_reflection_research_does_not_execute_mutators_or_wrong_signatures(self):
        lua=self.lua();self.start(lua);lua.execute('fixture_advance(0.21)')
        calls=list(lua.eval('fixture_result().calls').values())
        self.assertFalse(any(n.startswith(('set','change','create','register')) for n in calls))
        self.assertNotIn('get_State',calls);self.assertNotIn('get_Speed',calls)
        text=(ROOT/'scripts/runtime/bela_binding_probe_v7.lua').read_text(encoding='utf-8')
        for token in ('sdk.hook','sdk.create',':set_field(',':write_',':add_ref(',':release(','io.open'):
            self.assertNotIn(token,text)


class CaptureValidationTests(unittest.TestCase):
    def test_real_evidence_summary_rejects_mock_provenance(self):
        with self.assertRaises(ValueError):summarize(capture_fixture())

    def test_observed_fsm_resource_disambiguates_shared_fps_tps_ids(self):
        node={'hierarchy':'root/Default/NormalBreath','id':[1565925381,0],
            'fsm':{'name_hash':4197116285}}
        controllers=[{'path':'build/natives/stm/appsystem/fpsadd.motfsm2.45','nodes':[node]},
            {'path':'build/natives/stm/appsystem/tpsadd.motfsm2.45','nodes':[node]}]
        state={'observed_node_name':'Default.NormalBreath','observed_node_id_decimal':'1565925381',
            'observed_name_hash':4197116285}
        matches=match_fsm_state(state,['Resource[AppSystem/TPSAdd.motfsm2]'],controllers)
        self.assertEqual(len(matches),1);self.assertIn('tpsadd',matches[0]['controller'])
        self.assertFalse(match_fsm_state(state,[],controllers))
        for field,value in (('observed_node_name','Idle'),('observed_node_id_decimal','1'),('observed_name_hash',1)):
            changed=dict(state);changed[field]=value
            self.assertFalse(match_fsm_state(changed,['Resource[AppSystem/TPSAdd.motfsm2]'],controllers))

    def test_resource_change_with_same_bank_and_motion_id_is_visible(self):
        doc=capture_fixture()
        for i,sample in enumerate(doc['samples']):
            node=sample['watches'][0]['layers'][0]['nodes'][0]['observed']
            node['get_MotionID']=1
            node['get_MotionName']='GeneralS' if i<2 else 'GeneralM'
        result=analyze(doc)
        self.assertTrue(any('motion_name' in row['changed_fields'] for row in result['observed_state_changes']))
        self.assertFalse(result['activation_ready'])

    def test_live_bank_type_and_motion_name_are_kept_without_inventing_switch(self):
        doc=capture_fixture()
        for sample in doc['samples']:
            node=sample['watches'][0]['layers'][0]['nodes'][0]['observed']
            node.pop('get_SwitchValue',None);node['get_MotionBankType']=1048576
            node['get_MotionName']='ch0200_GeneralS_0001_Idle_Loop_VerB'
            node['get_MotionResourceDataLongId']=4503599627370497
        result=analyze(doc)
        self.assertEqual(result['idle_candidates'][0]['observed_bank_types'],[1048576])
        self.assertIsNone(result['idle_candidates'][0]['switch'])
        self.assertFalse(result['runtime_binding_verified'])

    def test_mock_sequence_detects_changes_but_never_live_proof(self):
        result=analyze(capture_fixture())
        self.assertEqual(len(result['observed_state_changes']),4)
        self.assertTrue(result['idle_candidates'][0]['review_candidate'])
        self.assertIn('Synthetic mock data cannot verify runtime binding',result['missing_evidence'])
        self.assertFalse(result['activation_ready']);self.assertFalse(result['runtime_binding_verified'])

    def test_malformed_nested_objects_report_errors_without_crashing(self):
        for value in (None,1,'bad',[],{'schema':'bela-runtime-binding-v2','read_only':True,'samples':[None,{'elapsed_clock':0,'watches':['bad']}]}):
            self.assertEqual(analyze(value)['status'],'INVALID_CAPTURE')
        doc=capture_fixture();doc['samples'][0]['watches'][0]['layers']='broken'
        self.assertEqual(analyze(doc)['status'],'INVALID_CAPTURE')

    def test_ids_booleans_references_nonfinite_and_backward_time_are_rejected(self):
        for field,value in (('get_MotionID',True),('get_SwitchValue',{'reference':{}}),('get_MotionBankID',-1),('get_Frame',math.nan)):
            doc=capture_fixture();doc['samples'][0]['watches'][0]['layers'][0]['nodes'][0]['observed'][field]=value
            self.assertEqual(analyze(doc)['status'],'INVALID_CAPTURE',(field,value))
        doc=capture_fixture();doc['samples'][1]['elapsed_clock']=-1
        self.assertEqual(analyze(doc)['status'],'INVALID_CAPTURE')

    def test_ambiguous_bank_ids_and_unknown_bank_are_not_inferred(self):
        doc=capture_fixture()
        for sample in doc['samples']:
            bank=copy.deepcopy(sample['watches'][0]['banks'][0]);bank['motion_list']['resource_string']='Animation/other.motlist'
            sample['watches'][0]['banks'].append(bank)
        result=analyze(doc);self.assertTrue(any('multiple' in m for m in result['missing_evidence']))
        doc=capture_fixture();doc['samples'][0]['watches'][0]['banks']=None
        self.assertTrue(analyze(doc)['unknown_banks'])

    def test_sdk_empty_arrays_missing_fields_and_loop_restart_are_reported(self):
        doc=capture_fixture();doc['api_errors']=None;doc['samples'][1]['watches'][0]['layers'][0]['nodes'][0]['observed']['get_Frame']=-1
        result=analyze(doc);self.assertEqual(len(result['possible_loop_wraps']),1)
        doc['samples'][1]['watches'][0]['layers'][0]['nodes']=None
        self.assertGreater(analyze(doc)['missing_fields']['layers_without_nodes'],0)

    def test_duplicate_keys_and_invalid_resource_references(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'bad.json'
            for text in ('{"samples":[],"samples":{}}','{"v":NaN}'):
                path.write_text(text)
                with self.assertRaises(ValueError):load_capture(path)
        for value in ('Animation/../secret.motlist','/Animation/a.motlist','Animation/a.motlist Animation/b.motlist','Animation/a.motlistgarbage','garbage'):
            self.assertIsNone(resource_path(value))
        self.assertEqual(resource_path('via.motion.MotionListResource[Animation/ch/x.motlist.1047]'),'animation/ch/x.motlist')

    def test_controller_helper_changes_and_api_signatures_are_separate_from_playback(self):
        doc=capture_fixture()
        for i,sample in enumerate(doc['samples']):
            sample['watches'][0]['components']=[{'object':{'type':'via.motion.MotionFsm2','address':'777'},
                'observed':{'get_CurrentState':'idle' if i<2 else 'moving','field:IKEnabled':True},'layers':None}]
        doc['api_catalog']=[{'type':'via.motion.MotionLayer','integration_method_candidates':[
            {'name':'changeMotion','parameters':['System.UInt32'],'count':1,'returns':'System.Void','static':False}]}]
        result=analyze(doc)
        self.assertEqual(len(result['component_state_helper_changes']),1)
        self.assertIn('field:IKEnabled',result['component_inventory'][0]['observed_fields'])
        self.assertFalse(result['reflected_integration_signatures'][0]['observed_call_success'])
        doc['api_catalog'][0]['integration_method_candidates'][0]['count']=2
        self.assertEqual(analyze(doc)['status'],'INVALID_CAPTURE')


class ProbeDiscoveryTests(unittest.TestCase):
    def test_verified_80_joint_controller_wins_over_render_siblings(self):
        lua=self.lua();lua.execute('''
        local m=fixture_objects.motion; m:get_type_definition():get_method("get_JointCount").spec.fn=function() return 80 end
        fixture_objects.go:get_type_definition():get_method("get_Name").spec.fn=function() return "cp_A100" end
        local render=fixture_obj(fixture_def("via.motion.RenderFixture", {get_JointCount=fixture_getter(611),
            get_GameObject=fixture_getter(fixture_obj(fixture_def("via.RenderGameObjectFixture", {get_Name=fixture_getter("Shadow")}))),
            get_ActiveMotionBank=fixture_getter(fixture_array({fixture_objects.bank}))}))
        fixture_objects.scene:get_type_definition():get_method("findComponents").spec.fn=function() return fixture_array({render,m}) end
        assert(BelaBindingProbeV3.prepare())
        ''')
        self.assertEqual(lua.eval('BelaBindingProbeV3.watches[1].selection.name'),'cp_A100')
        self.assertEqual(lua.eval('BelaBindingProbeV3.watches[1].selection.joint_count'),80)

    def test_all_twelve_blended_nodes_survive_capture(self):
        lua=self.lua();lua.execute('fixture_objects.layer:get_type_definition():get_method("getMotionNodeCount").spec.fn=function() return 12 end')
        ProbeV2Tests().start(lua);lua.execute('fixture_advance(0.21)')
        self.assertEqual(lua.eval('#BelaBindingProbeV3.samples[1].watches[1].layers[1].nodes'),12)
        self.assertFalse(lua.eval('BelaBindingProbeV3.truncation'))

    def test_primitive_bank_array_requires_typed_getter_not_pointer_read(self):
        for returns in ('System.UInt32','System.Object'):
            lua=self.lua();lua.execute('''
            local spec=fixture_getter(function(o,i) return 100+i end,{"System.Int32"});spec.returns="'''+returns+'''"
            local arr=fixture_obj(fixture_def("System.UInt32[]",{Get=spec}));arr.get_size=function() return 2 end
            arr.get_element=function() error("Primitive interpreted as pointer") end
            local m=fixture_objects.motion:get_type_definition();m.methods[#m.methods+1]=fixture_def("extra", {get_MotionBankIDTbl=fixture_getter(arr)}).methods[1]
            ''')
            ProbeV2Tests().start(lua);lua.execute('fixture_advance(0.21)')
            value=lua.eval('BelaBindingProbeV3.samples[1].watches[1].motion_bank_ids[1].value')
            self.assertEqual(value,100 if returns=='System.UInt32' else None)
            self.assertEqual(lua.eval('#BelaBindingProbeV3.errors'),0)

    def test_indexed_fsm_getters_check_signature_and_keep_integer_identity(self):
        lua=self.lua();lua.execute('''
        local function spec(value,returns) local s=fixture_getter(value,{"System.UInt32"});s.returns=returns;return s end
        local fsm=fixture_obj(fixture_def("via.motion.MotionFsm2",{
          getLayerCount=fixture_getter(2),getLayer=fixture_getter(fixture_objects.layer,{"System.UInt32"}),
          getCurrentNodeID=spec(4503599627370497,"System.UInt64"),
          getCurrentNodeName=spec(function(o,i) return "Idle"..i end,"System.String"),
          getCurrentNodeNameHash=spec(function() error("Wrong return type called") end,"System.Object")}))
        fixture_objects.go:get_type_definition():get_method("get_Components").spec.fn=function() return fixture_array({fsm}) end
        ''')
        ProbeV2Tests().start(lua);lua.execute('fixture_advance(0.21)')
        self.assertEqual(lua.eval('BelaBindingProbeV3.samples[1].watches[1].components[1].layers[2].observed.getCurrentNodeName'),'Idle1')
        self.assertEqual(lua.eval('BelaBindingProbeV3.samples[1].watches[1].components[1].layers[1].observed.getCurrentNodeID'),'4503599627370497')
        self.assertNotIn('getCurrentNodeNameHash',list(lua.eval('fixture_result().calls').values()))

    def lua(self):
        lua=ProbeV2Tests().lua()
        lua.execute((ROOT/'scripts/runtime/bela_binding_probe_v7.lua').read_text(encoding='utf-8'))
        lua.execute('BelaBindingProbeV3=BelaBindingProbeV7')
        return lua

    def test_failed_scene_diagnostic_preserves_exact_cause_and_saves_without_samples(self):
        lua=self.lua();lua.execute('sdk.call_native_func=function() return nil end; local p=BelaBindingProbeV3; assert(not p.prepare()); assert(p.status:find("Scene discovery failed")); assert(p.stop("discovery diagnostics"))')
        self.assertFalse(lua.eval('BelaBindingProbeV3.discovery.scene_returned'))
        doc=to_python(lua.eval('fixture_result().doc'))
        self.assertEqual(doc['discovery']['current_scene_method']['count'],0)
        self.assertNotEqual(analyze(doc)['status'],'INVALID_CAPTURE')

    def test_identity_failure_message_is_not_replaced_by_ambiguous_selection(self):
        lua=self.lua();lua.execute('reframework.get_game_name=function() return "other" end; BelaBindingProbeV3.prepare()')
        self.assertIn('identity mismatch',lua.eval('BelaBindingProbeV3.status'))
        self.assertEqual(lua.eval('#fixture_result().calls'),0)

    def test_live_diagnostic_type_catalog_includes_scene_and_manager_methods(self):
        lua=self.lua();lua.execute('BelaBindingProbeV3.prepare(); BelaBindingProbeV3.stop("discovery diagnostics")')
        doc=to_python(lua.eval('fixture_result().doc'))
        self.assertTrue(doc['discovery']['scene_returned'])
        self.assertEqual(doc['discovery']['component_array_size'],1)
        self.assertIn('via.SceneManager',[v['type'] for v in doc['api_catalog']])

    def test_player_after_256_environment_components_and_missing_active_bank_getter(self):
        lua=self.lua();lua.execute('''
        local env=fixture_obj(fixture_def("via.motion.EnvironmentFixture", {get_JointCount=fixture_getter(3),
            get_GameObject=fixture_getter(fixture_obj(fixture_def("via.EnvironmentGameObjectFixture", {get_Name=fixture_getter("environment")})))}))
        local player=fixture_objects.motion
        player:get_type_definition():get_method("get_ActiveMotionBank").spec.fn=function() return nil end
        fixture_objects.scene:get_type_definition():get_method("findComponents").spec.fn=function()
            local out={}; for i=1,416 do out[i]=env end;out[417]=player;return fixture_array(out) end
        BelaBindingProbeV3.prepare()
        ''')
        self.assertEqual(lua.eval('#BelaBindingProbeV3.candidates'),417)
        self.assertEqual(lua.eval('#BelaBindingProbeV3.watches'),1)
        self.assertEqual(lua.eval('BelaBindingProbeV3.watches[1].selection.joint_count'),611)


class OfflineIntegrationTests(unittest.TestCase):
    def test_accepted_all_phase_hashes_unchanged(self):
        self.assertEqual(protect()['status'],'PASSED')

    def test_controller_node_and_edge_reimport_matches_independent_reader(self):
        independent=json.loads((ROOT/'build/animation_v0.2.0/runtime_hardening/controller_graphs_reelib.json').read_text(encoding='utf-8'))
        lookup={c['file']:c for c in independent['controllers']}
        files=sorted((ROOT/'build/animation_v0.2.0/native_binding/extracted').rglob('*.motfsm2.45'))
        self.assertEqual(len(files),9)
        for path in files:
            actual=decode(path);expected=lookup[path.name]
            self.assertEqual(actual['sha256'],expected['sha256']);self.assertEqual(actual['node_count'],expected['node_count'])
            self.assertEqual(actual['node_table_end'],expected['node_table_end'])
            self.assertFalse(actual['unresolved_maps']);self.assertFalse(actual['unresolved_nodes'])
            for n,m in zip(actual['nodes'],expected['nodes']):
                for key in ('id','name','parent','attributes'):self.assertEqual(n[key],m[key])
                for key in ('states','all_states'):
                    self.assertEqual([{f:x[f] for f in ('target','map_id')} for x in n[key]],m[key])

    def test_controller_invalid_pointer_and_truncated_table_fail_closed(self):
        source=next((ROOT/'build/animation_v0.2.0/native_binding/extracted').rglob('*.motfsm2.45')).read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'broken.motfsm2.45'
            for data in (source[:200], source[:16]+struct.pack('<Q',len(source)+1)+source[24:]):
                path.write_bytes(data)
                with self.assertRaises(ValueError):decode(path)

    def test_conflict_and_rollback_owned_file_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            game=Path(folder);native=game/LOOSE;native.parent.mkdir(parents=True);native.write_bytes(b'candidate')
            original=game/'natives/original.mesh';original.write_bytes(b'protected')
            (game/'pak_mods').mkdir();(game/'pak_mods/unknown.pak').write_bytes(b'opaque')
            preview=conflict_preview(game,sha(native))
            self.assertEqual(len(preview['conflicts']),1);self.assertTrue(preview['opaque_mod_archive_files'])
            self.assertFalse(preview['install_allowed']);self.assertFalse(rollback_preview(game,preview)['removal_allowed_now'])
            native.write_bytes(b'changed')
            with self.assertRaises(ValueError):rollback_preview(game,preview)
            self.assertEqual(original.read_bytes(),b'protected')
            preview['prospective_loose_file']='../official.pak'
            with self.assertRaises(ValueError):rollback_preview(game,preview)

    def test_future_rollback_recovers_simulated_environment_without_other_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            game=Path(folder);protected=game/'original.pak';protected.write_bytes(b'official')
            before=sha(protected);preview=conflict_preview(game)
            self.assertFalse(preview['conflicts'])
            target=game/LOOSE;target.parent.mkdir(parents=True);target.write_bytes(b'new')
            preview['future_new_file']['sha256']=sha(target)
            plan=rollback_preview(game,preview);self.assertTrue(plan['owned_hash_matches'])
            target.unlink()  # Simulated, confined temporary directory only. No installer in production.
            self.assertFalse(rollback_preview(game,preview)['candidate_exists']);self.assertEqual(sha(protected),before)

    def test_inert_package_reproducibility_and_manifest_reimport(self):
        native=ROOT/'build/animation_v0.2.0/native_idle_canonical/native'
        files={'diagnostics/bela_binding_probe_v7.lua':(ROOT/'scripts/runtime/bela_binding_probe_v7.lua').read_bytes(),
            'resources/bela_idle.mot.983':(native/'bela_idle.mot.983').read_bytes(),
            'resources/bela_idle.motlist.1047':(native/'bela_idle.motlist.1047').read_bytes(),'README.txt':b'INERT'}
        files=with_manifest(files);payload=archive(files);self.assertEqual(payload,archive(files))
        import io
        with zipfile.ZipFile(io.BytesIO(payload)) as z:
            self.assertIsNone(z.testzip());manifest=json.loads(z.read('MANIFEST.json'))
            import hashlib
            for record in manifest['files']:
                self.assertEqual(hashlib.sha256(z.read(record['path'])).hexdigest(),record['sha256'])
        for path in ('natives/stm/replace.motlist.1047','reframework/autorun/play.lua','resources/official.pak','diagnostics/play.lua','../save.dat'):
            bad=dict(files);bad[path]=b'invalid'
            with self.assertRaises(ValueError):archive(bad)


if __name__=='__main__':unittest.main()

