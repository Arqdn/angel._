"""Qt bridge between the orchestrator (worker threads) and the QML scene.

All bridge callbacks arrive from background threads; they only emit Qt
signals, which Qt delivers to the UI thread via queued connections. No
secrets are ever exposed to QML — only settings values and status strings.
"""

from __future__ import annotations

import json
import logging

from PySide6.QtCore import Property, QObject, Signal, Slot

from angel.audio.microphone import list_input_devices
from angel.settings import Settings, get_secret

log = logging.getLogger("angel.controller")


class AngelController(QObject):
    stateChanged = Signal()
    statusChanged = Signal()
    micLevelChanged = Signal()
    voiceLevelChanged = Signal()
    userTextChanged = Signal()
    angelTextChanged = Signal()
    confirmActionChanged = Signal()
    errorTextChanged = Signal()
    setupIssuesChanged = Signal()
    settingsJsonChanged = Signal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._orchestrator = None  # set by app.py after construction
        self._state = "setup"
        self._status = ""
        self._mic_level = 0.0
        self._voice_level = 0.0
        self._user_text = ""
        self._angel_text = ""
        self._confirm_action = ""
        self._error_text = ""
        self._setup_issues: list[str] = []

    def attach_orchestrator(self, orchestrator) -> None:
        self._orchestrator = orchestrator

    # ---------------------------------------------------------------- bridge
    # Called from worker threads — only emit signals / set simple attributes.

    def on_state(self, state: str, info: str) -> None:
        self._state = state
        self.stateChanged.emit()
        if state not in ("error", "setup") and self._error_text:
            self._error_text = ""
            self.errorTextChanged.emit()

    def on_status(self, text: str) -> None:
        self._status = text
        self.statusChanged.emit()

    def on_mic_level(self, level: float) -> None:
        self._mic_level = float(level)
        self.micLevelChanged.emit()

    def on_voice_level(self, level: float) -> None:
        self._voice_level = float(level)
        self.voiceLevelChanged.emit()

    def on_user_text(self, text: str) -> None:
        self._user_text = text
        self.userTextChanged.emit()

    def on_angel_text(self, text: str) -> None:
        self._angel_text = text
        self.angelTextChanged.emit()

    def on_confirm_request(self, action: str) -> None:
        self._confirm_action = action
        self.confirmActionChanged.emit()

    def on_confirm_cleared(self) -> None:
        self._confirm_action = ""
        self.confirmActionChanged.emit()

    def on_error(self, ui_message: str) -> None:
        self._error_text = ui_message
        self.errorTextChanged.emit()

    def on_setup_issues(self, issues: list[str]) -> None:
        merged = list(dict.fromkeys(self._setup_issues + list(issues)))
        self._setup_issues = merged
        self.setupIssuesChanged.emit()

    # ------------------------------------------------------------- properties

    @Property(str, notify=stateChanged)
    def state(self) -> str:
        return self._state

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(float, notify=micLevelChanged)
    def micLevel(self) -> float:
        return self._mic_level

    @Property(float, notify=voiceLevelChanged)
    def voiceLevel(self) -> float:
        return self._voice_level

    @Property(str, notify=userTextChanged)
    def userText(self) -> str:
        return self._user_text

    @Property(str, notify=angelTextChanged)
    def angelText(self) -> str:
        return self._angel_text

    @Property(str, notify=confirmActionChanged)
    def confirmAction(self) -> str:
        return self._confirm_action

    @Property(str, notify=errorTextChanged)
    def errorText(self) -> str:
        return self._error_text

    @Property("QStringList", notify=setupIssuesChanged)
    def setupIssues(self):
        return self._setup_issues

    @Property(str, notify=settingsJsonChanged)
    def settingsJson(self) -> str:
        """Whitelisted, secret-free settings snapshot for the settings panel."""
        s = self._settings
        payload = {
            "tts.reference_id": s.get("tts.reference_id", ""),
            "tts.volume": s.get("tts.volume", 0.9),
            "tts.enabled": s.get("tts.enabled", True),
            "audio.input_device": s.get("audio.input_device"),
            "audio.vad_sensitivity": s.get("audio.vad_sensitivity", 0.5),
            "wake.enabled": s.get("wake.enabled", True),
            "wake.push_to_talk_enabled": s.get("wake.push_to_talk_enabled", True),
            "personality.intensity": s.get("personality.intensity", 0.7),
            "personality.verbosity": s.get("personality.verbosity", "balanced"),
            "safety.require_confirmation": s.get("safety.require_confirmation", True),
            "ui.fullscreen": s.get("ui.fullscreen", True),
            "ui.show_conversation": s.get("ui.show_conversation", True),
            "ui.particle_density": s.get("ui.particle_density", 1.0),
            "ui.reduce_motion": s.get("ui.reduce_motion", False),
            "app.auto_start": s.get("app.auto_start", False),
            "keys.openrouter": bool(get_secret("OPENROUTER_API_KEY")),
            "keys.fish": bool(get_secret("FISH_API_KEY")),
        }
        return json.dumps(payload)

    @Property("QVariantList", constant=True)
    def micDevices(self):
        return [{"index": d["index"], "name": d["name"], "default": d["default"]}
                for d in list_input_devices()]

    # ------------------------------------------------------------------ slots

    @Slot()
    def pushToTalk(self) -> None:
        if self._orchestrator:
            self._orchestrator.request_push_to_talk()

    @Slot(bool)
    def resolveConfirmation(self, approved: bool) -> None:
        if self._orchestrator:
            self._orchestrator.resolve_confirmation(bool(approved))

    @Slot(str)
    def submitTypedRequest(self, text: str) -> None:
        text = (text or "").strip()
        if text and self._orchestrator:
            self._orchestrator.submit_text_request(text)

    @Slot(str)
    def saveSettings(self, changes_json: str) -> None:
        """QML sends {'tts.volume': 0.8, ...}. Values are validated per key."""
        try:
            changes = json.loads(changes_json)
        except json.JSONDecodeError:
            log.warning("Bad settings payload from UI")
            return
        allowed_prefixes = ("tts.", "audio.", "wake.", "personality.",
                            "safety.", "ui.", "app.")
        cleaned = {k: v for k, v in changes.items()
                   if isinstance(k, str) and k.startswith(allowed_prefixes)}
        if not cleaned:
            return
        self._settings.update_many(cleaned)
        self._settings.save()
        if "app.auto_start" in cleaned:
            self._apply_autostart(bool(cleaned["app.auto_start"]))
        self.settingsJsonChanged.emit()
        # Refresh the system prompt so personality changes apply immediately.
        if self._orchestrator:
            from angel.ai.prompts import build_system_prompt

            self._orchestrator.conversation.set_system_prompt(
                build_system_prompt(self._settings))

    def _apply_autostart(self, enable: bool) -> None:
        """Create/remove a launcher in the user's Startup folder (Windows)."""
        import os
        import sys

        if sys.platform != "win32":
            return
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return
        from pathlib import Path

        from angel import paths

        startup = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" \
            / "Programs" / "Startup"
        shortcut = startup / "Angel.bat"
        try:
            if enable:
                launcher = paths.writable_root() / "run_angel.bat"
                shortcut.write_text(
                    f'@echo off\nstart "" /min "{launcher}"\n', encoding="utf-8")
                log.info("Auto-start enabled")
            elif shortcut.exists():
                shortcut.unlink()
                log.info("Auto-start disabled")
        except OSError as exc:
            log.warning("Could not update auto-start: %s", exc)

    @Slot()
    def quitAngel(self) -> None:
        from PySide6.QtCore import QCoreApplication

        if self._orchestrator:
            self._orchestrator.stop()
        QCoreApplication.quit()
