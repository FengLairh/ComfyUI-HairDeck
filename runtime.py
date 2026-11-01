"""Native model loading and execution owned by ComfyUI's model manager."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F

import comfy.model_management as mm
from comfy.model_patcher import ModelPatcher
from safetensors.torch import load_file

from . import model_files

from hairdeck_core import paths
from hairdeck_core.ckpt import load as load_checkpoint
from hairdeck_core.cards.tokens import LatentDecoder, clean_tokens, tokens_to_cards
from hairdeck_core.cards.vae import LoadedVAE
from hairdeck_core.data.crop import composite
from hairdeck_core.data.illus import crop_white
from hairdeck_core.infer.glb import hair_color
from hairdeck_core.infer.image import euler_cfg, load_image
from hairdeck_core.infer.panel import prep_panel
from hairdeck_core.models.imgmodel import DinoEncoder, ImgSetDiT
from hairdeck_core.models.tokenizer import LatentTokenizer
from hairdeck_core.prep.preprocess import PRESETS, Prep, Preprocessor
from hairdeck_core.sampling.flow import fm_sample
from hairdeck_core.spring.chaindit import ChainDiT, chain_stats, decode as decode_chains
from hairdeck_sam3.model_builder import build_sam3_image_model
from hairdeck_sam3.model.sam3_image_processor import Sam3Processor
from hairdeck_birefnet.birefnet import BiRefNet

def image_bytes(image, transparent_mask=None):
    if image.shape[0] != 1:
        raise ValueError('当前节点每次处理一张图片，批量生成请使用 ComfyUI 队列。')
    pixels = np.clip(image[0].detach().cpu().numpy() * 255 + 0.5, 0, 255).astype(np.uint8)
    if transparent_mask is not None:
        mask = np.clip(transparent_mask.reshape(-1, *transparent_mask.shape[-2:])[0].detach().cpu().numpy(), 0, 1)
        alpha = Image.fromarray(((1 - mask) * 255 + 0.5).astype(np.uint8))
        alpha = alpha.resize((pixels.shape[1], pixels.shape[0]), Image.Resampling.BILINEAR)
        pixels = np.concatenate([pixels[..., :3], np.array(alpha)[..., None]], axis=-1)
    return Image.fromarray(pixels)


def image_tensor(image):
    return torch.from_numpy(np.array(image.convert('RGB'), dtype=np.float32) / 255).unsqueeze(0)


class Matte(nn.Module):
    def __init__(self, checkpoint):
        super().__init__()
        self.net = BiRefNet(bb_pretrained=False)
        self.net.load_state_dict(load_file(str(checkpoint)))
        self.net.eval().half()
        self.register_buffer('mean', torch.tensor([.485, .456, .406]).view(1, 3, 1, 1))
        self.register_buffer('std', torch.tensor([.229, .224, .225]).view(1, 3, 1, 1))

    def forward(self, rgb):
        height, width = rgb.shape[:2]
        pixels = torch.from_numpy(np.array(rgb, copy=True)).to(self.mean.device).permute(2, 0, 1)[None].float() / 255
        pixels = F.interpolate(pixels, (768, 768), mode='bilinear', align_corners=False)
        result = self.net(((pixels - self.mean) / self.std).half())[-1].sigmoid().float()
        return F.interpolate(result, (height, width), mode='bilinear', align_corners=False)[0, 0]


class PreprocessWeights(nn.Module):
    def __init__(self, sam3, birefnet):
        super().__init__()
        self.sam = build_sam3_image_model(checkpoint_path=str(sam3),
                                          device='cpu', load_from_HF=False, compile=False)
        self.matte = Matte(birefnet)


class HairWeights(nn.Module):
    def __init__(self, root, image_model, card_vae, dinov3):
        super().__init__()
        checkpoint = load_checkpoint(str(image_model))
        self.args = SimpleNamespace(**checkpoint['args'])
        self.encoder = DinoEncoder(self.args.dino, self.args.res, weights=str(dinov3))
        self.dit = ImgSetDiT(40, self.args.dim, self.args.depth, self.args.heads,
                             enc_dim=self.encoder.dim, n_ctx=self.encoder.n_tokens).eval()
        self.dit.load_state_dict(checkpoint['ema'])
        self.vae = LoadedVAE(str(root / 'ckpt/card_vae'), 'cpu', checkpoint=str(card_vae))


class ChainWeights(nn.Module):
    def __init__(self, filename):
        super().__init__()
        checkpoint = load_checkpoint(str(filename))
        args = SimpleNamespace(**checkpoint['args'])
        self.dit = ChainDiT(checkpoint['dim'], args.dim, args.depth, args.heads).eval()
        self.dit.load_state_dict(checkpoint['ema'])
        self.token_dim = checkpoint['dim']
        self.vae_name = args.vae


class ModelBundle:
    def __init__(self, files):
        self.root = root = files.root
        self.signature = model_files.signature(files)
        self.device = mm.get_torch_device()
        if self.device.type != 'cuda' or not torch.cuda.is_bf16_supported():
            raise ValueError('HairDeck 需要支持 BF16 的 NVIDIA CUDA 显卡（RTX 30 系列或更新）。')
        cpu = torch.device('cpu')
        with paths.use(root):
            self.preprocess = ModelPatcher(PreprocessWeights(files.sam3, files.birefnet), self.device, cpu)
            self.hair = ModelPatcher(HairWeights(root, files.image_model, files.card_vae, files.dinov3), self.device, cpu)
            self.chain = ModelPatcher(ChainWeights(files.chain_model), self.device, cpu)
            self.chain_stats = chain_stats()
        if self.chain.model.vae_name != self.hair.model.args.vae:
            raise ValueError('骨骼模型与发片 VAE 版本不匹配。')
        self.token_stats = json.loads((root / 'data/token_stats_head.json').read_text())
        self.latent_stats = json.loads((root / 'ckpt/card_vae/latent_stats_head.json').read_text())

    def get_models(self):
        return [self.preprocess, self.hair, self.chain]

    def load(self, patcher, workspace_gb):
        mm.load_models_gpu([patcher], memory_required=int(workspace_gb * 2**30), force_full_load=True)
        mm.throw_exception_if_processing_interrupted()
        return patcher.model

    def tokenizer(self):
        return LatentTokenizer(self.token_stats, self.latent_stats, device=self.device)


@dataclass
class PreparedImage:
    root: Path
    model_signature: str
    signature: str
    crop: np.ndarray
    color: list


@dataclass
class HairData:
    root: Path
    model_signature: str
    signature: str
    seed: int
    cards: list
    tokens: np.ndarray
    color: list


@dataclass
class RigData:
    hair_signature: str
    chains: list


def preprocess(bundle, image, transparent_mask=None, source=None):
    weights = bundle.load(bundle.preprocess, 4)
    source = image_bytes(image, transparent_mask) if source is None else source
    rgb, alpha, _ = load_image(source)
    preset = PRESETS['best']
    prep = Prep(preset['cfg'], matte='birefnet_matting', matte_size=preset.get('alpha_size', 768),
                wr=preset.get('wr', 1024), crop_expand=preset.get('crop_expand', 1.3),
                model=weights.sam, processor=Sam3Processor(weights.sam, device=str(bundle.device), confidence_threshold=.5),
                matte_model=weights.matte)
    processor = Preprocessor(prep=prep)
    prepared = processor(rgb, alpha)
    if prepared['box'] is None:
        raise ValueError('未识别到头发或面部，请使用头部清晰可见的角色图片。')
    opacity = prepared['person'].copy()
    if opacity.max() <= 127:
        opacity[:] = 255
    full = np.asarray(composite(Image.fromarray(np.concatenate([rgb, opacity[..., None]], -1), 'RGBA')))
    crop = crop_white(full, prepared['box'], bundle.hair.model.args.res)
    digest = hashlib.sha256(repr((source.mode, source.size)).encode() + source.tobytes() + bundle.signature.encode()).hexdigest()
    output = PreparedImage(bundle.root, bundle.signature, digest, crop, hair_color(rgb, prepared['hair']))
    masks = [torch.from_numpy(prepared[key].astype(np.float32)).unsqueeze(0) for key in ('hair', 'face')]
    return output, image_tensor(Image.fromarray(crop)), *masks, image_tensor(prep_panel(prepared, crop))


def generate(bundle, prepared, seed, steps, cfg):
    if prepared.model_signature != bundle.signature:
        raise ValueError('预处理数据与模型版本不匹配，请重新执行预处理。')
    weights = bundle.load(bundle.hair, 2)
    token = bundle.tokenizer()
    rng = torch.Generator(device=bundle.device).manual_seed(seed)
    noise = torch.randn(1, weights.args.nmax, token.dim, generator=rng, device=bundle.device)
    pixels = torch.from_numpy(prepared.crop.copy()).permute(2, 0, 1)[None].to(bundle.device)
    with torch.autocast('cuda', dtype=torch.bfloat16):
        conditioning = weights.dit.encode_cond(weights.encoder(pixels))
        sampled = euler_cfg(weights.dit, conditioning, noise, steps, cfg)
    decoder = LatentDecoder(vae=weights.vae)
    cards = tokens_to_cards(token, sampled, decoder, fix=True)[0]
    if not cards:
        raise ValueError('未生成有效发片，请更换随机种子或图片。')
    digest = hashlib.sha256(f'{prepared.signature}:{seed}:{steps}:{cfg}'.encode()).hexdigest()
    return HairData(bundle.root, bundle.signature, digest, seed, cards, sampled.float().cpu().numpy().copy(), prepared.color)


def generate_rig(bundle, hair, seed, steps, cfg):
    if hair.model_signature != bundle.signature:
        raise ValueError('骨骼与发片必须使用同一个模型包。')
    weights = bundle.load(bundle.chain, 1)
    tokens = torch.from_numpy(hair.tokens).to(bundle.device)
    rng = torch.Generator(device=bundle.device).manual_seed(seed)
    with torch.autocast('cuda', dtype=torch.bfloat16):
        conditioning = weights.dit.encode_cond(clean_tokens(bundle.tokenizer(), tokens))
        sampled = fm_sample(weights.dit, conditioning, 48, weights.token_dim, steps, cfg, 1.0, rng, 'euler')
    chains = decode_chains(sampled[0].float().cpu().numpy(), bundle.chain_stats)
    return RigData(hair.signature, chains)
