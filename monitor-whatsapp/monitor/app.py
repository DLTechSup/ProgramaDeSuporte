"""Janela do Monitor de Demandas (tema claro)."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import tema
from .armazenamento import nome_pasta_grupo, pasta_do_dia
from .bandeja import Bandeja
from .config import TIPOS, Config, Grupo
from .lista import ListaDoDia
from .notificacao import Notificador
from .registro import RegistroDoDia
from .regras_ref import ARQUIVO as ARQ_REGRAS_REF, RegrasReferencia
from .servico import Servico
from .tema import (ACENTO, AVISO_BORDA, AVISO_FUNDO, AVISO_TEXTO, BORDA, BRANCO, FUNDO, OK_FUNDO, OK_TEXTO, SEC, SUAVE, TEXTO,
                   botao, cartao, etiqueta, fonte, pilula_status)

ROTULO_TIPO = {"A": ("Grupo A", "foto + legenda"), "B": ("Grupo B", "só foto da caixa"), "I": ("Conversa", "texto e fotos")}


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
        self.geometry("1060x740")
        self.minsize(900, 640)
        ctk.set_appearance_mode("light")
        self.configure(fg_color=FUNDO)
        self._icone()
        self.cfg = Config.carregar()
        self.eventos: queue.Queue = queue.Queue()
        self.servico: Servico | None = None
        self.conversas: list[str] = []
        self.notificador = Notificador(self)
        self.notificador.ligado, self.notificador.som = self.cfg.notificar, self.cfg.som
        self.protocol("WM_DELETE_WINDOW", self._minimizar)
        self.tem_bandeja = False
        self._avisou_bandeja = False

        self._cabecalho()
        self.abas = ctk.CTkTabview(self, fg_color=FUNDO, corner_radius=12, border_width=0,
                                   segmented_button_fg_color=SEC, segmented_button_selected_color=ACENTO,
                                   segmented_button_selected_hover_color=tema.ACENTO_HOVER,
                                   segmented_button_unselected_color=SEC, segmented_button_unselected_hover_color=tema.SEC_HOVER,
                                   text_color=TEXTO)
        self.abas.pack(fill="both", expand=True, padx=16, pady=(4, 0))
        self._aba_demanda(self.abas.add("Demanda do dia"))
        self._aba_config(self.abas.add("Configurações"))
        self._aba_registro(self.abas.add("Registro do dia"))
        self._rodape()
        self._recarregar_lista()
        self._carregar_log_do_dia()
        self._iniciar_bandeja()
        self.after(400, self._ler_eventos)
        if selftest:
            self.after(300, lambda: self.notificador.mostrar({"grupo": "TESTE", "pasta": "BEIRA RIO 123.456", "marca": "BEIRA RIO",
                       "referencia": "123.456", "novas": 3, "total": 3, "nova": True, "situacao": "ok", "obs": ""}))
            self.after(1200, self._fim_selftest)

    def _iniciar_bandeja(self) -> None:
        """Icone perto do relogio, com menu. Os cliques chegam de outra thread, entao viram eventos na fila."""
        try:
            from PIL import Image
            imagem = Image.open(tema.recurso("icone.png")).convert("RGBA")
        except Exception:  # noqa: BLE001
            return
        pedir = lambda nome: (lambda: self.eventos.put((nome, None)))
        self.bandeja = Bandeja(pedir("tray_abrir"), pedir("tray_alternar"), pedir("tray_pasta"), pedir("tray_sair"), imagem)
        self.tem_bandeja = self.bandeja.iniciar()

    def _mostrar_janela(self) -> None:
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _fim_selftest(self) -> None:
        self.destroy()

    def destroy(self) -> None:
        """Sempre fecha o icone da bandeja junto (senao a thread dele manteria o programa vivo)."""
        if getattr(self, "tem_bandeja", False):
            self.bandeja.parar()
            self.tem_bandeja = False
        super().destroy()

    def _icone(self) -> None:
        try:
            if sys.platform.startswith("win"):
                self.iconbitmap(str(tema.recurso("icone.ico")))
            else:
                from PIL import Image, ImageTk
                self._foto_icone = ImageTk.PhotoImage(Image.open(tema.recurso("icone.png")))
                self.iconphoto(True, self._foto_icone)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------ cabecalho
    def _cabecalho(self) -> None:
        barra = ctk.CTkFrame(self, fg_color=BRANCO, corner_radius=0, border_width=0, height=72)
        barra.pack(fill="x")
        barra.pack_propagate(False)
        ctk.CTkFrame(self, fg_color=BORDA, height=1, corner_radius=0).pack(fill="x")
        try:
            from PIL import Image
            img = ctk.CTkImage(Image.open(tema.recurso("icone.png")), size=(42, 42))
            ctk.CTkLabel(barra, image=img, text="").pack(side="left", padx=(18, 10))
        except Exception:  # noqa: BLE001
            pass
        nomes = ctk.CTkFrame(barra, fg_color="transparent")
        nomes.pack(side="left")
        ctk.CTkLabel(nomes, text="Monitor de Demandas", font=fonte(19, True), text_color=TEXTO, anchor="w").pack(anchor="w")
        ctk.CTkLabel(nomes, text="Seu assistente que salva as fotos e organiza as pastas", font=fonte(12), text_color=SUAVE, anchor="w").pack(anchor="w")
        direita = ctk.CTkFrame(barra, fg_color="transparent")
        direita.pack(side="right", padx=16)
        self.b_abrir = botao(direita, "Abrir WhatsApp", self._abrir_whatsapp, "primario", 150)
        self.b_abrir.pack(side="left", padx=4)
        self.b_monitor = botao(direita, "Iniciar monitor", self._alternar_monitor, "secundario", 150, state="disabled")
        self.b_monitor.pack(side="left", padx=4)
        self.lbl_status = ctk.CTkLabel(barra, text="", corner_radius=14, font=fonte(12, True), padx=14, height=30)
        self.lbl_status.pack(side="right", padx=8)
        self._status("Desligado")

    def _status(self, texto: str) -> None:
        txt, fundo, cor = pilula_status(texto)
        self.lbl_status.configure(text=txt, fg_color=fundo, text_color=cor)
        if self.tem_bandeja:
            self.bandeja.atualizar(texto, bool(self.servico and self.servico.monitorando))

    def _rodape(self) -> None:
        r = ctk.CTkFrame(self, fg_color="transparent")
        r.pack(fill="x", padx=18, pady=(4, 8))
        self.barra = ctk.CTkLabel(r, text="Pronto. Clique em \"Abrir WhatsApp\" para começar.", anchor="w", font=fonte(12), text_color=SUAVE)
        self.barra.pack(side="left")
        botao(r, "Sair de vez", self._sair, "perigo", 100, height=28).pack(side="right")
        ctk.CTkLabel(r, text=f"v{tema.VERSAO}", font=fonte(11), text_color=SUAVE).pack(side="right", padx=12)

    # ----------------------------------------------------------- acoes topo
    def _abrir_whatsapp(self) -> None:
        if self.servico and self.servico.is_alive():
            return
        self._guardar_config()
        self.servico = Servico(self.cfg, self.eventos)
        self.servico.start()
        self.b_abrir.configure(state="disabled", text="WhatsApp aberto")

    def _alternar_monitor(self) -> None:
        if not self.servico:
            return
        if self.servico.monitorando:
            self.servico.pedir("pausar")
            self.b_monitor.configure(text="Iniciar monitor")
            return
        if not self.cfg.pasta_base or not self.cfg.grupos:
            messagebox.showinfo("Falta configurar", "Na aba Configurações, escolha a pasta principal e adicione pelo menos um grupo.")
            self.abas.set("Configurações")
            return
        self._guardar_config()
        self.servico.pedir("iniciar")
        self.b_monitor.configure(text="Pausar monitor")

    # ------------------------------------------------------- demanda do dia
    def _aba_demanda(self, aba) -> None:
        topo = ctk.CTkFrame(aba, fg_color="transparent")
        topo.pack(fill="x", pady=(4, 8))
        self.cards_resumo = {}
        for chave, rotulo in (("total", "Demandas hoje"), ("feitas", "Feitas"), ("conferir", "Para conferir")):
            c = cartao(topo)
            c.pack(side="left", padx=(0, 10), ipadx=14, ipady=4)
            num = ctk.CTkLabel(c, text="0", font=fonte(24, True), text_color=ACENTO if chave != "conferir" else AVISO_TEXTO)
            num.pack(anchor="w", padx=14, pady=(6, 0))
            ctk.CTkLabel(c, text=rotulo, font=fonte(12), text_color=SUAVE).pack(anchor="w", padx=14, pady=(0, 6))
            self.cards_resumo[chave] = num
        ctk.CTkFrame(topo, fg_color="transparent", height=1, width=1).pack(side="left", expand=True)
        botao(topo, "Abrir pasta principal", self._abrir_pasta_dia, "secundario", 170).pack(side="right", padx=4)
        botao(topo, "Abrir lista do dia (.txt)", self._abrir_lista_txt, "secundario", 190).pack(side="right", padx=4)
        self.quadro = ctk.CTkScrollableFrame(aba, fg_color="transparent", corner_radius=0)
        self.quadro.pack(fill="both", expand=True)

    def _pasta_do_dia(self, grupo: str) -> Path | None:
        return pasta_do_dia(Path(self.cfg.pasta_base), grupo, date.today()) if self.cfg.pasta_base else None

    def _todos_os_itens(self):
        saida = []
        for g in self.cfg.grupos:
            if g.tipo == "I":
                continue
            p = self._pasta_do_dia(g.nome)
            if p:
                saida += [(g.nome, i) for i in ListaDoDia(p).ordenados()]
        return sorted(saida, key=lambda x: (x[1].feito, x[1].situacao != "conferir", x[1].hora))

    def _vazio(self, titulo: str, texto: str) -> None:
        c = ctk.CTkFrame(self.quadro, fg_color="transparent")
        c.pack(pady=50)
        ctk.CTkLabel(c, text=titulo, font=fonte(16, True), text_color=TEXTO).pack()
        ctk.CTkLabel(c, text=texto, font=fonte(13), text_color=SUAVE, wraplength=480, justify="center").pack(pady=6)

    def _recarregar_lista(self) -> None:
        for w in self.quadro.winfo_children():
            w.destroy()
        if not self.cfg.pasta_base or not self.cfg.grupos:
            for n in self.cards_resumo.values():
                n.configure(text="0")
            self._vazio("Vamos começar", "Na aba Configurações, escolha a pasta principal e adicione os grupos que você quer acompanhar. Depois é só abrir o WhatsApp e iniciar o monitor.")
            return
        itens = self._todos_os_itens()
        self.cards_resumo["total"].configure(text=str(len(itens)))
        self.cards_resumo["feitas"].configure(text=str(sum(1 for _, i in itens if i.feito)))
        self.cards_resumo["conferir"].configure(text=str(sum(1 for _, i in itens if i.situacao == "conferir")))
        if not itens:
            self._vazio("Nada chegou ainda hoje", "Quando alguma demanda chegar nos grupos monitorados, ela aparece aqui e você recebe um aviso no canto da tela.")
        for grupo, it in itens:
            self._linha(grupo, it)

    def _linha(self, grupo: str, it) -> None:
        conferir = it.situacao == "conferir"
        fundo = AVISO_FUNDO if conferir else (OK_FUNDO if it.feito else BRANCO)
        borda = AVISO_BORDA if conferir else BORDA
        card = ctk.CTkFrame(self.quadro, fg_color=fundo, corner_radius=10, border_width=1, border_color=borda)
        card.pack(fill="x", pady=4, padx=2)
        ctk.CTkFrame(card, fg_color=AVISO_BORDA if conferir else (OK_TEXTO if it.feito else ACENTO), width=5, height=1, corner_radius=3).pack(side="left", fill="y", padx=(8, 4), pady=8)
        var = ctk.BooleanVar(value=it.feito)
        ctk.CTkCheckBox(card, text="", variable=var, width=26, checkbox_width=22, checkbox_height=22, corner_radius=6,
                        fg_color=ACENTO, hover_color=tema.ACENTO_HOVER,
                        command=lambda g=grupo, k=it.chave, v=var: self._marcar(g, k, v.get())).pack(side="left", padx=(6, 6))
        centro = ctk.CTkFrame(card, fg_color="transparent")
        centro.pack(side="left", fill="x", expand=True, pady=8)
        marca = it.marca if it.marca and it.marca != "?" else ""
        titulo = f"{marca}  {it.referencia}".strip()
        ctk.CTkLabel(centro, text=titulo, font=fonte(15, True), text_color=OK_TEXTO if it.feito else TEXTO, anchor="w").pack(anchor="w")
        meta = f"{nome_pasta_grupo(grupo)}   ·   {it.fotos} foto(s)   ·   {it.hora}"
        ctk.CTkLabel(centro, text=meta, font=fonte(12), text_color=SUAVE, anchor="w").pack(anchor="w")
        if it.observacao:
            ctk.CTkLabel(centro, text="⚠ " + it.observacao, font=fonte(12), text_color=AVISO_TEXTO, anchor="w").pack(anchor="w")
        botao(card, "Abrir pasta", lambda g=grupo, p=it.pasta: self._abrir_sub(g, p), "secundario", 104, height=30).pack(side="right", padx=10)
        if conferir:
            etiqueta(card, " CONFERIR ", "#F9E3B0", AVISO_TEXTO).pack(side="right", padx=4)
        elif it.feito:
            etiqueta(card, " FEITO ", "#CDEBD6", OK_TEXTO).pack(side="right", padx=4)

    def _marcar(self, grupo: str, chave: str, feito: bool) -> None:
        pasta = self._pasta_do_dia(grupo)
        if pasta:
            ListaDoDia(pasta).marcar_feito(chave, feito)
            self._recarregar_lista()

    def _abrir_pasta_dia(self) -> None:
        if self.cfg.pasta_base and Path(self.cfg.pasta_base).exists():
            abrir_no_windows(Path(self.cfg.pasta_base))
        else:
            messagebox.showinfo("Pasta principal", "Escolha a pasta principal em Configurações.")

    def _abrir_sub(self, grupo: str, nome: str) -> None:
        p = self._pasta_do_dia(grupo)
        if p and (p / nome).exists():
            abrir_no_windows(p / nome)

    def _abrir_lista_txt(self) -> None:
        listas = [self._pasta_do_dia(g.nome) / "lista_do_dia.txt" for g in self.cfg.grupos if g.tipo != "I" and self._pasta_do_dia(g.nome)]
        existentes = [c for c in listas if c.exists()]
        if not existentes:
            messagebox.showinfo("Lista", "A lista ainda não foi criada (nada chegou hoje).")
        for c in existentes:
            abrir_no_windows(c)

    # ------------------------------------------------------- configuracoes
    def _aba_config(self, aba) -> None:
        rolagem = ctk.CTkScrollableFrame(aba, fg_color="transparent", corner_radius=0)
        rolagem.pack(fill="both", expand=True)

        c1 = cartao(rolagem)
        c1.pack(fill="x", pady=(4, 10), padx=2)
        ctk.CTkLabel(c1, text="Pasta principal", font=fonte(15, True), text_color=TEXTO).pack(anchor="w", padx=16, pady=(14, 0))
        ctk.CTkLabel(c1, text="Dentro dela o programa cria uma pasta para cada grupo ou pessoa e, dentro, uma pasta por dia.",
                     font=fonte(12), text_color=SUAVE, wraplength=860, justify="left").pack(anchor="w", padx=16)
        linha = ctk.CTkFrame(c1, fg_color="transparent")
        linha.pack(fill="x", padx=16, pady=(8, 14))
        self.e_pasta = ctk.CTkEntry(linha, height=34, font=fonte(13), border_color=BORDA, fg_color=BRANCO, text_color=TEXTO)
        self.e_pasta.pack(side="left", fill="x", expand=True)
        self.e_pasta.insert(0, self.cfg.pasta_base)
        botao(linha, "Escolher...", self._escolher_pasta, "secundario", 110).pack(side="left", padx=(8, 0))

        c2 = cartao(rolagem)
        c2.pack(fill="x", pady=10, padx=2)
        ctk.CTkLabel(c2, text="Grupos e conversas monitorados", font=fonte(15, True), text_color=TEXTO).pack(anchor="w", padx=16, pady=(14, 0))
        ctk.CTkLabel(c2, text="Adicione quantos quiser. Use o nome igualzinho ao que aparece no WhatsApp.", font=fonte(12), text_color=SUAVE).pack(anchor="w", padx=16)
        self.quadro_grupos = ctk.CTkFrame(c2, fg_color="transparent")
        self.quadro_grupos.pack(fill="x", padx=16, pady=8)
        add = ctk.CTkFrame(c2, fg_color=FUNDO, corner_radius=10)
        add.pack(fill="x", padx=16, pady=(0, 6))
        self.c_conversa = ctk.CTkComboBox(add, values=[""], width=330, height=34, font=fonte(13), border_color=BORDA, fg_color=BRANCO, text_color=TEXTO)
        self.c_conversa.set("")
        self.c_conversa.pack(side="left", padx=10, pady=10)
        self.c_tipo = ctk.CTkComboBox(add, values=list(TIPOS.values()), width=340, height=34, font=fonte(12), border_color=BORDA, fg_color=BRANCO, text_color=TEXTO)
        self.c_tipo.set(TIPOS["A"])
        self.c_tipo.pack(side="left", padx=4)
        botao(add, "Adicionar", self._adicionar_grupo, "primario", 100).pack(side="left", padx=10)
        botao(c2, "Atualizar lista de conversas (do WhatsApp aberto)", self._pedir_conversas, "secundario", 340).pack(anchor="w", padx=16, pady=(0, 14))

        c3 = cartao(rolagem)
        c3.pack(fill="x", pady=10, padx=2)
        ctk.CTkLabel(c3, text="Opções", font=fonte(15, True), text_color=TEXTO).pack(anchor="w", padx=16, pady=(14, 6))
        self.v_hoje = ctk.BooleanVar(value=self.cfg.incluir_hoje)
        self.v_escond = ctk.BooleanVar(value=self.cfg.tentar_escondidas)
        self.v_aviso = ctk.BooleanVar(value=self.cfg.notificar)
        self.v_som = ctk.BooleanVar(value=self.cfg.som)
        for var, texto in ((self.v_aviso, "Avisar na tela a cada item salvo (diz de qual grupo veio)"),
                           (self.v_som, "Tocar um som junto com o aviso"),
                           (self.v_hoje, "Pegar também o que já chegou hoje (ao iniciar o monitor)"),
                           (self.v_escond, "Álbum com \"+N\": tentar abrir e baixar todas as fotos")):
            ctk.CTkCheckBox(c3, text=texto, variable=var, command=self._guardar_config, font=fonte(13), text_color=TEXTO,
                            fg_color=ACENTO, hover_color=tema.ACENTO_HOVER, corner_radius=6).pack(anchor="w", padx=16, pady=5)
        ln = ctk.CTkFrame(c3, fg_color="transparent")
        ln.pack(anchor="w", padx=16, pady=(8, 0))
        ctk.CTkLabel(ln, text="Navegador do monitor:", font=fonte(13), text_color=TEXTO).pack(side="left", padx=(0, 10))
        self.seg_navegador = ctk.CTkSegmentedButton(ln, values=["Chrome", "Edge"], command=lambda _v: self._guardar_config(),
                                                    selected_color=ACENTO, selected_hover_color=tema.ACENTO_HOVER, font=fonte(12))
        self.seg_navegador.set("Edge" if self.cfg.navegador == "msedge" else "Chrome")
        self.seg_navegador.pack(side="left")
        ctk.CTkLabel(c3, text="É uma janela separada, com perfil próprio: não mexe no seu Chrome nem nos seus atalhos do WhatsApp.",
                     font=fonte(12), text_color=SUAVE).pack(anchor="w", padx=16, pady=(4, 12))
        botao(c3, "Regras de referência por marca (ex.: cortar a cor)", self._abrir_regras_ref, "secundario", 360).pack(anchor="w", padx=16, pady=(0, 14))
        self._desenhar_grupos()

    def _abrir_regras_ref(self) -> None:
        RegrasReferencia.carregar()                 # cria o arquivo com o modelo, se ainda nao existir
        abrir_no_windows(ARQ_REGRAS_REF)
        messagebox.showinfo("Regras de referência", "Edite o arquivo que abriu, salve e depois pause e inicie o monitor de novo para valer.")

    def _escolher_pasta(self) -> None:
        p = filedialog.askdirectory(title="Pasta principal das demandas")
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
        self._recarregar_lista()

    def _desenhar_grupos(self) -> None:
        for w in self.quadro_grupos.winfo_children():
            w.destroy()
        if not self.cfg.grupos:
            ctk.CTkLabel(self.quadro_grupos, text="Nenhum grupo ainda.", text_color=SUAVE, font=fonte(13)).pack(anchor="w", pady=6)
        for g in self.cfg.grupos:
            l = ctk.CTkFrame(self.quadro_grupos, fg_color=FUNDO, corner_radius=8)
            l.pack(fill="x", pady=3)
            ctk.CTkLabel(l, text=g.nome, anchor="w", font=fonte(13, True), text_color=TEXTO, width=340).pack(side="left", padx=12, pady=8)
            nome_tipo, desc = ROTULO_TIPO[g.tipo]
            cor_fundo = {"A": "#DCEFE9", "B": "#E3E9F9", "I": "#F3E6F7"}[g.tipo]
            cor_txt = {"A": ACENTO, "B": "#3552B5", "I": "#8A3FA3"}[g.tipo]
            etiqueta(l, f" {nome_tipo} ", cor_fundo, cor_txt).pack(side="left")
            ctk.CTkLabel(l, text=desc, font=fonte(12), text_color=SUAVE).pack(side="left", padx=10)
            botao(l, "Remover", lambda x=g: self._remover(x), "perigo", 84, height=28).pack(side="right", padx=8)

    def _remover(self, g: Grupo) -> None:
        self.cfg.grupos = [x for x in self.cfg.grupos if x is not g]
        self._guardar_config()
        self._desenhar_grupos()
        self._recarregar_lista()

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
        self.cfg.navegador = "msedge" if self.seg_navegador.get() == "Edge" else "chrome"
        self.notificador.ligado, self.notificador.som = self.cfg.notificar, self.cfg.som
        try:
            self.cfg.salvar()
        except OSError as e:
            messagebox.showerror("Não consegui salvar a configuração", str(e))

    # ------------------------------------------------------------- registro
    def _aba_registro(self, aba) -> None:
        barra = ctk.CTkFrame(aba, fg_color="transparent")
        barra.pack(fill="x", pady=(4, 8))
        ctk.CTkLabel(barra, text="Tudo o que aconteceu hoje, em ordem. Também fica salvo em um arquivo .txt.", font=fonte(12), text_color=SUAVE).pack(side="left")
        botao(barra, "Testar leitura (diagnóstico)", self._diagnostico, "secundario", 210).pack(side="right", padx=4)
        botao(barra, "Abrir log do dia (.txt)", self._abrir_log, "secundario", 190).pack(side="right", padx=4)
        self.log = ctk.CTkTextbox(aba, font=ctk.CTkFont(family="Consolas", size=12), fg_color=BRANCO, text_color=TEXTO,
                                  border_width=1, border_color=BORDA, corner_radius=10, wrap="word")
        self.log.pack(fill="both", expand=True)

    def _carregar_log_do_dia(self) -> None:
        if self.cfg.pasta_base:
            try:
                antigo = RegistroDoDia(self.cfg.pasta_base).ler()
            except OSError:
                antigo = ""
            if antigo:
                self.log.insert("end", antigo)
                self.log.see("end")

    def _abrir_log(self) -> None:
        if not self.cfg.pasta_base:
            messagebox.showinfo("Log", "Escolha a pasta principal em Configurações.")
            return
        arq = RegistroDoDia(self.cfg.pasta_base).arquivo
        if arq.exists():
            abrir_no_windows(arq)
        else:
            messagebox.showinfo("Log", "Ainda não há eventos hoje.")

    def _diagnostico(self) -> None:
        if self.servico and self.servico.is_alive():
            self.servico.pedir("diagnostico")
        else:
            messagebox.showinfo("Diagnóstico", "Abra o WhatsApp primeiro e deixe um grupo aberto na janela do navegador.")

    def _escrever_log(self, texto: str) -> None:
        self.log.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {texto}\n")
        self.log.see("end")

    # -------------------------------------------------------------- eventos
    def _ler_eventos(self) -> None:
        mudou_lista = False
        try:
            while True:
                tipo, dado = self.eventos.get_nowait()
                if tipo == "status":
                    self._status(str(dado))
                    pronto = any(k in str(dado) for k in ("conectado", "Monitor", "Monitorando", "Escolha"))
                    self.b_monitor.configure(state="normal" if pronto else "disabled")
                elif tipo == "log":
                    self._escrever_log(str(dado))
                    self.barra.configure(text=str(dado))
                elif tipo == "erro":
                    self.b_abrir.configure(state="normal", text="Abrir WhatsApp")
                    self._status("Erro")
                    self._escrever_log("ERRO: " + str(dado))
                    messagebox.showerror("Não foi possível abrir o WhatsApp", str(dado))
                elif tipo == "lista":
                    mudou_lista = True
                elif tipo == "salvo":
                    self.notificador.mostrar(dado)
                elif tipo == "tray_abrir":
                    self._mostrar_janela()
                elif tipo == "tray_alternar":
                    self._alternar_monitor()
                    self._status(self.lbl_status.cget("text").lstrip("● ").strip())
                elif tipo == "tray_pasta":
                    self._abrir_pasta_dia()
                elif tipo == "tray_sair":
                    self._mostrar_janela()
                    self._sair()
                elif tipo == "conversas":
                    self.conversas = list(dado)
                    self.c_conversa.configure(values=self.conversas or [""])
                    self.barra.configure(text=f"{len(self.conversas)} conversa(s) encontradas. Escolha na caixa e clique em Adicionar.")
                elif tipo == "diagnostico":
                    self._escrever_log("--- Diagnóstico ---\n" + str(dado))
                    self.abas.set("Registro do dia")
                elif tipo == "encerrado":
                    self.b_abrir.configure(state="normal", text="Abrir WhatsApp")
                    self.b_monitor.configure(text="Iniciar monitor", state="disabled")
                    self._status("Desligado")
        except queue.Empty:
            pass
        if mudou_lista:
            self._recarregar_lista()
        self.after(400, self._ler_eventos)

    # ----------------------------------------------------------------- saida
    def _minimizar(self) -> None:
        """Fechar a janela (X) manda o programa para a bandeja: o monitor continua. Sair de verdade: 'Sair de vez'."""
        if self.tem_bandeja:
            self.withdraw()
            if not self._avisou_bandeja:
                self._avisou_bandeja = True
                self.bandeja.avisar("Monitor de Demandas", "Continuo trabalhando aqui na bandeja. Clique no ícone para abrir.")
        else:
            self.iconify()
        self.barra.configure(text="O monitor continua rodando em segundo plano. Para encerrar use \"Sair de vez\".")

    def _sair(self) -> None:
        if self.servico and self.servico.is_alive():
            if not messagebox.askyesno("Sair", "Isso para o monitor e fecha o navegador do WhatsApp. Sair mesmo?"):
                return
            self.servico.pedir("sair")
            self.servico.join(timeout=8)
        self._guardar_config()
        self.destroy()
