"""Read-only diagnostic setup/conflict preview. No installer or game launcher."""
import argparse
import json
from pathlib import Path
from common import ROOT, confined, write_json
from source_animation_workflow import sha
from runtime_stage1 import environment, NATIVE, FRAMEWORK_COMMIT
from runtime_preparation_protection import protect

PROBE = ROOT / 'scripts/runtime/bela_binding_probe_v7.lua'
LOOSE = 'natives/stm/animation/bela_prototype/v020/bela_idle.motlist.1047'
RUNTIME = 'Animation/bela_prototype/v020/bela_idle.motlist'


def conflict_preview(game, expected_sha=None):
    game = Path(game).resolve(); candidate = confined(game, LOOSE)
    conflicts = []
    if candidate.exists():
        conflicts.append({'path':LOOSE,'reason':'Existing destination; never overwrite',
            'sha256':sha(candidate) if candidate.is_file() else None})
    pak_folder=game/'pak_mods'
    opaque=[p.relative_to(game).as_posix() for p in sorted(pak_folder.rglob('*')) if p.is_file()] if pak_folder.exists() else []
    return dict(candidate_runtime_path=RUNTIME,prospective_loose_file=LOOSE,
        install_allowed=False,preview_only=True,files_to_install_now=[],files_to_delete_now=[],
        future_new_file={'source':str(NATIVE/'bela_idle.motlist.1047'),'destination':str(candidate),'sha256':expected_sha},
        conflicts=conflicts,opaque_mod_archive_files=opaque,
        conflict_scan_scope='Exact new loose destination and pak_mods inventory. Other mod manager profiles/opaque archives not proven conflict-free.',
        separate_playback_authorization_required=True)


def rollback_preview(game, manifest):
    """Validate future ownership/removal plan; performs no removal."""
    if manifest.get('prospective_loose_file') != LOOSE: raise ValueError('Rollback scope must be the single fresh Bela resource')
    target=confined(Path(game).resolve(),LOOSE)
    record=manifest.get('future_new_file',{})
    if target.exists():
        if not target.is_file() or not record.get('sha256') or sha(target)!=record['sha256']:
            raise ValueError('Future resource changed or ownership hash absent; manual investigation required')
    return {'preview_only':True,'must_exit_RE9_before_removal':True,
        'candidate_file':str(target),'candidate_exists':target.is_file(),
        'owned_hash_matches':sha(target)==record.get('sha256') if target.is_file() else None,
        'removal_allowed_now':False,'protected_character_or_archive_files_in_plan':[],
        'steps':['End the future single-cycle test; return to original controller if verified abort is available',
            'Exit RE9 completely to discard component banks and loader caches',
            'Remove only the newly added MOTLIST after its ownership hash is checked',
            'Do not touch pre-existing directories/configs/PAKs/saves; restart with normal character mod',
            'Run preflight again and compare protected hashes; confirm original idle/move/aim/reload/interaction']}


def check():
    protection=protect()
    before=json.loads((ROOT/'reports/runtime_binding_v0.2.0/environment_before.json').read_text(encoding='utf-8'))
    current=environment(); game=Path(current['game_directory'])
    changed=[]; missing=[]
    for row in before['protected_installed_files']:
        path=confined(game,row['path'])
        if not path.is_file(): missing.append(row['path'])
        elif sha(path)!=row['sha256']: changed.append(row['path'])
    saves_unchanged=current['steam_save_files']==before['steam_save_files']
    archives_unchanged=current['official_archives']==before['official_archives']
    manifest_unchanged=current['appmanifest_sha256']==before['appmanifest_sha256']
    expected_sha=sha(NATIVE/'bela_idle.motlist.1047')
    preview=conflict_preview(game,expected_sha)
    folder=game/'reframework/data/bela_d2'
    captures=[{'path':str(p),'bytes':p.stat().st_size} for p in sorted(folder.glob('*.json'))] if folder.exists() else []
    dependencies={
        'framework_dll':(game/'dinput8.dll').is_file(),
        'probe':PROBE.is_file(),
        'embedded_native_motlist':(NATIVE/'bela_idle.motlist.1047').is_file(),
        'lua_mock_runtime':(ROOT/'tools/runtime-probe-deps/lupa').is_dir(),
        'matching_RE9_RSZ_schema_available':False}
    exact=current['steam_build_id']=='23634047' and current['exe_versions']['FileVersion']=='1.3.1.0'
    complete=not changed and not missing and saves_unchanged and archives_unchanged and manifest_unchanged and exact
    return dict(status='OFFLINE_PREFLIGHT_PASSED' if complete else 'REVIEW_ENVIRONMENT_CHANGES',
        protected=protection,game_directory=str(game),steam_build_id=current['steam_build_id'],exe_versions=current['exe_versions'],
        game_running=current['game_process'] is not None,game_launched=False,
        dependencies=dependencies,protected_installed_file_count=len(before['protected_installed_files']),
        changed_protected_files=changed,missing_protected_files=missing,steam_save_hashes_unchanged=saves_unchanged,
        official_archive_size_mtime_unchanged=archives_unchanged,official_archives_content_hashed=False,
        appmanifest_unchanged=manifest_unchanged,framework_log_commit=current['framework_log_commit'],
        historical_framework_identity_only=True,live_framework_required=FRAMEWORK_COMMIT,live_tdb_required=83,
        probe_path=str(PROBE),capture_directory=str(folder),captures=captures,installation_preview=preview,
        rollback=rollback_preview(game,preview),game_writes=0,
        runtime_api_support_tested=False,animation_activation_allowed=False,
        runtime_capture_instructions='REFramework > ScriptRunner > Run script > select workspace probe; no installation needed',
        v013_runtime_confirmation='Still pending; matching loose bytes do not prove all runtime behaviours')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output');args=p.parse_args()
    result=check()
    if args.output:
        path=confined(ROOT,args.output)
        if not path.is_relative_to(ROOT/'reports/runtime_preparation_v0.2.0') or path.exists():
            raise ValueError('Choose a fresh report under reports/runtime_preparation_v0.2.0')
        write_json(path,result)
    print(json.dumps({k:result[k] for k in ('status','game_directory','game_running','probe_path','capture_directory','game_writes')},indent=2))


if __name__=='__main__': main()

