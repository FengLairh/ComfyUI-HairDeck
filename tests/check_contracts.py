"""Check schema and data contracts without loading model weights."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import torch


def main():
    sys.path.insert(0, str(Path.cwd()))
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('hairdeck_contract_check', root / '__init__.py',
                                                 submodule_search_locations=[str(root)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    spec.loader.exec_module(package)
    runtime = sys.modules[spec.name + '.runtime']
    exporting = sys.modules[spec.name + '.exporting']
    from hairdeck_core import paths

    image = torch.tensor([[[[1.0, 0.5, 0.0], [0.0, 1.0, 0.5]]]])
    mask = torch.tensor([[[0.0, 1.0]]])
    result = runtime.image_bytes(image, mask)
    assert result.mode == 'RGBA' and result.getpixel((0, 0))[3] == 255 and result.getpixel((1, 0))[3] == 0
    try:
        runtime.image_bytes(image.repeat(2, 1, 1, 1))
    except ValueError:
        pass
    else:
        raise AssertionError('Unexpected silent handling of an unsupported image batch.')
    hair = SimpleNamespace(signature='hair-a', color=[.1, .2, .3])
    try:
        exporting.validate(hair, SimpleNamespace(hair_signature='hair-b'), 'auto')
    except ValueError:
        pass
    else:
        raise AssertionError('Mismatched hair and spring bones were accepted.')
    assert exporting.validate(hair, None, '#8040FF') == [128/255, 64/255, 1.0]
    for prefix in ['../escape', str(root.resolve())]:
        try:
            exporting.output_path(prefix, 'glb')
        except ValueError:
            pass
        else:
            raise AssertionError('Output escaped the configured output directory.')

    def workspace(name):
        with paths.use(root / name):
            return paths.get('root')
    with ThreadPoolExecutor(2) as pool:
        actual = list(pool.map(workspace, ['a', 'b']))
    assert actual[0] != actual[1]
    report = dict(alpha_mask_semantics=True, unsupported_batch_rejected=True, rig_binding_validated=True,
                  output_containment=True, workspace_isolation=True)
    print('CONTRACT_CHECK_PASSED', json.dumps(report))


if __name__ == '__main__':
    main()
