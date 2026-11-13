"""Leitura do WhatsApp Web por um navegador proprio (Chrome, com Edge de reserva, usando um perfil separado do seu). SO LE: nunca envia nada.

Os seletores ficam juntos aqui em cima porque o WhatsApp muda a tela de tempos em tempos.
"""
from __future__ import annotations

import base64
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from .config import RAIZ

URL = "https://web.whatsapp.com"
PERFIL = RAIZ / "perfil_whatsapp"

# JS que roda dentro da pagina: devolve as mensagens do chat aberto (so o que e visivel/carregado).
JS_LER = r"""
() => {
  const main = document.querySelector('#main');
  if (!main) return {aberto: false, titulo: '', msgs: []};
  const t = main.querySelector('header span[title]');
  const todos = [...main.querySelectorAll('div[data-id]')];
  const externos = todos.filter(n => !n.parentElement.closest('div[data-id]'));
  const msgs = externos.map(n => {
    const id = n.getAttribute('data-id') || '';
    const pre = n.querySelector('[data-pre-plain-text]');
    const caps = [...n.querySelectorAll('span.selectable-text')].filter(s => !s.parentElement.closest('span.selectable-text'));
    const imgs = [...n.querySelectorAll('img')].filter(i => !i.hasAttribute('data-plain-text') && !i.classList.contains('emoji')
        && (i.src.startsWith('blob:') || i.src.startsWith('data:image')) && (i.naturalWidth > 40 || i.width > 40));
    let mais = 0;
    for (const el of n.querySelectorAll('*')) {
      if (el.children.length === 0) { const m = (el.textContent || '').trim().match(/^\+(\d+)$/); if (m) { mais = parseInt(m[1], 10); break; } }
    }
    return {
      id, minha: id.startsWith('true_'),
      pre: pre ? pre.getAttribute('data-pre-plain-text') : '',
      legenda: caps.map(c => c.innerText).join('\n').trim(),
      blobs: imgs.filter(i => i.src.startsWith('blob:')).map(i => i.src),
      carregando: imgs.filter(i => i.src.startsWith('data:image')).length,
      mais
    };
  });
  return {aberto: true, titulo: t ? (t.getAttribute('title') || t.textContent) : '', msgs};
}
"""

JS_BAIXAR = r"""
async (urls) => Promise.all(urls.map(async u => {
  try {
    const b = await (await fetch(u)).blob();
    return await new Promise(res => { const f = new FileReader(); f.onload = () => res(f.result.split(',')[1]); f.readAsDataURL(b); });
  } catch (e) { return ''; }
}))
"""

JS_CONVERSAS = r"""
() => [...new Set([...document.querySelectorAll('#pane-side span[title]')].map(s => s.getAttribute('title')).filter(Boolean))]
"""

# Visualizador de fotos em tela cheia (album com "+N"): maior imagem blob FORA do #main
JS_VISUALIZADOR = r"""
() => {
  let melhor = null, area = 0;
  for (const i of document.querySelectorAll('img')) {
    if (!i.src.startsWith('blob:') || i.closest('#main') || i.closest('#pane-side')) continue;
    const r = i.getBoundingClientRect(); const a = r.width * r.height;
    if (a > area) { area = a; melhor = i; }
  }
  return melhor ? melhor.src : '';
}
"""


@dataclass
class Mensagem:
    id: str
    minha: bool
    legenda: str
    blobs: list[str]
    carregando: int
    mais: int
    remetente: str = ""
    dia: date | None = None
    hora: str = ""
    fotos: list[bytes] = field(default_factory=list)
    observacao_album: str = ""


def interpretar_pre(pre: str) -> tuple[str, date | None, str]:
    """'[18:42, 06/11/2026] Nome: ' -> (remetente, data, hora)"""
    m = re.match(r"\[(\d{1,2}:\d{2})(?::\d{2})?(?:\s?[AP]M)?,\s*(\d{1,2})/(\d{1,2})/(\d{4})\]\s*(.*?):?\s*$", pre or "")
    if not m:
        return "", None, ""
    try:
        return m.group(5).strip(), date(int(m.group(4)), int(m.group(3)), int(m.group(2))), m.group(1)
    except ValueError:
        return "", None, ""


def completar_datas(msgs: list[Mensagem]) -> None:
    """Mensagem so com foto nao traz data/remetente: herda da vizinha (anterior, ou a proxima)."""
    ultimo = (None, "", "")
    for m in msgs:
        if m.dia:
            ultimo = (m.dia, m.hora, m.remetente)
        elif ultimo[0]:
            m.dia, m.hora, m.remetente = ultimo
    proximo = (None, "", "")
    for m in reversed(msgs):
        if m.dia:
            proximo = (m.dia, m.hora, m.remetente)
        elif not m.dia and proximo[0]:
            m.dia, m.hora, m.remetente = proximo


