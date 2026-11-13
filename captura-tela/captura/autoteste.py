"""Autoteste do build (Windows): toda a cadeia selecao -> captura -> arquivo -> clipboard, sem precisar de mouse real."""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path


def _raiz() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


def rodar() -> None:
    raiz = _raiz()

    def passo(t: str) -> None:
        with open(raiz / "selftest_passos.txt", "a", encoding="utf-8") as f:
            f.write(t + "\n")

    def vigia():
        time.sleep(60)
        (raiz / "selftest_erro.txt").write_text("TRAVOU (veja selftest_passos.txt)", encoding="utf-8")
        os._exit(2)
    threading.Thread(target=vigia, daemon=True).start()
    try:
        tmp = Path(tempfile.mkdtemp())
        os.environ["CAPTURA_DADOS"] = str(tmp / "dados")
        passo("1 criando o programa")
        from .app import Aplicativo
        app = Aplicativo()
        app.update()
        passo(f"2 ouvinte do mouse: {'ativo' if app.gatilho_ativo else 'INATIVO'} / bandeja: {'ativa' if app.tem_bandeja else 'INATIVA'}")

        passo("3 simulando o gatilho (os dois botoes do mouse)")
        app.cfg.pasta_destino = str(tmp / "capturas")
        app.gatilho.clique(100, 100, "esquerdo", True)
        app.gatilho.clique(100, 100, "direito", True)   # dispara o inicio (dentro da janela de tempo)
        app._ler_eventos()
        app.update()
        assert app.overlay is not None, "a janela de selecao nao abriu"
        app.gatilho.ao_mover(260, 220)
        app._ler_eventos()
        app.update()
        app.gatilho.clique(260, 220, "esquerdo", False)   # solta: finaliza a selecao
        app._ler_eventos()
        app.update()
        passo("4 selecao finalizada; conferindo o arquivo")

        destino = Path(app.cfg.pasta_destino)
        arquivos = list(destino.glob("*.png")) if destino.exists() else []
        assert len(arquivos) == 1, f"esperava 1 captura salva, achei {len(arquivos)}"
        from PIL import Image
        with Image.open(arquivos[0]) as im:
            assert im.width >= 100 and im.height >= 100, f"tamanho da captura inesperado: {im.size}"
        passo(f"5 ok: {arquivos[0].name} ({im.size[0]}x{im.size[1]})")

        from .windows import copiar_imagem
        colou = copiar_imagem(Image.new("RGB", (20, 20), "red"))
        passo(f"6 copiar para a área de transferência: {'ok' if colou else 'nao funcionou'}")

        app.destroy()
        (raiz / "selftest_ok.txt").write_text(f"ok; mouse={'ativo' if app.gatilho_ativo else 'INATIVO'}; "
                                              f"bandeja={'ativa' if app.tem_bandeja else 'INATIVA'}; clipboard={'ok' if colou else 'falhou'}",
                                              encoding="utf-8")
    except Exception:  # noqa: BLE001
        (raiz / "selftest_erro.txt").write_text(traceback.format_exc(), encoding="utf-8")
    os._exit(0)
