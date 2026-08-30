"""Typed errors so the UI can show a specific, human message for each failure."""

from __future__ import annotations


class AngelError(Exception):
    """Base error. `ui_message` is what the UI displays; `spoken` is what Angel says."""

    ui_message = "SOMETHING WENT WRONG"
    spoken = "Something went wrong on my end."

    def __init__(self, detail: str = "", spoken: str | None = None):
        super().__init__(detail or self.ui_message)
        self.detail = detail
        if spoken:
            self.spoken = spoken


class MissingAPIKeyError(AngelError):
    ui_message = "OPENROUTER API KEY REQUIRED"
    spoken = "I need an OpenRouter API key before I can think. Add it to the dot env file."


class InvalidAPIKeyError(AngelError):
    ui_message = "OPENROUTER KEY REJECTED"
    spoken = "OpenRouter rejected the API key. It may be invalid or revoked."


class RateLimitError(AngelError):
    ui_message = "RATE LIMITED"
    spoken = "I'm being rate limited right now. Give me a moment and try again."


class ModelUnavailableError(AngelError):
    ui_message = "MODEL UNAVAILABLE"
    spoken = "My reasoning model is unavailable at the moment."


class NetworkError(AngelError):
    ui_message = "CONNECTION LOST"
    spoken = "I can't reach the network right now."


class MalformedResponseError(AngelError):
    ui_message = "ANGEL COULD NOT RESPOND"
    spoken = "I received a response I couldn't understand. Try asking again."


class VoiceKeyError(AngelError):
    ui_message = "VOICE API KEY REQUIRED"
    spoken = ""  # can't speak without a voice


class VoiceSynthesisError(AngelError):
    ui_message = "VOICE SYNTHESIS FAILED"
    spoken = ""


class MicrophoneError(AngelError):
    ui_message = "MICROPHONE UNAVAILABLE"
    spoken = "I can't hear you — no working microphone was found."


class ToolExecutionError(AngelError):
    ui_message = "ACTION FAILED"
    spoken = "That action failed."
