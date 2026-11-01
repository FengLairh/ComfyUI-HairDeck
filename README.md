# ComfyUI-HairDeck

原生 ComfyUI 节点：从单张角色图片生成风格化发片、弹簧骨骼，导出 GLB / VRM，并预览头发运动。

**推理直接运行在 ComfyUI 的 Python/CUDA 进程中。无需 HairDeck 网页、WSL、HTTP 推理服务或本机固定路径。**
VRM 导出使用安装脚本准备的便携版 Blender；动画与图片预览使用随插件提供的渲染代码。

![原生 ComfyUI 生成的角色多视图](docs/images/example.png)

[下载发布包](https://github.com/FengLairh/ComfyUI-HairDeck/releases/latest) ·
[完整示例工作流](example_workflows/03_完整示例_全流程.json) · [验证范围](VALIDATION.md)

## 安装

1. 下载发布包并将其中的 `ComfyUI-HairDeck` 文件夹放到 `ComfyUI/custom_nodes/`，或在该目录执行：

```bash
git clone https://github.com/FengLairh/ComfyUI-HairDeck.git
```

2. 使用 **ComfyUI 自己的 Python** 安装依赖；保留 ComfyUI 已有的 CUDA PyTorch/torchvision：

```bash
python -m pip install -r custom_nodes/ComfyUI-HairDeck/requirements.txt
```

Windows 便携版通常需要将 `python` 替换成自己的 `python_embeded/python.exe` 或启动器附带的 Python 路径。
以下命令的工作目录为 `ComfyUI`：

```bash
python custom_nodes/ComfyUI-HairDeck/install_models.py --models-dir models/hairdeck --with-blender
```

例如，官方 Windows 便携版可在包含 `python_embeded` 和 `ComfyUI` 的上级目录运行：

```powershell
.\python_embeded\python.exe -m pip install -r .\ComfyUI\custom_nodes\ComfyUI-HairDeck\requirements.txt
.\python_embeded\python.exe .\ComfyUI\custom_nodes\ComfyUI-HairDeck\install_models.py --models-dir .\ComfyUI\models\hairdeck --with-blender
```

下载按固定版本和 SHA-256 校验，支持分段续传。下载只在明确运行安装脚本时发生；导入节点和执行工作流不会自动下载。
只使用静态 GLB 时可省略 `--with-blender`。

已有兼容模型包可通过 `extra_model_paths.yaml.example` 配置，无需重复复制模型。
完整模型目录约需数 GB，便携 Blender 另需磁盘空间。

```text
ComfyUI/models/hairdeck/
├── ckpt/{card_vae,image_model,chain_model}/
├── data/{avatar,spring}/ ...
├── third_party/weights/{sam3,dinov3,birefnet_matting}/
└── tools/blender/               # VRM 导出用便携 Blender 与插件
```

安装完成后重启 ComfyUI，在菜单 **HairDeck / 发片生成** 中找到节点。

## 七个节点

| 节点 | 输入与用途 |
|---|---|
| 加载模型 | 选择模型包；权重交由 ComfyUI ModelPatcher 管理 |
| 图像预处理 | 角色图、可选透明区域 MASK；输出裁剪图、头发/面部蒙版和诊断预览 |
| 发片生成 | 模型、预处理数据、种子、步数、引导强度 |
| 弹簧骨骼生成 | 模型、发片数据、骨骼种子/采样设置 |
| 导出 GLB | 保存纯头发或带参考头模的模型，输出标准 `FILE_3D_GLB` |
| 导出 VRM | 装配到示例角色，输出带蒙皮和弹簧骨骼的 VRM 与正侧背面预览 |
| 动画预览 | 输出 3 秒转头动画，使用标准 `VIDEO` 输出和 ComfyUI 播放器 |

GLB 输出可以直接连接 ComfyUI 自带 **Preview3D**。骨骼数据连到 GLB 导出时生成的是骨骼线可视化；
可动画化的蒙皮和 VRM 弹簧骨骼由 VRM 节点导出。当前 VRM 节点使用上游示例角色，尚未提供任意自定义角色装配。

预处理的“透明区域蒙版”可以连接 LoadImage 的 MASK，1 表示透明；输出的“头发蒙版”则是 1 表示头发。
每次处理一张图片。多次生成可使用 ComfyUI 队列和种子递增。

## 示例工作流

把 `example_workflows/01_静态发片_GLB.json` 或 `02_弹簧骨骼_VRM_动画.json` 拖进 ComfyUI。
先在“加载图片”节点上传自己的角色图，再点击运行。

`03_完整示例_全流程.json` 将所有输出放在同一工作流中：三种 GLB、VRM、普通/骨骼线动画、
模型输入图、头发/面部蒙版和角色多视图。它包含全部七种 HairDeck 节点，配合 ComfyUI 内置节点共 22 个节点。
通过 `scripts/generate_full_example.py` 提交该示例时，保存的 PNG 会内嵌工作流，可拖进 ComfyUI 恢复。

建议用头部清晰、完整发型可见的图片。先使用单个方案和 50 步确认结果，再调整种子、颜色和骨骼参数。
换种子会复用预处理结果；改导出颜色/头模选项会复用已有发片。骨骼和发片必须来自同一方案，节点会检查关联关系。

结果保存到 ComfyUI 的 `output/HairDeck/`，临时导出数据在 ComfyUI 的 `temp/hairdeck/`。
输出节点每次运行会保存一份新文件，不覆盖旧结果。取消任务会在当前处理阶段结束后生效。

## 环境与验证范围

- ComfyUI **0.30.0 或更新版本**，Python 3.12+，PyTorch 2.8+ 的 CUDA 构建。
- 需要支持 BF16 的 NVIDIA CUDA 显卡，16GB 已实测跑通；12GB 仅作为配置参考，尚未实机验证，8GB 未验证。
- 原生 Windows 已通过实际工作流验证：Python 3.12.10、PyTorch 2.8.0+cu129、RTX 5060 Ti 16GB。
- Linux x86-64 路径和工具安装已实现，尚未完成 Linux 原生 ComfyUI 真机验证。
- 其他注意力后端、其他显卡和 Python 版本尚未逐一验证；以 `VALIDATION.md` 为准。

SAM 3 源码包含 Triton 模块导入；Windows 依赖由 `triton-windows` 提供，Linux 使用 `triton`。
本次验证的是 triton-windows 3.4.0.post21 与 PyTorch 2.8。节点不启用 SAM 3 的 torch.compile。

## 发布与许可

`pyproject.toml`、依赖文件、示例工作流与第三方许可均随源码提供。发布包不含模型、Blender 二进制、
本地配置、日志或访问令牌。登记 ComfyRegistry 前需填写自己的 `PublisherId` 和仓库 URL；这些身份信息不会预设为上游作者。

算法与模型来自 [HairDeck](https://github.com/hyz317/HairDeck)。原始代码与本适配器采用 Apache-2.0；
SAM 3、DINOv3、BiRefNet、pyrender 等材料保留各自许可，详见 [第三方声明](THIRD_PARTY_NOTICES.md)。
