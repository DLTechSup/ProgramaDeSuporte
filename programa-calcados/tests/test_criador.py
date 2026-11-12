import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.banco import Banco
from app.criador import gerar_nomes, gerar_descricao, refazer_final
from app.produto import Produto
from app.provedores import RespostaIA

P = Produto(1, "BR Sport", "2290.105", "Sandália", "Masculino", "adulto")


class IAFalsa:
    def __init__(self, *respostas): self.respostas, self.chamadas = list(respostas), []
    def chat(self, sistema, usuario, imagens=None, **kw):
        self.chamadas.append(usuario)
        return RespostaIA(json.dumps(self.respostas.pop(0), ensure_ascii=False), "falsa")


def banco(d):
    b = Banco(Path(d) / "b.db")
    b.importar_semente()
    b.criar_produto("BR Sport", "2290.105", "Sandália", "Masculino", "adulto")
    return b


def n(m): return f"SANDÁLIA MASCULINA BR SPORT {m} 2290.105"


def test_nomes_filtra_e_refaz():
    bons = [n("TRAZ PRATICIDADE E COMBINA COM BERMUDA"), n("DESCOMPLICA O FIM DE SEMANA COM ESTILO"),
            n("AMORTECE O IMPACTO E DEVOLVE ENERGIA PARA TREINOS"), n("FACILITA A HORA DE SAIR E VALORIZA O VISUAL"),
            n("LEVA CONFORTO ATE A PRAIA E VOLTA COM ESTILO"), n("SOLADO COM FRISOS E TIRAS QUE AJUSTAM COM FACILIDADE")]
    ruins = [n("ALIVIA A ROTINA E TRAZ ESTILO"), n("VERSATILIDADE NA TIRA E CONFORTO NA BASE 2 EM 1")]
    mais = [n("MUDA O VISUAL DA PRAIA PARA A CIDADE"), n("GARANTE ESTILO CASUAL E ACOMPANHA TODO PASSEIO"),
            n("ENTREGA ALTURA COM LEVEZA E ABRACA O PEITO")]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        b = banco(d)
        ia = IAFalsa({"sugestoes": ruins + bons, "recomendada": 3, "motivo": "ok"}, {"sugestoes": mais, "recomendada": 0})
        r = gerar_nomes(ia, b, P, tentativas=2)
        assert not any("ROTINA" in x for x in r.nomes)
        assert len(r.nomes) >= 6 and all(len(x) <= 85 for x in r.nomes)
        assert r.recomendada in r.nomes and r.rejeitados
        assert "rejeitou" in ia.chamadas[1].lower() or "REJEITOU" in ia.chamadas[1]     # 2a chamada leva os motivos
        assert len(b.sugestoes_do_produto(1)) >= len(r.nomes)


def test_manter_inicio():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        b = banco(d)
        ini = "SANDÁLIA MASCULINA BR SPORT TRAZ PRATICIDADE"
        ia = IAFalsa({"sugestoes": [ini + " E ESTILO PARA SAIR 2290.105", n("AMORTECE O IMPACTO E DEVOLVE ENERGIA PARA TREINOS")]})
        r = gerar_nomes(ia, b, P, manter_inicio=ini, tentativas=1)
        assert r.nomes == [ini + " E ESTILO PARA SAIR 2290.105"]


def test_descricao_valida_e_invalida():
    ok = {"frase_efeito": "Estilo que vai da praia à cidade.", "paragrafo": "A Sandália Masculina BR Sport 2290.105 une design casual, base macia e usos em passeios, viagens e fins de semana.",
          "topicos": {"Marca": "BR Sport", "Referência": "2290.105"},
          "paragrafo_final": "Leve o BR Sport 2290.105 e descubra um jeito leve de curtir cada programa.",
          "palavras_chave": ["sandália masculina", "br sport", "sandália casual", "chinelo masculino", "sandália praia", "2290.105", "br sport 2290.105", "sandália slide"]}
    ruim = dict(ok, paragrafo_final="Corra, últimas peças da rotina!")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        b = banco(d)
        ia = IAFalsa(ruim, ok)
        desc, erros = gerar_descricao(ia, b, P, "NOME FINAL X")
        assert erros == [] and "**Marca:** BR Sport" in desc.texto()
        assert len(ia.chamadas) == 2
        ia2 = IAFalsa({"paragrafo_final": "Leve o BR Sport 2290.105 para qualquer programa com estilo."})
        novo, erros = refazer_final(ia2, b, P, "NOME FINAL X", desc)
        assert erros == [] and novo.frase_efeito == desc.frase_efeito
