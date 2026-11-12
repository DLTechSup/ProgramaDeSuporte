import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image
from separador_fotos.marcas import MARCAS_PADRAO, detectar_marca
from separador_fotos.referencia import extrair_referencia
from separador_fotos.organizador import processar_pasta


def test_referencias():
    assert extrair_referencia("BEIRA RIO\nREF: 123.456\nCOR PRETO") == "123.456"
    assert extrair_referencia("Ref. 987.654 Tam 37 7891234567890") == "987.654"
    assert extrair_referencia("REFERÊNCIA\n4235-101") == "4235-101"
    assert extrair_referencia("7891234567890 LOTE 5521.100") == "5521.100"
    assert extrair_referencia("sem numero") is None


def test_marca_com_erro_de_ocr():
    assert detectar_marca("Dakota", MARCAS_PADRAO) == "Dakota"
    assert detectar_marca("VIA JÚPITER", MARCAS_PADRAO) == "Via Jupiter"
    assert detectar_marca("BEIRA  RI0 calçados", MARCAS_PADRAO) == "Beira Rio"


def test_fluxo_completo():
    textos = {
        "a.jpg": "BEIRA RIO REF: 123.456", "b.jpg": "Beira Rio\nREF 123-456",
        "c.jpg": "BEIRA RIO REF: 987.654", "d.jpg": "DAKOTA REF 555.111",
        "e.jpg": "borrado",
    }
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        for n in textos:
            Image.new("RGB", (10, 10)).save(base / n)
        fila = iter(textos.values())
        # cada foto gera 1 leitura; o motor falso devolve o texto na ordem alfabética
        res = processar_pasta(base, ler=lambda img: next(fila, ""))
        nomes = {p.name for p in base.iterdir() if p.is_dir()}
        assert "Beira Rio - 123.456" in nomes and "Beira Rio - 987.654" in nomes
        assert "Dakota - 555.111" in nomes and "_Nao_identificadas" in nomes
        assert len(list((base / "Beira Rio - 123.456").iterdir())) == 2
        assert all((base / n).exists() for n in textos)  # originais intactos
        assert (base / "relatorio_separacao.csv").exists()
