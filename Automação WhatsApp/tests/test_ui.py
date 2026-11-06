import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from demanda import core, ui  # noqa: E402


def test_lista_pesquisa_agrupa_e_recolhe(tmp_path):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    st = core.Store(tmp_path / "l.json")
    for b, r in [("BEIRA RIO", "1"), ("BEIRA RIO", "2"), ("DAKOTA", "3"), ("", "Vizzano 4")]:
        st.add(brand=b, ref=r, folder=str(tmp_path))
    h = {k: (lambda *a: None) for k in ("toggle", "open", "copy", "edit", "remove", "album")}
    p = ui.DemandPanel(st, h, core.Config(tmp_path / "c.json"))
    p.show()
    cards = lambda: len(p.inner.findChildren(ui.DemandCard))  # noqa: E731
    assert cards() == 4
    p.busca.setText("beira")
    app.processEvents()
    assert cards() == 2 and "2 encontrada" in p.counter.text()
    p.busca.setText("xyz")
    app.processEvents()
    assert cards() == 0
    p.busca.setText("")
    p.chk_marca.setChecked(False)
    app.processEvents()
    assert cards() == 4
    p.chk_marca.setChecked(True)
    p._toggle_brand("BEIRA RIO")
    app.processEvents()
    assert cards() == 2  # a marca recolhida esconde os cartões
