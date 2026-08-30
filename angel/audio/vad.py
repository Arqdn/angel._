"""Energy-based voice activity detection with an adaptive noise floor.

Deliberately dependency-free (pure numpy): reliable on any Windows laptop,
costs nothing on the GPU, and is easily swapped for a heavier VAD later.
"""

from __future__ import annotations

import collections
import logging
from dataclasses import dataclass, field

import numpy as np

log = logging.getLogger("angel.vad")


@dataclass
class VadConfig:
    sample_rate: int = 16000
    frame_ms: int = 30
    sensitivity: float = 0.5        # 0 (least sensitive) .. 1 (most)
    min_speech_ms: int = 250        # shorter bursts are ignored
    end_silence_ms: int = 700       # this much quiet ends an utterance
    max_utterance_s: float = 20.0
    pre_roll_ms: int = 300          # audio kept from just before speech onset

    @property
    def frame_len(self) -> int:
        return int(self.sample_rate * self.frame_ms / 1000)

    def frames(self, ms: float) -> int:
        return max(1, int(ms / self.frame_ms))


@dataclass
class Utterance:
    audio: np.ndarray  # float32 mono at sample_rate
    sample_rate: int = 16000
    duration_s: float = field(init=False)

    def __post_init__(self):
        self.duration_s = float(len(self.audio)) / float(self.sample_rate)


class SegmentDetector:
    """Feed frames in; get an Utterance back when one completes."""

    def __init__(self, config: VadConfig):
        self.cfg = config
        self._noise_floor = 0.003   # EMA of quiet-frame RMS
        self._pre_roll: collections.deque[np.ndarray] = collections.deque(
            maxlen=config.frames(config.pre_roll_ms))
        self._speech_frames: list[np.ndarray] = []
        self._in_speech = False
        self._silence_run = 0
        self._speech_run = 0
        self.level = 0.0            # last frame level 0..1 for the UI waveform

    @property
    def threshold(self) -> float:
        # Higher sensitivity → smaller multiplier → triggers on quieter speech.
        multiplier = 4.5 - 3.0 * max(0.0, min(1.0, self.cfg.sensitivity))
        return max(0.006, self._noise_floor * multiplier)

    def reset(self) -> None:
        self._speech_frames.clear()
        self._pre_roll.clear()
        self._in_speech = False
        self._silence_run = 0
        self._speech_run = 0

    def feed(self, frame: np.ndarray) -> Utterance | None:
        rms = float(np.sqrt(np.mean(np.square(frame)))) if frame.size else 0.0
        self.level = max(0.0, min(1.0, rms * 25.0))
        is_speech = rms >= self.threshold

        if not self._in_speech:
            if not is_speech:
                # Track the room's noise floor only while quiet.
                self._noise_floor = 0.95 * self._noise_floor + 0.05 * rms
                self._pre_roll.append(frame)
                self._speech_run = 0
                return None
            self._speech_run += 1
            self._pre_roll.append(frame)
            if self._speech_run >= 2:  # ~2 frames of speech = onset
                self._in_speech = True
                self._speech_frames = list(self._pre_roll)
                self._silence_run = 0
            return None

        # In speech
        self._speech_frames.append(frame)
        self._silence_run = 0 if is_speech else self._silence_run + 1

        max_frames = int(self.cfg.max_utterance_s * 1000 / self.cfg.frame_ms)
        ended = (self._silence_run >= self.cfg.frames(self.cfg.end_silence_ms)
                 or len(self._speech_frames) >= max_frames)
        if not ended:
            return None

        frames, self._speech_frames = self._speech_frames, []
        self._in_speech = False
        self._pre_roll.clear()

        audio = np.concatenate(frames) if frames else np.zeros(0, dtype=np.float32)
        speech_ms = len(audio) / self.cfg.sample_rate * 1000 \
            - self.cfg.end_silence_ms - self.cfg.pre_roll_ms
        if speech_ms < self.cfg.min_speech_ms:
            return None  # cough / click / chair creak
        return Utterance(audio=audio.astype(np.float32),
                         sample_rate=self.cfg.sample_rate)
