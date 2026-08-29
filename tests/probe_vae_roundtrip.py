"""Does the VAE round trip preferentially discard the lattice?

Every frame of the feedback loop is re-encoded and decoded by a VAE trained to reconstruct natural
image statistics. If that codec is selectively hostile to the 18-32px band — exactly the kind of
high-frequency non-natural structure such a codec throws away — then geometry saturation has a
mechanism, and no amount of peak-dwell or knob tuning can buy hard edges past that ceiling.

Declared BEFORE running: the claim is that band-power in 18-32px drops by **more than 20%** across a
bare encode->decode with no denoising, while total variance drops by less. Comparable losses refute
"selectively hostile" and send saturation looking for a different explanation.

Runs the VAE only — no U-Net, no new render.

Run from project root:  .venv/bin/python tests/probe_vae_roundtrip.py [frame.png ...]
"""
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image  # noqa: E402
from src.core.config import RunConfig  # noqa: E402
from src.render import engine  # noqa: E402
from tests.geometry_score import _gray, _radius  # noqa: E402

BAND_LO, BAND_HI = 18.0, 32.0
DROP_THRESHOLD = 0.20


def band_power(im: Image.Image, lo: float = BAND_LO, hi: float = BAND_HI) -> float:
    g = _gray(im)
    p = np.abs(np.fft.fftshift(np.fft.fft2(g - g.mean()))) ** 2
    r = _radius(p.shape)
    # radius <-> wavelength: wl = N / r, so the band maps to an annulus in r
    n = p.shape[0]
    r_lo, r_hi = n / hi, n / lo
    mask = (r >= r_lo) & (r <= r_hi)
    return float(p[mask].sum())


def total_variance(im: Image.Image) -> float:
    return float(_gray(im).var())


@torch.no_grad()
def roundtrip(pipe, im: Image.Image) -> Image.Image:
    pixels = engine._preprocess(im, im.size)
    rng = torch.Generator(device="cpu").manual_seed(0)
    latent = engine._encode(pipe, pixels, rng)
    return engine._postprocess(engine._decode(pipe, latent))


def main(argv: list[str]) -> None:
    cfg = RunConfig()
    frames = argv or _default_frames()
    if not frames:
        raise SystemExit("no frames found — pass one explicitly, e.g. output/latest/frames/13.png")

    print("loading pipeline (VAE only is used)", flush=True)
    pipe = engine.load_pipeline(cfg.model_id, cfg.device, cfg.dtype, cfg.scheduler)

    print(f"\n{'frame':30s} {'band_before':>12s} {'band_after':>12s} {'band_loss':>10s} "
          f"{'var_loss':>9s} {'selective':>10s}", flush=True)
    for path in frames:
        im = Image.open(path).convert("RGB")
        out = roundtrip(pipe, im)
        out.save(os.path.join("output/sweeps", "vae_" + os.path.basename(path)))

        b0, b1 = band_power(im), band_power(out)
        v0, v1 = total_variance(im), total_variance(out)
        band_loss = 1.0 - b1 / max(b0, 1e-9)
        var_loss = 1.0 - v1 / max(v0, 1e-9)
        selective = band_loss - var_loss

        name = os.path.relpath(path)
        if len(name) > 30:
            name = "…" + name[-29:]
        print(f"{name:30s} {b0:12.3e} {b1:12.3e} {band_loss*100:9.1f}% {var_loss*100:8.1f}% "
              f"{selective*100:9.1f}%", flush=True)

    print(f"\ndeclared threshold: band loss > {DROP_THRESHOLD*100:.0f}% AND band loss > variance loss")
    print("selective > 0 means the round trip discards lattice faster than it discards the picture")


def _default_frames() -> list[str]:
    for d in ("output/latest/frames",):
        if os.path.isdir(d):
            fs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
            if fs:
                # the apex frame plus a come-up frame for contrast
                picks = [fs[13], fs[0]] if len(fs) > 13 else [fs[0]]
                return [os.path.join(d, f) for f in picks]
    return []


if __name__ == "__main__":
    os.makedirs("output/sweeps", exist_ok=True)
    main(sys.argv[1:])
