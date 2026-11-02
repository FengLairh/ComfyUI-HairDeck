"""Geometry and glTF contracts for the export surface, independent of ComfyUI/CUDA."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_vendor'))
from hairdeck_core.cards import surface
from hairdeck_core.cards.mesh import card_mesh_vf
from hairdeck_core import materials
from hairdeck_core.infer.glb import hair_trimesh, write_glb
from hairdeck_core.spring import vrm_spring as VS
from hairdeck_core.vrm.prep import prep


def card(count=8, x=0., thickness=.005):
    seq = np.zeros((count, 8))
    seq[:, 0] = x
    seq[:, 1] = np.linspace(0, .2, count)
    seq[:, 3], seq[:, 4], seq[:, 5] = .025, thickness, 1.
    return seq, 0


class SurfaceTests(unittest.TestCase):
    def test_boundary_caps_only_and_original_surface_positions(self):
        seq, shape = card()
        previous = seq.copy()
        mesh = surface.build([(seq, shape)])
        self.assertEqual(len(mesh.F), 8 * (len(seq) - 1) + 4)
        raw, _ = card_mesh_vf(seq, shape)
        np.testing.assert_array_equal(mesh.V, raw[mesh.S])
        np.testing.assert_array_equal(seq, previous)
        welded = trimesh.Trimesh(mesh.V, mesh.F, process=True)
        self.assertTrue(welded.is_watertight)
        self.assertTrue(welded.is_winding_consistent)

    def test_float32_uv_and_tangent_frames(self):
        seq, shape = card()
        seq[3, :3] = seq[2, :3]
        for mode in ('shared', 'unique'):
            mesh = surface.build([(seq, shape)], mode, 4096)
            uv = mesh.UV.copy()
            uv[:, 1] = 1 - uv[:, 1]
            uv = uv.astype(np.float32).astype(np.float64)
            tri = uv[mesh.F]
            a, b = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
            self.assertTrue((np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]) > 1e-12).all())
            np.testing.assert_allclose(np.linalg.norm(mesh.N, axis=1), 1, atol=1e-6)
            np.testing.assert_allclose(np.linalg.norm(mesh.T[:, :3], axis=1), 1, atol=1e-6)
            np.testing.assert_allclose((mesh.N * mesh.T[:, :3]).sum(1), 0, atol=1e-6)
            self.assertTrue(np.isfinite(mesh.T).all())

    def test_unique_charts_do_not_overlap_including_padding(self):
        mesh = surface.build([card(x=i * .03) for i in range(20)], 'unique', 1024)
        boxes = []
        for item in mesh.layout:
            x, y, width, height = item['rect']
            pad = item['gutter']
            box = [x-pad, y-pad, x+width+pad, y+height+pad]
            self.assertTrue(min(box) >= 0 and max(box) <= 1024)
            for other in boxes:
                self.assertTrue(box[2] <= other[0] or other[2] <= box[0] or box[3] <= other[1] or other[3] <= box[1])
            boxes.append(box)
        self.assertEqual(len(mesh.layout), 60)
        shared = surface.build([card(x=i * .03) for i in range(20)], 'shared', 1024)
        self.assertEqual(len(shared.layout), 24)

    def test_uv_seams_copy_original_binding_indices(self):
        seq, shape = card()
        mesh = surface.build([(seq, shape)])
        original_weights = np.linspace(0, 1, 4 * len(seq))
        expanded = original_weights[mesh.S]
        for source in np.unique(mesh.S):
            self.assertTrue(np.all(expanded[mesh.S == source] == original_weights[source]))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'surface.npz'
            mesh.save(path)
            loaded = surface.load(path)
            np.testing.assert_array_equal(loaded.S, mesh.S)
            np.testing.assert_array_equal(loaded.UV, mesh.UV)

    def test_flat_and_empty_cards(self):
        flat = surface.build([card(thickness=0)])
        self.assertEqual(len(flat.F), 2 * 7)
        empty, shape = card()
        empty[:, 3:5] = 0
        mixed = surface.build([(empty, shape), card(x=.1)])
        self.assertEqual(mixed.card_offsets[0], mixed.card_offsets[1])
        with self.assertRaises(ValueError):
            surface.build([(empty, shape)])

    def test_exported_uv_tangent_handedness(self):
        vertices = np.array([[0., 0, 0], [1., 0, 0], [0., 1, 0]])
        faces = np.array([[0, 1, 2]])
        normal = np.tile([0., 0, 1], (3, 1))
        uv = vertices[:, :2].copy()
        first = surface.tangent_frame(vertices, faces, normal, uv)
        uv[:, 1] *= -1
        mirrored = surface.tangent_frame(vertices, faces, normal, uv)
        np.testing.assert_allclose(first[:, :3], mirrored[:, :3])
        np.testing.assert_allclose(first[:, 3], -mirrored[:, 3])

    def test_binding_is_copied_after_uv_vertex_splits(self):
        cards = [card(), card(x=.012)]
        fit = dict(w=.1, s=1., t=[0., 0., 0.], sx=1, sz=-1, head_joint=[0., 0., 0.])
        chains = [dict(joints=np.array([[0., 0, 0], [0, .1, 0], [0, .2, 0]]), stiffness=1., n_joints=3)]
        original, _ = prep(0, 'test', cards, chains, fit)
        mesh = surface.build(cards)
        optimized, _ = prep(0, 'test', cards, chains, fit, [mesh.card(i) for i in range(len(cards))])
        source = np.concatenate([mesh.card(i)[4] + 4 * sum(len(seq) for seq, _ in cards[:i]) for i in range(len(cards))])
        for name in ('vchain', 'vseg', 'vw', 'vseg2', 'valpha'):
            np.testing.assert_array_equal(optimized[name], original[name][source])


class MaterialTests(unittest.TestCase):
    def test_textures_embedded_and_previews_read_the_same_pixels(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cards = [card(), card(x=.04)]
            asset = materials.create(cards, [.3, .15, .1], 'unique', 1024, 'volume', root/'textures', root/'work')
            path = root/'hair.glb'
            write_glb(path, hair_trimesh(cards, [.3, .15, .1], asset.descriptor))
            materials.patch_glb(path, asset.descriptor)
            doc, binary = materials.read_glb(path)
            primitive = doc['meshes'][0]['primitives'][0]
            self.assertTrue({'NORMAL', 'TANGENT', 'TEXCOORD_0'} <= set(primitive['attributes']))
            normal = VS.accessor(doc, binary, primitive['attributes']['NORMAL'])
            tangent = VS.accessor(doc, binary, primitive['attributes']['TANGENT'])
            np.testing.assert_allclose((normal*tangent[:, :3]).sum(1), 0, atol=1e-5)
            preview = materials.gltf_material(doc, binary, primitive['material'])
            for channel, name in asset.material['textures'].items():
                with Image.open(root/'textures'/name) as image:
                    expected = np.array(image.convert('RGBA' if channel == 'baseColorTexture' else 'RGB'))
                np.testing.assert_array_equal(preview[channel], expected)
            self.assertEqual(preview['baseColorFactor'], [1., 1., 1., 1.])
            self.assertEqual(asset.material['geometry']['uv_degenerate_triangles'], 0)
            with Image.open(asset.directory/'roughness.png') as image:
                roughness = np.array(image).astype(int)
            with Image.open(asset.directory/'unity_metallic_smoothness.png') as image:
                unity = np.array(image)
            self.assertTrue((unity[..., 0] == 0).all())
            self.assertLessEqual(np.abs(unity[..., 3].astype(int) + roughness - 255).max(), 1)

    def test_ribbon_alpha_is_active_and_volume_is_opaque(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for preset in ('ribbon', 'volume'):
                asset=materials.create([card()], [.3,.15,.1], 'shared', 1024, preset, root/preset, root/(preset+'_work'))
                with Image.open(asset.directory/'base_color.png') as image:
                    alpha=np.array(image)[...,3]
                item=next(item for item in asset.material['layout'] if item['key'][1]=='surface')
                x,y,w,h=item['rect']
                alpha=alpha[y:y+h,x:x+w]
                if preset=='ribbon':
                    self.assertEqual(asset.material['alphaMode'],'MASK')
                    self.assertLess(alpha.min(),100)
                    self.assertGreater(alpha.max(),240)
                else:
                    self.assertTrue((alpha==255).all())
                    self.assertEqual(asset.material['alphaMode'],'OPAQUE')


if __name__ == '__main__':
    unittest.main(verbosity=2)
