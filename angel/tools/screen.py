"""Screen tools: screenshots (which flow to the model as vision input when it
asks for them) and display info. Screenshots are only ever taken on demand."""

from __future__ import annotations

import datetime
import logging

from angel import paths
from angel.tools.registry import ToolRegistry, ToolResult, ToolSpec

log = logging.getLogger("angel.tools.screen")


def take_screenshot(monitor: int = 0) -> ToolResult:
    """Capture the screen to a PNG. The orchestrator attaches the image to the
    conversation so the model can actually see it."""
    try:
        import mss
        import mss.tools
    except ImportError:
        return ToolResult(False, "mss is not installed")

    try:
        paths.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = paths.SCREENSHOTS_DIR / f"screen_{stamp}.png"
        with mss.mss() as sct:
            # monitor 0 = all displays combined; 1..n = individual displays
            index = monitor if 0 <= monitor < len(sct.monitors) else 0
            shot = sct.grab(sct.monitors[index])
            mss.tools.to_png(shot.rgb, shot.size, output=str(out_path))
        log.info("Screenshot saved: %s", out_path)
        return ToolResult(
            True,
            "screenshot captured; the image is attached for you to look at",
            attach_image=str(out_path),
        )
    except Exception as exc:
        return ToolResult(False, f"screenshot failed: {exc}")


def get_screen_resolution() -> ToolResult:
    try:
        import mss

        with mss.mss() as sct:
            displays = sct.monitors[1:] or sct.monitors[:1]
            parts = [f"display {i + 1}: {m['width']}x{m['height']}"
                     for i, m in enumerate(displays)]
        return ToolResult(True, "; ".join(parts))
    except Exception as exc:
        return ToolResult(False, f"could not read display info: {exc}")


def register(registry: ToolRegistry, _settings) -> None:
    registry.register(ToolSpec(
        name="take_screenshot",
        description="Capture the user's screen and attach the image so you can "
                    "see exactly what they are looking at. Use when the user "
                    "asks about anything currently on screen.",
        parameters={"monitor": {"type": "integer", "minimum": 0, "maximum": 8,
                                "description": "0 = all displays (default), "
                                               "1..n = a specific display"}},
        required=[], func=take_screenshot))
    registry.register(ToolSpec(
        name="get_screen_resolution",
        description="Get the resolution of the user's display(s).",
        parameters={}, required=[], func=get_screen_resolution))
