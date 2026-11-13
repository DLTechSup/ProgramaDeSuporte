"""Ponto de entrada do Monitor de Demandas (python programa.py  /  .exe)."""
import sys


def main() -> None:
    if "--selftest" in sys.argv:
        from monitor.autoteste import rodar
        rodar()
        return
    import os
    import socket
    trava = socket.socket()
    try:
        trava.bind(("127.0.0.1", 47653))          # so uma copia do programa por vez
    except OSError:
        from tkinter import Tk, messagebox
        raiz = Tk()
        raiz.withdraw()
        messagebox.showinfo("Monitor de Demandas", "O Monitor de Demandas já está aberto.\nProcure o ícone perto do relógio (bandeja do Windows).")
        return
    from monitor.app import Janela
    Janela().mainloop()
    os._exit(0)     # garante que nenhuma thread da bandeja mantenha o programa vivo depois de fechar


if __name__ == "__main__":
    main()
