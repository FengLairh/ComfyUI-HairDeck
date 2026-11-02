"""GPU preview regression: MASK discards pixels; OPAQUE ignores texture alpha."""
import os
from pathlib import Path
import sys

import numpy as np

if os.name != 'nt':
    os.environ.setdefault('PYOPENGL_PLATFORM', 'egl')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_vendor'))
import hairdeck_pyrender as pyrender


def quad(z, material):
    positions = np.array([[-.6, -.6, z], [.6, -.6, z], [.6, .6, z], [-.6, .6, z]], np.float32)
    normal = np.tile([0., 0., 1.], (4, 1)).astype(np.float32)
    uv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], np.float32)
    return pyrender.Mesh([pyrender.Primitive(positions=positions, normals=normal, texcoord_0=uv,
        indices=np.array([[0, 1, 2], [0, 2, 3]]), material=material)])


def main():
    texture = np.zeros((16, 16, 4), np.uint8)
    texture[..., 2] = 255
    texture[:, 8:, 3] = 255
    renderer = pyrender.OffscreenRenderer(128, 128)
    try:
        for mode in ('MASK', 'OPAQUE', 'BLEND'):
            scene = pyrender.Scene(bg_color=[0., 0., 0., 0.], ambient_light=[1., 1., 1.])
            camera_pose = np.eye(4)
            camera_pose[2, 3] = 2
            scene.add(pyrender.OrthographicCamera(xmag=.8, ymag=.8), pose=camera_pose)
            scene.add(quad(0, pyrender.MetallicRoughnessMaterial(baseColorFactor=[1., 0., 0., 1.], metallicFactor=0., roughnessFactor=1.)))
            source = texture.copy()
            if mode == 'BLEND':
                source[..., 3] = 128
            scene.add(quad(.1, pyrender.MetallicRoughnessMaterial(baseColorFactor=[1., 1., 1., 1.], baseColorTexture=source,
                alphaMode=mode, alphaCutoff=.5, metallicFactor=0., roughnessFactor=1.)))
            pixels, _ = renderer.render(scene, flags=pyrender.RenderFlags.RGBA)
            left, right = pixels[64, 40], pixels[64, 88]
            if mode == 'MASK':
                assert left[0] > 200 and left[2] < 20, ('MASK failed to reveal the background', left)
            elif mode == 'OPAQUE':
                assert left[2] > 200 and left[0] < 20 and left[3] == 255, ('OPAQUE incorrectly used texture alpha', left)
            else:
                assert 120 < left[0] < 140 and 120 < left[2] < 140 and left[3] == 255, ('BLEND coverage is incorrect', left)
            if mode != 'BLEND':
                assert right[2] > 200 and right[3] == 255
        print('PREVIEW_ALPHA_MODES_PASSED', flush=True)
    finally:
        renderer.delete()


if __name__ == '__main__':
    main()
