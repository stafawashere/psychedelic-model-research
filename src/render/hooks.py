from __future__ import annotations
import math
from typing import Any

from diffusers.models import UNet2DConditionModel
import torch
from torch._tensor import Tensor


CLAMP_STD = 6.0


def hookable_blocks(unet: UNet2DConditionModel) -> list:
    return [*unet.down_blocks, unet.mid_block, *unet.up_blocks] # 1-3 lower level edges (down blocks), 4 deppest gist (bottleneck, U), 5-8 build back res (up blocks)


def _logpolar_warp(activation: torch.Tensor) -> torch.Tensor:
    b, c, h, w = activation.shape
    device = activation.device
    src = activation.float()

    ys = torch.linspace(-1.0, 1.0, h, device=device, dtype=torch.float32)
    xs = torch.linspace(-1.0, 1.0, w, device=device, dtype=torch.float32)
    grid_y, grid_x = torch.meshgrid(ys, xs, indexing="ij")

    radius = torch.sqrt(grid_x * grid_x + grid_y * grid_y).clamp_min(1e-3) # foveal floor: no /0 at centre
    theta = torch.atan2(grid_y, grid_x) # angle, [-pi, pi]
    log_r = torch.log(radius)
    log_r = (log_r - log_r.min()) / (log_r.max() - log_r.min() + 1e-8) * 2.0 - 1.0  # rescale to [-1, 1]

    sample_x = theta / math.pi # angle input x in [-1, 1]
    sample_y = log_r # log-radius
    grid = torch.stack([sample_x, sample_y], dim=-1).unsqueeze(0).expand(b, -1, -1, -1)

    warped = torch.nn.functional.grid_sample(src, grid, mode="bilinear", padding_mode="reflection", align_corners=False)
    return warped.to(activation.dtype)


def _amplify(activation: torch.Tensor, gain: float, logpolar: bool, soft: bool = False) -> torch.Tensor:
    out = activation * gain # tweaking gain up
    if logpolar:
        out = _logpolar_warp(out)

    std = activation.float().std(dim=(2, 3), keepdim=True).clamp_min(1e-4).to(out.dtype)
    bound = CLAMP_STD * std
    if soft:
        out = bound * torch.tanh(out / bound)
    else:
        out = torch.minimum(torch.maximum(out, -bound), bound)
    return torch.nan_to_num(out, nan=0.0)


def _make_hook(gain: float, logpolar: bool, soft: bool):
    # factory so each looped depth captures its OWN gain (closure-in-loop trap otherwise)
    def hook(module, inputs, output) -> tuple[Tensor, *tuple[Any, ...]] | Tensor:
        is_down_block = isinstance(output, tuple)
        if is_down_block:
            summary = output[0]
            res_samples = output[1:] # transfer inside down block to create a direct tap between down and up
            return (_amplify(summary, gain, logpolar, soft), *res_samples)

        return _amplify(output, gain, logpolar, soft)
    return hook


def attach(unet: UNet2DConditionModel, depth, gain, logpolar: bool, soft: bool = False) -> list:
    # depth/gain may be a single value (back-compat) OR matching lists for multi-block hooking
    blocks = hookable_blocks(unet)
    depths = [depth] if isinstance(depth, int) else list(depth)
    gains = [gain] * len(depths) if isinstance(gain, (int, float)) else list(gain)
    if len(gains) != len(depths):
        raise ValueError(f"got {len(depths)} depths but {len(gains)} gains")

    handles = []
    for d, g in zip(depths, gains):
        if not 0 <= d < len(blocks):
            raise IndexError(f"depth {d} out of range for {len(blocks)} hookable blocks")
        handles.append(blocks[d].register_forward_hook(_make_hook(g, logpolar, soft)))
    return handles


def detach(handles: list) -> None:
    for handle in handles:
        handle.remove()
