"""Angel — entry point.

    python app.py            (or double-click run_angel.bat on Windows)

Loads .env, validates the environment, starts the QML scene on the GUI
thread and the voice orchestrator on background threads.
"""

from __future__ import annotations

import os
import sys


def _fail(msg: str) -> "NoReturn":  # noqa: F821
    print(f"\n[Angel] {msg}\n", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    if sys.version_info < (3, 10):
        _fail(f"Python 3.10+ required (you have {sys.version.split()[0]}). "
              "See README.md.")

    # .env before anything reads the environment.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        _fail("Dependencies are not installed. Run run_angel.bat, or:\n"
              "  .venv\\Scripts\\pip install -r requirements.txt")

    from angel import paths
    from angel.logging_setup import setup_logging
    from angel.settings import Settings

    paths.ensure_runtime_dirs()
    settings = Settings.load()
    log = setup_logging(settings.get("app.log_level", "INFO"))
    log.info("Angel starting (python %s)", sys.version.split()[0])

    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QGuiApplication, QIcon
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError as exc:
        _fail(f"PySide6 failed to import ({exc}).\n"
              "Reinstall dependencies: .venv\\Scripts\\pip install -r requirements.txt")

    # Software rendering escape hatch: set ANGEL_SOFTWARE_RENDER=1 if the GPU
    # driver misbehaves.
    if os.environ.get("ANGEL_SOFTWARE_RENDER") == "1":
        os.environ["QSG_RHI_BACKEND"] = "software"

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Angel")
    app.setOrganizationName("Angel")
    icon_path = paths.ASSETS_DIR / "angel" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    from angel.controller import AngelController
    from angel.orchestrator import Orchestrator

    controller = AngelController(settings)
    orchestrator = Orchestrator(settings, bridge=controller)
    controller.attach_orchestrator(orchestrator)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("angel", controller)
    engine.rootContext().setContextProperty(
        "assetsUrl", QUrl.fromLocalFile(str(paths.ASSETS_DIR)).toString())

    qml_file = paths.UI_DIR / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        _fail("The UI failed to load — see logs/angel.log for QML errors.")

    orchestrator.start()
    app.aboutToQuit.connect(orchestrator.stop)

    code = app.exec()
    log.info("Angel exiting (%d)", code)
    return code


if __name__ == "__main__":
    sys.exit(main())
