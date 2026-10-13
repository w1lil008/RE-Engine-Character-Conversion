"""Bounded disk-EXE disassembly of addresses captured by REFramework reflection.

No process access, memory reads, hooks, execution or writes to game assets.
Instruction evidence is not a substitute for a live decoding or playback test.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from common import ROOT, write_json
from source_animation_workflow import sha


def function_address(reference):
    if not isinstance(reference, str):
        raise ValueError('Function reference must be captured text')
    match = re.fullmatch(r'userdata:\s*(?:0x)?([0-9a-fA-F]{8,16})', reference)
    if not match:
        raise ValueError('Unsupported captured function reference')
    return int(match.group(1), 16)


def inspect(exe, metadata, expected_hash):
    if sha(exe) != expected_hash:
        raise ValueError('EXE differs from protected build')
    document = json.loads(Path(metadata).read_text(encoding='utf-8'))
    if document.get('schema') != 'bela-bank-api-v1' or document.get('metadata_only') is not True:
        raise ValueError('Not a read-only metadata capture')
    sys.path.insert(0, str(ROOT/'tools/runtime-experiment-deps'))
    import capstone
    import pefile
    pe = pefile.PE(str(exe), fast_load=True)
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)

    def decode(address, size=1536):
        rva = address-pe.OPTIONAL_HEADER.ImageBase
        section = pe.get_section_by_rva(rva) if 0 <= rva < pe.OPTIONAL_HEADER.SizeOfImage else None
        if section is None or not section.Characteristics & 0x20000000:
            raise ValueError('Address is not in an executable EXE section')
        available = section.VirtualAddress+section.SizeOfRawData-rva
        if available <= 0:
            raise ValueError('Address has no disk-backed instruction bytes')
        instructions = []
        for ins in decoder.disasm(pe.get_data(rva, min(size, available)), address):
            if ins.mnemonic == 'int3':
                break  # Compiler padding; do not decode the neighbouring routine.
            instructions.append({'address':hex(ins.address), 'bytes':ins.bytes.hex(),
                'mnemonic':ins.mnemonic, 'operands':ins.op_str})
        if not instructions:
            raise ValueError('No instructions at captured address')
        return {'address':hex(address), 'instructions':instructions,
            'bounded_bytes':min(size, available), 'scope':'Disk instructions, no runtime memory access'}

    selected = {}
    for row in document['types']:
        if row['type'] not in ('via.motion.DynamicMotionBank', 'via.motion.Motion', 'via.motion.MotionInfo','via.motion.TreeLayer'):
            continue
        for method in row.get('methods') or []:
            if method['name'] in ('hasDynamicMotion','set_MotionList','setupMotionBank','getDynamicMotionBank',
                'getMotionInfo','getJointIndexByNameHash','getAnimationTransform','getAnimationTransformLocalAmountStartToFrame',
                'setLayerCount','setLayer','setDynamicMotionBankCount','setDynamicMotionBank','set_BankID','set_OverwriteBankID',
                'changeMotion','clearMotionResource','set_Enabled','set_BlendRate','set_BaseLayerNo'):
                key=row['type']+'.'+method['name']
                if key in selected:key+='('+','.join(method.get('parameters') or [])+')'
                selected[key] = {'metadata':method,
                    'disassembly':decode(function_address(method['function_reference']))}
    native = {}
    for name, row in selected.items():
        instructions = row['disassembly']['instructions']
        last = instructions[-1]
        if last['mnemonic'] == 'jmp' and re.fullmatch(r'0x[0-9a-f]+', last['operands']):
            native[name+'.direct_thunk_target'] = decode(int(last['operands'],16))
        if name.endswith('.set_MotionList'):
            # Separate the reference-count routines from the setter's assignment
            # helper. Captured setter uses this helper in this exact build.
            for ins in instructions:
                if ins['mnemonic']=='call' and ins['operands']=='0x140ae5730':
                    native[name+'.assignment_helper'] = decode(int(ins['operands'],16))
    # This exact direct call is reached by the reflected Motion.setupMotionBank
    # thunk target. Keep it explicitly linked to the caller evidence.
    setup = native.get('via.motion.Motion.setupMotionBank.direct_thunk_target')
    if setup and any(i['mnemonic']=='call' and i['operands']=='0x14a104370' for i in setup['instructions']):
        native['setupMotionBank.dynamic_list_processing'] = decode(0x14a104370)
    transform = native.get('via.motion.MotionInfo.getAnimationTransform.direct_thunk_target')
    if transform:
        for address, label in ((0x1408e5770, 'channel_lookup'), (0x14556b780, 'rotation_decoder')):
            if any(i['mnemonic']=='call' and i['operands']==hex(address) for i in transform['instructions']):
                native['getAnimationTransform.'+label] = decode(address)
    pe.close()
    return {'schema':'bela-bank-disk-analysis-v1','exe_sha256':expected_hash,
        'metadata_sha256':sha(metadata),'methods':selected,'native_helpers':native,
        'no_runtime_memory_access':True, 'live_initialization_verified':False,
        'limitations':['Bounded instruction lists are not complete decompilation',
            'Derived prerequisites must be tested with an original-resource control',
            'No offset in this report is used for live memory writes']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--exe', required=True);parser.add_argument('--metadata', required=True)
    parser.add_argument('--expected-hash', required=True);parser.add_argument('--output', required=True)
    args=parser.parse_args()
    if Path(args.output).exists():raise ValueError('Preserve existing analysis')
    write_json(Path(args.output), inspect(Path(args.exe), Path(args.metadata), args.expected_hash))

