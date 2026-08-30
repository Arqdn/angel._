"""End-to-end request pipeline with mocked LLM + TTS (no audio hardware).

Proves: request → agent loop → tool execution → confirmation gating →
tool results fed back → final prose reply → spoken → state returns to IDLE.
"""

import threading
import time
from unittest.mock import MagicMock

import pytest

from angel.orchestrator import Orchestrator
from angel.state import AngelState


class RecordingBridge:
    def __init__(self):
        self.states: list[str] = []
        self.user_texts: list[str] = []
        self.angel_texts: list[str] = []
        self.errors: list[str] = []
        self.confirm_requests: list[str] = []
        self.setup_issues: list[list[str]] = []

    def on_state(self, state, info):
        self.states.append(state)

    def on_status(self, text):
        pass

    def on_mic_level(self, level):
        pass

    def on_voice_level(self, level):
        pass

    def on_user_text(self, text):
        self.user_texts.append(text)

    def on_angel_text(self, text):
        self.angel_texts.append(text)

    def on_confirm_request(self, action):
        self.confirm_requests.append(action)

    def on_confirm_cleared(self):
        pass

    def on_error(self, msg):
        self.errors.append(msg)

    def on_setup_issues(self, issues):
        self.setup_issues.append(list(issues))


@pytest.fixture()
def orch(settings, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.delenv("FISH_API_KEY", raising=False)
    settings.set("tts.enabled", False)  # no audio hardware in tests
    bridge = RecordingBridge()
    orchestrator = Orchestrator(settings, bridge)
    orchestrator.state.transition(AngelState.IDLE)
    return orchestrator, bridge


def test_plain_question_flow(orch):
    orchestrator, bridge = orch
    orchestrator.client.chat = MagicMock(
        return_value={"content": "It is a fine day."})

    orchestrator._handle_request("how are you")

    assert bridge.user_texts == ["how are you"]
    assert bridge.angel_texts == ["It is a fine day."]
    assert bridge.errors == []
    assert orchestrator.state.state == AngelState.IDLE
    assert "thinking" in bridge.states and "speaking" in bridge.states
    # Conversation remembered both sides.
    msgs = orchestrator.conversation.build_messages()
    assert msgs[-1]["content"] == "It is a fine day."


def test_tool_round_trip(orch):
    orchestrator, bridge = orch
    tool_reply = {
        "content": None,
        "tool_calls": [{"id": "c1", "type": "function",
                        "function": {"name": "get_time", "arguments": "{}"}}],
    }
    final_reply = {"content": "The clock has spoken."}
    orchestrator.client.chat = MagicMock(side_effect=[tool_reply, final_reply])

    orchestrator._handle_request("what time is it")

    assert bridge.angel_texts == ["The clock has spoken."]
    assert orchestrator.client.chat.call_count == 2
    # The tool result was actually fed back to the model.
    second_call_messages = orchestrator.client.chat.call_args_list[1].args[0]
    tool_msgs = [m for m in second_call_messages if m["role"] == "tool"]
    assert len(tool_msgs) == 1 and "It is" in tool_msgs[0]["content"]
    assert orchestrator.state.state == AngelState.IDLE


def test_dangerous_tool_denied_by_user(orch):
    orchestrator, bridge = orch
    tool_reply = {
        "content": None,
        "tool_calls": [{"id": "c1", "type": "function",
                        "function": {"name": "shutdown_computer",
                                     "arguments": "{}"}}],
    }
    final_reply = {"content": "Understood — I won't."}
    orchestrator.client.chat = MagicMock(side_effect=[tool_reply, final_reply])

    # Answer the confirmation "no" from another thread, like the UI would.
    def deny():
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if bridge.confirm_requests:
                orchestrator.resolve_confirmation(False)
                return
            time.sleep(0.02)

    denier = threading.Thread(target=deny, daemon=True)
    denier.start()
    orchestrator._handle_request("shut down my pc")
    denier.join(timeout=6)

    assert bridge.confirm_requests == ["shut down this computer"]
    second_call_messages = orchestrator.client.chat.call_args_list[1].args[0]
    tool_msgs = [m for m in second_call_messages if m["role"] == "tool"]
    assert "DENIED" in tool_msgs[0]["content"]
    assert orchestrator.state.state == AngelState.IDLE


def test_llm_error_surfaces_and_recovers(orch, monkeypatch):
    from angel import errors

    orchestrator, bridge = orch
    monkeypatch.setattr(time, "sleep", lambda s: None)  # skip the error dwell
    orchestrator.client.chat = MagicMock(
        side_effect=errors.NetworkError("proxy down"))

    orchestrator._handle_request("hello?")

    assert bridge.errors == ["CONNECTION LOST"]
    assert bridge.angel_texts == []
    assert orchestrator.state.state == AngelState.IDLE


def test_bad_tool_args_reported_not_crashed(orch):
    orchestrator, bridge = orch
    tool_reply = {
        "content": None,
        "tool_calls": [{"id": "c1", "type": "function",
                        "function": {"name": "set_volume",
                                     "arguments": '{"level": "loud"}'}}],
    }
    final_reply = {"content": "That volume made no sense to me."}
    orchestrator.client.chat = MagicMock(side_effect=[tool_reply, final_reply])

    orchestrator._handle_request("crank it to loud")

    second_call_messages = orchestrator.client.chat.call_args_list[1].args[0]
    tool_msgs = [m for m in second_call_messages if m["role"] == "tool"]
    assert "ERROR" in tool_msgs[0]["content"]
    assert bridge.errors == []
    assert orchestrator.state.state == AngelState.IDLE


def test_tool_iteration_cap(orch, settings):
    orchestrator, bridge = orch
    settings.set("llm.max_tool_iterations", 3)
    endless = {
        "content": None,
        "tool_calls": [{"id": "cx", "type": "function",
                        "function": {"name": "get_time", "arguments": "{}"}}],
    }
    orchestrator.client.chat = MagicMock(return_value=endless)

    orchestrator._handle_request("loop forever")

    assert orchestrator.client.chat.call_count == 3
    assert orchestrator.state.state == AngelState.IDLE
    assert bridge.angel_texts  # the fallback "stopped before finishing" line
