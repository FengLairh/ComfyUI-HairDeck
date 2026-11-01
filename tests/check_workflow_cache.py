import json
from pathlib import Path

from run_comfy_workflow import run, static_prompt


def cached_nodes(result):
    return set(next(message[1]['nodes'] for message in result['status']['messages'] if message[0] == 'execution_cached'))


if __name__ == '__main__':
    report = Path(__file__).resolve().parents[1] / '.runtime'
    unchanged = run(static_prompt('HairDeck_native_example.png'), 'http://127.0.0.1:8189', report / 'cache-unchanged.json')
    changed = run(static_prompt('HairDeck_native_example.png', seed=1), 'http://127.0.0.1:8189', report / 'cache-seed.json')
    assert {'1', '2', '3', '4'} <= cached_nodes(unchanged)
    assert {'1', '2', '3'} <= cached_nodes(changed) and '4' not in cached_nodes(changed)
    print('CACHE_CHECK_PASSED', json.dumps({'same_seed': sorted(cached_nodes(unchanged)),
                                          'changed_seed': sorted(cached_nodes(changed))}))
