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


import time as _time_modulo


def test_fluxo_em_duas_etapas_armar_depois_clicar_e_arrastar():
    """1) os dois botoes juntos ARMAM (sem precisar segurar). 2) so' depois, um clique+arraste
    com o ESQUERDO inicia, move e finaliza a selecao. Direito ou outro aperto cancela."""
    from captura.windows import GatilhoCaptura
    import captura.windows as w

    eventos = []
    g = GatilhoCaptura(lambda x, y: eventos.append(("armar", x, y)),
                      lambda x, y: eventos.append(("iniciar", x, y)),
                      lambda x, y: eventos.append(("mover", x, y)),
                      lambda x, y: eventos.append(("finalizar", x, y)),
                      lambda: eventos.append(("cancelar",)), janela_ms=300)
    t = [1000.0]
    w.time = type("T", (), {"monotonic": staticmethod(lambda: t[0])})
    try:
        # 1) toque rapido dos dois botoes: arma (nao inicia a selecao ainda)
        g.clique(10, 10, "esquerdo", True)
        t[0] += 0.05
        g.clique(10, 10, "direito", True)
        assert eventos == [("armar", 10, 10)] and g.estado == g.ARMADO
        # soltar os dois do toque inicial nao faz nada (continua armado)
        g.clique(10, 10, "esquerdo", False)
        g.clique(10, 10, "direito", False)
        assert eventos == [("armar", 10, 10)] and g.estado == g.ARMADO

        # 2) clique normal com o esquerdo: comeca, move, solta -> finaliza
        g.clique(50, 60, "esquerdo", True)
        assert eventos[-1] == ("iniciar", 50, 60) and g.estado == g.SELECIONANDO
        g._mover(80, 90)
        assert eventos[-1] == ("mover", 80, 90)
        g.clique(120, 130, "esquerdo", False)
        assert eventos[-1] == ("finalizar", 120, 130) and g.estado == g.IDLE

        # nao fica "pronto" sozinho de novo: um clique esquerdo solto nao faz nada sem armar antes
        eventos.clear()
        g.clique(1, 1, "esquerdo", True)
        g.clique(2, 2, "esquerdo", False)
        assert eventos == [] and g.estado == g.IDLE
    finally:
        w.time = _time_modulo


def test_cancelar_com_botao_direito_e_com_esc():
    from captura.windows import GatilhoCaptura
    import captura.windows as w
    eventos = []
    g = GatilhoCaptura(lambda x, y: eventos.append(("armar", x, y)), lambda x, y: eventos.append(("iniciar", x, y)),
                      lambda x, y: None, lambda x, y: eventos.append(("finalizar", x, y)),
                      lambda: eventos.append(("cancelar",)), janela_ms=300)
    t = [2000.0]
    w.time = type("T", (), {"monotonic": staticmethod(lambda: t[0])})
    try:
        g.clique(0, 0, "esquerdo", True); g.clique(0, 0, "direito", True)   # arma
        g.clique(0, 0, "esquerdo", False); g.clique(0, 0, "direito", False)
        g.clique(5, 5, "direito", True)                                     # cancela enquanto armado
        assert eventos[-1] == ("cancelar",) and g.estado == g.IDLE
        g.clique(5, 5, "direito", False)                                    # solta o direito do cancelamento

        eventos.clear()
        g.clique(0, 0, "esquerdo", True); g.clique(0, 0, "direito", True)   # arma de novo
        g.clique(0, 0, "esquerdo", False); g.clique(0, 0, "direito", False)
        g.clique(10, 10, "esquerdo", True)                                  # comeca a selecionar
        g.clique(10, 10, "direito", True)                                   # cancela durante a selecao
        assert eventos[-1] == ("cancelar",) and g.estado == g.IDLE and ("finalizar", 10, 10) not in eventos
        g.clique(10, 10, "esquerdo", False); g.clique(10, 10, "direito", False)

        eventos.clear()
        g.clique(0, 0, "esquerdo", True); g.clique(0, 0, "direito", True)   # arma
        g.cancelar()                                                        # Esc chamado de fora
        assert eventos == [("armar", 0, 0), ("cancelar",)] and g.estado == g.IDLE
        g.cancelar()                                                        # ja estava ocioso: nao duplica
        assert eventos == [("armar", 0, 0), ("cancelar",)]
    finally:
        w.time = _time_modulo


def test_direito_demorado_nao_arma():
    from captura.windows import GatilhoCaptura
    import captura.windows as w
    eventos = []
    g = GatilhoCaptura(lambda x, y: eventos.append("armar"), lambda x, y: None, lambda x, y: None,
                      lambda x, y: None, lambda: None, janela_ms=300)
    t = [3000.0]
    w.time = type("T", (), {"monotonic": staticmethod(lambda: t[0])})
    try:
        g.clique(0, 0, "esquerdo", True)
        t[0] += 1.0
        g.clique(0, 0, "direito", True)
        assert eventos == [] and g.estado == g.IDLE
    finally:
        w.time = _time_modulo
