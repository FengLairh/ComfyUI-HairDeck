v0.5.1 调整体积发束的法线和高光，减弱圆柱、绳状观感。

- 发束沿长度方向平滑，截面各侧保留棱角。
- 减弱细节法线，提高体积发束及根梢封口的粗糙度。
- 生成曲线、表面位置、三角形数量和 UV 布局保持不变。硬边需要拆分顶点，拆分后的顶点继承原有骨骼权重。
- 保持三个节点和六个独立模型选择。现有工作流选择“体积发束”后重新输出即可使用新效果；代码更新后需重启 ComfyUI。

### 验证

- 12 项 CPU 导出检查通过，覆盖截面棱角、纵向平滑、UV、切线、骨骼权重复制和 GLB 材质。
- 同一份蓝发结果重新导出，103 束、42,650 个三角形保持不变；无零面积 UV 三角形。硬边拆分后顶点由 27,579 增至 43,752。
- 前后对照使用相同曲线、相机和渲染器。
- 本机蓝发和公开示例均通过完整三节点流程。前后生成特征完全一致；GLB、VRM 均保留硬边，核心贴图一致，VRM 检查及 90 帧动画解码通过。

### 下载

- `ComfyUI-HairDeck-0.5.1.zip`：插件、中英文说明和三节点工作流。
- `HairDeck-Creased-Strands-Example-v0.5.1.zip`：上游公开输入和角色生成的完整示例，包含 GLB、VRM、贴图、动画和可恢复的三节点工作流。
- [完整资源与模型包（夸克网盘）](https://pan.quark.cn/s/cfe2401c29aa)：模型权重保持兼容，无需重新下载。
- [中文说明](https://github.com/FengLairh/ComfyUI-HairDeck#readme) · [English README](https://github.com/FengLairh/ComfyUI-HairDeck/blob/main/README.en.md) · [验证范围](https://github.com/FengLairh/ComfyUI-HairDeck/blob/main/VALIDATION.md)

代码包不包含用户提供的私人图片、头模或游戏参考资源。Unity/URP 内的最终材质与性能仍需在目标工程验收。
