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
from .marcas import compactar

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

# Acha a area de rolagem das mensagens (o elemento rolavel que contem as mensagens)
_JS_ROLAVEL = r"""
const achar = () => {
  const m = document.querySelector('#main'); if (!m) return null;
  const el = m.querySelector('div[data-id]'); if (!el) return null;
  let p = el.parentElement;
  while (p && p !== document.body) {
    const st = getComputedStyle(p);
    if ((st.overflowY === 'auto' || st.overflowY === 'scroll') && p.scrollHeight > p.clientHeight + 4) return p;
    p = p.parentElement;
  }
  return null;
};
"""

JS_ROLAR_TOPO = "() => {" + _JS_ROLAVEL + r"""
  const m = document.querySelector('#main'); const r = achar(); if (r) r.scrollTop = 0;
  const pre = m ? m.querySelector('[data-pre-plain-text]') : null;
  return {n: m ? m.querySelectorAll('div[data-id]').length : 0, pre: pre ? pre.getAttribute('data-pre-plain-text') : '', rolavel: !!r};
}"""

JS_ROLAR_PASSO = "() => {" + _JS_ROLAVEL + r"""
  const r = achar(); if (!r) return false;
  if (r.scrollTop + r.clientHeight >= r.scrollHeight - 6) return false;
  r.scrollTop = r.scrollTop + r.clientHeight * 0.8; return true;
}"""

JS_ROLAR_FIM = "() => {" + _JS_ROLAVEL + r"""
  const r = achar(); if (r) r.scrollTop = r.scrollHeight; return !!r;
}"""

JS_CONVERSAS = r"""
() => {
  const out = []; const add = t => { t = (t || '').trim(); if (t && !out.includes(t)) out.push(t); };
  document.querySelectorAll('#pane-side [title]').forEach(e => add(e.getAttribute('title')));
  if (out.length < 3) {   // se a tela nao usa o atributo title, pega a primeira linha de cada conversa da lista
    document.querySelectorAll('#pane-side [role="row"], #pane-side [role="listitem"], #pane-side [role="gridcell"]')
      .forEach(e => add(((e.innerText || '').split('\n').map(x => x.trim()).filter(Boolean))[0]));
  }
  return out;
}
"""

JS_TITULO_ABERTO = r"""
() => {
  const h = document.querySelector('#main header'); if (!h) return '';
  const t = h.querySelector('[title]');
  if (t && (t.getAttribute('title') || '').trim()) return t.getAttribute('title').trim();
  return ((h.innerText || '').split('\n').map(x => x.trim()).filter(Boolean))[0] || '';
}
"""

