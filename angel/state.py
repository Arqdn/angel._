"""Angel's state machine. Every subsystem reports through here; the UI mirrors it."""

from __future__ import annotations

import enum
import logging
import threading
from typing import Callable

log = logging.getLogger("angel.state")


class AngelState(str, enum.Enum):
    SETUP = "setup"          # first-run problems (missing key, no mic…)
    IDLE = "idle"            # waiting for the wake word
    LISTENING = "listening"  # actively capturing a request
    THINKING = "thinking"    # waiting on the model / running tools
    SPEAKING = "speaking"    # TTS playing
    CONFIRMING = "confirming"  # dangerous action awaiting yes/no
    ERROR = "error"          # a failure the user must see


# Legal transitions. ERROR and SETUP are reachable from anywhere.
_TRANSITIONS: dict[AngelState, set[AngelState]] = {
    AngelState.SETUP: {AngelState.IDLE},
    AngelState.IDLE: {AngelState.LISTENING, AngelState.THINKING},
    AngelState.LISTENING: {AngelState.THINKING, AngelState.IDLE},
    AngelState.THINKING: {AngelState.SPEAKING, AngelState.CONFIRMING, AngelState.IDLE},
    AngelState.SPEAKING: {AngelState.IDLE, AngelState.LISTENING, AngelState.THINKING,
                          AngelState.CONFIRMING},
    AngelState.CONFIRMING: {AngelState.THINKING, AngelState.SPEAKING, AngelState.IDLE},
    AngelState.ERROR: {AngelState.IDLE, AngelState.LISTENING},
}


class StateMachine:
    """Thread-safe; listeners get (new_state, info_text)."""

    def __init__(self, initial: AngelState = AngelState.SETUP):
        self._state = initial
        self._lock = threading.RLock()
        self._listeners: list[Callable[[AngelState, str], None]] = []

    @property
    def state(self) -> AngelState:
        with self._lock:
            return self._state

    def add_listener(self, fn: Callable[[AngelState, str], None]) -> None:
        self._listeners.append(fn)

    def can_transition(self, target: AngelState) -> bool:
        with self._lock:
            if target in (AngelState.ERROR, AngelState.SETUP) or target == self._state:
                return True
            return target in _TRANSITIONS.get(self._state, set())

    def transition(self, target: AngelState, info: str = "") -> bool:
        with self._lock:
            if not self.can_transition(target):
                log.warning("Illegal transition %s -> %s ignored", self._state, target)
                return False
            previous, self._state = self._state, target
        if previous != target:
            log.info("State %s -> %s %s", previous.value, target.value,
                     f"({info})" if info else "")
        for fn in list(self._listeners):
            try:
                fn(target, info)
            except Exception:
                log.exception("State listener failed")
        return True
