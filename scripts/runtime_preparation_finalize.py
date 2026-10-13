"""Offline validation/evidence/package builder. Never installs or launches anything."""
import io
import json
import subprocess
import unittest
import zipfile
from pathlib import Path
from common import ROOT,write_json,confined
from source_animation_workflow import sha
from runtime_preparation_protection import protect
from runtime_preflight import check,NATIVE,LOOSE,RUNTIME
from runtime_preparation_package import archive,with_manifest

REPORTS=ROOT/'reports/runtime_preparation_v0.2.0'
OUTPUT=ROOT/'build/animation_v0.2.0/runtime_hardening'
PACKAGE=ROOT/'dist/BelaGrace_RuntimePreparation_0.2.0_OfflineHardened.zip'


def static_summary():
    raw=json.loads((OUTPUT/'controller_graphs.json').read_text(encoding='utf-8'))
    independent=json.loads((OUTPUT/'controller_graphs_reelib.json').read_text(encoding='utf-8'))
    other={c['file']:c for c in independent['controllers']};summary=[]
    for controller in raw['controllers']:
        expected=other[Path(controller['path']).name]
        if controller['sha256']!=expected['sha256'] or controller['node_table_end']!=expected['node_table_end']:
            raise ValueError('Independent controller mismatch')
        for a,b in zip(controller['nodes'],expected['nodes']):
            for k in ('id','name','parent','attributes'):
                if a[k]!=b[k]:raise ValueError('Independent controller node mismatch')
            for k in ('states','all_states'):
                if [{f:x[f] for f in ('target','map_id')} for x in a[k]]!=b[k]:raise ValueError('Independent controller state edge mismatch')
        selected=[]
        for e in controller['edges']:
            if any(h in e['source'].lower() for h in ('root/idle/','root/holdidle/','root/weapon/holdstart/','root/weapon/inhibitaim/')):
                selected.append(e)
        if not selected:selected=controller['relevant_edges_by_label_inference']
        summary.append({'path':controller['path'],'sha256':controller['sha256'],'nodes':controller['node_count'],
            'edges':len(controller['edges']),'transition_records':controller['transition_record_count'],'map_entries':controller['map_count'],
            'unresolved_edge_targets':len(controller['unresolved_nodes']),'unresolved_map_ids':len(controller['unresolved_maps']),
            'representative_edges':selected[:12],'selection_is_label_based_inference':True,
            'independently_equal_node_identifiers_names_parents_attributes_and_state_edges':True})
    return {'status':'STATIC_GRAPH_VALIDATED','controllers':summary,'nodes':sum(c['nodes'] for c in summary),
        'edges':sum(c['edges'] for c in summary),'transition_records':sum(c['transition_records'] for c in summary),
        'full_diagnostics':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)} for p in
            (OUTPUT/'controller_graphs.json',OUTPUT/'controller_graphs_reelib.json')],
        'typed_RSZ_actions_conditions_decoded':False,'static_bank_to_motion_binding_added':False,
        'missing':'Build-matched RSZ schema and motion selection condition semantics; current TPS resource/node observations are in live_binding_evidence.json',
        'scope':'Verified named node/edge/map links; live current states are separately corroborated, condition semantics remain unresolved'}


