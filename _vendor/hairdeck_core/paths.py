"""Portable workspace paths supplied by the current ComfyUI execution."""
from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path

_workspace = ContextVar('hairdeck_workspace', default=None)
_blender = ContextVar('hairdeck_blender', default=None)
_vendor = Path(__file__).resolve().parents[1]
_layout = dict(data='data', ckpt='ckpt', results='results', scratch='scratch', logs='logs',
               weights=os.path.join('third_party', 'weights'))


@contextmanager
def use(root, blender=None):
    token = _workspace.set(str(Path(root).resolve()))
    blender_token = _blender.set(blender)
    try:
        yield
    finally:
        _workspace.reset(token)
        _blender.reset(blender_token)


def get(key):
    if key == 'blender':
        return _blender.get() or os.environ.get('HAIRDECK_NATIVE_BLENDER')
    if key == 'dinov3_repo':
        return str(_vendor / 'dinov3_hub')
    if key == 'sam3_repo':
        return str(_vendor)
    base = _workspace.get() or os.environ.get('HAIRDECK_NATIVE_ROOT')
    if not base:
        raise RuntimeError('HairDeck workspace is not configured for this execution.')
    return base if key == 'root' else os.path.join(base, _layout[key])


def root(*parts): return os.path.join(get('root'), *parts)
def data(*parts): return os.path.join(get('data'), *parts)
def ckpt(*parts): return os.path.join(get('ckpt'), *parts)
def weights(*parts): return os.path.join(get('weights'), *parts)
def results(*parts): return os.path.join(get('results'), *parts)
def logs(*parts): return os.path.join(get('logs'), *parts)
def scratch(*parts): return os.path.join(get('scratch'), *parts)
def sam3_repo(): return get('sam3_repo')
def dinov3_repo(): return get('dinov3_repo')


def resolve(path):
    return path if os.path.isabs(path) else root(path)
