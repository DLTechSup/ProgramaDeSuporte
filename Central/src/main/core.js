'use strict';
/* Núcleo sem interface: marca/referência, pastas, lista, histórico, configuração.
 * Nada aqui envia mensagem ou apaga fotos/pastas do usuário. */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// ------------------------------------------------------------ configuração
const DEFAULT_CONFIG = {
  pasta_marcas: '',
  grupo: '', // grupo escolhido para monitorar
  monitorando: false, // vira true quando o usuário confirma o grupo
  baseline_pendente: false, // ao confirmar sem "incluir o que já chegou", ignora o que já está no grupo
  modo: 'fotos_antes', // ou 'texto_antes'
  sessao_dedicada: false, // segunda sessão do WhatsApp só para o monitor
  intervalo_seg: 2,
  espera_texto_seg: 120,
  album_extra: 3, // total = album_extra + N  (ponto incerto)
  pastas_ignoradas: ['nova pasta*', 'fotos variadas'],
  lista_destacada: true, // a lista fica numa janela própria, sempre na frente
  fixar_na_frente: true,
  agrupar_por_marca: true,
  marcas_recolhidas: [],
  inicio_ref: '',
  inicio_ok: false,
  geometria_lista: null,
  geometria_principal: null,
  pagina: 'demanda', // última página aberta na Central
};

function writeJson(file, obj) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = file + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(obj, null, 2), 'utf8');
  fs.renameSync(tmp, file);
}
function readJson(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return fallback; }
}

class Config {
  constructor(file) {
    this.file = file;
    this.data = { ...DEFAULT_CONFIG, ...readJson(file, {}) };
  }
  get(k) { return this.data[k] !== undefined ? this.data[k] : DEFAULT_CONFIG[k]; }
  set(k, v) { this.data[k] = v; writeJson(this.file, this.data); }
  patch(obj) { Object.assign(this.data, obj); writeJson(this.file, this.data); }
}

