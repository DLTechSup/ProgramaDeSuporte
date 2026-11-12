import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.banco import Banco


def test_semente_e_busca():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        sem = Path(d) / "s.txt"
        sem.write_text("# comentario\nSANDÁLIA DAKOTA AMORTECE 1234\nSANDÁLIA DAKOTA AMORTECE 1234\nTÊNIS X LEVA VOCÊ 99\n", encoding="utf-8")
        b = Banco(Path(d) / "b.db")
        assert b.importar_semente(sem) == 2          # repetido ignorado
        assert b.importar_semente(sem) == 0          # reimportar nao duplica
        assert b.listar_nomes("dakota") == ["SANDÁLIA DAKOTA AMORTECE 1234"]
        pid = b.criar_produto("Dakota", "1234", "Sandália", "Feminino", "adulto")
        b.aprovar_nome(pid, "NOVO NOME 1")
        assert b.total_nomes() == 3
        b.fechar()


def test_filtrar_fotos(tmp_path):
    from app.fotos import filtrar_fotos
    (tmp_path / "a.JPG").write_bytes(b"x"); (tmp_path / "b.png").write_bytes(b"x"); (tmp_path / "nota.txt").write_text("x")
    sub = tmp_path / "pasta"; sub.mkdir(); (sub / "c.webp").write_bytes(b"x")
    r = filtrar_fotos([tmp_path / "a.JPG", tmp_path / "nota.txt", sub, "{" + str(tmp_path / "b.png") + "}", tmp_path / "a.JPG"])
    assert [p.name for p in r] == ["a.JPG", "c.webp", "b.png"]
