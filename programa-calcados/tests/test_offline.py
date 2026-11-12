import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.banco import Banco
from app.offline import gerar_nomes_offline, gerar_descricao_offline, semear_pecas, aprender_de_nome
from app.produto import Produto
from app.validador import Contexto, validar


def novo(d):
    b = Banco(Path(d) / "b.db"); b.importar_semente(); semear_pecas(b); return b


def test_nomes_offline_passam_no_validador():
    with tempfile.TemporaryDirectory() as d:
        b = novo(d)
        p = Produto(None, "Dakota", "Z1234", "Tamanco", "Feminino", "adulto", ["salto_bloco", "strass", "palmilha_acolchoada"])
        nomes = gerar_nomes_offline(b, p, semente=1)
        assert len(nomes) >= 8, nomes
        ctx = Contexto(p.marca, p.referencia, p.categoria_completa, p.genero, p.publico, aprovados=b.listar_nomes(limite=10**6))
        assert all(validar(n, ctx).aprovado for n in nomes)
        assert all(len(n) <= 85 and n.endswith("Z1234") for n in nomes)


def test_masculino_e_evitar():
    with tempfile.TemporaryDirectory() as d:
        b = novo(d)
        p = Produto(None, "BR Sport", "2999.100", "Sandália", "Masculino", "adulto", ["slide", "palmilha_acolchoada"])
        nomes = gerar_nomes_offline(b, p, evitar="praia", semente=2)
        assert nomes and all("MASCULINA" in n and "PRAIA" not in n and "LAÇO" not in n for n in nomes)


def test_descricao_offline_valida():
    with tempfile.TemporaryDirectory() as d:
        b = novo(d)
        p = Produto(None, "Vizzano", "6500.101", "Sandália", "Feminino", "adulto", ["anabela", "strass"])
        desc, erros = gerar_descricao_offline(b, p, "NOME", semente=3)
        assert erros == [], erros
        assert "Vizzano 6500.101" in desc.paragrafo_final


def test_aprende_pecas():
    with tempfile.TemporaryDirectory() as d:
        b = novo(d)
        p = Produto(None, "Dakota", "Z1", "Tamanco", "Feminino", "adulto", ["strass"])
        antes = b.total_pecas()
        assert aprender_de_nome(b, "TAMANCO DAKOTA REALCA O BRILHO E FACILITA O VISUAL Z1", p) == 2
        assert b.total_pecas() == antes + 2
