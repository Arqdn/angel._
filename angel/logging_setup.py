"""Logging with secret masking. API keys must never reach a log file."""

from __future__ import annotations

import logging
import logging.handlers
import os
import re

from angel import paths

_SECRET_ENV_VARS = ("OPENROUTER_API_KEY", "FISH_API_KEY")
# Catches raw key material even if it arrives via an exception message.
_KEY_PATTERN = re.compile(r"(sk-or-[A-Za-z0-9\-_]{8,}|Bearer\s+\S{8,})")


class SecretMaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        masked = msg
        for var in _SECRET_ENV_VARS:
            value = os.environ.get(var)
            if value and len(value) >= 6 and value in masked:
                masked = masked.replace(value, value[:4] + "…[masked]")
        masked = _KEY_PATTERN.sub("[masked-credential]", masked)
        if masked != msg:
            record.msg = masked
            record.args = ()
        return True


def mask_secret(value: str | None) -> str:
    """For displaying key status: 'sk-o…[masked]' or '(not set)'."""
    if not value:
        return "(not set)"
    return value[:4] + "…[masked]"


def setup_logging(level: str = "INFO") -> logging.Logger:
    paths.ensure_runtime_dirs()
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S"
    )
    masker = SecretMaskingFilter()

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    stream.addFilter(masker)

    file_handler = logging.handlers.RotatingFileHandler(
        paths.LOGS_DIR / "angel.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.addFilter(masker)

    root.handlers.clear()
    root.addHandler(stream)
    root.addHandler(file_handler)
    # Third-party libraries are chatty at INFO.
    for noisy in ("httpx", "httpcore", "urllib3", "openai", "faster_whisper"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger("angel")
