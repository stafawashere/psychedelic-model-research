"""The gain/depth knob: reach into ONE level of the U-Net and turn up the volume.

Brain picture: this is 5-HT2A cortical gain. We pick one level of the visual
hierarchy (the `depth` knob) and crank how loudly its neurons fire (the `gain`
knob) — the DeepDream move, "amplify whatever this layer already sees."

How it physically happens: a forward hook. We don't rewrite the U-Net; we clip a
tap onto one block so that every time the network's data flows THROUGH that block,
we grab the output on its way out, scale it, and hand it back. attach() clips the
tap on, detach() takes it off after the frame.

Two facts the empirical probes (testing/) nailed down, and that this file is shaped by:

  * A block's output is NOT always one tensor. Down blocks hand back TWO things:
    (summary-going-down, photocopies-for-the-shelf) -- the res_samples skip copies.
    Mid and up blocks hand back a single tensor. So the hook has to check which it got.

  * "Multiply, then renormalize back to the original size" CANCELS ITSELF OUT for a
    flat gain -- it's the identity, the knob does nothing. (Every block starts with
    GroupNorm, which divides out any uniform scaling.) So to stop blow-up we do NOT
    renorm; we CLAMP -- cap how far any value can swing. That bounds the runaway
    without erasing the gain effect.
"""
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


def _amplify(activation: torch.Tensor, gain: float, logpolar: bool) -> torch.Tensor:
    out = activation * gain # tweaking gain up
    if logpolar:
        out = _logpolar_warp(out)

    std = activation.float().std(dim=(2, 3), keepdim=True).clamp_min(1e-4).to(out.dtype)
    bound = CLAMP_STD * std
    out = torch.minimum(torch.maximum(out, -bound), bound) 
    return torch.nan_to_num(out, nan=0.0)


def attach(unet: UNet2DConditionModel, depth: int, gain: float, logpolar: bool) -> list:
    blocks = hookable_blocks(unet)
    out_of_depth = not 0 <= depth < len(blocks)
    if out_of_depth:
        raise IndexError(f"depth {depth} out of range for {len(blocks)} hookable blocks")

    block = blocks[depth]
    def hook(module, inputs, output) -> tuple[Tensor, *tuple[Any, ...]] | Tensor:
        is_down_block = isinstance(output, tuple)
        if is_down_block:
            summary = output[0]
            res_samples = output[1:] # transfer inside down block to create a direct tap between down and up
            return (_amplify(summary, gain, logpolar), *res_samples)

        return _amplify(output, gain, logpolar)
    return [block.register_forward_hook(hook)] 


def detach(handles: list) -> None:
    for handle in handles:
        handle.remove()
