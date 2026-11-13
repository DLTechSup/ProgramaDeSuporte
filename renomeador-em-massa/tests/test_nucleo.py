import os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest
from renomeador import nucleo as n


def criar(pasta: Path, nomes, mtimes=None):
    out = []
    for i, nome in enumerate(nomes):
        f = pasta / nome
        f.write_bytes(b"x" * (i + 1))
        if mtimes:
            os.utime(f, (mtimes[i], mtimes[i]))
        out.append(str(f))
    return out


def test_sequencia_basica_como_pedido(tmp_path):
    arqs = criar(tmp_path, ["IMG-20260101-WA0007.JPG", "IMG-20260101-WA0008.jpg", "foto.png"], [100, 200, 300])
    p = n.montar_plano(arqs, n.Opcoes(nome="branco"))
    assert [Path(b).name for _, b in p.pares] == ["branco 01.jpg", "branco 02.jpg", "branco 03.png"]      # extensao em minuscula
    assert p.erro == "" and p.inicio == 1


def test_ordens_zeros_separador_e_inicio(tmp_path):
    arqs = criar(tmp_path, ["b 10.jpg", "b 2.jpg", "b 1.jpg"], [300, 200, 100])
    nomes = lambda **kw: [Path(b).name for _, b in n.montar_plano(arqs, n.Opcoes(nome="x", **kw)).pares]
    assert nomes(ordem="nome") == ["x 01.jpg", "x 02.jpg", "x 03.jpg"]
    p = n.montar_plano(arqs, n.Opcoes(nome="x", ordem="nome"))
    assert [Path(a).name for a, _ in p.pares] == ["b 1.jpg", "b 2.jpg", "b 10.jpg"]                      # ordem natural (2 antes de 10)
    p = n.montar_plano(arqs, n.Opcoes(nome="x", ordem="data"))
    assert [Path(a).name for a, _ in p.pares] == ["b 1.jpg", "b 2.jpg", "b 10.jpg"]                      # por data de modificacao
    assert nomes(zeros=False, inicio=8) == ["x 8.jpg", "x 9.jpg", "x 10.jpg"]
    assert nomes(zeros=True, inicio=99) == ["x 099.jpg", "x 100.jpg", "x 101.jpg"]                        # largura cresce sozinha
    assert nomes(separador="sublinhado") == ["x_01.jpg", "x_02.jpg", "x_03.jpg"]
    assert nomes(separador="nenhum") == ["x01.jpg", "x02.jpg", "x03.jpg"]


def test_continua_a_numeracao_que_ja_existe_na_pasta(tmp_path):
    criar(tmp_path, ["branco 01.jpg", "branco 02.jpg", "branco 07.png", "preto 09.jpg"])
    novos = criar(tmp_path, ["a.jpg", "b.jpg"])
    p = n.montar_plano(novos, n.Opcoes(nome="branco"))
    assert [Path(b).name for _, b in p.pares] == ["branco 08.jpg", "branco 09.jpg"] and p.avisos
    p2 = n.montar_plano(novos, n.Opcoes(nome="branco", continuar=False))
    assert p2.erro and "branco 01.jpg" in p2.erro                                                         # conflito detectado, nada sobrescrito
    assert n.montar_plano(novos, n.Opcoes(nome="branco", inicio=20)).erro == ""


def test_nome_invalido_e_vazio(tmp_path):
    arqs = criar(tmp_path, ["a.jpg"])
    assert n.nome_seguro('  bra:nco/<1>?  ') == "branco1"
    assert n.montar_plano(arqs, n.Opcoes(nome="")).erro and n.montar_plano([], n.Opcoes(nome="x")).erro
    assert n.montar_plano(arqs, n.Opcoes(nome='a/b*c')).pares[0][1].endswith("abc 01.jpg")


def test_executar_com_nomes_que_se_cruzam_e_desfazer(tmp_path):
    arqs = criar(tmp_path, ["branco 02.jpg", "branco 01.jpg"], [100, 200])        # os nomes novos colidem com os antigos
    p = n.montar_plano(arqs, n.Opcoes(nome="branco", continuar=False, inicio=1))
    assert p.erro == ""
    feitos = n.executar(p.pares)
    assert (tmp_path / "branco 01.jpg").read_bytes() == b"x" and (tmp_path / "branco 02.jpg").read_bytes() == b"xx"   # conteudos trocados certo
    assert n.desfazer(feitos) == 2
    assert (tmp_path / "branco 02.jpg").read_bytes() == b"x" and (tmp_path / "branco 01.jpg").read_bytes() == b"xx"
    assert not list(tmp_path.glob("__*"))                                                                       # nada temporario sobrando


def test_executar_reverte_se_falhar(tmp_path, monkeypatch):
    arqs = criar(tmp_path, ["a.jpg", "b.jpg", "c.jpg"])
    p = n.montar_plano(arqs, n.Opcoes(nome="x", ordem="nome"))
    real, chamadas = os.rename, []
    def falha(a, b):
        chamadas.append(1)
        if len(chamadas) == 5: raise OSError("arquivo em uso")
        return real(a, b)
    monkeypatch.setattr(os, "rename", falha)
    with pytest.raises(OSError):
        n.executar(p.pares)
    monkeypatch.setattr(os, "rename", real)
    assert sorted(f.name for f in tmp_path.iterdir()) == ["a.jpg", "b.jpg", "c.jpg"]                             # tudo como era


def test_historico_permite_desfazer_depois(tmp_path):
    h = n.Historico(tmp_path / "dados" / "hist.json", limite=2)
    assert h.ultimo() is None
    for i in range(3): h.registrar([(f"n{i}", f"a{i}")], f"nome{i}")
    assert h.ultimo()["nome"] == "nome2" and len(h._ler()) == 2
    h.remover_ultimo()
    assert h.ultimo()["nome"] == "nome1"


def test_ordem_por_data_da_foto_exif(tmp_path):
    from PIL import Image
    a, b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    for f, data in ((a, "2026:01:05 10:00:00"), (b, "2026:01:01 09:00:00")):
        im = Image.new("RGB", (20, 20)); ex = im.getexif(); ex[0x0132] = data; im.save(f, exif=ex)
    os.utime(a, (100, 100)); os.utime(b, (200, 200))                                   # data do arquivo diz o contrario
    assert [Path(x).name for x in n.ordenar([str(a), str(b)], "foto")] == ["b.jpg", "a.jpg"]
    assert [Path(x).name for x in n.ordenar([str(a), str(b)], "data")] == ["a.jpg", "b.jpg"]


def test_atalho_e_config(tmp_path):
    from renomeador.windows import interpretar_atalho, formatar_atalho
    assert interpretar_atalho("Ctrl+Alt+R") == (3, ord("R")) and formatar_atalho("alt+control+r") == "Ctrl+Alt+R"
    assert interpretar_atalho("Ctrl+Shift+F5") == (6, 0x74)
    for ruim in ("R", "Ctrl+", "Ctrl+Alt+Home"):
        with pytest.raises(ValueError):
            interpretar_atalho(ruim)
    from renomeador.config import Config
    c = Config()
    for nome in ("branco", "preto", "Branco", "bege"): c.lembrar_nome(nome)
    assert c.ultimos_nomes == ["bege", "Branco", "preto"]
    c.salvar(tmp_path / "c.json")
    assert Config.carregar(tmp_path / "c.json").ultimos_nomes == ["bege", "Branco", "preto"] and Config.carregar(tmp_path / "nao.json").atalho == "Ctrl+Alt+R"
