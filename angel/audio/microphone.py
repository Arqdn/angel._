"""Microphone capture via sounddevice. Frames land on a queue; nothing ever
leaves this machine until the orchestrator decides a real request happened."""

from __future__ import annotations

import logging
import queue
from typing import Any

import numpy as np

from angel import errors
from angel.settings import Settings

log = logging.getLogger("angel.mic")


def list_input_devices() -> list[dict[str, Any]]:
    """[{index, name, default}] for the settings UI. Empty list if audio is broken."""
    try:
        import sounddevice as sd

        default_idx = sd.default.device[0]
        devices = []
        for idx, dev in enumerate(sd.query_devices()):
            if dev.get("max_input_channels", 0) > 0:
                devices.append({
                    "index": idx,
                    "name": dev.get("name", f"Device {idx}"),
                    "default": idx == default_idx,
                })
        return devices
    except Exception as exc:
        log.warning("Could not enumerate audio devices: %s", exc)
        return []


class Microphone:
    """Continuous 16 kHz mono float32 capture. Frames go to self.frames."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self.sample_rate = int(settings.get("audio.sample_rate", 16000))
        self.frame_samples = int(self.sample_rate *
                                 int(settings.get("audio.frame_ms", 30)) / 1000)
        self.frames: queue.Queue[np.ndarray] = queue.Queue(maxsize=256)
        self._stream = None

    def start(self) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:  # missing PortAudio, etc.
            raise errors.MicrophoneError(f"sounddevice unavailable: {exc}") from exc

        device = self._settings.get("audio.input_device")

        def callback(indata, _frames, _time, status):
            if status:
                log.debug("Mic status: %s", status)
            try:
                self.frames.put_nowait(indata[:, 0].copy())
            except queue.Full:
                pass  # drop; better than blocking the audio thread

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self.frame_samples,
                device=device,
                callback=callback,
            )
            self._stream.start()
        except Exception as exc:
            raise errors.MicrophoneError(f"Could not open microphone: {exc}") from exc
        log.info("Microphone started (%d Hz, %d-sample frames, device=%s)",
                 self.sample_rate, self.frame_samples, device if device is not None else "default")

    def read(self, timeout: float = 0.5) -> np.ndarray | None:
        try:
            return self.frames.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain(self) -> None:
        """Throw away anything buffered (e.g. Angel's own TTS tail)."""
        try:
            while True:
                self.frames.get_nowait()
        except queue.Empty:
            pass

    def stop(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
