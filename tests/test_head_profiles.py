"""Path and selection contracts for local head assets, without CUDA or model weights."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import heads


class HeadProfileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.directory = self.root / 'heads/HeadA'
        self.directory.mkdir(parents=True)
        for name in ('head.glb', 'avatar.vrm'):
            (self.directory / name).write_bytes(b'local test asset')
        self.manifest = dict(mesh='head.glb', body='body.json')
        self.body = dict(vrm='heads/HeadA/avatar.vrm', head_mesh='heads/HeadA/head.glb')
        self.write_profile()

    def write_profile(self):
        for name, value in [('profile.json', self.manifest), ('body.json', self.body)]:
            (self.directory / name).write_text(json.dumps(value), encoding='utf-8')

    def test_auto_and_explicit_selection(self):
        self.assertIsNone(heads.resolve(self.root))
        (self.root / 'heads/active.json').write_text(json.dumps({'name': 'HeadA'}), encoding='utf-8')
        selected = heads.resolve(self.root)
        self.assertEqual(selected.name, 'HeadA')
        self.assertEqual(selected.mesh, self.directory / 'head.glb')
        self.assertIsNone(heads.resolve(self.root, 'upstream'))
        self.assertEqual(heads.choices([self.root]), ['auto', 'upstream', 'HeadA'])

    def test_profile_name_cannot_escape_or_use_path_components(self):
        for name in ('../HeadA', 'other/../HeadA', r'other\..\HeadA', str(self.directory), '..'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                heads.profile_directory(self.root, name)

    def test_mesh_cannot_escape_profile(self):
        (self.root / 'heads/other.glb').write_bytes(b'other asset')
        self.manifest['mesh'] = '../other.glb'
        self.write_profile()
        with self.assertRaises(ValueError):
            heads.resolve(self.root, 'HeadA')

    def test_vrm_cannot_escape_profile(self):
        (self.root / 'outside.vrm').write_bytes(b'other asset')
        self.body['vrm'] = 'outside.vrm'
        self.write_profile()
        with self.assertRaises(ValueError):
            heads.resolve(self.root, 'HeadA')

    def test_glb_and_motion_use_the_same_mesh(self):
        (self.directory / 'other.glb').write_bytes(b'other asset')
        self.body['head_mesh'] = 'heads/HeadA/other.glb'
        self.write_profile()
        with self.assertRaises(ValueError):
            heads.resolve(self.root, 'HeadA')


if __name__ == '__main__':
    unittest.main()
