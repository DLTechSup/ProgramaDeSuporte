import os, sys, tempfile
from datetime import date
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from monitor.config import Config, Grupo
from monitor.leitor import Mensagem, Navegador
from monitor.motor import Processador, ler_etiqueta
from monitor.marcas import carregar_marcas
from tests.fixture import criar

CHROMIUM = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium")
HOJE = date.today()


def pasta_dia(base, grupo="Demandas Fotos"):
    from monitor.armazenamento import nome_pasta_grupo
    return Path(base) / nome_pasta_grupo(grupo) / HOJE.strftime("%d-%m-%Y")


@pytest.fixture
def nav(tmp_path):
    pytest.importorskip("playwright")
    if not Path(CHROMIUM).exists():
        pytest.skip("sem Chromium")
    n = Navegador(executable_path=CHROMIUM, headless=True, perfil=tmp_path / "perfil", url=criar(tmp_path))
    n.iniciar()
    yield n
    n.fechar()


def test_leitor_ve_conversas_e_mensagens(nav):
    assert nav.logado() and "Demandas Fotos" in nav.conversas()
    assert nav.abrir_conversa("Demandas Fotos")
    titulo, msgs = nav.ler()
    assert titulo == "Demandas Fotos" and len(msgs) == 4
    assert msgs[0].legenda == "BEIRA RIO 8513.115" and msgs[0].remetente == "Camilo" and msgs[0].dia == HOJE
    assert msgs[1].mais == 3 and msgs[2].dia.year == 2020 and msgs[3].minha


def test_grupo_a_salva_pastas_e_lista(nav, tmp_path):
    cfg = Config(pasta_base=str(tmp_path / "saida"), grupos=[Grupo("Demandas Fotos", "A")])
    eventos = []
    p = Processador(cfg, nav, evento=lambda t, d: eventos.append((t, d)))
    p.ciclo()
    avisos = [d for t, d in eventos if t == "salvo"]
    assert [(a["grupo"], a["referencia"], a["novas"], a["nova"]) for a in avisos] == [
        ("Demandas Fotos", "8513.115", 3, True), ("Demandas Fotos", "rosa Choque", 6, True)]
    dia = pasta_dia(cfg.pasta_base)
    beira = dia / "BEIRA RIO 8513.115"
    assert len(list(beira.glob("foto_*.jpg"))) == 3
    assert len(list((dia / "DAKOTA rosa Choque").glob("foto_*"))) == 6          # album +3: 4 visiveis + 2 escondidas
    assert not (dia / "VIZZANO 1111.100").exists() and not (dia / "MODARE 7000.100").exists()   # antiga e propria
    assert {i.referencia for i in p.listas['Demandas Fotos'].itens.values()} == {"8513.115", "rosa Choque"}
    p.ciclo()                                                                   # segunda volta: nada novo
    assert len(list(beira.glob("foto_*"))) == 3 and len(p.listas['Demandas Fotos'].itens) == 2
    txt = (dia / "lista_do_dia.txt").read_bytes().decode("utf-8")
    assert "[ ] 8513.115\r\n    Marca: BEIRA RIO\r\n" in txt and "    Fotos: 3\r\n" in txt and "    Fotos: 6\r\n" in txt
    assert not list(dia.glob("*.csv")) and all(len(l) < 60 for l in txt.split("\r\n"))     # nada junto numa linha so


def test_grupo_b_le_etiqueta(nav, tmp_path):
    textos = iter(["BEIRA RIO\nREF: 2282.107\nCOR PRETO", "etiqueta ilegivel"] + [""] * 20)
    cfg = Config(pasta_base=str(tmp_path / "saida"), grupos=[Grupo("Só Foto Caixa", "B")])
    p = Processador(cfg, nav, ocr=lambda img: next(textos, ""))
    p.ciclo()
    dia = pasta_dia(cfg.pasta_base, "Só Foto Caixa")
    assert len(list((dia / "BEIRA RIO 2282.107").glob("foto_*"))) == 1
    conferir = [d for d in dia.iterdir() if d.name.startswith("_Conferir")]
    assert len(conferir) == 1 and len(list(conferir[0].glob("foto_*"))) == 1
    situ = {i.situacao for i in p.listas['Só Foto Caixa'].itens.values()}
    assert situ == {"ok", "conferir"}


