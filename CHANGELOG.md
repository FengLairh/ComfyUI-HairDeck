# Changelog

## 0.3.0

- Add local FBX head-profile import with canonical scale/position alignment and rigid head-bone binding.
- Select the base head in the output node; GLB, VRM and motion previews use the same profile, with a local default and an explicit upstream option.
- Keep the three-node interface and reuse generated hair when changing the head profile. Custom model assets remain outside the plugin source archive.

## 0.2.1

- Match torch SDPA autocast before ComfyUI attention dispatch, fixing FP32 Q/K with BF16 V in xFormers during hair generation.
- Add CUDA regression checks for the actual model's self/cross-attention, BF16/FP16 autocast, unbatched inputs, and explicit FP32 execution.

## 0.2.0

- Replace the seven public nodes with exactly three: model loader, generation, and output/save.
- Add image upload directly inside generation; preprocessing and optional spring bones run internally.
- Centralize GLB/VRM/video/debug outputs in one result directory with preview and download controls.
- Preserve preprocessing reuse across seed changes through a CPU-only temporary disk cache.
- Replace every current example with a three-node workflow. Old 0.1 workflows remain in the previous release.
- Keep compatibility with the existing v0.1.1 model bundle.

## 0.1.1

- Add a complete 22-node example covering every native HairDeck node and all media outputs.
- Embed editable workflow metadata in saved example PNGs.
- Add full-example file, VRM, UV, mask and video validation.
- Correct the native validation GPU to RTX 5060 Ti 16GB, verified from ComfyUI runtime information.

## 0.1.0

- Initial seven native ComfyUI nodes for preprocessing, hair-card generation, chains, GLB, VRM and motion preview.
- Portable model/tool installer, isolated dependency namespaces and Chinese example workflows.
