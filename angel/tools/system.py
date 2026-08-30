"""System tools: time, info, clipboard, lock/sleep/shutdown (with confirmation)."""

from __future__ import annotations

import datetime
import platform
import subprocess
import sys

from angel.tools.registry import ToolRegistry, ToolResult, ToolSpec

IS_WINDOWS = sys.platform == "win32"


def get_time() -> ToolResult:
    now = datetime.datetime.now()
    return ToolResult(True, now.strftime("It is %A, %B %d, %Y, %I:%M %p"))


def get_system_info() -> ToolResult:
    lines = [f"OS: {platform.system()} {platform.release()}",
             f"Machine: {platform.machine()}"]
    try:
        import psutil

        vm = psutil.virtual_memory()
        lines.append(f"CPU usage: {psutil.cpu_percent(interval=0.3):.0f}%"
                     f" across {psutil.cpu_count()} threads")
        lines.append(f"RAM: {vm.used / 1e9:.1f} of {vm.total / 1e9:.1f} GB used"
                     f" ({vm.percent:.0f}%)")
        battery = psutil.sensors_battery()
        if battery is not None:
            state = "charging" if battery.power_plugged else "on battery"
            lines.append(f"Battery: {battery.percent:.0f}% ({state})")
        disk = psutil.disk_usage("C:\\" if IS_WINDOWS else "/")
        lines.append(f"Disk: {disk.free / 1e9:.0f} GB free of {disk.total / 1e9:.0f} GB")
    except Exception:
        pass
    return ToolResult(True, "; ".join(lines))


def get_clipboard() -> ToolResult:
    if not IS_WINDOWS:
        return ToolResult(False, "clipboard access is only available on Windows")
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=10)
        text = (out.stdout or "").strip()
        if not text:
            return ToolResult(True, "the clipboard is empty")
        return ToolResult(True, f"clipboard contents: {text[:2000]}")
    except Exception as exc:
        return ToolResult(False, f"could not read clipboard: {exc}")


def set_clipboard(text: str) -> ToolResult:
    if not IS_WINDOWS:
        return ToolResult(False, "clipboard access is only available on Windows")
    try:
        subprocess.run(["clip"], input=text, text=True, timeout=10, check=True)
        return ToolResult(True, f"copied {len(text)} characters to the clipboard")
    except Exception as exc:
        return ToolResult(False, f"could not write clipboard: {exc}")


def lock_computer() -> ToolResult:
    if not IS_WINDOWS:
        return ToolResult(False, "locking is only available on Windows")
    try:
        import ctypes

        ctypes.windll.user32.LockWorkStation()
        return ToolResult(True, "locked the computer")
    except Exception as exc:
        return ToolResult(False, f"could not lock: {exc}")


def sleep_computer() -> ToolResult:
    if not IS_WINDOWS:
        return ToolResult(False, "sleep is only available on Windows")
    try:
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return ToolResult(True, "putting the computer to sleep")
    except Exception as exc:
        return ToolResult(False, f"could not sleep: {exc}")


def shutdown_computer() -> ToolResult:
    if not IS_WINDOWS:
        return ToolResult(False, "shutdown is only available on Windows")
    try:
        subprocess.Popen(["shutdown", "/s", "/t", "10"])
        return ToolResult(True, "shutting down in ten seconds "
                                "(run 'shutdown /a' to abort)")
    except Exception as exc:
        return ToolResult(False, f"could not shut down: {exc}")


def restart_computer() -> ToolResult:
    if not IS_WINDOWS:
        return ToolResult(False, "restart is only available on Windows")
    try:
        subprocess.Popen(["shutdown", "/r", "/t", "10"])
        return ToolResult(True, "restarting in ten seconds "
                                "(run 'shutdown /a' to abort)")
    except Exception as exc:
        return ToolResult(False, f"could not restart: {exc}")


def empty_recycle_bin() -> ToolResult:
    if not IS_WINDOWS:
        return ToolResult(False, "recycle bin is only available on Windows")
    try:
        import ctypes

        # SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x7)
        if result in (0, -2147418113):  # S_OK or already empty
            return ToolResult(True, "emptied the recycle bin")
        return ToolResult(False, f"recycle bin call returned code {result}")
    except Exception as exc:
        return ToolResult(False, f"could not empty recycle bin: {exc}")


def register(registry: ToolRegistry, _settings) -> None:
    registry.register(ToolSpec(
        name="get_time", description="Get the current local date and time.",
        parameters={}, required=[], func=get_time))
    registry.register(ToolSpec(
        name="get_system_info",
        description="Get CPU, memory, battery and disk status for this computer.",
        parameters={}, required=[], func=get_system_info))
    registry.register(ToolSpec(
        name="get_clipboard", description="Read the current clipboard text.",
        parameters={}, required=[], func=get_clipboard))
    registry.register(ToolSpec(
        name="set_clipboard", description="Replace the clipboard with given text.",
        parameters={"text": {"type": "string"}}, required=["text"],
        func=set_clipboard))
    registry.register(ToolSpec(
        name="lock_computer",
        description="Lock the Windows session (user unlocks with their password).",
        parameters={}, required=[], func=lock_computer))
    registry.register(ToolSpec(
        name="sleep_computer", description="Put the computer to sleep.",
        parameters={}, required=[], func=sleep_computer,
        dangerous=True, confirm_template="put the computer to sleep"))
    registry.register(ToolSpec(
        name="shutdown_computer", description="Shut the computer down.",
        parameters={}, required=[], func=shutdown_computer,
        dangerous=True, confirm_template="shut down this computer"))
    registry.register(ToolSpec(
        name="restart_computer", description="Restart the computer.",
        parameters={}, required=[], func=restart_computer,
        dangerous=True, confirm_template="restart this computer"))
    registry.register(ToolSpec(
        name="empty_recycle_bin",
        description="Permanently empty the Windows recycle bin.",
        parameters={}, required=[], func=empty_recycle_bin,
        dangerous=True, confirm_template="permanently empty the recycle bin"))
