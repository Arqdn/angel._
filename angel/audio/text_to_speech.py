"""Fish Audio text-to-speech.

API (docs.fish.audio): POST https://api.fish.audio/v1/tts with a
MessagePack-encoded body, `Authorization: Bearer <FISH_API_KEY>` and the TTS
engine chosen via the `model` HTTP header (default here: s2.1-pro-free).
The response streams audio bytes — we request WAV and start playing as soon
as the header arrives, so Angel begins speaking before synthesis finishes.

Sentence streaming: long replies are split into sentence chunks; while one
chunk plays, the next is already being synthesized.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

import requests

from angel import errors
from angel.audio.playback import AudioPlayer, WavStreamParser
from angel.audio.sanitize import sanitize_for_speech, split_sentences
from angel.settings import Settings, get_secret

log = logging.getLogger("angel.tts")


def _encode_msgpack(payload: dict) -> tuple[bytes, str]:
    try:
        import ormsgpack

        return ormsgpack.packb(payload), "application/msgpack"
    except ImportError:
        try:
            import msgpack  # type: ignore

            return msgpack.packb(payload), "application/msgpack"
        except ImportError:
            import json

            # Fish Audio accepts the same fields as JSON.
            return json.dumps(payload).encode("utf-8"), "application/json"


class FishTTS:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._executor = ThreadPoolExecutor(max_workers=1,
                                            thread_name_prefix="tts-prefetch")

    def validate_config(self) -> list[str]:
        problems = []
        if self._settings.get("tts.enabled", True) and not get_secret("FISH_API_KEY"):
            problems.append("VOICE API KEY REQUIRED")
        return problems

    @property
    def enabled(self) -> bool:
        return bool(self._settings.get("tts.enabled", True))

    def _reference_id(self) -> str | None:
        # Env var wins; else the settings file; else Fish's default voice.
        return get_secret("FISH_REFERENCE_ID") \
            or (self._settings.get("tts.reference_id") or "").strip() or None

    def _build_payload(self, text: str) -> dict:
        payload = {
            "text": text,
            "format": self._settings.get("tts.format", "wav"),
            "sample_rate": int(self._settings.get("tts.sample_rate", 44100)),
            "chunk_length": int(self._settings.get("tts.chunk_length", 200)),
            "normalize": bool(self._settings.get("tts.normalize", True)),
            "latency": self._settings.get("tts.latency", "normal"),
        }
        ref = self._reference_id()
        if ref:
            payload["reference_id"] = ref
        return payload

    def _request_stream(self, text: str) -> requests.Response:
        key = get_secret("FISH_API_KEY")
        if not key:
            raise errors.VoiceKeyError("FISH_API_KEY is not set")
        body, content_type = _encode_msgpack(self._build_payload(text))
        try:
            response = requests.post(
                self._settings.get("tts.endpoint", "https://api.fish.audio/v1/tts"),
                data=body,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": content_type,
                    "model": self._settings.get("tts.model", "s2.1-pro-free"),
                },
                stream=True,
                timeout=(10, 60),
            )
        except requests.RequestException as exc:
            raise errors.VoiceSynthesisError(f"Fish Audio unreachable: {exc}") from exc

        if response.status_code in (401, 403):
            response.close()
            raise errors.VoiceKeyError("Fish Audio rejected the API key")
        if response.status_code == 402:
            response.close()
            raise errors.VoiceKeyError("Fish Audio account has no credit")
        if response.status_code == 429:
            response.close()
            raise errors.VoiceSynthesisError("Fish Audio rate limit reached")
        if response.status_code >= 400:
            detail = ""
            try:
                detail = response.text[:200]
            except Exception:
                pass
            response.close()
            raise errors.VoiceSynthesisError(
                f"Fish Audio error {response.status_code}: {detail}")
        return response

    def _fetch_bytes(self, text: str) -> bytes:
        """Fully download one chunk's audio (used for prefetching)."""
        response = self._request_stream(text)
        try:
            return b"".join(response.iter_content(chunk_size=8192))
        finally:
            response.close()

    def speak(
        self,
        text: str,
        on_amplitude: Callable[[float], None] | None = None,
        stop_event: threading.Event | None = None,
        on_first_audio: Callable[[], None] | None = None,
    ) -> bool:
        """Blocking; returns True if anything was spoken. Raises AngelError
        kinds on configuration/API failures BEFORE audio starts; after audio
        has started, later chunk failures are logged and speech just ends."""
        speakable = sanitize_for_speech(text)
        if not speakable or not self.enabled:
            return False

        stop_event = stop_event or threading.Event()
        chunks = (split_sentences(speakable)
                  if self._settings.get("tts.sentence_streaming", True)
                  else [speakable])
        if not chunks:
            return False

        volume = float(self._settings.get("tts.volume", 0.9))
        output_device = self._settings.get("audio.output_device")
        started = False
        prefetch: Future | None = None

        for index, chunk in enumerate(chunks):
            if stop_event.is_set():
                break
            # Kick off the next chunk's synthesis before playing this one.
            next_prefetch: Future | None = None
            if index + 1 < len(chunks):
                next_chunk = chunks[index + 1]
                next_prefetch = self._executor.submit(self._fetch_bytes, next_chunk)

            try:
                if prefetch is not None:
                    audio_bytes = prefetch.result()
                    self._play_bytes(audio_bytes, volume, output_device,
                                     on_amplitude, stop_event,
                                     on_first_audio if not started else None)
                else:
                    self._play_response(self._request_stream(chunk), volume,
                                        output_device, on_amplitude, stop_event,
                                        on_first_audio if not started else None)
                started = True
            except errors.AngelError:
                if next_prefetch is not None:
                    next_prefetch.cancel()
                if not started:
                    raise
                log.warning("TTS failed mid-reply; ending speech early")
                break
            prefetch = next_prefetch
        return started

    # ---------------------------------------------------------------- playback

    def _play_response(self, response, volume, device, on_amplitude,
                       stop_event, on_first_audio) -> None:
        parser = WavStreamParser()
        player = AudioPlayer(volume=volume, output_device=device,
                             on_amplitude=on_amplitude)
        fired_first = False
        try:
            for raw in response.iter_content(chunk_size=8192):
                if stop_event.is_set():
                    player.stop()
                    break
                pcm = parser.feed(raw)
                if parser.header_parsed and player._stream is None:
                    player.open(parser.sample_rate or 44100,
                                parser.channels or 1, parser.bits or 16)
                if pcm:
                    if not fired_first and on_first_audio:
                        fired_first = True
                        on_first_audio()
                    player.feed_pcm(pcm)
        except (requests.RequestException, ValueError) as exc:
            raise errors.VoiceSynthesisError(f"TTS stream failed: {exc}") from exc
        finally:
            response.close()
            player.close()

    def _play_bytes(self, audio_bytes: bytes, volume, device, on_amplitude,
                    stop_event, on_first_audio) -> None:
        parser = WavStreamParser()
        player = AudioPlayer(volume=volume, output_device=device,
                             on_amplitude=on_amplitude)
        try:
            pcm = parser.feed(audio_bytes)
            if not parser.header_parsed:
                raise errors.VoiceSynthesisError("Malformed audio from Fish Audio")
            player.open(parser.sample_rate or 44100,
                        parser.channels or 1, parser.bits or 16)
            if on_first_audio:
                on_first_audio()
            if not stop_event.is_set():
                player.feed_pcm(pcm)
        except ValueError as exc:
            raise errors.VoiceSynthesisError(str(exc)) from exc
        finally:
            player.close()

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
