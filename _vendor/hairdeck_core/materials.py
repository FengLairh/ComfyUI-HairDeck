"""One procedural appearance bundle shared by GLB, VRM and local previews."""
from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image, ImageDraw

from .cards import surface
from .spring import vrm_spring as VS


@dataclass
class Appearance:
    mesh: surface.Surface
    material: dict
    directory: Path
    descriptor: Path


def smoothstep(low, high, value):
    t = np.clip((value - low) / (high - low), 0., 1.)
    return t * t * (3 - 2 * t)


def texture_patch(width, height, kind, variant, color, preset):
    u = np.linspace(0, 1, width)[None, :]
    v = np.linspace(1, 0, height)[:, None]
    frequency = max(1, min(18 + variant % 13, width // 4))
    phase = 2 * np.pi * (frequency * u + .12 * np.sin(2 * np.pi * v + variant))
    fibre = .5 + .5 * np.cos(phase)
    shade = (.80 + .28 * v) * (.91 + .12 * fibre) * (.95 + .05 * np.sin(variant * 2.13))
    roughness = np.broadcast_to(.59 - .09 * v + .06 * (1 - fibre), (height, width)).copy()
    strength = .1 if preset == 'volume' else .22
    if preset == 'volume':
        shade = (.86 + .18 * v) * (.96 + .05 * fibre) * (.96 + .04 * np.sin(variant * 2.13))
        roughness = np.broadcast_to(.72 - .04 * v + .025 * (1 - fibre), (height, width)).copy()
    nx = strength * np.sin(phase)
    # V in the GLB texture coordinates points down the PNG; normals use that exported tangent frame.
    ny = -strength * np.sin(phase) * (.12 * 2 * np.pi * np.cos(2 * np.pi * v + variant)) / frequency
    normal = np.stack(np.broadcast_arrays(nx, ny, np.sqrt(np.maximum(1 - nx * nx - ny * ny, 0))), axis=-1)
    alpha = np.ones((height, width))
    if preset == 'ribbon':
        edge = smoothstep(0, .09, u) * smoothstep(0, .09, 1 - u)
        tip = smoothstep(0, .04, .88 + .12 * fibre - v)
        alpha = edge * tip * (.65 + .35 * fibre)
    if kind != 'surface':
        shade = np.full((height, width), .80 if kind == 'root' else 1.03)
        normal = np.broadcast_to([0., 0., 1.], (height, width, 3)).copy()
        roughness[:] = .6 if kind == 'root' else .5
        alpha[:] = 1
    if preset in ('solid', 'checker'):
        shade = np.ones((height, width))
        normal[:] = [0, 0, 1]
        roughness[:] = .75
    rgb = np.clip(np.asarray(color)[None, None, :] * shade[..., None], 0, 1)
    if preset == 'checker':
        checks = (np.floor(u * max(2, width // 20)) + np.floor(v * max(2, height // 20))) % 2
        rgb = np.where(checks[..., None] > 0, [.18, .55, .7], [.85, .85, .85])
        rgb = np.where(np.broadcast_to(v < .035, (height, width))[..., None], [.1, .8, .2], rgb)
        rgb = np.where(np.broadcast_to(v > .965, (height, width))[..., None], [.9, .15, .1], rgb)
        if kind != 'surface':
            rgb[:] = [.1, .8, .2] if kind == 'root' else [.9, .15, .1]
    base = np.concatenate([rgb, alpha[..., None]], axis=-1)
    mr = np.stack([np.ones_like(roughness), roughness, np.zeros_like(roughness)], axis=-1)
    unity = np.stack([np.zeros_like(roughness)] * 3 + [1. - roughness], axis=-1)
    return {'base_color.png': np.uint8(base * 255 + .5), 'normal.png': np.uint8((normal * .5 + .5) * 255 + .5),
            'roughness.png': np.uint8(roughness * 255 + .5), 'metallic_roughness.png': np.uint8(mr * 255 + .5),
            'unity_metallic_smoothness.png': np.uint8(unity * 255 + .5), 'alpha.png': np.uint8(alpha * 255 + .5)}


def create(cards, color, uv_mode, resolution, preset, directory, work):
    if uv_mode not in ('shared', 'unique') or preset not in ('volume', 'ribbon', 'solid', 'checker'):
        raise ValueError('Unsupported UV or material preset.')
    if resolution not in (1024, 2048, 4096):
        raise ValueError('Unsupported texture resolution.')
    directory, work = Path(directory), Path(work)
    directory.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    mesh = surface.build(cards, uv_mode, resolution, ribbon=preset == 'ribbon')
    atlases = {'base_color.png': np.zeros((resolution, resolution, 4), np.uint8),
               'normal.png': np.full((resolution, resolution, 3), [128, 128, 255], np.uint8),
               'roughness.png': np.full((resolution, resolution), 153, np.uint8),
               'metallic_roughness.png': np.full((resolution, resolution, 3), [255, 153, 0], np.uint8),
               'unity_metallic_smoothness.png': np.full((resolution, resolution, 4), [0, 0, 0, 102], np.uint8),
               'alpha.png': np.zeros((resolution, resolution), np.uint8)}
    for tile in mesh.layout:
        x, y, width, height = tile['rect']
        gutter = tile['gutter']
        variant, kind = tile['key']
        for name, patch in texture_patch(width, height, kind, variant, color, preset).items():
            padding = ((gutter, gutter), (gutter, gutter)) + (((0, 0),) if patch.ndim == 3 else ())
            atlases[name][y - gutter:y + height + gutter, x - gutter:x + width + gutter] = np.pad(patch, padding, mode='edge')
    for name, data in atlases.items():
        Image.fromarray(data).save(directory / name)
    layout_image = Image.new('RGB', (resolution, resolution), (25, 28, 33))
    draw = ImageDraw.Draw(layout_image)
    for tile in mesh.layout:
        x, y, width, height = tile['rect']
        draw.rectangle((x, y, x + width - 1, y + height - 1), outline=(100, 160, 210))
    for face in mesh.F:
        xy = mesh.UV[face] * [resolution, -resolution] + [0, resolution]
        draw.line([tuple(point) for point in np.vstack([xy, xy[:1]])], fill=(190, 205, 215), width=1)
    layout_image.save(directory / 'uv_layout.png')
    exported_uv = mesh.UV.copy()
    exported_uv[:, 1] = 1. - exported_uv[:, 1]
    tri = exported_uv.astype(np.float32).astype(np.float64)[mesh.F]
    a, b = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    area = np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]) * .5
    report = dict(vertices=len(mesh.V), triangles=len(mesh.F), cards=len(cards), uv_degenerate_triangles=int((area < 1e-12).sum()),
                  atlas_charts=len(mesh.layout), uv_overlap='intentional shared variants' if uv_mode == 'shared' else 'none',
                  normal_length_range=[float(np.linalg.norm(mesh.N, axis=1).min()), float(np.linalg.norm(mesh.N, axis=1).max())])
    config = dict(version=1, preset=preset, uv_mode=uv_mode, resolution=resolution, base_color_srgb=list(map(float, color)),
                  baseColorFactor=[1., 1., 1., 1.], metallicFactor=0., roughnessFactor=1.,
                  alphaMode='MASK' if preset == 'ribbon' else 'OPAQUE', alphaCutoff=.35, doubleSided=True,
                  textures=dict(baseColorTexture='base_color.png', normalTexture='normal.png',
                                metallicRoughnessTexture='metallic_roughness.png'),
                  color_spaces={'base_color.png': 'sRGB', 'normal.png': 'linear', 'roughness.png': 'linear',
                                'metallic_roughness.png': 'linear', 'unity_metallic_smoothness.png': 'linear', 'alpha.png': 'linear'},
                  channel_layouts={'metallic_roughness.png': 'G=roughness, B=metallic (0); R is unused',
                                   'unity_metallic_smoothness.png': 'R=metallic (0), A=smoothness (1-roughness)'},
                  normal_convention='glTF tangent space, +Y', strand_direction='editor +V: root to tip; exported glTF strand direction: -bitangent',
                  geometry=report, layout=mesh.layout)
    (directory / 'material.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    mesh.save(work / 'surface.npz')
    descriptor = work / 'appearance.json'
    descriptor.write_text(json.dumps({'surface': 'surface.npz', 'material': str((directory / 'material.json').resolve())}), encoding='utf-8')
    return Appearance(mesh, config, directory, descriptor)


def load(descriptor):
    descriptor = Path(descriptor)
    data = json.loads(descriptor.read_text(encoding='utf-8'))
    path = Path(data['material'])
    return Appearance(surface.load(descriptor.parent / data['surface']),
                      json.loads(path.read_text(encoding='utf-8')), path.parent, descriptor)


def input_files(descriptor):
    descriptor = Path(descriptor)
    data = json.loads(descriptor.read_text(encoding='utf-8'))
    material = Path(data['material'])
    config = json.loads(material.read_text(encoding='utf-8'))
    return [str(descriptor), str(descriptor.parent / data['surface']), str(material),
            *[str(material.parent / name) for name in sorted(set(config['textures'].values()))]]


def read_glb(path):
    data = Path(path).read_bytes()
    size = struct.unpack_from('<I', data, 12)[0]
    document = json.loads(data[20:20 + size])
    offset = 20 + size
    binary_size = struct.unpack_from('<I', data, offset)[0]
    return document, bytearray(data[offset + 8:offset + 8 + binary_size])


def write_glb(path, document, binary):
    document['buffers'][0]['byteLength'] = len(binary)
    text = json.dumps(document, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    text += b' ' * (-len(text) % 4)
    binary += b'\0' * (-len(binary) % 4)
    body = struct.pack('<II', len(text), 0x4e4f534a) + text + struct.pack('<II', len(binary), 0x004e4942) + binary
    Path(path).write_bytes(struct.pack('<III', 0x46546c67, 2, 12 + len(body)) + body)


def patch_glb(path, appearance, mesh_names=('hair_cards', 'Hair_gen')):
    asset = load(appearance)
    doc, binary = read_glb(path)

    def append(data, target=None):
        binary.extend(b'\0' * (-len(binary) % 4))
        view = dict(buffer=0, byteOffset=len(binary), byteLength=len(data))
        if target:
            view['target'] = target
        binary.extend(data)
        index = len(doc.setdefault('bufferViews', []))
        doc['bufferViews'].append(view)
        return index

    sampler = len(doc.setdefault('samplers', []))
    doc['samplers'].append(dict(magFilter=9729, minFilter=9987, wrapS=33071, wrapT=33071))
    textures = {}
    for channel, name in asset.material['textures'].items():
        image_index = len(doc.setdefault('images', []))
        doc['images'].append(dict(name=name, bufferView=append((asset.directory / name).read_bytes()), mimeType='image/png'))
        textures[channel] = len(doc.setdefault('textures', []))
        doc['textures'].append(dict(source=image_index, sampler=sampler))
    touched = set()
    for mesh in doc['meshes']:
        if mesh.get('name') not in mesh_names:
            continue
        for primitive in mesh['primitives']:
            attrs = primitive['attributes']
            vertices = VS.accessor(doc, binary, attrs['POSITION']).astype(np.float64)
            faces = VS.accessor(doc, binary, primitive['indices']).reshape(-1, 3).astype(np.int64)
            uv = VS.accessor(doc, binary, attrs['TEXCOORD_0']).astype(np.float64)
            normal = (VS.accessor(doc, binary, attrs['NORMAL']).astype(np.float64)
                      if 'NORMAL' in attrs else surface.normals(vertices, faces))
            for name, values in [('NORMAL', surface.unit(normal)), ('TANGENT', surface.tangent_frame(vertices, faces, normal, uv))]:
                view = append(np.asarray(values, dtype='<f4').tobytes(), 34962)
                attrs[name] = len(doc['accessors'])
                doc['accessors'].append(dict(bufferView=view, componentType=5126, count=len(values),
                                             type='VEC' + str(values.shape[1])))
            attrs.pop('COLOR_0', None)
            index = primitive['material']
            if index in touched:
                continue
            touched.add(index)
            mat = doc['materials'][index]
            mat.update(alphaMode=asset.material['alphaMode'], alphaCutoff=asset.material['alphaCutoff'], doubleSided=True)
            mat['pbrMetallicRoughness'] = dict(baseColorFactor=[1., 1., 1., 1.], metallicFactor=0., roughnessFactor=1.,
                                               baseColorTexture={'index': textures['baseColorTexture']},
                                               metallicRoughnessTexture={'index': textures['metallicRoughnessTexture']})
            mat['normalTexture'] = dict(index=textures['normalTexture'], scale=1.)
            if 'VRM' in doc.get('extensions', {}):
                props = doc['extensions']['VRM']['materialProperties'][index]
                props.setdefault('textureProperties', {}).update(_MainTex=textures['baseColorTexture'],
                    _ShadeTexture=textures['baseColorTexture'], _BumpMap=textures['normalTexture'])
                props.setdefault('vectorProperties', {}).update(_Color=[1., 1., 1., 1.], _ShadeColor=[.6, .6, .6, 1.])
                masked = asset.material['alphaMode'] == 'MASK'
                props.setdefault('floatProperties', {}).update(_BumpScale=1., _Cutoff=asset.material['alphaCutoff'],
                    _BlendMode=1. if masked else 0., _CullMode=0., _ZWrite=1., _SrcBlend=1., _DstBlend=0.)
                props.setdefault('keywordMap', {}).update(_ALPHATEST_ON=masked, _ALPHABLEND_ON=False, _ALPHAPREMULTIPLY_ON=False)
                props.setdefault('tagMap', {})['RenderType'] = 'TransparentCutout' if masked else 'Opaque'
                props['renderQueue'] = 2450 if masked else 2000
    if not touched:
        raise ValueError('The exported file contains no generated hair mesh.')
    write_glb(path, doc, binary)


def render_kwargs(config, directory):
    directory = Path(directory)
    result = {key: config[key] for key in ('baseColorFactor', 'metallicFactor', 'roughnessFactor', 'alphaMode', 'alphaCutoff', 'doubleSided')}
    for channel, name in config['textures'].items():
        with Image.open(directory / name) as image:
            result[channel] = np.array(image)
    return result


def gltf_material(doc, binary, index):
    mat = doc['materials'][index] if index is not None else {}
    pbr = mat.get('pbrMetallicRoughness', {})
    result = dict(baseColorFactor=pbr.get('baseColorFactor', [1., 1., 1., 1.]),
                  metallicFactor=pbr.get('metallicFactor', 0.), roughnessFactor=pbr.get('roughnessFactor', .8),
                  alphaMode=mat.get('alphaMode', 'OPAQUE'), alphaCutoff=mat.get('alphaCutoff', .5),
                  doubleSided=mat.get('doubleSided', False))
    for key, owner in [('baseColorTexture', pbr), ('metallicRoughnessTexture', pbr), ('normalTexture', mat)]:
        if key not in owner:
            continue
        image = doc['images'][doc['textures'][owner[key]['index']]['source']]
        if 'bufferView' not in image:
            raise ValueError('Local previews require embedded texture images.')
        view = doc['bufferViews'][image['bufferView']]
        offset = view.get('byteOffset', 0)
        with Image.open(BytesIO(bytes(binary[offset:offset + view['byteLength']]))) as decoded:
            result[key] = np.array(decoded.convert('RGBA' if key == 'baseColorTexture' else 'RGB'))
    return result
