from __future__ import annotations
from dataclasses import dataclass, field, asdict
from io import TextIOWrapper
from typing import Literal
import yaml
import random


GeometryArm = Literal["A_pure_emergence", "B_logpolar_bias"] #  test wether natural emergence mirrors biased emergence


@dataclass
class DoseConfig:
    peak_min: float = 4.0
    rise: float = 1.2
    fall: float = 4.5
    dmax: float = 1.0
    total_min: float = 12.0
    n_frames: int = 11
    hold_min: float = 0.0 

    def __post_init__(self):
        if self.rise <= 0 or self.fall <= 0:
            raise ValueError("rise and fall must be positive")


@dataclass
class KnobShaping:
    scene_min: float = 0.15  # sensory precision floor, reached at peak; must stay > 0 so the scene can return
    scene_max: float = 0.85  # sensory precision ceiling, at rest / baseline (docs use 1.0; equivalent here since recurrence≈0 at rest)
    prior_w_base: float = 7.5 # rebus prior
    prior_w_min: float = 1.0
    gain_slope: float = 1.5 # 1 + gain_slope * D
    depth_shallow: int = 0 # flat hookable_blocks index: 0 = shallowest down_block
    depth_deep: int = 4 # 4 = mid_block bottleneck (idx 0..3 down, 4 mid, 5..8 up); see note below
    # NOTE: depth = round(lerp(shallow, deep, D))
    recurrence_min: float = 0.0
    recurrence_max: float = 0.6
    ds_min: float = 0.0
    ds_max: float = 0.0


@dataclass
class RunConfig:
    model_id: str = "stable-diffusion-v1-5/stable-diffusion-v1-5"
    device: str = "mps"
    dtype: str = "float32"
    scheduler: str = "ddim"
    height: int = 512
    width: int = 512
    denoise_steps: int = 30
    seed: int = 0
    geometry_arm: GeometryArm = "A_pure_emergence"
    caption: str | None = None
    scene_path: str = "resources/scene.jpg"
    out_dir: str = "output/latest"
    dose: DoseConfig = field(default_factory=DoseConfig)
    knobs: KnobShaping = field(default_factory=KnobShaping)

    def set_random_seed(self) -> int:
        self.seed = random.randrange(2**32)
        return self.seed

    def to_yaml(self, path: str) -> TextIOWrapper | None:
        with open(path, "w") as file:
            yaml.dump(asdict(self), file)
            return file
        return None

    @classmethod
    def from_yaml(cls, path: str) -> "RunConfig":
        with open(path, "r") as file: 
            data = yaml.safe_load(file)

        dose_cfg = data.get("dose")
        knob_cfg = data.get("knobs")
        
        return RunConfig(
            model_id=data.get("model_id", "stable-diffusion-v1-5/stable-diffusion-v1-5"),
            device=data.get("device", "mps"),
            dtype=data.get("dtype", "float32"),
            scheduler=data.get("scheduler", "ddim"),
            height=data.get("height", 512),
            width=data.get("width", 512),
            denoise_steps=data.get("denoise_steps", 30),
            seed=data.get("seed", 0),
            geometry_arm=data.get("geometry_arm", "A_pure_emergence"),
            caption=data.get("caption", None),
            scene_path=data.get("scene_path", "resources/scene.jpg"),
            out_dir=data.get("out_dir", "output/latest"),
            dose=DoseConfig(**dose_cfg),
            knobs=KnobShaping(**knob_cfg),
        )