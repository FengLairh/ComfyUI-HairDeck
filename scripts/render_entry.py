"""Run CPU/graphics preview code with this package's isolated source modules."""
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_vendor'))
mode = sys.argv.pop(1)
module = {'vrm': 'hairdeck_core.vrm.render', 'motion': 'hairdeck_core.vis.turn_preview'}[mode]
runpy.run_module(module, run_name='__main__')
