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
    assert (dia / "lista_do_dia.csv").read_text(encoding="utf-8-sig").count("\n") == 3


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
