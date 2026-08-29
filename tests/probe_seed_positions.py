"""Is the arm-A lattice's POSITION seeded by the frozen noise?

`render_frame` re-seeds a CPU generator from the constant `cfg.seed` on every call and consumes it
in a fixed order, so `initial_noise` is byte-identical on every frame of a run. That makes the
headline "input-independent lattice" claim vulnerable: if the pattern is really a fingerprint of one
noise draw, it is a seed artifact, not an emergent form constant.

The discriminator is position, not presence. Render the same peak knobs at three seeds on flat gray
with no caption:
  - INTRINSIC: wavelength stays in the 18-32px band at all three seeds, while the cells LAND
    SOMEWHERE ELSE each time (non-zero, seed-varying cross-correlation offset).
  - ARTIFACT:  frames near-identical across seeds (offset ~0), or the wavelength wanders outside the
    band, which refutes input-independence outright.

Run from project root:  .venv/bin/python tests/probe_seed_positions.py
"""
from __future__ import annotations
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from src.core.config import RunConfig  # noqa: E402
from src.core.knobs import Knobs  # noqa: E402
from src.render import engine  # noqa: E402
from tests.geometry_score import clarity  # noqa: E402


OUT_DIR = "output/sweeps/seed_positions"
SEEDS = [0, 1, 2]
# the real apex operating point of configs/crisp_trip.yaml (frame 13, D=1.0) — probing anything
# else does not test the finding. prior 6.0 is E-PRIOR's floor: at CFG 1 the lattice is mush.
GAIN = 2.8
DEPTH = 0
DENOISE_STRENGTH = 0.82
PRIOR = 6.0
SCENE_PRECISION = 0.4
RECURRENCE = 0.12


def _gray(im: Image.Image) -> np.ndarray:
    a = np.asarray(im.convert("L")).astype(np.float32)
    return a - a.mean()


def offset_from(reference: Image.Image, other: Image.Image) -> tuple[int, int, float]:
    # peak of the circular cross-correlation, via FFT; offset in px from the top-left origin
    a = _gray(reference)
    b = _gray(other)
    corr = np.fft.ifft2(np.fft.fft2(a) * np.conj(np.fft.fft2(b))).real
    peak = np.unravel_index(int(np.argmax(corr)), corr.shape)
    normalized = corr.max() / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)

    dy = peak[0] if peak[0] <= a.shape[0] // 2 else peak[0] - a.shape[0]
    dx = peak[1] if peak[1] <= a.shape[1] // 2 else peak[1] - a.shape[1]
    return int(dy), int(dx), float(normalized)


def main() -> None:
    cfg = RunConfig()
    os.makedirs(OUT_DIR, exist_ok=True)
    print("loading pipeline")
    pipe = engine.load_pipeline(cfg.model_id, cfg.device, cfg.dtype, cfg.scheduler)

    flat = Image.new("RGB", (cfg.width, cfg.height), (127, 127, 127))
    knobs = Knobs(scene_precision=SCENE_PRECISION, prior_precision=PRIOR, gain=GAIN, depth=DEPTH,
                  recurrence=RECURRENCE)

    frames = {}
    for seed in SEEDS:
        t0 = time.time()
        frames[seed] = engine.render_frame(
            pipe, flat, flat, "", knobs, seed,
            steps=cfg.denoise_steps, logpolar=False, soft_clip=True,
            denoise_strength=DENOISE_STRENGTH,
        )
        frames[seed].save(os.path.join(OUT_DIR, f"seed{seed}.png"))
        print(f"  seed {seed}  {time.time() - t0:5.1f}s")

    print()
    print(f"{'seed':>5s} {'wl_px':>7s} {'band':>5s} {'clarity':>9s} {'dy':>5s} {'dx':>5s} {'xcorr':>7s}")
    for seed in SEEDS:
        m = clarity(frames[seed])
        if seed == SEEDS[0]:
            dy, dx, xc = 0, 0, 1.0
        else:
            dy, dx, xc = offset_from(frames[SEEDS[0]], frames[seed])
        band = "in" if m["in_band"] else "OUT"
        print(f"{seed:5d} {m['wavelength']:7.1f} {band:>5s} {m['clarity']:9.2f} {dy:5d} {dx:5d} {xc:7.3f}")

    in_band = [clarity(frames[s])["in_band"] for s in SEEDS]
    offsets = [offset_from(frames[SEEDS[0]], frames[s])[:2] for s in SEEDS[1:]]
    moved = all(o != (0, 0) for o in offsets)

    print()
    print(f"wavelength in band at all seeds: {all(in_band)}")
    print(f"cells move across seeds:         {moved}  offsets={offsets}")
    if all(in_band) and moved:
        print("VERDICT: intrinsic — same form constant, different placement per seed.")
    elif not all(in_band):
        print("VERDICT: REFUTED — wavelength is seed-dependent; the arm-A finding does not hold.")
    else:
        print("VERDICT: frozen-noise artifact, or the seed is not varying — investigate before use.")
    print(f"done -> {OUT_DIR}")


if __name__ == "__main__":
    main()