class NavFalso:
    def __init__(self, msgs): self.msgs = msgs
    def abrir_conversa(self, nome): return True
    def ler(self): return "g", self.msgs
    def baixar(self, urls): return [b"\xff\xd8\xff" + bytes(5000) + u.encode() for u in urls]
    def baixar_album_completo(self, m, esperado): return []


def msg(id, legenda="", blobs=("blob:1",), rem="Ana", dia=None, mais=0, carregando=0):
    return Mensagem(id, False, legenda, list(blobs), carregando, mais, rem, dia or HOJE, "10:00")


def test_foto_sem_legenda_espera_texto_e_vence_o_prazo(tmp_path):
    cfg = Config(pasta_base=str(tmp_path), grupos=[Grupo("G", "A")], espera_legenda_seg=100)
    relogio = [1000.0]
    nav = NavFalso([msg("1", "")])
    p = Processador(cfg, nav, agora=lambda: relogio[0])
    p.ciclo()
    assert not any(d.name.startswith("BEIRA") for d in pasta_dia(tmp_path, "G").iterdir() if d.is_dir())
    nav.msgs = [msg("1", ""), msg("2", "BEIRA RIO 777.1", blobs=())]       # texto chega depois
    p.ciclo()
    assert (pasta_dia(tmp_path, "G") / "BEIRA RIO 777.1").is_dir()
    # outro caso: texto nunca chega
    nav.msgs = [msg("3", "", rem="Bia")]
    p.ciclo(); relogio[0] += 150; p.ciclo()
    assert any(d.name.startswith("_Conferir sem legenda") for d in pasta_dia(tmp_path, "G").iterdir())


def test_marca_desconhecida_vai_para_conferir_e_miniatura_borrada_espera(tmp_path):
    cfg = Config(pasta_base=str(tmp_path), grupos=[Grupo("G", "A")])
    nav = NavFalso([msg("1", "bom dia pessoal"), msg("2", "NOVA MARCA 55-1", carregando=1)])
    p = Processador(cfg, nav)
    p.ciclo()
    nomes = [d.name for d in pasta_dia(tmp_path, "G").iterdir() if d.is_dir()]
    assert any(n.startswith("_Conferir bom dia") for n in nomes)
    assert "NOVA MARCA 55-1" not in nomes                         # ainda carregando: espera
    nav.msgs[1].carregando = 0
    p.ciclo()
    assert "NOVA MARCA 55-1" in [d.name for d in pasta_dia(tmp_path, "G").iterdir()]


def test_incluir_hoje_falso_ignora_o_que_ja_estava(tmp_path):
    cfg = Config(pasta_base=str(tmp_path), grupos=[Grupo("G", "A")], incluir_hoje=False)
    nav = NavFalso([msg("1", "BEIRA RIO 1.1")])
    p = Processador(cfg, nav); p.ciclo()
    assert not (pasta_dia(tmp_path, "G") / "BEIRA RIO 1.1").exists()
    nav.msgs.append(msg("2", "DAKOTA 2.2")); p.ciclo()
    assert (pasta_dia(tmp_path, "G") / "DAKOTA 2.2").is_dir()


def test_ler_etiqueta_para_assim_que_acha():
    chamadas = []
    def ler(img): chamadas.append(1); return "MODARE\nREF 7226.106" if len(chamadas) == 1 else "x"
    from PIL import Image
    import io
    buf = io.BytesIO(); Image.new("RGB", (50, 50)).save(buf, "JPEG")
    assert ler_etiqueta(ler, buf.getvalue(), carregar_marcas(None)) == ("MODARE", "7226.106") and len(chamadas) == 1


