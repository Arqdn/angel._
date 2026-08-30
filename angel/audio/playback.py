"""Streaming WAV playback with live amplitude reporting for the UI.

Fish Audio streams a WAV file; we parse its header incrementally and push PCM
to a sounddevice output stream, computing RMS per block so the QML angel can
breathe with the voice.
"""

from __future__ import annotations

import logging
import struct
import threading
from typing import Callable

import numpy as np

log = logging.getLogger("angel.playback")


class WavStreamParser:
    """Incremental RIFF/WAVE parser: feed bytes, get (fmt, pcm_bytes) out."""

    def __init__(self):
        self._buf = bytearray()
        self.channels: int | None = None
        self.sample_rate: int | None = None
        self.bits: int | None = None
        self._in_data = False

    @property
    def header_parsed(self) -> bool:
        return self._in_data

    def feed(self, chunk: bytes) -> bytes:
        """Returns raw PCM bytes ready to play (may be b'')."""
        if self._in_data:
            return chunk
        self._buf.extend(chunk)
        # Need at least the RIFF header.
        if len(self._buf) < 12 or self._buf[0:4] != b"RIFF" or self._buf[8:12] != b"WAVE":
            if len(self._buf) >= 12 and self._buf[0:4] != b"RIFF":
                raise ValueError("Not a WAV stream")
            return b""
        pos = 12
        while pos + 8 <= len(self._buf):
            cid = bytes(self._buf[pos:pos + 4])
            size = struct.unpack("<I", self._buf[pos + 4:pos + 8])[0]
            if cid == b"fmt " and pos + 8 + 16 <= len(self._buf):
                fmt = struct.unpack("<HHIIHH", self._buf[pos + 8:pos + 8 + 16])
                _audio_fmt, self.channels, self.sample_rate, _br, _ba, self.bits = fmt
            if cid == b"data":
                pcm_start = pos + 8
                pcm = bytes(self._buf[pcm_start:])
                self._buf.clear()
                self._in_data = True
                return pcm
            # Streaming responses often declare size 0xFFFFFFFF; only skip
            # complete non-data chunks.
            if pos + 8 + size + (size % 2) > len(self._buf):
                break
            pos += 8 + size + (size % 2)
        return b""


class AudioPlayer:
    """One player per spoken reply. Thread-safe stop; volume applied per-sample."""

    def __init__(self, volume: float = 0.9, output_device=None,
                 on_amplitude: Callable[[float], None] | None = None):
        self.volume = max(0.0, min(1.0, volume))
        self._device = output_device
        self._on_amplitude = on_amplitude
        self._stream = None
        self._stop = threading.Event()
        self._leftover = b""
        self._sample_width = 2
        self._channels = 1

    def stop(self) -> None:
        self._stop.set()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def open(self, sample_rate: int, channels: int, bits: int) -> None:
        import sounddevice as sd

        self._channels = max(1, channels)
        self._sample_width = max(1, bits // 8)
        if self._sample_width != 2:
            raise ValueError(f"Only 16-bit PCM supported, got {bits}-bit")
        self._stream = sd.RawOutputStream(
            samplerate=sample_rate,
            channels=self._channels,
            dtype="int16",
            device=self._device,
        )
        self._stream.start()

    def feed_pcm(self, pcm: bytes) -> None:
        """Write PCM to the device in small blocks, reporting amplitude."""
        if self._stream is None or self._stop.is_set() or not pcm:
            return
        data = self._leftover + pcm
        frame_bytes = self._sample_width * self._channels
        usable = len(data) - (len(data) % frame_bytes)
        self._leftover = data[usable:]
        data = data[:usable]

        block = 4096 * frame_bytes // 2
        for start in range(0, len(data), block):
            if self._stop.is_set():
                return
            chunk = data[start:start + block]
            samples = np.frombuffer(chunk, dtype=np.int16)
            if self.volume < 0.999:
                samples = (samples.astype(np.float32) * self.volume).astype(np.int16)
                chunk = samples.tobytes()
            if self._on_amplitude is not None and samples.size:
                rms = float(np.sqrt(np.mean(np.square(
                    samples.astype(np.float32) / 32768.0))))
                # Perceptual-ish scaling: speech RMS ~0.02-0.2
                self._on_amplitude(max(0.0, min(1.0, rms * 4.0)))
            try:
                self._stream.write(chunk)
            except Exception as exc:
                log.warning("Audio write failed: %s", exc)
                self._stop.set()
                return

    def close(self) -> None:
        if self._on_amplitude is not None:
            try:
                self._on_amplitude(0.0)
            except Exception:
                pass
        if self._stream is not None:
            try:
                if not self._stop.is_set():
                    # Let the tail of the buffer play out.
                    self._stream.stop()
                else:
                    self._stream.abort()
                self._stream.close()
            except Exception:
                pass
            self._stream = None


def play_wav_file(path, volume: float = 0.8, output_device=None) -> None:
    """Small helper for UI chimes. Fire-and-forget from a worker thread."""
    try:
        import wave

        with wave.open(str(path), "rb") as wf:
            rate, channels, width = wf.getframerate(), wf.getnchannels(), wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
        if width != 2:
            return
        player = AudioPlayer(volume=volume, output_device=output_device)
        player.open(rate, channels, 16)
        player.feed_pcm(frames)
        player.close()
    except Exception as exc:
        log.debug("Chime playback failed: %s", exc)
