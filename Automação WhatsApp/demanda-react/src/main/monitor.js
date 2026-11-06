'use strict';
/* Monitor: lê o chat aberto do grupo escolhido e cria as demandas.
 * SOMENTE LEITURA — só executa JavaScript que lê a página. Nunca envia mensagem. */
const fs = require('fs');
const path = require('path');
const EventEmitter = require('events');
const core = require('./core');
const js = require('./js');

const decode = (dataUrl) => {
  if (!dataUrl || !dataUrl.includes(',')) return null;
  try { return Buffer.from(dataUrl.split(',')[1], 'base64'); } catch { return null; }
};
const sameChat = (title, grupo) => {
  const a = core.norm(title), b = core.norm(grupo);
  return !!a && !!b && (a === b || a.includes(b) || b.includes(a));
};

class Monitor extends EventEmitter {
  /** runJs(code) => Promise<any>: executa o código na página do WhatsApp. */
  constructor({ runJs, cfg, store, hist, seen, dedicated = false }) {
    super();
    Object.assign(this, { runJs, cfg, store, hist, seen, dedicated });
    this.busy = false; this.running = false; this.timer = null;
    this.pending = new Map(); // remetente -> {images, msg, since}
    this.current = new Map(); // remetente -> [marca, ref]  (modo texto_antes)
    this.waits = new Map();
  }

  start() {
    this.running = true;
    const ms = Math.max(500, Number(this.cfg.get('intervalo_seg')) * 1000);
    this.timer = setInterval(() => this.tick(), ms);
    this.emit('log', 'Monitor iniciado.');
  }
  stop() { this.running = false; clearInterval(this.timer); this.timer = null; }

  status(text, level) { this.emit('status', text, level); }
  log(text) { this.emit('log', text); }

  async listChats() {
    try { return JSON.parse(await this.runJs(js.LIST_CHATS)); } catch { return []; }
  }
  async openChat(name) {
    try { return !!(await this.runJs(js.openChat(name))); } catch { return false; }
  }

  async tick() {
    if (this.busy || !this.running) return;
    this.busy = true;
    try {
      await this.flushPending();
      const grupo = this.cfg.get('grupo');
      if (!this.cfg.get('monitorando') || !grupo) {
        this.status('Escolha o grupo e clique em “Confirmar” para começar.', 'wait');
        return;
      }
      if (this.dedicated) await this.openChat(grupo);
      let res = null;
      try { res = JSON.parse(await this.runJs(js.SCAN)); } catch { res = null; }
      if (!res) { this.status('Aguardando o WhatsApp carregar...', 'wait'); return; }
      if (!res.ready) { this.status(res.qr ? 'Escaneie o QR code com o celular...' : 'Aguardando o WhatsApp carregar...', 'wait'); return; }
      if (!res.open || !sameChat(res.title, grupo)) {
        this.status(`Pausado: abra o grupo “${grupo}”${res.open ? ` (agora está em “${res.title}”)` : ''}.`, 'wait');
        return;
      }
      const root = this.cfg.get('pasta_marcas');
      if (!root || !fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
        this.status('Escolha a pasta das marcas (⚙ Configurações).', 'err'); return;
      }
      let msgs = res.msgs;
      if (this.cfg.get('baseline_pendente')) {
        for (const m of msgs) this.seen.add(m.id); // não inclui o que já estava no grupo
        this.cfg.set('baseline_pendente', false);
        this.log(`Monitorando “${grupo}” a partir de agora (${msgs.length} mensagem(ns) anteriores ignoradas).`);
        msgs = [];
      }
      const inicio = String(this.cfg.get('inicio_ref') || '').trim();
      if (inicio && !this.cfg.get('inicio_ok')) {
        let idx = msgs.findIndex((m) => m.caption && core.captionHasRef(m.caption, inicio));
        if (idx < 0) { this.status(`Aguardando “${inicio}” aparecer no grupo...`, 'wait'); return; }
        const prev = idx > 0 ? msgs[idx - 1] : null;
        if (prev && prev.photos.length && !prev.caption && !msgs[idx].photos.length && prev.sender === msgs[idx].sender) idx -= 1;
        for (const m of msgs.slice(0, idx)) this.seen.add(m.id);
        this.cfg.set('inicio_ok', true);
        this.log(`Ponto de partida encontrado: ${inicio}`);
        msgs = msgs.slice(idx);
      }
      this.status(`Monitorando: ${res.title}`, 'ok');
      const hoje = core.todayISO();
      const fila = [];
      for (const m of msgs) {
        if (this.seen.has(m.id)) continue;
        if (m.date && m.date !== hoje) { this.seen.add(m.id); continue; }
        fila.push(m);
      }
      for (const m of fila) {
        if (m.thumbs > 0 && (this.waits.get(m.id) || 0) < 10) { this.waits.set(m.id, (this.waits.get(m.id) || 0) + 1); break; } // espera as fotos carregarem, mantendo a ordem
        if (!m.photos.length && !m.caption.trim()) { this.seen.add(m.id); continue; }
        const images = await this.fetchImages(m);
        try { await this.apply(m, images); } catch (e) { this.log(`Erro ao processar mensagem: ${e.message}`); }
        this.seen.add(m.id);
        this.emit('changed');
      }
    } catch (e) {
      this.log(`Erro no monitor: ${e.message}`);
    } finally { this.busy = false; }
  }

