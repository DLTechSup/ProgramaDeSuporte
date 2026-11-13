"""Aviso na tela (canto inferior direito) a cada item salvo. Fica por cima de tudo, mesmo com a janela minimizada."""
from __future__ import annotations

import sys
try:
    import tkinter as tk
except ImportError:      # so para poder testar o texto em maquinas sem tkinter
    tk = None  # type: ignore[assignment]

DURACAO_MS = 7000
MAX_VISIVEIS = 4
LARGURA, ALTURA, MARGEM = 380, 86, 10


def texto_do_aviso(d: dict) -> tuple[str, str, str]:
    """(titulo, linha 1, linha 2) a partir do evento 'salvo'."""
    marca = d["marca"] if d["marca"] and d["marca"] != "?" else ""
    nome = f"{marca} {d['referencia']}".strip()
    if d["situacao"] == "conferir":
        titulo = f"⚠ {d['grupo']} — conferir"
    elif d["nova"]:
        titulo = f"✔ {d['grupo']}"
    else:
        titulo = f"＋ {d['grupo']} — mais fotos"
    fotos = f"{d['novas']} foto(s) salva(s)" + ("" if d["nova"] else f" (total {d['total']})")
    return titulo, nome, fotos + (f" · {d['obs']}" if d["obs"] else "")


class Notificador:
    def __init__(self, raiz: tk.Misc) -> None:
        self.raiz = raiz
        self.abertos: list[tk.Toplevel] = []
        self.fila: list[dict] = []
        self.ligado = True
        self.som = True

    def mostrar(self, d: dict) -> None:
        if not self.ligado:
            return
        if len(self.abertos) >= MAX_VISIVEIS:
            self.fila.append(d)
            return
        self._criar(d)

    def _criar(self, d: dict) -> None:
        titulo, l1, l2 = texto_do_aviso(d)
        conferir = d["situacao"] == "conferir"
        w = tk.Toplevel(self.raiz)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        fundo = "#7a4b00" if conferir else "#1f3a2a"
        w.configure(bg=fundo, highlightthickness=1, highlightbackground="#000000")
        tk.Label(w, text=titulo, bg=fundo, fg="#ffffff", font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(w, text=l1, bg=fundo, fg="#ffffff", font=("Segoe UI", 12), anchor="w").pack(fill="x", padx=12)
        tk.Label(w, text=l2, bg=fundo, fg="#d7e8dc", font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=12, pady=(0, 6))
        w.bind("<Button-1>", lambda _e, x=w: self._fechar(x))
        for filho in w.winfo_children():
            filho.bind("<Button-1>", lambda _e, x=w: self._fechar(x))
        self.abertos.append(w)
        self._posicionar()
        if self.som:
            self._beep()
        w.after(DURACAO_MS, lambda x=w: self._fechar(x))

    def _posicionar(self) -> None:
        sw, sh = self.raiz.winfo_screenwidth(), self.raiz.winfo_screenheight()
        for i, w in enumerate(self.abertos):
            x = sw - LARGURA - MARGEM
            y = sh - 60 - MARGEM - (i + 1) * (ALTURA + MARGEM)     # 60 = altura aproximada da barra de tarefas
            w.geometry(f"{LARGURA}x{ALTURA}+{x}+{max(0, y)}")

    def _fechar(self, w: tk.Toplevel) -> None:
        if w in self.abertos:
            self.abertos.remove(w)
            try:
                w.destroy()
            except tk.TclError:
                pass
            self._posicionar()
            if self.fila:
                self._criar(self.fila.pop(0))

    @staticmethod
    def _beep() -> None:
        try:
            if sys.platform.startswith("win"):
                import winsound
                winsound.MessageBeep()
        except Exception:  # noqa: BLE001
            pass
