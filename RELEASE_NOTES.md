v0.4.0 将 AI 模型加载改为 ComfyUI 常见的独立文件下拉框，工作流仍为三个节点。

“模型加载”节点分别列出：

1. 发片生成模型
2. 发片 VAE
3. 弹簧骨骼模型
4. SAM 3 分割模型
5. DINOv3 图像编码器
6. BiRefNet 抠图模型

每项显示实际文件名，并真正加载所选文件。支持独立模型目录、重命名权重和 `extra_model_paths.yaml` 配置。配套统计文件、标准头框、角色及自定义头模的目录放在高级选项“配套资源目录”中。

**升级说明：** 原来的 `bundle: auto` 加载输入已替换。更新插件并重启、刷新 ComfyUI 后，请导入新版三节点模板，或重新添加“模型加载”节点并选择文件。已有模型和头模资源可继续使用，无需重新下载权重。

### 验证

- 八项模型选择检查通过，覆盖六项文件解析、重命名、外部目录、路径限制、缓存失效及实际加载参数传递。
- 已在 ComfyUI 0.43.0、RTX 3090、xFormers 上完成完整流程，约 32 秒生成 GLB、VRM 和 3 秒动画。
- 同一输入的采样数据与 v0.3.0 参考结果完全一致，已有自定义头模正常使用。
- 三份 GUI/API 模板及五张内嵌工作流的 PNG 均确认包含明确的模型文件选择。

### 下载与文档

- 最新插件：本页附件 `ComfyUI-HairDeck-0.4.0.zip`，内含中英文说明、安装工具及新版三节点模板。
- [完整资源与模型包（夸克网盘）](https://pan.quark.cn/s/cfe2401c29aa)。
- [中文说明](https://github.com/FengLairh/ComfyUI-HairDeck#readme) · [English README](https://github.com/FengLairh/ComfyUI-HairDeck/blob/main/README.en.md) · [官方模型地址](https://github.com/FengLairh/ComfyUI-HairDeck#official-models) · [验证范围](https://github.com/FengLairh/ComfyUI-HairDeck/blob/main/VALIDATION.md)

插件包不含模型权重、用户 FBX、转换后的私有头模或 Blender。
