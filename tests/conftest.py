import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from angel.settings import Settings  # noqa: E402


@pytest.fixture()
def settings() -> Settings:
    """Fresh defaults-only settings (never touches the user's settings.json)."""
    import json

    data = json.loads((ROOT / "config" / "defaults.json").read_text("utf-8"))
    return Settings(data)
