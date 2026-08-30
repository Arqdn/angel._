"""Procedurally generate Angel's small binary assets (no copyrighted art):

  assets/angel/particle.png   soft dust mote sprite for the particle system
  assets/angel/glow.png       large radial glow sprite
  assets/angel/noise.png      tileable film-grain texture
  assets/angel/icon.ico       app icon (layered golden glow)
  assets/sounds/wake.wav      gentle two-note chime when Angel wakes
  assets/sounds/error.wav     low, soft error tone

Run once: python scripts/generate_assets.py  (outputs are committed to git,
so users never need to run this).
"""

from __future__ import annotations

import struct
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ANGEL_DIR = ROOT / "assets" / "angel"
SOUNDS_DIR = ROOT / "assets" / "sounds"


def radial(size: int, inner=(255, 250, 240), power: float = 2.2,
           alpha_max: int = 255) -> Image.Image:
    """Soft radial sprite: bright warm center fading to transparent."""
    yy, xx = np.mgrid[0:size, 0:size]
    cx = cy = (size - 1) / 2
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (size / 2)
    falloff = np.clip(1.0 - dist, 0.0, 1.0) ** power
    img = np.zeros((size, size, 4), dtype=np.uint8)
    for channel, value in enumerate(inner):
        img[..., channel] = value
    img[..., 3] = (falloff * alpha_max).astype(np.uint8)
    return Image.fromarray(img, "RGBA")


def make_particle() -> None:
    radial(48, inner=(255, 244, 224), power=2.6).save(ANGEL_DIR / "particle.png")


def make_glow() -> None:
    radial(512, inner=(255, 246, 228), power=2.0).save(ANGEL_DIR / "glow.png")


def make_noise() -> None:
    rng = np.random.default_rng(7)
    grain = rng.normal(128, 34, (256, 256)).clip(0, 255).astype(np.uint8)
    rgba = np.dstack([grain, grain, grain,
                      np.full((256, 256), 255, dtype=np.uint8)])
    Image.fromarray(rgba, "RGBA").save(ANGEL_DIR / "noise.png")


def make_icon() -> None:
    base = radial(256, inner=(240, 214, 150), power=1.6)
    core = radial(256, inner=(255, 252, 244), power=4.0)
    ring = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    yy, xx = np.mgrid[0:256, 0:256]
    dist = np.sqrt((xx - 127.5) ** 2 + (yy - 127.5) ** 2)
    band = np.exp(-((dist - 92) ** 2) / 26.0)
    ring_arr = np.zeros((256, 256, 4), dtype=np.uint8)
    ring_arr[..., 0], ring_arr[..., 1], ring_arr[..., 2] = 226, 195, 132
    ring_arr[..., 3] = (band * 200).astype(np.uint8)
    ring = Image.fromarray(ring_arr, "RGBA")
    icon = Image.alpha_composite(Image.alpha_composite(base, ring), core)
    icon.save(ANGEL_DIR / "icon.ico",
              sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
    icon.save(ANGEL_DIR / "icon.png")


def _tone(freqs_amps: list[tuple[float, float]], duration: float,
          sample_rate: int = 44100, fade: float = 0.35) -> np.ndarray:
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = np.zeros_like(t)
    for freq, amp in freqs_amps:
        signal += amp * np.sin(2 * np.pi * freq * t)
    envelope = np.minimum(1.0, t / 0.015)  # quick attack
    envelope *= np.exp(-t / fade)          # gentle decay
    return signal * envelope


def _save_wav(path: Path, signal: np.ndarray, sample_rate: int = 44100) -> None:
    signal = np.clip(signal, -1.0, 1.0)
    pcm = (signal * 32000).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def make_sounds() -> None:
    rate = 44100
    # Wake: soft bell dyad (A5 then E6), airy overtones — celestial, not "ding".
    first = _tone([(880.0, 0.30), (1760.0, 0.10), (2637.0, 0.04)], 0.9, rate, 0.30)
    second = _tone([(1318.5, 0.26), (2637.0, 0.08)], 1.1, rate, 0.40)
    wake = np.zeros(int(rate * 1.35))
    wake[:len(first)] += first
    wake[int(rate * 0.22):int(rate * 0.22) + len(second)] += second
    _save_wav(SOUNDS_DIR / "wake.wav", wake, rate)

    # Error: low soft minor second, quickly damped.
    error = _tone([(220.0, 0.32), (233.1, 0.22), (110.0, 0.10)], 0.9, rate, 0.22)
    _save_wav(SOUNDS_DIR / "error.wav", error, rate)


def main() -> int:
    ANGEL_DIR.mkdir(parents=True, exist_ok=True)
    SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
    make_particle()
    make_glow()
    make_noise()
    make_icon()
    make_sounds()
    for f in sorted(list(ANGEL_DIR.iterdir()) + list(SOUNDS_DIR.iterdir())):
        print(f"  {f.relative_to(ROOT)}  ({f.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
