"""Uma copia so do programa: se abrir de novo, a copia que ja esta na bandeja recebe o pedido de abrir a janela."""
from __future__ import annotations

import socket
import threading
from typing import Callable

PORTA = 47654


def ser_o_unico() -> socket.socket | None:
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", PORTA))
        s.listen(5)
        return s
    except OSError:
        s.close()
        return None


def escutar(servidor: socket.socket, ao_receber: Callable[[str], None]) -> None:
    def laco():
        while True:
            try:
                c, _ = servidor.accept()
                with c:
                    ao_receber(c.recv(64).decode("utf-8", "ignore").strip() or "abrir")
            except OSError:
                return
    threading.Thread(target=laco, daemon=True).start()


def avisar_o_que_ja_esta_aberto(comando: str = "abrir") -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORTA), timeout=2) as c:
            c.sendall(comando.encode("utf-8"))
        return True
    except OSError:
        return False
