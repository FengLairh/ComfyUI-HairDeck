"""Export surfaces: boundary caps, seam-safe UVs, normals and tangent frames."""
from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np

from .mesh import card_mesh_vf


def unit(values):
    return values / np.maximum(np.linalg.norm(values, axis=-1, keepdims=True), 1e-20)


def normals(vertices, faces):
    result = np.zeros_like(vertices, dtype=np.float64)
    tri = vertices[faces]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    for column in range(3):
        np.add.at(result, faces[:, column], cross)
    return unit(result)


def grouped_normals(vertices, faces, groups):
    tri = vertices[faces]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    sums = np.zeros((int(groups.max()) + 1, 3))
    for column in range(3):
        np.add.at(sums, groups[faces[:, column]], cross)
    return unit(sums)[groups]


def tangent_frame(vertices, faces, normal, uv):
    normal = unit(np.asarray(normal, dtype=np.float64))
    tri, tex = vertices[faces], uv[faces]
    e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    d1, d2 = tex[:, 1] - tex[:, 0], tex[:, 2] - tex[:, 0]
    det = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    valid = np.abs(det) > 1e-15
    reciprocal = np.zeros_like(det)
    reciprocal[valid] = 1. / det[valid]
    ta = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) * reciprocal[:, None]
    bi = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) * reciprocal[:, None]
    tangent, bitangent = np.zeros_like(vertices), np.zeros_like(vertices)
    for column in range(3):
        np.add.at(tangent, faces[:, column], ta)
        np.add.at(bitangent, faces[:, column], bi)
    tangent -= normal * np.sum(normal * tangent, axis=1, keepdims=True)
    missing = np.linalg.norm(tangent, axis=1) < 1e-12
    axis = np.eye(3)[np.argmin(np.abs(normal), axis=1)]
    tangent[missing] = np.cross(axis[missing], normal[missing])
    tangent = unit(tangent)
    tangent = unit(tangent - normal * np.sum(normal * tangent, axis=1, keepdims=True))
    handedness = np.where(np.sum(np.cross(normal, tangent) * bitangent, axis=1) < 0, -1., 1.)
    return np.column_stack([tangent, handedness])


def clean_faces(vertices, faces):
    tri = vertices[faces]
    return faces[np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1) > 1e-14]


def chart(vertices, faces, uv, normal, dimensions, kind, card, source):
    faces = clean_faces(vertices, np.asarray(faces, dtype=np.int64))
    if not len(faces):
        return None
    keep, faces = np.unique(faces, return_inverse=True)
    return dict(V=vertices[keep], F=faces.reshape(-1, 3), UV=uv[keep], N=normal[keep],
                dimensions=dimensions, kind=kind, card=card, source=np.asarray(source)[keep])


