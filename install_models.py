"""Explicit, checksum-verified model/tool installation. Never runs on node import."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts'))
from fetch_public import fetch

MODEL_REVISION = '129ad77fba42edfb79a59246f43b11d3fc64c6d1'
BASE = f'https://huggingface.co/hyz317/HairDeck/resolve/{MODEL_REVISION}/'
THIRD_PARTY = [
    ('https://modelscope.cn/models/facebook/sam3/resolve/f8ee5d16d5c30d0e87b1d22cbd358ce97761df56/sam3.pt',
     'third_party/weights/sam3/sam3.pt', '9999e2341ceef5e136daa386eecb55cb414446a00ac2b55eb2dfd2f7c3cf8c9e'),
    ('https://modelscope.cn/models/facebook/dinov3-vitl16-pretrain-lvd1689m/resolve/99b6205b0321c4d9726dd072d8c6a80aa6be72df/model.safetensors',
     'third_party/weights/dinov3/model.safetensors', 'dcb2e45127cccbf1601e5f42fef165eea275c8e5213197e8dcf3f48822718179'),
    ('https://huggingface.co/ZhengPeng7/BiRefNet-matting/resolve/eccde0a8cbdce7ac5fecfeb06340fe7b949e85d9/model.safetensors',
     'third_party/weights/birefnet_matting/model.safetensors', 'a9875de5b1e6c8eb5fdaa8c727a82927ce442cdc87ba3abee6a77e6fa46c25bb'),
]
BLENDER = {
    'Windows': ('blender-4.2.23-windows-x64.zip', '82e791475779a7342424a480bdde9a20b43710da9264c60346125aa16cd910cb'),
    'Linux': ('blender-4.2.23-linux-x64.tar.xz', 'bea0eb3146be13eae6225409a117b215184f41b7f79e799f97cb3abb8f6dc404'),
}
ADDON = ('https://github.com/saturday06/VRM-Addon-for-Blender/releases/download/v4.10.2/VRM_Addon_for_Blender-Extension-4_10_2.zip',
         '228e622d158fbbf070b1b49547708f360a223873f00fa81a42170794492e6db9')


def install_blender(root):
    system = platform.system()
    if system not in BLENDER or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError('Portable Blender installation supports Windows/Linux x86-64.')
    name, checksum = BLENDER[system]
    tools = root / 'tools/blender'
    archive = tools / name
    top = name.removesuffix('.zip').removesuffix('.tar.xz')
    executable = tools / top / ('blender.exe' if system == 'Windows' else 'blender')
    if not executable.is_file():
        fetch('https://download.blender.org/release/Blender4.2/' + name, archive, checksum)
        print('EXTRACT', archive.name, flush=True)
        if system == 'Windows':
            with zipfile.ZipFile(archive) as source:
                source.extractall(tools)
        else:
            with tarfile.open(archive) as source:
                source.extractall(tools, filter='data')
    resources = tools / 'user'
    environment = dict(os.environ)
    environment.update(BLENDER_USER_RESOURCES=str(resources), BLENDER_USER_CONFIG=str(resources / 'config'),
                       BLENDER_USER_SCRIPTS=str(resources / 'scripts'), BLENDER_USER_DATAFILES=str(resources / 'datafiles'),
                       BLENDER_USER_EXTENSIONS=str(resources / 'extensions'),
                       BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION='true')
    addon = tools / ADDON[0].rsplit('/', 1)[-1]
    if not (resources / 'extensions/user_default/vrm').is_dir():
        fetch(ADDON[0], addon, ADDON[1])
        subprocess.run([str(executable), '--command', 'extension', 'install-file', '--repo', 'user_default',
                        '--enable', str(addon)], env=environment, check=True)
    print('BLENDER_READY', executable, flush=True)


def install_models(root):
    index = fetch(BASE + 'MANIFEST.json', root / 'MANIFEST.json')
    manifest = json.loads(index.read_text(encoding='utf-8'))['files']
    selected = {name: meta for name, meta in manifest.items()
                if name.startswith(('ckpt/card_vae/', 'ckpt/image_model/', 'ckpt/chain_model/', 'data/avatar/'))
                and 'latents_test' not in name}
    for name in ['data/token_stats_head.json', 'data/head_frame_train.npz', 'data/spring/chain_stats_head.json']:
        selected[name] = manifest[name]
    downloads = [(BASE + name, root / name, meta['sha256']) for name, meta in selected.items()]
    downloads += [(url, root / name, checksum) for url, name, checksum in THIRD_PARTY]
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(fetch, url, path, checksum) for url, path, checksum in downloads]
        for job in jobs:
            job.result()
    print('MODELS_READY', root, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models-dir', required=True, type=Path, help='For example: ComfyUI/models/hairdeck')
    parser.add_argument('--with-blender', action='store_true', help='Also install portable Blender and the VRM add-on')
    parser.add_argument('--only-blender', action='store_true', help='Install Blender without downloading model weights')
    args = parser.parse_args()
    destination = args.models_dir.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if not args.only_blender:
        install_models(destination)
    if args.with_blender or args.only_blender:
        install_blender(destination)
