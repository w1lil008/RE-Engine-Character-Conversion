"""Deterministic inert package construction. No game installation or invocation."""
import hashlib
import io
import json
import zipfile
from pathlib import PurePosixPath


def validate_files(files):
    required={'diagnostics/bela_binding_probe_v7.lua','resources/bela_idle.mot.983','resources/bela_idle.motlist.1047','README.txt'}
    if not required.issubset(files): raise ValueError('Incomplete preparation package')
    for name,data in files.items():
        p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name: raise ValueError('Unsafe package path')
        if p.parts[0] not in ('diagnostics','resources','docs','reports','README.txt','MANIFEST.json'):
            raise ValueError('Package must remain outside game native/autorun/mod-manager layouts')
        if name.endswith('.lua') and name!='diagnostics/bela_binding_probe_v7.lua': raise ValueError('Unexpected executable Lua')
        if name.lower().endswith(('modinfo.ini','.pak','.dll','.exe','.ps1','.bat')): raise ValueError('Activation/install payload forbidden')
        if not isinstance(data,bytes): raise ValueError('Expected file bytes')


def archive(files):
    validate_files(files);stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16;z.writestr(info,data,compresslevel=9)
    return stream.getvalue()


def with_manifest(files):
    validate_files(files)
    files=dict(files)
    files['MANIFEST.json']=(json.dumps({'scope':'Offline hardened, inert preparation. Manual diagnostics only; no playback harness.',
        'installed':False,'live_binding_verified':False,'manifest_self_excluded':True,
        'files':[{'path':n,'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in sorted(files.items())]},indent=2)+'\n').encode()
    return files

