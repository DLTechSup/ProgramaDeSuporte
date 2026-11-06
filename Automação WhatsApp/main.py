"""Demanda do Dia — ponto de entrada."""
import os
import sys

# Necessário se rodar como administrador/root (sandbox do Chromium).
if hasattr(os, "geteuid") and os.geteuid() == 0:
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

from PySide6.QtWidgets import QApplication

from demanda import ui
from demanda.app import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Demanda do Dia")
    app.setStyleSheet(ui.STYLE)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
