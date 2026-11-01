"""Run with ComfyUI's Python from its directory; exercises the selected CUDA attention backend."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_vendor'))

import torch
import torch.nn.functional as F

import hairdeck_comfy_ops as attention
from hairdeck_core.models import setdit


class AttentionDtypeTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(17)

    def test_model_rmsnorm_under_autocast(self):
        for dtype in (torch.bfloat16, torch.float16):
            for cross in (False, True):
                with self.subTest(dtype=dtype, cross_attention=cross):
                    block = setdit.Attention(128, 2, ctx_dim=96 if cross else None).cuda().eval()
                    image = torch.randn(1, 8, 128, device='cuda')
                    context = torch.randn(1, 5, 96, device='cuda') if cross else None
                    with torch.autocast('cuda', dtype=dtype):
                        with patch.object(setdit, 'comfy_attention', F.scaled_dot_product_attention):
                            expected = block(image, context)
                        with patch.object(attention, 'optimized_attention', wraps=attention.optimized_attention) as kernel:
                            actual = block(image, context)
                    self.assertEqual(actual.dtype, dtype)
                    self.assertEqual(tuple(value.dtype for value in kernel.call_args.args[:3]), (dtype,) * 3)
                    torch.testing.assert_close(actual, expected, rtol=.02, atol=.02)

    def test_fp32_inputs_follow_autocast(self):
        q, k, v = [torch.randn(1, 2, 8, 64, device='cuda') for _ in range(3)]
        with torch.autocast('cuda', dtype=torch.bfloat16):
            expected = F.scaled_dot_product_attention(q, k, v)
            actual = attention.scaled_dot_product_attention(q, k, v)
        self.assertEqual(actual.dtype, torch.bfloat16)
        torch.testing.assert_close(actual, expected, rtol=.02, atol=.02)

    def test_disabled_autocast_preserves_fp32(self):
        q, k, v = [torch.randn(1, 2, 8, 64, device='cuda') for _ in range(3)]
        with torch.autocast('cuda', enabled=False):
            expected = F.scaled_dot_product_attention(q, k, v)
            actual = attention.scaled_dot_product_attention(q, k, v)
        self.assertEqual(actual.dtype, torch.float32)
        torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-5)

    def test_unbatched_mixed_inputs_follow_autocast(self):
        q, k = [torch.randn(2, 8, 64, device='cuda') for _ in range(2)]
        v = torch.randn_like(q, dtype=torch.bfloat16)
        with torch.autocast('cuda', dtype=torch.bfloat16):
            expected = F.scaled_dot_product_attention(q, k, v)
            actual = attention.scaled_dot_product_attention(q, k, v)
        self.assertEqual(actual.shape, q.shape)
        self.assertEqual(actual.dtype, torch.bfloat16)
        torch.testing.assert_close(actual, expected, rtol=.02, atol=.02)


if __name__ == '__main__':
    unittest.main(verbosity=2)
