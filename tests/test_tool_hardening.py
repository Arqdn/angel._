"""Model-supplied tool arguments must never reach a shell unsanitized."""

from angel.tools.apps import open_application
from angel.tools.browser import open_url


def test_open_application_rejects_shell_metacharacters():
    for evil in ('chrome" & del /q C:\\*', "a|b", "x&y", "p^q", "%PATH%",
                 "line\nbreak"):
        result = open_application(evil)
        assert not result.ok
        assert "not a valid application name" in result.output


def test_open_application_normal_names_pass_validation():
    # On Linux CI these fail at the Windows guard, NOT at validation.
    result = open_application("chrome")
    assert "not a valid application name" not in result.output
    result = open_application("ms-settings:")
    assert "not a valid application name" not in result.output


def test_open_url_rejects_non_urls():
    assert not open_url("not a url at all").ok
    assert not open_url("").ok
