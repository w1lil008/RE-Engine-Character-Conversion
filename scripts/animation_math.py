"""Column-vector TRS and source-editor sampling; independent of weight fitting."""
import numpy as np


def unit_quaternion(value):
    q = np.asarray(value, dtype=float)
    n = np.linalg.norm(q)
    if q.shape != (4,) or not np.isfinite(q).all() or n < 1e-10:
        raise ValueError("Invalid XYZW quaternion")
    return q / n


def quaternion_matrix(value):
    x, y, z, w = unit_quaternion(value)
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def matrix_quaternion(r):
    """Stable largest-component conversion, including near-180 degree rotations."""
    r = np.asarray(r, dtype=float)
    candidates = np.array([1+r[0,0]-r[1,1]-r[2,2], 1-r[0,0]+r[1,1]-r[2,2],
                           1-r[0,0]-r[1,1]+r[2,2], 1+np.trace(r)])
    i = int(np.argmax(candidates)); v = np.sqrt(max(0, candidates[i])) / 2
    if v < 1e-10:
        raise ValueError("Degenerate rotation matrix")
    if i == 0: q = [v,(r[0,1]+r[1,0])/(4*v),(r[0,2]+r[2,0])/(4*v),(r[2,1]-r[1,2])/(4*v)]
    elif i == 1: q = [(r[0,1]+r[1,0])/(4*v),v,(r[1,2]+r[2,1])/(4*v),(r[0,2]-r[2,0])/(4*v)]
    elif i == 2: q = [(r[0,2]+r[2,0])/(4*v),(r[1,2]+r[2,1])/(4*v),v,(r[1,0]-r[0,1])/(4*v)]
    else: q = [(r[2,1]-r[1,2])/(4*v),(r[0,2]-r[2,0])/(4*v),(r[1,0]-r[0,1])/(4*v),v]
    return unit_quaternion(q)


def compose(t, q, s=(1, 1, 1)):
    m = np.eye(4); m[:3,:3] = quaternion_matrix(q) @ np.diag(s); m[:3,3] = t
    if not np.isfinite(m).all(): raise ValueError("Nonfinite TRS")
    return m


def decompose(m):
    m = np.asarray(m, dtype=float); s = np.linalg.norm(m[:3,:3], axis=0)
    if np.any(s < 1e-10): raise ValueError("Zero scale")
    r = m[:3,:3] / s
    if np.linalg.det(r) < 0: s[0] *= -1; r[:,0] *= -1
    if not np.allclose(r.T @ r, np.eye(3), atol=2e-5): raise ValueError("Shear cannot be encoded as TRS")
    return m[:3,3].copy(), matrix_quaternion(r), s


def sample(channel, frame, quaternion=False):
    values = np.asarray(channel['values'], dtype=float)
    times = channel['frames']
    if times is None or len(times) == 1: return unit_quaternion(values[0]) if quaternion else values[0]
    if frame <= times[0]: return unit_quaternion(values[0]) if quaternion else values[0]
    if frame >= times[-1]: return unit_quaternion(values[-1]) if quaternion else values[-1]
    b = int(np.searchsorted(times, frame, side='right')); a = b-1
    w = (frame-times[a])/(times[b]-times[a]); v1,v2 = values[a],values[b]
    # Match System.Numerics.Quaternion.Lerp used by the pinned source viewer.
    if quaternion and np.dot(v1,v2) < 0: v2 = -v2
    out = (1-w)*v1+w*v2
    return unit_quaternion(out) if quaternion else out


def hierarchy_globals(local, parents):
    if len(local) != len(parents): raise ValueError("Hierarchy length mismatch")
    result = [None]*len(local); visiting = set()
    def visit(i):
        if i in visiting: raise ValueError("Cyclic hierarchy")
        if result[i] is not None: return result[i]
        visiting.add(i); p = parents[i]
        if p < -1 or p >= len(local): raise ValueError("Invalid parent")
        result[i] = local[i] if p == -1 else visit(p) @ local[i]
        visiting.remove(i); return result[i]
    return np.asarray([visit(i) for i in range(len(local))])


def motion_globals(decoded, frame):
    bones = decoded['bones']; lookup = {b['name']:i for i,b in enumerate(bones)}
    tracks = {t['bone']:t for t in decoded['tracks']}; local=[]
    for b in bones:
        c=tracks.get(b['name'], {})
        t=sample(c['translation'],frame) if c.get('translation') else b['translation']
        q=sample(c['rotation'],frame,True) if c.get('rotation') else b['quaternion_xyzw']
        s=sample(c['scale'],frame) if c.get('scale') else [1,1,1]
        local.append(compose(t,q,s))
    parents=[lookup[b['parent']] if b['parent'] else -1 for b in bones]
    return hierarchy_globals(local,parents)


def reference_samples(path):
    import struct
    raw=path.read_bytes()
    if raw[:4]!=b'BGS1': raise ValueError("Unknown reference sample format")
    frames,bones=struct.unpack_from('<ii',raw,4)
    if len(raw)!=12+frames*(4+bones*16*4): raise ValueError("Truncated reference")
    data=np.frombuffer(raw[12:],dtype='<f4').reshape(frames,1+bones*16)
    return data[:,0].copy(),data[:,1:].reshape(frames,bones,4,4).swapaxes(-1,-2).copy()

