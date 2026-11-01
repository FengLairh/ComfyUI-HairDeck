"""Local head profiles, separate from checkpoints and published plugin assets."""
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class HeadProfile:
    name: str
    mesh: Path
    body: Path


def profile_directory(root, name):
    base = (Path(root) / 'heads').resolve()
    candidate = (base / name).resolve()
    if not name or '/' in name or '\\' in name or name in ('auto', 'upstream', '.', '..') or candidate.parent != base:
        raise ValueError('头模名称必须是 heads 目录内的单个文件夹名称。')
    return candidate


def choices(roots):
    names = set()
    for root in roots:
        base = Path(root) / 'heads'
        if base.is_dir():
            names.update(path.name for path in base.iterdir() if path.is_dir() and (path / 'profile.json').is_file())
    return ['auto', 'upstream', *sorted(names)]


def resolve(root, name='auto'):
    root = Path(root).resolve()
    if name == 'auto':
        active = root / 'heads/active.json'
        name = json.loads(active.read_text(encoding='utf-8'))['name'] if active.is_file() else 'upstream'
    if name == 'upstream':
        return None
    directory = profile_directory(root, name)
    manifest = json.loads((directory / 'profile.json').read_text(encoding='utf-8'))

    def asset(value, suffix):
        path = (directory / value).resolve()
        if not path.is_relative_to(directory) or path.suffix.lower() != suffix or not path.is_file():
            raise ValueError('头模资源路径无效或超出当前头模目录。')
        return path

    mesh, body = asset(manifest['mesh'], '.glb'), asset(manifest['body'], '.json')
    body_data = json.loads(body.read_text(encoding='utf-8'))
    for key, suffix in [('vrm', '.vrm'), ('head_mesh', '.glb')]:
        path = (root / body_data[key]).resolve()
        if not path.is_relative_to(directory) or path.suffix.lower() != suffix or not path.is_file():
            raise ValueError('头模 VRM 配置中的资源路径无效。')
        if key == 'head_mesh' and path != mesh:
            raise ValueError('GLB 与动画必须使用同一份基础头模。')
    return HeadProfile(name, mesh, body)
