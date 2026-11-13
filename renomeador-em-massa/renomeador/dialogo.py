"""Janela que abre com o atalho: nome, opcoes, previa e confirmar."""
from __future__ import annotations

from pathlib import Path
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from . import nucleo, tema
from .config import Config
from .tema import ACENTO, BORDA, BRANCO, ERRO_TEXTO, FUNDO, OK_TEXTO, SEC, SUAVE, TEXTO, botao, cartao, fonte

EXTENSOES_FOTO = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
ROTULO_SEP = {"espaco": "espaço", "traco": "traço (-)", "sublinhado": "sublinhado (_)", "nenhum": "nenhum"}
SEP_DE_ROTULO = {v: k for k, v in ROTULO_SEP.items()}
ORDEM_DE_ROTULO = {v: k for k, v in nucleo.ORDENS.items()}


class Dialogo(ctk.CTkToplevel):
    def __init__(self, raiz, arquivos: list[str], cfg: Config, ao_concluir: Callable[[list[tuple[str, str]], str], None]) -> None:
        super().__init__(raiz)
        self.arquivos, self.cfg, self.ao_concluir = [str(a) for a in arquivos], cfg, ao_concluir
        self.title("Renomear em sequência")
        self.configure(fg_color=FUNDO)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        try:
            from PIL import Image, ImageTk
            self._icone = ImageTk.PhotoImage(Image.open(tema.recurso("icone.png")))
            self.after(250, lambda: self.iconphoto(False, self._icone))
        except Exception:  # noqa: BLE001
            pass
        self._miniaturas = []
        self._agendado = None
        self._montar()
        self._centralizar(560, 820)
        self.after(120, self._focar)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._renomear())
        self._previa()

    # ------------------------------------------------------------ montagem
    def _centralizar(self, w: int, h: int) -> None:
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        h = min(h, sh - 80)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(10, (sh - h) // 2 - 20)}")

    def _focar(self) -> None:
        self.lift()
        self.focus_force()
        self.e_nome.focus_set()
        self.after(400, lambda: self.attributes("-topmost", False))

    def _montar(self) -> None:
        topo = ctk.CTkFrame(self, fg_color=BRANCO, corner_radius=0, height=76)
        topo.pack(fill="x")
        topo.pack_propagate(False)
        try:
            from PIL import Image
            ctk.CTkLabel(topo, image=ctk.CTkImage(Image.open(tema.recurso("icone.png")), size=(44, 44)), text="").pack(side="left", padx=(18, 10))
        except Exception:  # noqa: BLE001
            pass
        t = ctk.CTkFrame(topo, fg_color="transparent")
        t.pack(side="left")
        ctk.CTkLabel(t, text="Renomear em sequência", font=fonte(19, True), text_color=TEXTO).pack(anchor="w")
        pasta = Path(self.arquivos[0]).parent.name or str(Path(self.arquivos[0]).parent)
        self.lbl_info = ctk.CTkLabel(t, text=f"{len(self.arquivos)} arquivo(s) · pasta {pasta}", font=fonte(12), text_color=SUAVE)
        self.lbl_info.pack(anchor="w")
        ctk.CTkFrame(self, fg_color=BORDA, height=1, corner_radius=0).pack(fill="x")

        rod = ctk.CTkFrame(self, fg_color="transparent")
        rod.pack(side="bottom", fill="x", padx=16, pady=(4, 14))
        botao(rod, "Cancelar (Esc)", self.destroy, "secundario", 130).pack(side="left")
        self.b_ok = botao(rod, "Renomear  (Enter)", self._renomear, "primario", 190, height=40)
        self.b_ok.pack(side="right")

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=16, pady=(12, 8))

        self._faixa_fotos(corpo)

        c1 = cartao(corpo)
        c1.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(c1, text="Novo nome", font=fonte(13, True), text_color=TEXTO).pack(anchor="w", padx=14, pady=(10, 2))
        self.var_nome = ctk.StringVar(value="")
        self.var_nome.trace_add("write", lambda *_: self._agendar_previa())
        self.e_nome = ctk.CTkEntry(c1, textvariable=self.var_nome, height=44, font=fonte(17), border_color=BORDA, fg_color=BRANCO,
                                   text_color=TEXTO, placeholder_text="ex.: branco")
        self.e_nome.pack(fill="x", padx=14)
        self.lbl_exemplo = ctk.CTkLabel(c1, text="Digite o nome e veja como vai ficar.", font=fonte(12), text_color=SUAVE)
        self.lbl_exemplo.pack(anchor="w", padx=14, pady=(4, 0))
        if self.cfg.ultimos_nomes:
            fx = ctk.CTkFrame(c1, fg_color="transparent")
            fx.pack(fill="x", padx=12, pady=(6, 0))
            ctk.CTkLabel(fx, text="Recentes:", font=fonte(12), text_color=SUAVE).pack(side="left", padx=(2, 6))
            for nome in self.cfg.ultimos_nomes[:6]:
                ctk.CTkButton(fx, text=nome, width=10, height=26, corner_radius=13, font=fonte(12), fg_color=SEC, hover_color=tema.SEC_HOVER,
                              text_color=TEXTO, command=lambda n=nome: self._usar_nome(n)).pack(side="left", padx=2)
        ctk.CTkLabel(c1, text="", height=4).pack()

        c2 = cartao(corpo)
        c2.pack(fill="x", pady=(0, 10))
        g = ctk.CTkFrame(c2, fg_color="transparent")
        g.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(g, text="Começar em", font=fonte(12), text_color=SUAVE).grid(row=0, column=0, sticky="w")
        self.var_inicio = ctk.StringVar(value="")
        self.var_inicio.trace_add("write", lambda *_: self._agendar_previa())
        ctk.CTkEntry(g, textvariable=self.var_inicio, width=110, height=32, placeholder_text="automático", border_color=BORDA,
                     fg_color=BRANCO, text_color=TEXTO).grid(row=1, column=0, sticky="w", padx=(0, 14))
        ctk.CTkLabel(g, text="Separador", font=fonte(12), text_color=SUAVE).grid(row=0, column=1, sticky="w")
        self.seg_sep = ctk.CTkSegmentedButton(g, values=list(ROTULO_SEP.values()), command=lambda _v: self._previa(), font=fonte(12),
                                              selected_color=ACENTO, selected_hover_color=tema.ACENTO_HOVER, height=32)
        self.seg_sep.set(ROTULO_SEP.get(self.cfg.separador, "espaço"))
        self.seg_sep.grid(row=1, column=1, sticky="w")
        ctk.CTkLabel(g, text="Ordenar por", font=fonte(12), text_color=SUAVE).grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.c_ordem = ctk.CTkComboBox(g, values=list(nucleo.ORDENS.values()), width=330, height=32, command=lambda _v: self._previa(),
                                       border_color=BORDA, fg_color=BRANCO, text_color=TEXTO, state="readonly")
        self.c_ordem.set(nucleo.ORDENS.get(self.cfg.ordem, nucleo.ORDENS["data"]))
        self.c_ordem.grid(row=3, column=0, columnspan=2, sticky="w")
        self.v_zeros = ctk.BooleanVar(value=self.cfg.zeros)
        self.v_cont = ctk.BooleanVar(value=self.cfg.continuar)
        self.v_ext = ctk.BooleanVar(value=self.cfg.extensao_minuscula)
        for var, txt in ((self.v_zeros, "Números com zero (01, 02, 03...)"),
                         (self.v_cont, "Continuar a numeração se a pasta já tiver esse nome"),
                         (self.v_ext, "Extensão em minúsculas (.jpg em vez de .JPG)")):
            ctk.CTkCheckBox(c2, text=txt, variable=var, command=self._previa, font=fonte(13), text_color=TEXTO, fg_color=ACENTO,
                            hover_color=tema.ACENTO_HOVER, corner_radius=6).pack(anchor="w", padx=14, pady=3)
        ctk.CTkLabel(c2, text="", height=4).pack()

        c3 = cartao(corpo)
        c3.pack(fill="both", expand=True)
        ctk.CTkLabel(c3, text="Prévia", font=fonte(13, True), text_color=TEXTO).pack(anchor="w", padx=14, pady=(10, 0))
        self.lbl_aviso = ctk.CTkLabel(c3, text="", font=fonte(12), wraplength=480, justify="left", anchor="w")
        self.lbl_aviso.pack(fill="x", padx=14)
        self.caixa = ctk.CTkTextbox(c3, font=ctk.CTkFont(family="Consolas", size=12), fg_color=FUNDO, text_color=TEXTO, border_width=0,
                                    corner_radius=8, wrap="none", height=150)
        self.caixa.pack(fill="both", expand=True, padx=12, pady=(4, 12))

    def _faixa_fotos(self, pai) -> None:
        fotos = [a for a in self.arquivos if Path(a).suffix.lower() in EXTENSOES_FOTO][:8]
        if not fotos:
            return
        faixa = ctk.CTkFrame(pai, fg_color="transparent")
        faixa.pack(fill="x", pady=(0, 10))
        try:
            from PIL import Image, ImageOps
            for f in fotos:
                with Image.open(f) as im:
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    im = ImageOps.fit(im, (64, 64))
                img = ctk.CTkImage(im, size=(64, 64))
                self._miniaturas.append(img)
                ctk.CTkLabel(faixa, image=img, text="", corner_radius=8).pack(side="left", padx=(0, 6))
            extra = len(self.arquivos) - len(fotos)
            if extra > 0:
                ctk.CTkLabel(faixa, text=f"+{extra}", font=fonte(15, True), text_color=SUAVE).pack(side="left", padx=6)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------ logica
    def _usar_nome(self, nome: str) -> None:
        self.var_nome.set(nome)
        self.e_nome.focus_set()
        self.e_nome.icursor("end")

    def _agendar_previa(self) -> None:
        if self._agendado:
            self.after_cancel(self._agendado)
        self._agendado = self.after(120, self._previa)

    def _opcoes(self) -> nucleo.Opcoes:
        txt = self.var_inicio.get().strip()
        inicio = int(txt) if txt.isdigit() else None
        return nucleo.Opcoes(nome=self.var_nome.get(), inicio=inicio, zeros=bool(self.v_zeros.get()),
                             separador=SEP_DE_ROTULO.get(self.seg_sep.get(), "espaco"),
                             ordem=ORDEM_DE_ROTULO.get(self.c_ordem.get(), "data"), continuar=bool(self.v_cont.get()),
                             extensao_minuscula=bool(self.v_ext.get()))

    def _previa(self) -> None:
        self._agendado = None
        plano = nucleo.montar_plano(self.arquivos, self._opcoes())
        self.caixa.configure(state="normal")
        self.caixa.delete("1.0", "end")
        for antigo, novo in plano.pares[:60]:
            self.caixa.insert("end", f"{Path(antigo).name}\n     →  {Path(novo).name}\n")
        if len(plano.pares) > 60:
            self.caixa.insert("end", f"... e mais {len(plano.pares) - 60} arquivo(s)\n")
        if not plano.pares:
            self.caixa.insert("end", "Digite o novo nome para ver a prévia." if not self.var_nome.get().strip() else "")
        self.caixa.configure(state="disabled")
        if plano.erro and self.var_nome.get().strip():
            self.lbl_aviso.configure(text="⚠ " + plano.erro, text_color=ERRO_TEXTO)
        elif plano.avisos:
            self.lbl_aviso.configure(text="ℹ " + " ".join(plano.avisos), text_color=OK_TEXTO)
        else:
            self.lbl_aviso.configure(text="")
        self.b_ok.configure(state="normal" if plano.pares and not plano.erro else "disabled")
        if plano.pares:
            ex = [Path(n).name for _, n in plano.pares]
            self.lbl_exemplo.configure(text="Vai ficar assim:  " + ",  ".join(ex[:3]) + ("..." if len(ex) > 3 else ""))
        else:
            self.lbl_exemplo.configure(text="Digite o nome e veja como vai ficar.")

    def _renomear(self) -> None:
        plano = nucleo.montar_plano(self.arquivos, self._opcoes())
        if plano.erro or not plano.pares:
            return
        op = self._opcoes()
        try:
            feitos = nucleo.executar(plano.pares)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Não foi possível renomear", f"{e}\n\nNada foi alterado: os nomes originais foram restaurados.", parent=self)
            return
        self.cfg.lembrar_nome(op.nome)
        self.cfg.zeros, self.cfg.separador, self.cfg.ordem = op.zeros, op.separador, op.ordem
        self.cfg.continuar, self.cfg.extensao_minuscula = op.continuar, op.extensao_minuscula
        self.cfg.ultima_pasta = str(Path(self.arquivos[0]).parent)
        try:
            self.cfg.salvar()
        except OSError:
            pass
        self.destroy()
        self.ao_concluir(feitos, nucleo.nome_seguro(op.nome))
