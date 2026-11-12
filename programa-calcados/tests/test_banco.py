import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.banco import Banco


def test_semente_e_busca():
    with tempfile.TemporaryDirectory() as d:
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