def card_charts(seq, shape, card, ribbon=False):
    raw, _ = card_mesh_vf(seq, shape)
    rings = raw.reshape(-1, 4, 3)
    count = len(rings)
    distance = np.linalg.norm(np.diff(rings, axis=0), axis=2).mean(axis=1)
    distance = np.maximum(distance, max(float(distance.sum()) * 1e-4, 1e-12))
    length = float(distance.sum())
    along = np.r_[0., np.cumsum(distance)] / length
    if ribbon or np.max(np.asarray(seq)[:, 4]) < 1e-9:
        vertices = rings[:, [0, 2]].reshape(-1, 3)
        faces = []
        for i in range(1, count):
            a, b = 2 * (i - 1), 2 * i
            faces.extend([[b, a, b + 1], [a + 1, b + 1, a]])
        faces = clean_faces(vertices, np.asarray(faces))
        uv = np.column_stack([np.tile([0., 1.], count), np.repeat(along, 2)])
        width = float(np.linalg.norm(rings[:, 0] - rings[:, 2], axis=1).mean())
        source = (4 * np.arange(count)[:, None] + np.array([0, 2])).reshape(-1)
        result = chart(vertices, faces, uv, normals(vertices, faces), [width, length], 'surface', card, source)
        return [result] if result is not None else []
    # Welded side topology supplies smooth normals before the UV seam is split.
    raw_faces = []
    for i in range(1, count):
        for side in range(4):
            a, b, c, d = 4 * (i - 1) + side, 4 * i + side, 4 * i + (side + 1) % 4, 4 * (i - 1) + (side + 1) % 4
            raw_faces.extend([[b, a, c], [d, c, a]])
    raw_faces = clean_faces(raw, np.asarray(raw_faces))
    centre = np.repeat(np.asarray(seq)[:, :3], 4, axis=0)
    tri = raw[raw_faces]
    orientation = np.sum(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]) *
                         (tri.mean(axis=1) - centre[raw_faces].mean(axis=1)), axis=1)
    raw_faces[orientation < 0] = raw_faces[orientation < 0, ::-1]
    raw_normals = normals(raw, raw_faces)
    indices = (4 * np.arange(count)[:, None] + np.array([0, 1, 2, 3, 0])).reshape(-1)
    vertices = raw[indices]
    faces = []
    for i in range(1, count):
        for side in range(4):
            a, b = 5 * (i - 1) + side, 5 * i + side
            faces.extend([[b, a, b + 1], [a + 1, b + 1, a]])
    faces = np.asarray(faces)
    tri = vertices[faces]
    centre_split = np.repeat(np.asarray(seq)[:, :3], 5, axis=0)
    inward = np.sum(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]) *
                    (tri.mean(axis=1) - centre_split[faces].mean(axis=1)), axis=1) < 0
    faces[inward] = faces[inward, ::-1]
    perimeter = np.linalg.norm(rings - np.roll(rings, -1, axis=1), axis=2).sum(axis=1).mean()
    uv = np.column_stack([np.tile(np.linspace(0, 1, 5), count), np.repeat(along, 5)])
    result = [chart(vertices, faces, uv, raw_normals[indices], [float(perimeter), length], 'surface', card, indices)]
    for index, kind, direction in [(0, 'root', seq[0, :3] - seq[1, :3]),
                                    (-1, 'tip', seq[-1, :3] - seq[-2, :3])]:
        vertices = rings[index]
        faces = np.array([[0, 2, 1], [0, 3, 2]])
        tri = vertices[faces]
        inward = np.sum(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]) * direction, axis=1) < 0
        faces[inward] = faces[inward, ::-1]
        uv = np.array([[1, .5], [.5, 1], [0, .5], [.5, 0]], dtype=np.float64)
        dimensions = [float(np.linalg.norm(vertices[0] - vertices[2])),
                      float(np.linalg.norm(vertices[1] - vertices[3]))]
        source = np.arange(4) + (0 if index == 0 else 4 * (count - 1))
        result.append(chart(vertices, faces, uv, normals(vertices, faces), dimensions, kind, card, source))
    return [item for item in result if item is not None]


def pack(rectangles, resolution, gutter):
    """Deterministic shelves; chart rotation is prohibited to preserve root-to-tip V."""
    def attempt(density):
        sizes = [(key, max(8, int(math.ceil(size[0] * density))),
                  max(8, int(math.ceil(size[1] * density)))) for key, size in rectangles.items()]
        shelves, placements = [], {}
        for key, width, height in sorted(sizes, key=lambda item: (-item[2], -item[1], item[0])):
            outer_w, outer_h = width + 2 * gutter, height + 2 * gutter
            if outer_w > resolution or outer_h > resolution:
                return None
            shelf = next((s for s in shelves if s[2] >= outer_h and s[0] + outer_w <= resolution), None)
            if shelf is None:
                y = sum(s[2] for s in shelves)
                if y + outer_h > resolution:
                    return None
                shelf = [0, y, outer_h]
                shelves.append(shelf)
            placements[key] = [shelf[0] + gutter, shelf[1] + gutter, width, height]
            shelf[0] += outer_w
        return placements
    low, high = 0., resolution / max(max(size) for size in rectangles.values()) * 16
    best = attempt(0)
    if best is None:
        raise ValueError('UV 图集分辨率不足，请提高贴图分辨率。')
    for _ in range(28):
        middle = (low + high) / 2
        placement = attempt(middle)
        if placement is None:
            high = middle
        else:
            low, best = middle, placement
    return best


