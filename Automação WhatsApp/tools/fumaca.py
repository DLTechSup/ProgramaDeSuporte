"""Abre a janela principal por alguns segundos e sai (verifica que não há erros)."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from demanda import core, ui

tmp = Path(tempfile.mkdtemp())
core.data_dir = lambda: tmp  # não mexe nos dados reais
import demanda.app as appmod  # noqa: E402

app = QApplication([])
app.setStyleSheet(ui.STYLE)
(tmp / "marcas" / "DAKOTA").mkdir(parents=True)
cfg = core.Config(tmp / "config.json")
cfg["pasta_marcas"] = str(tmp / "marcas")
win = appmod.MainWindow()
win.show()


def passo():
    win.toggle_detach()      # destaca a lista
    QTimer.singleShot(600, lambda: (win.toggle_detach(), QTimer.singleShot(600, fim)))


def fim():
    win.monitor.stop()
    print("status:", win.panel.status.text())
    print("OK janela principal", flush=True)
    os._exit(0)


QTimer.singleShot(1500, passo)
app.exec()
os._exit(0)
