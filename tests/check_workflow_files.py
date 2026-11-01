"""Check GUI link/widget serialization against ComfyUI's actual node contracts."""
import json
from pathlib import Path

import requests

root = Path(__file__).resolve().parents[1]
contracts = requests.get('http://127.0.0.1:8189/object_info', timeout=15).json()
for path in (root / 'example_workflows').glob('*.json'):
    if path.name.endswith('.api.json'):
        continue
    workflow = json.loads(path.read_text(encoding='utf-8'))
    links = {link[0]: link for link in workflow['links']}
    actual = {}
    for node in workflow['nodes']:
        contract = contracts[node['type']]
        schema = {**contract['input'].get('required', {}), **contract['input'].get('optional', {})}
        widgets = iter(node['widgets_values'])
        slots = {slot['name']: slot for slot in node.get('inputs', [])}
        values = {}
        for name, (kind, *options) in schema.items():
            options = options[0] if options else {}
            widget = isinstance(kind, list) or kind in ('INT', 'FLOAT', 'STRING', 'BOOLEAN', 'COMBO')
            default = next(widgets) if widget else None
            if widget and options.get('control_after_generate'):
                next(widgets)
            if slots.get(name, {}).get('link') is not None:
                _, origin, origin_slot, target, target_slot, _ = links[slots[name]['link']]
                assert target == node['id'] and node['inputs'][target_slot]['name'] == name
                values[name] = [str(origin), origin_slot]
            elif widget:
                values[name] = default
        actual[str(node['id'])] = {'class_type': node['type'], 'inputs': values}
    expected = json.loads(path.with_name(path.stem + '.api.json').read_text(encoding='utf-8'))
    assert actual == expected, (path.name, actual, expected)
    print('WORKFLOW_FILE_PASSED', path.name)
