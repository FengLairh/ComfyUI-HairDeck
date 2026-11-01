from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_vendor'))
from hairdeck_sam3.model_builder import build_sam3_image_model
from hairdeck_sam3.model.sam3_image_processor import Sam3Processor
from hairdeck_core.models.imgmodel import ImgSetDiT
from hairdeck_core.infer.glb import hair_trimesh
import hairdeck_pyrender

print('VENDORED_IMPORTS_OK', build_sam3_image_model.__module__, hairdeck_pyrender.__name__)
