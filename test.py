from __future__ import annotations
from PIL import Image
from config import RunConfig
from knobs import Knobs
from datetime import datetime
import os
import shutil
import engine


os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

def archive_existing(out_dir: str) -> None:
    if not os.path.isdir(out_dir) or not os.listdir(out_dir):
        return
        
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = os.path.join("runs", "past", stamp)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(out_dir, dest)


def main() -> None:
    cfg = RunConfig()
    #cfg.set_random_seed() 

    print(f"seed: {cfg.seed}")
    out_dir = "runs/latest"
    archive_existing(out_dir)
    cond_dir = os.path.join(out_dir, "conditional")
    uncond_dir = os.path.join(out_dir, "unconditional")
    os.makedirs(cond_dir, exist_ok=True)
    os.makedirs(uncond_dir, exist_ok=True)

    if not os.path.exists(cfg.scene_path):
        raise SystemExit(f"no scene image at {cfg.scene_path!r} — drop one there first")

    print("loading pipeline")
    pipe = engine.load_pipeline(cfg.model_id, cfg.device, cfg.dtype, cfg.scheduler)

    caption = engine.caption_scene(cfg.scene_path)
    print(f"  caption: {caption!r}")

    scene = Image.open(cfg.scene_path).convert("RGB").resize((cfg.width, cfg.height))
    scene.save(f"{out_dir}/scene.png")

    base = Knobs(scene_precision=0.5, prior_precision=7.5, gain=1.0, depth=0, recurrence=0.35)

    print("  rendering conditional frame")
    cond = engine.render_frame(pipe, scene, scene, caption, base, cfg.seed, steps=cfg.denoise_steps)
    cond.save(f"{cond_dir}/01.png")

    print("  rendering unconditional frame")
    uncond_knobs = Knobs(scene_precision=0.5, prior_precision=1.0, gain=1.0, depth=0, recurrence=0.35)
    uncond = engine.render_frame(pipe, scene, scene, "", uncond_knobs, cfg.seed, steps=cfg.denoise_steps)
    uncond.save(f"{uncond_dir}/01.png")

    print(f"done {out_dir}")


if __name__ == "__main__":
    main()