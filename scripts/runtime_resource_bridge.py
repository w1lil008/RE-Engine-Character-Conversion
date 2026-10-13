"""Read-only evidence gate for the pinned REFramework resource lifetime bridge."""
import re
import sys
import subprocess
from pathlib import Path
from common import ROOT
from source_animation_workflow import sha


def inspect_release(exe, address):
    sys.path.insert(0, str(ROOT/'tools/runtime-experiment-deps'))
    import pefile
    import capstone
    pe=pefile.PE(str(exe), fast_load=True)
    rva=address-pe.OPTIONAL_HEADER.ImageBase
    if not 0<=rva<pe.OPTIONAL_HEADER.SizeOfImage:
        raise ValueError('Scanned release address outside protected EXE')
    code=pe.get_data(rva,96)
    instructions=[{'address':hex(i.address),'instruction':i.mnemonic+' '+i.op_str}
        for i in capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64).disasm(code,address)]
    pe.close()
    if not any(i['instruction']=='lock dec dword ptr [rcx + 0x28]' for i in instructions):
        raise ValueError('SDK fallback refcount does not match inspected native release')
    return instructions


def verify(game, expected_exe_hash):
    game=Path(game);exe=game/'re9.exe'
    if sha(exe)!=expected_exe_hash:raise ValueError('Unexpected EXE hash')
    source=ROOT/'tools/research/REFramework/shared/sdk/ResourceManager.cpp'
    pinned=subprocess.check_output(['git','-C',str(source.parents[2]),'show',
        'd1461375aee4ec3f313170f8eaad12064eb542d9:shared/sdk/ResourceManager.cpp'])
    if source.read_bytes().replace(b'\r\n',b'\n')!=pinned.replace(b'\r\n',b'\n'):
        raise ValueError('SDK resource bridge source differs from pinned commit')
    log=(game/'re2_framework_log.txt').read_text(encoding='utf-8',errors='replace')
    if 'Commit hash: d1461375aee4ec3f313170f8eaad12064eb542d9' not in log:
        raise ValueError('Framework log identity mismatch')
    releases=re.findall(r'\[Resource::update_pointers\] Found release function at ([0-9a-f]+)',log)
    creates=re.findall(r'\[ResourceManager::create_resource\] Found function at ([0-9a-f]+)',log)
    if not releases or not creates:raise ValueError('Resource scanner evidence missing')
    address=int(releases[-1],16)
    instructions=inspect_release(exe,address)
    return {'checked':True,'exe_sha256':expected_exe_hash,'sdk_source_sha256':sha(source),
        'release_address':hex(address),'native_refcount_offset':'0x28',
        'create_resource_address':hex(int(creates[-1],16)),'release_instructions':instructions,
        'scope':'Disk EXE and pinned SDK evidence; holder lifetime and engine loading still require live tests'}

