"""Screenshot pruning: image parts must not be re-sent forever."""

from angel.ai.conversation import Conversation


def test_drop_images_replaces_only_image_parts():
    conv = Conversation("SYS")
    conv.add_user([{"type": "text", "text": "look at this"},
                   {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAAA"}}])
    conv.add_assistant({"content": "I see a window."})
    conv.drop_images()

    user_msg = conv.build_messages()[1]
    kinds = [p["type"] for p in user_msg["content"]]
    assert kinds == ["text", "text"]
    assert user_msg["content"][0]["text"] == "look at this"
    assert "no longer attached" in user_msg["content"][1]["text"]
    # Plain-string messages untouched.
    assert conv.build_messages()[2]["content"] == "I see a window."
