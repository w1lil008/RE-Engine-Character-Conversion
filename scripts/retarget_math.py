"""World-space bone-basis retargeting; never changes target binds or offsets."""
import numpy as np
from animation_math import compose, decompose, quaternion_matrix, hierarchy_globals, motion_globals


def rotation(matrix):
    return quaternion_matrix(decompose(matrix)[1])


def swing(a, b):
    """Shortest proper rotation aligning two directions, including antiparallel."""
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    if np.linalg.norm(a) < 1e-9 or np.linalg.norm(b) < 1e-9:
        raise ValueError('Undefined anatomical segment')
    a /= np.linalg.norm(a); b /= np.linalg.norm(b)
    dot = float(np.clip(np.dot(a, b), -1, 1))
    if dot < -.999999:
        helper = np.eye(3)[int(np.argmin(np.abs(a)))]
        axis = np.cross(a, helper); axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    cross = np.cross(a, b)
    k = np.array([[0, -cross[2], cross[1]], [cross[2], 0, -cross[0]], [-cross[1], cross[0], 0]])
    return np.eye(3) + k + k @ k / (1 + dot)


class Retarget:
    def __init__(self, decoded, source_bind, target, config):
        if config['rotation_method'] != 'original_mesh_bind_world_delta':
            raise ValueError('Unsupported rotation conversion method')
        self.decoded = decoded; self.config = config; self.target = target
        self.names = [b['name'] for b in target]; self.index = {n: i for i, n in enumerate(self.names)}
        self.source_index = {b['name']: i for i, b in enumerate(decoded['bones'])}
        self.parents = [self.index[b['parent']] if b['parent'] else -1 for b in target]
        self.bind_local = np.asarray([b['local'] for b in target])
        self.bind_world = hierarchy_globals(self.bind_local, self.parents)
        self.source_bind = source_bind
        self.mapping = config['mapping']; self.reverse = {v: k for k, v in self.mapping.items()}
        if len(self.reverse) != len(self.mapping): raise ValueError('Duplicate target mapping')
        self.align = {}
        self.mapping_rows = []
        for source, dest in self.mapping.items():
            if source not in self.source_index or source not in source_bind or dest not in self.index:
                raise ValueError(f'Missing correspondence: {source} -> {dest}')
            ti = self.index[dest]; alignment = np.eye(3)
            if config['anatomical_alignment'] and source in config['segment_ends']:
                se, te = config['segment_ends'][source]
                sv = source_bind[se][:3, 3] - source_bind[source][:3, 3]
                tv = self.bind_world[self.index[te], :3, 3] - self.bind_world[ti, :3, 3]
                alignment = swing(tv, sv)
            self.align[source] = alignment
            sb = decoded['bones'][self.source_index[source]]
            self.mapping_rows.append({'source': source, 'target': dest, 'source_parent': sb['parent'],
                'target_parent': target[ti]['parent'], 'static_anatomical_alignment': alignment.tolist(),
                'source_mesh_bind_rotation': rotation(source_bind[source]).tolist(),
                'source_MOT_rest_rotation': sb['quaternion_xyzw'], 'target_bind_rotation': rotation(self.bind_world[ti]).tolist()})
        # Inspect the actual source tree. Null_Offset is a leaf sibling of Hip.
        if decoded['bones'][self.source_index['Hip']]['parent'] != 'root':
            raise ValueError('Source hip hierarchy changed; explicit helper adapter required')
        null = decoded['bones'][self.source_index['Null_Offset']]
        if null['parent'] != 'root' or any(b['parent'] == 'Null_Offset' for b in decoded['bones']):
            raise ValueError('Source Null_Offset hierarchy changed')
        self.root_origin = motion_globals(decoded, 0)[self.source_index['root'], :3, 3]

    def from_source_world(self, source_world):
        world = []; local = []
        for i, bone in enumerate(self.target):
            parent = self.parents[i]; base = self.bind_local[i].copy()
            if parent >= i: raise ValueError('Target must retain its parent-first hierarchy')
            parent_world = world[parent] if parent >= 0 else np.eye(4)
            source = self.reverse.get(bone['name'])
            if source:
                desired = rotation(source_world[self.source_index[source]]) @ rotation(self.source_bind[source]).T
                desired = desired @ self.align[source] @ rotation(self.bind_world[i])
                translation, _, scale = decompose(base)
                local_rotation = rotation(parent_world).T @ desired
                base = np.eye(4); base[:3, 3] = translation
                base[:3, :3] = local_rotation @ np.diag(scale)
                if source == 'root':
                    base[:3, 3] += source_world[self.source_index[source], :3, 3] - self.root_origin
                    base[1, 3] += self.config.get('root_floor_offset_m', 0.)
            local.append(base); world.append(parent_world @ base)
        return np.asarray(local), np.asarray(world)

    def pose(self, frame):
        return self.from_source_world(motion_globals(self.decoded, frame))

