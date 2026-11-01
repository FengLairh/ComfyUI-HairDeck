v0.2.1 修复启用 xFormers 时生成头发失败的精度报错：`query/key: float32, value: bfloat16`。

模型的 Q/K 归一化会产生 FP32；此前的适配层没有执行原始 PyTorch SDPA 的自动精度转换。本版在调用 ComfyUI 注意力后端前按当前 autocast 精度统一 Q/K/V，继续使用所选后端。

- 新增 BF16 / FP16、自注意力 / 交叉注意力、三维输入及关闭 autocast 时的 FP32 回归检查。
- 已在发生报错的原始环境复测：ComfyUI 0.43.0、PyTorch 2.9.1+cu130、xFormers 0.0.33.post2、RTX 3090 24GB。
- 原完整工作流约 46 秒执行成功，生成 152 张发片和 3 条骨骼链；GLB、VRM、五张内嵌工作流的 PNG 及 3 秒 H.264 动画均通过文件检查。
- 同时通过 ComfyUI 0.30.0、PyTorch 2.8.0+cu129、RTX 5060 Ti 16GB 的 PyTorch 注意力回归检查。

**更新方法：** 安装本页附件 `ComfyUI-HairDeck-0.2.1.zip`，或在插件目录执行 `git pull`，然后重启 ComfyUI。已有三节点工作流可继续使用，模型无需重新下载。

### 下载与文档

- 最新插件修复包：本页附件 `ComfyUI-HairDeck-0.2.1.zip`，包含中英文 README 和三节点模板。
- [完整资源与模型包（夸克网盘）](https://pan.quark.cn/s/cfe2401c29aa)。模型与工具的安装位置见 [README](https://github.com/FengLairh/ComfyUI-HairDeck#离线模型整合包)。
- [完整三节点示例下载](https://github.com/FengLairh/ComfyUI-HairDeck/releases/download/v0.2.0/HairDeck-ThreeNode-Example-v0.2.0.zip)：可在 v0.2.1 中继续使用。
- [中文说明](https://github.com/FengLairh/ComfyUI-HairDeck#readme) · [English README](https://github.com/FengLairh/ComfyUI-HairDeck/blob/main/README.en.md) · [官方模型地址](https://github.com/FengLairh/ComfyUI-HairDeck#official-models) · [验证范围](https://github.com/FengLairh/ComfyUI-HairDeck/blob/main/VALIDATION.md)

代码 ZIP 不含模型权重和 Blender。第三方代码及模型保留各自许可，详见 THIRD_PARTY_NOTICES.md。
