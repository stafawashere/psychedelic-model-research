"""measurement probe, NOT a gate. answers one question about a rendered run: is the apex
periodic, and is it symmetric? synthetic controls run alongside so a null result is readable.

    .venv/bin/python tests/probe_apex_structure.py output/past/2026-08-29_05-31-15/frames 0 13 15

backs docs/conclusion.md section 2. no model load, no torch.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image

SIZE = 512
CONTROL_WAVELENGTH = 24


def _load_gray(frame_dir: str, index: int) -> np.ndarray:
    for name in sorted(os.listdir(frame_dir)):
        stem, ext = os.path.splitext(name)
        if ext.lower() == ".png" and stem.isdigit() and int(stem) == index:
            return np.asarray(Image.open(os.path.join(frame_dir, name)).convert("L"), dtype=np.float64) / 255.0

    raise FileNotFoundError(f"no frame {index} in {frame_dir}")


def _windowed(img: np.ndarray) -> np.ndarray:
    # hann both axes so the fft does not read the frame border as a hard edge
    vertical = np.hanning(img.shape[0])[:, None]
    horizontal = np.hanning(img.shape[1])[None, :]
    return (img - img.mean()) * vertical * horizontal


def _radial_profile(img: np.ndarray) -> np.ndarray:
    power = np.fft.fftshift(np.abs(np.fft.fft2(_windowed(img))) ** 2)
    height, width = img.shape
    center_y, center_x = height // 2, width // 2
    grid_y, grid_x = np.mgrid[0:height, 0:width]
    radius = np.sqrt((grid_y - center_y) ** 2 + (grid_x - center_x) ** 2).astype(int)

    bins = min(center_y, center_x)
    summed = np.bincount(radius.ravel(), power.ravel(), minlength=bins + 1)[:bins]
    counts = np.bincount(radius.ravel(), minlength=bins + 1)[:bins]

    return summed / np.maximum(counts, 1)


def whitened_peak(img: np.ndarray, k_lo: int = 8, k_hi: int = 140) -> tuple[float, float]:
    # natural images are 1/f^a, so a raw spectral max just finds dc. fit the trend in log-log and
    # look for a BUMP above it -- that is what a selected wavelength would look like.
    profile = _radial_profile(img)
    wavenumber = np.arange(len(profile))
    band = slice(k_lo, k_hi)

    log_k = np.log(wavenumber[band])
    log_p = np.log(profile[band] + 1e-20)
    slope, intercept = np.polyfit(log_k, log_p, 1)
    residual = log_p - (slope * log_k + intercept)

    peak = int(np.argmax(residual))
    return SIZE / wavenumber[band][peak], float(residual[peak])


def angular_anisotropy(img: np.ndarray, sectors: int = 36, r_lo: int = 8, r_hi: int = 120) -> float:
    power = np.fft.fftshift(np.abs(np.fft.fft2(_windowed(img))) ** 2)
    height, width = img.shape
    center_y, center_x = height // 2, width // 2
    grid_y, grid_x = np.mgrid[0:height, 0:width]

    radius = np.sqrt((grid_y - center_y) ** 2 + (grid_x - center_x) ** 2)
    angle = np.degrees(np.arctan2(grid_y - center_y, grid_x - center_x)) % 180
    band = (radius > r_lo) & (radius < r_hi)

    per_sector = np.array([
        power[band & (angle >= i * 180 / sectors) & (angle < (i + 1) * 180 / sectors)].mean()
        for i in range(sectors)
    ])

    return float(per_sector.max() / per_sector.min())


def _correlate(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def rotational_symmetry(img: np.ndarray, degrees: float, margin: int = 96) -> float:
    # crop the margin off both: rotation about the centre pulls undefined corners into view
    as_u8 = Image.fromarray((img * 255).astype(np.uint8))
    rotated = np.asarray(as_u8.rotate(degrees, resample=Image.BILINEAR), dtype=np.float64) / 255.0
    height, width = img.shape

    return _correlate(img[margin:height - margin, margin:width - margin],
                      rotated[margin:height - margin, margin:width - margin])


def _controls() -> list[tuple[str, np.ndarray]]:
    grid_y, grid_x = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    center = SIZE / 2
    period = CONTROL_WAVELENGTH

    lattice = (np.cos(2 * np.pi * grid_x / period)
               + np.cos(2 * np.pi * (grid_x * 0.5 + grid_y * 0.866) / period)
               + np.cos(2 * np.pi * (-grid_x * 0.5 + grid_y * 0.866) / period))
    lattice = (lattice - lattice.min()) / (lattice.max() - lattice.min())

    radius = np.sqrt((grid_x - center) ** 2 + (grid_y - center) ** 2)
    theta = np.arctan2(grid_y - center, grid_x - center)

    rings = 0.5 + 0.5 * np.cos(2 * np.pi * radius / period)
    spiral = 0.5 + 0.5 * np.cos(6 * theta + 2 * np.pi * np.log(radius + 2) / 0.35)

    return [("CONTROL hex lattice", lattice),
            ("CONTROL rings", rings),
            ("CONTROL log spiral", spiral)]


def main() -> None:
    frame_dir = sys.argv[1] if len(sys.argv) > 1 else "output/latest/frames"
    indices = [int(a) for a in sys.argv[2:]] or [0, 13, 15]

    targets = _controls() + [(f"frame {i:02d}", _load_gray(frame_dir, i)) for i in indices]

    print(f"{'image':<22}{'wavelen':>10}{'bump':>8}{'excess':>11}{'aniso':>12}{'mirLR':>8}{'rot60':>8}{'rot90':>8}")
    for name, img in targets:
        wavelength, bump = whitened_peak(img)
        print(f"{name:<22}{wavelength:>8.1f}px{bump:>8.2f}{np.exp(bump):>10.3g}x"
              f"{angular_anisotropy(img):>12.4g}{_correlate(img, img[:, ::-1]):>8.3f}"
              f"{rotational_symmetry(img, 60):>8.3f}{rotational_symmetry(img, 90):>8.3f}")

    print("\ncontrols set the dynamic range: a real form constant reads bump > 10 and/or symmetry > 0.9.")
    print("periodicity WITHOUT symmetry means a saturation texture, not a Turing pattern.")


if __name__ == "__main__":
    main()
