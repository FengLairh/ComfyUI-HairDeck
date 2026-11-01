"""Render local HairDeck GLB front/side/back previews without loading neural models."""
import sys

import numpy as np
from PIL import Image, ImageDraw
import trimesh

from ..infer.glb import srgb_to_linear
from ..vrm.render import render


def main():
    output, source, rgb = sys.argv[1:]
    color = [float(value) for value in rgb.split(',')]
    scene = trimesh.load(source, force='scene')
    meshes = []
    for name, mesh in scene.geometry.items():
        selected = [.65, .65, .67] if 'head' in name.lower() else [1., .45, .04] if 'chain' in name.lower() else color
        meshes.append(dict(name='Hair_gen', V=mesh.vertices, F=mesh.faces, colour=srgb_to_linear(selected)))
    vertices = np.concatenate([mesh['V'] for mesh in meshes])
    low, high = vertices.min(0), vertices.max(0)
    target = (low + high) / 2
    half = max(.05, float((high - low).max()) * .6)
    sheet = Image.new('RGB', (1080, 384), 'white')
    labels = ImageDraw.Draw(sheet)
    for index, (title, direction) in enumerate([('front', (0, 0, 1)), ('side', (1, 0, 0)), ('back', (0, 0, -1))]):
        sheet.paste(render(meshes, target, direction, half), (index * 360, 24))
        labels.text((index * 360 + 8, 6), title, fill='black')
    sheet.save(output)


if __name__ == '__main__':
    main()
