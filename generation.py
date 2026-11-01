"""One generation interface with CPU-only, content-addressed preprocessing data."""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
import time
import zipfile

import numpy as np
import torch
import folder_paths

from . import runtime


@dataclass
class GenerationResult:
    hair: runtime.HairData
    rig: runtime.RigData | None
    crop: torch.Tensor
    hair_mask: torch.Tensor
    face_mask: torch.Tensor
    preview: torch.Tensor
    seed: int
    steps: int
    cfg: float
    preprocess_cache_hit: bool
    seconds: float


def prepared_key(bundle, image):
    return hashlib.sha256(repr((image.mode, image.size)).encode() + image.tobytes() + bundle.signature.encode()).hexdigest()


def cached_preprocess(bundle, image, transparent_mask=None):
    source = runtime.image_bytes(image, transparent_mask)
    key = prepared_key(bundle, source)
    directory = Path(folder_paths.get_temp_directory()) / 'hairdeck' / 'preprocess-v1'
    directory.mkdir(parents=True, exist_ok=True)
    cache = directory / (key + '.npz')
    if cache.is_file():
        try:
            with np.load(cache, allow_pickle=False) as data:
                if str(data['signature']) != key:
                    raise ValueError('Stale preprocessing cache')
                crop = data['crop'].copy()
                if crop.shape != (bundle.hair.model.args.res, bundle.hair.model.args.res, 3):
                    raise ValueError('Invalid preprocessing crop shape')
                prepared = runtime.PreparedImage(bundle.root, bundle.signature, key, crop, data['color'].tolist())
                images = [torch.from_numpy(data[name].copy().astype(np.float32) / 255).unsqueeze(0)
                          for name in ('crop', 'preview')]
                masks = [torch.from_numpy(data[name].copy().astype(np.float32)).unsqueeze(0)
                         for name in ('hair_mask', 'face_mask')]
                return (prepared, images[0], *masks, images[1]), True
        except (OSError, ValueError, KeyError, zipfile.BadZipFile):
            # An interrupted/corrupted temporary cache must not block regeneration.
            pass
    outputs = runtime.preprocess(bundle, image, transparent_mask, source=source)
    prepared, crop, hair_mask, face_mask, preview = outputs
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, suffix='.npz', delete=False) as target:
            temporary = Path(target.name)
            np.savez_compressed(target, signature=key, crop=prepared.crop, color=prepared.color,
                                hair_mask=hair_mask[0].numpy().astype(np.uint8),
                                face_mask=face_mask[0].numpy().astype(np.uint8),
                                preview=np.clip(preview[0].numpy() * 255 + .5, 0, 255).astype(np.uint8))
        os.replace(temporary, cache)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return outputs, False


def generate(model, image, seed, steps, cfg, generate_bones, transparent_mask=None):
    started = time.monotonic()
    outputs, cache_hit = cached_preprocess(model, image, transparent_mask)
    prepared, crop, hair_mask, face_mask, preview = outputs
    hair = runtime.generate(model, prepared, seed, steps, cfg)
    rig = runtime.generate_rig(model, hair, seed, 50, 2.0) if generate_bones else None
    return GenerationResult(hair, rig, crop, hair_mask, face_mask, preview, seed, steps, cfg,
                            cache_hit, round(time.monotonic() - started, 3))
