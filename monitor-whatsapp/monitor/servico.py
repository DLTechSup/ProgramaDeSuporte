"""Thread do monitor: dona do navegador (o Playwright exige uma thread so) e do laco de leitura."""
from __future__ import annotations

import queue
import threading
import time

from .config import Config
from .leitor import Navegador
from .motor import Processador
from .registro import RegistroDoDia


class Servico(threading.Thread):
    def __init__(self, cfg: Config, eventos: queue.Queue) -> None:
        super().__init__(daemon=True)
        self.cfg, self.eventos = cfg, eventos
        self.comandos: queue.Queue = queue.Queue()
        self.monitorando = False
        self.intervalo = 4.0
        self.nav: Navegador | None = None
        self.proc: Processador | None = None

    def emitir(self, tipo: str, dado=None) -> None:
        self.eventos.put((tipo, dado))
        texto = {"log": dado, "status": dado, "erro": f"ERRO: {dado}"}.get(tipo)   # 'salvo' ja aparece como 'log'
        if texto and self.cfg.pasta_base:
            try:
                RegistroDoDia(self.cfg.pasta_base).escrever(str(texto))
            except OSError:
                pass

    def pedir(self, comando: str) -> None:
        self.comandos.put(comando)

    def run(self) -> None:
        try:
            self.emitir("status", "Abrindo o navegador...")
            self.nav = Navegador(canal=self.cfg.navegador)
            self.nav.iniciar()
        except Exception as e:  # noqa: BLE001
            self.emitir("erro", f"{e}")
            return
        try:
            self._laco()
        finally:
            self.nav.fechar()
            self.emitir("status", "Navegador fechado.")
            self.emitir("encerrado", None)

    def _laco(self) -> None:
        ultimo_status = ""
        while True:
            if not self.nav.vivo():
                self.emitir("log", "A janela do WhatsApp foi fechada.")
                return
            for _ in range(self.comandos.qsize()):
                if self._comando(self.comandos.get_nowait()) == "sair":
                    return
            if not self.nav.logado():
                novo = "Entre no WhatsApp: leia o QR code na janela do navegador."
                self._status(novo, ultimo_status)
                ultimo_status = novo
                time.sleep(1.5)
                continue
            if self.monitorando and self.proc:
                try:
                    self.proc.ciclo()
                    novo = f"Monitorando {len(self.cfg.grupos)} grupo(s)..."
                except Exception as e:  # noqa: BLE001
                    novo = "Erro na leitura (vou tentar de novo)."
                    self.emitir("log", f"Erro: {type(e).__name__}: {e}")
                self._status(novo, ultimo_status)
                ultimo_status = novo
                time.sleep(self.intervalo)
            else:
                novo = "WhatsApp conectado. Monitor parado." if not self.monitorando else "Escolha a pasta e os grupos."
                self._status(novo, ultimo_status)
                ultimo_status = novo
                time.sleep(1.0)

    def _status(self, novo: str, antigo: str) -> None:
        if novo != antigo:
            self.emitir("status", novo)

    def _comando(self, c: str) -> str:
        if c == "sair":
            return "sair"
        if c == "iniciar":
            if not self.cfg.pasta_base or not self.cfg.grupos:
                self.emitir("log", "Escolha a pasta das demandas e pelo menos um grupo antes de iniciar.")
                return ""
            self.proc = Processador(self.cfg, self.nav, evento=self.emitir)
            self.monitorando = True
            self.emitir("status", f"Monitorando {len(self.cfg.grupos)} grupo(s)...")
            self.emitir("log", "Monitor iniciado. Grupos: " + ", ".join(f"{g.nome} ({g.tipo})" for g in self.cfg.grupos))
        elif c == "pausar":
            self.monitorando = False
            self.emitir("log", "Monitor pausado.")
        elif c == "conversas":
            try:
                self.emitir("conversas", self.nav.conversas())
            except Exception as e:  # noqa: BLE001
                self.emitir("log", f"Não consegui listar as conversas: {e}")
        elif c == "diagnostico":
            try:
                self.emitir("diagnostico", self.nav.diagnostico())
            except Exception as e:  # noqa: BLE001
                self.emitir("log", f"Diagnóstico falhou: {e}")
        return ""
