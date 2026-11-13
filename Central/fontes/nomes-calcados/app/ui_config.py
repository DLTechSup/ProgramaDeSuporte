"""Assistente de configuracao das chaves (um provedor por vez). O login e sempre feito pelo usuario no navegador."""
from __future__ import annotations

import threading
import webbrowser
from tkinter import messagebox

import customtkinter as ctk

from .provedores import Provedores, detectar_chave

PASSOS = {
    "google": "Entre com seu Gmail, clique em \"Create API key\", copie a chave e volte aqui.",
    "groq": "Entre (pode ser com a conta Google), crie uma chave em \"API Keys\", copie e volte aqui.",
    "openrouter": "Entre (pode ser com a conta Google), crie uma chave, copie e volte aqui.",
}


def abrir_assistente(app, prov: Provedores, ao_fechar=lambda: None) -> None:
    win = ctk.CTkToplevel(app)
    win.title("Configurar chaves de IA")
    win.geometry("640x470")
    win.after(150, win.focus)
    itens = prov.itens
    estado = {"i": 0}

    cab = ctk.CTkLabel(win, text="", font=("Segoe UI", 16, "bold"))
    cab.pack(pady=(14, 2))
    sub = ctk.CTkLabel(win, text="", wraplength=580, justify="left")
    sub.pack(padx=20)
    status = ctk.CTkLabel(win, text="", text_color="gray35")
    status.pack(pady=4)
    entrada = ctk.CTkEntry(win, width=520, show="•")
    entrada.pack(pady=8)
    msg = ctk.CTkLabel(win, text="", wraplength=580)
    msg.pack(pady=4)
    linha = ctk.CTkFrame(win, fg_color="transparent")
    linha.pack(pady=4)
    rodape = ctk.CTkFrame(win, fg_color="transparent")
    rodape.pack(side="bottom", pady=14)

    def item():
        return itens[estado["i"]]

    def mostrar():
        it = item()
        obrig = it.get("obrigatorio")
        cab.configure(text=f"{estado['i'] + 1} de {len(itens)} — {it['nome']}" + ("  (obrigatório)" if obrig else "  (opcional)"))
        sub.configure(text=PASSOS.get(it["id"], "") + "\nCom só a chave do Google o programa já funciona.")
        atual = prov.chave(it)
        status.configure(text="Chave já salva: " + ("•" * 8 + atual[-4:]) if atual else "Nenhuma chave salva ainda.")
        entrada.delete(0, "end")
        msg.configure(text="")
        pular.configure(text="Pular, configurar depois" if estado["i"] < len(itens) - 1 else "Concluir")
        checar_area()

    def checar_area():
        try:
            achada = detectar_chave(win.clipboard_get(), item()["id"])
        except Exception:  # noqa: BLE001
            achada = ""
        if achada:
            colar.configure(text="Colar a chave que está na área de transferência", state="normal")
        else:
            colar.configure(text="Colar da área de transferência", state="normal")
        win.after(1500, lambda: win.winfo_exists() and checar_area())

    def abrir_pagina():
        webbrowser.open(item()["url_chaves"])

    def colar_chave():
        try:
            txt = win.clipboard_get().strip()
        except Exception:  # noqa: BLE001
            txt = ""
        entrada.delete(0, "end")
        entrada.insert(0, detectar_chave(txt, item()["id"]) or txt)

    def testar():
        chave = entrada.get().strip()
        if not chave:
            msg.configure(text="Cole a chave primeiro.", text_color="firebrick")
            return
        msg.configure(text="Testando...", text_color="gray35")

        def trabalho():
            ok, texto = prov.testar(item(), chave)
            def fim():
                if ok:
                    prov.salvar_chave(item(), chave)
                    msg.configure(text="✅ " + texto + " Chave salva.", text_color="forest green")
                    status.configure(text="Chave salva: " + "•" * 8 + chave[-4:])
                else:
                    msg.configure(text="❌ " + texto, text_color="firebrick")
            win.after(0, fim)
        threading.Thread(target=trabalho, daemon=True).start()

    def avancar():
        if estado["i"] < len(itens) - 1:
            estado["i"] += 1
            mostrar()
        else:
            ao_fechar()
            win.destroy()

    ctk.CTkButton(linha, text="Abrir a página da chave no navegador", command=abrir_pagina).pack(side="left", padx=6)
    colar = ctk.CTkButton(linha, text="Colar da área de transferência", command=colar_chave)
    colar.pack(side="left", padx=6)
    ctk.CTkButton(linha, text="Testar e salvar", command=testar).pack(side="left", padx=6)
    pular = ctk.CTkButton(rodape, text="Pular, configurar depois", fg_color="gray50", command=avancar)
    pular.pack(side="left", padx=8)
    ctk.CTkButton(rodape, text="Próximo", command=avancar).pack(side="left", padx=8)
    mostrar()
