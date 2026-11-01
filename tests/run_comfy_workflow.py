"""Submit real native ComfyUI workflows and retain their execution evidence."""
import argparse
import json
from pathlib import Path
import time
import uuid

import requests


def static_prompt(image, seed=0):
    return {
        '1': {'class_type': 'HairDeckLoader', 'inputs': {'bundle': 'auto'}},
        '2': {'class_type': 'HairDeckGenerate', 'inputs': {'model': ['1', 0], 'image': image,
                                                       'seed': seed, 'steps': 50, 'cfg': 2.0, 'generate_bones': False}},
        '3': {'class_type': 'HairDeckSave', 'inputs': {'result': ['2', 0], 'format': 'GLB',
                                                    'filename_prefix': 'HairDeck/three_node_test', 'color': 'auto',
                                                    'show_head': False, 'show_chains': False,
                                                    'save_debug': True, 'blender_path': ''}},
    }


def animated_prompt(image):
    prompt = static_prompt(image)
    prompt['2']['inputs']['generate_bones'] = True
    prompt['3']['inputs']['format'] = 'GLB + VRM + 动画'
    return prompt


def run(prompt, url, report, workflow=None):
    payload = {'prompt': prompt, 'client_id': uuid.uuid4().hex}
    if workflow is not None:
        payload['extra_data'] = {'extra_pnginfo': {'workflow': workflow}}
    response = requests.post(url + '/prompt', json=payload, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(response.text[:6000])
    identifier = response.json()['prompt_id']
    print('PROMPT_ACCEPTED', identifier, flush=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    (report.with_suffix('.prompt.json')).write_text(json.dumps(prompt, ensure_ascii=False, indent=2), encoding='utf-8')
    deadline = time.monotonic() + 1200
    while time.monotonic() < deadline:
        history = requests.get(url + '/history/' + identifier, timeout=15).json()
        if identifier in history:
            result = history[identifier]
            report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            status = result['status']
            print('EXECUTION_STATUS', status['status_str'], flush=True)
            if status['status_str'] != 'success':
                print(json.dumps(status['messages'], ensure_ascii=False)[-8000:], flush=True)
                raise SystemExit(1)
            print('NATIVE_WORKFLOW_PASSED', report, flush=True)
            return result
        time.sleep(2)
    raise TimeoutError('ComfyUI workflow did not finish within 20 minutes.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8189')
    parser.add_argument('--image', default='HairDeck_native_example.png')
    parser.add_argument('--animated', action='store_true')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    prompt = animated_prompt(args.image) if args.animated else static_prompt(args.image)
    run(prompt, args.url, args.report)
