import copy,json,sys,unittest,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from runtime_capture import load_capture
from runtime_one_cycle import analyze,restage_resource,RESOURCE_SESSION,validate_environment,verify_steam_identity
from runtime_experiment import remove_owned

class LiveEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.live=load_capture(ROOT/'build/animation_v0.2.0/runtime_experiment/grace_zero_weight_20261011_c/grace_zero_weight_20261011_c_7.json')

    def test_real_zero_weight_evidence_passes_without_claiming_playback(self):
        result=analyze(self.live)
        self.assertEqual(result['status'],'PASSED')
        self.assertFalse(result['playback_cycle_observed'] or result['visual_acceptance_verified'])

    def test_complete_label_cannot_hide_a_runtime_error(self):
        doc=copy.deepcopy(self.live);doc['errors']=['Synthetic failure']
        self.assertEqual(analyze(doc)['status'],'FAILED')

    def test_wrong_or_missing_joints_are_rejected(self):
        for field in ('remove','hash','index','nan'):
            with self.subTest(field=field):
                doc=copy.deepcopy(self.live);j=doc['poses'][0]['joints']
                if field=='remove':j.pop()
                elif field=='hash':j[0]['hash']=0
                elif field=='index':j[1]['index']=j[0]['index']
                else:j[0]['rotation'][0]=float('nan')
                with self.assertRaises(ValueError):analyze(doc)

    def test_cleanup_reference_or_count_mismatch_fails(self):
        for field,value in [('bank_count',4),('layer_count',10),('original_references_preserved',False)]:
            doc=copy.deepcopy(self.live);doc['cleanup'][field]=value
            self.assertEqual(analyze(doc)['status'],'FAILED')

    def test_visible_weight_is_rejected_in_dry_run(self):
        doc=copy.deepcopy(self.live);doc['poses'][0]['layer']['weight']=1
        self.assertEqual(analyze(doc)['status'],'FAILED')

    def test_reusable_staging_preserves_conflicts_and_requires_ownership_for_rollback(self):
        source=ROOT/'build/animation_v0.2.0/native_idle_canonical/native/bela_idle.motlist.1047'
        with tempfile.TemporaryDirectory() as folder:
            game=Path(folder);record=restage_resource(game,source,'replay_test_20261011')
            target=game/record['relative_path']
            self.assertEqual(record['session'],RESOURCE_SESSION)
            with self.assertRaises(FileExistsError):restage_resource(game,source,'replay_test_20261012')
            with self.assertRaises(ValueError):remove_owned(game,record,True)
            target.write_bytes(b'changed experimental file')
            with self.assertRaises(ValueError):remove_owned(game,record,False)
            self.assertTrue(target.exists())

    def test_environment_gate_rejects_protected_installation_changes(self):
        baseline={'changed_protected_files':[],'missing_protected_files':[],'steam_build_id':'23634047',
            'exe_versions':{'FileVersion':'1.3.1.0'},'official_archive_size_mtime_unchanged':True,'appmanifest_unchanged':True}
        validate_environment(baseline)
        for field,value in [('changed_protected_files',['asset']),('official_archive_size_mtime_unchanged',False),('steam_build_id','different')]:
            doc=copy.deepcopy(baseline);doc[field]=value
            with self.assertRaises(ValueError):validate_environment(doc)

    def test_current_and_target_build_must_match_despite_volatile_last_played(self):
        with tempfile.TemporaryDirectory() as folder:
            steam=Path(folder);game=steam/'common/game';game.mkdir(parents=True)
            path=steam/'appmanifest_3764200.acf'
            path.write_text('"appid" "3764200"\n"buildid" "23634047"\n"TargetBuildID" "23634047"\n"LastPlayed" "1"')
            first=verify_steam_identity(game)
            path.write_text(path.read_text().replace('"LastPlayed" "1"','"LastPlayed" "2"'))
            self.assertEqual(first['identifiers'],verify_steam_identity(game)['identifiers'])
            path.write_text(path.read_text().replace('"TargetBuildID" "23634047"','"TargetBuildID" "different"'))
            with self.assertRaises(ValueError):verify_steam_identity(game)

if __name__=='__main__':unittest.main()

