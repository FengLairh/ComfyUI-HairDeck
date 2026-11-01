"""Verify an extracted HairDeck offline model bundle using only Python's standard library."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

MANIFEST = 'MODEL_BUNDLE_MANIFEST.json'


def safe_path(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or '\\' in relative or ':' in relative:
        raise ValueError('Unsafe bundle path: ' + relative)
    resolved = root.joinpath(*path.parts).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError('Bundle path escapes its directory: ' + relative)
    return resolved


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / MANIFEST).read_text(encoding='utf-8'))
    if manifest.get('format') != 'comfyui-hairdeck-model-bundle' or manifest.get('format_version') != 1:
        raise ValueError('Unsupported model bundle manifest.')
    for index, (relative, expected) in enumerate(manifest['files'].items(), 1):
        path = safe_path(root, relative)
        if not path.is_file() or path.stat().st_size != expected['size']:
            raise ValueError('Missing file or incorrect size: ' + relative)
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != expected['sha256']:
            raise ValueError('SHA-256 mismatch: ' + relative)
        print(f'VERIFIED {index}/{len(manifest["files"])} {relative}', flush=True)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = verify(args.directory)
    print('MODEL_BUNDLE_OK', result['bundle_version'], len(result['files']), 'files', flush=True)
