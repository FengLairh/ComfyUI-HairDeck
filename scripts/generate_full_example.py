"""Generate a complete example with exactly three native HairDeck nodes."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import sys
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from run_comfy_workflow import animated_prompt, run, loader_defaults
from build_workflows import gui_workflow


def full_prompt(image, prefix, loader=None):
    prompt = animated_prompt(image, loader=loader)
    prompt['3']['inputs']['filename_prefix'] = prefix
    return prompt


def full_gui(prompt, contracts):
    return gui_workflow(prompt, contracts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--comfy-dir', type=Path, required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8189')
    parser.add_argument('--image', default='HairDeck_example.png')
    args = parser.parse_args()
    comfy = args.comfy_dir.resolve()
    source = (comfy / 'input' / args.image).resolve()
    if not source.is_relative_to((comfy / 'input').resolve()) or not source.is_file():
        raise ValueError('Example image must be inside ComfyUI/input.')
    system = requests.get(args.url + '/system_stats', timeout=10).json()
    contracts = requests.get(args.url + '/object_info', timeout=10).json()
    registered = {name for name in contracts if name.startswith('HairDeck')}
    if registered != {'HairDeckLoader', 'HairDeckGenerate', 'HairDeckSave'}:
        raise ValueError('The running instance must register exactly the three HairDeck nodes.')
    date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d')
    prompt = full_prompt(args.image, 'HairDeck/three_node_example_' + date, loader=loader_defaults(contracts))
    workflow = full_gui(prompt, contracts)
    report = ROOT / '.runtime/full-example-three-history.json'
    started = time.monotonic()
    result = run(prompt, args.url, report, workflow=workflow)
    saved = result['outputs']['3']['hairdeck_files']
    directory = (comfy / 'output' / saved[0]['subfolder']).resolve()
    if not directory.is_relative_to((comfy / 'output').resolve()):
        raise ValueError('Result directory is outside ComfyUI output.')
    shutil.copyfile(source, directory / 'input.png')
    shutil.copyfile(report, directory / 'run_history.json')
    (directory / 'workflow.json').write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding='utf-8')
    (directory / 'workflow.api.json').write_text(json.dumps(prompt, ensure_ascii=False, indent=2), encoding='utf-8')
    info = dict(result_directory=str(directory), elapsed_seconds=round(time.monotonic() - started, 2),
                device=system['devices'][0]['name'], comfyui=system['system']['comfyui_version'],
                python=system['system']['python_version'].split()[0], torch=system['system']['pytorch_version'])
    (directory / 'run_info.json').write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / '.runtime/last-full-example.path').write_text(str(directory), encoding='utf-8')
    print('FULL_THREE_NODE_EXAMPLE_READY', json.dumps(info, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
