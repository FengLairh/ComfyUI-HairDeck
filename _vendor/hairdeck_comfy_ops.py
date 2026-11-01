"""Attention dispatch through the backend selected by ComfyUI."""
import torch
from comfy.ldm.modules.attention import optimized_attention


def scaled_dot_product_attention(q, k, v, attn_mask=None, dropout_p=0.0, is_causal=False,
                                 scale=None, enable_gqa=False):
    if dropout_p:
        raise ValueError('HairDeck nodes support inference attention without dropout.')
    unbatched = q.ndim == 3
    if unbatched:
        q, k, v = q.unsqueeze(0), k.unsqueeze(0), v.unsqueeze(0)
    if is_causal:
        if attn_mask is not None:
            raise ValueError('Causal attention cannot also receive an explicit mask.')
        attn_mask = torch.ones(q.shape[-2], k.shape[-2], dtype=torch.bool, device=q.device).tril()
    result = optimized_attention(q, k, v, q.shape[-3], mask=attn_mask, skip_reshape=True,
                                 skip_output_reshape=True, scale=scale, enable_gqa=enable_gqa)
    return result.squeeze(0) if unbatched else result
