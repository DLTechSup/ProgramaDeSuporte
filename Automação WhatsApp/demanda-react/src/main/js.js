'use strict';
/* JavaScript injetado na página do WhatsApp Web — SOMENTE LEITURA.
 * Nenhum trecho envia mensagem. Os seletores podem precisar de ajuste se o WhatsApp mudar. */

const HELPERS = `
const sleep = ms => new Promise(r => setTimeout(r, ms));
const toDataUrl = async src => {
  const r = await fetch(src); const b = await r.blob();
  return await new Promise((ok, err) => { const f = new FileReader();
    f.onload = () => ok(f.result); f.onerror = err; f.readAsDataURL(b); });
};`;

// Lê o chat aberto. Devolve JSON (string).
const SCAN = String.raw`(() => {
  const out = {ready: !!document.querySelector('#pane-side'), qr: false, open: false,
               title: '', isGroup: false, msgs: []};
  if (!out.ready) {
    out.qr = !!document.querySelector('canvas[aria-label], [data-ref], [data-testid="qrcode"]');
    return JSON.stringify(out);
  }
  const main = document.querySelector('#main');
  if (!main) return JSON.stringify(out);
  out.open = true;
  const header = main.querySelector('header');
  if (header) {
    const t = header.querySelector('span[title]') || header.querySelector('span[dir="auto"]');
    out.title = t ? ((t.getAttribute('title') || t.textContent || '') + '').trim() : '';
  }
  const nodes = [...main.querySelectorAll('div[data-id]')]
      .filter(n => !(n.parentElement && n.parentElement.closest('[data-id]')));
  let lastDate = '', lastTime = '', lastSender = '';
  for (const n of nodes) {
    const id = n.getAttribute('data-id') || '';
    if (id.indexOf('@g.us') >= 0) out.isGroup = true;
    let time = lastTime, date = lastDate, sender = lastSender;
    const pre = n.querySelector('[data-pre-plain-text]');
    if (pre) {
      const m = (pre.getAttribute('data-pre-plain-text') || '')
          .match(/^\[([^,\]]+),\s*(\d{1,2})\/(\d{1,2})\/(\d{4})\]\s*([\s\S]*?):\s*$/);
      if (m) {
        time = m[1].trim();
        date = m[4] + '-' + m[3].padStart(2, '0') + '-' + m[2].padStart(2, '0');
        sender = m[5].trim();
      }
    }
    lastTime = time; lastDate = date; lastSender = sender;
    if (!sender) { const mm = id.match(/_(\d+)@c\.us$/); sender = mm ? mm[1] : ''; }
    const caps = [...n.querySelectorAll('span.selectable-text')]
        .filter(s => !(s.parentElement && s.parentElement.closest('span.selectable-text')));
    const caption = caps.map(s => (s.innerText || '').trim()).filter(Boolean).join('\n');
    let plusEl = null, plus = 0;
    for (const e of n.querySelectorAll('div,span')) {
      if (e.children.length === 0 && /^\+\d+$/.test((e.textContent || '').trim())) {
        plusEl = e; plus = parseInt(e.textContent.trim().slice(1), 10); break;
      }
    }
    let tileImg = null;
    if (plusEl) {
      let p = plusEl.parentElement;
      while (p && p !== n) { const im = p.querySelector('img[src^="blob:"]'); if (im) { tileImg = im; break; } p = p.parentElement; }
    }
    const photos = []; let thumbs = 0; const seen = new Set();
    for (const im of n.querySelectorAll('img')) {
      if (im.hasAttribute('data-plain-text') || im.classList.contains('emoji')) continue;
      const src = im.getAttribute('src') || '';
      const w = im.getBoundingClientRect().width;
      if (src.startsWith('blob:')) {
        if (w < 60 || seen.has(src)) continue;
        seen.add(src); photos.push({src: src, tile: im === tileImg});
      } else if (src.startsWith('data:image/jpeg') && w >= 60) { thumbs++; }
    }
    out.msgs.push({id: id, outgoing: id.startsWith('true_'), sender: sender, date: date, time: time,
                   caption: caption, photos: photos, thumbs: thumbs, plus: plus});
  }
  return JSON.stringify(out);
})()`;

