"""Bounded MOTFSM2.45/BHVT42 node graph reader. No RSZ assumptions or writer.

Layout source: pinned ReeLib BhvtFile.cs / Motfsm2File.cs. Node labels help
prioritize inspection; neither labels nor edges establish a live animation slot.
"""
import argparse
import json
import struct
from pathlib import Path
from common import ROOT, write_json
from source_animation_workflow import sha


class Cursor:
    def __init__(self, data, position=0): self.data, self.position = data, position
    def read(self, fmt):
        size = struct.calcsize('<' + fmt)
        if self.position < 0 or self.position + size > len(self.data):
            raise ValueError('Controller read outside file')
        values = struct.unpack_from('<' + fmt, self.data, self.position)
        self.position += size
        return values[0] if len(values) == 1 else values
    def count(self):
        value = self.read('i')
        if not 0 <= value <= 100000: raise ValueError('Invalid controller count')
        return value
    def columns(self, n):
        count = self.count()
        cols = [[self.read('I') for _ in range(count)] for _ in range(n)]
        return list(zip(*cols))


def decode(path):
    data = Path(path).read_bytes(); c = Cursor(data)
    if c.read('II') != (45, 0x3273666d): raise ValueError('Expected MOTFSM2.45')
    c.position = 16; tree, maps, transitions, unknown, info = c.read('5Q')
    map_count, transition_count, start = c.read('iii')
    if not (0 <= map_count <= 100000 and 0 <= transition_count <= 100000): raise ValueError('Invalid header count')
    c.position = tree
    magic, header_hash, reserved = c.read('III')
    if magic != 0x54564842 or reserved: raise ValueError('Expected BHVT42 header')
    offsets = c.read('18Q'); c.position = tree + offsets[0]
    node_count = c.count(); nodes = []
    for _ in range(node_count):
        id_, ex = c.read('II'); name_offset = c.read('i'); parent = c.read('II')
        children = c.columns(3); selector = c.read('i')
        callers = [c.read('I') for _ in range(c.count())]; caller_condition = c.read('I')
        actions = c.columns(2); priority = c.read('i'); attributes = c.read('H')
        fsm = None
        if attributes & 32:
            work, name_hash, full_hash = c.read('HII')
            tags = [c.read('I') for _ in range(c.count())]
            branch, end = c.read('BB')
            fsm = dict(work_flags=work, name_hash=name_hash, full_name_hash=full_hash,
                tags=tags, branch=bool(branch), end=bool(end))
        else:
            if c.read('H'): raise ValueError('Unknown node reserved bits')
        count = c.count()
        events = [[c.read('I') for _ in range(c.count())] for _ in range(count)]
        cols = [[c.read('I') for _ in range(count)] for _ in range(5)]
        states = [dict(target=[a, d], condition=b, map_id=m, extension=e, events=events[i])
            for i, (a, b, m, d, e) in enumerate(zip(*cols))]
        count = c.count()
        transition_events = [[c.read('I') for _ in range(c.count())] for _ in range(count)]
        cols = [[c.read('I') for _ in range(count)] for _ in range(3)]
        incoming = [dict(encoded_start=[a, ex_], condition=b, events=transition_events[i])
            for i, (a, b, ex_) in enumerate(zip(*cols))]
        all_states = [] if attributes & 4 else [dict(target=[a, d], condition=b, map_id=m, attributes=e)
            for a, b, m, d, e in c.columns(5)]
        reference_offset = c.read('i')
        pos = tree + offsets[12] + 4 + name_offset * 2
        if pos < 0 or pos >= len(data): raise ValueError('Invalid name offset')
        end_pos = pos
        while end_pos + 2 <= len(data) and data[end_pos:end_pos+2] != b'\x00\x00':
            end_pos += 2
            if end_pos - pos > 8192: raise ValueError('Unbounded node name')
        if end_pos + 2 > len(data): raise ValueError('Unterminated node name')
        name = data[pos:end_pos].decode('utf-16-le')
        nodes.append(dict(id=[id_, ex], name=name, parent=list(parent), attributes=attributes,
            children=[dict(target=[a, b], condition=co) for a,b,co in children], selector_id=selector,
            caller_ids=callers, caller_condition=caller_condition,
            actions=[dict(id=a, extension=b) for a,b in actions], priority=priority, fsm=fsm,
            states=states, incoming=incoming, all_states=all_states, reference_tree_path_offset=reference_offset))
    node_end = c.position
    if node_end > tree + offsets[1]: raise ValueError('Node table overlaps actions')
    lookup = {tuple(n['id']): n for n in nodes}
    if len(lookup) != len(nodes): raise ValueError('Duplicate node identity')
    for n in nodes:
        lineage = []; current = n; visited = set()
        while current:
            identity = tuple(current['id'])
            if identity in visited: raise ValueError('Controller parent cycle')
            visited.add(identity); lineage.append(current['name']); current = lookup.get(tuple(current['parent']))
        n['hierarchy'] = '/'.join(reversed(lineage))
    c.position = transitions
    transition_rows = []
    for i in range(transition_count):
        values = c.read('IIfI4fHHI')
        transition_rows.append(dict(index=i, id=values[0], flags=values[1], exit_frame=values[2],
            opaque_rsz_reference=values[3], start_frame=values[4], interpolation_frames=values[5],
            playback_speed=values[6], timeout_frames=values[7], continue_layer=values[8],
            continue_mask=values[9], reserved=values[10]))
    c.position = maps; mapping = {}
    for _ in range(map_count):
        map_id, index = c.read('Ii')
        if not 0 <= index < transition_count: raise ValueError('Invalid transition reference')
        if map_id in mapping: raise ValueError('Duplicate transition map ID')
        mapping[map_id] = index
    edges = []; unresolved_nodes = []; unresolved_maps = []
    for n in nodes:
        for kind in ('states', 'all_states'):
            for s in n[kind]:
                target = lookup.get(tuple(s['target'])); index = mapping.get(s['map_id'])
                # Unset/external references are reported rather than discarded.
                if target is None: unresolved_nodes.append({'source': n['id'], 'target': s['target'], 'kind': kind})
                if index is None: unresolved_maps.append({'source': n['id'], 'map_id': s['map_id']})
                edges.append(dict(source=n['hierarchy'], source_id=n['id'], target=target['hierarchy'] if target else None,
                    target_id=s['target'], kind=kind, condition=s['condition'], map_id=s['map_id'],
                    transition=transition_rows[index] if index is not None else None))
    relevant = [e for e in edges if any(hint in (e['source'] + ' ' + (e['target'] or '')).lower()
        for hint in ('idle', 'stand', 'walk', 'move', 'aim', 'hold', 'interact', 'gimmick', 'reload'))]
    return dict(path=str(Path(path).relative_to(ROOT)).replace('\\', '/') if Path(path).is_relative_to(ROOT) else str(path),
        sha256=sha(path), version=45, bhvt_layout_version=42, start_node_header=start,
        node_count=node_count, transition_record_count=transition_count, map_count=map_count,
        node_table_end=node_end, action_table_start=tree + offsets[1], nodes=nodes, edges=edges,
        relevant_edges_by_label_inference=relevant, unresolved_nodes=unresolved_nodes, unresolved_maps=unresolved_maps,
        typed_action_condition_payloads_decoded=False, live_binding_verified=False)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    files = sorted((ROOT / 'build/animation_v0.2.0/native_binding/extracted').rglob('*.motfsm2.45'))
    controllers = [decode(p) for p in files]
    write_json(args.output, {'controllers': controllers,
        'scope': 'Static node identities, hierarchy, transition-map links. State labels are interpretation aids only.',
        'missing': 'Matching RE9 RSZ action/condition schema and live component/layer observations'})
    print(json.dumps({'controllers': len(controllers), 'nodes': sum(c['node_count'] for c in controllers),
        'edges': sum(len(c['edges']) for c in controllers), 'records': sum(c['transition_record_count'] for c in controllers)}))


if __name__ == '__main__': main()

