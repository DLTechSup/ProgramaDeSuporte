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


def test_colar_demandas_previa_e_entradas(tmp_path):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    QtWidgets.QApplication.clipboard().setText("")
    items = [{"brand": "BEIRA RIO", "ref": "8513.115"}]
    d = ui.PasteDialog(["BEIRA RIO", "DAKOTA"], items)
    d.texto.setPlainText("1. BEIRA RIO 8513.115\n- dakota 777-1\nVizzano 9")
    app.processEvents()
    assert d.previa.count() == 3
    assert "2 para adicionar" in d.resumo.text() and "1 já estava" in d.resumo.text()
    entries, site, atac = d.entries()
    assert [(b, r) for b, r, _, _ in entries] == [("DAKOTA", "777-1"), (None, "Vizzano 9")]
    d.texto.setPlainText("BEIRA RIO 8513.115")
    app.processEvents()
    assert not d.bb.button(QtWidgets.QDialogButtonBox.Ok).isEnabled()  # nada novo


def test_cartao_pronto_tem_selo(tmp_path):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    st = core.Store(tmp_path / "l.json")
    a = st.add(brand="X", ref="1", folder=str(tmp_path), site=True, atacado=True)
    h = {k: (lambda *a: None) for k in ("toggle", "open", "copy", "edit", "remove", "album")}
    c = ui.DemandCard(st.get(a["id"]), h)
    textos = [l.text() for l in c.findChildren(QtWidgets.QLabel)]
    assert any("PRONTO" in t for t in textos)
