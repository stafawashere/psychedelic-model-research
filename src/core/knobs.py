from __future__ import annotations
from dataclasses import dataclass
from .config import KnobShaping


def lerp(low: float, high: float, x: float) -> float:
    return low + (high - low) * x


@dataclass
class Knobs:
    scene_precision: float # trust
    prior_precision: float # weight
    gain: float # amplifier 1 + gain_slope * D
    depth: int # target block/layer
    recurrence: float # bleed between frames


def knobs_from_dose(dose: float, cfg: KnobShaping) -> Knobs:
    return Knobs(
        # sensory precision falls from its ceiling at rest toward the floor at peak
        # ("stop trusting the eyes"); floor (scene_min) stays > 0 so the scene can return
        scene_precision=lerp(cfg.scene_max, cfg.scene_min, dose),
        prior_precision=lerp(cfg.prior_w_base, cfg.prior_w_min, dose) ,
        gain=1.0 + cfg.gain_slope * dose,
        depth=round(lerp(cfg.depth_shallow, cfg.depth_deep, dose)),
        recurrence=lerp(cfg.recurrence_min, cfg.recurrence_max, dose),
    ) 