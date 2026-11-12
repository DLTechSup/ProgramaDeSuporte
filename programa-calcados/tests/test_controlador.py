import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.banco import Banco
from app.controlador import Controlador
from app.provedores import ErroIA, RespostaIA
from tests.test_pesquisa import HTML
import app.pesquisa as P


class IA:
    def __init__(self, *r): self.r = list(r)
    def chat(self, s, u, imagens=None, **k): return RespostaIA(json.dumps(self.r.pop(0) if len(self.r) > 1 else self.r[0], ensure_ascii=False), "falsa")


def novo(d, ia=None, modo="Online"):
    b = Banco(Path(d) / "b.db"); b.importar_semente()
    c = Controlador(b, ia, buscar=lambda q: [{"href": "https://loja.com/p"}], abrir=lambda u: HTML)
    c.modo = modo
    return c


def test_sem_foto_exige_confirmacao(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "LOGS", tmp_path)
    with tempfile.TemporaryDirectory() as d:
        c = novo(d)
        c.definir_produto("BR Sport", "2282.107", "Sandália", "Masculino", "adulto")
        assert not c.pode_criar_nomes[0]
        assert c.pesquisar() == "cartoes" and c.cartoes
        c.confirmar_cartao(c.cartoes[0])
        assert c.pode_criar_nomes[0] and "link confirmado" in c.log_texto.lower()


def test_foto_divergente_e_fluxo_completo(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "LOGS", tmp_path)
    nomes = [f"SANDÁLIA MASCULINA BR SPORT {m} 2282.107" for m in
             ["TRAZ PRATICIDADE E COMBINA COM BERMUDA", "DESCOMPLICA O FIM DE SEMANA COM ESTILO", "FACILITA A HORA DE SAIR E VALORIZA O VISUAL"]]
    ia = IA({"referencia": "9999.999", "cor": "CAFE 569"}, {"sugestoes": nomes, "recomendada": 1, "motivo": "m"})
    with tempfile.TemporaryDirectory() as d:
        c = novo(d, ia)
        c.fotos = [Path("x.jpg")]
        c.definir_produto("BR Sport", "2282.107", "Sandália", "Masculino", "adulto")
        assert c.pesquisar() == "foto" and "ATENÇÃO" in c.log_texto and c.pesquisa.peso.startswith("380")
        r = c.criar_nomes(evitar="charme")
        assert r.nomes and r.recomendada == nomes[1]
        assert c.banco.listar_correcoes(c.produto.id) == ["EVITAR: charme"]
        c.aprovar_nome(r.nomes[0])
        assert r.nomes[0] in c.banco.listar_nomes()


def test_modo_offline_sem_ia():
    with tempfile.TemporaryDirectory() as d:
        c = novo(d, None, "Offline")
        c.definir_produto("Dakota", "Z1", "Tamanco", "Feminino", "adulto", ["salto_bloco", "strass"])
        r = c.criar_nomes()
        assert r.provedor == "offline" and len(r.nomes) >= 8
        c.aprovar_nome(r.nomes[0])
        desc, erros = c.gerar_descricao()
        assert not erros and c.texto_para_copiar().startswith(r.nomes[0])


def test_inicio_para_ajuste_e_detectar_chave():
    from app.controlador import inicio_para_ajuste
    from app.produto import Produto
    from app.provedores import detectar_chave
    p = Produto(1, "BR Sport", "2282.107", "Sandália", "Masculino", "adulto")
    ini = inicio_para_ajuste("SANDÁLIA MASCULINA BR SPORT TRAZ PRATICIDADE E COMBINA COM BERMUDA 2282.107", p)
    assert ini == "SANDÁLIA MASCULINA BR SPORT TRAZ PRATICIDADE"
    assert detectar_chave("minha chave: AIzaSyA1234567890abcdefghijklmnopqrstuv ok", "google").startswith("AIza")
    assert detectar_chave("gsk_abcdefghijklmnopqrstuvwx", "groq") and detectar_chave("nada", "google") == ""
