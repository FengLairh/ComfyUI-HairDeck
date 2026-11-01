"""Check merged node contracts and preprocessing reuse without loading checkpoints."""
import asyncio
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import torch


def main():
    sys.path.insert(0, str(Path.cwd()))
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('hairdeck_three_check', root / '__init__.py',
                                                 submodule_search_locations=[str(root)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    spec.loader.exec_module(package)
    nodes = sys.modules[spec.name + '.nodes']
    runtime = sys.modules[spec.name + '.runtime']
    generation = sys.modules[spec.name + '.generation']
    output = sys.modules[spec.name + '.output']
    classes = asyncio.run(package.comfy_entrypoint()).get_node_list()
    classes = asyncio.run(classes)
    assert [cls.define_schema().node_id for cls in classes] == ['HairDeckLoader', 'HairDeckGenerate', 'HairDeckSave']
    upload = nodes.HairDeckGenerate.INPUT_TYPES()['required']['image'][1]
    assert upload['image_upload'] is True
    assert len(nodes.HairDeckGenerate.RETURN_TYPES) == 1
    assert len(nodes.HairDeckSave.RETURN_TYPES) == 2
    image = torch.zeros(1, 2, 2, 3)
    image[0, 0, 0] = 1
    bundle = SimpleNamespace(root=root, signature='test-model', hair=SimpleNamespace(model=SimpleNamespace(args=SimpleNamespace(res=2))))
    calls = []

    def preprocess(model, pixels, transparent_mask, source=None):
        calls.append(True)
        key = generation.prepared_key(model, source)
        crop = np.array(source.convert('RGB'))
        prepared = runtime.PreparedImage(root, model.signature, key, crop, [.1, .2, .3])
        return prepared, pixels.clone(), torch.ones(1, 2, 2), torch.zeros(1, 2, 2), pixels.clone()

    with tempfile.TemporaryDirectory() as directory, patch.object(generation.folder_paths, 'get_temp_directory', return_value=directory), \
         patch.object(runtime, 'preprocess', side_effect=preprocess):
        initial, hit = generation.cached_preprocess(bundle, image)
        assert not hit and len(calls) == 1
        repeated, hit = generation.cached_preprocess(bundle, image)
        assert hit and len(calls) == 1 and torch.equal(initial[1], repeated[1])
        changed_image = image.clone()
        changed_image[0, 1, 1] = .5
        generation.cached_preprocess(bundle, changed_image)
        assert len(calls) == 2
        source = runtime.image_bytes(image)
        cache = Path(directory) / 'hairdeck/preprocess-v1' / (generation.prepared_key(bundle, source) + '.npz')
        cache.write_bytes(b'interrupted cache')
        _, hit = generation.cached_preprocess(bundle, image)
        assert not hit and len(calls) == 3
    with tempfile.TemporaryDirectory() as directory:
        image_file = Path(directory) / 'input.png'
        image_file.write_bytes(b'first content')
        with patch.object(nodes.folder_paths, 'get_input_directory', return_value=directory), \
             patch.object(nodes.folder_paths, 'get_annotated_filepath', return_value=str(image_file)):
            original = nodes.HairDeckGenerate.fingerprint_inputs('input.png')
            image_file.write_bytes(b'changed content')
            assert original != nodes.HairDeckGenerate.fingerprint_inputs('input.png')
    result = SimpleNamespace(rig=None)
    try:
        output.save(None, result, 'GLB + VRM', 'HairDeck/test', 'auto', False, False, False, '')
    except ValueError as error:
        assert '生成弹簧骨骼' in str(error)
    else:
        raise AssertionError('VRM export accepted a result without bones.')
    print('THREE_NODE_CONTRACTS_PASSED: exactly 3 nodes, internal upload, cache reuse/invalidation/repair, missing-rig guard')


if __name__ == '__main__':
    main()
