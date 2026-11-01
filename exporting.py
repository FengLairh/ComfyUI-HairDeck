"""Portable file export; inference stays in ComfyUI and previews use short-lived local helpers."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import trimesh

from PIL import Image
import folder_paths
from comfy_api.latest import io, ui

from hairdeck_core import paths
from hairdeck_core.cards.mesh import cards_to_json
from hairdeck_core.infer import glb
from hairdeck_core.vrm import export as vrm
from .runtime import image_tensor


def output_path(prefix, extension):
    if not prefix or Path(prefix).is_absolute() or '..' in prefix.replace('\\', '/').split('/'):
        raise ValueError('文件名前缀必须是输出目录内的相对路径。')
    root = Path(folder_paths.get_output_directory()).resolve()
    directory, stem, counter, subfolder, _ = folder_paths.get_save_image_path(prefix, str(root))
    result = (Path(directory) / f'{stem}_{counter:05}_.{extension}').resolve()
    if not result.is_relative_to(root):
        raise ValueError('输出路径超出 ComfyUI 输出目录。')
    return result, ui.SavedResult(result.name, subfolder, io.FolderType.output)


def validate(hair, rig, color):
    if rig is not None and rig.hair_signature != hair.signature:
        raise ValueError('骨骼与发片来自不同方案，请重新连接对应数据。')
    if color == 'auto':
        return hair.color
    if not re.fullmatch('#[0-9a-fA-F]{6}', color):
        raise ValueError('发色应为 auto 或 #RRGGBB。')
    return [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]


def save_glb(hair, rig, show_head, color, prefix, head=None):
    color = validate(hair, rig, color)
    output, _ = output_path(prefix, 'glb')
    with paths.use(hair.root):
        head_mesh = (trimesh.load(str(head.mesh), force='mesh') if head else glb.head_trimesh()) if show_head else None
        glb.write_glb(str(output), glb.hair_trimesh(hair.cards, color),
                      head_mesh,
                      glb.chain_trimesh(rig.chains) if rig and rig.chains else None)
    return output


def resolve_blender(root, explicit=''):
    if explicit:
        executable = Path(explicit).expanduser().resolve()
        if not executable.is_file() or executable.name.lower() not in ('blender.exe', 'blender'):
            raise ValueError('Blender 路径无效，请选择 Blender 4.2 LTS 的可执行文件。')
        version = subprocess.run([str(executable), '--version'], check=True, capture_output=True, text=True,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if not version.stdout.startswith('Blender 4.2.'):
            raise ValueError('VRM 导出需要 Blender 4.2 LTS，请选择对应版本。')
        return str(executable)
    folder = root / 'tools' / 'blender'
    executable_name = 'blender.exe' if os.name == 'nt' else 'blender'
    candidates = list(folder.glob('blender-4.2*/' + executable_name))
    if not candidates:
        raise FileNotFoundError('未找到 Blender 4.2 LTS。请运行 install_models.py --with-blender，或指定 Blender 路径。')
    return str(candidates[0].resolve())


def work_directory(hair, rig):
    base = Path(folder_paths.get_temp_directory()) / 'hairdeck'
    base.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='export_', dir=base))
    (directory / f'cards_seed{hair.seed}.json').write_text(json.dumps(cards_to_json(hair.cards)), encoding='utf-8')
    (directory / f'chains_seed{hair.seed}.json').write_text(json.dumps(rig.chains), encoding='utf-8')
    return directory


def save_vrm(hair, rig, color, prefix, blender_path, head=None):
    color = validate(hair, rig, color)
    blender = resolve_blender(hair.root, blender_path)
    directory = work_directory(hair, rig)
    output, _ = output_path(prefix, 'vrm')
    with paths.use(hair.root, blender=blender):
        result = vrm.export_vrm(str(directory), hair.seed, color, body=str(head.body) if head else None)
    if not result['ok']:
        raise RuntimeError('VRM 结构检查失败：' + '; '.join(result['problems']))
    shutil.copyfile(result['vrm'], output)
    preview_path = output.with_suffix('.png')
    shutil.copyfile(result['rest_png'], preview_path)
    output.with_suffix('.check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return output, image_tensor(Image.open(preview_path))


def save_motion(hair, rig, show_chains, color, prefix, head=None):
    color = validate(hair, rig, color)
    directory = work_directory(hair, rig)
    output, saved = output_path(prefix, 'mp4')
    with paths.use(hair.root):
        result = vrm.turn_preview(str(directory), hair.seed, color, show_chains=show_chains, body=str(head.body) if head else None)
    shutil.copyfile(result['out'], output)
    return output, saved
