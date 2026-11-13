'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('url');
const core = require('../src/main/core');
const { Monitor } = require('../src/main/monitor');

let chromium;
try { ({ chromium } = require('playwright')); } catch { /* sem Playwright: pula */ }
const skip = !chromium && 'Playwright não instalado';
const FIXTURE = pathToFileURL(path.join(__dirname, 'fixtures', 'fake_wa.html')).href;
const GRUPO = 'PROGRAMAÇÃO ✨📷💰';

async function setup(t, cfgExtra = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mon-'));
  const root = path.join(dir, 'LANÇAMENTOS');
  for (const b of ['BEIRA RIO', 'BEBECÊ', 'DAKOTA']) fs.mkdirSync(path.join(root, b), { recursive: true });
  const cfg = new core.Config(path.join(dir, 'config.json'));
  cfg.patch({ pasta_marcas: root, grupo: GRUPO, monitorando: true, espera_texto_seg: 10, ...cfgExtra });
  const store = new core.Store(path.join(dir, 'lista.json'));
  const hist = new core.History(path.join(dir, 'h.jsonl'));
  const seen = new core.Seen(path.join(dir, 'v.json'));
  const browser = await chromium.launch();
  t.after(() => browser.close());
  const page = await browser.newPage({ viewport: { width: 1100, height: 800 } });
  await page.goto(FIXTURE);
  await page.waitForFunction('window.pronto === true');
  const mon = new Monitor({ runJs: (code) => page.evaluate(code), cfg, store, hist, seen, dedicated: !!cfgExtra.dedicated });
  mon.running = true;
  const logs = []; const status = [];
  mon.on('log', (l) => logs.push(l)); mon.on('status', (s, lv) => status.push([s, lv]));
  return { dir, root, cfg, store, seen, page, mon, logs, status };
}
const tickAll = async (mon, n = 3) => { for (let i = 0; i < n; i++) await mon.tick(); };

test('cria demandas, baixa fotos, _REVISAR e ignora "bom dia"', { skip }, async (t) => {
  const { root, store, seen, mon, status } = await setup(t);
  await tickAll(mon);
  const by = Object.fromEntries(store.items.map((d) => [`${d.brand}|${d.ref}`, d]));
  assert.ok(by['BEIRA RIO|8513.115'] && by['BEBECÊ|T3533-150'] && by['|Vizzano 99'], Object.keys(by).join());
  const a = by['BEIRA RIO|8513.115'];
  assert.equal(a.photos, 3); assert.equal(a.sender, 'Camilo'); assert.equal(a.time, '16:49');
  assert.ok(fs.existsSync(path.join(root, 'BEIRA RIO', 'BEIRA RIO 8513.115', 'foto_01.jpg')));
  assert.ok(by['BEBECÊ|T3533-150'].plus === 7 && by['BEBECÊ|T3533-150'].warn.some((w) => w.includes('+7')));
  assert.ok(by['|Vizzano 99'].warn.some((w) => w.includes('marca não reconhecida')));
  assert.ok(fs.statSync(path.join(root, '_REVISAR', 'Vizzano 99')).isDirectory());
  assert.ok(seen.has('false_1203@g.us_A2_5511@c.us'));
  assert.equal(status.at(-1)[1], 'ok');
});

test('sem confirmar o grupo nada é salvo', { skip }, async (t) => {
  const { store, mon, status } = await setup(t, { monitorando: false });
  await tickAll(mon);
  assert.equal(store.items.length, 0);
  assert.match(status.at(-1)[0], /Escolha o grupo/);
});

test('grupo diferente do escolhido: pausa e não salva', { skip }, async (t) => {
  const { store, mon, status } = await setup(t, { grupo: 'OUTRO GRUPO' });
  await tickAll(mon);
  assert.equal(store.items.length, 0);
  assert.match(status.at(-1)[0], /Pausado: abra o grupo “OUTRO GRUPO”/);
});

test('"a partir de agora": ignora o que já estava e pega só o novo', { skip }, async (t) => {
  const { store, page, mon } = await setup(t, { baseline_pendente: true });
  await tickAll(mon);
  assert.equal(store.items.length, 0);
  await page.evaluate(`msg('false_1203@g.us_B1_5533@c.us', 'Ana', '17:10', 2, 'DAKOTA 777-1', 0)`);
  await tickAll(mon);
  assert.deepEqual(store.items.map((d) => `${d.brand} ${d.ref}`), ['DAKOTA 777-1']);
});

