"""Convert a local FBX into a canonical head profile using the installed portable Blender."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import heads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--models-dir', type=Path, required=True)
    parser.add_argument('--name', default=None)
    parser.add_argument('--blender', type=Path)
    parser.add_argument('--make-default', action='store_true')
    parser.add_argument('--scale-adjust', type=float, default=1.)
    parser.add_argument('--offset', type=float, nargs=3, default=[0., 0., 0.], metavar=('X', 'Y', 'Z'))
    args = parser.parse_args()
    source, root = args.source.resolve(), args.models_dir.resolve()
    if not source.is_file() or source.suffix.lower() != '.fbx':
        raise ValueError('Source must be an existing FBX file.')
    if not args.scale_adjust > 0:
        raise ValueError('Scale adjustment must be positive.')
    name = args.name or source.stem
    destination = heads.profile_directory(root, name)
    if destination.exists():
        raise FileExistsError('Choose a new profile name; existing head profiles are not overwritten: ' + str(destination))
    tools = root / 'tools/blender'
    executable = 'blender.exe' if os.name == 'nt' else 'blender'
    candidates = sorted(tools.glob('blender-4.2*/' + executable))
    blender = args.blender.resolve() if args.blender else (candidates[0] if candidates else None)
    if blender is None or not blender.is_file():
        raise FileNotFoundError('Install Blender 4.2 and the VRM add-on with install_models.py --with-blender first.')
    destination.mkdir(parents=True)
    job = dict(source=str(source), root=str(root), destination=str(destination), name=name,
               source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), scale_adjust=args.scale_adjust, offset=args.offset)
    environment = dict(os.environ)
    environment.update(HAIRDECK_NATIVE_ROOT=str(root), PYTHONNOUSERSITE='1', PYTHONPATH=str(ROOT / '_vendor'),
                       BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION='true')
    resources = tools / 'user'
    environment.update(BLENDER_USER_RESOURCES=str(resources), BLENDER_USER_CONFIG=str(resources / 'config'),
                       BLENDER_USER_SCRIPTS=str(resources / 'scripts'), BLENDER_USER_DATAFILES=str(resources / 'datafiles'),
                       BLENDER_USER_EXTENSIONS=str(resources / 'extensions'))
    with tempfile.TemporaryDirectory(prefix='head-import-', dir=destination.parent) as temporary:
        config = Path(temporary) / 'job.json'
        config.write_text(json.dumps(job), encoding='utf-8')
        command = [str(blender), '-b', '--python', str(ROOT / '_vendor/blender_scripts/import_head.py'), '--', str(config)]
        with (destination / 'import.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if result.returncode:
        raise RuntimeError('Head import failed: ' + (destination / 'import.log').read_text(encoding='utf-8', errors='replace')[-2000:])
    heads.resolve(root, name)
    if args.make_default:
        active = destination.parent / 'active.json'
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=destination.parent, delete=False) as stream:
            json.dump({'name': name}, stream)
            temporary = Path(stream.name)
        os.replace(temporary, active)
    print('HEAD_PROFILE_READY', destination, 'default=' + str(args.make_default), flush=True)


if __name__ == '__main__':
    main()
