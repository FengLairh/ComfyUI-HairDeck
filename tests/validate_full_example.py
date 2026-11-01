"""Validate saved files and embedded workflow metadata from the three-node example."""
import argparse
import json
from pathlib import Path
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
    workflow = json.loads((root / 'workflow.json').read_text(encoding='utf-8'))
    assert history['status']['status_str'] == 'success'
    assert len(workflow['nodes']) == 3
    assert {node['type'] for node in workflow['nodes']} == {'HairDeckLoader', 'HairDeckGenerate', 'HairDeckSave'}
    manifest = json.loads((root / 'result.json').read_text(encoding='utf-8'))
    summary = history['outputs']['3']['hairdeck_summary']
    assert isinstance(summary, list) and len(summary) == 1 and '保存完成' in summary[0]
    for entry in manifest['files']:
        assert (root / entry['filename']).is_file(), entry['filename']
    model = next(root.glob('hair_*.glb'))
    scene = trimesh.load(str(model), force='scene')
    hair = scene.geometry['hair_cards']
    assert np.isfinite(hair.vertices).all() and hair.visual.uv is not None and np.isfinite(hair.visual.uv).all()
    vrm = json.loads(next(root.glob('avatar_*.check.json')).read_text(encoding='utf-8'))
    assert vrm['ok'] and not vrm['problems']
    cards = json.loads((root / 'cards.json').read_text(encoding='utf-8'))
    chains = json.loads((root / 'chains.json').read_text(encoding='utf-8'))
    assert len(cards) == manifest['hair_cards'] and len(chains) == manifest['generated_chains']
    images = {}
    for prefix in ['preview', 'preprocess', 'model_input', 'hair_mask', 'face_mask']:
        path = next(root.glob(prefix + '_*.png'))
        with Image.open(path) as image:
            image.load()
            assert json.loads(image.info['workflow']) == workflow
            assert len(json.loads(image.info['prompt'])) == 3
            images[path.name] = dict(width=image.width, height=image.height, workflow_embedded=True)
    movie = next(root.glob('motion_*.mp4'))
    with av.open(str(movie)) as container:
        stream = container.streams.video[0]
        frames = sum(1 for _ in container.decode(video=0))
        duration = float(container.duration / av.time_base)
        assert frames == 90 and abs(duration - 3) < .1
        video = dict(codec=stream.codec_context.name, width=stream.width, height=stream.height,
                     frames=frames, duration=duration)
    info = json.loads((root / 'run_info.json').read_text(encoding='utf-8'))
    summary = dict(workflow_nodes=3, device=info['device'], elapsed_seconds=info['elapsed_seconds'],
                   hair_cards=len(cards), generated_chains=len(chains), vrm_spring_groups=vrm['n_spring_groups'],
                   vrm_validation=True, glb_vertices=len(hair.vertices), images=images, video=video,
                   preprocess_cache_hit=manifest['preprocess_cache_hit'])
    (root / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    readme = '''# HairDeck 三节点完整示例

1. 安装 v0.2 节点和模型，把 input.png 复制到 ComfyUI/input/ 并命名为 HairDeck_example.png。
2. 导入 workflow.json，或将 preview / preprocess PNG 拖进 ComfyUI；图片内嵌的工作流只有三个节点。
3. 第一个节点加载模型；第二个节点直接选择/上传图片并生成；第三个节点选择保存格式并输出。

所有结果集中在同一文件夹：GLB、VRM、动画、预览、蒙版、曲线及 result.json 清单。
VRM 使用上游示例角色，骨骼线仅是可视化；真正蒙皮与弹簧属性在 VRM。
本例由原生 ComfyUI 队列实际生成，VRM 检查通过，视频为 480×480、90 帧、3 秒 H.264。
'''
    (root / '使用说明.md').write_text(readme, encoding='utf-8')
    archive = root.parent / (root.name + '.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for path in root.iterdir():
            if path.suffix in ('.png', '.glb', '.vrm', '.mp4', '.npy') or path.name in (
                'workflow.json', 'workflow.api.json', 'summary.json', 'result.json', 'cards.json', 'chains.json', '使用说明.md'):
                output.write(path, root.name + '/' + path.name)
    print('FULL_THREE_NODE_EXAMPLE_VALIDATED', json.dumps(summary, ensure_ascii=False), flush=True)
    print('EXAMPLE_ARCHIVE', archive, flush=True)


if __name__ == '__main__':
    main()
