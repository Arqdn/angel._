"""The conductor: microphone → VAD → wake word → STT → Ox Alpha (+tools) → TTS.

Runs entirely on background threads; talks to the UI only through the
AngelBridge callback interface (implemented by the Qt controller), so the UI
thread never blocks on audio or network.

Privacy invariant: audio is processed locally (VAD + faster-whisper). Nothing
is sent to OpenRouter until a wake word or push-to-talk produced an actual
request. Screenshots are captured only when the model calls take_screenshot.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any, Protocol

from angel import errors, paths
from angel.ai.conversation import Conversation
from angel.ai.openrouter_client import OpenRouterClient, image_file_to_content_part
from angel.ai.prompts import build_system_prompt
from angel.audio.microphone import Microphone
from angel.audio.playback import play_wav_file
from angel.audio.sanitize import sanitize_for_speech
from angel.audio.speech_to_text import SpeechToText
from angel.audio.text_to_speech import FishTTS
from angel.audio.vad import SegmentDetector, VadConfig
from angel.settings import Settings
from angel.state import AngelState, StateMachine
from angel.tools.builtin import build_registry
from angel.tools.registry import ToolRegistry

log = logging.getLogger("angel.orchestrator")

_PUNCT = re.compile(r"[^\w\s]")
_YES = {"yes", "yeah", "yep", "sure", "confirm", "confirmed", "do it", "go ahead",
        "affirmative", "please do", "ok", "okay", "proceed"}
_NO = {"no", "nope", "cancel", "stop", "don't", "dont", "never mind", "nevermind",
       "abort", "negative", "deny"}


class AngelBridge(Protocol):
    """Implemented by the Qt controller; every call may come from a worker thread."""

    def on_state(self, state: str, info: str) -> None: ...
    def on_status(self, text: str) -> None: ...
    def on_mic_level(self, level: float) -> None: ...
    def on_voice_level(self, level: float) -> None: ...
    def on_user_text(self, text: str) -> None: ...
    def on_angel_text(self, text: str) -> None: ...
    def on_confirm_request(self, action: str) -> None: ...
    def on_confirm_cleared(self) -> None: ...
    def on_error(self, ui_message: str) -> None: ...
    def on_setup_issues(self, issues: list[str]) -> None: ...


class Orchestrator:
    def __init__(self, settings: Settings, bridge: AngelBridge):
        self.settings = settings
        self.bridge = bridge
        self.state = StateMachine()
        self.state.add_listener(lambda s, info: bridge.on_state(s.value, info))

        self.client = OpenRouterClient(settings)
        self.tts = FishTTS(settings)
        self.stt = SpeechToText(settings)
        self.registry: ToolRegistry = build_registry(settings)
        self.conversation = Conversation(
            build_system_prompt(settings),
            max_turns=int(settings.get("memory.max_turns", 24)),
        )

        self.mic: Microphone | None = None
        self.vad = SegmentDetector(VadConfig(
            sample_rate=int(settings.get("audio.sample_rate", 16000)),
            frame_ms=int(settings.get("audio.frame_ms", 30)),
            sensitivity=float(settings.get("audio.vad_sensitivity", 0.5)),
            min_speech_ms=int(settings.get("audio.vad_min_speech_ms", 250)),
            end_silence_ms=int(settings.get("audio.vad_end_silence_ms", 700)),
            max_utterance_s=float(settings.get("audio.vad_max_utterance_s", 20)),
            pre_roll_ms=int(settings.get("audio.vad_pre_roll_ms", 300)),
        ))

        self._stop = threading.Event()
        self._busy = threading.Lock()  # one request pipeline at a time
        self._speech_stop = threading.Event()
        self._ptt_requested = threading.Event()
        self._confirm_reply: str | None = None
        self._confirm_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_level_emit = 0.0

    # ---------------------------------------------------------------- lifecycle

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="angel-orchestrator",
                                        daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._speech_stop.set()
        self._confirm_event.set()
        if self.mic:
            self.mic.stop()
        self.tts.shutdown()

    # ------------------------------------------------------------ UI-facing API

    def request_push_to_talk(self) -> None:
        """UI key/button: stop any speech and listen right now."""
        self._speech_stop.set()
        self._ptt_requested.set()

    def resolve_confirmation(self, approved: bool) -> None:
        self._confirm_reply = "yes" if approved else "no"
        self._confirm_event.set()

    def submit_text_request(self, text: str) -> None:
        """Typed input from the UI (works even with no microphone)."""
        if self.state.state in (AngelState.IDLE, AngelState.SETUP, AngelState.ERROR):
            threading.Thread(target=self._handle_request, args=(text,),
                             daemon=True, name="angel-typed").start()

    # ------------------------------------------------------------------ helpers

    def _emit_mic_level(self) -> None:
        now = time.monotonic()
        if now - self._last_level_emit >= 0.05:
            self._last_level_emit = now
            self.bridge.on_mic_level(self.vad.level)

    def _chime(self, name: str) -> None:
        if not self.settings.get("wake.chime", True):
            return
        path = paths.ASSETS_DIR / "sounds" / f"{name}.wav"
        if path.exists():
            threading.Thread(target=play_wav_file, args=(path,),
                             kwargs={"output_device":
                                     self.settings.get("audio.output_device")},
                             daemon=True).start()

    def _wake_match(self, transcript: str) -> tuple[bool, str]:
        """Returns (woke, remaining_command)."""
        cleaned = _PUNCT.sub(" ", transcript.lower())
        words = cleaned.split()
        if not words:
            return False, ""
        aliases = {a.lower() for a in
                   (self.settings.get("wake.aliases") or ["angel"])}
        aliases.add((self.settings.get("wake.word") or "angel").lower())
        for position in range(min(3, len(words))):
            if words[position] in aliases:
                command = " ".join(words[position + 1:]).strip()
                return True, command
        return False, ""

    # ---------------------------------------------------------------- main loop

    def _run(self) -> None:
        issues = self._validate_setup()
        if issues:
            self.bridge.on_setup_issues(issues)

        # Warm the STT model off the hot path so the first wake is fast.
        threading.Thread(target=self._warm_stt, daemon=True).start()

        try:
            self.mic = Microphone(self.settings)
            self.mic.start()
        except errors.MicrophoneError as exc:
            log.error("Mic unavailable: %s", exc.detail)
            self.bridge.on_setup_issues(issues + [exc.ui_message])
            self.state.transition(AngelState.SETUP, exc.ui_message)
            self._idle_without_mic()
            return

        self.state.transition(AngelState.IDLE)
        if not issues:
            self.bridge.on_status("say “Angel” to begin")

        while not self._stop.is_set():
            try:
                self._idle_cycle()
            except errors.AngelError as exc:
                self._show_error(exc)
            except Exception:
                log.exception("Orchestrator loop error")
                self._show_error(errors.AngelError("unexpected failure"))

    def _warm_stt(self) -> None:
        try:
            self.stt.warm_up()
            self.bridge.on_status(f"hearing ready ({self.stt.device_used})")
        except Exception as exc:
            log.error("STT warm-up failed: %s", exc)
            self.bridge.on_setup_issues(["SPEECH RECOGNITION UNAVAILABLE"])

    def _idle_without_mic(self) -> None:
        """No microphone: stay alive so typed requests still work."""
        while not self._stop.is_set():
            time.sleep(0.2)

    def _idle_cycle(self) -> None:
        assert self.mic is not None
        if self._ptt_requested.is_set():
            self._ptt_requested.clear()
            self._active_listen(source="push-to-talk")
            return

        frame = self.mic.read(timeout=0.2)
        if frame is None:
            return
        self._emit_mic_level()
        utterance = self.vad.feed(frame)
        if utterance is None:
            return

        if not self.settings.get("wake.enabled", True):
            return  # wake word off: only push-to-talk listens

        transcript = self.stt.transcribe(utterance.audio, utterance.sample_rate)
        if not transcript:
            return
        woke, command = self._wake_match(transcript)
        if not woke:
            log.debug("Heard (no wake): %r", transcript)
            return

        log.info("Wake word heard")
        self._chime("wake")
        if command and len(command.split()) >= 2:
            # "Angel, open Chrome" — the request came with the wake word.
            self._handle_request(command)
        else:
            self._active_listen(source="wake")

    def _active_listen(self, source: str) -> None:
        """LISTENING: capture the next utterance and treat it as the request."""
        assert self.mic is not None
        self.state.transition(AngelState.LISTENING)
        self.bridge.on_status("listening…")
        self.mic.drain()
        self.vad.reset()
        deadline = time.monotonic() + float(
            self.settings.get("wake.follow_up_window_s", 8))

        while not self._stop.is_set() and time.monotonic() < deadline:
            frame = self.mic.read(timeout=0.2)
            if frame is None:
                continue
            self._emit_mic_level()
            utterance = self.vad.feed(frame)
            if utterance is None:
                continue
            transcript = self.stt.transcribe(utterance.audio, utterance.sample_rate)
            if transcript:
                # Saying just the wake word again shouldn't become a request.
                woke, command = self._wake_match(transcript)
                request = command if woke else transcript
                if request:
                    self._handle_request(request)
                    return
            deadline = time.monotonic() + 3.0  # brief grace after empty audio

        self.bridge.on_status("")
        self.state.transition(AngelState.IDLE, f"{source} timed out")

    # ------------------------------------------------------------- LLM handling

    def _handle_request(self, text: str) -> None:
        if not self._busy.acquire(blocking=False):
            log.info("Request ignored — already handling one")
            return
        try:
            self.bridge.on_user_text(text)
            self.bridge.on_status("")
            self.state.transition(AngelState.THINKING)
            self.conversation.add_user(text)

            try:
                reply = self._agent_loop()
            except errors.AngelError as exc:
                self._show_error(exc)
                return
            finally:
                # Keep history light: screenshots served their purpose this turn.
                self.conversation.drop_images()
                if self.mic:
                    self.mic.drain()
                self.vad.reset()

            if not reply.strip():
                self._show_error(errors.MalformedResponseError("empty reply"))
                return
            self._speak_reply(reply)
            self.state.transition(AngelState.IDLE)
        finally:
            self._busy.release()

    def _agent_loop(self) -> str:
        """Chat rounds until the model answers in prose instead of tool calls."""
        max_rounds = int(self.settings.get("llm.max_tool_iterations", 6))
        tools = self.registry.openai_tools()

        for _round in range(max_rounds):
            message = self.client.chat(self.conversation.build_messages(),
                                       tools=tools)
            self.conversation.add_assistant(message)
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return message.get("content") or ""

            pending_image: str | None = None
            for call in tool_calls:
                name = call["function"]["name"]
                args, parse_error = self.registry.parse_call_args(
                    call["function"]["arguments"])
                if parse_error:
                    self.conversation.add_tool_result(
                        call["id"], name, f"ERROR: {parse_error}")
                    continue
                result = self._execute_tool_with_safety(name, args)
                self.conversation.add_tool_result(call["id"], name,
                                                  result.for_model())
                if result.attach_image:
                    pending_image = result.attach_image

            if pending_image:
                try:
                    part = image_file_to_content_part(pending_image)
                    self.conversation.add_user([
                        {"type": "text",
                         "text": "Here is the screenshot you just captured."},
                        part,
                    ])
                except Exception as exc:
                    log.warning("Could not attach screenshot: %s", exc)
            # Back to THINKING visuals between tool rounds.
            self.state.transition(AngelState.THINKING)

        return self.conversation.last_assistant_text() or \
            "I stopped before finishing — that took more steps than I allow at once."

    def _execute_tool_with_safety(self, name: str, args: dict[str, Any]):
        from angel.tools.registry import ToolResult

        spec = self.registry.get(name)
        if spec is None:
            return ToolResult(False, f"no tool named '{name}' exists")
        needs_confirm = spec.dangerous and \
            self.settings.get("safety.require_confirmation", True)
        if needs_confirm:
            action = spec.describe_action(args)
            approved = self._ask_confirmation(action)
            if not approved:
                return ToolResult(
                    False, "the user DENIED this action; it was NOT executed. "
                           "Acknowledge and do not retry.")
        return self.registry.execute(name, args)

    # ------------------------------------------------------------- confirmation

    def _ask_confirmation(self, action: str) -> bool:
        self.state.transition(AngelState.CONFIRMING)
        self.bridge.on_confirm_request(action)
        self._confirm_reply = None
        self._confirm_event.clear()

        try:
            self._speak(f"I'm about to {action}. Should I proceed?",
                        allow_errors=False)
        except Exception:
            pass

        approved = False
        deadline = time.monotonic() + float(
            self.settings.get("safety.confirm_timeout_s", 30))
        if self.mic:
            self.mic.drain()
        self.vad.reset()

        while not self._stop.is_set() and time.monotonic() < deadline:
            if self._confirm_event.is_set():          # UI buttons
                approved = self._confirm_reply == "yes"
                break
            answer = self._listen_for_confirmation()  # voice
            if answer is not None:
                approved = answer
                break

        self.bridge.on_confirm_cleared()
        self.state.transition(AngelState.THINKING)
        log.info("Confirmation for %r -> %s", action,
                 "approved" if approved else "denied")
        return approved

    def _listen_for_confirmation(self) -> bool | None:
        if not self.mic:
            time.sleep(0.1)
            return None
        frame = self.mic.read(timeout=0.2)
        if frame is None:
            return None
        self._emit_mic_level()
        utterance = self.vad.feed(frame)
        if utterance is None:
            return None
        transcript = self.stt.transcribe(utterance.audio, utterance.sample_rate)
        if not transcript:
            return None
        cleaned = _PUNCT.sub(" ", transcript.lower()).strip()
        words = set(cleaned.split())
        if words & {w for phrase in _NO for w in phrase.split()} or cleaned in _NO:
            return False
        if words & {w for phrase in _YES for w in phrase.split()} or cleaned in _YES:
            return True
        return None  # unclear — keep waiting until timeout

    # ------------------------------------------------------------------- speech

    def _speak_reply(self, reply: str) -> None:
        display_text = sanitize_for_speech(reply)
        self.bridge.on_angel_text(display_text or reply)
        self._speak(reply, allow_errors=True)

    def _speak(self, text: str, allow_errors: bool) -> None:
        self._speech_stop.clear()
        previous = self.state.state
        self.state.transition(AngelState.SPEAKING)
        try:
            spoke = self.tts.speak(
                text,
                on_amplitude=self.bridge.on_voice_level,
                stop_event=self._speech_stop,
            )
            if not spoke:
                log.info("TTS produced no audio (disabled or empty text)")
        except errors.AngelError as exc:
            if allow_errors:
                # The reply is already on screen; report the voice problem quietly.
                self.bridge.on_error(exc.ui_message)
                log.error("TTS failed: %s", exc.detail)
            else:
                raise
        finally:
            self.bridge.on_voice_level(0.0)
            if self.mic:
                self.mic.drain()
            self.vad.reset()
            if self.state.state == AngelState.SPEAKING and previous == AngelState.CONFIRMING:
                self.state.transition(AngelState.CONFIRMING)

    # -------------------------------------------------------------------- misc

    def _validate_setup(self) -> list[str]:
        issues = []
        issues.extend(self.client.validate_config())
        issues.extend(self.tts.validate_config())
        return issues

    def _show_error(self, exc: errors.AngelError) -> None:
        log.error("Error: %s (%s)", exc.ui_message, exc.detail)
        self.bridge.on_error(exc.ui_message)
        self.state.transition(AngelState.ERROR, exc.ui_message)
        if exc.spoken and not isinstance(exc, (errors.VoiceKeyError,
                                               errors.VoiceSynthesisError)):
            try:
                self.tts.speak(exc.spoken, on_amplitude=self.bridge.on_voice_level,
                               stop_event=self._speech_stop)
            except errors.AngelError:
                pass
            finally:
                self.bridge.on_voice_level(0.0)
        time.sleep(2.5)
        if self.mic:
            self.mic.drain()
        self.vad.reset()
        self.state.transition(AngelState.IDLE)
