"""Run from ComfyUI with its Python; verifies real folder resolution without loading model weights."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path.cwd()))
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hairdeck_selection_check', ROOT / '__init__.py',
                                             submodule_search_locations=[str(ROOT)])
package = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = package
spec.loader.exec_module(package)
files = sys.modules[spec.name + '.model_files']
runtime = sys.modules[spec.name + '.runtime']
nodes = sys.modules[spec.name + '.nodes']
import folder_paths
import torch


class ModelSelectionTests(unittest.TestCase):
    def setUp(self):
        original = copy.deepcopy(folder_paths.folder_names_and_paths)
        self.addCleanup(self.restore, original)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'pack'
        for name in files.RESOURCE_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}', encoding='utf-8')
        self.names = {}
        for role, (_, directory, _) in files.MODELS.items():
            path = self.root / directory / ('sam3.pt' if role == 'sam3' else 'model.safetensors')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(role.encode())
            self.names[role] = path.name
            folder_paths.folder_names_and_paths.pop('hairdeck_' + role, None)
        folder_paths.folder_names_and_paths['hairdeck'] = ([str(self.root)], set())
        folder_paths.filename_list_cache.clear()
        files.register()

    @staticmethod
    def restore(original):
        folder_paths.folder_names_and_paths.clear()
        folder_paths.folder_names_and_paths.update(original)
        folder_paths.filename_list_cache.clear()

    def renamed_selection(self):
        for role, (_, directory, _) in files.MODELS.items():
            path = self.root / directory / self.names[role]
            renamed = path.with_name('selected_' + role + path.suffix)
            path.rename(renamed)
            self.names[role] = renamed.name
        folder_paths.filename_list_cache.clear()
        return files.resolve('pack', self.names)

    def test_six_independent_selectors(self):
        selected = files.resolve('pack', self.names)
        for role, (_, directory, _) in files.MODELS.items():
            self.assertEqual(getattr(selected, role), self.root / directory / self.names[role])
        inputs = nodes.HairDeckLoader.INPUT_TYPES()['required']
        self.assertEqual(set(inputs), set(files.MODELS) | {'resources'})
        self.assertNotIn('bundle', inputs)
        self.assertTrue(all(value[1].get('default') != 'auto' for value in inputs.values()))

    def test_all_six_files_can_be_renamed(self):
        original = files.signature(files.resolve('pack', self.names))
        selected = self.renamed_selection()
        for role in files.MODELS:
            self.assertEqual(getattr(selected, role).name, self.names[role])
        self.assertNotEqual(original, files.signature(selected))

    def test_external_model_directory(self):
        directory = self.root.parent / 'external_dino'
        directory.mkdir()
        checkpoint = directory / 'custom.safetensors'
        checkpoint.write_bytes(b'custom encoder')
        folder_paths.add_model_folder_path('hairdeck_dinov3', str(directory))
        folder_paths.filename_list_cache.clear()
        self.names['dinov3'] = checkpoint.name
        self.assertEqual(files.resolve('pack', self.names).dinov3, checkpoint)

    def test_unregistered_paths_and_auto_are_rejected(self):
        for value in ('auto', '../model.safetensors', str(self.root / 'outside.safetensors')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                files.resolve('pack', dict(self.names, image_model=value))

    def test_selected_weights_and_statistics_invalidate_cache(self):
        selected = files.resolve('pack', self.names)
        initial = files.signature(selected)
        selected.sam3.write_bytes(b'changed checkpoint')
        changed = files.signature(selected)
        self.assertNotEqual(initial, changed)
        (self.root / files.RESOURCE_FILES[0]).write_text('{"changed":true}', encoding='utf-8')
        self.assertNotEqual(changed, files.signature(selected))

    def test_loader_passes_explicit_selection(self):
        selected = self.renamed_selection()
        with patch.object(runtime, 'ModelBundle') as loader:
            nodes.HairDeckLoader.execute(resources='pack', **self.names)
        loader.assert_called_once_with(selected)
        self.assertEqual(nodes.HairDeckLoader.fingerprint_inputs(resources='pack', **self.names), files.signature(selected))

    def test_model_bundle_forwards_all_paths(self):
        selected = self.renamed_selection()
        hair = SimpleNamespace(args=SimpleNamespace(vae='card_vae'))
        chain = SimpleNamespace(vae_name='card_vae')
        with patch.object(runtime.mm, 'get_torch_device', return_value=torch.device('cuda')), \
             patch.object(torch.cuda, 'is_bf16_supported', return_value=True), \
             patch.object(runtime, 'ModelPatcher', side_effect=lambda model, *_: SimpleNamespace(model=model)), \
             patch.object(runtime, 'PreprocessWeights') as preprocessing, \
             patch.object(runtime, 'HairWeights', return_value=hair) as hair_weights, \
             patch.object(runtime, 'ChainWeights', return_value=chain) as chain_weights, \
             patch.object(runtime, 'chain_stats', return_value={}):
            bundle = runtime.ModelBundle(selected)
        preprocessing.assert_called_once_with(selected.sam3, selected.birefnet)
        hair_weights.assert_called_once_with(self.root, selected.image_model, selected.card_vae, selected.dinov3)
        chain_weights.assert_called_once_with(selected.chain_model)
        self.assertEqual(bundle.signature, files.signature(selected))


if __name__ == '__main__':
    unittest.main(verbosity=2)
