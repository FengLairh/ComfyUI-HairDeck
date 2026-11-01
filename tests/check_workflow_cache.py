import json
from pathlib import Path
import argparse

from run_comfy_workflow import run, static_prompt


def cached_nodes(result):
    return set(next(message[1]['nodes'] for message in result['status']['messages'] if message[0] == 'execution_cached'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--comfy-dir', type=Path, required=True)
    args = parser.parse_args()
    report = Path(__file__).resolve().parents[1] / '.runtime'
    run(static_prompt('HairDeck_native_example.png'), 'http://127.0.0.1:8189', report / 'cache-prime.json')
    unchanged = run(static_prompt('HairDeck_native_example.png'), 'http://127.0.0.1:8189', report / 'cache-unchanged.json')
    changed = run(static_prompt('HairDeck_native_example.png', seed=1), 'http://127.0.0.1:8189', report / 'cache-seed.json')
    assert {'1', '2'} <= cached_nodes(unchanged)
    assert '1' in cached_nodes(changed) and '2' not in cached_nodes(changed)
    manifest = next(item for item in changed['outputs']['3']['hairdeck_files'] if item['label'] == '结果清单')
    path = args.comfy_dir / 'output' / manifest['subfolder'] / manifest['filename']
    assert json.loads(path.read_text(encoding='utf-8'))['preprocess_cache_hit'] is True
    print('CACHE_CHECK_PASSED', json.dumps({'same_seed': sorted(cached_nodes(unchanged)),
                                          'changed_seed': sorted(cached_nodes(changed))}))
