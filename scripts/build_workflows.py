"""Build portable GUI and API workflows from the installed node contracts."""
import argparse
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from run_comfy_workflow import static_prompt, animated_prompt

TITLES = {'1': '① 模型加载', '2': '② 上传图片并生成', '3': '③ 输出保存与预览'}
POSITIONS = {'1': [30, 40], '2': [390, 40], '3': [870, 40]}


def gui_workflow(prompt, contracts, titles=None, positions=None):
    titles = TITLES if titles is None else titles
    positions = POSITIONS if positions is None else positions
    links, nodes = [], []
    for order, (identifier, spec) in enumerate(prompt.items()):
        contract = contracts[spec['class_type']]
        inputs, widgets = [], []
        schema = {**contract['input'].get('required', {}), **contract['input'].get('optional', {})}
        for name, (kind, *options) in schema.items():
            value = spec['inputs'].get(name)
            options = options[0] if options else {}
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                link_id = len(links) + 1
                output_type = contracts[prompt[value[0]]['class_type']]['output'][value[1]]
                links.append([link_id, int(value[0]), value[1], int(identifier), len(inputs), output_type])
                connection = dict(name=name, type=output_type, link=link_id)
                if isinstance(kind, list) or kind in ('INT', 'FLOAT', 'STRING', 'BOOLEAN', 'COMBO'):
                    connection['widget'] = {'name': name}
                    widgets.append(options.get('default', ''))
                inputs.append(connection)
            elif isinstance(kind, list) or kind in ('INT', 'FLOAT', 'STRING', 'BOOLEAN', 'COMBO'):
                widgets.append(value if value is not None else options.get('default'))
                if options.get('control_after_generate'):
                    widgets.append('fixed')
            else:
                inputs.append(dict(name=name, type=kind, link=None))
        if spec['class_type'] == 'LoadImage':
            widgets = [spec['inputs']['image'], 'image']
        size = {'HairDeckLoader': [300, 120], 'HairDeckGenerate': [410, 530], 'HairDeckSave': [450, 680]}[spec['class_type']]
        outputs = [dict(name=name, type=kind, links=[], slot_index=index)
                   for index, (name, kind) in enumerate(zip(contract['output_name'], contract['output']))]
        nodes.append(dict(id=int(identifier), type=spec['class_type'], title=titles[identifier], pos=positions[identifier],
                          size=size, flags={}, order=order, mode=0, inputs=inputs, outputs=outputs,
                          properties={'Node name for S&R': spec['class_type']}, widgets_values=widgets))
    mapping = {node['id']: node for node in nodes}
    for link_id, origin, slot, _, _, _ in links:
        mapping[origin]['outputs'][slot]['links'].append(link_id)
    return dict(last_node_id=max(mapping), last_link_id=len(links), nodes=nodes, links=links, groups=[], config={},
                extra={'ds': {'scale': .75, 'offset': [30, 40]}}, version=.4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--comfy-url', required=True)
    args = parser.parse_args()
    contracts = requests.get(args.comfy_url.rstrip('/') + '/object_info', timeout=15).json()
    directory = ROOT / 'example_workflows'
    vrm = animated_prompt('HairDeck_example.png')
    vrm['3']['inputs']['format'] = 'GLB + VRM'
    examples = [('01_静态发片_GLB', static_prompt('HairDeck_example.png')),
                ('02_弹簧骨骼_VRM_动画', vrm),
                ('03_完整示例_全流程', animated_prompt('HairDeck_example.png'))]
    for name, prompt in examples:
        for node in prompt.values():
            if 'filename_prefix' in node['inputs']:
                node['inputs']['filename_prefix'] = 'HairDeck/result'
        (directory / (name + '.json')).write_text(json.dumps(gui_workflow(prompt, contracts), ensure_ascii=False, indent=2), encoding='utf-8')
        (directory / (name + '.api.json')).write_text(json.dumps(prompt, ensure_ascii=False, indent=2), encoding='utf-8')
        print('WORKFLOW_WRITTEN', name)


if __name__ == '__main__':
    main()
