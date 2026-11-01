原生 ComfyUI-HairDeck 首次公开发布，版本 v0.1.1。

- 提供 7 个原生 V3 节点：模型加载、预处理、发片、弹簧骨骼、GLB、VRM 和动画预览。
- 提供 3 份中文工作流，包括覆盖全部输出的 22 节点完整示例。
- 推理运行在 ComfyUI Python/CUDA 进程中，无需 HairDeck 网页或 WSL 后端。
- 安装脚本按固定版本和 SHA-256 下载模型及可选的便携 Blender；发布包不含模型或 Blender 二进制。
- 已在 Windows、ComfyUI 0.30.0、Python 3.12、PyTorch 2.8、RTX 5060 Ti 16GB 上跑通完整流程，并完成 ZIP 解压复测。
- 完整示例生成 123 张发片、20 条骨骼链，VRM 结构检查通过；两份 3 秒 H.264 动画均已逐帧解码验证。

安装请参阅 README。首次使用需单独安装依赖和下载模型。
Linux、8GB 配置和其他注意力后端尚未实机验证。第三方代码及模型保留各自许可，详见 THIRD_PARTY_NOTICES.md。
