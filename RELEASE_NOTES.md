v0.5.0 完成导出网格、UV 和基础发丝材质优化，仍保持三个节点和六个独立模型文件选择。

- 清理发束内部封口，补齐 UV 接缝、法线和切线；拆分顶点复制原有骨骼权重。
- 提供共享图集和独立 UV，支持 1K / 2K / 4K。
- 提供体积发束、透明发片、纯色诊断和 UV 检查预设。
- 输出发色/Alpha、法线、粗糙度、独立 Alpha、UV 布局和材质说明，并提供 glTF 金属粗糙度、Unity 金属光滑度两种打包图。
- GLB 与 VRM 嵌入相同核心贴图，静态和动画预览读取这些材质。修复预览中的 Alpha 裁剪及透明覆盖问题。
- 旧 v0.4 工作流可使用默认设置，刷新或导入新版模板可看到高级选项。

### 验证

- 10 项 CPU 导出检查和 GPU Alpha 模式检查通过。
- 本机新参考图完整流程约 40 秒完成；相同曲线的三角形从 29,356 减至 23,730，UV 零面积三角形从 5,896 降至 0。
- 原项目公开示例约 36 秒完成，独立 UV、GLB、VRM 和 90 帧动画均通过检查。
- 完整示例中的 PNG 可恢复三节点工作流，ZIP 内的模型、贴图及清单已检查齐全。

### 下载

- `ComfyUI-HairDeck-0.5.0.zip`：插件、安装工具、中英文说明和工作流模板。
- `HairDeck-UV-Material-Example-v0.5.0.zip`：使用上游公开输入和角色生成的完整示例，包含模型、贴图、动画和工作流。
- [完整资源与模型包（夸克网盘）](https://pan.quark.cn/s/cfe2401c29aa)。既有权重可以继续使用。
- [中文说明](https://github.com/FengLairh/ComfyUI-HairDeck#readme) · [English README](https://github.com/FengLairh/ComfyUI-HairDeck/blob/main/README.en.md) · [验证范围](https://github.com/FengLairh/ComfyUI-HairDeck/blob/main/VALIDATION.md)

材质贴图采用程序化生成并提取参考图基础发色。VRM 的 MToon 与 PBR 光照存在差异；目标 Unity/URP 工程中的材质、远距透明效果及性能仍需验收。头皮贴合和模型训练不属于本次改动。

代码包及公开示例不包含用户提供的私人图片、头模或游戏参考资源。
