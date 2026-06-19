from __future__ import annotations
from config import DoseConfig
from math import exp


def dose(t_min: float, cfg: DoseConfig) -> float: # D(t) curve
    if t_min < 0: raise ValueError("t_min must be non-negative")

    approaching_peak = t_min < cfg.peak_min
    if approaching_peak:
        time_until_peak = cfg.peak_min - t_min
        exponent = -time_until_peak / cfg.rise
        return cfg.dmax * exp(exponent)

    time_since_peak = t_min - cfg.peak_min
    exponent = -time_since_peak / cfg.fall
    return cfg.dmax * exp(exponent)


def map_dose(cfg: DoseConfig) -> list[tuple[float, float]]: # [(0.0, 0.035673993347252395), (1.2, 0.09697196786440505), (2.4, 0.2635971381157267), (3.5999999999999996, 0.716531310573789), (4.8, 0.8371284313607638), (6.0, 0.6411803884299546), (7.199999999999999, 0.4910982295021552), (8.4, 0.37614605089640657), (9.6, 0.2881009197455093), (10.799999999999999, 0.22066465874200497), (12.0, 0.1690133154060661)]
    if cfg.n_frames < 2: raise ValueError("n_frames must be >= 2")

    frames = []
    minutes_between_frames = cfg.total_min / (cfg.n_frames - 1)
    for frame_index in range(cfg.n_frames):
        t_min = frame_index * minutes_between_frames
        intensity = dose(t_min, cfg)
        frames.append((t_min, intensity))

    return frames