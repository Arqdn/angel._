"""Local speech-to-text via faster-whisper.

Runs fully offline. Defaults tuned for a laptop RTX 3060 (6 GB): base.en on
CUDA float16 uses well under 1 GB VRAM; if CUDA is missing or broken we fall
back to CPU int8 automatically.
"""

from __future__ import annotations

import logging
import threading

import numpy as np

from angel.settings import Settings

log = logging.getLogger("angel.stt")

_ALLOWED_SIZES = {"tiny", "tiny.en", "base", "base.en", "small", "small.en",
                  "medium", "medium.en", "distil-small.en", "large-v3-turbo"}


class SpeechToText:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._model = None
        self._lock = threading.Lock()
        self.device_used = "unloaded"

    def _load(self):
        from faster_whisper import WhisperModel

        size = self._settings.get("stt.model_size", "base.en")
        if size not in _ALLOWED_SIZES:
            log.warning("Unknown stt.model_size %r, using base.en", size)
            size = "base.en"

        device = self._settings.get("stt.device", "auto")
        compute = self._settings.get("stt.compute_type", "auto")
        attempts = []
        if device in ("auto", "cuda"):
            attempts.append(("cuda", "float16" if compute == "auto" else compute))
        if device in ("auto", "cpu"):
            attempts.append(("cpu", "int8" if compute == "auto" else compute))

        last_exc: Exception | None = None
        for dev, comp in attempts:
            try:
                model = WhisperModel(size, device=dev, compute_type=comp)
                self.device_used = f"{dev}/{comp}"
                log.info("faster-whisper %s loaded on %s", size, self.device_used)
                return model
            except Exception as exc:  # missing CUDA/cuDNN, OOM, bad compute type
                log.warning("STT load failed on %s/%s: %s", dev, comp, exc)
                last_exc = exc
        raise RuntimeError(f"Could not load faster-whisper: {last_exc}")

    def warm_up(self) -> None:
        """Load the model ahead of the first utterance (called off the UI thread)."""
        with self._lock:
            if self._model is None:
                self._model = self._load()

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """audio: float32 mono. Returns plain text ('' if nothing recognized)."""
        with self._lock:
            if self._model is None:
                self._model = self._load()
            model = self._model

        if sample_rate != 16000:
            # faster-whisper expects 16 kHz; simple linear resample is fine for speech.
            duration = len(audio) / sample_rate
            target_len = int(duration * 16000)
            audio = np.interp(
                np.linspace(0.0, len(audio) - 1, target_len),
                np.arange(len(audio)),
                audio,
            ).astype(np.float32)

        language = self._settings.get("stt.language") or None
        segments, _info = model.transcribe(
            audio,
            language=language,
            beam_size=int(self._settings.get("stt.beam_size", 2)),
            vad_filter=True,  # trims residual silence inside the segment
            condition_on_previous_text=False,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        log.debug("Transcribed %.1fs -> %r", len(audio) / 16000, text)
        return text
