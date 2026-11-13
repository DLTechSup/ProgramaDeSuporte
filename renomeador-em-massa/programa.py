"""Renomeador em Massa: fica na bandeja; o atalho (padrao Ctrl+Alt+R) abre a janela para renomear os arquivos selecionados."""
import os
import sys


def main() -> None:
    if "--selftest" in sys.argv:
        from renomeador.autoteste import rodar
        rodar()
        return
    from renomeador import instancia
    servidor = instancia.ser_o_unico()
    if servidor is None:                                   # ja esta aberto na bandeja: so pede para abrir a janela
        instancia.avisar_o_que_ja_esta_aberto("escolher")
        return
    from renomeador.app import Aplicativo
    app = Aplicativo()
    instancia.escutar(servidor, lambda cmd: app.pedir("escolher" if cmd in ("abrir", "escolher") else cmd))
    app.mainloop()
    os._exit(0)


if __name__ == "__main__":
    main()
