"""One output interface for model files, previews, motion and diagnostics."""
from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil

from PIL import Image
import numpy as np
import folder_paths
from comfy_api.latest import io, ui

from hairdeck_core import paths
from hairdeck_core import materials
from hairdeck_core.cards.mesh import cards_to_json
from hairdeck_core.vrm import export as vrm
from . import exporting, runtime, heads

FORMATS = ['GLB', 'GLB + VRM', 'GLB + VRM + 动画']
UV_MODES = {'共享图集': 'shared', '独立展开': 'unique'}
MATERIAL_PRESETS = {'体积发束': 'volume', '透明发片': 'ribbon', '纯色诊断': 'solid', 'UV 检查': 'checker'}
TEXTURE_SIZES = {'1K': 1024, '2K': 2048, '4K': 4096}


@dataclass
class SavedOutput:
    directory: Path
    model: Path
    ui: dict


def new_directory(prefix):
    # Use the existing resolver/containment check before allocating a result folder.
    exporting.output_path(prefix, 'json')
    directory, stem, counter, _, _ = folder_paths.get_save_image_path(prefix, folder_paths.get_output_directory())
    for number in itertools.count(counter):
        candidate = (Path(directory) / f'{stem}_{number:05}').resolve()
        if not candidate.is_relative_to(Path(folder_paths.get_output_directory()).resolve()):
            raise ValueError('输出路径超出 ComfyUI 输出目录。')
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue


