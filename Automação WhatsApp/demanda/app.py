"""Janela principal: WhatsApp Web embutido + lista de demandas ao lado."""
from __future__ import annotations

import collections
import datetime as dt
import re
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QApplication, QMainWindow, QSplitter, QVBoxLayout, QWidget)

from . import core, ui
from .monitor import Monitor

WA_URL = "https://web.whatsapp.com"


def clean_user_agent(ua: str) -> str:
    """Tira o 'QtWebEngine/x' para o WhatsApp Web tratar como Chrome comum."""
    return re.sub(r"\s*QtWebEngine/\S+", "", ua)


class WaPage(QWebEnginePage):
    """Links externos abrem no navegador padrão; o resto fica no WhatsApp."""

    def acceptNavigationRequest(self, url, nav_type, is_main):
        if (nav_type == QWebEnginePage.NavigationTypeLinkClicked
                and "whatsapp" not in url.host()):
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main)

    def createWindow(self, _type):
        tmp = QWebEnginePage(self.profile(), self)
        tmp.urlChanged.connect(lambda u: (QDesktopServices.openUrl(u), tmp.deleteLater()))
        return tmp


def make_profile(name: str, parent) -> QWebEngineProfile:
    base = core.app_dir() / "perfil_whatsapp" / name
    base.mkdir(parents=True, exist_ok=True)
    p = QWebEngineProfile(name, parent)
    p.setPersistentStoragePath(str(base / "dados"))
    p.setCachePath(str(base / "cache"))
    p.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
    p.setHttpUserAgent(clean_user_agent(p.httpUserAgent()))

    def baixar(item):
        pasta = Path.home() / "Downloads"
        pasta.mkdir(exist_ok=True)
        item.setDownloadDirectory(str(pasta))
        item.accept()

    p.downloadRequested.connect(baixar)
    return p


def make_view(profile, parent=None) -> QWebEngineView:
    v = QWebEngineView(parent)
    v.setPage(WaPage(profile, v))
    v.load(QUrl(WA_URL))
    return v


class MonitorWindow(QWidget):
    """Sessão do monitor (segundo WhatsApp Web, só para o grupo). Fica fora da tela."""

    def __init__(self, parent_app):
        super().__init__()
        self.setWindowTitle("WhatsApp — sessão do monitor")
        self.resize(1100, 820)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.profile = make_profile("monitor", self)
        self.view = make_view(self.profile, self)
        lay.addWidget(self.view)
        self.setAttribute(Qt.WA_DontShowOnScreen, True)
        self.show()  # "mostrado" fora da tela: a página continua renderizando

    def mostrar(self):
        self.hide()
        self.setAttribute(Qt.WA_DontShowOnScreen, False)
        self.show()

    def closeEvent(self, e):
        e.ignore()
        self.hide()
        self.setAttribute(Qt.WA_DontShowOnScreen, True)
        self.show()


