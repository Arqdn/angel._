"""Tool registry: schemas, validation, enable/disable, dangerous flags."""

import json

import pytest

from angel.tools.builtin import build_registry
from angel.tools.registry import ToolRegistry, ToolResult, ToolSpec, validate_args


def _spec(**kw) -> ToolSpec:
    base = dict(
        name="demo",
        description="d",
        parameters={"level": {"type": "integer", "minimum": 0, "maximum": 100},
                    "name": {"type": "string"},
                    "mode": {"type": "string", "enum": ["a", "b"]}},
        required=["level"],
        func=lambda **kwargs: ToolResult(True, "ok"),
    )
    base.update(kw)
    return ToolSpec(**base)


def test_openai_schema_shape():
    schema = _spec().openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "demo"
    assert schema["function"]["parameters"]["required"] == ["level"]


def test_validate_missing_required():
    assert "missing required" in validate_args(_spec(), {})


def test_validate_wrong_type():
    assert "must be of type integer" in validate_args(_spec(), {"level": "50"})
    assert "must be an integer" in validate_args(_spec(), {"level": True})


def test_validate_range_and_enum():
    assert "must be <= 100" in validate_args(_spec(), {"level": 200})
    assert "one of" in validate_args(_spec(), {"level": 5, "mode": "z"})
    assert validate_args(_spec(), {"level": 5, "mode": "a"}) is None


def test_validate_unknown_arg():
    assert "unknown argument" in validate_args(_spec(), {"level": 1, "zzz": 1})


def test_execute_validates_and_reports():
    registry = ToolRegistry()
    registry.register(_spec())
    result = registry.execute("demo", {"level": "bad"})
    assert not result.ok and "invalid arguments" in result.output
    assert registry.execute("nope", {}).ok is False


def test_execute_catches_crashes():
    registry = ToolRegistry()

    def boom(**kwargs):
        raise RuntimeError("kaboom")

    registry.register(_spec(func=boom))
    result = registry.execute("demo", {"level": 1})
    assert not result.ok and "kaboom" in result.output


def test_disabled_tools_hidden_and_blocked():
    registry = ToolRegistry()
    registry.register(_spec())
    registry.set_enabled("demo", False)
    assert registry.openai_tools() == []
    assert "disabled" in registry.execute("demo", {"level": 1}).output


def test_duplicate_registration_rejected():
    registry = ToolRegistry()
    registry.register(_spec())
    with pytest.raises(ValueError):
        registry.register(_spec())


def test_parse_call_args():
    registry = ToolRegistry()
    args, err = registry.parse_call_args('{"a": 1}')
    assert args == {"a": 1} and err is None
    args, err = registry.parse_call_args("not json")
    assert args is None and "JSON" in err
    args, err = registry.parse_call_args("[1,2]")
    assert args is None and err


def test_builtin_registry_has_spec_required_tools(settings):
    registry = build_registry(settings)
    names = set(registry.names())
    for required in ("open_application", "close_application", "open_url",
                     "search_web", "take_screenshot", "get_screen_resolution",
                     "type_text", "press_key", "hotkey", "set_volume",
                     "get_volume", "mute_volume", "unmute_volume",
                     "play_media", "pause_media", "get_time", "get_system_info"):
        assert required in names, required


def test_builtin_dangerous_tools_marked(settings):
    registry = build_registry(settings)
    for name in ("shutdown_computer", "restart_computer", "empty_recycle_bin"):
        assert registry.get(name).dangerous, name
    for name in ("get_time", "open_url", "take_screenshot"):
        assert not registry.get(name).dangerous, name


def test_disabled_list_from_settings(settings):
    settings.set("safety.disabled_tools", ["shutdown_computer"])
    registry = build_registry(settings)
    tool_names = [json.dumps(t["function"]["name"]) for t in registry.openai_tools()]
    assert '"shutdown_computer"' not in tool_names


def test_describe_action_template():
    spec = _spec(confirm_template="set the level to {level}")
    assert spec.describe_action({"level": 4}) == "set the level to 4"
    # Broken template falls back to a generic description.
    spec = _spec(confirm_template="{missing}")
    assert "demo" in spec.describe_action({"level": 4})
