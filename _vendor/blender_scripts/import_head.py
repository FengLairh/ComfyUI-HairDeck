"""Build a local head-only VRM and matching canonical GLB from an FBX mesh."""
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import vrm_hair as E
import vrm_scene as V
from hairdeck_core.vrm import body as B


def to_head(points):
    return np.stack([points[:, 0], points[:, 2], -points[:, 1]], axis=-1)


def to_world(points):
    return np.stack([points[:, 0], -points[:, 2], points[:, 1]], axis=-1)


def world_vertices(obj):
    return np.array([tuple(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices], dtype=np.float64)


def main():
    job = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text(encoding='utf-8'))
    root, destination = Path(job['root']), Path(job['destination'])
    source_body = json.loads((root / 'data/avatar/body.json').read_text(encoding='utf-8'))
    with np.load(root / 'data/head_frame_train.npz') as frame:
        width, origin = float(frame['W']), frame['O'].astype(np.float64)
    V.clear_scene()
    bpy.ops.import_scene.fbx(filepath=job['source'])
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and len(obj.data.vertices)]
    if not meshes:
        raise ValueError('The FBX has no mesh vertices.')
    points = np.concatenate([to_head(world_vertices(obj)) for obj in meshes])
    low, high = points.min(0), points.max(0)
    scale = .81 * width / (high[0] - low[0]) * job['scale_adjust']
    offset = np.array([origin[0] - scale * (low[0] + high[0]) / 2,
                       origin[1] + .053 * width - scale * high[1],
                       origin[2] - .7 * width - scale * low[2]]) + job['offset']
    material = bpy.data.materials.new('HeadBase')
    material.use_nodes = True
    material.diffuse_color = (.55, .55, .55, 1.)
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = material.diffuse_color
    bsdf.inputs['Roughness'].default_value = .85
    for obj in meshes:
        vertices = to_world(to_head(world_vertices(obj)) * scale + offset)
        obj.parent = None
        obj.matrix_world = Matrix.Identity(4)
        obj.modifiers.clear()
        obj.vertex_groups.clear()
        obj.data.materials.clear()
        obj.data.materials.append(material)
        for vertex, position in zip(obj.data.vertices, vertices):
            vertex.co = position
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    head = bpy.context.view_layer.objects.active
    head.name, head.data.name = 'HeadBase', 'HeadBase'
    bpy.ops.export_scene.gltf(filepath=str(destination / 'head.glb'), export_format='GLB', use_selection=True)

    arm = V.import_vrm(str(root / source_body['vrm']))
    E.remove_original_hair(arm, {})
    ext = arm.data.vrm_addon_extension.vrm0
    ext.blend_shape_master.blend_shape_groups.clear()
    ext.first_person.mesh_annotations.clear()
    ext.secondary_animation.bone_groups.clear()
    for obj in list(bpy.data.objects):
        if obj.type == 'MESH':
            bpy.data.objects.remove(obj, do_unlink=True)
    previous = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(destination / 'head.glb'))
    meshes = [obj for obj in bpy.data.objects if obj not in previous and obj.type == 'MESH']
    fit = source_body['fit']
    for obj in meshes:
        canonical = to_head(world_vertices(obj))
        dataset = (canonical - source_body['b']) / source_body['k']
        body = (dataset - fit['t']) / fit['s']
        vertices = np.stack([fit['sx'] * body[:, 0], fit['sz'] * body[:, 2], body[:, 1]], axis=-1)
        obj.parent = arm
        obj.matrix_world = Matrix.Identity(4)
        obj.modifiers.clear()
        obj.vertex_groups.clear()
        for vertex, position in zip(obj.data.vertices, vertices):
            vertex.co = position
        obj.name, obj.data.name = 'HeadBase', 'HeadBase'
        group = obj.vertex_groups.new(name=V.human_bones(arm)['head'])
        group.add(list(range(len(obj.data.vertices))), 1., 'REPLACE')
        obj.modifiers.new('Head rig', 'ARMATURE').object = arm
        for mat in obj.data.materials:
            bpy.ops.vrm.convert_material_to_mtoon1(material_name=mat.name)
            mat.vrm_addon_extension.mtoon1.pbr_metallic_roughness.base_color_factor = (.55, .55, .55, 1.)
            mat.vrm_addon_extension.mtoon1.extensions.vrmc_materials_mtoon.shade_color_factor = (.33, .33, .33)
    relative = (Path('heads') / job['name']).as_posix()
    body = dict(source_body, key=job['name'], file_tag='custom_head', vrm=relative + '/avatar.vrm',
                head_mesh=relative + '/head.glb',
                vrm_meta=dict(title=job['name'], author='User-provided model; author unspecified', licenseName='Other',
                              otherLicenseUrl='', allowedUserName='OnlyAuthor', commercialUssageName='Disallow'))
    B.apply_vrm_meta(arm, body)
    if not E.export(arm, str(destination / 'avatar.vrm')):
        raise RuntimeError('The custom head VRM could not be exported.')
    (destination / 'body.json').write_text(json.dumps(body, indent=2), encoding='utf-8')
    manifest = dict(version=1, name=job['name'], mesh='head.glb', body='body.json', source=Path(job['source']).name,
                    source_sha256=job['source_sha256'], source_vertices=len(points), scale=scale,
                    offset=offset.tolist(), bounds=[(low * scale + offset).tolist(), (high * scale + offset).tolist()],
                    permissions='Source asset permissions are unspecified; this local profile grants no redistribution rights.')
    (destination / 'profile.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print('CUSTOM_HEAD_PROFILE', json.dumps(manifest, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
