"""One-variable-at-a-time sweep around the APEX operating point, on the scene.

The deliverable trip's apex (configs/closed_arc.yaml frame 13) is a soft cell field. DMT geometry
reads hard-edged, high-contrast and ornate, so the question is which of the three knobs that can
still move at the apex buys edge definition without deepfrying:

  ds     0.82 -> 0.92   established crispness lever (cap is 0.92)
  gain   2.8  -> 4.0    more drive into idx0
  prior  6.0  -> 12.0   E-PRIOR found CFG monotonically sharpens WITH a caption. NOTE this fights
                        the REBUS direction (prior precision should FALL with dose) — a win here is
                        a tradeoff to report, not a free improvement.

Probed on the scene, not flat gray: with an empty caption cond == uncond, so CFG is a mathematical
no-op and a flat-field probe cannot rank `prior` at all.

Caveat: a single frame with prev == scene approximates the apex but omits the feedback history a
real frame 13 carries. Use this to RANK, then confirm with a trip.

Run from project root:  .venv/bin/python tests/sweep_apex.py
"""
from __future__ import annotations
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

from PIL import Image  # noqa: E402
from src.core.config import RunConfig  # noqa: E402
from src.core.knobs import Knobs  # noqa: E402
from src.render import engine  # noqa: E402
from src.measure.metrics import clarity_ungated, scene_fidelity  # noqa: E402


OUT_DIR = "output/sweeps/apex"
APEX = {"scene_precision": 0.4, "prior": 6.0, "gain": 2.8, "recurrence": 0.12, "ds": 0.82}
VARIANTS = [
    ("baseline", {}),
    ("ds_0.87", {"ds": 0.87}),
    ("ds_0.92", {"ds": 0.92}),
    ("gain_3.4", {"gain": 3.4}),
    ("gain_4.0", {"gain": 4.0}),
    ("prior_9", {"prior": 9.0}),
    ("prior_12", {"prior": 12.0}),
    ("ds_0.92_prior_12", {"ds": 0.92, "prior": 12.0}),
    ("ds_0.92_gain_4.0", {"ds": 0.92, "gain": 4.0}),
]


def main() -> None:
    cfg = RunConfig.from_yaml("configs/closed_arc.yaml")
    os.makedirs(OUT_DIR, exist_ok=True)
    print("loading pipeline", flush=True)
    pipe = engine.load_pipeline(cfg.model_id, cfg.device, cfg.dtype, cfg.scheduler)

    caption = engine.caption_scene(cfg.scene_path)
    print(f"  caption: {caption!r}", flush=True)
    scene = Image.open(cfg.scene_path).convert("RGB").resize((cfg.width, cfg.height))

    print(f"\n{'variant':20s} {'ungated':>9s} {'bandSh':>9s} {'acut':>6s} {'wl':>6s} "
          f"{'clip%':>6s} {'fidelity':>9s}", flush=True)
    for tag, override in VARIANTS:
        p = {**APEX, **override}
        knobs = Knobs(scene_precision=p["scene_precision"], prior_precision=p["prior"],
                      gain=p["gain"], depth=0, recurrence=p["recurrence"])
        t0 = time.time()
        frame = engine.render_frame(
            pipe, scene, scene, caption, knobs, cfg.seed,
            steps=cfg.denoise_steps, logpolar=False, soft_clip=True,
            denoise_strength=p["ds"],
        )
        frame.save(os.path.join(OUT_DIR, f"{tag}.png"))
        m = clarity_ungated(frame)
        fid = scene_fidelity(frame, scene)
        print(f"{tag:20s} {m['clarity_ungated']:9.1f} {m['band_sharp']:9.1f} {m['acutance']:6.2f} "
              f"{m['wavelength']:6.1f} {m['clip']*100:6.1f} {fid:9.3f}   ({time.time()-t0:4.1f}s)",
              flush=True)

    print(f"\ndone -> {OUT_DIR}  (clip% > ~10 is regressing toward deepfry; LOOK before ranking)",
          flush=True)


if __name__ == "__main__":
    main()