@dataclass
class Surface:
    V: np.ndarray
    F: np.ndarray
    UV: np.ndarray
    N: np.ndarray
    T: np.ndarray
    G: np.ndarray
    S: np.ndarray
    card_offsets: np.ndarray
    face_offsets: np.ndarray
    layout: list

    def card(self, index):
        a, b = self.card_offsets[index:index + 2]
        c, d = self.face_offsets[index:index + 2]
        return self.V[a:b], self.F[c:d] - a, self.UV[a:b], self.N[a:b], self.S[a:b]

    def save(self, path):
        np.savez_compressed(path, V=self.V, F=self.F, UV=self.UV, N=self.N, T=self.T, G=self.G, S=self.S,
                            card_offsets=self.card_offsets, face_offsets=self.face_offsets)


def build(cards, uv_mode='shared', resolution=2048, ribbon=False):
    if uv_mode not in ('shared', 'unique'):
        raise ValueError('Unsupported UV mode.')
    charts = [item for card, (seq, shape) in enumerate(cards) for item in card_charts(np.asarray(seq), shape, card, ribbon)]
    if not charts:
        raise ValueError('没有可导出的有效发束表面。')
    groups = {}
    for item in charts:
        variant = item['card'] % 8 if uv_mode == 'shared' else item['card']
        key = (variant, item['kind'])
        item['group'] = key
        groups.setdefault(key, []).append(item['dimensions'])
    dimensions = {key: np.median(value, axis=0).tolist() for key, value in groups.items()}
    gutter = max(4, resolution // 256)
    packed = pack(dimensions, resolution, gutter)
    vertices, faces, uv, normal, sources, vo, fo = [], [], [], [], [], [0], [0]
    layout = [dict(key=list(key), rect=rect, gutter=gutter) for key, rect in sorted(packed.items())]
    for card in range(len(cards)):
        offset, count = vo[-1], fo[-1]
        for item in (value for value in charts if value['card'] == card):
            x, y, width, height = packed[item['group']]
            mapped = item['UV'].copy()
            mapped[:, 0] = (x + .5 + mapped[:, 0] * (width - 1)) / resolution
            mapped[:, 1] = 1. - (y + .5 + (1. - mapped[:, 1]) * (height - 1)) / resolution
            vertices.append(item['V'])
            normal.append(item['N'])
            sources.append(item['source'])
            uv.append(mapped)
            faces.append(item['F'] + offset)
            offset += len(item['V'])
            count += len(item['F'])
        vo.append(offset)
        fo.append(count)
    vertices, faces, uv, normal = map(np.concatenate, (vertices, faces, uv, normal))
    card_ids = np.repeat(np.arange(len(cards)), np.diff(vo))
    _, groups = np.unique(np.round(np.column_stack([card_ids, vertices, normal]), 10), axis=0, return_inverse=True)
    gltf_uv = uv.copy()
    gltf_uv[:, 1] = 1. - gltf_uv[:, 1]
    return Surface(vertices, faces, uv, normal, tangent_frame(vertices, faces, normal, gltf_uv), groups, np.concatenate(sources),
                   np.asarray(vo), np.asarray(fo), layout)


def load(path):
    with np.load(Path(path), allow_pickle=False) as data:
        return Surface(*(data[key].copy() for key in ('V', 'F', 'UV', 'N', 'T', 'G', 'S', 'card_offsets', 'face_offsets')), [])