def test_cada_grupo_tem_a_sua_pasta_e_nome_sem_emoji(tmp_path):
    from monitor.armazenamento import nome_pasta_grupo
    assert nome_pasta_grupo("PROGRAMAÇÃO ✨📷💰") == "PROGRAMAÇÃO"
    assert nome_pasta_grupo("Só Foto: Caixa/2") == "Só Foto- Caixa-2"
    assert nome_pasta_grupo("✨📷") == "Grupo"
    cfg = Config(pasta_base=str(tmp_path), grupos=[Grupo("Grupo ✨ X", "A"), Grupo("Grupo Y", "A")])

    class DoisGrupos(NavFalso):
        def __init__(self): self.atual = ""
        def abrir_conversa(self, nome): self.atual = nome; return True
        def ler(self): return self.atual, [msg("1", "BEIRA RIO 1.1" if "X" in self.atual else "DAKOTA 2.2")]
    p = Processador(cfg, DoisGrupos()); p.ciclo()
    assert (tmp_path / "Grupo X" / HOJE.strftime("%d-%m-%Y") / "BEIRA RIO 1.1").is_dir()
    assert (tmp_path / "Grupo Y" / HOJE.strftime("%d-%m-%Y") / "DAKOTA 2.2").is_dir()
    assert not (tmp_path / "Grupo Y" / HOJE.strftime("%d-%m-%Y") / "BEIRA RIO 1.1").exists()      # nada mistura


def test_texto_do_aviso():
    from monitor.notificacao import texto_do_aviso
    d = {"grupo": "PROGRAMAÇÃO", "marca": "BEIRA RIO", "referencia": "123.456", "novas": 3, "total": 3, "nova": True, "situacao": "ok", "obs": ""}
    assert texto_do_aviso(d) == ("✔ PROGRAMAÇÃO", "BEIRA RIO 123.456", "3 foto(s) salva(s)")
    assert texto_do_aviso(dict(d, nova=False, total=5, novas=2))[0].startswith("＋ PROGRAMAÇÃO")
    t, l1, l2 = texto_do_aviso(dict(d, marca="?", referencia="não lida", situacao="conferir", obs="não consegui ler"))
    assert t.startswith("⚠") and l1 == "não lida" and "não consegui ler" in l2


def test_conversa_individual_salva_texto_mesmo_se_apagar(tmp_path):
    from monitor.leitor import Mensagem
    def m(id, texto, minha=False, blobs=(), hora="10:00", dia=None):
        return Mensagem(id, minha, texto, list(blobs), 0, 0, "Maria", dia or HOJE, hora)
    cfg = Config(pasta_base=str(tmp_path), grupos=[Grupo("Maria Silva", "I")])
    nav = NavFalso([m("1", "bom dia"), m("2", "linha 1\nlinha 2", hora="10:05"), m("3", "resposta minha", minha=True),
                    m("4", "", blobs=("blob:x",), hora="10:06"), m("5", "antiga", dia=date(2020, 1, 1))])
    eventos = []
    p = Processador(cfg, nav, evento=lambda t, d: eventos.append((t, d)))
    p.ciclo()
    arq = tmp_path / "Maria Silva" / HOJE.strftime("%d-%m-%Y") / "mensagens.txt"
    assert arq.read_bytes().decode("utf-8").split("\r\n") == ["[10:00] bom dia", "", "[10:05] linha 1", "        linha 2", "", "[10:06] [foto]", "", ""]
    fotos = list((arq.parent / "fotos").glob("*"))
    assert [f.name for f in fotos] == ["Maria Silva - foto_01.jpg"]                  # foto salva com o nome do contato
    aviso = [d for t, d in eventos if t == "salvo"][0]
    assert aviso["mensagens"] == 3 and aviso["fotos"] == 1 and aviso["previa"] == "bom dia"
    # a pessoa apaga a mensagem 1 e manda outra: o que ja foi salvo continua, e nao duplica
    nav.msgs = [m("1", "Esta mensagem foi apagada"), m("2", "linha 1\nlinha 2", hora="10:05"), m("6", "nova msg", hora="10:20")]
    p.ciclo()
    linhas = [l for l in arq.read_bytes().decode("utf-8").split("\r\n") if l]
    assert linhas[0] == "[10:00] bom dia" and linhas[-1] == "[10:20] nova msg" and len(linhas) == 5


