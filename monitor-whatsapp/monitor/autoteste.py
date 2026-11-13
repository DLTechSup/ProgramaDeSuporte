"""Autoteste usado no build do .exe (Windows): abre a janela, abre o Edge sem tela e roda um ciclo na pagina de teste."""
from __future__ import annotations

import os
import tempfile
import threading
import time
import traceback
from pathlib import Path

from .config import RAIZ


def _passo(txt: str) -> None:
    with open(RAIZ / "selftest_passos.txt", "a", encoding="utf-8") as f:
        f.write(txt + "\n")


def rodar() -> None:
    def vigia():
        time.sleep(110)
        (RAIZ / "selftest_erro.txt").write_text("TRAVOU (veja selftest_passos.txt)", encoding="utf-8")
        os._exit(2)
    threading.Thread(target=vigia, daemon=True).start()
    try:
        _passo("1 janela")
        from .app import Janela
        j = Janela(selftest=True)
        j.mainloop()
        _passo("2 navegador sem tela + pagina de teste")
        from .config import Config, Grupo
        from .fixture_teste import criar
        from .leitor import Navegador
        from .motor import Processador
        tmp = Path(tempfile.mkdtemp())
        nav = Navegador(headless=True, perfil=tmp / "perfil", url=criar(tmp))
        nav.iniciar()
        try:
            assert nav.logado(), "pagina de teste nao carregou"
            cfg = Config(pasta_base=str(tmp / "saida"), grupos=[Grupo("Demandas Fotos", "A")])
            p = Processador(cfg, nav)
            _passo("3 ciclo de leitura")
            p.ciclo()
            n = len(p.listas['Demandas Fotos'].itens)
            assert n == 2, f"esperava 2 demandas, achei {n}"
        finally:
            nav.fechar()
        _passo("4 leitor de etiquetas (OCR) dentro do .exe")
        from PIL import Image, ImageDraw, ImageFont
        import io
        from .marcas import carregar_marcas
        from .motor import ler_etiqueta
        from .ocr import criar_motor
        img = Image.new("RGB", (900, 300), "white")
        ImageDraw.Draw(img).text((40, 100), "BEIRA RIO  REF: 123.456", fill="black", font=ImageFont.load_default(size=56))
        buf = io.BytesIO()
        img.save(buf, "JPEG")
        marca, ref = ler_etiqueta(criar_motor(), buf.getvalue(), carregar_marcas(None))
        assert (marca, ref) == ("BEIRA RIO", "123.456"), f"OCR leu {marca!r} {ref!r}"
        (RAIZ / "selftest_ok.txt").write_text("ok", encoding="utf-8")
    except Exception:  # noqa: BLE001
        (RAIZ / "selftest_erro.txt").write_text(traceback.format_exc(), encoding="utf-8")
    os._exit(0)