def file_entry(path, label, kind):
    root = Path(folder_paths.get_output_directory()).resolve()
    path = Path(path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('输出文件超出保存目录。')
    return dict(filename=path.name, subfolder=path.parent.relative_to(root).as_posix(), type='output',
                label=label, kind=kind)


def glb_preview(root, model_path, destination):
    helper = Path(__file__).resolve().parent / 'scripts/render_entry.py'
    with paths.use(root):
        environment = vrm._env(True)
    command = [sys.executable, str(helper), 'glb', str(destination), str(model_path)]
    result = subprocess.run(command, env=environment, capture_output=True, text=True,
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
    if result.returncode:
        raise RuntimeError('GLB 预览渲染失败：' + result.stderr[-1500:])
    return runtime.image_tensor(Image.open(destination))


def save(cls, result, format, filename_prefix, color, show_head, show_chains, save_debug, blender_path, head_profile='auto',
         uv_mode='共享图集', texture_size='2K', material_preset='体积发束'):
    if format not in FORMATS:
        raise ValueError('不支持的保存格式。')
    animated = format != 'GLB'
    if (animated or show_chains) and result.rig is None:
        raise ValueError('请在生成节点开启“生成弹簧骨骼”，然后重新生成。')
    if uv_mode not in UV_MODES or texture_size not in TEXTURE_SIZES or material_preset not in MATERIAL_PRESETS:
        raise ValueError('请选择有效的 UV 模式、贴图尺寸和材质预设。')
    rgb = exporting.validate(result.hair, result.rig, color)
    head = heads.resolve(result.hair.root, head_profile)
    if animated:
        exporting.resolve_blender(result.hair.root, blender_path)
    directory = new_directory(filename_prefix)
    relative = directory.relative_to(Path(folder_paths.get_output_directory()).resolve()).as_posix()
    temporary = Path(folder_paths.get_temp_directory()).resolve() / 'hairdeck'
    temporary.mkdir(parents=True, exist_ok=True)
    asset_work = Path(tempfile.mkdtemp(prefix='surface_', dir=temporary))
    asset = materials.create(result.hair.cards, rgb, UV_MODES[uv_mode], TEXTURE_SIZES[texture_size],
                             MATERIAL_PRESETS[material_preset], directory / 'textures', asset_work)
    appearance = str(asset.descriptor)
    files = []
    model_path = exporting.save_glb(result.hair, result.rig if show_chains else None, show_head, color, relative + '/hair', head, appearance)
    files.append(file_entry(model_path, 'GLB 模型', 'model'))
    if animated:
        avatar_path, preview = exporting.save_vrm(result.hair, result.rig, color, relative + '/avatar', blender_path, head, appearance)
        files.append(file_entry(avatar_path, 'VRM 角色', 'model'))
        files.append(file_entry(avatar_path.with_suffix('.check.json'), 'VRM 检查记录', 'data'))
    else:
        preview = glb_preview(result.hair.root, model_path, directory / 'model_views.png')
    primary = ui.ImageSaveHelper.save_images(preview, filename_prefix=relative + '/preview',
                                             folder_type=io.FolderType.output, cls=cls)[0]
    files.append(dict(primary, label='模型多视图', kind='image'))
    if format == 'GLB + VRM + 动画':
        motion_path, motion = exporting.save_motion(result.hair, result.rig, show_chains, color, relative + '/motion', head, appearance)
        files.append(dict(motion, label='动画预览', kind='video'))
    for filename, label in [('base_color.png', '发色与透明度'), ('normal.png', '发丝法线'), ('roughness.png', '粗糙度'),
                            ('metallic_roughness.png', 'glTF 金属粗糙度'), ('unity_metallic_smoothness.png', 'Unity 金属光滑度'),
                            ('alpha.png', '透明度'), ('uv_layout.png', 'UV 布局'),
                            ('material.json', '材质与网格数据说明')]:
        files.append(file_entry(directory / 'textures' / filename, label, 'data' if filename.endswith('.json') else 'image'))
    if save_debug:
        shutil.copyfile(asset_work / 'surface.npz', directory / 'surface.npz')
        files.append(file_entry(directory / 'surface.npz', '优化表面数据', 'data'))
        debug_images = [('model_input', result.crop, '模型输入图'), ('preprocess', result.preview, '预处理图'),
                        ('hair_mask', result.hair_mask[..., None].expand(-1, -1, -1, 3), '头发蒙版'),
                        ('face_mask', result.face_mask[..., None].expand(-1, -1, -1, 3), '面部蒙版')]
        for name, image, label in debug_images:
            image_file = ui.ImageSaveHelper.save_images(image, filename_prefix=relative + '/' + name,
                                                         folder_type=io.FolderType.output, cls=cls)[0]
            files.append(dict(image_file, label=label, kind='image'))
        (directory / 'cards.json').write_text(json.dumps(cards_to_json(result.hair.cards)), encoding='utf-8')
        np.save(directory / 'tokens.npy', result.hair.tokens, allow_pickle=False)
        files.extend([file_entry(directory / 'cards.json', '发片曲线', 'data'),
                      file_entry(directory / 'tokens.npy', '生成特征', 'data')])
        if result.rig is not None:
            (directory / 'chains.json').write_text(json.dumps(result.rig.chains), encoding='utf-8')
            files.append(file_entry(directory / 'chains.json', '骨骼链数据', 'data'))
    manifest = dict(format_version=1, hair_cards=len(result.hair.cards),
                    generated_chains=len(result.rig.chains) if result.rig else 0,
                    seed=result.seed, steps=result.steps, cfg=result.cfg,
                    generation_seconds=result.seconds, preprocess_cache_hit=result.preprocess_cache_hit,
                    saved_format=format, base_head=head.name if head else 'upstream',
                    uv_mode=uv_mode, material_preset=material_preset, texture_size=texture_size,
                    geometry=asset.material['geometry'], files=files)
    manifest_path = directory / 'result.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    files.append(file_entry(manifest_path, '结果清单', 'data'))
    summary = f'{len(result.hair.cards)} 张发片 · {manifest["generated_chains"]} 条骨骼链 · {manifest["base_head"]} · 保存完成'
    return SavedOutput(directory, model_path,
                       dict(images=[primary], hairdeck_files=files, hairdeck_summary=[summary]))
