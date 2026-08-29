from __future__ import annotations
import os
import sys
import shutil
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from src.core.config import RunConfig  # noqa: E402
from src.core.dose import map_dose  # noqa: E402
from src.core.knobs import knobs_from_dose, lerp  # noqa: E402
from src.render import engine  # noqa: E402
from src.measure.make_video import frames_to_media  # noqa: E402


STABILIZE_CONTRAST = True


def _match_contrast(frame: Image.Image, ref: Image.Image) -> Image.Image:
    f = np.asarray(frame, dtype=np.float32)
    r = np.asarray(ref, dtype=np.float32)
    out = np.empty_like(f)
    for c in range(3):
        fc = f[..., c]
        rc = r[..., c]
        out[..., c] = (fc - fc.mean()) * (rc.std() / (fc.std() + 1e-5)) + rc.mean()
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def archive_existing(out_dir: str) -> None:
    if not os.path.isdir(out_dir) or not os.listdir(out_dir):
        return

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = os.path.join("output", "past", stamp)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(out_dir, dest)


def main(config_path: str | None = None) -> None:
    cfg = RunConfig.from_yaml(config_path) if config_path else RunConfig()
    arm_is_logpolar = cfg.geometry_arm == "B_logpolar_bias"  # arm B warps; arm A never does
    print(f"seed: {cfg.seed}  arm: {cfg.geometry_arm}")

    schedule = map_dose(cfg.dose)
    sampled_peak = max(d for _, d in schedule)
    peak_frame = max(range(len(schedule)), key=lambda i: schedule[i][1])
    if abs(sampled_peak - cfg.dose.dmax) > 1e-9:
        raise SystemExit(
            f"sampled peak {sampled_peak:.6f} < dmax {cfg.dose.dmax:.6f} "
            f"(nearest frame {peak_frame} at t={schedule[peak_frame][0]:.3f}min) — "
            "the schedule never lands on the apex; adjust n_frames or hold_min"
        )

    out_dir = cfg.out_dir
    archive_existing(out_dir)
    frame_dir = os.path.join(out_dir, "frames")
    os.makedirs(frame_dir, exist_ok=True)
    if not os.path.exists(cfg.scene_path):
        raise SystemExit(f"no scene image at {cfg.scene_path!r} — drop one there first")

    print("loading pipeline")
    pipe = engine.load_pipeline(cfg.model_id, cfg.device, cfg.dtype, cfg.scheduler)

    caption = cfg.caption if cfg.caption is not None else engine.caption_scene(cfg.scene_path)
    print(f"  caption: {caption!r}")

    # snapshot the resolved config, caption included — it is the run's pre-registration
    cfg.caption = caption
    cfg.to_yaml(os.path.join(out_dir, "config.yaml"))

    scene = Image.open(cfg.scene_path).convert("RGB").resize((cfg.width, cfg.height))
    scene.save(os.path.join(out_dir, "scene.png"))

    pad = len(str(len(schedule) - 1))
    decouple_ds = cfg.knobs.ds_max > 0.0

    prev = scene
    for i, (t_min, d) in enumerate(schedule):
        knobs = knobs_from_dose(d, cfg.knobs)
        ds = lerp(cfg.knobs.ds_min, cfg.knobs.ds_max, d) if decouple_ds else None
        print(
            f"  frame {i:>{pad}}  t={t_min:5.1f}min  D={d:.3f}  "
            f"scene={knobs.scene_precision:.3f} prior={knobs.prior_precision:.2f} "
            f"gain={knobs.gain:.3f} depth={knobs.depth} recur={knobs.recurrence:.3f}"
            + (f" ds={ds:.3f}" if ds is not None else "")
        )

        frame = engine.render_frame(
            pipe,
            scene,
            prev,
            caption,
            knobs,
            cfg.seed,
            steps=cfg.denoise_steps,
            logpolar=arm_is_logpolar,
            soft_clip=True,
            denoise_strength=ds,
        )

        frame.save(os.path.join(frame_dir, f"{i:0{pad}d}.png"))
        prev = _match_contrast(frame, scene) if STABILIZE_CONTRAST else frame

    frames_to_media(frame_dir, os.path.join(out_dir, "trip"), fps=5, hold_ends=2)
    print(f"done {out_dir}  ({len(schedule)} frames in frames/, trip.mp4 + trip.gif)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
