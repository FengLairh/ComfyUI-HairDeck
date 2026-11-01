v0.2.0 将 HairDeck 工作流整合为三个节点：**模型加载 → 生成头发 → 输出保存**。

- 模型加载：统一选择模型包，由 ComfyUI 管理显存。
- 生成头发：直接在节点内上传图片，内部完成预处理、发片及可选的弹簧骨骼生成。
- 输出保存：集中导出 GLB / VRM / 动画、预览和过程图，结果保存在同一个文件夹；节点内提供下载链接和动画播放器。
- 三份中文示例模板都只有三个节点，完整示例的 PNG 也内嵌三节点工作流。
- 改种子复用图片预处理；改保存格式或颜色复用生成结果。
- 原生 Windows、ComfyUI 0.30.0、Python 3.12、PyTorch 2.8、RTX 5060 Ti 16GB 已实测生成完整结果：123 张发片、20 条骨骼链，VRM 结构检查通过；3 秒 H.264 动画已逐帧解码验证。
- 发布 ZIP 已在单独目录解压复测，首次完整运行约 38 秒；已有预处理缓存时约 30 秒。

**升级说明：** 本版替换旧的七节点接口，不再注册旧节点。更新后重启并刷新 ComfyUI，导入新版模板；旧工作流仍可使用 v0.1.1。已有模型和 v0.1.1 离线模型包无需重新下载。

推理在 ComfyUI Python/CUDA 进程中运行。首次安装仍需安装依赖并准备模型；代码 ZIP 不含模型权重和 Blender。Linux、8GB 配置及其他注意力后端尚未实机验证，浏览器视觉验收尚未完成。

### 下载内容

- `ComfyUI-HairDeck-0.2.0.zip`：插件源码、依赖清单、三节点模板和安装工具。
- `01_static_glb.json` / `02_spring_bones_vrm_motion.json` / `03_complete_example.json`：可直接导入 ComfyUI 的三节点工作流。
- `HairDeck-ThreeNode-Example-v0.2.0.zip`：本机实际生成的完整示例，包含输入图、工作流、GLB、VRM、动画及过程结果。

### 官方模型地址

- [HairDeck 官方模型与配套数据](https://huggingface.co/hyz317/HairDeck)：发片 VAE、图像发片生成、弹簧骨骼生成三个模型。
- [SAM 3 — facebook/sam3](https://huggingface.co/facebook/sam3)：使用 `sam3.pt`。
- [DINOv3 ViT-L/16](https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m)：使用 `model.safetensors`。
- [BiRefNet matting](https://huggingface.co/ZhengPeng7/BiRefNet-matting)：使用 `model.safetensors`。

六个权重合计约 6.4GB，另需 HairDeck 配套统计文件和角色数据。
具体文件、模型包用法、访问权限和安装方法见 [README](https://github.com/FengLairh/ComfyUI-HairDeck#official-models)。
第三方代码及模型保留各自许可，详见仓库的 THIRD_PARTY_NOTICES.md。
