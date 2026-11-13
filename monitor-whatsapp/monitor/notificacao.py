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
    if d.get("tipo") == "I":
        extra = f" · {d['fotos']} foto(s)" if d.get("fotos") else ""
        return f"💬 {d['grupo']}", d["previa"], f"{d['mensagens']} mensagem(ns) salva(s) em texto{extra}"
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
        faixa, fundo = ("#E0A030", "#FFF9EC") if conferir else ("#0E7C66", "#FFFFFF")
        w = tk.Toplevel(self.raiz)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg="#C9D1D9")                                   # borda fina
        corpo = tk.Frame(w, bg=fundo)
        corpo.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(corpo, bg=faixa, width=6).pack(side="left", fill="y")
        texto = tk.Frame(corpo, bg=fundo)
        texto.pack(side="left", fill="both", expand=True, padx=12, pady=8)
        tk.Label(texto, text=titulo, bg=fundo, fg=faixa if not conferir else "#8A5A00", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(texto, text=l1, bg=fundo, fg="#1F2933", font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(texto, text=l2, bg=fundo, fg="#6B7785", font=("Segoe UI", 9), anchor="w").pack(fill="x")
        for parte in (w, corpo, texto, *texto.winfo_children()):
            parte.bind("<Button-1>", lambda _e, x=w: self._fechar(x))
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
