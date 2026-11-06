"""Widgets da interface (tema escuro, janela estreita ~360 px)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
                               QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
                               QHeaderView)

from . import core

BG, CARD, CARD_OK = "#1b1d24", "#272a35", "#1f3a2c"
TXT, SOFT, ACCENT = "#e9eaf0", "#9aa0b4", "#4f8cff"
WARN, GREEN, RED, ORANGE = "#f0b24a", "#3ddc84", "#ff5d5d", "#f0b24a"

STYLE = f"""
* {{ font-family: 'Segoe UI', 'Noto Sans', sans-serif; font-size: 13px; color: {TXT}; }}
QWidget#raiz, QDialog, QMainWindow {{ background: {BG}; }}
QLabel {{ background: transparent; }}
QLabel#soft {{ color: {SOFT}; font-size: 12px; }}
QLabel#warn {{ color: {WARN}; font-size: 12px; }}
QFrame#card {{ background: {CARD}; border-radius: 12px; }}
QFrame#card[done="true"] {{ background: {CARD_OK}; }}
QPushButton {{ background: #343848; border: none; border-radius: 8px; padding: 7px 12px; }}
QPushButton:hover {{ background: #404560; }}
QPushButton#primario {{ background: {ACCENT}; color: white; font-weight: 600; }}
QPushButton#primario:hover {{ background: #6a9dff; }}
QPushButton#mini {{ padding: 5px 9px; font-size: 12px; }}
QPushButton#marca {{ background: transparent; text-align: left; font-weight: 700;
                    color: {ACCENT}; padding: 8px 4px 2px 4px; }}
QPushButton#marca:hover {{ color: #8ab3ff; }}
QPushButton#x {{ padding: 2px 8px; background: transparent; color: {SOFT}; font-size: 15px; }}
QPushButton#x:hover {{ color: {RED}; }}
QCheckBox {{ spacing: 8px; font-size: 14px; font-weight: 600; }}
QCheckBox::indicator {{ width: 24px; height: 24px; border-radius: 6px; border: 2px solid #5b617a;
                        background: #1b1d24; }}
QCheckBox::indicator:checked {{ background: {GREEN}; border-color: {GREEN}; }}
QLineEdit, QComboBox, QPlainTextEdit, QListWidget, QTableWidget, QSpinBox {{
    background: #20222b; border: 1px solid #3a3e50; border-radius: 8px; padding: 6px; }}
QHeaderView::section {{ background: #272a35; border: none; padding: 5px; color: {SOFT}; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{ background: transparent; padding: 8px 14px; color: {SOFT}; }}
QTabBar::tab:selected {{ color: {TXT}; border-bottom: 2px solid {ACCENT}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: #3a3e50; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QSplitter::handle {{ background: #12131a; width: 4px; }}
"""


def open_path(p) -> None:
    p = str(p)
    if sys.platform.startswith("win"):
        os.startfile(p)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", p])
    else:
        subprocess.Popen(["xdg-open", p])


def copy_text(t: str) -> None:
    QGuiApplication.clipboard().setText(t)


# ----------------------------------------------------------------- cartão
class DemandCard(QFrame):
    def __init__(self, d: dict, h):
        super().__init__()
        self.setObjectName("card")
        done = core.Store.is_done(d)
        self.setProperty("done", "true" if done else "false")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        top = QHBoxLayout()
        title = QLabel((f"{d['brand']} {d['ref']}".strip() or "(sem referência)"))
        f = QFont(title.font())
        f.setPointSize(11)
        f.setBold(True)
        f.setStrikeOut(done)
        title.setFont(f)
        title.setWordWrap(True)
        title.setStyleSheet(f"color: {SOFT if done else TXT};")
        title.setMinimumWidth(10)
        top.addWidget(title, 1)
        x = QPushButton("✕")
        x.setObjectName("x")
        x.setToolTip("Tirar da lista (não apaga a pasta nem as fotos)")
        x.clicked.connect(lambda: h["remove"](d["id"]))
        top.addWidget(x, 0, Qt.AlignTop)
        lay.addLayout(top)

        if done:
            ok = QLabel("✔ PRONTO — Site e Atacado")
            ok.setStyleSheet(f"color: {GREEN}; font-weight: 700; font-size: 12px;")
            lay.addWidget(ok)
        info = QLabel(f"{d['photos']} foto(s) · {d['time']}" + (f" · {d['sender']}" if d["sender"] else ""))
        info.setObjectName("soft")
        lay.addWidget(info)
        for w in d["warn"]:
            lw = QLabel(w)
            lw.setObjectName("warn")
            lw.setWordWrap(True)
            lay.addWidget(lw)

        row = QHBoxLayout()
        row.setSpacing(18)
        for field, label in (("site", "Site"), ("atacado", "Atacado")):
            cb = QCheckBox(label)
            cb.setChecked(bool(d[field]))
            cb.setMinimumHeight(30)
            cb.toggled.connect(lambda v, f=field: h["toggle"](d["id"], f, v))
            row.addWidget(cb)
        row.addStretch(1)
        lay.addLayout(row)

        btns = QHBoxLayout()
        btns.setSpacing(6)
        for text, key in (("Abrir pasta", "open"), ("Copiar ref", "copy"), ("Editar", "edit")):
            b = QPushButton(text)
            b.setObjectName("mini")
            b.clicked.connect(lambda _=False, k=key: h[k](d["id"]))
            btns.addWidget(b)
        btns.addStretch(1)
        lay.addLayout(btns)
        if d.get("plus") and d.get("msg_id"):
            b = QPushButton("Pegar fotos restantes do álbum")
            b.setObjectName("mini")
            b.clicked.connect(lambda _=False: h["album"](d["id"]))
            lay.addWidget(b)


# ----------------------------------------------------------------- painel
class DemandPanel(QWidget):
    """Cabeçalho + "Estou fazendo" + pesquisa + lista por marca + rodapé."""
    open_painel = Signal()
    open_config = Signal()
    toggle_detach = Signal()
    add_manual = Signal()
    import_current = Signal()
    reconnect = Signal()
    mark_ref = Signal(str)
    clear_start = Signal()
    paste_demands = Signal()

    def __init__(self, store, handlers, cfg):
        super().__init__()
        self.setObjectName("raiz")
        self.store, self.h, self.cfg = store, handlers, cfg
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        head = QHBoxLayout()
        self.dot = QLabel("●")
        self.status = QLabel("Iniciando...")
        self.status.setWordWrap(True)
        head.addWidget(self.dot)
        head.addWidget(self.status, 1)
        root.addLayout(head)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        for text, sig, tip in (("Painel", self.open_painel, "Histórico e atividade"),
                               ("⚙", self.open_config, "Configurações"),
                               ("Destacar lista", self.toggle_detach,
                                "Abre a lista numa janela separada, sempre na frente (e encaixa de volta)")):
            b = QPushButton(text)
            b.setObjectName("mini")
            b.setToolTip(tip)
            b.clicked.connect(sig)
            bar.addWidget(b)
        self.btn_detach = bar.itemAt(2).widget()
        self.btn_reconnect = QPushButton("Recarregar")
        self.btn_reconnect.setObjectName("mini")
        self.btn_reconnect.setToolTip("Recarrega o WhatsApp Web e o monitor")
        self.btn_reconnect.clicked.connect(self.reconnect)
        bar.addWidget(self.btn_reconnect)
        bar.addStretch(1)
        root.addLayout(bar)

        # "Estou fazendo": marca a referência e só entra o que chegar a partir dela
        fz = QHBoxLayout()
        fz.setSpacing(6)
        self.fazendo = QLineEdit()
        self.fazendo.setPlaceholderText("Estou fazendo: ex. BEIRA RIO 8513.115")
        self.fazendo.returnPressed.connect(self._marcar)
        mk = QPushButton("Marcar")
        mk.setObjectName("primario")
        mk.setToolTip("Coloca esta referência na lista e passa a adicionar só o que chegar no grupo a partir dela")
        mk.clicked.connect(self._marcar)
        fz.addWidget(self.fazendo, 1)
        fz.addWidget(mk)
        root.addLayout(fz)
        ini = QHBoxLayout()
        self.inicio = QLabel("")
        self.inicio.setObjectName("soft")
        self.inicio.setWordWrap(True)
        self.btn_limpar = QPushButton("limpar")
        self.btn_limpar.setObjectName("mini")
        self.btn_limpar.clicked.connect(self.clear_start)
        ini.addWidget(self.inicio, 1)
        ini.addWidget(self.btn_limpar)
        root.addLayout(ini)

        # pesquisa + agrupar
        pr = QHBoxLayout()
        pr.setSpacing(8)
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Pesquisar referência ou marca...")
        self.busca.setClearButtonEnabled(True)
        self.busca.textChanged.connect(lambda _t: self.refresh())
        self.chk_marca = QCheckBox("Por marca")
        self.chk_marca.setChecked(bool(cfg["agrupar_por_marca"]))
        self.chk_marca.toggled.connect(self._set_group)
        pr.addWidget(self.busca, 1)
        pr.addWidget(self.chk_marca)
        root.addLayout(pr)

        self.counter = QLabel("")
        self.counter.setStyleSheet("font-weight: 600; font-size: 14px;")
        root.addWidget(self.counter)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.inner = QWidget()
        self.inner.setObjectName("raiz")
        self.lay = QVBoxLayout(self.inner)
        self.lay.setContentsMargins(0, 0, 4, 0)
        self.lay.setSpacing(8)
        self.lay.addStretch(1)
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll, 1)

        colar = QPushButton("Colar demandas")
        colar.setObjectName("primario")
        colar.setToolTip("Copie as demandas de qualquer lugar (uma por linha) e cole aqui  (Ctrl+Shift+V)")
        colar.clicked.connect(self.paste_demands)
        root.addWidget(colar)
        foot = QHBoxLayout()
        add = QPushButton("+ Adicionar uma")
        add.clicked.connect(self.add_manual)
        imp = QPushButton("Importar das pastas")
        imp.clicked.connect(self.import_current)
        foot.addWidget(add)
        foot.addWidget(imp, 1)
        root.addLayout(foot)
        sc = QShortcut(QKeySequence("Ctrl+Shift+V"), self)
        sc.setContext(Qt.WidgetWithChildrenShortcut)
        sc.activated.connect(self.paste_demands)
        self.set_status("Iniciando...", "wait")
        self.refresh()

    # ---------------------------------------------------------- ações
    def _marcar(self):
        t = self.fazendo.text().strip()
        if t:
            self.mark_ref.emit(t)
            self.fazendo.clear()

    def _set_group(self, v):
        self.cfg["agrupar_por_marca"] = bool(v)
        self.refresh()

    def _toggle_brand(self, brand):
        rec = list(self.cfg["marcas_recolhidas"])
        rec.remove(brand) if brand in rec else rec.append(brand)
        self.cfg["marcas_recolhidas"] = rec
        self.refresh()

    def set_status(self, text: str, level: str) -> None:
        color = {"ok": GREEN, "wait": ORANGE, "err": RED}.get(level, ORANGE)
        self.dot.setStyleSheet(f"color: {color}; font-size: 16px;")
        self.status.setText(text)

    # --------------------------------------------------------- lista
    def _brand_header(self, brand, items, collapsed):
        pend = sum(1 for i in items if not core.Store.is_done(i))
        pronta = len(items) - pend
        partes = []
        if pend:
            partes.append(f"{pend} pendente{'s' if pend != 1 else ''}")
        if pronta:
            partes.append(f"{pronta} pronta{'s' if pronta != 1 else ''}")
        b = QPushButton(f"{'▸' if collapsed else '▾'}  {brand}      {' · '.join(partes)}")
        b.setObjectName("marca")
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, br=brand: self._toggle_brand(br))
        return b

    def refresh(self) -> None:
        pos = self.scroll.verticalScrollBar().value()
        while self.lay.count() > 1:
            it = self.lay.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)  # some na hora
                w.deleteLater()
        q = self.busca.text().strip()
        todos = self.store.ordered()
        shown = 0
        w = []
        if self.chk_marca.isChecked():
            rec = set(self.cfg["marcas_recolhidas"])
            for brand, its in core.group_by_brand(todos, q):
                collapsed = brand in rec and not q
                w.append(self._brand_header(brand, its, collapsed))
                if not collapsed:
                    w += [DemandCard(d, self.h) for d in its]
                shown += len(its)
        else:
            its = [d for d in todos if core.matches(d, q)]
            w = [DemandCard(d, self.h) for d in its]
            shown = len(its)
        if not w:
            msg = (f"Nada encontrado para “{q}”." if q else
                   "Nenhuma demanda ainda.\nQuando chegar um álbum no grupo,\nele aparece aqui.")
            vazio = QLabel(msg)
            vazio.setObjectName("soft")
            vazio.setAlignment(Qt.AlignCenter)
            w = [vazio]
        for i, x in enumerate(w):
            self.lay.insertWidget(i, x)
        p, r = self.store.counts()
        extra = f"  ·  {shown} encontrada(s)" if q else ""
        self.counter.setText(f"Pendentes: {p} · Prontas hoje: {r}{extra}")
        ini = (self.cfg["inicio_ref"] or "").strip()
        self.inicio.setText("" if not ini else
                            (f"▶ Acompanhando a partir de: {ini}" if self.cfg["inicio_ok"]
                             else f"⏳ Aguardando “{ini}” aparecer no grupo..."))
        self.inicio.setVisible(bool(ini))
        self.btn_limpar.setVisible(bool(ini))
        self.scroll.verticalScrollBar().setValue(pos)


# ---------------------------------------------------------------- diálogos
def _buttons(dlg, ok_text="Salvar") -> QDialogButtonBox:
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.button(QDialogButtonBox.Ok).setText(ok_text)
    bb.button(QDialogButtonBox.Ok).setObjectName("primario")
    bb.button(QDialogButtonBox.Cancel).setText("Cancelar")
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    return bb


class EditDialog(QDialog):
    def __init__(self, brands, brand="", ref="", parent=None, title="Editar demanda"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(340)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Marca"))
        self.brand = QComboBox()
        self.brand.addItems(brands)
        if brand in brands:
            self.brand.setCurrentText(brand)
        lay.addWidget(self.brand)
        lay.addWidget(QLabel("Referência"))
        self.ref = QLineEdit(ref)
        lay.addWidget(self.ref)
        lay.addWidget(_buttons(self))

    def values(self):
        return self.brand.currentText(), self.ref.text().strip()


class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None, show_monitor=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Configurações")
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)

        lay.addWidget(QLabel("Pasta principal das marcas"))
        row = QHBoxLayout()
        self.pasta = QLineEdit(cfg["pasta_marcas"])
        esc = QPushButton("Escolher...")
        esc.clicked.connect(self._pick)
        row.addWidget(self.pasta, 1)
        row.addWidget(esc)
        lay.addLayout(row)
        self.info = QLabel("")
        self.info.setObjectName("soft")
        lay.addWidget(self.info)
        self.pasta.textChanged.connect(self._info)
        self._info()

        lay.addWidget(QLabel("Grupos a acompanhar (um por linha; vazio = qualquer grupo aberto)"))
        self.grupos = QPlainTextEdit("\n".join(cfg["grupos"]))
        self.grupos.setFixedHeight(70)
        lay.addWidget(self.grupos)

        lay.addWidget(QLabel("Como as demandas chegam"))
        self.modo = QComboBox()
        self.modo.addItem("Fotos primeiro (ou no mesmo álbum) e a legenda junto/depois", "fotos_antes")
        self.modo.addItem("Texto com marca/referência primeiro e fotos depois", "texto_antes")
        self.modo.setCurrentIndex(0 if cfg["modo"] == "fotos_antes" else 1)
        lay.addWidget(self.modo)

        lay.addWidget(QLabel("Acompanhamento"))
        self.sessao = QComboBox()
        self.sessao.addItem("Compartilhado: acompanha a conversa que estiver aberta na tela", "compartilhada")
        self.sessao.addItem("Dedicado: sessão própria só do grupo (você usa o WhatsApp livremente)", "dedicada")
        self.sessao.setCurrentIndex(0 if cfg["sessao"] == "compartilhada" else 1)
        lay.addWidget(self.sessao)
        lay.addWidget(QLabel("Nome do grupo (modo dedicado)"))
        self.grupo_ded = QLineEdit(cfg["grupo_dedicado"])
        lay.addWidget(self.grupo_ded)
        if show_monitor:
            b = QPushButton("Mostrar a sessão do monitor (para escanear o QR code)")
            b.clicked.connect(show_monitor)
            lay.addWidget(b)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Esperar a legenda por (segundos)"))
        self.espera = QSpinBox()
        self.espera.setRange(10, 3600)
        self.espera.setValue(int(cfg["espera_texto_seg"]))
        r2.addWidget(self.espera)
        r2.addStretch(1)
        lay.addLayout(r2)
        self.destacar = QCheckBox("Abrir a lista numa janela separada (além da janela principal)")
        self.destacar.setChecked(bool(cfg["lista_destacada"]))
        lay.addWidget(self.destacar)
        self.compat = QCheckBox("Modo de compatibilidade gráfica (corrige tela cinza/branca; reabra o programa)")
        self.compat.setChecked(bool(cfg["compat_grafica"]))
        lay.addWidget(self.compat)
        self.fixar = QCheckBox("Fixar a lista na frente quando destacada")
        self.fixar.setChecked(bool(cfg["fixar_na_frente"]))
        lay.addWidget(self.fixar)
        lay.addWidget(_buttons(self))

    def _pick(self):
        d = QFileDialog.getExistingDirectory(self, "Pasta principal das marcas", self.pasta.text())
        if d:
            self.pasta.setText(d)

    def _info(self):
        p = self.pasta.text().strip()
        if not p:
            self.info.setText("Nenhuma pasta escolhida.")
        elif not Path(p).is_dir():
            self.info.setText("⚠ Essa pasta não existe.")
            self.info.setStyleSheet(f"color: {RED};")
        else:
            self.info.setStyleSheet(f"color: {SOFT};")
            self.info.setText(f"{len(core.list_brands(p))} marca(s) encontrada(s).")

    def apply(self):
        c = self.cfg
        c["pasta_marcas"] = self.pasta.text().strip()
        c["grupos"] = [g.strip() for g in self.grupos.toPlainText().splitlines() if g.strip()]
        c["modo"] = self.modo.currentData()
        c["sessao"] = self.sessao.currentData()
        c["grupo_dedicado"] = self.grupo_ded.text().strip()
        c["espera_texto_seg"] = self.espera.value()
        c["fixar_na_frente"] = self.fixar.isChecked()
        c["compat_grafica"] = self.compat.isChecked()


class ImportDialog(QDialog):
    """Importar a demanda atual: escolher das pastas ou colar a lista."""

    def __init__(self, root, brands, parent=None):
        super().__init__(parent)
        self.root, self.brands = root, brands
        self.setWindowTitle("Importar demanda atual")
        self.setMinimumSize(420, 420)
        lay = QVBoxLayout(self)
        self.tabs = QTabWidget()
        a = QWidget()
        la = QVBoxLayout(a)
        self.marca = QComboBox()
        self.marca.addItems(brands)
        self.marca.currentTextChanged.connect(self._fill)
        la.addWidget(self.marca)
        self.lista = QListWidget()
        self.lista.setSelectionMode(QAbstractItemView.MultiSelection)
        la.addWidget(self.lista, 1)
        self.tabs.addTab(a, "Escolher das pastas")
        b = QWidget()
        lb = QVBoxLayout(b)
        lb.addWidget(QLabel("Uma demanda por linha, ex.: BEIRA RIO 8513.115"))
        self.texto = QPlainTextEdit()
        lb.addWidget(self.texto, 1)
        self.tabs.addTab(b, "Colar lista")
        lay.addWidget(self.tabs, 1)
        self.c_site = QCheckBox("Já está no Site")
        self.c_atac = QCheckBox("Já está no Atacado")
        lay.addWidget(self.c_site)
        lay.addWidget(self.c_atac)
        lay.addWidget(_buttons(self, "Importar"))
        self._fill(self.marca.currentText())

    def _fill(self, brand):
        self.lista.clear()
        base = Path(self.root) / brand
        try:
            dirs = sorted((d for d in base.iterdir() if d.is_dir()),
                          key=lambda d: d.stat().st_mtime, reverse=True)
        except OSError:
            dirs = []
        import datetime as dt
        for d in dirs:
            self.lista.addItem(f"{d.name}   ·   {dt.datetime.fromtimestamp(d.stat().st_mtime):%d/%m}")
            self.lista.item(self.lista.count() - 1).setData(Qt.UserRole, str(d))

    def entries(self):
        """Lista de (marca|None, referencia, pasta|None, legenda)."""
        out = []
        if self.tabs.currentIndex() == 0:
            brand = self.marca.currentText()
            for it in self.lista.selectedItems():
                p = Path(it.data(Qt.UserRole))
                ref = p.name
                if core.norm(ref).startswith(core.norm(brand)):
                    ref = ref[len(brand):].strip()
                out.append((brand, ref, p, p.name))
        else:
            for line in self.texto.toPlainText().splitlines():
                line = line.strip()
                if not line:
                    continue
                b, r, _ = core.split_caption(line, self.brands)
                out.append((b, r, None, line))
        return out, self.c_site.isChecked(), self.c_atac.isChecked()


class PasteDialog(QDialog):
    """Cola demandas de fora do programa (uma por linha) e mostra a prévia antes de adicionar."""

    _ROTULO = {"nova": ("✔", GREEN, "nova"),
               "revisar": ("⚠", WARN, "confira a marca"),
               "sem_marca": ("⚠", WARN, "marca não reconhecida → vai para Revisar"),
               "repetida": ("↺", SOFT, "já está na lista")}

    def __init__(self, brands, items, parent=None):
        super().__init__(parent)
        self.brands, self.items = brands, items
        self.setWindowTitle("Colar demandas")
        self.setMinimumSize(460, 520)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Cole aqui as demandas (uma por linha), ex.:\nBEIRA RIO 8513.115"))
        self.texto = QPlainTextEdit()
        self.texto.setPlaceholderText("BEIRA RIO 8513.115\nBEBECÊ T3533-150\nDAKOTA 777-1")
        clip = QGuiApplication.clipboard().text()
        if clip and clip.strip():
            self.texto.setPlainText(clip)
        self.texto.textChanged.connect(self._prever)
        lay.addWidget(self.texto, 2)
        self.resumo = QLabel("")
        self.resumo.setObjectName("soft")
        lay.addWidget(self.resumo)
        self.previa = QListWidget()
        self.previa.setSelectionMode(QAbstractItemView.NoSelection)
        lay.addWidget(self.previa, 3)
        self.c_site = QCheckBox("Já estão no Site")
        self.c_atac = QCheckBox("Já estão no Atacado")
        lay.addWidget(self.c_site)
        lay.addWidget(self.c_atac)
        self.bb = _buttons(self, "Adicionar")
        lay.addWidget(self.bb)
        self._prever()

    def _prever(self):
        self.plano = core.plan_paste(self.texto.toPlainText(), self.brands, self.items)
        self.previa.clear()
        for it in self.plano:
            icone, cor, txt = self._ROTULO[it["status"]]
            nome = f"{it['brand']}  {it['ref']}" if it["brand"] else it["line"]
            item = QListWidgetItem(f"{icone}  {nome}   ·   {txt}")
            item.setForeground(QColor(cor))
            self.previa.addItem(item)
        novas = sum(1 for i in self.plano if i["status"] != "repetida")
        rep = len(self.plano) - novas
        self.resumo.setText(f"{novas} para adicionar" + (f" · {rep} já estavam na lista" if rep else ""))
        self.bb.button(QDialogButtonBox.Ok).setText(f"Adicionar {novas}" if novas else "Adicionar")
        self.bb.button(QDialogButtonBox.Ok).setEnabled(novas > 0)

    def entries(self):
        """[(marca|None, referencia, None, linha)] só das linhas novas."""
        return ([(i["brand"], i["ref"], None, i["line"]) for i in self.plano
                 if i["status"] != "repetida"], self.c_site.isChecked(), self.c_atac.isChecked())


class PainelDialog(QDialog):
    def __init__(self, history, cfg, log_lines, on_summary, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Painel")
        self.resize(620, 460)
        self.history = history
        lay = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tab = QTableWidget(0, 5)
        self.tab.setHorizontalHeaderLabels(["Hora", "O que aconteceu", "Marca", "Referência", "Fotos"])
        self.tab.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tab.verticalHeader().hide()
        self.tab.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tab.cellDoubleClicked.connect(self._open_row)
        self._rows = history.today()
        for r in self._rows:
            i = self.tab.rowCount()
            self.tab.insertRow(i)
            for c, k in enumerate(("hora", "evento", "marca", "ref", "fotos")):
                self.tab.setItem(i, c, QTableWidgetItem(str(r.get(k, ""))))
        self.tabs.addTab(self.tab, "Histórico de hoje")
        self.live = QPlainTextEdit("\n".join(log_lines))
        self.live.setReadOnly(True)
        self.tabs.addTab(self.live, "Atividade ao vivo")
        lay.addWidget(self.tabs, 1)
        row = QHBoxLayout()
        b1 = QPushButton("Resumo do dia")
        b1.setObjectName("primario")
        b1.clicked.connect(on_summary)
        b2 = QPushButton("Abrir pasta das marcas")
        b2.clicked.connect(lambda: cfg["pasta_marcas"] and open_path(cfg["pasta_marcas"]))
        b3 = QPushButton("Abrir pasta do programa")
        b3.clicked.connect(lambda: open_path(core.data_dir()))
        for b in (b1, b2, b3):
            row.addWidget(b)
        lay.addLayout(row)

    def _open_row(self, row, _col):
        p = self._rows[row].get("pasta")
        if p and Path(p).exists():
            open_path(p)

    def append_log(self, line):
        self.live.appendPlainText(line)


def confirm(parent, title, text, default_no=True) -> bool:
    m = QMessageBox(QMessageBox.Question, title, text, QMessageBox.Yes | QMessageBox.No, parent)
    m.button(QMessageBox.Yes).setText("Sim")
    m.button(QMessageBox.No).setText("Não")
    m.setDefaultButton(QMessageBox.No if default_no else QMessageBox.Yes)
    return m.exec() == QMessageBox.Yes