// --------------------------------------------------- marca e referência
const FORBIDDEN = /[<>:"/\\|?*\u0000-\u001f]/g;

function norm(s) {
  return String(s || '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()
    .replace(/['’`]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
}
function safeName(s) {
  s = String(s || '').replace(FORBIDDEN, ' ').replace(/\s+/g, ' ').trim().replace(/[. ]+$/, '');
  return s || 'sem nome';
}

// equivalente ao difflib.SequenceMatcher(...).ratio()
function lcs(a, b) {
  let best = [0, 0, 0];
  let prev = new Array(b.length + 1).fill(0);
  for (let i = 1; i <= a.length; i++) {
    const cur = new Array(b.length + 1).fill(0);
    for (let j = 1; j <= b.length; j++) {
      if (a[i - 1] === b[j - 1]) {
        cur[j] = prev[j - 1] + 1;
        if (cur[j] > best[2]) best = [i - cur[j], j - cur[j], cur[j]];
      }
    }
    prev = cur;
  }
  return best;
}
function matching(a, b) {
  if (!a.length || !b.length) return 0;
  const [i, j, k] = lcs(a, b);
  if (!k) return 0;
  return k + matching(a.slice(0, i), b.slice(0, j)) + matching(a.slice(i + k), b.slice(j + k));
}
function ratio(a, b) {
  return a.length + b.length ? (2 * matching(a, b)) / (a.length + b.length) : 1;
}

function globToRegex(g) {
  return new RegExp('^' + g.toLowerCase().replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$');
}

function listBrands(root, ignoradas) {
  ignoradas = ignoradas || DEFAULT_CONFIG.pastas_ignoradas;
  const pats = ignoradas.map(globToRegex);
  let out = [];
  try {
    for (const e of fs.readdirSync(root, { withFileTypes: true })) {
      if (!e.isDirectory()) continue;
      const n = e.name;
      if (n.startsWith('_')) continue;
      if (pats.some((r) => r.test(n.toLowerCase()))) continue;
      out.push(n);
    }
  } catch { /* pasta inexistente */ }
  return out.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
}

/** [marca|null, referencia, pontuacao] — marca = pasta de marca que aparece na legenda. */
function splitCaption(caption, brands) {
  const text = String(caption || '').replace(/\s+/g, ' ').trim();
  const words = text ? text.split(' ') : [];
  if (!words.length) return [null, '', 0];
  let best = null; // {score,n,pos,brand}
  for (const brand of brands) {
    const bn = norm(brand);
    if (!bn) continue;
    const n = bn.split(' ').length;
    for (let pos = 0; pos + n <= words.length; pos++) {
      const win = norm(words.slice(pos, pos + n).join(' '));
      if (!win) continue;
      const score = win === bn ? 1 : ratio(win, bn);
      if (score < 1 && (bn.length <= 4 || score < 0.84)) continue;
      const cand = { score, n, pos, brand };
      if (!best || score > best.score || (score === best.score && (n > best.n || (n === best.n && pos < best.pos)))) best = cand;
    }
  }
  if (!best) return [null, text, 0];
  const rest = words.slice(0, best.pos).concat(words.slice(best.pos + best.n));
  const has = (w) => /[0-9A-Za-zÀ-ÿ]/.test(w);
  while (rest.length && !has(rest[0])) rest.shift();
  while (rest.length && !has(rest[rest.length - 1])) rest.pop();
  return [best.brand, rest.join(' '), best.score];
}

function targetFolder(root, brand, ref, caption = '') {
  if (brand) return path.join(root, brand, safeName(`${brand} ${ref}`.trim()));
  return path.join(root, '_REVISAR', safeName(caption || ref || 'sem legenda'));
}

/** Pasta da referência que JÁ existe dentro da marca (ignora maiúsculas/acentos). */
function findRefFolder(root, brand, ref) {
  const wantA = norm(`${brand} ${ref}`);
  const wantB = norm(ref);
  try {
    for (const e of fs.readdirSync(path.join(root, brand), { withFileTypes: true })) {
      if (!e.isDirectory()) continue;
      const n = norm(e.name);
      if (n.startsWith('fotos novas')) continue;
      if (n === wantA || (wantB && n === wantB)) return path.join(root, brand, e.name);
    }
  } catch { /* sem pasta da marca */ }
  return null;
}

function dateLabel(d = new Date()) {
  return `${d.getDate()}-${d.getMonth() + 1}-${d.getFullYear()}`; // 6-11-2026 ("/" é proibido no Windows)
}
function newPhotosDir(refDir, d = new Date()) {
  return path.join(refDir, `fotos novas dia ${dateLabel(d)}`);
}

// ------------------------------------------------------------------ fotos
const MIN_BYTES = 3 * 1024;
const IMG_EXT = new Set(['.jpg', '.jpeg', '.png', '.webp', '.gif']);

function extOf(buf) {
  if (buf.slice(0, 3).equals(Buffer.from([0xff, 0xd8, 0xff]))) return '.jpg';
  if (buf.slice(0, 4).toString('latin1') === '\x89PNG') return '.png';
  if (buf.slice(0, 4).toString('latin1') === 'RIFF') return '.webp';
  if (buf.slice(0, 4).toString('latin1') === 'GIF8') return '.gif';
  return '.jpg';
}
function* walkImages(dir) {
  let ents = [];
  try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) yield* walkImages(p);
    else if (IMG_EXT.has(path.extname(e.name).toLowerCase())) yield p;
  }
}
const sha1 = (buf) => crypto.createHash('sha1').update(buf).digest('hex');
function countPhotos(dir) { let n = 0; for (const _ of walkImages(dir)) n++; return n; }

/**
 * Grava as fotos sem duplicar (SHA-1 contra TUDO que já existe em `dedupeRoot`) e sem apagar nada.
 * A pasta só é criada se houver ao menos uma foto nova.
 * @returns {{saved:number, dup:number}}
 */
function saveImages(folder, images, { prefix = 'foto_', dedupeRoot = folder } = {}) {
  const have = new Set();
  for (const f of walkImages(dedupeRoot)) { try { have.add(sha1(fs.readFileSync(f))); } catch { /* */ } }
  let n = 0;
  try {
    for (const e of fs.readdirSync(folder)) {
      const m = e.match(/^(?:foto_nova_|foto_)(\d+)/);
      if (m) n = Math.max(n, parseInt(m[1], 10));
    }
  } catch { /* pasta ainda não existe */ }
  let saved = 0, dup = 0;
  for (const buf of images) {
    if (!buf || buf.length < MIN_BYTES) continue;
    const h = sha1(buf);
    if (have.has(h)) { dup++; continue; }
    if (!saved) fs.mkdirSync(folder, { recursive: true });
    n++;
    fs.writeFileSync(path.join(folder, `${prefix}${String(n).padStart(2, '0')}${extOf(buf)}`), buf);
    have.add(h);
    saved++;
  }
  return { saved, dup };
}

/** Move a pasta; se o destino existe, mescla os arquivos (não sobrescreve). */
function moveFolder(src, dst) {
  if (!fs.existsSync(src) || path.resolve(src) === path.resolve(dst)) return;
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  if (!fs.existsSync(dst)) { fs.renameSync(src, dst); return; }
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const from = path.join(src, e.name);
    let to = path.join(dst, e.name);
    const ext = path.extname(e.name), stem = path.basename(e.name, ext);
    let i = 1;
    while (fs.existsSync(to)) { to = path.join(dst, `${stem}_${i}${ext}`); i++; }
    fs.renameSync(from, to);
  }
  try { fs.rmdirSync(src); } catch { /* só some se ficou vazia */ }
}

// ---------------------------------------------------------------- lista
const todayISO = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
const hhmm = () => { const d = new Date(); return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };
const isDone = (d) => !!(d.site && d.atacado);
const newId = () => crypto.randomBytes(5).toString('hex');

class Store {
  constructor(file) {
    this.file = file;
    const t = todayISO();
    // prontas de dias anteriores somem; pendentes continuam
    this.items = readJson(file, []).filter((d) => !(isDone(d) && d.date !== t));
    this.save();
  }
  save() { writeJson(this.file, this.items); }
  add(kw) {
    const d = { id: newId(), brand: '', ref: '', folder: '', saveDir: '', photos: 0, sender: '', time: hhmm(),
      date: todayISO(), site: false, atacado: false, warn: [], info: [], msg_id: '', plus: 0, ...kw };
    this.items.push(d); this.save(); return d;
  }
  get(id) { return this.items.find((d) => d.id === id) || null; }
  findOpen(brand, ref) {
    if (!brand) return null;
    return this.items.find((d) => !isDone(d) && norm(d.brand) === norm(brand) && norm(d.ref) === norm(ref)) || null;
  }
  update(id, kw) { const d = this.get(id); if (d) { Object.assign(d, kw); this.save(); } }
  remove(id) { this.items = this.items.filter((d) => d.id !== id); this.save(); }
  ordered() {
    return this.items.filter((d) => !isDone(d)).concat(this.items.filter(isDone)).map((d) => ({ ...d }));
  }
  counts() {
    const t = todayISO();
    return [this.items.filter((d) => !isDone(d)).length, this.items.filter((d) => isDone(d) && d.date === t).length];
  }
}

class History {
  constructor(file) { this.file = file; }
  add(evento, marca = '', ref = '', fotos = '', pasta = '') {
    fs.mkdirSync(path.dirname(this.file), { recursive: true });
    fs.appendFileSync(this.file, JSON.stringify({ data: todayISO(), hora: new Date().toTimeString().slice(0, 8), evento, marca, ref, fotos, pasta }) + '\n');
  }
  today() {
    try {
      return fs.readFileSync(this.file, 'utf8').split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch { return null; } })
        .filter((r) => r && r.data === todayISO()).reverse();
    } catch { return []; }
  }
}

