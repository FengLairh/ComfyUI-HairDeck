"""Explicit checkpoint selection through ComfyUI's model-folder registry."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import folder_paths

MODELS = {
    'image_model': ('发片生成模型', 'ckpt/image_model', {'.safetensors', '.pt'}),
    'card_vae': ('发片 VAE', 'ckpt/card_vae', {'.safetensors', '.pt'}),
    'chain_model': ('弹簧骨骼模型', 'ckpt/chain_model', {'.safetensors', '.pt'}),
    'sam3': ('SAM 3 分割模型', 'third_party/weights/sam3', {'.pt', '.pth'}),
    'dinov3': ('DINOv3 图像编码器', 'third_party/weights/dinov3', {'.safetensors'}),
    'birefnet': ('BiRefNet 抠图模型', 'third_party/weights/birefnet_matting', {'.safetensors'}),
}
RESOURCE_FILES = ('ckpt/card_vae/stats.json', 'ckpt/card_vae/latent_stats_head.json',
                  'data/token_stats_head.json', 'data/head_frame_train.npz', 'data/spring/chain_stats_head.json')


@dataclass(frozen=True)
class ModelFiles:
    root: Path
    image_model: Path
    card_vae: Path
    chain_model: Path
    sam3: Path
    dinov3: Path
    birefnet: Path


def register():
    folder_paths.add_model_folder_path('hairdeck', str(Path(folder_paths.models_dir) / 'hairdeck'))
    for role, (_, relative, extensions) in MODELS.items():
        category = 'hairdeck_' + role
        for root in folder_paths.get_folder_paths('hairdeck'):
            folder_paths.add_model_folder_path(category, str(Path(root) / relative))
        locations, _ = folder_paths.folder_names_and_paths[category]
        folder_paths.folder_names_and_paths[category] = (locations, extensions)


def resources():
    result = {}
    for folder in folder_paths.get_folder_paths('hairdeck'):
        root = Path(folder).resolve()
        if root in result.values() or not all((root / name).is_file() for name in RESOURCE_FILES):
            continue
        label = Path(folder).name
        name, number = label, 2
        while name in result:
            name = f'{label} ({number})'
            number += 1
        result[name] = root
    return result


def filenames(role):
    return [name.replace('\\', '/') for name in folder_paths.get_filename_list('hairdeck_' + role)]


def default_file(role):
    names = filenames(role)
    preferred = 'sam3.pt' if role == 'sam3' else 'model.safetensors'
    return preferred if preferred in names else (names[0] if names else None)


def resolve(resources_name, names):
    packs = resources()
    if resources_name not in packs:
        raise ValueError('请选择已安装的配套资源目录，或先运行 install_models.py 安装统计文件及角色数据。')
    selected = {}
    for role in MODELS:
        name = names[role].replace('\\', '/')
        if name not in filenames(role):
            raise ValueError(f'{MODELS[role][0]}：请选择模型下拉框中的实际文件。')
        selected[role] = Path(folder_paths.get_full_path_or_raise('hairdeck_' + role, name)).resolve()
    return ModelFiles(packs[resources_name], **selected)


def signature(files):
    selected = [(role, getattr(files, role)) for role in MODELS]
    selected += [(name, files.root / name) for name in RESOURCE_FILES]
    versions = [(role, str(path), path.stat().st_size, path.stat().st_mtime_ns) for role, path in selected]
    return hashlib.sha256(json.dumps(versions).encode()).hexdigest()


register()
