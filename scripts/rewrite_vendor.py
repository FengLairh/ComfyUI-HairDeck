"""Namespace third-party source copies so they do not collide with other node packs."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1] / '_vendor'
for path in root.rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    for original, private in [('sam3', 'hairdeck_sam3'), ('dinov3', 'hairdeck_dinov3'), ('pyrender', 'hairdeck_pyrender')]:
        text = re.sub(r'(?m)^(\s*(?:from|import)\s+)' + original + r'(?=[.\s])', r'\g<1>' + private, text)
        text = text.replace(f'resource_filename("{original}"', f'resource_filename("{private}"')
        text = text.replace(f"resource_filename('{original}'", f"resource_filename('{private}'")
        text = re.sub(r'(resource_filename\(\s*[\"\'])' + original + r'([\"\'])',
                      r'\g<1>' + private + r'\2', text)
    if 'hairdeck_core' in path.parts or 'blender_scripts' in path.parts:
        text = re.sub(r'(?m)^(\s*(?:from|import)\s+)hairdeck(?=[.\s])', r'\g<1>hairdeck_core', text)
        text = text.replace("'hairdeck.vrm.", "'hairdeck_core.vrm.")
        text = text.replace("'hairdeck.vis.", "'hairdeck_core.vis.")
    path.write_text(text, encoding='utf-8', newline='\n')
