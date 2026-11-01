"""Create a source release without local models, binaries, configuration or execution data."""
import hashlib
from pathlib import Path
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = ['__init__.py', 'nodes.py', 'runtime.py', 'exporting.py', 'generation.py', 'output.py', 'heads.py', 'install_models.py', 'requirements.txt',
             'pyproject.toml', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'README.md', 'README.en.md', 'VALIDATION.md',
             'extra_model_paths.yaml.example', '.gitignore', 'CHANGELOG.md']
FOLDERS = ['_vendor', 'scripts', 'tests', 'example_workflows', 'docs', 'web']
SKIP = {'__pycache__', '.git', '.runtime', '.pytest_cache'}


def main():
    destination = ROOT / 'dist'
    destination.mkdir(exist_ok=True)
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    output = destination / f'ComfyUI-HairDeck-{version}.zip'
    sources = [ROOT / name for name in TOP_FILES]
    sources += [path for directory in FOLDERS for path in (ROOT / directory).rglob('*') if path.is_file()
                and not any(part in SKIP for part in path.parts) and path.suffix not in ('.pyc', '.pyo', '.log')]
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(sources):
            archive.write(path, 'ComfyUI-HairDeck/' + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            assert not name.endswith(('.safetensors', '.pt', '.exe', '.dll', '.pyc', '.log'))
            assert '/.runtime/' not in name
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest + '  ' + output.name + '\n', encoding='ascii')
    print('RELEASE_READY', output, output.stat().st_size, 'bytes', digest)


if __name__ == '__main__':
    main()