JS_CLICAR_CONVERSA = r"""
(nome) => {
  const alvo = [...document.querySelectorAll('#pane-side [title], #pane-side span, #pane-side div[dir="auto"]')]
    .find(e => ((e.getAttribute('title') || e.innerText || '').trim()) === nome);
  if (!alvo) return false;
  const linha = alvo.closest('[role="row"], [role="listitem"], [tabindex]') || alvo;
  for (const tipo of ['mousedown', 'mouseup', 'click']) linha.dispatchEvent(new MouseEvent(tipo, {bubbles: true, cancelable: true}));
  return true;
}
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
        """Abre o grupo pela lista lateral (ou pela busca). So clica; nao digita mensagem.
        O nome vale igual ao do WhatsApp OU sem emojis, acentos e maiusculas (ex.: 'programacao' acha 'PROGRAMAÇÃO ✨📷💰')."""
        if self._mesmo_nome(self._titulo_aberto(), nome):
            return True
        real = self._titulo_equivalente(nome)
        clicou = False
        if real is not None:
            clicou = self._clicar(real)
        if not clicou and not self._abrir_pela_busca(nome):
            return False
        fim = time.time() + 5
        while time.time() < fim:
            if self._mesmo_nome(self._titulo_aberto(), nome):
                self.pagina.wait_for_timeout(500)
                return True
            self.pagina.wait_for_timeout(200)
        return False

    def _clicar(self, titulo: str) -> bool:
        """Clica na conversa da lista lateral por tres caminhos (o WhatsApp muda a tela de tempos em tempos)."""
        try:
            self.pagina.locator("#pane-side").get_by_title(titulo, exact=True).first.click(timeout=2500)
            return True
        except Exception:  # noqa: BLE001
            pass
        try:
            self.pagina.locator("#pane-side").get_by_text(titulo, exact=True).first.click(timeout=2500)
            return True
        except Exception:  # noqa: BLE001
            pass
        try:
            return bool(self.pagina.evaluate(JS_CLICAR_CONVERSA, titulo))
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    def _mesmo_nome(a: str, b: str) -> bool:
        return bool(compactar(a)) and compactar(a) == compactar(b)

    def _titulo_equivalente(self, nome: str) -> str | None:
        try:
            for t in self.conversas():
                if self._mesmo_nome(t, nome):
                    return t
        except Exception:  # noqa: BLE001
            pass
        return None

    def _titulo_aberto(self) -> str:
        try:
            return self.pagina.evaluate(JS_TITULO_ABERTO)
        except Exception:  # noqa: BLE001
            return ""

    def _abrir_pela_busca(self, nome: str) -> bool:
        try:
            caixa = None
            for seletor in ('#side div[contenteditable="true"]', 'div[contenteditable="true"][data-tab="3"]',
                            'div[role="textbox"][contenteditable="true"]:not(#main *)', 'input[type="text"]'):
                cand = self.pagina.locator(seletor).first
                if cand.count():
                    caixa = cand
                    break
            if caixa is None:
                return False
            caixa.click(timeout=2000)
            caixa.fill(nome)
            self.pagina.wait_for_timeout(1500)
            real = self._titulo_equivalente(nome)
            return real is not None and self._clicar(real)
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

    def rolar_para_o_inicio_do_dia(self, hoje: date, max_voltas: int = 60) -> int:
        """Sobe a conversa ate aparecer uma mensagem de antes de hoje (ou nao carregar mais nada). So rola; nao envia nada."""
        parados, ultimo = 0, -1
        for volta in range(max_voltas):
            r = self.pagina.evaluate(JS_ROLAR_TOPO)
            self.pagina.wait_for_timeout(900)
            _, dia, _ = interpretar_pre(r.get("pre", ""))
            if dia and dia < hoje:
                return volta + 1
            if not r.get("rolavel"):
                return volta + 1
            n = self.pagina.evaluate("() => document.querySelectorAll('#main div[data-id]').length")
            parados = parados + 1 if n == ultimo else 0
            ultimo = n
            if parados >= 2:                       # nao carrega mais nada: chegou no comeco da conversa
                return volta + 1
        return max_voltas

    def rolar_um_passo(self) -> bool:
        """Desce uma tela. False quando chegou ao fim (ou nao ha rolagem)."""
        ok = bool(self.pagina.evaluate(JS_ROLAR_PASSO))
        self.pagina.wait_for_timeout(900)          # da tempo de as fotos da tela carregarem
        return ok

    def rolar_para_o_fim(self) -> None:
        self.pagina.evaluate(JS_ROLAR_FIM)
        self.pagina.wait_for_timeout(400)

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

    def resumo_conversas(self, limite: int = 8) -> str:
        """Texto curto para o registro: o que o programa enxerga na lista lateral."""
        try:
            nomes = self.conversas()
        except Exception:  # noqa: BLE001
            return "não consegui ler a lista de conversas"
        if not nomes:
            return "a lista de conversas aparece VAZIA para o programa"
        extra = f" (+{len(nomes) - limite} outras)" if len(nomes) > limite else ""
        return "vejo " + ", ".join(nomes[:limite]) + extra

    def diagnostico(self) -> str:
        """Estrutura do que o programa enxerga (sem o texto das conversas), para ajustar os seletores."""
        info = self.pagina.evaluate(r"""() => {
          const q = s => document.querySelectorAll(s).length;
          return {url: location.href, painel_lateral: q('#pane-side'), conversa_aberta: q('#main'),
                  mensagens: q('#main div[data-id]'), legendas: q('#main span.selectable-text'),
                  imagens_blob: q('#main img[src^="blob:"]'), titulos_na_lista: q('#pane-side span[title]'),
                  pre_plain_text: q('#main [data-pre-plain-text]')};
        }""")
        info["conversas_que_o_programa_ve"] = len(self.conversas())
        info["conversa_aberta_titulo"] = self._titulo_aberto() or "(nenhuma)"
        return "\n".join(f"{k}: {v}" for k, v in info.items()) + "\nprimeiras conversas: " + self.resumo_conversas(12)
