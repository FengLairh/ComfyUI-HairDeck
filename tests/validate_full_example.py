"""Validate and organize the files produced by the full native ComfyUI example."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import av
import numpy as np
from PIL import Image
import trimesh


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    root = args.directory.resolve()
    history = json.loads((root / 'run_history.json').read_text(encoding='utf-8'))
    assert history['status']['status_str'] == 'success'
    workflow = json.loads((root / 'workflow.json').read_text(encoding='utf-8'))
    meshes = {}
    for prefix in ['hair_nohead', 'hair_with_head', 'hair_bone_lines']:
        path = next(root.glob(prefix + '_*.glb'))
        scene = trimesh.load(str(path), force='scene')
        geometries = list(scene.geometry.values())
        assert geometries and all(np.isfinite(mesh.vertices).all() for mesh in geometries)
        meshes[path.name] = dict(meshes=len(geometries), vertices=sum(len(mesh.vertices) for mesh in geometries),
                                 triangles=sum(len(mesh.faces) for mesh in geometries))
        if prefix == 'hair_nohead':
            uv = geometries[0].visual.uv
            assert uv is not None and np.isfinite(uv).all() and np.all(np.ptp(uv, axis=0) > 0)

    vrm = json.loads(next(root.glob('avatar_*.check.json')).read_text(encoding='utf-8'))
    assert vrm['ok'] and not vrm['problems']
    work = Path(vrm['vrm']).parent
    cards = next(work.glob('cards_seed*.json'))
    chains = next(work.glob('chains_seed*.json'))
    shutil.copyfile(cards, root / 'cards.json')
    shutil.copyfile(chains, root / 'chains.json')
    card_data = json.loads((root / 'cards.json').read_text())
    chain_data = json.loads((root / 'chains.json').read_text())
    assert len(card_data) == vrm['n_cards'] and len(chain_data) == vrm['n_chains_in']

    images = {}
    for prefix in ['preprocess', 'model_input', 'hair_mask', 'face_mask', 'avatar_views']:
        path = next(root.glob(prefix + '_*.png'))
        with Image.open(path) as image:
            image.load()
            embedded = json.loads(image.info['workflow'])
            embedded_prompt = json.loads(image.info['prompt'])
            assert embedded == workflow and len(embedded_prompt) == len(workflow['nodes'])
            if prefix.endswith('_mask'):
                assert np.array(image).min() == 0 and np.array(image).max() == 255
            images[path.name] = dict(width=image.width, height=image.height, workflow_embedded=True)

    videos = {}
    for prefix in ['motion', 'motion_bones']:
        path = next(p for p in root.glob(prefix + '_*.mp4') if prefix != 'motion' or not p.name.startswith('motion_bones'))
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            frames = sum(1 for _ in container.decode(video=0))
            duration = float(container.duration / av.time_base)
            assert frames > 0 and abs(duration - 3.0) < .1
            videos[path.name] = dict(codec=stream.codec_context.name, width=stream.width, height=stream.height,
                                     frames=frames, duration=duration)

    info = json.loads((root / 'run_info.json').read_text(encoding='utf-8'))
    summary = dict(device=info['device'], comfyui=info['comfyui'], torch=info['torch'],
                   elapsed_seconds=info['elapsed_seconds'], workflow_nodes=len(workflow['nodes']),
                   hair_cards=len(card_data), generated_chains=len(chain_data), vrm_spring_groups=vrm['n_spring_groups'],
                   vrm_validation=True, meshes=meshes, images=images, videos=videos,
                   input_sha256=hashlib.sha256((root / 'input.png').read_bytes()).hexdigest())
    (root / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    readme = f'''# 本机 ComfyUI 完整示例

本示例通过原生 ComfyUI 队列生成，运行状态为 success。

- 显卡：{info['device']}
- ComfyUI：{info['comfyui']}；PyTorch：{info['torch']}
- 总耗时：{info['elapsed_seconds']} 秒（含模型首次加载、两份动画和所有文件输出）
- 发片：{len(card_data)} 张；生成骨骼链：{len(chain_data)} 条；VRM 弹簧组：{vrm['n_spring_groups']} 组
- VRM 结构检查通过；两份动画均为 3 秒 H.264，已逐帧解码检查。

## 复现

1. 已安装 ComfyUI-HairDeck 节点和模型后，把 input.png 复制到 ComfyUI/input，并命名为 HairDeck_example.png。
2. 导入 workflow.json，或者将 preprocess / avatar_views PNG 拖进 ComfyUI；这些 PNG 内嵌完整工作流。
3. 点击运行。模型包选择 auto；无需网页后端或 WSL。

## 文件

- input.png：实际输入，来自 HairDeck 发布模型仓库的 ex01.png。
- preprocess / model_input / hair_mask / face_mask PNG：预处理、模型输入与蒙版。
- hair_nohead GLB：纯头发，保留 UV；hair_with_head GLB：参考头模；hair_bone_lines GLB：骨骼线可视化。
- avatar VRM：装配到示例角色，包含蒙皮与弹簧骨骼；avatar_views PNG：角色正侧背面预览。
- motion MP4：正常动画；motion_bones MP4：显示骨骼线的动画。
- cards.json / chains.json：本次生成的发片曲线与骨骼链数据。
- summary.json：文件结构、视频、PNG 工作流元数据等检查结果。
- workflow.json / workflow.api.json：可编辑界面工作流与对应队列参数。

此示例使用上游示例角色；GLB 中的骨骼线用于显示，真正的蒙皮和弹簧属性位于 VRM。
示例输入来源：https://huggingface.co/hyz317/HairDeck/tree/main/data/demo_examples
'''
    (root / '使用说明.md').write_text(readme, encoding='utf-8')
    archive_path = root.parent / (root.name + '.zip')
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in root.iterdir():
            if path.suffix in ('.png', '.glb', '.vrm', '.mp4') or path.name in (
                'workflow.json', 'workflow.api.json', 'summary.json', 'cards.json', 'chains.json', '使用说明.md'):
                archive.write(path, root.name + '/' + path.name)
    print('FULL_EXAMPLE_VALIDATED', json.dumps(summary, ensure_ascii=False), flush=True)
    print('EXAMPLE_ARCHIVE', archive_path, archive_path.stat().st_size, flush=True)


if __name__ == '__main__':
    main()