test('referência que já existe: fotos novas vão para "fotos novas dia D-M-AAAA"', { skip }, async (t) => {
  const { root, store, page, mon } = await setup(t);
  await tickAll(mon);
  const ref = path.join(root, 'BEIRA RIO', 'BEIRA RIO 8513.115');
  assert.equal(core.countPhotos(ref), 3);
  // reenviam a mesma referência, agora com fotos diferentes (id mais longo => imagens diferentes)
  await page.evaluate(`msg('false_1203@g.us_C1XX_5511@c.us', 'Camilo', '18:00', 2, 'beira rio 8513.115', 0)`);
  await tickAll(mon);
  const nova = path.join(ref, `fotos novas dia ${core.dateLabel()}`);
  assert.deepEqual(fs.readdirSync(nova).sort(), ['foto_nova_01.jpg', 'foto_nova_02.jpg']);
  assert.equal(core.countPhotos(ref), 5);
  assert.equal(fs.readdirSync(ref).filter((f) => f.startsWith('foto_') && !f.startsWith('foto_nova')).length, 3); // originais intactas
  const item = store.items.find((d) => d.brand === 'BEIRA RIO');
  assert.equal(item.photos, 5);
  assert.ok(item.info.some((i) => i.includes('fotos novas dia')));
  assert.equal(store.items.filter((d) => d.brand === 'BEIRA RIO').length, 1); // continua um cartão só
});

test('reenvio com as MESMAS fotos não cria nada', { skip }, async (t) => {
  const { root, page, mon } = await setup(t);
  await tickAll(mon);
  const ref = path.join(root, 'BEIRA RIO', 'BEIRA RIO 8513.115');
  // mesmo tamanho de id do original (A1 -> D1) => mesmas imagens
  await page.evaluate(`msg('false_1203@g.us_D1_5511@c.us', 'Camilo', '18:05', 3, 'BEIRA RIO 8513.115', 0)`);
  await tickAll(mon);
  assert.equal(core.countPhotos(ref), 3);
  assert.equal(fs.readdirSync(ref).some((f) => f.startsWith('fotos novas')), false);
});

test('referência antiga só no disco (fora da lista) volta como pendente com fotos novas', { skip }, async (t) => {
  const { root, store, mon } = await setup(t);
  const antiga = path.join(root, 'BEBECÊ', 'Bebece T3533-150'); // caixa diferente, criada fora do programa
  fs.mkdirSync(antiga, { recursive: true });
  fs.writeFileSync(path.join(antiga, 'foto_01.jpg'), Buffer.concat([Buffer.from([0xff, 0xd8, 0xff]), Buffer.alloc(5000, 7)]));
  await tickAll(mon);
  const d = store.items.find((x) => x.brand === 'BEBECÊ');
  assert.equal(d.folder, antiga);
  assert.ok(fs.readdirSync(antiga).some((f) => f.startsWith('fotos novas dia')));
  assert.ok(!fs.existsSync(path.join(root, 'BEBECÊ', 'BEBECÊ T3533-150'))); // não criou pasta duplicada
});

test('"Estou fazendo": o que veio antes é ignorado', { skip }, async (t) => {
  const { root, store, seen, mon, cfg } = await setup(t, { inicio_ref: 'bebece T3533-150' });
  await tickAll(mon);
  assert.deepEqual(store.items.map((d) => d.brand).sort(), ['', 'BEBECÊ']);
  assert.ok(seen.has('false_1203@g.us_A1_5511@c.us'));
  assert.ok(!fs.existsSync(path.join(root, 'BEIRA RIO', 'BEIRA RIO 8513.115')));
  assert.equal(cfg.get('inicio_ok'), true);
});

test('sessão dedicada abre o álbum "+7" e salva as 10 fotos', { skip }, async (t) => {
  const { store, mon } = await setup(t, { dedicated: true });
  await tickAll(mon);
  const b = store.items.find((d) => d.brand === 'BEBECÊ');
  assert.equal(b.photos, 10);
  assert.equal(b.plus, 0);
});

test('listChats devolve os nomes da lista da esquerda', { skip }, async (t) => {
  const { mon } = await setup(t);
  assert.deepEqual(await mon.listChats(), ['PROGRAMAÇÃO']);
});
