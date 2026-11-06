"""Roda o Monitor de verdade (Qt WebEngine) contra uma página que imita o WhatsApp Web."""
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
pytest.importorskip("PySide6.QtWebEngineWidgets")

from PySide6.QtCore import QTimer, QUrl  # noqa: E402
from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: E402

from demanda import core  # noqa: E402
from demanda.monitor import Monitor  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "fake_wa.html"


def _rodar(tmp_path, dedicated):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    root = tmp_path / "LANÇAMENTOS"
    for b in ("BEIRA RIO", "BEBECÊ", "DAKOTA"):
        (root / b).mkdir(parents=True)
    cfg = core.Config(tmp_path / "config.json")
    cfg["pasta_marcas"] = str(root)
    cfg["intervalo_seg"] = 0.5
    cfg["espera_texto_seg"] = 10
    store = core.Store(tmp_path / "lista.json")
    hist = core.History(tmp_path / "h.jsonl")
    seen = core.Seen(tmp_path / "v.json")

    view = QWebEngineView()
    view.resize(1100, 800)
    view.load(QUrl.fromLocalFile(str(FIXTURE)))
    view.show()
    mon = Monitor(view, cfg, store, hist, seen, dedicated=dedicated)
    logs = []
    mon.log.connect(logs.append)
    state = {"n": 0}

    def start():
        view.page().runJavaScript("window.pronto === true", 0, lambda ok: (
            mon.start() if ok else QTimer.singleShot(300, start)))

    def check():
        state["n"] += 1
        if len(store.items) >= 3 or state["n"] > 90:
            app.quit()
        else:
            QTimer.singleShot(500, check)

    QTimer.singleShot(1500, start)
    QTimer.singleShot(3000, check)
    app.exec()
    mon.stop()

    print("LOG:", logs)
    return root, store, seen


def cenario_compartilhado(tmp_path):
    root, store, seen = _rodar(tmp_path, dedicated=False)
    by = {(d["brand"], d["ref"]): d for d in store.items}
    assert ("BEIRA RIO", "8513.115") in by, by.keys()
    assert ("BEBECÊ", "T3533-150") in by, by.keys()
    assert ("", "Vizzano 99") in by, by.keys()
    a = by[("BEIRA RIO", "8513.115")]
    assert a["photos"] == 3 and a["sender"] == "Camilo" and a["time"] == "16:49"
    assert (root / "BEIRA RIO" / "BEIRA RIO 8513.115" / "foto_01.jpg").exists()
    b = by[("BEBECÊ", "T3533-150")]
    assert b["plus"] == 7 and any("+7" in w for w in b["warn"])
    assert any("marca não reconhecida" in w for w in by[("", "Vizzano 99")]["warn"])
    assert (root / "_REVISAR" / "Vizzano 99").is_dir()
    assert "false_1203@g.us_A2_5511@c.us" in seen  # "bom dia" ignorado, mas marcado como visto


def cenario_dedicado(tmp_path):
    """Com a sessão dedicada, o álbum "+7" é aberto e todas as fotos são salvas."""
    root, store, seen = _rodar(tmp_path, dedicated=True)
    b = next(d for d in store.items if d["brand"] == "BEBECÊ")
    # 3 fotos visíveis + 7 do visualizador (album_extra=3 → total = 3 + N)
    assert b["photos"] == 10, b
    assert b["plus"] == 0 and not any("+7" in w for w in b["warn"])


def _em_processo_separado(nome, tmp_path):
    # o Qt WebEngine só aceita uma aplicação por processo
    import subprocess
    r = subprocess.run([sys.executable, __file__, nome, str(tmp_path)],
                       capture_output=True, text=True, timeout=150)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


def test_monitor_cria_demandas(tmp_path):
    _em_processo_separado("cenario_compartilhado", tmp_path)


def test_sessao_dedicada_pega_album_completo(tmp_path):
    _em_processo_separado("cenario_dedicado", tmp_path)


if __name__ == "__main__":
    globals()[sys.argv[1]](Path(sys.argv[2]))