def evidence():
    files=[]
    for repo,revision,names in [
        ('REFramework','d1461375aee4ec3f313170f8eaad12064eb542d9',[
            'src/mods/bindings/Sdk.cpp','src/mods/bindings/Fs.cpp','src/mods/bindings/Json.cpp',
            'src/mods/ScriptRunner.cpp','src/mods/tools/ObjectExplorer.cpp','shared/sdk/ResourceManager.cpp']),
        ('EMV-Engine','a8a89961fde640d542afc72bd66fd8e12f3b82b3',['EMV Engine/reframework/autorun/EMV Engine/init.lua']),
        ('RE-Engine-Lib','ceb0d2fbe9d76f29c552e4c56f4fd8cd87a165ef',[
            'REE-Lib/RszFile/BhvtFile.cs','REE-Lib/RszFile/Motfsm2File.cs'])]:
        folder=ROOT/'tools/research'/repo
        current=subprocess.check_output(['git','-C',str(folder),'rev-parse','HEAD'],text=True).strip()
        if current!=revision:raise ValueError('Pinned research revision changed')
        for name in names:files.append({'repository':repo,'revision':revision,'path':name,'sha256':sha(folder/name)})
    return {'status':'PINNED_IMPLEMENTATIONS_REVIEWED','files':files,
        'verified_framework_exports':['Reflection (types/methods/parameters/fields)','Manual ScriptRunner file loading',
            'Read-only game/commit/TDB identity','is_key_down','json dump/load and fs glob/read',
            'REResource.create_holder / create_holder_global (not exercised)'],
        'JSON_findings':['Empty Lua tables serialize as null','dump_string defaults compact; dump_file defaults four-space indentation',
            'dump_file returns true without stream error check; probe explicitly matches four-space output against fs.read and load_file'],
        'dynamic_bank_findings':['EMV example requires MotionListResourceHolder, not a bare REResource',
            'EMV helper uses write_qword(0x10); no guessed memory offset is reused',
            'Pinned SDK exposes Resource.create_holder(holderType); RE9 type and lifetime need live verification',
            'set_OverwriteBankID(true) is part of older dynamic-bank example; RE9 signatures reflected live; setters and lifetime unexercised',
            'ResourceManager scans engine functions at runtime; SDK export existence does not verify RE9 loader readiness',
            'Live framework startup reports LooseFileLoader via.io.file and path_to_hash discovery failures; fresh loose MOTLIST loading is not established'],
        'engine_getters_observed_in_RE9':True,'live_probe_executed_by_agent':True,'dynamic_bank_mutators_invoked':False}


def strategy():
    return {'stage':'D1_HARDENED_WITH_PARTIAL_LIVE_BINDING','activation_authorized':False,'integration_harness_included':False,
        'preferred_method':'Fresh MOTLIST path, component-local dynamic bank only after live signature/ownership evidence',
        'runtime_resource_path':RUNTIME,'prospective_loose_file':LOOSE,
        'native_assets':[{'file':name,'sha256':sha(NATIVE/name),'bytes':(NATIVE/name).stat().st_size} for name in ('bela_idle.mot.983','bela_idle.motlist.1047')],
        'native_embedded_motlist_self_contained':True,'standalone_mot_is_inspection_artifact_only':True,
        'joint_map_reference':'GameAssets/Character/CharacterPrefab/cp_A1/cp_A100/JointMap/cp_A1JointMap_ForConvert.jmap',
        'actual_live_idle':{'bank_asset':'Animation/ch/ch02/ch0200/motbank/ch0200.motbank','bank_id':0,'motion_id':1,'layer':0,'joint_mask':0,'switch_observed':None,'contexts':'GeneralS during user Requiem capture; GeneralM after holstering in agent Guard Office capture','resource_selection_depends_on_context':True,'direct_MOTLIST_reference_observed':False,
            'observed_TPS_idle_FSM':{'resource':'AppSystem/Character/CharacterPrefab/PlayerCommon/Subtype/TPS/MotionFsm/TPSBase.motfsm2','layer':0,'node':'Idle.new state 6DD29B56.Idle','id_decimal':'1962794700','name_hash':3389212796},
            'observed_TPS_breath_FSM':{'resource':'AppSystem/Character/CharacterPrefab/PlayerCommon/Subtype/TPS/MotionFsm/TPSAdd.motfsm2','layer':8,'node':'Default.NormalBreath','id_decimal':'1565925381','name_hash':4197116285}},
        'prototype_local_only':{'motion_id':0,'switch':0,'frames':[0,300],'fps':60,'seconds':5,'events':0},
        'fresh_dynamic_bank_id':None,'root_policy':'Accepted periodic sway/floor offset, no accumulated root locomotion',
        'full_quaternion_tracks':['R_Arm_Clavicle','L_Leg_Upper'],'full_quaternion_mode':'0x00000',
        'full_quaternion_runtime_support_verified':False,
        'required_live_API_evidence':[
            'Supported fresh resource overlay mechanism: installed LooseFileLoader reports startup discovery failures; do not infer readiness from working character assets',
            'Motion getDynamicMotionBankCount/getDynamicMotionBank; exact parameter and return types',
            'Motion setDynamicMotionBankCount/setDynamicMotionBank; construction, append and restoration semantics',
            'DynamicMotionBank set_MotionList (holder parameter), set_BankID, set_OverwriteBankID, constructor',
            'Actual MotionListResourceHolder definition and SDK holder bridge compatibility/lifetime',
            'Layer changeMotion overload and live controller/layer ownership',
            'Verified one-cycle termination, original controller resume or immediate process-exit fallback',
            'Mask/helper/IK effects and FPS/TPS object identities; no guessed mask-zero meaning'],
        'guarded_registration_spec':[
            'Record selected object address/layer/original bank count and all existing dynamic entries',
            'Choose a free component-local bank ID from live enumeration; do not guess or reuse ID 0',
            'Use supported SDK holder creation, never EMV raw memory write',
            'Append a new entry without touching existing slots; record ownership',
            'Do not force puppet/controller modes, modify masks, hook transitions or request play every frame',
            'If verified one-shot request is immediately overwritten by FSM, abort and investigate'],
        'load_logging_spec':['Resource path and source hash/build/framework identity before request',
            'Resource/holder null or type mismatch, loader error messages, timeout; stop before registration',
            'Pre/post bank inventory, selected tuple, frame progress, original controller resumption'],
        'A_E_experiment':[
            'A: Fresh-path load only; confirm matching resource and one MOT, no playback',
            'B: Compare engine-sampled clavicle/thigh XYZW at all 301 keys and 300 midpoint poses if read-only native sampling API exists; gate 50 micrometres world-position / 0.05 degree rotation',
            'B fallback: If no engine sampler exists, disclose that numerical runtime decoding remains unverified; separately authorize combined B/C and inspect characteristic clavicle/thigh poses',
            'C: Exactly one 300-frame/60-FPS cycle in an independently verified non-critical layer/state; no indefinite looping',
            'D: Original idle resumes; walk/aim/reload/interaction interrupt cleanly without forcing frames or layers',
            'E: Exit game; hash-check/remove only new loose MOTLIST; restart and confirm original behaviour'],
        'alternative_method':'One-slot overlay of live-proven source MOTLIST only if dynamic route fails; no candidate slot selected now',
        'overlay_dependencies':['Prove exact live bank/type/mask/list/slot first','Preserve all unrelated clips/aliases/shared rest tables/index words',
            'Actual live base idle is one frame; separate L8 additive is 1136 GeneralS / 666 GeneralM frames. Do not replace base and additive blindly','814-frame GeneralM Idle_caution used for C roundtrip was not the observed base idle; its 90 events are not automatically transferred',
            'Separate manifest/ownership/conflict/rollback and authorization before install'],
        'ready_for_read_only_capture':True,'ready_for_authorized_playback_now':False}


