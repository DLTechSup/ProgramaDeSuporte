"""Demanda do Dia — ponto de entrada."""
import json
import os
import sys


def _preparar_navegador() -> None:
    """Define as opções do navegador embutido ANTES de abrir o Qt."""
    flags = []
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        flags.append("--no-sandbox")  # só quando rodar como root
    compat = True
    try:
        from demanda import core
        compat = bool(json.loads((core.data_dir() / "config.json").read_text("utf-8"))
                      .get("compat_grafica", True))
    except Exception:
        pass
    if compat:
        flags += ["--disable-gpu", "--disable-gpu-compositing"]
    if flags:
        atual = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (atual + " " + " ".join(flags)).strip()


_preparar_navegador()

from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from demanda import core, ui  # noqa: E402
from demanda.app import MainWindow  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Demanda do Dia")
    app.setStyleSheet(ui.STYLE)
    icone = core.app_dir() / "assets" / "icone.ico"
    if not icone.exists():
        icone = core.app_dir() / "_internal" / "assets" / "icone.ico"
    if icone.exists():
        app.setWindowIcon(QIcon(str(icone)))
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
