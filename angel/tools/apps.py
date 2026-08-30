"""Application launch/close tools (Windows-first, graceful elsewhere)."""

from __future__ import annotations

import logging
import subprocess
import sys

from angel.tools.registry import ToolRegistry, ToolResult

log = logging.getLogger("angel.tools.apps")

IS_WINDOWS = sys.platform == "win32"

# Friendly name -> what Windows can actually start. Anything not listed is
# tried verbatim (Start knows about PATH and App Paths registrations).
_APP_ALIASES: dict[str, str] = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "firefox": "firefox",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "spotify": "spotify",
    "discord": "discord",
    "steam": "steam",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "terminal": "wt",
    "windows terminal": "wt",
    "cmd": "cmd",
    "powershell": "powershell",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "control panel": "control",
    "snipping tool": "snippingtool",
    "obs": "obs64",
}

# Process names for close_application (without .exe).
_PROCESS_ALIASES: dict[str, list[str]] = {
    "chrome": ["chrome"],
    "google chrome": ["chrome"],
    "edge": ["msedge"],
    "firefox": ["firefox"],
    "notepad": ["notepad"],
    "calculator": ["CalculatorApp", "Calculator", "calc"],
    "spotify": ["Spotify"],
    "discord": ["Discord"],
    "word": ["WINWORD"],
    "excel": ["EXCEL"],
    "vs code": ["Code"],
    "vscode": ["Code"],
    "steam": ["steam"],
    "obs": ["obs64"],
}


def _resolve_app(app_name: str) -> str:
    return _APP_ALIASES.get(app_name.strip().lower(), app_name.strip())


def open_application(app_name: str) -> ToolResult:
    target = _resolve_app(app_name)
    if not target:
        return ToolResult(False, "no application name given")
    if not IS_WINDOWS:
        return ToolResult(False, f"can only open applications on Windows "
                                 f"(would have opened '{target}')")
    try:
        # `start` resolves App Paths, UWP aliases and URL schemes alike.
        subprocess.Popen(f'start "" "{target}"', shell=True)
        return ToolResult(True, f"launched {app_name}")
    except OSError as exc:
        return ToolResult(False, f"could not launch {app_name}: {exc}")


def close_application(app_name: str) -> ToolResult:
    """Politely terminate an app's processes (no force-kill)."""
    try:
        import psutil
    except ImportError:
        return ToolResult(False, "psutil is not installed")

    lookup = app_name.strip().lower()
    candidates = {c.lower() for c in _PROCESS_ALIASES.get(lookup, [lookup])}
    matched = []
    for proc in psutil.process_iter(["name"]):
        try:
            name = (proc.info["name"] or "").rsplit(".exe", 1)[0].lower()
            if name in candidates:
                proc.terminate()
                matched.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if not matched:
        return ToolResult(False, f"no running process found for '{app_name}'")
    psutil.wait_procs(matched, timeout=4)
    return ToolResult(True, f"asked {app_name} to close "
                            f"({len(matched)} process(es))")


def register(registry: ToolRegistry, _settings) -> None:
    registry.register(_spec(
        "open_application",
        "Open/launch an application on the user's computer by name, e.g. "
        "'chrome', 'notepad', 'spotify', 'settings'.",
        {"app_name": {"type": "string", "description": "Application name"}},
        ["app_name"], open_application))
    registry.register(_spec(
        "close_application",
        "Politely close a running application by name. Unsaved work may be lost, "
        "so only use when the user asked for it.",
        {"app_name": {"type": "string", "description": "Application name"}},
        ["app_name"], close_application,
        dangerous=True, confirm_template="close the application {app_name}"))


def _spec(name, description, parameters, required, func,
          dangerous=False, confirm_template=""):
    from angel.tools.registry import ToolSpec

    return ToolSpec(name=name, description=description, parameters=parameters,
                    required=required, func=func, dangerous=dangerous,
                    confirm_template=confirm_template)
