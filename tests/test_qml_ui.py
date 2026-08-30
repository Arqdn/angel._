"""Headless smoke test: the full QML scene must load with zero errors.

Skipped automatically when PySide6/Qt can't run in this environment.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

_LOADER = """
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QSG_RHI_BACKEND", "software")
sys.path.insert(0, {root!r})

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

class Stub(QObject):
    stateChanged = Signal(); statusChanged = Signal(); micLevelChanged = Signal()
    voiceLevelChanged = Signal(); userTextChanged = Signal(); angelTextChanged = Signal()
    confirmActionChanged = Signal(); errorTextChanged = Signal()
    setupIssuesChanged = Signal(); settingsJsonChanged = Signal()
    state = Property(str, lambda self: "idle", notify=stateChanged)
    status = Property(str, lambda self: "", notify=statusChanged)
    micLevel = Property(float, lambda self: 0.0, notify=micLevelChanged)
    voiceLevel = Property(float, lambda self: 0.2, notify=voiceLevelChanged)
    userText = Property(str, lambda self: "hello", notify=userTextChanged)
    angelText = Property(str, lambda self: "I am here.", notify=angelTextChanged)
    confirmAction = Property(str, lambda self: "shut down this computer",
                             notify=confirmActionChanged)
    errorText = Property(str, lambda self: "", notify=errorTextChanged)
    setupIssues = Property("QStringList", lambda self: ["VOICE API KEY REQUIRED"],
                           notify=setupIssuesChanged)
    settingsJson = Property(str, lambda self: '{{"ui.fullscreen": false}}',
                            notify=settingsJsonChanged)
    micDevices = Property("QVariantList", lambda self: [], constant=True)
    @Slot()
    def pushToTalk(self): pass
    @Slot(bool)
    def resolveConfirmation(self, v): pass
    @Slot(str)
    def submitTypedRequest(self, t): pass
    @Slot(str)
    def saveSettings(self, j): pass
    @Slot()
    def quitAngel(self): pass

app = QGuiApplication([])
engine = QQmlApplicationEngine()
problems = []
engine.warnings.connect(lambda ws: problems.extend(w.toString() for w in ws))
engine.rootContext().setContextProperty("angel", Stub())
engine.rootContext().setContextProperty(
    "assetsUrl", QUrl.fromLocalFile({root!r} + "/assets").toString())
engine.load(QUrl.fromLocalFile({root!r} + "/ui/Main.qml"))
assert engine.rootObjects(), "Main.qml produced no root object"
QTimer.singleShot(1200, app.quit)
app.exec()
assert not problems, "QML warnings: " + "; ".join(problems)
print("OK")
"""


def test_main_qml_loads_headless(tmp_path):
    pytest.importorskip("PySide6")
    script = tmp_path / "loader.py"
    script.write_text(_LOADER.format(root=str(ROOT)), encoding="utf-8")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QSG_RHI_BACKEND="software")
    proc = subprocess.run([sys.executable, str(script)], env=env,
                          capture_output=True, text=True, timeout=120)
    if proc.returncode != 0 and ("libEGL" in proc.stderr or "xcb" in proc.stderr):
        pytest.skip(f"Qt cannot run headless here: {proc.stderr[-200:]}")
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "OK" in proc.stdout