def test_conversa_apagada_antes_de_ler_e_aviso_individual(tmp_path):
    from monitor.leitor import Mensagem
    from monitor.notificacao import texto_do_aviso
    cfg = Config(pasta_base=str(tmp_path), grupos=[Grupo("Joao", "I")])
    nav = NavFalso([Mensagem("1", False, "Você apagou esta mensagem", [], 0, 0, "Joao", HOJE, "09:00")])
    Processador(cfg, nav).ciclo()
    arq = tmp_path / "Joao" / HOJE.strftime("%d-%m-%Y") / "mensagens.txt"
    assert "[mensagem apagada antes de o monitor ler]" in arq.read_text(encoding="utf-8")
    assert texto_do_aviso({"grupo": "Joao", "tipo": "I", "mensagens": 2, "fotos": 1, "previa": "oi", "situacao": "ok", "obs": ""}) == ("💬 Joao", "oi", "2 mensagem(ns) salva(s) em texto · 1 foto(s)")


def test_log_do_dia(tmp_path):
    from datetime import datetime
    from monitor.registro import RegistroDoDia
    r = RegistroDoDia(tmp_path, agora=lambda: datetime(2026, 11, 13, 9, 5, 7))
    r.escrever("Monitor iniciado")
    r.escrever("PROGRAMAÇÃO: BEIRA RIO 123.456 (+3 foto(s))\nsegunda linha")
    bruto = (tmp_path / "_Log" / "log_13-11-2026.txt").read_bytes().decode("utf-8")
    assert bruto == "[09:05:07] Monitor iniciado\r\n[09:05:07] PROGRAMAÇÃO: BEIRA RIO 123.456 (+3 foto(s))\r\n           segunda linha\r\n"
    assert "Monitor iniciado" in r.ler()


def test_servico_grava_o_log(tmp_path):
    import queue
    from monitor.servico import Servico
    sv = Servico(Config(pasta_base=str(tmp_path)), queue.Queue())
    sv.emitir("log", "Camilo mandou 3 fotos"); sv.emitir("erro", "falhou"); sv.emitir("lista", None)
    from monitor.registro import RegistroDoDia
    txt = RegistroDoDia(tmp_path).ler()
    assert "Camilo mandou 3 fotos" in txt and "ERRO: falhou" in txt and txt.count("\n") == 2


def test_referencias_so_numero_letras_e_nomes():
    from monitor.referencia import extrair_referencia as x
    assert x("PEGADA\nREF: (133) 161-01") == "133 161-01"
    assert x("REF: 8513.115") == "8513.115"
    assert x("MODELO: CORRE 2") == "CORRE 2"
    assert x("REF.: T3533-150") == "T3533-150"
    assert x("sem nada de util") is None


def test_regra_cortar_cor_por_marca(tmp_path):
    from monitor.regras_ref import RegrasReferencia
    arq = tmp_path / "regras.txt"
    r = RegrasReferencia.carregar(arq)                       # cria o modelo com a regra da Pegada
    assert arq.exists() and r.aplicar("Pegada", "133 161-01") == ("133 161", "133 161-01")
    assert r.aplicar("PEGADA", "133 161") == ("133 161", "")  # nada a cortar
    assert r.aplicar("Olympikus", "CORRE 2") == ("CORRE 2", "")   # marca sem regra: completa
    arq.write_text("MODARE | .NNN\nOlympikus | -LL\n", encoding="utf-8")
    r2 = RegrasReferencia.carregar(arq)
    assert r2.aplicar("Modare", "7226.106") == ("7226", "7226.106") and r2.aplicar("Olympikus", "CORRE-AB")[0] == "CORRE"


def test_pegada_cores_diferentes_caem_na_mesma_pasta(tmp_path):
    from monitor.regras_ref import RegrasReferencia
    cfg = Config(pasta_base=str(tmp_path), grupos=[Grupo("G", "A")])
    nav = NavFalso([msg("1", "PEGADA (133) 161-01"), msg("2", "Pegada (133) 161-02"), msg("3", "OLYMPIKUS CORRE 2")])
    p = Processador(cfg, nav, regras_ref=RegrasReferencia.carregar(tmp_path / "r.txt"))
    p.ciclo()
    nomes = sorted(d.name for d in pasta_dia(tmp_path, "G").iterdir() if d.is_dir())
    assert nomes == ["OLYMPIKUS CORRE 2", "PEGADA (133) 161"]      # mantém como a pessoa escreveu, sem o -01 da cor
    item = [i for i in p.listas["G"].itens.values() if i.marca == "PEGADA"][0]
    assert "(133) 161-01" in item.observacao            # a referencia completa fica registrada na lista
