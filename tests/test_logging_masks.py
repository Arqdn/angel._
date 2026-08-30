"""Secrets must never appear in log output."""

import logging

from angel.logging_setup import SecretMaskingFilter, mask_secret


def _filtered(msg: str, monkeypatch=None) -> str:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, msg, (), None)
    SecretMaskingFilter().filter(record)
    return record.getMessage()


def test_env_key_value_masked(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-supersecret123456")
    out = _filtered("request failed with key sk-or-v1-supersecret123456 oops")
    assert "supersecret" not in out
    assert "[masked" in out


def test_bearer_tokens_masked():
    out = _filtered("header was Authorization: Bearer abcdef1234567890")
    assert "abcdef1234567890" not in out


def test_sk_or_pattern_masked_even_if_not_in_env(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    out = _filtered("stray sk-or-v1-abcdefghijklmnop leaked")
    assert "abcdefghijklmnop" not in out


def test_plain_messages_untouched():
    assert _filtered("microphone started at 16000 Hz") == \
        "microphone started at 16000 Hz"


def test_mask_secret_display():
    assert mask_secret(None) == "(not set)"
    assert mask_secret("sk-or-v1-abcdef") == "sk-o…[masked]"