class Navegador:
    """Dono do navegador. TEM de ser usado sempre na mesma thread (regra do Playwright)."""

    def __init__(self, canal: str = "chrome", executable_path: str | None = None, headless: bool = False,
                 perfil: Path = PERFIL, url: str = URL) -> None:
        self.canal, self.exe, self.headless, self.perfil, self.url = canal, executable_path, headless, perfil, url
        self._pw = None
        self.ctx = None
        self.pagina = None

    def iniciar(self) -> None:
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        args = ["--disable-blink-features=AutomationControlled", "--no-first-run"]
        opcoes = dict(headless=self.headless, args=args, viewport=None if not self.headless else {"width": 1280, "height": 900})
        reserva = "msedge" if self.canal == "chrome" else "chrome"
        tentativas = [{"executable_path": self.exe}] if self.exe else [{"channel": self.canal}, {"channel": reserva}, {}]
        erro = None
        for extra in tentativas:
            try:
                self.ctx = self._pw.chromium.launch_persistent_context(str(self.perfil), **opcoes, **extra)
                break
            except Exception as e:  # noqa: BLE001
                erro = e
        if self.ctx is None:
            raise RuntimeError(f"Não consegui abrir o Chrome (nem o Edge): {erro}")
        self.pagina = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.pagina.goto(self.url)

    def fechar(self) -> None:
        try:
            if self.ctx:
                self.ctx.close()
        finally:
            if self._pw:
                self._pw.stop()
            self.ctx = self._pw = self.pagina = None

    # ---- estado ------------------------------------------------------------
    def vivo(self) -> bool:
        try:
            return bool(self.pagina) and not self.pagina.is_closed()
        except Exception:  # noqa: BLE001
            return False

    def logado(self) -> bool:
        try:
            return self.pagina.locator("#pane-side").count() > 0
        except Exception:  # noqa: BLE001
            return False

    def conversas(self) -> list[str]:
        return self.pagina.evaluate(JS_CONVERSAS)

    # ---- conversa ----------------------------------------------------------
    def abrir_conversa(self, nome: str) -> bool:
        """Abre o grupo pela lista lateral (ou pela busca). So clica; nao digita mensagem."""
        if self._titulo_aberto() == nome:
            return True
        try:
            self.pagina.locator("#pane-side").get_by_title(nome, exact=True).first.click(timeout=3000)
        except Exception:  # noqa: BLE001
            if not self._abrir_pela_busca(nome):
                return False
        fim = time.time() + 5
        while time.time() < fim:
            if self._titulo_aberto() == nome:
                self.pagina.wait_for_timeout(500)
                return True
            self.pagina.wait_for_timeout(200)
        return False

    def _titulo_aberto(self) -> str:
        try:
            return self.pagina.evaluate("() => { const t = document.querySelector('#main header span[title]'); return t ? t.getAttribute('title') : ''; }")
        except Exception:  # noqa: BLE001
            return ""

    def _abrir_pela_busca(self, nome: str) -> bool:
        try:
            caixa = self.pagina.locator('#side div[contenteditable="true"]').first
            caixa.click(timeout=2000)
            caixa.fill(nome)
            self.pagina.wait_for_timeout(1200)
            self.pagina.locator("#pane-side").get_by_title(nome, exact=True).first.click(timeout=3000)
            return True
        except Exception:  # noqa: BLE001
            return False
        finally:
            try:
                self.pagina.keyboard.press("Escape")
            except Exception:  # noqa: BLE001
                pass

    def ler(self) -> tuple[str, list[Mensagem]]:
        d = self.pagina.evaluate(JS_LER)
        msgs = []
        for x in d.get("msgs", []):
            rem, dia, hora = interpretar_pre(x["pre"])
            msgs.append(Mensagem(x["id"], x["minha"], x["legenda"], x["blobs"], x["carregando"], x["mais"], rem, dia, hora))
        completar_datas(msgs)
        return d.get("titulo", ""), msgs

    def baixar(self, urls: list[str]) -> list[bytes]:
        if not urls:
            return []
        saida = self.pagina.evaluate(JS_BAIXAR, urls)
        return [base64.b64decode(s) for s in saida if s]

    def baixar_album_completo(self, msg: Mensagem, esperado: int) -> list[bytes]:
        """Album com '+N': abre o visualizador na 1a foto e passa todas com a seta direita.
        Melhor esforco: devolve o que conseguiu (o chamador confere a contagem)."""
        fotos: list[bytes] = []
        try:
            seletor = f'div[data-id="{msg.id}"] img[src^="blob:"]'
            self.pagina.locator(seletor).first.click(timeout=3000)
            self.pagina.wait_for_timeout(900)
            vistos: set[str] = set()
            repetidas = 0
            for _ in range(esperado + 2):
                src = self.pagina.evaluate(JS_VISUALIZADOR)
                if src and src not in vistos:
                    vistos.add(src)
                    fotos += self.baixar([src])
                    repetidas = 0
                else:
                    repetidas += 1
                if len(fotos) >= esperado or repetidas >= 2:
                    break
                self.pagina.keyboard.press("ArrowRight")
                self.pagina.wait_for_timeout(500)
        except Exception:  # noqa: BLE001
            pass
        finally:
            try:
                self.pagina.keyboard.press("Escape")
                self.pagina.wait_for_timeout(300)
            except Exception:  # noqa: BLE001
                pass
        return fotos

    def diagnostico(self) -> str:
        """Estrutura do que o programa enxerga (sem o texto das conversas), para ajustar os seletores."""
        info = self.pagina.evaluate(r"""() => {
          const q = s => document.querySelectorAll(s).length;
          return {url: location.href, painel_lateral: q('#pane-side'), conversa_aberta: q('#main'),
                  mensagens: q('#main div[data-id]'), legendas: q('#main span.selectable-text'),
                  imagens_blob: q('#main img[src^="blob:"]'), titulos_na_lista: q('#pane-side span[title]'),
                  pre_plain_text: q('#main [data-pre-plain-text]')};
        }""")
        return "\n".join(f"{k}: {v}" for k, v in info.items())
