from pathlib import Path
import hashlib

import nodes as comfy_nodes
import folder_paths
from comfy_api.latest import ComfyExtension, io, ui, Types

from . import runtime, generation, output, heads, model_files

MODEL = io.Custom('HAIRDECK_MODEL')
RESULT = io.Custom('HAIRDECK_RESULT')
CATEGORY = 'HairDeck'


def input_images():
    directory = Path(folder_paths.get_input_directory())
    return [''] + sorted(path.name for path in directory.iterdir()
                         if path.is_file() and path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff'))


def input_path(image):
    root = Path(folder_paths.get_input_directory()).resolve()
    path = Path(folder_paths.get_annotated_filepath(image)).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('图片必须位于 ComfyUI input 目录。')
    return path


def load_input(image, external_image, transparent_mask):
    if external_image is not None:
        return external_image, transparent_mask
    if not image:
        raise ValueError('请在生成节点上传/选择角色图片，或连接高级选项中的外部图像。')
    input_path(image)
    pixels, alpha = comfy_nodes.LoadImage().load_image(image)
    return pixels, transparent_mask if transparent_mask is not None else alpha


class HairDeckLoader(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id='HairDeckLoader', display_name='HairDeck 模型加载', category=CATEGORY,
                         description='分别选择六个实际模型文件，由 ComfyUI 管理显存。',
                         inputs=[*[io.Combo.Input(role, display_name=label, options=model_files.filenames(role),
                                                  default=model_files.default_file(role),
                                                  tooltip='ComfyUI/models/hairdeck/' + relative)
                                    for role, (label, relative, _) in model_files.MODELS.items()],
                                 io.Combo.Input('resources', display_name='配套资源目录',
                                                options=list(model_files.resources()),
                                                default=next(iter(model_files.resources()), None), advanced=True,
                                                tooltip='统计文件、角色和头模资源所在目录；权重使用上方独立选择的文件。')],
                         outputs=[MODEL.Output(display_name='模型')])

    @classmethod
    def execute(cls, resources, **models):
        return io.NodeOutput(runtime.ModelBundle(model_files.resolve(resources, models)))

    @classmethod
    def fingerprint_inputs(cls, resources, **models):
        return model_files.signature(model_files.resolve(resources, models))


class HairDeckGenerate(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id='HairDeckGenerate', display_name='HairDeck 生成头发', category=CATEGORY,
                         description='内部完成图片预处理、发片生成和可选弹簧骨骼，无需拆成多个节点。',
                         inputs=[MODEL.Input('model', display_name='模型'),
                                 io.Combo.Input('image', display_name='角色图片', options=input_images(), default='',
                                                extra_dict={'image_upload': True}),
                                 io.Int.Input('seed', display_name='随机种子', default=0, min=0, max=2**64 - 1,
                                              control_after_generate=True),
                                 io.Int.Input('steps', display_name='采样步数', default=50, min=1, max=200),
                                 io.Float.Input('cfg', display_name='引导强度', default=2.0, min=1.0, max=4.0, step=.25),
                                 io.Boolean.Input('generate_bones', display_name='生成弹簧骨骼', default=True),
                                 io.Image.Input('external_image', display_name='外部图像', optional=True, advanced=True,
                                                tooltip='连接后优先使用此图像；默认直接在本节点上传图片。'),
                                 io.Mask.Input('transparent_mask', display_name='透明区域蒙版', optional=True, advanced=True,
                                               tooltip='1 为透明，0 为保留；不连接时使用上传图片自带的透明度。')],
                         outputs=[RESULT.Output(display_name='生成结果')])

    @classmethod
    def execute(cls, model, image, seed, steps, cfg, generate_bones, external_image=None, transparent_mask=None):
        pixels, mask = load_input(image, external_image, transparent_mask)
        result = generation.generate(model, pixels, seed, steps, cfg, generate_bones, mask)
        return io.NodeOutput(result, ui=ui.PreviewImage(result.preview, cls=cls))

    @classmethod
    def fingerprint_inputs(cls, image, external_image=None, **kwargs):
        if external_image is not None or not image:
            return 'external-image'
        return hashlib.sha256(input_path(image).read_bytes()).hexdigest()


class HairDeckSave(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id='HairDeckSave', display_name='HairDeck 输出保存', category=CATEGORY,
                         description='集中保存模型、VRM、动画和可选过程图；输出区域提供预览和下载。', is_output_node=True,
                         inputs=[RESULT.Input('result', display_name='生成结果'),
                                 io.Combo.Input('format', display_name='保存内容', options=output.FORMATS,
                                                default='GLB + VRM + 动画'),
                                 io.String.Input('filename_prefix', display_name='保存前缀', default='HairDeck/result'),
                                 io.String.Input('color', display_name='发色', default='auto', tooltip='auto 或 #RRGGBB'),
                                 io.Boolean.Input('show_head', display_name='GLB 包含参考头模', default=False),
                                 io.Boolean.Input('show_chains', display_name='显示骨骼线', default=False, advanced=True),
                                 io.Boolean.Input('save_debug', display_name='保存过程图和曲线数据', default=True, advanced=True),
                                 io.String.Input('blender_path', display_name='Blender 路径', default='', advanced=True,
                                                 tooltip='VRM 导出使用；留空时自动查找模型包中的便携工具。'),
                                 io.Combo.Input('head_profile', display_name='基础头模', optional=True,
                                                options=heads.choices(model_files.resources().values()), default='auto',
                                                tooltip='auto 使用本机默认头模；upstream 使用原始参考头模。')],
                         hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo],
                         outputs=[io.File3DGLB.Output(display_name='GLB 模型'), io.String.Output(display_name='结果目录')])

    @classmethod
    def execute(cls, result, format, filename_prefix, color, show_head, show_chains, save_debug, blender_path, head_profile='auto'):
        saved = output.save(cls, result, format, filename_prefix, color, show_head, show_chains, save_debug, blender_path, head_profile)
        return io.NodeOutput(Types.File3D(str(saved.model)), str(saved.directory), ui=saved.ui)

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return float('nan')


class HairDeckExtension(ComfyExtension):
    async def get_node_list(self):
        return [HairDeckLoader, HairDeckGenerate, HairDeckSave]
