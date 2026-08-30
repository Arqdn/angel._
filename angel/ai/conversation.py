"""Session memory: the running message list sent to the model.

Short-term only by design — nothing is persisted to disk. The `MemoryStore`
protocol at the bottom is the seam where optional long-term memory can be
added later without touching the conversation logic.
"""

from __future__ import annotations

import threading
from typing import Any, Protocol


class Conversation:
    """Holds system prompt + rolling turn history, trimmed to a turn budget."""

    def __init__(self, system_prompt: str, max_turns: int = 24):
        self._lock = threading.RLock()
        self._system_prompt = system_prompt
        self._max_turns = max(2, int(max_turns))
        self._messages: list[dict[str, Any]] = []

    def set_system_prompt(self, prompt: str) -> None:
        with self._lock:
            self._system_prompt = prompt

    def add_user(self, content: Any) -> None:
        """content may be a string or a multimodal content list (vision)."""
        self._append({"role": "user", "content": content})

    def add_assistant(self, message: dict[str, Any]) -> None:
        """Append the assistant message dict as returned by the API
        (may contain tool_calls)."""
        entry: dict[str, Any] = {"role": "assistant",
                                 "content": message.get("content") or ""}
        if message.get("tool_calls"):
            entry["tool_calls"] = message["tool_calls"]
        self._append(entry)

    def add_tool_result(self, tool_call_id: str, name: str, result: str) -> None:
        self._append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": result,
        })

    def _append(self, message: dict[str, Any]) -> None:
        with self._lock:
            self._messages.append(message)
            self._trim()

    def _trim(self) -> None:
        # Count user turns; drop oldest complete exchanges beyond the budget.
        while sum(1 for m in self._messages if m["role"] == "user") > self._max_turns:
            # Drop the first user turn and everything up to (not incl.) the next one.
            try:
                first_user = next(i for i, m in enumerate(self._messages)
                                  if m["role"] == "user")
                next_user = next(i for i, m in enumerate(self._messages)
                                 if m["role"] == "user" and i > first_user)
            except StopIteration:
                break
            del self._messages[first_user:next_user]

    def build_messages(self) -> list[dict[str, Any]]:
        with self._lock:
            msgs = [{"role": "system", "content": self._system_prompt}]
            msgs.extend(dict(m) for m in self._messages)
            return msgs

    def last_assistant_text(self) -> str:
        with self._lock:
            for m in reversed(self._messages):
                if m["role"] == "assistant" and isinstance(m.get("content"), str) \
                        and m["content"].strip():
                    return m["content"]
        return ""

    def drop_images(self) -> None:
        """Replace image parts with placeholders so old screenshots don't get
        re-sent (and re-billed) with every subsequent request."""
        with self._lock:
            for m in self._messages:
                content = m.get("content")
                if isinstance(content, list):
                    m["content"] = [
                        part if part.get("type") != "image_url"
                        else {"type": "text",
                              "text": "[an earlier screenshot, no longer attached]"}
                        for part in content
                    ]

    def clear(self) -> None:
        with self._lock:
            self._messages.clear()

    @property
    def turn_count(self) -> int:
        with self._lock:
            return sum(1 for m in self._messages if m["role"] == "user")


class MemoryStore(Protocol):
    """Future long-term memory backends implement this. Nothing is stored today."""

    def remember(self, fact: str) -> None: ...
    def recall(self, query: str, limit: int = 5) -> list[str]: ...