  async fetchImages(m) {
    const useWalk = this.dedicated && m.plus > 0;
    const urls = m.photos.filter((p) => !(useWalk && p.tile)).map((p) => p.src);
    let imgs = [];
    if (urls.length) {
      try { imgs = (await this.runJs(js.fetchPhotos(urls))).map(decode).filter(Boolean); } catch (e) { this.log(`Falha ao baixar fotos: ${e.message}`); }
    }
    if (useWalk) imgs = imgs.concat(await this.walk(m.id, m.plus, m.photos.filter((p) => !p.tile).length));
    return imgs;
  }
  async walk(msgId, plus, visible) {
    const count = Math.max(1, Number(this.cfg.get('album_extra')) + plus - visible);
    try { return (await this.runJs(js.walkAlbum(msgId, count))).map(decode).filter(Boolean); } catch (e) { this.log(`Álbum +${plus}: ${e.message}`); return []; }
  }

  /** Botão do cartão: abre o álbum e pega as fotos escondidas (ação do usuário). */
  async completeAlbum(did) {
    const d = this.store.get(did);
    if (!d || !d.msg_id || !d.plus) return;
    const imgs = await this.walk(d.msg_id, d.plus, 3);
    const dir = d.saveDir || d.folder;
    const nova = path.resolve(dir) !== path.resolve(d.folder);
    const r = core.saveImages(dir, imgs, { prefix: nova ? 'foto_nova_' : 'foto_', dedupeRoot: d.folder });
    this.store.update(did, { photos: core.countPhotos(d.folder), warn: d.warn.filter((w) => !w.includes('+')), plus: 0 });
    this.hist.add('Fotos adicionadas', d.brand, d.ref, r.saved, dir);
    this.log(`Álbum completado: ${r.saved} foto(s) nova(s).`);
    this.emit('changed');
  }

  // ------------------------------------------------------ regras do plano
  async apply(m, images) {
    const cap = m.caption.trim(), who = m.sender;
    const brands = core.listBrands(this.cfg.get('pasta_marcas'), this.cfg.get('pastas_ignoradas'));
    if (images.length && cap) return this.make(m, cap, images, brands);
    if (images.length) {
      const cur = this.cfg.get('modo') === 'texto_antes' ? this.current.get(who) : null;
      if (cur) return this.make(m, `${cur[0]} ${cur[1]}`.trim(), images, brands);
      const p = this.pending.get(who) || { images: [], msg: m, since: Date.now() };
      p.images = p.images.concat(images); this.pending.set(who, p);
      return undefined;
    }
    if (cap) {
      const p = this.pending.get(who);
      if (p) { this.pending.delete(who); return this.make(p.msg, cap, p.images, brands); }
      if (this.cfg.get('modo') === 'texto_antes') {
        const [brand, ref] = core.splitCaption(cap, brands);
        if (brand) this.current.set(who, [brand, ref]);
      }
    }
    return undefined;
  }

