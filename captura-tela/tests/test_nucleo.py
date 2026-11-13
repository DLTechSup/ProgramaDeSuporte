import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from captura import nucleo as n


def test_normalizar_area_qualquer_direcao_do_arrasto():
    assert n.normalizar_area(100, 200, 10, 20) == (10, 20, 100, 200)
    assert n.normalizar_area(10, 20, 100, 200) == (10, 20, 100, 200)
    assert n.normalizar_area(10.6, 20.4, 100.2, 200.9) == (11, 20, 100, 201)


def test_area_valida_rejeita_clique_sem_arrastar():
    assert not n.area_valida((100, 100, 101, 101))
    assert not n.area_valida((100, 100, 102, 150))     # largura menor que o minimo
    assert n.area_valida((100, 100, 110, 110))


def test_nome_de_arquivo_sem_caracteres_proibidos():
    nome = n.nome_arquivo(datetime(2026, 11, 13, 15, 30, 7))
    assert nome == "Captura 2026-11-13 15-30-07.png" and ":" not in nome
    assert n.nome_arquivo(datetime(2026, 1, 1), prefixo="Tela:Teste/1").startswith("Tela-Teste-1 ")


def test_caminho_sem_sobrescrever(tmp_path):
    nome = "Captura 2026-11-13 15-30-07.png"
    assert n.caminho_sem_sobrescrever(tmp_path, nome) == tmp_path / nome
    (tmp_path / nome).write_bytes(b"x")
    assert n.caminho_sem_sobrescrever(tmp_path, nome) == tmp_path / "Captura 2026-11-13 15-30-07 (2).png"
    (tmp_path / "Captura 2026-11-13 15-30-07 (2).png").write_bytes(b"x")
    assert n.caminho_sem_sobrescrever(tmp_path, nome) == tmp_path / "Captura 2026-11-13 15-30-07 (3).png"


def test_config_salvar_e_carregar(tmp_path):
    arq = tmp_path / "cfg.json"
    c = n.Config(pasta_destino="C:/x", som=False)
    c.salvar(arq)
    c2 = n.Config.carregar(arq)
    assert c2.pasta_destino == "C:/x" and c2.som is False and c2.copiar_para_area_transferencia is True
    assert n.Config.carregar(tmp_path / "nao_existe.json").pasta_destino == ""


def test_gatilho_dos_dois_botoes_logica_pura():
    """So a logica de 'os dois ficaram pressionados dentro da janela de tempo' -- sem pynput de verdade."""
    from captura.windows import GatilhoDoisBotoes
    import captura.windows as w

    eventos = []
    g = GatilhoDoisBotoes(lambda x, y: eventos.append(("iniciar", x, y)),
                         lambda x, y: eventos.append(("mover", x, y)),
                         lambda x, y: eventos.append(("soltar", x, y)), janela_ms=300)

    import time
    t = [1000.0]
    w.time = type("T", (), {"monotonic": staticmethod(lambda: t[0])})
    try:
        g.clique(10, 20, "esquerdo", True)           # so o esquerdo: nada ainda
        assert eventos == []
        t[0] += 0.1
        g.clique(10, 20, "direito", True)             # direito chegou rapido: dispara
        assert eventos == [("iniciar", 10, 20)]
        g._mover(15, 25)
        assert eventos[-1] == ("mover", 15, 25)
        g.clique(30, 40, "esquerdo", False)            # soltar qualquer um dos dois finaliza
        assert eventos[-1] == ("soltar", 30, 40)

        eventos.clear()
        g.clique(0, 0, "esquerdo", True)
        t[0] += 1.0                                    # direito demorou demais: nao conta
        g.clique(0, 0, "direito", True)
        assert eventos == []
    finally:
        w.time = time
