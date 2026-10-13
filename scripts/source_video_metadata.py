"""Read MP4 sample timing to verify complete Blender previews, without playback."""
import struct
from pathlib import Path


def boxes(data, start=0, end=None):
    end = len(data) if end is None else end
    while start < end:
        if start + 8 > end:
            raise ValueError('Truncated MP4 box')
        size, kind = struct.unpack_from('>I4s', data, start)
        header = 8
        if size == 1:
            size = struct.unpack_from('>Q', data, start + 8)[0]
            header = 16
        elif size == 0:
            size = end - start
        if size < header or start + size > end:
            raise ValueError('Invalid MP4 box length')
        yield kind, start + header, start + size
        start += size


def child(data, parent, kind):
    found = [(a, b) for k, a, b in boxes(data, *parent) if k == kind]
    if len(found) != 1:
        raise ValueError(f'Expected one MP4 {kind!r} box')
    return found[0]


def video_metadata(path):
    data = Path(path).read_bytes()
    movie = child(data, (0, len(data)), b'moov')
    tracks = []
    for kind, a, b in boxes(data, *movie):
        if kind != b'trak':
            continue
        media = child(data, (a, b), b'mdia')
        handler = child(data, media, b'hdlr')[0]
        if data[handler + 8:handler + 12] != b'vide':
            continue
        header = child(data, media, b'mdhd')[0]
        version = data[header]
        if version == 0:
            timescale, duration = struct.unpack_from('>II', data, header + 12)
        elif version == 1:
            timescale, duration = struct.unpack_from('>IQ', data, header + 20)
        else:
            raise ValueError('Unsupported MP4 media-header version')
        table = child(data, child(data, media, b'minf'), b'stbl')
        timing = child(data, table, b'stts')[0]
        count = struct.unpack_from('>I', data, timing + 4)[0]
        entries = [struct.unpack_from('>II', data, timing + 8 + i * 8) for i in range(count)]
        samples = sum(n for n, delta in entries)
        ticks = sum(n * delta for n, delta in entries)
        size_table = child(data, table, b'stsz')[0]
        size_samples = struct.unpack_from('>I', data, size_table + 8)[0]
        if not timescale or samples != size_samples or duration != ticks:
            raise ValueError('Video sample count/duration disagree')
        description = child(data, table, b'stsd')
        codec, payload, _ = next(boxes(data, description[0] + 8, description[1]))
        width, height = struct.unpack_from('>HH', data, payload + 24)
        tracks.append({'codec': codec.decode('ascii'), 'width': width, 'height': height,
                       'frame_count': samples, 'duration_seconds': ticks / timescale,
                       'fps': samples * timescale / ticks,
                       'constant_frame_timing': len({delta for n, delta in entries}) == 1})
    if len(tracks) != 1:
        raise ValueError('Expected one video track')
    return tracks[0]

