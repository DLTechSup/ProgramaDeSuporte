import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.validador import Contexto, validar

SEMENTE = [l.strip() for l in (Path(__file__).resolve().parent.parent / "dados/semente_nomes.txt").read_text(encoding="utf-8").splitlines()
           if l.strip() and not l.startswith("#")]
BASE = dict(marca="BR Sport", referencia="2290.105", categoria="SANDÁLIA MASCULINA", genero="Masculino", publico="adulto")


def ctx(**kw):
    d = dict(BASE, aprovados=[a for a in SEMENTE if not a.endswith("2290.105")])
    d.update(kw)
    return Contexto(**d)


def falhas(nome, **kw):
    return {i.regra for i in validar(nome, ctx(**kw)).itens if not i.ok}


def test_nome_valido_do_arquivo_v5():
    r = validar("SANDÁLIA MASCULINA BR SPORT VAI BEM COM TODO LOOK E FACILITA A HORA DE SAIR 2290.105", ctx())
    assert r.aprovado, r.motivos


def test_limite_85():
    assert "85 caracteres" in falhas("SANDÁLIA MASCULINA BR SPORT DESCOMPLICA O SEU FIM DE SEMANA COM ESTILO CASUAL 2290.105")


def test_palavra_proibida_e_cor():
    assert "Sem palavras proibidas" in falhas("SANDÁLIA MASCULINA BR SPORT TRAZ ALIVIO PARA A ROTINA 2290.105")
    assert "Sem cor no nome" in falhas("SANDÁLIA MASCULINA BR SPORT PRETA E PRATICA COM ESTILO 2290.105")


def test_repeticao_com_palavras_trocadas_e_sinonimo():
    assert "Não repetido" in falhas("SANDÁLIA MASCULINA BR SPORT VERSATILIDADE NA TIRA E CONFORTO NA BASE 2 EM 1 2290.105")
    ant = ["SANDÁLIA MASCULINA BR SPORT ALIVIA O CANSAÇO E ESTABILIZA 2290.105"]
    assert "Não repetido" in falhas("SANDÁLIA MASCULINA BR SPORT REDUZ O CANSAÇO E ESTABILIZA 2290.105", anteriores=ant)


def test_estrutura_categoria_marca_referencia():
    f = falhas("TÊNIS BR SPORT TRAZ PRATICIDADE E COMBINA COM BERMUDA 9999")
    assert {"Começa pela categoria", "Termina com a referência"} <= f


def test_tom_masculino_e_ligacao_verbal():
    assert "Tom masculino" in falhas("SANDÁLIA MASCULINA BR SPORT TRAZ CHARME E PRATICIDADE PARA SAIR 2290.105")
    assert "Ligação verbal" in falhas("SANDÁLIA MASCULINA BR SPORT BASE ANATOMICA SOLADO ROBUSTO TIRA LARGA 2290.105")


def test_diversidade_e_moderacao_no_lote():
    lote = ["SANDÁLIA MASCULINA BR SPORT TRAZ PRATICIDADE E COMBINA COM BERMUDA 2290.105"]
    assert "Diversidade no lote" in falhas("SANDÁLIA MASCULINA BR SPORT TRAZ SOLADO COM FRISOS PARA SAIR 2290.105", lote=lote)
    lote2 = ["SANDÁLIA MASCULINA BR SPORT VAI BEM COM TODO LOOK E FACILITA A SAIDA 2290.105"]
    assert "Palavras de moderação" in falhas("SANDÁLIA MASCULINA BR SPORT LEVA ESTILO CASUAL PARA UM LOOK DE FIM DE SEMANA 2290.105", lote=lote2)
