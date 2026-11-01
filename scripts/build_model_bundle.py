"""Build checksum-verified, portable ZIP64 model and optional Windows tool bundles."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import zipfile

from verify_model_bundle import safe_path

PROJECT = Path(__file__).resolve().parents[1]
VERSION = '0.1.1'


def constant(path, name):
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('Constant not found: ' + name)


def digest_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def model_files(source):
    manifest = json.loads((source / 'MANIFEST.json').read_text(encoding='utf-8'))['files']
    selected = {name: data['sha256'] for name, data in manifest.items()
                if name.startswith(('ckpt/card_vae/', 'ckpt/image_model/', 'ckpt/chain_model/', 'data/avatar/'))
                and 'latents_test' not in name}
    for name in ('data/token_stats_head.json', 'data/head_frame_train.npz', 'data/spring/chain_stats_head.json'):
        selected[name] = manifest[name]['sha256']
    for _, name, checksum in constant(PROJECT / 'install_models.py', 'THIRD_PARTY'):
        selected[name] = checksum
    required = constant(PROJECT / 'runtime.py', 'REQUIRED')
    if not set(required).issubset(selected):
        raise ValueError('Bundle selection does not cover the runtime requirements.')
    entries = {name: (safe_path(source, name), checksum) for name, checksum in selected.items()}
    licenses = {
        'licenses/HairDeck-LICENSE.txt': PROJECT / 'LICENSE',
        'licenses/SAM3-LICENSE.txt': PROJECT / '_vendor/hairdeck_sam3/LICENSE',
        'licenses/DINOv3-LICENSE.md': PROJECT / '_vendor/hairdeck_dinov3/LICENSE.md',
        'licenses/BiRefNet-LICENSE.txt': PROJECT / '_vendor/hairdeck_birefnet/LICENSE',
        'licenses/THIRD_PARTY_NOTICES.md': PROJECT / 'THIRD_PARTY_NOTICES.md',
        'verify_models.py': PROJECT / 'scripts/verify_model_bundle.py',
    }
    entries.update({name: (path, None) for name, path in licenses.items()})
    return entries


def write_bundle(output, entries, *, kind, readme):
    if output.exists() or output.with_suffix('.partial.zip').exists():
        raise FileExistsError('Use a fresh output directory; existing bundles are preserved: ' + str(output))
    for path, _ in entries.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.partial.zip')
    total = sum(path.stat().st_size for path, _ in entries.values())
    records = {}
    done = 0
    started = time.monotonic()
    last_update = 0.0
    compression = zipfile.ZIP_DEFLATED if kind == 'models' else zipfile.ZIP_STORED
    with zipfile.ZipFile(temporary, 'w', compression=compression, compresslevel=1 if kind == 'models' else None,
                         allowZip64=True) as archive:
        for index, (name, (path, expected)) in enumerate(sorted(entries.items()), 1):
            digest = hashlib.sha256()
            before = path.stat()
            print(f'PACK {index}/{len(entries)} {name} {before.st_size} bytes', flush=True)
            with path.open('rb') as source, archive.open('hairdeck/' + name, 'w', force_zip64=True) as target:
                for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                    digest.update(block)
                    target.write(block)
                    done += len(block)
                    elapsed = time.monotonic() - started
                    if elapsed - last_update >= 15:
                        print(f'PROGRESS {done}/{total} bytes {elapsed:.1f}s', flush=True)
                        last_update = elapsed
            if digest.hexdigest() != expected and expected is not None:
                raise ValueError('Source does not match the released SHA-256: ' + name)
            if before.st_mtime_ns != path.stat().st_mtime_ns or before.st_size != path.stat().st_size:
                raise ValueError('Source changed while packaging: ' + name)
            records[name] = dict(size=before.st_size, sha256=digest.hexdigest())
        manifest = dict(format='comfyui-hairdeck-model-bundle', format_version=1, bundle_version=VERSION,
                        kind=kind, created_utc=datetime.now(timezone.utc).isoformat(), files=records,
                        sources=dict(hairdeck='https://huggingface.co/hyz317/HairDeck',
                                     sam3='https://huggingface.co/facebook/sam3',
                                     dinov3='https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m',
                                     birefnet='https://huggingface.co/ZhengPeng7/BiRefNet-matting'))
        marker = 'MODEL_BUNDLE_MANIFEST.json' if kind == 'models' else 'WINDOWS_TOOLS_MANIFEST.json'
        archive.writestr('hairdeck/' + marker, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        archive.writestr('hairdeck/' + ('模型包使用说明.md' if kind == 'models' else 'Windows工具包使用说明.md'), readme)
    temporary.replace(output)
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    checksum = digest_file(output)
    output.with_suffix(output.suffix + '.sha256').write_text(checksum + '  ' + output.name + '\n', encoding='ascii')
    print('BUNDLE_WRITTEN', output, output.stat().st_size, 'bytes', checksum, flush=True)
    return output, manifest


def verify_archive(path, manifest):
    with zipfile.ZipFile(path) as archive:
        expected_names = {'hairdeck/' + name for name in manifest['files']}
        if not expected_names.issubset(archive.namelist()):
            raise ValueError('Archive is missing required members.')
        for index, (name, expected) in enumerate(manifest['files'].items(), 1):
            digest = hashlib.sha256()
            with archive.open('hairdeck/' + name) as source:
                for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest() != expected['sha256']:
                raise ValueError('Archive extraction hash mismatch: ' + name)
            print(f'ARCHIVE_VERIFIED {index}/{len(manifest["files"])} {name}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Existing verified HairDeck model workspace')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--windows-tools', action='store_true', help='Also package the Windows Blender/add-on archives separately')
    args = parser.parse_args()
    source = args.source.resolve()
    destination = args.output_dir.resolve()
    readme = '''# HairDeck 离线模型包

包含六个运行必需模型、发片/骨骼统计数据、示例角色数据和各组件许可。
不包含缓存、日志、生成结果、源码仓库或用户配置。

1. 先安装 ComfyUI-HairDeck 插件及其 Python 依赖。
2. 将此 ZIP 解压到 ComfyUI/models/，得到 ComfyUI/models/hairdeck/ckpt、data 和 third_party。
3. 使用 ComfyUI 的 Python 执行：python models/hairdeck/verify_models.py models/hairdeck
4. 校验通过后重启 ComfyUI，模型加载节点选择 auto。

解压后的 hairdeck 文件夹也可放在其他目录，并通过 ComfyUI 的 extra_model_paths.yaml 注册 hairdeck 路径。
无需逐个下载模型，也无需运行在线模型下载步骤。

VRM 导出还需要 Blender 4.2 LTS 和 VRM Add-on。可另下载 Windows 工具包并解压到同一 ComfyUI/models/ 目录，
再执行：python custom_nodes/ComfyUI-HairDeck/install_models.py --models-dir models/hairdeck --only-blender
缓存的工具压缩包校验通过时，该命令会直接使用本地文件完成解压与插件启用。
Linux 用户可使用同一模型包，工具安装需按平台另行准备；Linux 原生运行尚未真机验证。

原始来源见 MODEL_BUNDLE_MANIFEST.json，各组件许可见 licenses/。
源项目：https://github.com/hyz317/HairDeck
节点：https://github.com/FengLairh/ComfyUI-HairDeck
'''
    output, manifest = write_bundle(destination / f'HairDeck-Models-v{VERSION}.zip', model_files(source),
                                    kind='models', readme=readme)
    verify_archive(output, manifest)
    if args.windows_tools:
        windows = constant(PROJECT / 'install_models.py', 'BLENDER')['Windows']
        addon = constant(PROJECT / 'install_models.py', 'ADDON')
        archive_name = addon[0].rsplit('/', 1)[-1]
        entries = {f'tools/blender/{windows[0]}': (source / 'tools/blender' / windows[0], windows[1]),
                   f'tools/blender/{archive_name}': (source / 'tools/blender' / archive_name, addon[1])}
        instructions = ('# Windows VRM 导出工具包\n\n'
                        '将本包解压到 ComfyUI/models/，与模型包的 hairdeck 文件夹合并。\n'
                        '然后使用 ComfyUI 的 Python 执行：\n\n'
                        'python custom_nodes/ComfyUI-HairDeck/install_models.py --models-dir models/hairdeck --only-blender\n\n'
                        '文件包含 Blender 4.2.23 Windows x64 官方 ZIP 与 VRM Add-on 4.10.2，保留其原有许可。\n'
                        '不包含本机 Blender 用户偏好、登录信息或个人路径。\n')
        tool_output, tool_manifest = write_bundle(destination / f'HairDeck-Windows-VRM-Tools-v{VERSION}.zip', entries,
                                                  kind='tools', readme=instructions)
        verify_archive(tool_output, tool_manifest)
    print('ALL_BUNDLES_VERIFIED', destination, flush=True)


if __name__ == '__main__':
    main()
