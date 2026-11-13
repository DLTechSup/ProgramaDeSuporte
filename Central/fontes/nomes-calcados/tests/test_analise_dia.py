import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.analise_dia import analisar, aplicar, Proposta
from app.banco import Banco


def test_analise_simples_e_aplicacao():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        b = Banco(Path(d) / "b.db")
        pid = b.criar_produto("Dakota", "1", "Tamanco", "Feminino", "adulto")
        for i in range(3):
            b.aprovar_nome(pid, f"TAMANCO DAKOTA GARANTE ENCAIXE E BRILHO {i} 1")
        b.adicionar_correcao(pid, "EVITAR: sola, charme")
        props, origem = analisar(b, ia=None)
        tipos = {(p.tipo, p.valor) for p in props}
        assert ("adicionar_proibida", "sola") in tipos and ("adicionar_moderacao", "garante") in tipos
        regras = Path(d) / "regras"; regras.mkdir()
        (regras / "proibidas.json").write_text(json.dumps({"palavras": ["golada"]}), encoding="utf-8")
        backup = aplicar(Proposta("adicionar_proibida", "sola", "x"), b, regras)
        assert "sola" in json.loads((regras / "proibidas.json").read_text())["palavras"]
        assert (Path(backup) / "proibidas.json").exists()          # backup guarda a versao ANTERIOR
        assert "sola" not in (Path(backup) / "proibidas.json").read_text()
        assert b.con.execute("SELECT COUNT(*) FROM regras_versoes").fetchone()[0] == 1


def test_dia_vazio():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        props, msg = analisar(Banco(Path(d) / "b.db"))
        assert props == [] and "Nada" in msg
