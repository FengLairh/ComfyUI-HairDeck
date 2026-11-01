"""Apply small, documented ComfyUI ownership adaptations to namespaced sources."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1] / '_vendor'
for path in root.rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    text = re.sub(r'(?m)^\s*@torch\.(?:no_grad|inference_mode)\(\)\n', '\n', text)
    text = text.replace('import hairdeck_pyrender\n', 'import hairdeck_pyrender as pyrender\n')
    if 'pkg_resources' in text:
        text = text.replace('import pkg_resources', 'from importlib.resources import files as resource_files')
        text = re.sub(r'pkg_resources\.resource_filename\(\s*([\"\'])(?:sam3|hairdeck_sam3)\1,\s*([\"\'])([^\"\']+)\2\s*\)',
                      lambda m: 'str(resource_files("hairdeck_sam3").joinpath(' + repr(m[3]) + '))', text)
    path.write_text(text, encoding='utf-8', newline='\n')
