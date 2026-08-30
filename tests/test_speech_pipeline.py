"""Sanitizer, sentence chunking, wake-word matching, Fish TTS payload, WAV parser."""

import struct

import numpy as np
import pytest

from angel.audio.playback import WavStreamParser
from angel.audio.sanitize import sanitize_for_speech, split_sentences
from angel.audio.text_to_speech import FishTTS, _encode_msgpack


# ---------------------------------------------------------------- sanitizer

def test_strips_markdown():
    text = ("# Header\n**bold** and *italic* and `code`\n"
            "- bullet one\n1. numbered\n[link](https://x.com)\n"
            "```python\nprint('hi')\n```\n| a | b |\n")
    out = sanitize_for_speech(text)
    assert "#" not in out and "*" not in out and "`" not in out
    assert "https://" not in out and "|" not in out
    assert "bold" in out and "italic" in out and "link" in out


def test_strips_leaked_reasoning():
    out = sanitize_for_speech("<think>secret chain of thought</think>The answer is four.")
    assert "secret" not in out
    assert "answer is four" in out


def test_code_block_replaced_with_notice():
    out = sanitize_for_speech("Here:\n```js\nlet x = 1\n```")
    assert "let x" not in out
    assert "code" in out.lower()


def test_plain_text_untouched():
    assert sanitize_for_speech("Hello there, friend.") == "Hello there, friend."


# ----------------------------------------------------------------- chunking

def test_split_sentences_merges_short_and_splits_long():
    chunks = split_sentences("Yes. No. Maybe so, I think that could be true today.")
    assert all(len(c) <= 320 for c in chunks)
    assert " ".join(chunks).startswith("Yes.")

    long_sentence = "word " * 200
    chunks = split_sentences(long_sentence.strip())
    assert all(len(c) <= 320 for c in chunks)
    assert len(chunks) >= 3


def test_split_sentences_empty():
    assert split_sentences("") == []


# --------------------------------------------------------------- wake word

def _orchestrator_wake(settings):
    """Test the matcher without building the full orchestrator."""
    from angel.orchestrator import Orchestrator

    matcher = Orchestrator.__new__(Orchestrator)  # skip __init__ (no audio here)
    matcher.settings = settings
    return matcher


def test_wake_word_variants(settings):
    orch = _orchestrator_wake(settings)
    assert orch._wake_match("Angel") == (True, "")
    assert orch._wake_match("angel, open chrome") == (True, "open chrome")
    assert orch._wake_match("Hey Angel what time is it") == (True, "what time is it")
    assert orch._wake_match("Angle open notepad")[0] is True  # whisper misspelling
    assert orch._wake_match("the angels sang")[1] == "sang"


def test_wake_word_not_matched_mid_sentence(settings):
    orch = _orchestrator_wake(settings)
    woke, _ = orch._wake_match("I was talking about my guardian angel yesterday")
    assert woke is False
    assert orch._wake_match("open chrome please") == (False, "")


# ------------------------------------------------------------- fish payload

def test_fish_payload_fields(settings, monkeypatch):
    monkeypatch.setenv("FISH_API_KEY", "fk-test")
    monkeypatch.delenv("FISH_REFERENCE_ID", raising=False)
    tts = FishTTS(settings)
    payload = tts._build_payload("Hello world")
    assert payload["text"] == "Hello world"
    assert payload["format"] == "wav"
    assert payload["sample_rate"] == 44100
    assert "reference_id" not in payload  # empty means Fish default voice

    settings.set("tts.reference_id", "my-male-voice")
    assert tts._build_payload("x")["reference_id"] == "my-male-voice"


def test_fish_env_reference_overrides_settings(settings, monkeypatch):
    monkeypatch.setenv("FISH_REFERENCE_ID", "env-voice")
    settings.set("tts.reference_id", "file-voice")
    assert FishTTS(settings)._build_payload("x")["reference_id"] == "env-voice"


def test_msgpack_roundtrip():
    body, content_type = _encode_msgpack({"text": "hi", "n": 3})
    assert content_type == "application/msgpack"
    import ormsgpack

    assert ormsgpack.unpackb(body) == {"text": "hi", "n": 3}


def test_missing_fish_key_reported(settings, monkeypatch):
    monkeypatch.delenv("FISH_API_KEY", raising=False)
    assert FishTTS(settings).validate_config() == ["VOICE API KEY REQUIRED"]
    from angel import errors

    with pytest.raises(errors.VoiceKeyError):
        FishTTS(settings)._request_stream("hello")


# --------------------------------------------------------------- wav parser

def _wav_bytes(pcm: bytes, rate=44100, channels=1) -> bytes:
    header = (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVE"
              + b"fmt " + struct.pack("<IHHIIHH", 16, 1, channels, rate,
                                      rate * channels * 2, channels * 2, 16)
              + b"data" + struct.pack("<I", len(pcm)))
    return header + pcm


def test_wav_parser_single_feed():
    pcm = np.arange(1000, dtype="<i2").tobytes()
    parser = WavStreamParser()
    out = parser.feed(_wav_bytes(pcm))
    assert parser.header_parsed
    assert parser.sample_rate == 44100 and parser.channels == 1 and parser.bits == 16
    assert out == pcm


def test_wav_parser_dribbled_bytes():
    pcm = np.arange(500, dtype="<i2").tobytes()
    blob = _wav_bytes(pcm, rate=22050)
    parser = WavStreamParser()
    collected = b""
    for i in range(0, len(blob), 7):  # 7-byte dribbles across the header
        collected += parser.feed(blob[i:i + 7])
    assert parser.sample_rate == 22050
    assert collected == pcm


def test_wav_parser_rejects_not_wav():
    parser = WavStreamParser()
    with pytest.raises(ValueError):
        parser.feed(b"<html>error page that is definitely not audio</html>")
