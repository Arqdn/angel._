"""Turn model output into speakable text. Angel never reads markdown,
JSON, code, or leaked reasoning aloud."""

from __future__ import annotations

import re

_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_REASONING = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.DOTALL | re.IGNORECASE)
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_URL = re.compile(r"https?://\S+")
_HEADER = re.compile(r"^#{1,6}\s*", re.MULTILINE)
_EMPHASIS = re.compile(r"(\*{1,3}|_{1,3})(\S(?:.*?\S)?)\1")
_BULLET = re.compile(r"^\s*[-*+•]\s+", re.MULTILINE)
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+", re.MULTILINE)
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_MULTI_WS = re.compile(r"[ \t]{2,}")
_MULTI_NL = re.compile(r"\n{2,}")


def sanitize_for_speech(text: str) -> str:
    """Strip everything that would sound wrong when spoken aloud."""
    if not text:
        return ""
    out = text
    out = _REASONING.sub(" ", out)
    out = _CODE_BLOCK.sub(" I've put the code on screen. ", out)
    out = _INLINE_CODE.sub(r"\1", out)
    out = _MD_LINK.sub(r"\1", out)
    out = _URL.sub(" a web link ", out)
    out = _HEADER.sub("", out)
    for _ in range(3):  # nested emphasis like ***word***
        out = _EMPHASIS.sub(r"\2", out)
    out = _TABLE_ROW.sub("", out)
    out = _BULLET.sub("", out)
    out = _NUMBERED.sub("", out)
    out = _HTML_TAG.sub(" ", out)
    out = out.replace("#", " ").replace("~", " ")
    out = _MULTI_WS.sub(" ", out)
    out = _MULTI_NL.sub("\n", out)
    return out.strip()


_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def split_sentences(text: str, min_chars: int = 40, max_chars: int = 320) -> list[str]:
    """Split text into TTS-friendly chunks: full sentences, merged so tiny
    fragments don't cause choppy audio, split so huge ones don't stall it."""
    parts = [p.strip() for p in _SENTENCE_END.split(text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for part in parts:
        candidate = f"{current} {part}".strip() if current else part
        if len(candidate) <= max_chars:
            current = candidate
            if len(current) >= min_chars:
                chunks.append(current)
                current = ""
        else:
            if current:
                chunks.append(current)
            # Hard-split an over-long sentence on commas or spaces.
            while len(part) > max_chars:
                cut = part.rfind(",", 0, max_chars)
                if cut < max_chars // 2:
                    cut = part.rfind(" ", 0, max_chars)
                if cut <= 0:
                    cut = max_chars
                chunks.append(part[:cut].strip())
                part = part[cut:].lstrip(", ")
            current = part
    if current:
        chunks.append(current)
    return chunks
