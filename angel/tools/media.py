"""Volume and media playback tools.

Master volume uses pycaw (Core Audio) on Windows; media transport uses the
keyboard media keys, which every player (Spotify, YouTube, VLC…) honors.
"""

from __future__ import annotations

import sys

from angel.tools.registry import ToolRegistry, ToolResult, ToolSpec

IS_WINDOWS = sys.platform == "win32"


def _volume_interface():
    if not IS_WINDOWS:
        raise RuntimeError("volume control is only available on Windows")
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    device = AudioUtilities.GetSpeakers()
    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    import ctypes

    return ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))


def _media_key(key: str, action: str) -> ToolResult:
    if not IS_WINDOWS:
        return ToolResult(False, f"{action} is only available on Windows")
    try:
        import pyautogui

        pyautogui.press(key)
        return ToolResult(True, action)
    except Exception as exc:
        return ToolResult(False, f"{action} failed: {exc}")


def set_volume(level: int) -> ToolResult:
    try:
        volume = _volume_interface()
        volume.SetMasterVolumeLevelScalar(max(0, min(100, int(level))) / 100.0, None)
        return ToolResult(True, f"volume set to {int(level)} percent")
    except Exception as exc:
        return ToolResult(False, f"could not set volume: {exc}")


def get_volume() -> ToolResult:
    try:
        volume = _volume_interface()
        level = round(volume.GetMasterVolumeLevelScalar() * 100)
        muted = bool(volume.GetMute())
        return ToolResult(True, f"volume is {level} percent"
                                + (", muted" if muted else ""))
    except Exception as exc:
        return ToolResult(False, f"could not read volume: {exc}")


def mute_volume() -> ToolResult:
    try:
        _volume_interface().SetMute(1, None)
        return ToolResult(True, "muted")
    except Exception as exc:
        return ToolResult(False, f"could not mute: {exc}")


def unmute_volume() -> ToolResult:
    try:
        _volume_interface().SetMute(0, None)
        return ToolResult(True, "unmuted")
    except Exception as exc:
        return ToolResult(False, f"could not unmute: {exc}")


def play_media() -> ToolResult:
    return _media_key("playpause", "sent play/pause to the active media player")


def pause_media() -> ToolResult:
    return _media_key("playpause", "sent play/pause to the active media player")


def next_track() -> ToolResult:
    return _media_key("nexttrack", "skipped to the next track")


def previous_track() -> ToolResult:
    return _media_key("prevtrack", "went to the previous track")


def register(registry: ToolRegistry, _settings) -> None:
    registry.register(ToolSpec(
        name="set_volume",
        description="Set the system master volume (0–100).",
        parameters={"level": {"type": "integer", "minimum": 0, "maximum": 100,
                              "description": "Volume percent"}},
        required=["level"], func=set_volume))
    registry.register(ToolSpec(
        name="get_volume", description="Get the current system volume and mute state.",
        parameters={}, required=[], func=get_volume))
    registry.register(ToolSpec(
        name="mute_volume", description="Mute the system audio.",
        parameters={}, required=[], func=mute_volume))
    registry.register(ToolSpec(
        name="unmute_volume", description="Unmute the system audio.",
        parameters={}, required=[], func=unmute_volume))
    registry.register(ToolSpec(
        name="play_media",
        description="Press play (toggles play/pause in the active media player).",
        parameters={}, required=[], func=play_media))
    registry.register(ToolSpec(
        name="pause_media",
        description="Press pause (toggles play/pause in the active media player).",
        parameters={}, required=[], func=pause_media))
    registry.register(ToolSpec(
        name="next_track", description="Skip to the next media track.",
        parameters={}, required=[], func=next_track))
    registry.register(ToolSpec(
        name="previous_track", description="Go back to the previous media track.",
        parameters={}, required=[], func=previous_track))
