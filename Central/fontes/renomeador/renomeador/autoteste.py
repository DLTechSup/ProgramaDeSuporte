"""Autoteste do build (Windows): atalho global, leitura da selecao do Explorador, janela, renomear e desfazer, bandeja."""
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
        time.sleep(90)
        (raiz / "selftest_erro.txt").write_text("TRAVOU (veja selftest_passos.txt)", encoding="utf-8")
        os._exit(2)
    threading.Thread(target=vigia, daemon=True).start()
    try:
        tmp = Path(tempfile.mkdtemp())
        os.environ["RENOMEADOR_DADOS"] = str(tmp / "dados")
        passo("1 criando o programa")
        from PIL import Image
        from .app import Aplicativo
        from .dialogo import Dialogo
        from .windows import EH_WINDOWS, arquivos_selecionados
        app = Aplicativo(atalho_teste="Ctrl+Alt+Shift+F11")
        app.update()
        registrado = app.atalho.registrado
        passo(f"2 atalho global: {'registrado' if registrado else 'NAO registrado'} / bandeja: {'ativa' if app.tem_bandeja else 'INATIVA'}")
        if EH_WINDOWS:
            import ctypes
            assert registrado, "o atalho global nao foi registrado"
            lista = arquivos_selecionados(int(ctypes.windll.user32.GetForegroundWindow() or 0))
            passo(f"3 leitura da selecao do Explorador executou sem erro ({len(lista)} arquivo(s))")
        passo("4 janela de renomear")
        pasta = tmp / "fotos"
        pasta.mkdir()
        arqs = []
        for i, nome in enumerate(["IMG_9.JPG", "IMG_10.JPG", "IMG_2.JPG"]):
            f = pasta / nome
            Image.new("RGB", (60, 60), (200, 10 * i, 30)).save(f)
            os.utime(f, (1700000000 + i, 1700000000 + i))
            arqs.append(str(f))
        d = Dialogo(app, arqs, app.cfg, app._concluido)
        d.var_nome.set("branco")
        d.update()
        d._previa()
        d._renomear()
        app.update()
        assert sorted(p.name for p in pasta.iterdir()) == ["branco 01.jpg", "branco 02.jpg", "branco 03.jpg"], sorted(p.name for p in pasta.iterdir())
        passo("5 renomeou em sequencia")
        app.desfazer_ultimo()
        app.update()
        assert sorted(p.name for p in pasta.iterdir()) == ["IMG_10.JPG", "IMG_2.JPG", "IMG_9.JPG"], sorted(p.name for p in pasta.iterdir())
        passo("6 desfez")
        (raiz / "selftest_ok.txt").write_text(f"ok; atalho={'registrado' if registrado else 'NAO'}; bandeja={'ativa' if app.tem_bandeja else 'INATIVA'}", encoding="utf-8")
        app.destroy()
    except Exception:  # noqa: BLE001
        (raiz / "selftest_erro.txt").write_text(traceback.format_exc(), encoding="utf-8")
    os._exit(0)
