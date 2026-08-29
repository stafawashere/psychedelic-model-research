"""Are there entities in a rendered trip?

There is no face detector in this environment and the no-new-dependencies policy stands, so this
uses the two readouts that already exist:

1. **Semantic** — BLIP's own description of each frame. If a frame contains a figure, the caption is
   where it shows up ("a person", "a bird", "a man standing"). This is the same instrument the
   recaption loop uses, so it costs nothing extra on runs that already logged `captions.tsv`.
2. **Structural** — figures are large, coherent, low-frequency blobs, unlike the ~24px cell field.
   Low-frequency energy share is a weak proxy but it is objective, and it distinguishes "the frame
   is a lattice" from "the frame has big object-scale structure in it".

Neither is proof. A caption saying "a person" means BLIP found the frame person-like, NOT that a
recognizable figure is there — BLIP hallucinates on abstract input. **Both are screens: a positive
means LOOK at the frame, never report an entity on a caption alone.**

Run:  .venv/bin/python tests/check_entities.py [output/latest]
"""
from __future__ import annotations
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from tests.geometry_score import _gray, _radius  # noqa: E402

# words that would indicate a figure. deliberately broad: this is a screen, not a classifier.
ENTITY_WORDS = frozenset({
    "person", "people", "man", "men", "woman", "women", "girl", "boy", "child", "children",
    "face", "faces", "head", "figure", "figures", "human", "humans", "someone", "somebody",
    "creature", "creatures", "animal", "animals", "bird", "birds", "dog", "dogs", "cat", "cats",
    "alien", "aliens", "monster", "angel", "statue", "portrait", "silhouette", "body",
})
LOWFREQ_WAVELENGTH = 64.0  # px; figure-scale structure sits well below the 24px cell fundamental


def lowfreq_share(im: Image.Image) -> float:
    """Fraction of spectral power at wavelengths longer than LOWFREQ_WAVELENGTH."""
    g = _gray(im)
    power = np.abs(np.fft.fftshift(np.fft.fft2(g - g.mean()))) ** 2
    radius = _radius(power.shape)
    cutoff = power.shape[0] / LOWFREQ_WAVELENGTH
    low = power[(radius > 0) & (radius <= cutoff)].sum()
    total = power[radius > 0].sum()
    return float(low / max(total, 1e-9))


def entity_words_in(text: str) -> list[str]:
    tokens = re.findall(r"[a-z]+", text.lower())
    return sorted({t for t in tokens if t in ENTITY_WORDS})


def main(argv: list[str]) -> None:
    run_dir = argv[0] if argv else "output/latest"
    frame_dir = os.path.join(run_dir, "frames")
    if not os.path.isdir(frame_dir):
        raise SystemExit(f"no frames at {frame_dir!r}")

    captions = {}
    caption_path = os.path.join(run_dir, "captions.tsv")
    if os.path.exists(caption_path):
        with open(caption_path) as handle:
            next(handle, None)
            for line in handle:
                if "\t" in line:
                    idx, text = line.rstrip("\n").split("\t", 1)
                    captions[int(idx)] = text
    print(f"{run_dir}: {len(captions)} logged captions")

    hits = []
    for idx in sorted(captions):
        words = entity_words_in(captions[idx])
        if words:
            hits.append((idx, words, captions[idx]))

    print(f"\n== semantic screen ==")
    if hits:
        print(f"{len(hits)}/{len(captions)} captions name a figure:")
        for idx, words, text in hits:
            print(f"  fr {idx:>4d}  {','.join(words):<22s} {text!r}")
    else:
        print("no caption names a figure")

    files = sorted(f for f in os.listdir(frame_dir) if f.endswith(".png"))
    shares = np.array([lowfreq_share(Image.open(os.path.join(frame_dir, f))) for f in files])
    print(f"\n== structural screen (power at wavelengths > {LOWFREQ_WAVELENGTH:.0f}px) ==")
    print(f"mean {shares.mean():.3f}  min {shares.min():.3f}  max {shares.max():.3f} "
          f"(frame {files[int(shares.argmax())]})")
    top = np.argsort(shares)[-5:][::-1]
    print("most object-scale frames: " + ", ".join(f"{files[k]} ({shares[k]:.3f})" for k in top))

    print(f"\nVERDICT: {'candidate frames exist — LOOK at them before claiming anything' if hits else 'no semantic entity signal'}")
    print("Neither screen is proof. BLIP hallucinates figures on abstract input; a caption is a "
          "reason to look, never a finding.")


if __name__ == "__main__":
    main(sys.argv[1:])