class Seen {
  constructor(file) { this.file = file; this.ids = readJson(file, []); this.set = new Set(this.ids); }
  has(i) { return this.set.has(i); }
  add(i) {
    if (this.set.has(i)) return;
    this.set.add(i); this.ids.push(i);
    if (this.ids.length > 4000) { this.ids = this.ids.slice(-4000); this.set = new Set(this.ids); }
    writeJson(this.file, this.ids);
  }
}

// ------------------------------------------------ pesquisa e agrupamento
function matches(item, query) {
  const q = norm(query);
  if (!q) return true;
  const alvo = norm(`${item.brand || ''} ${item.ref || ''} ${item.sender || ''}`);
  return q.split(' ').every((t) => alvo.includes(t));
}
function groupByBrand(items, query = '') {
  const groups = new Map();
  for (const it of items) if (matches(it, query)) { const k = it.brand || ''; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(it); }
  const keys = [...groups.keys()].sort((a, b) => (a === '') !== (b === '') ? (a === '' ? -1 : 1) : norm(a).localeCompare(norm(b)));
  return keys.map((k) => {
    const its = groups.get(k);
    return [k || 'SEM MARCA (revisar)', its.filter((i) => !isDone(i)).concat(its.filter(isDone))];
  });
}
function captionHasRef(caption, start) {
  const a = norm(caption), b = norm(start);
  return !!b && (` ${a} `).includes(` ${b} `);
}