  async flushPending() {
    const limite = Number(this.cfg.get('espera_texto_seg')) * 1000;
    for (const [who, p] of [...this.pending]) {
      if (Date.now() - p.since < limite) continue;
      this.pending.delete(who);
      const brands = core.listBrands(this.cfg.get('pasta_marcas'), this.cfg.get('pastas_ignoradas'));
      const nome = `sem referencia ${String(p.msg.time || '').replace(':', 'h')} ${who}`.trim();
      try { this.make(p.msg, nome, p.images, brands, { forceReview: true }); } catch (e) { this.log(`Erro: ${e.message}`); }
      this.emit('changed');
    }
  }

  /** Cria a demanda (ou guarda em "fotos novas" se a referência já existe na pasta). */
  make(m, caption, images, brands, { forceReview = false } = {}) {
    const root = this.cfg.get('pasta_marcas');
    const [brand, ref, score] = forceReview ? [null, caption, 0] : core.splitCaption(caption, brands);
    const warn = [], info = [];
    if (forceReview) warn.push('⚠ sem referência: revisar marca e referência');
    else if (!brand) warn.push('⚠ marca não reconhecida');
    else if (score < 1) warn.push('⚠ revisar marca e referência');
    const plus = this.dedicated && m.plus ? 0 : m.plus;
    if (plus) warn.push(`⚠ álbum com +${plus}: faltam fotos (use “Pegar fotos restantes”)`);

    const refDir = brand ? core.findRefFolder(root, brand, ref) : null;
    if (refDir) {
      // A referência JÁ existe na pasta da marca: as fotos vão para "fotos novas dia D-M-AAAA".
      const nova = core.newPhotosDir(refDir);
      const r = core.saveImages(nova, images, { prefix: 'foto_nova_', dedupeRoot: refDir });
      if (!r.saved) { this.log(`${brand} ${ref}: reenviada, mas as fotos já existiam. Nada novo.`); return; }
      info.push(`ℹ referência já existia: ${r.saved} foto(s) nova(s) em “${path.basename(nova)}”` + (r.dup ? ` (${r.dup} repetida(s) ignorada(s))` : ''));
      const total = core.countPhotos(refDir);
      const open = this.store.findOpen(brand, ref);
      if (open) {
        this.store.update(open.id, { photos: total, info: open.info.concat(info), saveDir: nova });
        this.hist.add('Fotos novas (referência já existia)', brand, ref, r.saved, nova);
        this.log(`+${r.saved} foto(s) nova(s) em ${brand} ${ref}`);
        return;
      }
      this.store.add({ brand, ref, folder: refDir, saveDir: nova, photos: total, sender: m.sender, time: m.time || core.hhmm(), warn, info, msg_id: m.id, plus });
      this.hist.add('Fotos novas (referência já existia)', brand, ref, r.saved, nova);
      this.log(`Referência já existia: ${brand} ${ref} → ${r.saved} foto(s) em ${path.basename(nova)}`);
      return;
    }

    const folder = core.targetFolder(root, brand, ref, caption);
    const existed = fs.existsSync(folder);
    if (existed) warn.push('⚠ pasta já existia');
    const r = core.saveImages(folder, images);
    fs.mkdirSync(folder, { recursive: true });
    const total = core.countPhotos(folder);
    if (total === 0) warn.push('⚠ sem fotos');
    const open = this.store.findOpen(brand, ref);
    if (open) { // mesma demanda já na lista (ex.: pasta renomeada): só acrescenta
      this.store.update(open.id, { photos: total });
      this.hist.add('Fotos adicionadas', brand, ref, r.saved, folder);
      return;
    }
    this.store.add({ brand: brand || '', ref, folder, saveDir: folder, photos: total, sender: m.sender, time: m.time || core.hhmm(), warn, info, msg_id: m.id, plus });
    this.hist.add('Demanda criada', brand || '(sem marca)', ref, total, folder);
    this.log(`Demanda criada: ${brand || '?'} ${ref} (${total} foto(s))`);
  }
}

module.exports = { Monitor, sameChat };
