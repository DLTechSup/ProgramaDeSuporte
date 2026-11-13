"""Ponto de entrada (PyInstaller): python programa.py"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    if "--selftest" in sys.argv:
        from captura.autoteste import rodar
        rodar()
        return
    from captura.app import Aplicativo
    app = Aplicativo()
    app.mainloop()
    os._exit(0)


if __name__ == "__main__":
    main()
