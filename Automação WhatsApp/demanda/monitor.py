"""Monitor: lê o chat aberto numa visualização do WhatsApp Web e cria as demandas.

SOMENTE LEITURA: só executa JavaScript que lê a página. Nunca envia mensagem.
Todas as chamadas ao navegador são assíncronas (callbacks na thread da interface).
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import time
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from . import core, js

VISIVEL_ESPERA_MAX = 10  # ciclos esperando miniatura virar foto


def _decode(data_url):
    if not data_url or "," not in data_url:
        return None
    try:
        return base64.b64decode(data_url.split(",", 1)[1])
    except ValueError:
        return None


class Monitor(QObject):
    status = Signal(str, str)  # texto, nível: ok | wait | err
    changed = Signal()
    log = Signal(str)

    def __init__(self, view, cfg, store, history, seen, dedicated=False, parent=None):
        super().__init__(parent)
        self.view, self.cfg, self.store, self.hist, self.seen = view, cfg, store, history, seen
        self.dedicated = dedicated
        self.busy = False
        self.running = False
        self.pending: dict[str, dict] = {}  # remetente -> {"images": [], "msg": {}, "since": t}
        self.current: dict[str, tuple] = {}  # remetente -> (marca, ref)  (modo texto_antes)
        self.waits: dict[str, int] = {}
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    # ------------------------------------------------------------ controle
    def start(self):
        self.running = True
        self.timer.start(int(max(0.5, float(self.cfg["intervalo_seg"])) * 1000))
        self.log.emit("Monitor iniciado.")

    def stop(self):
        self.running = False
        self.timer.stop()

    def page(self):
        return self.view.page()

    # ----------------------------------------------------- ponte com o JS
    def run_js(self, code, cb):
        self.page().runJavaScript(code, 0, cb)

    def job(self, body: str, cb, timeout_ms=30000):
        """Roda código assíncrono na página e lê o resultado por polling."""
        key = uuid.uuid4().hex
        start = ("(()=>{window.__inf=window.__inf||{r:{}};const k=%s;(async()=>{try{"
                 "window.__inf.r[k]={ok:true,v:await (async()=>{%s\n%s})()};}catch(e){"
                 "window.__inf.r[k]={ok:false,e:String(e)};}})();return 1;})()"
                 % (json.dumps(key), js.HELPERS, body))
        poll = ("(()=>{const x=window.__inf&&window.__inf.r[%s];if(!x)return null;"
                "delete window.__inf.r[%s];return JSON.stringify(x);})()"
                % (json.dumps(key), json.dumps(key)))
        t0 = time.monotonic()

        def check():
            def got(r):
                if r:
                    try:
                        x = json.loads(r)
                    except ValueError:
                        x = {"ok": False, "e": "resposta inválida"}
                    cb(x.get("v") if x.get("ok") else None, x.get("e"))
                elif (time.monotonic() - t0) * 1000 > timeout_ms:
                    cb(None, "tempo esgotado")
                else:
                    QTimer.singleShot(300, check)
            self.run_js(poll, got)

        self.run_js(start, lambda _r: QTimer.singleShot(300, check))

    # --------------------------------------------------------------- ciclo
    def tick(self):
        if self.busy or not self.running:
            return
        self.busy = True
        self._flush_pending()
        if self.dedicated and self.cfg["grupo_dedicado"]:
            self.run_js(js.OPEN_CHAT.replace("{NAME}", json.dumps(self.cfg["grupo_dedicado"])),
                        lambda _r: self.run_js(js.SCAN, self._on_scan))
        else:
            self.run_js(js.SCAN, self._on_scan)

    def _free(self):
        self.busy = False

    def _on_scan(self, raw):
        try:
            res = json.loads(raw) if raw else None
        except ValueError:
            res = None
        if not res:
            self.status.emit("Aguardando o WhatsApp carregar...", "wait")
            return self._free()
        if not res.get("ready"):
            self.status.emit("Escaneie o QR code com o celular..." if res.get("qr")
                             else "Aguardando o WhatsApp carregar...", "wait")
            return self._free()
        if not res.get("open"):
            self.status.emit("Abra o grupo das demandas para acompanhar.", "wait")
            return self._free()
        title = res.get("title", "")
        grupos = [g.strip().lower() for g in (self.cfg["grupos"] or []) if g.strip()]
        if not res.get("isGroup"):
            self.status.emit(f"“{title}” não é grupo — não acompanhado.", "wait")
            return self._free()
        if grupos and not self.dedicated and title.lower() not in grupos:
            self.status.emit(f"“{title}” não está na lista de grupos.", "wait")
            return self._free()
        root = self.cfg["pasta_marcas"]
        if not root or not Path(root).is_dir():
            self.status.emit("Escolha a pasta das marcas (⚙ Configurações).", "err")
            return self._free()
        self.status.emit(f"Acompanhando: {title}", "ok")
        hoje = core.today()
        fila = []
        for m in res["msgs"]:
            if m["id"] in self.seen:
                continue
            if m["date"] and m["date"] != hoje:
                self.seen.add(m["id"])
                continue
            fila.append(m)
        self._next(fila)

    def _next(self, fila):
        if not fila:
            return self._free()
        m = fila.pop(0)
        srcs = [p for p in m["photos"]]
        if m["thumbs"] > 0 and self.waits.get(m["id"], 0) < VISIVEL_ESPERA_MAX:
            self.waits[m["id"]] = self.waits.get(m["id"], 0) + 1
            return self._free()  # espera as fotos carregarem, mantendo a ordem
        if not srcs and not m["caption"].strip():
            self.seen.add(m["id"])
            return self._next(fila)

        def after(images):
            try:
                self._apply(m, images)
            except Exception as e:  # nunca derruba o monitor
                self.log.emit(f"Erro ao processar mensagem: {e!r}")
            self.seen.add(m["id"])
            self.changed.emit()
            self._next(fila)

        self._fetch_photos(m, after)

    def _fetch_photos(self, m, cb):
        use_walk = self.dedicated and m["plus"] > 0
        urls = [p["src"] for p in m["photos"] if not (use_walk and p["tile"])]
        if not urls and not use_walk:
            return cb([])

        def got(list_, _err):
            imgs = [b for b in (_decode(x) for x in (list_ or [])) if b]
            if use_walk:
                return self._walk(m, imgs, cb)
            cb(imgs)

        if urls:
            self.job(js.FETCH.replace("{SRCS}", json.dumps(urls)), got)
        else:
            got([], None)

    def _walk(self, m, imgs, cb):
        visible = sum(1 for p in m["photos"] if not p["tile"])
        count = max(1, int(self.cfg["album_extra"]) + m["plus"] - visible)
        body = js.WALK.replace("{MSGID}", json.dumps(m["id"])).replace("{COUNT}", str(count))

        def got(list_, err):
            extra = [b for b in (_decode(x) for x in (list_ or [])) if b]
            if err:
                self.log.emit(f"Álbum +{m['plus']}: {err}")
            cb(imgs + extra)

        self.job(body, got, timeout_ms=60000)

    def complete_album(self, did, done=None):
        """Botão do cartão: abre o álbum e pega as fotos escondidas (ação do usuário)."""
        d = self.store.get(did)
        if not d or not d.get("msg_id") or not d.get("plus"):
            return
        m = {"id": d["msg_id"], "plus": d["plus"],
             "photos": [{"src": "", "tile": False}] * 3}
        self._walk(m, [], lambda imgs: self._after_complete(d, imgs, done))

    def _after_complete(self, d, imgs, done):
        folder = Path(d["folder"])
        n = core.save_images(folder, imgs)
        warn = [w for w in d["warn"] if "+" not in w]
        self.store.update(d["id"], photos=core.count_photos(folder), warn=warn, plus=0)
        self.hist.add("Fotos adicionadas", d["brand"], d["ref"], n, str(folder))
        self.log.emit(f"Álbum completado: {n} foto(s) nova(s).")
        self.changed.emit()
        if done:
            done()

    # ------------------------------------------------------ regras do plano
    def _apply(self, m, images):
        cap, who = m["caption"].strip(), m["sender"]
        root = self.cfg["pasta_marcas"]
        brands = core.list_brands(root, self.cfg["pastas_ignoradas"])
        if images and cap:
            return self._make(m, cap, images, brands)
        if images:
            cur = self.current.get(who) if self.cfg["modo"] == "texto_antes" else None
            if cur:
                return self._make(m, f"{cur[0]} {cur[1]}".strip(), images, brands)
            p = self.pending.setdefault(who, {"images": [], "msg": m, "since": time.time()})
            p["images"] += images
            return
        if cap:
            p = self.pending.pop(who, None)
            if p:
                return self._make(p["msg"], cap, p["images"], brands, plus_msg=p["msg"])
            if self.cfg["modo"] == "texto_antes":
                brand, ref, _ = core.split_caption(cap, brands)
                if brand:
                    self.current[who] = (brand, ref)

    def _flush_pending(self):
        limite = float(self.cfg["espera_texto_seg"])
        for who, p in list(self.pending.items()):
            if time.time() - p["since"] >= limite:
                self.pending.pop(who)
                brands = core.list_brands(self.cfg["pasta_marcas"], self.cfg["pastas_ignoradas"])
                m = p["msg"]
                nome = f"sem referencia {m['time'].replace(':', 'h')} {who}".strip()
                try:
                    self._make(m, nome, p["images"], brands, force_review=True)
                except Exception as e:
                    self.log.emit(f"Erro: {e!r}")
                self.changed.emit()

    def _make(self, m, caption, images, brands, plus_msg=None, force_review=False):
        root = self.cfg["pasta_marcas"]
        brand, ref, score = (None, caption, 0.0) if force_review else core.split_caption(caption, brands)
        folder = core.target_folder(root, brand, ref, caption)
        warn = []
        if force_review:
            warn.append("⚠ sem referência: revisar marca e referência")
        elif not brand:
            warn.append("⚠ marca não reconhecida")
        elif score < 1.0:
            warn.append("⚠ revisar marca e referência")
        pm = plus_msg or m
        plus = pm["plus"] if not (self.dedicated and pm["plus"]) else 0
        if plus:
            warn.append(f"⚠ álbum com +{plus}: faltam fotos (use “Pegar fotos restantes”)")
        existing = self.store.find_open(brand or "", ref) if brand else None
        if existing:
            n = core.save_images(Path(existing["folder"]), images)
            self.store.update(existing["id"], photos=core.count_photos(Path(existing["folder"])))
            self.hist.add("Fotos adicionadas", brand, ref, n, existing["folder"])
            self.log.emit(f"+{n} foto(s) em {brand} {ref}")
            return
        existed = folder.exists()
        if existed:
            warn.append("⚠ pasta já existia")
        n = core.save_images(folder, images) if images else 0
        if not images:
            folder.mkdir(parents=True, exist_ok=True)
        total = core.count_photos(folder)
        if total == 0:
            warn.append("⚠ sem fotos")
        self.store.add(brand=brand or "", ref=ref, folder=str(folder), photos=total,
                       sender=m["sender"], time=(m["time"] or dt.datetime.now().strftime("%H:%M")),
                       warn=warn, msg_id=pm["id"] if plus else "", plus=plus)
        self.hist.add("Demanda criada", brand or "(sem marca)", ref, total, str(folder))
        self.log.emit(f"Demanda criada: {brand or '?'} {ref} ({total} foto(s))")
