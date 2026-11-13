r"""Executa um .py num console, mostra o resultado e espera Enter antes de fechar.
Uso: ExecutarPy.exe caminho\do\script.py [argumentos do script...]
(e' isto que fica associado ao duplo clique nos arquivos .py)
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys

from .nucleo import interpretar_saida, preparar_execucao, separar_argumentos

VERDE, VERMELHO, AMARELO, RESET = "\x1b[92m", "\x1b[91m", "\x1b[93m", "\x1b[0m"


def _ativar_cores_ansi() -> None:
    if sys.platform.startswith("win"):
        try:
            k = ctypes.windll.kernel32
            h = k.GetStdHandle(-11)
            modo = ctypes.c_uint32()
            k.GetConsoleMode(h, ctypes.byref(modo))
            k.SetConsoleMode(h, modo.value | 0x0004)
        except Exception:  # noqa: BLE001
            pass


def _titulo(caminho: str) -> None:
    if sys.platform.startswith("win"):
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(f"{os.path.basename(caminho)} — Executar .py")
        except Exception:  # noqa: BLE001
            pass


def _pausar(mensagem: str = "Pressione Enter para sair...") -> None:
    if os.environ.get("EXECUTARPY_TESTE"):   # usado so pelo autoteste do build, para nao travar esperando Enter
        return
    try:
        input(f"\n{mensagem}")
    except (EOFError, KeyboardInterrupt):
        pass


def main(argv: list[str] | None = None) -> int:
    if argv is None and len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        from .autoteste import rodar
        rodar()
        return 0
    _ativar_cores_ansi()
    caminho, argumentos = separar_argumentos(sys.argv[1:] if argv is None else argv)
    _titulo(caminho or "Executar .py")
    r = preparar_execucao(caminho, argumentos)
    if not r.ok:
        print(f"{VERMELHO}✘ {r.mensagem}{RESET}")
        _pausar()
        return 1
    print(f"{AMARELO}▶ Executando: {os.path.basename(caminho)}{RESET}\n")
    try:
        codigo = subprocess.call(r.comando, cwd=os.path.dirname(os.path.abspath(caminho)) or None)
    except KeyboardInterrupt:
        codigo = -2
    except OSError as e:
        print(f"{VERMELHO}✘ Não consegui iniciar o Python: {e}{RESET}")
        _pausar()
        return 1
    rotulo, tipo = interpretar_saida(codigo)
    cor = VERDE if tipo == "ok" else VERMELHO
    marca = "✔" if tipo == "ok" else "✘"
    print(f"\n{cor}{marca} {rotulo}{RESET}")
    _pausar()
    return 0 if codigo == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
