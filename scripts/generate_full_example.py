"""Generate a complete, reproducible example on an existing native ComfyUI instance."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from run_comfy_workflow import animated_prompt, run
from build_workflows import gui_workflow, TITLES, POSITIONS


def full_prompt(image, prefix):
    prompt = animated_prompt(image)
    prompt['5']['inputs']['filename_prefix'] = prefix + '/hair_nohead'
    prompt['9']['inputs']['filename_prefix'] = prefix + '/avatar'
    prompt['10']['inputs']['filename_prefix'] = prefix + '/motion'
    prompt.update({
        '11': {'class_type': 'HairDeckExportGLB', 'inputs': {'hair': ['4', 0], 'show_head': True, 'color': 'auto',
                                                          'filename_prefix': prefix + '/hair_with_head'}},
        '12': {'class_type': 'Preview3D', 'inputs': {'model_file': ['11', 0]}},
        '13': {'class_type': 'HairDeckExportGLB', 'inputs': {'hair': ['4', 0], 'rig': ['8', 0], 'show_head': True,
                                                          'color': 'auto', 'filename_prefix': prefix + '/hair_bone_lines'}},
        '14': {'class_type': 'Preview3D', 'inputs': {'model_file': ['13', 0]}},
        '15': {'class_type': 'HairDeckMotionPreview', 'inputs': {'hair': ['4', 0], 'rig': ['8', 0], 'show_chains': True,
                                                              'color': 'auto', 'filename_prefix': prefix + '/motion_bones'}},
        '20': {'class_type': 'SaveImage', 'inputs': {'images': ['3', 4], 'filename_prefix': prefix + '/preprocess'}},
        '21': {'class_type': 'SaveImage', 'inputs': {'images': ['3', 1], 'filename_prefix': prefix + '/model_input'}},
        '22': {'class_type': 'MaskToImage', 'inputs': {'mask': ['3', 2]}},
        '23': {'class_type': 'SaveImage', 'inputs': {'images': ['22', 0], 'filename_prefix': prefix + '/hair_mask'}},
        '24': {'class_type': 'MaskToImage', 'inputs': {'mask': ['3', 3]}},
        '25': {'class_type': 'SaveImage', 'inputs': {'images': ['24', 0], 'filename_prefix': prefix + '/face_mask'}},
        '26': {'class_type': 'SaveImage', 'inputs': {'images': ['9', 1], 'filename_prefix': prefix + '/avatar_views'}},
    })
    return prompt


def full_gui(prompt, contracts):
    titles = dict(TITLES)
    titles.update({'5': 'GLB：纯头发', '6': '预览：纯头发', '11': 'GLB：参考头模', '12': '预览：参考头模',
                   '13': 'GLB：骨骼线可视化', '14': '预览：骨骼线', '15': '动画：显示骨骼线',
                   '20': '保存预处理图（含工作流）', '21': '保存模型输入图', '22': '头发蒙版转图像',
                   '23': '保存头发蒙版', '24': '面部蒙版转图像', '25': '保存面部蒙版', '26': '保存角色多视图（含工作流）'})
    positions = dict(POSITIONS)
    positions.update({'1': [30, 30], '2': [30, 450], '3': [420, 30], '4': [850, 30], '5': [1260, 30],
                      '6': [1660, 30], '7': [420, 520], '8': [1260, 390], '9': [1660, 1000], '10': [2120, 1000],
                      '11': [1260, 780], '12': [2120, 30], '13': [1660, 600], '14': [2580, 30], '15': [2580, 1000],
                      '20': [420, 1040], '21': [850, 520], '22': [30, 900], '23': [850, 1000],
                      '24': [30, 1120], '25': [850, 1450], '26': [1660, 1500]})
    workflow = gui_workflow(prompt, contracts, titles=titles, positions=positions)
    workflow['extra']['ds'] = {'scale': .38, 'offset': [20, 20]}
    return workflow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--comfy-dir', type=Path, required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8189')
    parser.add_argument('--image', default='HairDeck_example.png')
    args = parser.parse_args()
    comfy = args.comfy_dir.resolve()
    source = comfy / 'input' / args.image
    if not source.is_file():
        raise FileNotFoundError('Put the example image in ComfyUI/input before running.')
    system = requests.get(args.url + '/system_stats', timeout=10).json()
    contracts = requests.get(args.url + '/object_info', timeout=10).json()
    for node in ['HairDeckLoader', 'HairDeckGenerate', 'HairDeckExportVRM', 'HairDeckMotionPreview', 'MaskToImage']:
        if node not in contracts:
            raise RuntimeError('Missing node: ' + node)
    # The user-facing date follows Asia/Shanghai, independently of host timezone.
    from zoneinfo import ZoneInfo
    date = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d')
    parent = comfy / 'output/HairDeck'
    version = 1
    while (parent / f'full_example_{date}_v{version:03}').exists():
        version += 1
    name = f'full_example_{date}_v{version:03}'
    result = parent / name
    result.mkdir(parents=True)
    shutil.copyfile(source, result / 'input.png')
    prompt = full_prompt(args.image, 'HairDeck/' + name)
    workflow = full_gui(prompt, contracts)
    (result / 'workflow.json').write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding='utf-8')
    (result / 'workflow.api.json').write_text(json.dumps(prompt, ensure_ascii=False, indent=2), encoding='utf-8')
    start = time.monotonic()
    run(prompt, args.url, result / 'run_history.json', workflow=workflow)
    (result / 'environment.json').write_text(json.dumps(system, ensure_ascii=False, indent=2), encoding='utf-8')
    info = dict(result_directory=str(result), elapsed_seconds=round(time.monotonic() - start, 2),
                device=system['devices'][0]['name'], comfyui=system['system']['comfyui_version'],
                python=system['system']['python_version'].split()[0], torch=system['system']['pytorch_version'])
    (result / 'run_info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / '.runtime/last-full-example.path').write_text(str(result), encoding='utf-8')
    portable = full_prompt('HairDeck_example.png', 'HairDeck/full_example')
    portable_gui = full_gui(portable, contracts)
    base = ROOT / 'example_workflows/03_完整示例_全流程'
    base.with_suffix('.json').write_text(json.dumps(portable_gui, ensure_ascii=False, indent=2), encoding='utf-8')
    base.with_suffix('.api.json').write_text(json.dumps(portable, ensure_ascii=False, indent=2), encoding='utf-8')
    print('FULL_EXAMPLE_READY', json.dumps(info, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
