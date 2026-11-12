import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import pesquisa as P

HTML = """<html><head><title>Sandália BR Sport 2282.107 Preta</title>
<meta property="og:image" content="https://x.com/foto.jpg"><meta property="og:description" content="Sandália masculina">
</head><body><script>var x=1</script><ul><li>Material: Napa Monaco</li><li>Solado: PVC</li>
<li>Altura do salto: 3,5 cm</li><li>Peso: 380 g do par</li><li>Cor: CAFE 569/CONHAQUE 1273</li></ul></body></html>"""


def test_formatos_e_consultas():
    assert P.formatos_referencia("2282.107") == ["2282.107", "2282-107", "2282107"]
    assert len(P.montar_consultas("BR Sport", "2282.107", "sandália", "masculina")) >= 4
    assert P.prefixo_irma("2282.107") == "2282"


def test_bloqueio_calcados24h():
    assert P.bloqueado("https://www.calcados24h.com.br/x") and not P.bloqueado("https://outra.com.br")


def test_ler_html_e_peso():
    pg = P.ler_html("https://loja.com/p", HTML)
    assert pg.imagem.endswith("foto.jpg") and pg.dados["material"].startswith("Napa")
    assert pg.dados["salto"] == "3,5 cm" and "380 g (do par)" in pg.dados["peso"]
    assert "caixa" in P.extrair_peso("Embalagem: caixa com peso 769 g dimensões 30x20").lower()


def test_exata_irma():
    assert P.classificar_referencia("ref 2282-107 preta", "2282.107") == (True, False)
    assert P.classificar_referencia("modelo 2282.101", "2282.107") == (False, True)
    assert P.classificar_referencia("nada", "2282.107") == (False, False)


def test_sugerir_cor():
    assert P.sugerir_cor("CAFE 569/CONHAQUE 1273") == "Café/Conhaque"
    assert P.sugerir_cor("PRETO 01/CARAMELO 787") == "Preto/Caramelo"


def test_pesquisar_com_busca_falsa_e_log(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "LOGS", tmp_path)
    busca = lambda c: [{"href": "https://calcados24h.com.br/a"}, {"href": "https://loja.com/p"}]
    r = P.pesquisar("BR Sport", "2282.107", "sandália", "masculina", busca=busca, abrir=lambda u: HTML)
    assert len(r.consultas) >= 4 and len(r.paginas) == 1 and r.paginas[0].exata
    assert r.peso.startswith("380 g") and r.cor_sugerida == "Café/Conhaque"
    assert P.candidatos_sem_foto(r)[0].site == "loja.com"
    txt = P.salvar_log("BR Sport", "2282.107", r)
    assert "Peso" in txt and list(tmp_path.rglob("*.md"))
