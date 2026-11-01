v0.3.0 增加自定义基础头模支持，工作流仍为三个节点：模型加载 → 生成头发 → 输出保存。

- 使用 `scripts/import_head.py` 将自己的 FBX 转换为统一头部坐标系中的参考网格和头部 VRM 预设，保留网格及 UV，并绑定到基准角色头骨。
- 输出保存节点新增可选的“基础头模”：`auto` 使用本机默认，`upstream` 使用原始参考头模，也可选择已导入的预设。
- GLB、VRM 和动画使用同一份头模；切换输出设置可复用已有生成结果。查看 GLB 中的头模时，请开启“GLB 包含参考头模”。
- 中英文 README 已加入导入步骤；发布 ZIP 包含通用工具和三节点模板。

已在 Windows / ComfyUI 0.43.0 / RTX 3090 / xFormers 上实测：本地 FBX 导入、三节点完整生成、静态 GLB、VRM 和 90 帧动画均通过。完整流程约 32 秒；GLB 与导入网格、VRM 与头模预设的几何一致性检查通过。新增五项 CPU 路径与预设选择检查。

### 使用自己的头模

在 `ComfyUI` 目录使用其 Python 运行（需要已安装便携 Blender 和 VRM 插件）：

```bash
python custom_nodes/ComfyUI-HairDeck/scripts/import_head.py "path/to/MyHead.fbx" --models-dir models/hairdeck --name MyHead --make-default
```

刷新 ComfyUI 后，在输出节点选择 `auto` 或 `MyHead`。资源写入 `models/hairdeck/heads/MyHead/`。模型权重无需重新下载。

生成仍使用角色图片，头模用于输出装配和预览；导入采用统一缩放和平移，弹簧碰撞使用近似碰撞体。完整自定义角色装配尚未提供。

### 下载与文档

- 最新插件：本页附件 `ComfyUI-HairDeck-0.3.0.zip`，内含导入工具、中英文说明和三个工作流模板。
- [完整资源与模型包（夸克网盘）](https://pan.quark.cn/s/cfe2401c29aa)。
- [中文说明](https://github.com/FengLairh/ComfyUI-HairDeck#readme) · [English README](https://github.com/FengLairh/ComfyUI-HairDeck/blob/main/README.en.md) · [官方模型地址](https://github.com/FengLairh/ComfyUI-HairDeck#official-models) · [验证范围](https://github.com/FengLairh/ComfyUI-HairDeck/blob/main/VALIDATION.md)

用户 FBX 和转换资源按原资产许可使用，保存在各自的本地模型目录。插件代码包只包含通用接入代码，不包含用户模型、模型权重或 Blender。
