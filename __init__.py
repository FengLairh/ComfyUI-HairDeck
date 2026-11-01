"""Native HairDeck nodes for ComfyUI."""
from pathlib import Path
import sys

vendor_directory = str(Path(__file__).resolve().parent / '_vendor')
if vendor_directory not in sys.path:
    sys.path.insert(0, vendor_directory)

from .nodes import HairDeckExtension

WEB_DIRECTORY = './web'


async def comfy_entrypoint():
    return HairDeckExtension()
