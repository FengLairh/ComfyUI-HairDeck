from pathlib import Path

root = Path(__file__).resolve().parents[1] / '_vendor'
for package in ['hairdeck_core', 'hairdeck_sam3', 'hairdeck_dinov3']:
    for path in (root / package).rglob('*.py'):
        source = path.read_text(encoding='utf-8')
        if 'F.scaled_dot_product_attention(' not in source:
            continue
        source = source.replace('F.scaled_dot_product_attention(', 'comfy_attention(')
        # Keep a module docstring and any future imports at the beginning.
        lines = source.splitlines()
        insertion = next(i for i, line in enumerate(lines) if line.startswith('import torch'))
        lines.insert(insertion, 'from hairdeck_comfy_ops import scaled_dot_product_attention as comfy_attention')
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
