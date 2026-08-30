"""OpenRouter client (OpenAI-compatible) with typed error mapping.

Primary model: stealth/ox-alpha (tool calling + vision, per its OpenRouter page).
Optionally falls back to a local OpenAI-compatible server (Ollama / LM Studio)
when OpenRouter is unreachable and the fallback is enabled in settings.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from angel import errors
from angel.settings import Settings, get_secret

log = logging.getLogger("angel.llm")

_APP_HEADERS = {
    # OpenRouter attribution headers (optional but recommended by their docs).
    "HTTP-Referer": "https://github.com/arqdn/angel",
    "X-Title": "Angel Desktop Assistant",
}


class OpenRouterClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = None  # lazy: importing openai is not free

    # ------------------------------------------------------------------ config

    def validate_config(self) -> list[str]:
        """Returns a list of human-readable setup problems (empty = good)."""
        problems = []
        if not get_secret("OPENROUTER_API_KEY"):
            problems.append("OPENROUTER API KEY REQUIRED")
        return problems

    def _get_client(self):
        if self._client is None:
            key = get_secret("OPENROUTER_API_KEY")
            if not key:
                raise errors.MissingAPIKeyError("OPENROUTER_API_KEY is not set")
            from openai import OpenAI

            self._client = OpenAI(
                api_key=key,
                base_url=self._settings.get("llm.base_url",
                                            "https://openrouter.ai/api/v1"),
                default_headers=_APP_HEADERS,
                timeout=float(self._settings.get("llm.request_timeout_seconds", 90)),
                max_retries=1,
            )
        return self._client

    # -------------------------------------------------------------------- chat

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """One completion round. Returns the assistant message as a plain dict:
        {"content": str|None, "tool_calls": [...]|None}. Raises AngelError kinds."""
        try:
            return self._chat_once(self._get_client(), messages, tools,
                                   model or self._settings.get("llm.model"))
        except errors.NetworkError:
            if self._settings.get("llm.local_fallback.enabled", False):
                return self._chat_local_fallback(messages, tools)
            raise

    def _chat_once(self, client, messages, tools, model) -> dict[str, Any]:
        import openai as openai_mod

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": float(self._settings.get("llm.temperature", 0.7)),
            "max_tokens": int(self._settings.get("llm.max_tokens", 1024)),
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        effort = self._settings.get("llm.reasoning_effort")
        if effort:
            # OpenRouter reasoning control; harmless if the model ignores it.
            kwargs["extra_body"] = {"reasoning": {"effort": effort}}

        try:
            response = client.chat.completions.create(**kwargs)
        except openai_mod.AuthenticationError as exc:
            raise errors.InvalidAPIKeyError(str(exc)) from exc
        except openai_mod.PermissionDeniedError as exc:
            raise errors.InvalidAPIKeyError(str(exc)) from exc
        except openai_mod.RateLimitError as exc:
            raise errors.RateLimitError(str(exc)) from exc
        except openai_mod.NotFoundError as exc:
            raise errors.ModelUnavailableError(str(exc)) from exc
        except (openai_mod.APIConnectionError, openai_mod.APITimeoutError) as exc:
            raise errors.NetworkError(str(exc)) from exc
        except openai_mod.InternalServerError as exc:
            raise errors.ModelUnavailableError(str(exc)) from exc
        except openai_mod.APIStatusError as exc:
            raise errors.ModelUnavailableError(str(exc)) from exc

        try:
            choice = response.choices[0]
            message = choice.message
            result: dict[str, Any] = {"content": message.content}
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in message.tool_calls
                ]
            return result
        except (AttributeError, IndexError, TypeError) as exc:
            raise errors.MalformedResponseError(f"Unexpected response shape: {exc}") from exc

    def _chat_local_fallback(self, messages, tools) -> dict[str, Any]:
        """Best-effort offline path via a local OpenAI-compatible server."""
        log.warning("OpenRouter unreachable — trying local fallback model")
        from openai import OpenAI

        local = OpenAI(
            api_key="local",
            base_url=self._settings.get("llm.local_fallback.base_url",
                                        "http://localhost:11434/v1"),
            timeout=60.0,
            max_retries=0,
        )
        try:
            return self._chat_once(
                local, messages, tools,
                self._settings.get("llm.local_fallback.model", "qwen3:4b"))
        except errors.AngelError as exc:
            # Surface the ORIGINAL problem class: the network is down.
            raise errors.NetworkError(
                f"OpenRouter unreachable and local fallback failed: {exc.detail}"
            ) from exc


# ----------------------------------------------------------------- vision utils

def image_file_to_content_part(path: str | Path, max_side: int = 1568) -> dict[str, Any]:
    """Encode a screenshot for the model, downscaled to keep tokens sane."""
    from io import BytesIO

    from PIL import Image

    with Image.open(path) as img:
        img = img.convert("RGB")
        if max(img.size) > max_side:
            ratio = max_side / max(img.size)
            img = img.resize((max(1, int(img.width * ratio)),
                              max(1, int(img.height * ratio))))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=82)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return {"type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
