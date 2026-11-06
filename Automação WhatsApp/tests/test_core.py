import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from demanda import core

BRANDS = ["ACTVITTA", "BEBECÊ", "BEIRA RIO", "DAKOTA", "Maria's Shoes", "MOLECA"]


@pytest.mark.parametrize("legenda,marca,ref", [
    ("BEIRA RIO 8513.115", "BEIRA RIO", "8513.115"),
    ("BEBECE T3533-150", "BEBECÊ", "T3533-150"),
    ("dakota rosa Choque", "DAKOTA", "rosa Choque"),
    ("Moleca - AB_12/x", "MOLECA", "AB_12/x"),
    ("Marias Shoes Salto Fino", "Maria's Shoes", "Salto Fino"),
    ("Dakotta 777-1", "DAKOTA", "777-1"),
    ("BEIRA RIO\n8562.213", "BEIRA RIO", "8562.213"),
])
def test_split_caption(legenda, marca, ref):
    b, r, _ = core.split_caption(legenda, BRANDS)
    assert (b, r) == (marca, ref)


def test_marca_desconhecida():
    b, r, _ = core.split_caption("Vizzano 1234", BRANDS)
    assert b is None and r == "Vizzano 1234"


def test_pastas_do_plano(tmp_path):
    t = lambda b, r: core.target_folder(str(tmp_path), b, r)
    assert t("BEIRA RIO", "8513.115") == tmp_path / "BEIRA RIO" / "BEIRA RIO 8513.115"
    assert t("MOLECA", "AB_12/x") == tmp_path / "MOLECA" / "MOLECA AB_12 x"
    assert t(None, "", ).parent.name == "_REVISAR"


def test_list_brands_ignora(tmp_path):
    for n in ["BEIRA RIO", "Nova pasta", "Nova pasta (2)", "_REVISAR", "FOTOS variadas", "DAKOTA"]:
        (tmp_path / n).mkdir()
    (tmp_path / "arquivo.txt").write_text("x")
    assert core.list_brands(str(tmp_path)) == ["BEIRA RIO", "DAKOTA"]


def test_save_images_sem_duplicar(tmp_path):
    a = b"\xff\xd8\xff" + b"a" * 5000
    b = b"\xff\xd8\xff" + b"b" * 5000
    assert core.save_images(tmp_path, [a, b, b"x"]) == 2
    assert core.save_images(tmp_path, [a, b]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["foto_01.jpg", "foto_02.jpg"]
    c = b"\xff\xd8\xff" + b"c" * 5000
    core.save_images(tmp_path, [c])
    assert (tmp_path / "foto_03.jpg").exists()


def test_move_folder_mescla(tmp_path):
    s, d = tmp_path / "s", tmp_path / "d"
    s.mkdir(); d.mkdir()
    (s / "foto_01.jpg").write_text("novo")
    (d / "foto_01.jpg").write_text("antigo")
    core.move_folder(s, d)
    assert (d / "foto_01.jpg").read_text() == "antigo"
    assert (d / "foto_01_1.jpg").read_text() == "novo"
    assert not s.exists()


def test_store_ordem_e_prontas(tmp_path):
    st = core.Store(tmp_path / "l.json")
    a = st.add(brand="X", ref="1")
    b = st.add(brand="X", ref="2")
    st.update(a["id"], site=True, atacado=True)
    assert [d["ref"] for d in st.ordered()] == ["2", "1"]
    assert st.counts() == (1, 1)
    assert st.find_open("x", "2")["id"] == b["id"]
    assert st.find_open("x", "1") is None
    # prontas de outro dia somem ao recarregar
    st.update(a["id"], date="2000-01-01")
    assert [d["ref"] for d in core.Store(tmp_path / "l.json").items] == ["2"]


def test_seen_persiste(tmp_path):
    s = core.Seen(tmp_path / "v.json")
    s.add("a")
    assert "a" in core.Seen(tmp_path / "v.json")
