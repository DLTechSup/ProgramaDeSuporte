"""Ponto de entrada do Monitor de Demandas (python programa.py  /  .exe)."""
import sys


def main() -> None:
    if "--selftest" in sys.argv:
        from monitor.autoteste import rodar
        rodar()
        return
    from monitor.app import Janela
    Janela().mainloop()


if __name__ == "__main__":
    main()
