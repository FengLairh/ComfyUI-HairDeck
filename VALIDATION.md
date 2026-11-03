# Validation — 0.5.1

## v0.5.1: strand shading

- Twelve CPU export tests pass. New regressions cover distinct normals at cross-section creases, matching normals across a side's width, longitudinal smoothing, retained original positions and restrained volume highlights. Exported GLB normals match the surface data.
- Re-exporting the same 103-card blue reference preserves every original vertex position and all 42,650 triangles. Crease splits increase the vertex count from 27,579 to 43,752. Float32 UVs have no zero-area triangles; normals and tangents remain finite, unit-length and orthogonal.
- Before/after GLB views use the same source cards, camera and renderer; no inference or shape parameters are changed in this comparison.
- Both references passed the full installed ComfyUI 0.43.0 / PyTorch 2.9.1+cu130 / RTX 3090 workflow. The blue reference completed in 52.17 seconds with 103 cards and 18 generated chains; the public example completed in 38.11 seconds with 124 cards and 19 chains. Their generated tokens exactly match the previous outputs. Blue-reference card and chain files are byte-identical.
- Exported GLB and VRM retain the creases, finite unit normals/tangents and orthogonal frames; embedded core texture pixels match between formats. Both VRMs passed structural validation, both animations decode to 90 frames / 3 seconds, and all five PNGs retain a three-node workflow. The public example uses shared UVs and 33,884 triangles.

## v0.5.0: export surfaces and appearance

- Ten CPU export tests pass: boundary-only caps, retained source positions, float32 UV validity, atlas padding/non-overlap, normals/tangent frames including rounded-normal input, original skin-weight copying, flat/empty cards, embedded texture pixels and Unity packing.
- A GPU preview test reproduced and fixed missing alpha-mask behavior; OPAQUE, MASK and BLEND now pass an overlapping-quad visibility/coverage check. Preview images use the file's UVs, normals, tangents and textures rather than recoloring meshes.
- Both shared volume and unique ribbon offline exports passed VRM structural checks and 90-frame animation decoding. UV-split vertices matched the original geometric binding exactly; GLB/VRM core texture pixels matched byte for byte.
- The new local silver-haired reference completed the full three-node workflow on ComfyUI 0.43.0 / PyTorch 2.9.1+cu130 / RTX 3090 / xFormers in 40.16 seconds: 88 cards, 9 generated chains, 9 spring groups. From the same generated curves, triangle count fell from 29,356 to 23,730, and zero-area UV triangles from 5,896 to 0. The final surface has 15,659 vertices because UV/normal seams require splits.
- The public upstream example completed in 36.17 seconds with unique UVs: 124 cards, 19 chains and 18 spring groups. Triangles fell from 42,010 to 33,884, with zero-area UV triangles reduced from 8,546 to 0.
- Final GLB and VRM files were checked for finite unit normals/tangents, orthogonality, non-degenerate UVs, embedded matching textures and valid VRM skin/bone data. Seven 2K PNG maps/diagnostics were checked, including glTF G-roughness/B-metallic and Unity R-metallic/A-smoothness packing. Five PNG previews retain the three-node workflow, and videos decode to 90 frames over 3 seconds.
- Old v0.4 save inputs ran with the new optional defaults in an isolated native instance. Ribbon and UV-check presets also ran through the actual ComfyUI queue.
- The supplied game asset was analyzed locally to inform restrained detail and future geometry/Toon work; its meshes, textures and shader sources are not distributed with this plugin. Private head/image examples stay local. Public examples use the upstream input and avatar.
- Preview uses a PBR renderer. VRM's MToon lighting differs; roughness is retained in the PBR fallback and standalone maps. Unity/URP appearance, mip-distance behavior and device performance are not yet validated in the target game project. Scalp fitting, candidate selection and model training remain later work.

## v0.4.0: explicit model files

- The loader exposes six independent checkpoint dropdowns using ComfyUI's model-folder registry, plus an advanced companion-resource directory. The former `bundle: auto` input is removed; workflows must use the updated loader inputs.
- Eight contract checks pass in ComfyUI's Python without loading checkpoints: six independent fields, renamed files for all six roles, external model directories, unregistered/path-traversal rejection, weight/statistics fingerprint invalidation, node selection forwarding, model-constructor forwarding, and explicit VAE checkpoint loading.
- The complete three-node workflow passed on ComfyUI 0.43.0 / RTX 3090 / xFormers in 32.11 seconds using the six explicit installed files and the existing local head profile. It produced 152 cards, 3 chains, validated GLB/VRM outputs and a 90-frame, 3-second animation.
- The explicit loader and static GLB workflow also passed on ComfyUI 0.30.0 / PyTorch 2.8.0+cu129 / RTX 5060 Ti 16GB with PyTorch attention.
- The model input pixels matched the v0.3.0 reference run; generated token arrays matched exactly (maximum absolute difference 0). The selected custom head remained present with 3,982 vertices.
- All five saved PNGs embed a three-node workflow whose loader contains seven concrete widget values (six model filenames plus the resource directory), with no automatic model-bundle value. All three shipped GUI/API templates passed serialization checks against the running ComfyUI contracts.

## v0.3.0: local custom heads

