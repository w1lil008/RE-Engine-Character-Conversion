"""Copy/analyze saved read-only diagnostics. Reads no animation controller state."""
import argparse
import json
from pathlib import Path
from common import ROOT,confined,write_json
from source_animation_workflow import sha
from runtime_capture import load_capture,analyze,MAX_BYTES


def collect(source=None, operator='user'):
    if operator not in ('user','agent'):raise ValueError('Unknown capture operator')
    game=Path(json.loads((ROOT/'config/project.json').read_text(encoding='utf-8'))['games']['re9'])
    folder=game/'reframework/data/bela_d2'
    if source is None:
        files=list(folder.glob('*.json'))
        if not files:raise ValueError('No captured Bela D2/D3/D4 diagnostic JSON found')
        source=max(files,key=lambda p:p.stat().st_mtime_ns)
    source=Path(source).resolve()
    if source.parent!=folder.resolve() or source.suffix.lower()!='.json':raise ValueError('Only Bela diagnostic folder JSON may be collected')
    document=load_capture(source)
    digest=sha(source);stem=source.stem+'_'+digest[:12]
    raw=ROOT/'build/animation_v0.2.0/runtime_hardening/captures'/(stem+'.json')
    if raw.exists() and sha(raw)!=digest:raise ValueError('Captured reference changed')
    raw.parent.mkdir(parents=True,exist_ok=True)
    if not raw.exists():raw.write_bytes(source.read_bytes())
    static=json.loads((ROOT/'reports/native_animation_v0.2.0/binding_analysis.json').read_text(encoding='utf-8'))
    result=analyze(document,static)
    result.update({'raw_capture':raw.relative_to(ROOT).as_posix(),'raw_sha256':digest,
        'source_diagnostic_path':str(source),'probe_version':document.get('probe_version'),
        'runtime_identity':document.get('runtime_identity'),'context':document.get('context'),
        'discovery_diagnostics':document.get('discovery'),'source_game_files_modified':False,
        'source_scope':('User manually loaded read-only probe; observations do not authorize native playback' if operator=='user' else
                        'Agent loaded read-only probe through observed REFramework UI under user authorization; no native playback')})
    output=ROOT/'reports/runtime_preparation_v0.2.0/captures'/(stem+'.analysis.v3.json')
    if output.exists():
        if json.loads(output.read_text(encoding='utf-8'))!=result:raise ValueError('Analysis already exists with different evidence; choose a separate revision')
    else:write_json(output,result)
    return {'status':result['status'],'analysis':str(output),'raw_sha256':digest,
        'samples':result.get('sample_count',0),'idle_candidate_count':len(result.get('idle_candidates',[])),
        'missing_evidence':result.get('missing_evidence',[])}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture');p.add_argument('--operator',choices=('user','agent'),default='user');args=p.parse_args()
    print(json.dumps(collect(args.capture,args.operator),indent=2))


if __name__=='__main__':main()