// Nomes das conversas visíveis na lista da esquerda (para escolher o grupo).
const LIST_CHATS = String.raw`(() => {
  const side = document.querySelector('#pane-side');
  if (!side) return JSON.stringify([]);
  const out = [], seen = new Set();
  const rows = side.querySelectorAll('[role="listitem"], [role="row"]');
  const els = rows.length ? [...rows].map(r => r.querySelector('span[title]')) : [...side.querySelectorAll('span[title]')];
  for (const s of els) {
    const t = s ? (s.getAttribute('title') || '').trim() : '';
    if (t && !seen.has(t)) { seen.add(t); out.push(t); }
  }
  return JSON.stringify(out);
})()`;

const openChat = (name) => `(() => {
  const name = ${JSON.stringify(name)};
  const side = document.querySelector('#pane-side'); if (!side) return false;
  const norm = s => (s || '').trim().toLowerCase();
  for (const s of side.querySelectorAll('span[title]')) {
    if (norm(s.getAttribute('title')) === norm(name)) {
      const row = s.closest('[role="listitem"], [role="row"]') || s.parentElement;
      for (const t of ['mousedown', 'mouseup', 'click'])
        row.dispatchEvent(new MouseEvent(t, {bubbles: true, cancelable: true}));
      return true;
    }
  }
  return false;
})()`;

// Baixa blobs já carregados na conversa (sem mexer na tela).
const fetchPhotos = (srcs) => `(async () => { ${HELPERS}
  const srcs = ${JSON.stringify(srcs)}; const res = [];
  for (const s of srcs) { try { res.push(await toDataUrl(s)); } catch (e) { res.push(null); } }
  return res;
})()`;

// Abre o álbum clicando no "+N", captura a foto grande e avança com a seta.
const walkAlbum = (msgId, count) => `(async () => { ${HELPERS}
  const msgId = ${JSON.stringify(msgId)}; const count = ${Number(count)};
  const n = [...document.querySelectorAll('#main div[data-id]')].find(x => x.getAttribute('data-id') === msgId);
  if (!n) throw new Error('mensagem não encontrada');
  let tile = null;
  for (const e of n.querySelectorAll('div,span')) {
    if (e.children.length === 0 && /^\\+\\d+$/.test((e.textContent || '').trim())) { tile = e; break; }
  }
  if (!tile) throw new Error('tile +N não encontrado');
  const main = document.querySelector('#main');
  const big = () => { let best = null, area = 0;
    for (const im of document.querySelectorAll('img[src^="blob:"]')) {
      if (main.contains(im)) continue;
      const r = im.getBoundingClientRect(), a = r.width * r.height;
      if (a > area) { area = a; best = im; } }
    return best; };
  const key = (name, code) => { const ev = new KeyboardEvent('keydown',
    {key: name, code: name, keyCode: code, which: code, bubbles: true});
    (document.activeElement || document.body).dispatchEvent(ev); document.dispatchEvent(ev); };
  tile.click();
  await sleep(1300);
  const out = []; let prev = '';
  for (let i = 0; i < count; i++) {
    let im = null;
    for (let t = 0; t < 30; t++) { im = big(); if (im && im.src !== prev) break; await sleep(200); }
    if (!im || im.src === prev) break;
    out.push(await toDataUrl(im.src)); prev = im.src;
    if (i < count - 1) {
      const nx = document.querySelector('[data-icon*="chevron-right"]');
      if (nx) (nx.closest('button,[role="button"]') || nx.querySelector('button') || nx).click();
      else key('ArrowRight', 39);
      await sleep(500);
    }
  }
  key('Escape', 27);
  return out;
})()`;

module.exports = { SCAN, LIST_CHATS, openChat, fetchPhotos, walkAlbum };
