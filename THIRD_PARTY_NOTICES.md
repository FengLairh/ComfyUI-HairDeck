# Third-party notices

The original adapter and HairDeck code use the Apache License 2.0 in `LICENSE`.
Vendored dependencies retain their own licenses, which take precedence for those files.
Model weights and Blender are downloaded separately and are not included in the release archive.

| Component | Upstream revision / version | License file |
|---|---|---|
| [HairDeck](https://github.com/hyz317/HairDeck) | `5f1c18a32e622cb8d1acec2a856694fb43375c1a` | `LICENSE` |
| [SAM 3](https://github.com/facebookresearch/sam3) | `0570b3a5be9c4e694f23d85232fb55f4a6f1f7fc` | `_vendor/hairdeck_sam3/LICENSE` |
| [DINOv3](https://github.com/facebookresearch/dinov3) | `6876159a11b4df116f30f667f8c9888617df0751` | `_vendor/hairdeck_dinov3/LICENSE.md` |
| [BiRefNet matting](https://huggingface.co/ZhengPeng7/BiRefNet-matting) | `eccde0a8cbdce7ac5fecfeb06340fe7b949e85d9` | `_vendor/hairdeck_birefnet/LICENSE` |
| [pyrender](https://github.com/mmatl/pyrender) | `0.1.45` | `_vendor/hairdeck_pyrender/LICENSE` |

The optional installer fetches Blender 4.2.23 LTS (GPL) and the VRM Add-on 4.10.2 (MIT).
Their license files remain in the downloaded tool archives/directories.

Local source adaptations: private package namespaces; per-execution workspace paths;
ComfyUI model ownership and attention dispatch; movable VAE normalization buffers;
removal of inference decorators because ComfyUI owns inference execution; standard-library
resource lookup; Windows/Linux one-shot Blender export and rendering.
The checkpoint formats and the original card/chain representations are retained.

Weights are fetched from the HairDeck release repository and the user-selectable public
ModelScope mirrors of SAM 3 / DINOv3. Each weight file is checked against the release SHA-256.
The SAM and DINO licenses included above also describe conditions applicable to those materials.