class FloatWin(QWidget):
    def __init__(self, on_close):
        super().__init__()
        self.on_close = on_close
        self.setWindowTitle("Demanda do dia")
        self.setObjectName("raiz")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)

    def closeEvent(self, e):
        e.ignore()
        self.on_close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        data = core.app_dir()
        self.cfg = core.Config(data / "config.json")
        self.store = core.Store(data / "lista.json")
        self.hist = core.History(data / "historico.jsonl")
        self.seen = core.Seen(data / "vistos.json")
        self.log_lines = collections.deque(maxlen=500)
        self.painel_dlg = None
        self.mon_win = None
        self.monitor = None
        self.float = None
        self.setWindowTitle("Suporte Informax — Demanda do dia")
        self.resize(1400, 860)

        self.profile = make_profile("principal", self)
        self.view = make_view(self.profile, self)
        handlers = {"toggle": self.h_toggle, "open": self.h_open, "copy": self.h_copy,
                    "edit": self.h_edit, "remove": self.h_remove, "album": self.h_album}
        self.panel = ui.DemandPanel(self.store, handlers)
        self.panel.open_painel.connect(self.show_painel)
        self.panel.open_config.connect(self.show_settings)
        self.panel.toggle_detach.connect(self.toggle_detach)
        self.panel.add_manual.connect(self.add_manual)
        self.panel.import_current.connect(self.import_current)
        self.panel.reconnect.connect(self.reconnect)

        self.split = QSplitter(Qt.Horizontal)
        self.split.addWidget(self.view)
        self.split.addWidget(self.panel)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 0)
        self.split.setSizes([1000, int(self.cfg["largura_lista"])])
        self.setCentralWidget(self.split)
        if self.cfg["geometria"]:
            self.restoreGeometry(QByteArray.fromHex(self.cfg["geometria"].encode()))
        self.setup_monitor()
        if self.cfg["lista_destacada"]:
            QTimer.singleShot(300, self.toggle_detach)
        if not self.cfg["pasta_marcas"]:
            QTimer.singleShot(600, self.show_settings)

    # ------------------------------------------------------------ monitor
    def setup_monitor(self):
        if self.monitor:
            self.monitor.stop()
            self.monitor.deleteLater()
        dedicated = self.cfg["sessao"] == "dedicada"
        view = self.view
        if dedicated:
            if not self.mon_win:
                self.mon_win = MonitorWindow(self)
            view = self.mon_win.view
        self.monitor = Monitor(view, self.cfg, self.store, self.hist, self.seen,
                               dedicated=dedicated, parent=self)
        self.monitor.status.connect(self.panel.set_status)
        self.monitor.changed.connect(self.panel.refresh)
        self.monitor.log.connect(self.on_log)
        self.monitor.start()

    def on_log(self, text):
        line = f"{dt.datetime.now():%H:%M:%S}  {text}"
        self.log_lines.append(line)
        if self.painel_dlg and self.painel_dlg.isVisible():
            self.painel_dlg.append_log(line)

    def reconnect(self):
        self.view.reload()
        self.setup_monitor()

    # ----------------------------------------------------------- handlers
    def _later_refresh(self):
        QTimer.singleShot(0, self.panel.refresh)

    def h_toggle(self, did, field, value):
        d = self.store.get(did)
        if not d:
            return
        self.store.update(did, **{field: bool(value)})
        nome = "Site" if field == "site" else "Atacado"
        self.hist.add(f"{nome} marcado OK" if value else f"{nome} desmarcado",
                      d["brand"], d["ref"], d["photos"], d["folder"])
        self._later_refresh()

    def h_open(self, did):
        d = self.store.get(did)
        if d and Path(d["folder"]).exists():
            ui.open_path(d["folder"])

    def h_copy(self, did):
        d = self.store.get(did)
        if d:
            ui.copy_text(d["ref"])
            self.panel.status.setText(f"Referência copiada: {d['ref']}")

    def brands(self):
        return core.list_brands(self.cfg["pasta_marcas"], self.cfg["pastas_ignoradas"])

    def h_edit(self, did):
        d = self.store.get(did)
        if not d:
            return
        dlg = ui.EditDialog(self.brands(), d["brand"], d["ref"], self)
        if not dlg.exec():
            return
        brand, ref = dlg.values()
        if not brand:
            return
        new = core.target_folder(self.cfg["pasta_marcas"], brand, ref)
        old = Path(d["folder"])
        try:
            core.move_folder(old, new)
        except OSError as e:
            ui.QMessageBox.warning(self, "Editar", f"Não consegui mover a pasta:\n{e}")
            return
        warn = [w for w in d["warn"] if "marca" not in w and "revisar" not in w]
        self.store.update(did, brand=brand, ref=ref, folder=str(new),
                          photos=core.count_photos(new), warn=warn)
        self.hist.add("Editada", brand, ref, core.count_photos(new), str(new))
        self._later_refresh()

    def h_remove(self, did):
        d = self.store.get(did)
        if d and ui.confirm(self, "Tirar da lista",
                            "Tirar da lista?\n(A pasta e as fotos NÃO são apagadas.)"):
            self.store.remove(did)
            self.hist.add("Tirada da lista", d["brand"], d["ref"], d["photos"], d["folder"])
            self._later_refresh()

    def h_album(self, did):
        if self.monitor.dedicated:
            self.on_log("Para pegar as fotos restantes, use o modo compartilhado.")
        self.monitor.complete_album(did)

    # ------------------------------------------------------------ diálogos
    def add_manual(self):
        if not self.cfg["pasta_marcas"]:
            return self.show_settings()
        dlg = ui.EditDialog(self.brands(), "", "", self, "Adicionar demanda")
        if not dlg.exec():
            return
        brand, ref = dlg.values()
        if not brand or not ref:
            return
        folder = core.target_folder(self.cfg["pasta_marcas"], brand, ref)
        folder.mkdir(parents=True, exist_ok=True)
        self.store.add(brand=brand, ref=ref, folder=str(folder), photos=core.count_photos(folder),
                       sender="manual")
        self.hist.add("Adicionada manualmente", brand, ref, core.count_photos(folder), str(folder))
        self.panel.refresh()

    def import_current(self):
        root = self.cfg["pasta_marcas"]
        if not root:
            return self.show_settings()
        brands = self.brands()
        dlg = ui.ImportDialog(root, brands, self)
        if not dlg.exec():
            return
        entries, site, atac = dlg.entries()
        novas = ja = 0
        for brand, ref, pasta, legenda in entries:
            folder = pasta or core.target_folder(root, brand, ref, legenda)
            if any(Path(i["folder"]) == folder for i in self.store.items):
                ja += 1
                continue
            folder.mkdir(parents=True, exist_ok=True)
            warn = [] if brand else ["⚠ marca não reconhecida"]
            self.store.add(brand=brand or "", ref=ref, folder=str(folder), sender="importada",
                           photos=core.count_photos(folder), site=site, atacado=atac, warn=warn)
            self.hist.add("Importada (demanda atual)", brand or "(sem marca)", ref,
                          core.count_photos(folder), str(folder))
            novas += 1
        self.panel.refresh()
        self.panel.status.setText(f"{novas} adicionada(s), {ja} já estavam.")

    def show_settings(self):
        dlg = ui.SettingsDialog(self.cfg, self,
                                show_monitor=lambda: (self.mon_win or self._criar_mon()).mostrar())
        if dlg.exec():
            antes = (self.cfg["sessao"], self.cfg["modo"], self.cfg["grupo_dedicado"])
            dlg.apply()
            self.hist.add("Configurações salvas")
            if antes != (self.cfg["sessao"], self.cfg["modo"], self.cfg["grupo_dedicado"]):
                self.setup_monitor()
            if self.float:
                self._apply_float_flags()

    def _criar_mon(self):
        self.mon_win = MonitorWindow(self)
        return self.mon_win

    def show_painel(self):
        self.painel_dlg = ui.PainelDialog(self.hist, self.cfg, list(self.log_lines),
                                          self.make_summary, self)
        self.painel_dlg.show()

    def make_summary(self):
        items = self.store.ordered()
        texto = core.summary_text(items)
        arq = core.app_dir() / f"Resumo {dt.date.today():%d-%m-%Y}.txt"
        arq.write_text(texto, "utf-8")
        ui.copy_text(texto)
        self.hist.add("Resumo do dia gerado")
        self.panel.status.setText("Resumo copiado para a área de transferência.")
        ui.open_path(arq)

    # ------------------------------------------------- lista destacada
    def _apply_float_flags(self):
        flags = Qt.Tool | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
        if self.cfg["fixar_na_frente"]:
            flags |= Qt.WindowStaysOnTopHint
        self.float.setWindowFlags(flags)
        self.float.show()

    def toggle_detach(self):
        if self.float:
            return self.dock()
        self.float = FloatWin(self.dock)
        self.float.lay.addWidget(self.panel)
        self.float.resize(380, 680)
        g = self.cfg.data.get("geometria_lista")
        if g:
            self.float.restoreGeometry(QByteArray.fromHex(g.encode()))
        self._apply_float_flags()
        self.cfg["lista_destacada"] = True

    def dock(self):
        if not self.float:
            return
        self.cfg["geometria_lista"] = bytes(self.float.saveGeometry().toHex()).decode()
        self.split.addWidget(self.panel)
        self.split.setSizes([1000, int(self.cfg["largura_lista"])])
        self.float.hide()
        self.float.deleteLater()
        self.float = None
        self.cfg["lista_destacada"] = False

    # ----------------------------------------------------------- fechar
    def closeEvent(self, e):
        if not ui.confirm(self, "Fechar",
                          "Se fechar, a lista deixa de receber as demandas.\nQuer mesmo fechar?"):
            return e.ignore()
        self.cfg["geometria"] = bytes(self.saveGeometry().toHex()).decode()
        if self.float:
            self.cfg["geometria_lista"] = bytes(self.float.saveGeometry().toHex()).decode()
            self.float.hide()
        self.monitor.stop()
        e.accept()
        QApplication.quit()
