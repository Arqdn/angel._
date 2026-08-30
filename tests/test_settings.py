"""Settings: defaults loading, deep-merge, dotted access, secret handling."""

import json

from angel.settings import Settings, _deep_merge, get_secret


def test_defaults_have_all_core_sections(settings):
    for section in ("llm", "tts", "stt", "audio", "wake", "personality",
                    "safety", "memory", "ui", "app"):
        assert isinstance(settings.get(section), dict), section


def test_primary_model_is_ox_alpha(settings):
    assert settings.get("llm.model") == "stealth/ox-alpha"
    assert settings.get("llm.base_url") == "https://openrouter.ai/api/v1"


def test_fish_defaults(settings):
    assert settings.get("tts.endpoint") == "https://api.fish.audio/v1/tts"
    assert settings.get("tts.model") == "s2.1-pro-free"


def test_dotted_get_set(settings):
    assert settings.get("does.not.exist", 42) == 42
    settings.set("tts.volume", 0.5)
    assert settings.get("tts.volume") == 0.5
    settings.set("brand.new.key", "x")
    assert settings.get("brand.new.key") == "x"


def test_deep_merge_preserves_unrelated_keys():
    base = {"a": {"b": 1, "c": 2}, "d": 3}
    merged = _deep_merge(base, {"a": {"b": 9}})
    assert merged == {"a": {"b": 9, "c": 2}, "d": 3}
    assert base["a"]["b"] == 1  # no mutation


def test_update_many(settings):
    settings.update_many({"tts.volume": 0.1, "wake.enabled": False})
    assert settings.get("tts.volume") == 0.1
    assert settings.get("wake.enabled") is False


def test_get_returns_copies_not_references(settings):
    aliases = settings.get("wake.aliases")
    aliases.append("hacked")
    assert "hacked" not in settings.get("wake.aliases")


def test_get_secret_env(monkeypatch):
    monkeypatch.delenv("ANGEL_TEST_SECRET", raising=False)
    assert get_secret("ANGEL_TEST_SECRET") is None
    monkeypatch.setenv("ANGEL_TEST_SECRET", "  value  ")
    assert get_secret("ANGEL_TEST_SECRET") == "value"
    monkeypatch.setenv("ANGEL_TEST_SECRET", "   ")
    assert get_secret("ANGEL_TEST_SECRET") is None


def test_no_secrets_in_defaults():
    """The committed defaults file must never contain key material."""
    from angel import paths

    text = paths.DEFAULTS_FILE.read_text("utf-8").lower()
    data = json.loads(paths.DEFAULTS_FILE.read_text("utf-8"))
    assert "sk-or-" not in text
    assert "api_key" not in json.dumps(data).lower()