def main():
    REPORTS.mkdir(exist_ok=True);before=protect()
    write_json(REPORTS/'controller_analysis.json',static_summary())
    write_json(REPORTS/'sdk_verification.json',evidence())
    write_json(REPORTS/'integration_strategy.json',strategy())
    rebuilt=ROOT/'build/animation_v0.2.0/native_runtime_hardening_verify_2'
    native_report=json.loads((rebuilt/'workflow_report.json').read_text(encoding='utf-8'))
    for name in ('bela_idle.mot.983','bela_idle.motlist.1047'):
        if sha(rebuilt/'native'/name)!=sha(NATIVE/name):raise ValueError('Fresh native rebuild differs from accepted C')
    write_json(REPORTS/'native_rebuild.json',{'status':'PASSED','fresh_output':rebuilt.relative_to(ROOT).as_posix(),
        'original_roundtrip':native_report['roundtrip'],'native_reimport':native_report['reimport'],
        'native_outputs_byte_identical_to_accepted_C':True,'accepted_C_references_modified':False,'runtime_tested':False})
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
    (REPORTS/'automated_tests.log').write_text(log.getvalue(),encoding='utf-8')
    tests={'status':'PASSED' if result.wasSuccessful() else 'FAILED','tests_run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),
        'probe_scope':'Lua 5.4 mocks and offline structural tests. Real v6/v7 getter captures are separate evidence; no converted animation playback'}
    write_json(REPORTS/'automated_tests.json',tests)
    if not result.wasSuccessful() or result.skipped:raise ValueError('Full suite failed; see new test log')
    current=check();write_json(REPORTS/'preflight_after.json',current)
    if current['changed_protected_files'] or current['missing_protected_files']:raise ValueError('Protected installed file changed')
    # User may now launch/play RE9 to run the read-only capture. Its ordinary save
    # writes are recorded, never restored or blamed on offline tooling.
    files={'README.txt':('INERT OFFLINE PREPARATION — no installer/autorun/playback harness.\n'
        'Extract only to a workspace. Run diagnostics/bela_binding_probe_v7.lua manually through REFramework.\n'
        'Do not copy resources into RE9 or a mod manager. Playback requires live evidence and separate authorization.\n').encode(),
        'diagnostics/bela_binding_probe_v7.lua':(ROOT/'scripts/runtime/bela_binding_probe_v7.lua').read_bytes()}
    for name in ('bela_idle.mot.983','bela_idle.motlist.1047'):files['resources/'+name]=(NATIVE/name).read_bytes()
    for name in ('RUNTIME_CAPTURE_QUICKSTART.md','RUNTIME_PREPARATION_HARDENING_V0.2.0.md'):files['docs/'+name]=(ROOT/'docs'/name).read_bytes()
    for name in ('controller_analysis.json','sdk_verification.json','integration_strategy.json','native_rebuild.json','automated_tests.json','live_binding_evidence.json','live_execution.json'):
        files['reports/'+name]=(REPORTS/name).read_bytes()
    files=with_manifest(files);payload=archive(files)
    if payload!=archive(files):raise ValueError('Non-repeatable package')
    if PACKAGE.exists() and PACKAGE.read_bytes()!=payload:raise ValueError('Preserve previous hardened package; choose a fresh package version')
    folder=OUTPUT/'preparation'
    for name,data in files.items():
        path=confined(folder,name)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Preserve previous preparation output')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    PACKAGE.parent.mkdir(exist_ok=True);PACKAGE.write_bytes(payload)
    with zipfile.ZipFile(PACKAGE) as z:
        if z.testzip() is not None or set(z.namelist())!=set(files):raise ValueError('Package reimport failure')
        for name,data in files.items():
            if z.read(name)!=data:raise ValueError('Package changed')
    if protect()!=before:raise ValueError('Accepted checkpoints changed')
    source_paths=['scripts/runtime_preparation_protection.py','scripts/runtime_controller_graph.py','scripts/runtime_capture.py',
        'scripts/runtime_preflight.py','scripts/Prepare_Runtime_Capture.ps1','scripts/runtime_preparation_package.py',
        'scripts/runtime_preparation_finalize.py','scripts/runtime_collect.py','scripts/runtime/bela_binding_probe_v2.lua',
        'scripts/runtime/bela_binding_probe_v3.lua','scripts/runtime/bela_binding_probe_v4.lua','scripts/runtime/bela_binding_probe_v5.lua','scripts/runtime/bela_binding_probe_v6.lua','scripts/runtime/bela_binding_probe_v7.lua','scripts/runtime_live_evidence.py',
        'tests/test_runtime_preparation.py','tests/runtime_probe_v2_fixture.lua']
    source_paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'scripts/animation/ReeControllerInspect').glob('*')) if p.is_file()]
    phase={'status':'OFFLINE_HARDENING_COMPLETE_PARTIAL_LIVE_BINDING_CAPTURED','accepted_D1_checkpoint':'48d139f',
        'protected':before,'tests':tests,'source_code_hashes':[{'path':p,'sha256':sha(ROOT/p)} for p in source_paths],
        'package':PACKAGE.relative_to(ROOT).as_posix(),'package_sha256':sha(PACKAGE),'package_files':len(files),
        'preparation_folder':folder.relative_to(ROOT).as_posix(),'native_rebuilt_byte_identically':True,
        'live_runtime_binding_verified':False,'runtime_probe_executed_by_agent':True,'game_launched_by_agent':True,
        'game_file_installation_or_animation_activation':False,'runtime_API_and_XYZW_support_verified':False,
        'current_game_process_detected':current['game_running'],
        'save_fingerprints_match_original_D1':current['steam_save_hashes_unchanged'],
        'save_change_policy':'Read-only comparison; manual gameplay may write normal saves; no automatic restore or modification',
        'next':'Repeat v7 marked walk/aim capture -> confirm layer/skeleton association and one-shot/abort/holder route -> separately authorized A/B/C playback'}
    write_json(REPORTS/'phase_results.json',phase)
    print(json.dumps({'status':phase['status'],'tests':tests,'package':str(PACKAGE)},indent=2))


if __name__=='__main__':main()

