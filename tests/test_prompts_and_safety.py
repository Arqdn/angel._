"""System prompt construction + orchestrator confirmation gating."""

from unittest.mock import MagicMock

from angel.ai.prompts import build_system_prompt
from angel.tools.registry import ToolRegistry, ToolResult, ToolSpec


def test_prompt_reflects_personality(settings):
    prompt = build_system_prompt(settings)
    assert "Angel" in prompt
    assert "male" in prompt.lower()
    assert "NEVER claim" in prompt
    assert "No markdown" in prompt

    settings.set("personality.verbosity", "terse")
    assert "one or two sentences" in build_system_prompt(settings)

    settings.set("personality.intensity", 0.1)
    assert "mystique stays in the background" in build_system_prompt(settings)


def test_prompt_includes_user_extra_instructions(settings):
    settings.set("personality.extra_instructions", "Call me Commander.")
    assert "Call me Commander." in build_system_prompt(settings)


def test_prompt_is_loyal_to_user(settings):
    prompt = build_system_prompt(settings)
    assert "on your user's side" in prompt


def _orchestrator_for_safety(settings):
    """Orchestrator with only the pieces the safety path needs."""
    from angel.orchestrator import Orchestrator

    orch = Orchestrator.__new__(Orchestrator)
    orch.settings = settings
    orch.registry = ToolRegistry()
    orch.registry.register(ToolSpec(
        name="detonate", description="dangerous demo", parameters={},
        required=[], dangerous=True, confirm_template="detonate everything",
        func=lambda: ToolResult(True, "boom")))
    orch.registry.register(ToolSpec(
        name="harmless", description="safe demo", parameters={},
        required=[], func=lambda: ToolResult(True, "done")))
    return orch


def test_dangerous_tool_denied_not_executed(settings):
    orch = _orchestrator_for_safety(settings)
    orch._ask_confirmation = MagicMock(return_value=False)
    result = orch._execute_tool_with_safety("detonate", {})
    assert result.ok is False
    assert "DENIED" in result.output
    orch._ask_confirmation.assert_called_once_with("detonate everything")


def test_dangerous_tool_approved_executes(settings):
    orch = _orchestrator_for_safety(settings)
    orch._ask_confirmation = MagicMock(return_value=True)
    result = orch._execute_tool_with_safety("detonate", {})
    assert result.ok and result.output == "boom"


def test_safe_tool_skips_confirmation(settings):
    orch = _orchestrator_for_safety(settings)
    orch._ask_confirmation = MagicMock()
    result = orch._execute_tool_with_safety("harmless", {})
    assert result.ok
    orch._ask_confirmation.assert_not_called()


def test_confirmation_can_be_disabled_in_settings(settings):
    settings.set("safety.require_confirmation", False)
    orch = _orchestrator_for_safety(settings)
    orch._ask_confirmation = MagicMock()
    result = orch._execute_tool_with_safety("detonate", {})
    assert result.ok
    orch._ask_confirmation.assert_not_called()


def test_unknown_tool_safe_failure(settings):
    orch = _orchestrator_for_safety(settings)
    result = orch._execute_tool_with_safety("ghost_tool", {})
    assert result.ok is False and "no tool named" in result.output
