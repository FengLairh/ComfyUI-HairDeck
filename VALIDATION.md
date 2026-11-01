# Validation — 0.1.1

Test environment: Windows x64, ComfyUI 0.30.0, Python 3.12.10, PyTorch 2.8.0+cu129,
torchvision 0.23.0+cu129, NVIDIA RTX 5060 Ti (16GB).
Device identity was verified from ComfyUI `/system_stats` and process startup logs;
the earlier RTX 3090 label was based on the launch argument and has been corrected.
The Windows environment includes triton-windows 3.4.0.post21; compilation is disabled for SAM 3.

Completed with real checkpoints and the upstream ex01 image:

- All seven native V3 nodes register through `comfy_entrypoint`.
- Static workflow: preprocessing → hair cards → GLB → standard Preview3D; successful, about 17 seconds including initial model load.
- Full workflow: hair cards → chains → GLB, VRM, 3-second H.264 motion preview; successful, about 39 seconds.
- The old HairDeck web backend was stopped during the full workflow. No WSL or web inference module is used by the node implementation.
- 123 hair cards and 20 generated chains; VRM export produced 19 spring groups and passed the upstream structural checks.
- Model groups are registered as ComfyUI ModelPatcher objects and loaded with `load_models_gpu`.
- The release ZIP was extracted into a separate ComfyUI base directory. Its packaged modules ran the complete workflow again in about 38 seconds, using only a configured model directory.
- Input alpha, single-image limits, hair/rig matching, workspace isolation and output path containment are covered by contract checks.
- Repeated-seed execution reused nodes 1–4 (image, loader, preprocessing, generation); changing the seed reused nodes 1–3 and reran generation as intended.
- Complete local example: 22 workflow nodes, including all seven HairDeck node types; three GLBs, VRM, normal and bone-line animations, crop, masks and previews were generated in about 54 seconds on the RTX 5060 Ti 16GB.
- Each of the five SaveImage PNGs contains the complete workflow and API prompt. Both H.264 videos were decoded frame by frame: 90 frames, 480×480, 3 seconds.
- This complete example generated 123 hair cards and 20 chains; its VRM contained 17 spring groups and passed the structural checks. The earlier validation fixture produced 19 groups; counts can differ after filtering and numerical/backend differences.

Not yet assessed: other GPUs, 8GB configurations, Linux native ComfyUI, arbitrary custom avatar fitting,
all optional attention backends, and browser visual acceptance. The in-app browser tool was unavailable in this session.

Source and versioned ZIP distribution: https://github.com/FengLairh/ComfyUI-HairDeck
ComfyRegistry registration is separate and has not been performed.
