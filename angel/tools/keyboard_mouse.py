"""Keyboard and mouse control via pyautogui (Windows).

pyautogui's failsafe stays ON: slamming the mouse into the top-left corner
aborts any automation — the user always wins.
"""

from __future__ import annotations

import sys

from angel.tools.registry import ToolRegistry, ToolResult, ToolSpec

IS_WINDOWS = sys.platform == "win32"

_KEY_ALIASES = {
    "windows": "win", "meta": "win", "super": "win",
    "control": "ctrl", "escape": "esc", "return": "enter",
    "spacebar": "space", "page up": "pageup", "page down": "pagedown",
    "print screen": "printscreen", "caps lock": "capslock",
}


def _pyautogui():
    if not IS_WINDOWS:
        raise RuntimeError("input control is only available on Windows")
    import pyautogui

    pyautogui.FAILSAFE = True
    return pyautogui


def _normalize_key(key: str) -> str:
    key = key.strip().lower()
    return _KEY_ALIASES.get(key, key)


def type_text(text: str) -> ToolResult:
    if not text:
        return ToolResult(False, "no text given")
    try:
        gui = _pyautogui()
        gui.write(text, interval=0.015)
        return ToolResult(True, f"typed {len(text)} characters")
    except Exception as exc:
        return ToolResult(False, f"typing failed: {exc}")


def press_key(key: str) -> ToolResult:
    try:
        gui = _pyautogui()
        name = _normalize_key(key)
        if name not in gui.KEYBOARD_KEYS:
            return ToolResult(False, f"unknown key '{key}'")
        gui.press(name)
        return ToolResult(True, f"pressed {name}")
    except Exception as exc:
        return ToolResult(False, f"key press failed: {exc}")


def hotkey(keys: list) -> ToolResult:
    try:
        gui = _pyautogui()
        names = [_normalize_key(str(k)) for k in keys]
        if not names:
            return ToolResult(False, "no keys given")
        for name in names:
            if name not in gui.KEYBOARD_KEYS:
                return ToolResult(False, f"unknown key '{name}'")
        gui.hotkey(*names)
        return ToolResult(True, "pressed " + " + ".join(names))
    except Exception as exc:
        return ToolResult(False, f"hotkey failed: {exc}")


def move_mouse(x: int, y: int) -> ToolResult:
    try:
        gui = _pyautogui()
        gui.moveTo(int(x), int(y), duration=0.2)
        return ToolResult(True, f"moved mouse to ({x}, {y})")
    except Exception as exc:
        return ToolResult(False, f"mouse move failed: {exc}")


def click_mouse(button: str = "left", x: int | None = None,
                y: int | None = None) -> ToolResult:
    try:
        gui = _pyautogui()
        if x is not None and y is not None:
            gui.click(x=int(x), y=int(y), button=button)
            return ToolResult(True, f"{button}-clicked at ({x}, {y})")
        gui.click(button=button)
        return ToolResult(True, f"{button}-clicked at the current cursor position")
    except Exception as exc:
        return ToolResult(False, f"click failed: {exc}")


def scroll(amount: int) -> ToolResult:
    try:
        gui = _pyautogui()
        gui.scroll(int(amount))
        direction = "up" if amount > 0 else "down"
        return ToolResult(True, f"scrolled {direction}")
    except Exception as exc:
        return ToolResult(False, f"scroll failed: {exc}")


def register(registry: ToolRegistry, _settings) -> None:
    registry.register(ToolSpec(
        name="type_text",
        description="Type text at the current cursor/focus position, as if on the keyboard.",
        parameters={"text": {"type": "string", "description": "Text to type"}},
        required=["text"], func=type_text))
    registry.register(ToolSpec(
        name="press_key",
        description="Press a single keyboard key, e.g. 'enter', 'esc', 'f5', 'tab'.",
        parameters={"key": {"type": "string", "description": "Key name"}},
        required=["key"], func=press_key))
    registry.register(ToolSpec(
        name="hotkey",
        description="Press a key combination, e.g. ['ctrl','s'] or ['alt','tab'].",
        parameters={"keys": {"type": "array", "items": {"type": "string"},
                             "description": "Keys pressed together, in order"}},
        required=["keys"], func=hotkey))
    registry.register(ToolSpec(
        name="move_mouse",
        description="Move the mouse cursor to absolute screen coordinates.",
        parameters={"x": {"type": "integer"}, "y": {"type": "integer"}},
        required=["x", "y"], func=move_mouse))
    registry.register(ToolSpec(
        name="click_mouse",
        description="Click the mouse, optionally at specific coordinates.",
        parameters={
            "button": {"type": "string", "enum": ["left", "right", "middle"]},
            "x": {"type": "integer"}, "y": {"type": "integer"},
        },
        required=[], func=click_mouse))
    registry.register(ToolSpec(
        name="scroll",
        description="Scroll the mouse wheel. Positive = up, negative = down. "
                    "One notch is about 120.",
        parameters={"amount": {"type": "integer", "description": "Scroll amount"}},
        required=["amount"], func=scroll))
