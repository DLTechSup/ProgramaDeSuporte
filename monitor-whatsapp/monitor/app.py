"""Janela do Monitor de Demandas."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .armazenamento import nome_pasta_grupo, pasta_do_dia
from .config import ARQUIVO, RAIZ, TIPOS, Config, Grupo
from .lista import ListaDoDia
from .notificacao import Notificador
from .servico import Servico


def abrir_no_windows(caminho: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(caminho))      # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(caminho)])
    except Exception as e:  # noqa: BLE001
        messagebox.showerror("Não consegui abrir", str(e))


class Janela(ctk.CTk):
    def __init__(self, selftest: bool = False) -> None:
        super().__init__()
        self.title("Monitor de Demandas")
        self.geometry("980x700")
        self.minsize(860, 600)
        ctk.set_appearance_mode("light")
        self.cfg = Config.carregar()
        self.eventos: queue.Queue = queue.Queue()
        self.servico: Servico | None = None
        self.conversas: list[str] = []
        self.notificador = Notificador(self)
        self.notificador.ligado, self.notificador.som = self.cfg.notificar, self.cfg.som
        self.protocol("WM_DELETE_WINDOW", self._minimizar)
        self._topo()
        self.abas = ctk.CTkTabview(self)
        self.abas.pack(fill="both", expand=True, padx=10, pady=4)
        self._aba_demanda(self.abas.add("Demanda do dia"))
        self._aba_config(self.abas.add("Configurações"))
        self._aba_registro(self.abas.add("Registro"))
        self.barra = ctk.CTkLabel(self, text="Pronto. Clique em \"Abrir WhatsApp\".", anchor="w")
        self.barra.pack(fill="x", padx=14, pady=(0, 8))
        self._recarregar_lista()
        self.after(400, self._ler_eventos)
        if selftest:
            self.after(300, lambda: self.notificador.mostrar({"grupo": "TESTE", "pasta": "BEIRA RIO 123.456", "marca": "BEIRA RIO",
                       "referencia": "123.456", "novas": 3, "total": 3, "nova": True, "situacao": "ok", "obs": ""}))
            self.after(1200, self.destroy)

    # ---------------------------------------------------------------- topo
    def _topo(self) -> None:
        t = ctk.CTkFrame(self)
        t.pack(fill="x", padx=10, pady=(10, 4))
        self.b_abrir = ctk.CTkButton(t, text="Abrir WhatsApp", width=140, command=self._abrir_whatsapp)
        self.b_abrir.pack(side="left", padx=6, pady=6)
        self.b_monitor = ctk.CTkButton(t, text="Iniciar monitor", width=140, state="disabled", command=self._alternar_monitor)
        self.b_monitor.pack(side="left", padx=6)
        self.lbl_status = ctk.CTkLabel(t, text="Desligado", text_color="gray35")
        self.lbl_status.pack(side="left", padx=12)
        ctk.CTkButton(t, text="Sair de vez", width=100, fg_color="gray50", command=self._sair).pack(side="right", padx=6)

    def _abrir_whatsapp(self) -> None:
        if self.servico and self.servico.is_alive():
            return
        self.servico = Servico(self.cfg, self.eventos)
        self.servico.start()
        self.b_abrir.configure(state="disabled")

    def _alternar_monitor(self) -> None:
        if not self.servico:
            return
        if self.servico.monitorando:
            self.servico.pedir("pausar")
            self.b_monitor.configure(text="Iniciar monitor")
        else:
            if not self._config_ok():
                return
            self._guardar_config()
            self.servico.pedir("iniciar")
            self.b_monitor.configure(text="Pausar monitor")

    def _config_ok(self) -> bool:
        if not self.cfg.pasta_base or not self.cfg.grupos:
            messagebox.showinfo("Falta configurar", "Na aba Configurações, escolha a pasta das demandas e adicione os grupos.")
            self.abas.set("Configurações")
            return False
        return True

    # ------------------------------------------------------- demanda do dia
    def _aba_demanda(self, aba) -> None:
        linha = ctk.CTkFrame(aba, fg_color="transparent")
        linha.pack(fill="x")
        ctk.CTkButton(linha, text="Abrir pasta principal", width=170, command=self._abrir_pasta_dia).pack(side="left", padx=4)
        ctk.CTkButton(linha, text="Abrir lista do dia (.txt)", width=170, command=self._abrir_lista_txt).pack(side="left", padx=4)
        self.lbl_total = ctk.CTkLabel(linha, text="", text_color="gray30")
        self.lbl_total.pack(side="left", padx=12)
        self.quadro = ctk.CTkScrollableFrame(aba)
        self.quadro.pack(fill="both", expand=True, pady=6)

    def _pasta_do_dia(self, grupo: str) -> Path | None:
        return pasta_do_dia(Path(self.cfg.pasta_base), grupo, date.today()) if self.cfg.pasta_base else None

    def _todos_os_itens(self):
        """[(grupo, item)] de todos os grupos monitorados, de hoje."""
        saida = []
        for g in self.cfg.grupos:
            p = self._pasta_do_dia(g.nome)
            if p:
                saida += [(g.nome, i) for i in ListaDoDia(p).ordenados()]
        return sorted(saida, key=lambda x: (x[1].feito, x[1].situacao != "conferir", x[1].hora))

    def _recarregar_lista(self) -> None:
        for w in self.quadro.winfo_children():
            w.destroy()
        if not self.cfg.pasta_base or not self.cfg.grupos:
            ctk.CTkLabel(self.quadro, text="Escolha a pasta e adicione os grupos em Configurações.").pack(pady=30)
            self.lbl_total.configure(text="")
            return
        itens = self._todos_os_itens()
        feitos = sum(1 for _, i in itens if i.feito)
        self.lbl_total.configure(text=f"{len(itens)} demanda(s) hoje · {feitos} feita(s) · {sum(1 for _, i in itens if i.situacao == 'conferir')} para conferir")
        if not itens:
            ctk.CTkLabel(self.quadro, text="Nada chegou ainda hoje.").pack(pady=30)
        for grupo, it in itens:
            cor = "#fdecc8" if it.situacao == "conferir" else ("#dff3e0" if it.feito else None)
            linha = ctk.CTkFrame(self.quadro, fg_color=cor) if cor else ctk.CTkFrame(self.quadro)
            linha.pack(fill="x", pady=2, padx=2)
            var = ctk.BooleanVar(value=it.feito)
            ctk.CTkCheckBox(linha, text="", variable=var, width=26,
                            command=lambda g=grupo, k=it.chave, v=var: self._marcar(g, k, v.get())).pack(side="left", padx=(8, 2))
            ctk.CTkLabel(linha, text=it.hora, width=44).pack(side="left")
            marca = f"{it.marca} · " if it.marca and it.marca != "?" else ""
            ctk.CTkLabel(linha, text=f"{marca}{it.referencia}", anchor="w", font=("Segoe UI", 13, "bold"), width=300).pack(side="left", padx=6)
            ctk.CTkLabel(linha, text=f"{it.fotos} foto(s) · {nome_pasta_grupo(grupo)}", anchor="w", text_color="gray30", width=250).pack(side="left")
            if it.situacao == "conferir" or it.observacao:
                ctk.CTkLabel(linha, text=("⚠ " + it.observacao)[:70], text_color="#a15c00", anchor="w").pack(side="left", padx=6)
            ctk.CTkButton(linha, text="Abrir pasta", width=84, command=lambda g=grupo, p=it.pasta: self._abrir_sub(g, p)).pack(side="right", padx=6, pady=4)

    def _marcar(self, grupo: str, chave: str, feito: bool) -> None:
        pasta = self._pasta_do_dia(grupo)
        if pasta:
            ListaDoDia(pasta).marcar_feito(chave, feito)
            self._recarregar_lista()

    def _abrir_pasta_dia(self) -> None:
        """Abre a pasta principal (dentro dela ha uma pasta por grupo)."""
        if self.cfg.pasta_base and Path(self.cfg.pasta_base).exists():
            abrir_no_windows(Path(self.cfg.pasta_base))

    def _abrir_sub(self, grupo: str, nome: str) -> None:
        p = self._pasta_do_dia(grupo)
        if p and (p / nome).exists():
            abrir_no_windows(p / nome)

    def _abrir_lista_txt(self) -> None:
        """Abre a lista de hoje: se ha um grupo so, abre o dele; se ha varios, abre a pasta de cada um."""
        listas = [self._pasta_do_dia(g.nome) / "lista_do_dia.txt" for g in self.cfg.grupos if self._pasta_do_dia(g.nome)]
        existentes = [c for c in listas if c.exists()]
        if not existentes:
            messagebox.showinfo("Lista", "A lista ainda não foi criada (nada chegou hoje).")
        for c in existentes:
            abrir_no_windows(c)

    # ------------------------------------------------------- configuracoes
    def _aba_config(self, aba) -> None:
        ctk.CTkLabel(aba, text="Pasta principal (dentro dela o programa cria uma pasta para cada grupo ou pessoa, e dentro dela uma por dia):", anchor="w").pack(fill="x", padx=6, pady=(6, 0))
        linha = ctk.CTkFrame(aba, fg_color="transparent")
        linha.pack(fill="x", padx=6)
        self.e_pasta = ctk.CTkEntry(linha)
        self.e_pasta.pack(side="left", fill="x", expand=True)
        self.e_pasta.insert(0, self.cfg.pasta_base)
        ctk.CTkButton(linha, text="Escolher...", width=100, command=self._escolher_pasta).pack(side="left", padx=6)

        ctk.CTkLabel(aba, text="Grupos e conversas monitorados (quantos quiser):", anchor="w", font=("Segoe UI", 13, "bold")).pack(fill="x", padx=6, pady=(14, 0))
        self.quadro_grupos = ctk.CTkFrame(aba)
        self.quadro_grupos.pack(fill="x", padx=6, pady=4)

        add = ctk.CTkFrame(aba, fg_color="transparent")
        add.pack(fill="x", padx=6, pady=4)
        self.c_conversa = ctk.CTkComboBox(add, values=[""], width=340)
        self.c_conversa.set("")
        self.c_conversa.pack(side="left")
        self.c_tipo = ctk.CTkComboBox(add, values=list(TIPOS.values()), width=330)
        self.c_tipo.set(TIPOS["A"])
        self.c_tipo.pack(side="left", padx=6)
        ctk.CTkButton(add, text="Adicionar", width=90, command=self._adicionar_grupo).pack(side="left")
        ctk.CTkButton(aba, text="Atualizar lista de conversas (do WhatsApp aberto)", width=330, command=self._pedir_conversas).pack(anchor="w", padx=6, pady=2)
        ctk.CTkLabel(aba, anchor="w", text_color="gray35", wraplength=900, justify="left",
                     text="Dica: digite o nome do grupo ou da pessoa igualzinho ao do WhatsApp, ou use \"Atualizar lista\" e escolha na caixa (aparecem as conversas visíveis na lista lateral).").pack(fill="x", padx=6)

        self.v_hoje = ctk.BooleanVar(value=self.cfg.incluir_hoje)
        self.v_escond = ctk.BooleanVar(value=self.cfg.tentar_escondidas)
        ctk.CTkCheckBox(aba, text="Pegar também o que já chegou hoje (ao iniciar o monitor)", variable=self.v_hoje, command=self._guardar_config).pack(anchor="w", padx=6, pady=(14, 2))
        ctk.CTkCheckBox(aba, text="Álbum com \"+N\": tentar abrir e baixar todas as fotos", variable=self.v_escond, command=self._guardar_config).pack(anchor="w", padx=6, pady=2)
        self.v_aviso = ctk.BooleanVar(value=self.cfg.notificar)
        self.v_som = ctk.BooleanVar(value=self.cfg.som)
        ctk.CTkCheckBox(aba, text="Avisar na tela a cada item salvo (diz de qual grupo veio)", variable=self.v_aviso, command=self._guardar_config).pack(anchor="w", padx=6, pady=2)
        ctk.CTkCheckBox(aba, text="Tocar um som junto com o aviso", variable=self.v_som, command=self._guardar_config).pack(anchor="w", padx=6, pady=2)
        self._desenhar_grupos()

    def _escolher_pasta(self) -> None:
        p = filedialog.askdirectory(title="Pasta das demandas")
        if p:
            self.e_pasta.delete(0, "end")
            self.e_pasta.insert(0, p)
            self._guardar_config()
            self._recarregar_lista()

    def _tipo_da_caixa(self) -> str:
        t = self.c_tipo.get()
        return "B" if t.startswith("Grupo B") else ("I" if t.startswith("Conversa") else "A")

    def _adicionar_grupo(self) -> None:
        nome = self.c_conversa.get().strip()
        if not nome:
            return
        if any(g.nome == nome for g in self.cfg.grupos):
            messagebox.showinfo("Grupo", "Esse grupo já está na lista.")
            return
        self.cfg.grupos.append(Grupo(nome, self._tipo_da_caixa()))
        self.c_conversa.set("")
        self._guardar_config()
        self._desenhar_grupos()

    def _desenhar_grupos(self) -> None:
        for w in self.quadro_grupos.winfo_children():
            w.destroy()
        if not self.cfg.grupos:
            ctk.CTkLabel(self.quadro_grupos, text="Nenhum grupo ainda.", text_color="gray35").pack(padx=8, pady=6)
        for g in self.cfg.grupos:
            l = ctk.CTkFrame(self.quadro_grupos, fg_color="transparent")
            l.pack(fill="x", pady=1)
            ctk.CTkLabel(l, text=g.nome, anchor="w", width=330).pack(side="left", padx=8)
            ctk.CTkLabel(l, text=TIPOS[g.tipo], anchor="w", text_color="gray30").pack(side="left")
            ctk.CTkButton(l, text="Remover", width=80, fg_color="gray50", command=lambda x=g: self._remover(x)).pack(side="right", padx=6)

    def _remover(self, g: Grupo) -> None:
        self.cfg.grupos = [x for x in self.cfg.grupos if x is not g]
        self._guardar_config()
        self._desenhar_grupos()

    def _pedir_conversas(self) -> None:
        if not self.servico or not self.servico.is_alive():
            messagebox.showinfo("WhatsApp", "Clique em \"Abrir WhatsApp\" e entre com o QR code primeiro.")
            return
        self.servico.pedir("conversas")

    def _guardar_config(self) -> None:
        self.cfg.pasta_base = self.e_pasta.get().strip()
        self.cfg.incluir_hoje = bool(self.v_hoje.get())
        self.cfg.tentar_escondidas = bool(self.v_escond.get())
        self.cfg.notificar, self.cfg.som = bool(self.v_aviso.get()), bool(self.v_som.get())
        self.notificador.ligado, self.notificador.som = self.cfg.notificar, self.cfg.som
        try:
            self.cfg.salvar()
        except OSError as e:
            messagebox.showerror("Não consegui salvar a configuração", str(e))

    # ------------------------------------------------------------- registro
    def _aba_registro(self, aba) -> None:
        ctk.CTkButton(aba, text="Testar leitura (diagnóstico)", width=220, command=self._diagnostico).pack(anchor="w", pady=4)
        self.log = ctk.CTkTextbox(aba, font=("Consolas", 11))
        self.log.pack(fill="both", expand=True)

    def _diagnostico(self) -> None:
        if self.servico and self.servico.is_alive():
            self.servico.pedir("diagnostico")
        else:
            messagebox.showinfo("Diagnóstico", "Abra o WhatsApp primeiro e deixe um grupo aberto na janela do navegador.")

    def _escrever_log(self, texto: str) -> None:
        self.log.insert("end", texto + "\n")
        self.log.see("end")

    # -------------------------------------------------------------- eventos
    def _ler_eventos(self) -> None:
        mudou_lista = False
        try:
            while True:
                tipo, dado = self.eventos.get_nowait()
                if tipo == "status":
                    self.lbl_status.configure(text=str(dado))
                    self.b_monitor.configure(state="normal" if "conectado" in str(dado) or "Monitor" in str(dado) or "Monitorando" in str(dado) or "Escolha" in str(dado) else "disabled")
                elif tipo == "log":
                    self._escrever_log(str(dado))
                    self.barra.configure(text=str(dado))
                elif tipo == "erro":
                    self.b_abrir.configure(state="normal")
                    self._escrever_log("ERRO: " + str(dado))
                    messagebox.showerror("Não foi possível abrir o WhatsApp", str(dado))
                elif tipo == "lista":
                    mudou_lista = True
                elif tipo == "salvo":
                    self.notificador.mostrar(dado)
                elif tipo == "conversas":
                    self.conversas = list(dado)
                    self.c_conversa.configure(values=self.conversas or [""])
                    self.barra.configure(text=f"{len(self.conversas)} conversa(s) encontradas.")
                elif tipo == "diagnostico":
                    self._escrever_log("--- Diagnóstico ---\n" + str(dado))
                    self.abas.set("Registro")
                elif tipo == "encerrado":
                    self.b_abrir.configure(state="normal")
                    self.b_monitor.configure(text="Iniciar monitor", state="disabled")
        except queue.Empty:
            pass
        if mudou_lista:
            self._recarregar_lista()
        self.after(400, self._ler_eventos)

    # ----------------------------------------------------------------- saida
    def _minimizar(self) -> None:
        """Fechar a janela so minimiza: o monitor continua. Para sair de verdade use 'Sair de vez'."""
        self.iconify()
        self.barra.configure(text="O monitor continua rodando. Para encerrar use \"Sair de vez\".")

    def _sair(self) -> None:
        if self.servico and self.servico.is_alive():
            if not messagebox.askyesno("Sair", "Isso para o monitor e fecha o navegador do WhatsApp. Sair mesmo?"):
                return
            self.servico.pedir("sair")
            self.servico.join(timeout=8)
        self._guardar_config()
        self.destroy()
