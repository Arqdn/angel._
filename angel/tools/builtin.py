"""Assemble the full tool registry from every tool module."""

from __future__ import annotations

from angel.settings import Settings
from angel.tools import apps, browser, keyboard_mouse, media, screen, system
from angel.tools.registry import ToolRegistry

_MODULES = (apps, browser, keyboard_mouse, media, screen, system)


def build_registry(settings: Settings) -> ToolRegistry:
    registry = ToolRegistry()
    for module in _MODULES:
        module.register(registry, settings)
    registry.apply_disabled_list(settings.get("safety.disabled_tools", []) or [])
    return registry
