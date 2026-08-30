"""Conversation memory: ordering, trimming, tool messages."""

from angel.ai.conversation import Conversation


def _conv(max_turns=3) -> Conversation:
    return Conversation("SYSTEM", max_turns=max_turns)


def test_system_prompt_first():
    conv = _conv()
    conv.add_user("hi")
    msgs = conv.build_messages()
    assert msgs[0] == {"role": "system", "content": "SYSTEM"}
    assert msgs[1]["role"] == "user"


def test_assistant_and_tool_flow():
    conv = _conv()
    conv.add_user("open chrome")
    conv.add_assistant({"content": None, "tool_calls": [
        {"id": "c1", "type": "function",
         "function": {"name": "open_application", "arguments": "{}"}}]})
    conv.add_tool_result("c1", "open_application", "launched chrome")
    conv.add_assistant({"content": "Done."})
    msgs = conv.build_messages()
    roles = [m["role"] for m in msgs]
    assert roles == ["system", "user", "assistant", "tool", "assistant"]
    assert msgs[2]["tool_calls"][0]["id"] == "c1"
    assert msgs[3]["tool_call_id"] == "c1"


def test_trimming_keeps_recent_and_complete_exchanges():
    conv = _conv(max_turns=2)
    for i in range(5):
        conv.add_user(f"question {i}")
        conv.add_assistant({"content": f"answer {i}"})
    assert conv.turn_count == 2
    msgs = conv.build_messages()
    texts = [m["content"] for m in msgs if m["role"] == "user"]
    assert texts == ["question 3", "question 4"]
    # No orphaned tool/assistant messages at the front.
    assert msgs[1]["role"] == "user"


def test_last_assistant_text_skips_tool_only_messages():
    conv = _conv()
    conv.add_user("x")
    conv.add_assistant({"content": "spoken words"})
    conv.add_assistant({"content": None, "tool_calls": [
        {"id": "a", "type": "function",
         "function": {"name": "t", "arguments": "{}"}}]})
    assert conv.last_assistant_text() == "spoken words"


def test_clear():
    conv = _conv()
    conv.add_user("x")
    conv.clear()
    assert conv.turn_count == 0
    assert len(conv.build_messages()) == 1  # just the system prompt


def test_multimodal_user_content_allowed():
    conv = _conv()
    conv.add_user([{"type": "text", "text": "look"},
                   {"type": "image_url", "image_url": {"url": "data:..."}}])
    assert isinstance(conv.build_messages()[1]["content"], list)
