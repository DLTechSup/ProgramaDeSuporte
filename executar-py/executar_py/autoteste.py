"""Autoteste usado no build (Windows): chama o programa (ja rodando dentro do .exe) para executar scripts
de verdade com o Python do sistema. Nao usa sys.executable (dentro do .exe congelado ele e' o proprio
ExecutarPy.exe, nao um python.exe) -- chama main() direto, em processo."""
from __future__ import annotations

import io
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path


def _raiz() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


def rodar() -> None:
    raiz = _raiz()
    passos = raiz / "selftest_passos.txt"

    def passo(t: str) -> None:
        with open(passos, "a", encoding="utf-8") as f:
            f.write(t + "\n")

    try:
        os.environ["EXECUTARPY_TESTE"] = "1"
        from .main import main

        passo("1 preparando scripts de teste")
        tmp = Path(tempfile.mkdtemp())
        ok, erro = tmp / "ok.py", tmp / "erro.py"
        ok.write_text("print('ola do autoteste')\n")
        erro.write_text("raise ValueError('falha proposital')\n")

        passo("2 rodando um script que funciona")
        buf = io.StringIO()
        with redirect_stdout(buf):
            codigo = main([str(ok)])
        saida = buf.getvalue()
        assert codigo == 0 and "terminou normalmente" in saida, saida
        passo("3 ok: código de saída correto e mensagem final mostrada")

        passo("4 rodando um script com erro")
        buf = io.StringIO()
        with redirect_stdout(buf):
            codigo = main([str(erro)])
        saida = buf.getvalue()
        assert codigo == 1 and "terminou com erro" in saida, saida
        passo("5 ok: erro foi mostrado e código de saída != 0")

        (raiz / "selftest_ok.txt").write_text("ok", encoding="utf-8")
    except Exception:  # noqa: BLE001
        import traceback
        (raiz / "selftest_erro.txt").write_text(traceback.format_exc(), encoding="utf-8")


if __name__ == "__main__":
    rodar()
