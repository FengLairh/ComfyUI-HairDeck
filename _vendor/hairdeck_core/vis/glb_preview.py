"""Render local HairDeck GLB front/side/back previews without loading neural models."""
import sys

import numpy as np
from PIL import Image, ImageDraw
from ..vrm.render import render, skinned_meshes


def main():
    output, source = sys.argv[1:]
    meshes, _ = skinned_meshes(source)
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