- Imported a local static FBX with 3,982 vertices, 7,528 triangles and UVs into a canonical gray head GLB and a head-only VRM profile. The original FBX SHA-256 remained unchanged.
- Verified explicit profile selection and the local `auto` default in native ComfyUI 0.43.0 on the RTX 3090 / xFormers environment below. Exactly three HairDeck nodes remain registered; the new output input is optional and defaults to `auto`.
- The full three-node workflow completed in 32.12 seconds, exporting GLB, VRM and a 90-frame animation. Static GLB export also passed. All five preview/debug PNGs embed a three-node workflow.
- Both output GLBs contain the selected 3,982-vertex head with a maximum nearest-vertex error below 1e-7 against the canonical profile mesh. VRM preserved the profile's head geometry within 1.4e-8 and passed the upstream structural checks. The selected mesh is also used in the motion preview; generated previews were visually inspected.
- Changing output format and switching from explicit selection to the local `auto` default reused the cached loader and generation nodes.
- Five CPU tests cover default/explicit head selection, profile-name containment, mesh/VRM path containment, and GLB/motion mesh consistency. GUI templates were regenerated for the optional profile input.
- Alignment is a uniform scale/translation to the training head frame. Spring collisions use approximate colliders; this is head-only output assembly, not complete custom-avatar fitting or mesh-conditioned generation. Custom source/converted assets stay in the local model directory and are excluded from the plugin archive.

## v0.2.1: attention autocast

- Reproduced the exact xFormers error with FP32 query/key and BF16 value, both in a minimal adapter call and in the real model's self/cross-attention blocks.
- The model's Q/K RMSNorm uses FP32 weights, promoting its result to FP32. The adapter now applies the active torch autocast dtype before calling ComfyUI's selected attention backend, matching the original torch SDPA behavior.
- Four CUDA regression tests pass, covering BF16/FP16 self/cross-attention against torch SDPA, all-FP32 inputs under autocast, unbatched mixed inputs, and explicit FP32 execution with autocast disabled.
- Regression environments: RTX 3090 24GB, PyTorch 2.9.1+cu130, xFormers 0.0.33.post2, ComfyUI 0.43.0; and RTX 5060 Ti 16GB, PyTorch 2.8.0+cu129, PyTorch attention, ComfyUI 0.30.0. These GPU checks ran locally with each ComfyUI installation's Python.
- Replayed the previously failing complete local workflow in the original ComfyUI 0.43.0 instance, keeping xFormers enabled: successful in 46.16 seconds, with 152 hair cards, 3 generated chains, and 3 VRM spring groups.
- Output checks passed: GLB with 14,120 vertices and finite positions/UVs, upstream VRM structural validation, five PNGs with embedded workflow metadata, and H.264 video decoded as 90 frames at 480×480 over 3 seconds.

## v0.2.0 baseline

Test environment: Windows x64, ComfyUI 0.30.0, Python 3.12.10, PyTorch 2.8.0+cu129,
torchvision 0.23.0+cu129, NVIDIA RTX 5060 Ti (16GB).
Device identity was verified from ComfyUI `/system_stats` and process startup logs.
The Windows environment includes triton-windows 3.4.0.post21; compilation is disabled for SAM 3.

Completed with real checkpoints and the upstream ex01 image:

- Exactly three native V3 nodes register through `comfy_entrypoint`: `HairDeckLoader`, `HairDeckGenerate`, `HairDeckSave`. The former standalone preprocessing, bone and export nodes are no longer registered.
- All three GUI templates and their API counterparts contain exactly three nodes and two connections. GUI widget serialization was checked against the running ComfyUI contracts.
- The generation node exposes ComfyUI's standard image-upload control. File contents are included in its fingerprint so replacing a file under the same name invalidates generation.
- Static three-node workflow: successful GLB export and locally rendered front/side/back preview, about 15 seconds including initial model load.
- Complete three-node workflow: GLB, VRM, a 3-second H.264 animation, previews, masks and curve data, about 30 seconds with preprocessing cached.
- The release ZIP was extracted into a separate ComfyUI base directory, with only a model-directory junction and the input image configured. Its packaged three-node workflow ran successfully in 38.11 seconds, including initial model load and preprocessing; the same GLB/VRM/PNG/video checks passed.
- The complete example generated 123 hair cards and 20 chains. Its GLB contained 17,152 vertices with finite positions and UVs. Its VRM contained 17 spring groups and passed the upstream structural checks.
- Each of the five saved preview/debug PNGs contains the exact three-node GUI workflow and API prompt. The H.264 video was decoded frame by frame: 90 frames, 480×480, 3 seconds.
- Repeated-seed execution reused nodes 1–2 (loader and generation); changing the seed reused node 1 and reran generation with the temporary CPU preprocessing cache. Output/save ran on each submission and used a new result folder.
- Contract checks cover input alpha, single-image limits, matching hair/rig data, workspace isolation, output containment, missing-bone export errors, preprocessing cache reuse/invalidation and recovery from a corrupt cache.
- The local preview extension is served by ComfyUI; JavaScript syntax checks pass. Browser interaction and visual acceptance have not been assessed.
- The old HairDeck web backend was stopped during validation. Inference runs in ComfyUI Python/CUDA, without WSL or an HTTP inference backend.
- Model groups are registered as ComfyUI ModelPatcher objects and loaded with `load_models_gpu`. The preprocessing disk cache contains CPU image data, not persistent GPU features.
- Offline model-bundle manifest containment, official-hash rejection and ZIP corruption handling tests pass. Existing v0.1.1 model/tool bundles remain compatible.

Not yet assessed: GPUs other than the RTX 5060 Ti and RTX 3090, 8GB configurations, Linux native ComfyUI, arbitrary custom avatar fitting,
all optional attention backends, and browser visual acceptance. The in-app browser tool was unavailable in this session.

v0.2 replaces the v0.1 seven-node interface. Import the new templates; previous workflows remain available in the v0.1.1 release.

Source and versioned ZIP distribution: https://github.com/FengLairh/ComfyUI-HairDeck
ComfyRegistry registration is separate and has not been performed.
