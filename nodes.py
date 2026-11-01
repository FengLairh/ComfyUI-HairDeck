from pathlib import Path

from comfy_api.latest import ComfyExtension, io, ui, InputImpl, Types

from . import runtime
from . import exporting

MODEL = io.Custom('HAIRDECK_MODEL')
PREPARED = io.Custom('HAIRDECK_PREPARED')
HAIR = io.Custom('HAIRDECK_HAIR')
RIG = io.Custom('HAIRDECK_RIG')
CATEGORY = 'HairDeck / 发片生成'


class HairDeckLoader(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id='HairDeckLoader', display_name='HairDeck 加载模型', category=CATEGORY,
                         description='原生运行于 ComfyUI；模型由 ComfyUI 管理，无需网页、WSL 或外部推理服务。',
                         inputs=[io.Combo.Input('bundle', display_name='模型包', options=['auto', *runtime.bundles()], default='auto')],
                         outputs=[MODEL.Output(display_name='模型')])

    @classmethod
    def execute(cls, bundle):
        return io.NodeOutput(runtime.ModelBundle(runtime.resolve_bundle(bundle)))

    @classmethod
    def fingerprint_inputs(cls, bundle):
        return runtime.signature(runtime.resolve_bundle(bundle))


class HairDeckPreprocess(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id='HairDeckPreprocess', display_name='HairDeck 图像预处理', category=CATEGORY,
                         inputs=[MODEL.Input('model', display_name='模型'), io.Image.Input('image', display_name='角色图片'),
                                 io.Mask.Input('transparent_mask', display_name='透明区域蒙版', optional=True,
                                               tooltip='可连接“加载图片”的 MASK；1 表示透明，0 表示保留。不是头发分割蒙版。')],
                         outputs=[PREPARED.Output(display_name='预处理数据'), io.Image.Output(display_name='裁剪图'),
                                  io.Mask.Output(display_name='头发蒙版'), io.Mask.Output(display_name='面部蒙版'),
                                  io.Image.Output(display_name='处理预览')])

    @classmethod
    def execute(cls, model, image, transparent_mask=None):
        prepared, crop, hair_mask, face_mask, preview = runtime.preprocess(model, image, transparent_mask)
        return io.NodeOutput(prepared, crop, hair_mask, face_mask, preview, ui=ui.PreviewImage(preview, cls=cls))


class HairDeckGenerate(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id='HairDeckGenerate', display_name='HairDeck 发片生成', category=CATEGORY,
                         inputs=[MODEL.Input('model', display_name='模型'), PREPARED.Input('prepared', display_name='预处理数据'),
                                 io.Int.Input('seed', display_name='随机种子', default=0, min=0, max=2**64 - 1,
                                              control_after_generate=True),
                                 io.Int.Input('steps', display_name='采样步数', default=50, min=1, max=200),
                                 io.Float.Input('cfg', display_name='引导强度', default=2.0, min=1.0, max=4.0, step=.25)],
                         outputs=[HAIR.Output(display_name='发片数据')])

    @classmethod
    def execute(cls, model, prepared, seed, steps, cfg):
        return io.NodeOutput(runtime.generate(model, prepared, seed, steps, cfg))


class HairDeckSpringBones(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id='HairDeckSpringBones', display_name='HairDeck 弹簧骨骼生成', category=CATEGORY,
                         inputs=[MODEL.Input('model', display_name='模型'), HAIR.Input('hair', display_name='发片数据'),
                                 io.Int.Input('seed', display_name='骨骼随机种子', default=0, min=0, max=2**64 - 1),
                                 io.Int.Input('steps', display_name='骨骼采样步数', default=50, min=1, max=200),
                                 io.Float.Input('cfg', display_name='骨骼引导强度', default=2.0, min=1.0, max=4.0, step=.25)],
                         outputs=[RIG.Output(display_name='骨骼数据')])

    @classmethod
    def execute(cls, model, hair, seed, steps, cfg):
        return io.NodeOutput(runtime.generate_rig(model, hair, seed, steps, cfg))


class HairDeckExportGLB(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id='HairDeckExportGLB', display_name='HairDeck 导出 GLB', category=CATEGORY,
                         is_output_node=True,
                         inputs=[HAIR.Input('hair', display_name='发片数据'),
                                 io.Boolean.Input('show_head', display_name='包含参考头模', default=False),
                                 io.String.Input('color', display_name='发色', default='auto', tooltip='auto 或 #RRGGBB'),
                                 io.String.Input('filename_prefix', display_name='文件名前缀', default='HairDeck/hair'),
                                 RIG.Input('rig', display_name='骨骼线预览', optional=True,
                                           tooltip='连接后将骨骼显示为线条几何；真正的蒙皮和弹簧骨骼请使用 VRM 导出。')],
                         outputs=[io.File3DGLB.Output(display_name='GLB 模型'), io.String.Output(display_name='文件路径')])

    @classmethod
    def execute(cls, hair, show_head, color, filename_prefix, rig=None):
        path = exporting.save_glb(hair, rig, show_head, color, filename_prefix)
        return io.NodeOutput(Types.File3D(str(path)), str(path), ui=ui.PreviewText(str(path)))

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return float('nan')


class HairDeckExportVRM(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id='HairDeckExportVRM', display_name='HairDeck 导出 VRM', category=CATEGORY,
                         description='将头发与弹簧骨骼装配到示例角色；调用本地 Blender 4.2 LTS。', is_output_node=True,
                         inputs=[HAIR.Input('hair', display_name='发片数据'), RIG.Input('rig', display_name='骨骼数据'),
                                 io.String.Input('color', display_name='发色', default='auto', tooltip='auto 或 #RRGGBB'),
                                 io.String.Input('filename_prefix', display_name='文件名前缀', default='HairDeck/avatar'),
                                 io.String.Input('blender_path', display_name='Blender 路径', default='',
                                                 tooltip='留空时使用模型包 tools/blender 中的便携版。')],
                         outputs=[io.String.Output(display_name='VRM 文件路径'), io.Image.Output(display_name='角色预览')])

    @classmethod
    def execute(cls, hair, rig, color, filename_prefix, blender_path):
        path, preview = exporting.save_vrm(hair, rig, color, filename_prefix, blender_path)
        return io.NodeOutput(str(path), preview, ui=ui.PreviewImage(preview, cls=cls))

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return float('nan')


class HairDeckMotionPreview(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id='HairDeckMotionPreview', display_name='HairDeck 动画预览', category=CATEGORY,
                         is_output_node=True,
                         inputs=[HAIR.Input('hair', display_name='发片数据'), RIG.Input('rig', display_name='骨骼数据'),
                                 io.Boolean.Input('show_chains', display_name='显示骨骼线', default=False),
                                 io.String.Input('color', display_name='发色', default='auto'),
                                 io.String.Input('filename_prefix', display_name='文件名前缀', default='HairDeck/motion')],
                         outputs=[io.Video.Output(display_name='动画'), io.String.Output(display_name='视频路径')])

    @classmethod
    def execute(cls, hair, rig, show_chains, color, filename_prefix):
        path, saved = exporting.save_motion(hair, rig, show_chains, color, filename_prefix)
        return io.NodeOutput(InputImpl.VideoFromFile(str(path)), str(path), ui=ui.PreviewVideo([saved]))

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return float('nan')


class HairDeckExtension(ComfyExtension):
    async def get_node_list(self):
        return [HairDeckLoader, HairDeckPreprocess, HairDeckGenerate, HairDeckSpringBones,
                HairDeckExportGLB, HairDeckExportVRM, HairDeckMotionPreview]