// ------------------------------------------------- colar demandas de fora
const BULLET = /^\s*(?:[-–—•*·▪●■□✔✅☑]|\d{1,3}[.)])\s*/u;
function parseLines(text) {
  const out = [], vistas = new Set();
  for (const raw of String(text || '').replace(/\t/g, ' ').split(/\r?\n/)) {
    let line = raw.trim();
    for (;;) { const nv = line.replace(BULLET, '').trim(); if (nv === line) break; line = nv; }
    line = line.replace(/\s+/g, ' ');
    if (line && !vistas.has(norm(line))) { vistas.add(norm(line)); out.push(line); }
  }
  return out;
}
function planPaste(text, brands, items) {
  const existentes = new Set(items.map((i) => `${norm(i.brand)}|${norm(i.ref)}`));
  return parseLines(text).map((line) => {
    const [brand, ref, score] = splitCaption(line, brands);
    const key = `${norm(brand || '')}|${norm(ref)}`;
    const status = existentes.has(key) ? 'repetida' : !brand ? 'sem_marca' : score < 1 ? 'revisar' : 'nova';
    return { line, brand, ref, status };
  });
}

function summaryText(items) {
  const d = new Date();
  const out = [`RESUMO DO DIA — ${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`, ''];
  const by = new Map();
  for (const it of items) { const k = it.brand || 'SEM MARCA'; if (!by.has(k)) by.set(k, []); by.get(k).push(it); }
  for (const b of [...by.keys()].sort((x, y) => x.toLowerCase().localeCompare(y.toLowerCase()))) {
    out.push(b);
    for (const it of by.get(b)) out.push(`  - ${it.ref || '(sem referência)'}  [${it.photos || 0} foto(s)]  Site: ${it.site ? 'OK' : '--'}  Atacado: ${it.atacado ? 'OK' : '--'}`);
    out.push('');
  }
  const done = items.filter(isDone).length;
  out.push(`Pendentes: ${items.length - done} · Prontas: ${done}`);
  return out.join('\n');
}

module.exports = {
  DEFAULT_CONFIG, Config, Store, History, Seen, norm, safeName, ratio, listBrands, splitCaption, targetFolder,
  findRefFolder, newPhotosDir, dateLabel, saveImages, countPhotos, moveFolder, matches, groupByBrand, captionHasRef,
  parseLines, planPaste, summaryText, isDone, todayISO, hhmm, writeJson, readJson,
};
