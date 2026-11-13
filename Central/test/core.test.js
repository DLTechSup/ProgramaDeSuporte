'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const core = require('../src/main/core');

const BRANDS = ['ACTVITTA', 'BEBECÊ', 'BEIRA RIO', 'DAKOTA', "Maria's Shoes", 'MOLECA'];
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'demanda-'));
const img = (c) => Buffer.concat([Buffer.from([0xff, 0xd8, 0xff]), Buffer.alloc(5000, c)]);

test('legendas do plano: marca + referência', () => {
  const casos = [
    ['BEIRA RIO 8513.115', 'BEIRA RIO', '8513.115'],
    ['BEBECE T3533-150', 'BEBECÊ', 'T3533-150'],
    ['dakota rosa Choque', 'DAKOTA', 'rosa Choque'],
    ['Moleca - AB_12/x', 'MOLECA', 'AB_12/x'],
    ['Marias Shoes Salto Fino', "Maria's Shoes", 'Salto Fino'],
    ['Dakotta 777-1', 'DAKOTA', '777-1'],
    ['BEIRA RIO\n8562.213', 'BEIRA RIO', '8562.213'],
  ];
  for (const [leg, marca, ref] of casos) {
    const [b, r] = core.splitCaption(leg, BRANDS);
    assert.deepEqual([b, r], [marca, ref], leg);
  }
});

test('marca desconhecida', () => {
  const [b, r] = core.splitCaption('Vizzano 1234', BRANDS);
  assert.equal(b, null); assert.equal(r, 'Vizzano 1234');
});

test('pastas do plano', () => {
  const root = tmp();
  assert.equal(core.targetFolder(root, 'BEIRA RIO', '8513.115'), path.join(root, 'BEIRA RIO', 'BEIRA RIO 8513.115'));
  assert.equal(core.targetFolder(root, 'MOLECA', 'AB_12/x'), path.join(root, 'MOLECA', 'MOLECA AB_12 x'));
  assert.ok(core.targetFolder(root, null, '').includes('_REVISAR'));
});

test('listBrands ignora Nova pasta, _ e arquivos', () => {
  const root = tmp();
  for (const n of ['BEIRA RIO', 'Nova pasta', 'Nova pasta (2)', '_REVISAR', 'FOTOS variadas', 'DAKOTA']) fs.mkdirSync(path.join(root, n));
  fs.writeFileSync(path.join(root, 'a.txt'), 'x');
  assert.deepEqual(core.listBrands(root), ['BEIRA RIO', 'DAKOTA']);
});

test('referência que já existe é achada mesmo com caixa/acentos diferentes', () => {
  const root = tmp();
  fs.mkdirSync(path.join(root, 'BEBECÊ', 'Bebece T3533-150'), { recursive: true });
  fs.mkdirSync(path.join(root, 'BEBECÊ', 'fotos novas dia 1-1-2026 sem nada'), { recursive: true });
  assert.equal(core.findRefFolder(root, 'BEBECÊ', 'T3533-150'), path.join(root, 'BEBECÊ', 'Bebece T3533-150'));
  assert.equal(core.findRefFolder(root, 'BEBECÊ', 'OUTRA'), null);
});

test('pasta "fotos novas dia" usa a data sem barra', () => {
  assert.equal(path.basename(core.newPhotosDir('/x/y', new Date(2026, 10, 6))), 'fotos novas dia 6-11-2026');
});

test('saveImages não duplica nem apaga e continua a numeração', () => {
  const f = path.join(tmp(), 'p');
  assert.deepEqual(core.saveImages(f, [img(1), img(2), Buffer.from('x')]), { saved: 2, dup: 0 });
  assert.deepEqual(core.saveImages(f, [img(1), img(2)]), { saved: 0, dup: 2 });
  assert.deepEqual(fs.readdirSync(f).sort(), ['foto_01.jpg', 'foto_02.jpg']);
  core.saveImages(f, [img(3)]);
  assert.ok(fs.existsSync(path.join(f, 'foto_03.jpg')));
});

test('fotos novas: só cria a pasta se houver foto nova e compara com a pasta inteira', () => {
  const root = tmp();
  const ref = path.join(root, 'REF');
  core.saveImages(ref, [img(1), img(2)]);
  const nova = core.newPhotosDir(ref, new Date(2026, 10, 6));
  // só repetidas: nada é criado
  assert.deepEqual(core.saveImages(nova, [img(1), img(2)], { prefix: 'foto_nova_', dedupeRoot: ref }), { saved: 0, dup: 2 });
  assert.equal(fs.existsSync(nova), false);
  // uma repetida e uma nova: só a nova entra
  assert.deepEqual(core.saveImages(nova, [img(1), img(9)], { prefix: 'foto_nova_', dedupeRoot: ref }), { saved: 1, dup: 1 });
  assert.deepEqual(fs.readdirSync(nova), ['foto_nova_01.jpg']);
  assert.equal(core.countPhotos(ref), 3); // conta a pasta e as subpastas
});

test('moveFolder mescla sem sobrescrever', () => {
  const root = tmp(); const s = path.join(root, 's'), d = path.join(root, 'd');
  fs.mkdirSync(s); fs.mkdirSync(d);
  fs.writeFileSync(path.join(s, 'foto_01.jpg'), 'novo'); fs.writeFileSync(path.join(d, 'foto_01.jpg'), 'antigo');
  core.moveFolder(s, d);
  assert.equal(fs.readFileSync(path.join(d, 'foto_01.jpg'), 'utf8'), 'antigo');
  assert.equal(fs.readFileSync(path.join(d, 'foto_01_1.jpg'), 'utf8'), 'novo');
  assert.equal(fs.existsSync(s), false);
});

test('Store: ordem, prontas, dia seguinte', () => {
  const file = path.join(tmp(), 'l.json');
  const st = new core.Store(file);
  const a = st.add({ brand: 'X', ref: '1' }); const b = st.add({ brand: 'X', ref: '2' });
  st.update(a.id, { site: true, atacado: true });
  assert.deepEqual(st.ordered().map((d) => d.ref), ['2', '1']);
  assert.deepEqual(st.counts(), [1, 1]);
  assert.equal(st.findOpen('x', '2').id, b.id);
  assert.equal(st.findOpen('x', '1'), null);
  st.update(a.id, { date: '2000-01-01' });
  assert.deepEqual(new core.Store(file).items.map((d) => d.ref), ['2']);
});

test('pesquisa e agrupamento por marca', () => {
  const its = [
    { brand: 'DAKOTA', ref: '777-1', sender: 'Ana' },
    { brand: 'BEIRA RIO', ref: '8513.115', sender: 'Camilo', site: true, atacado: true },
    { brand: 'BEIRA RIO', ref: '8562.213', sender: 'Camilo' },
    { brand: '', ref: 'Vizzano 9', sender: 'Ana' },
  ];
  const g = core.groupByBrand(its);
  assert.deepEqual(g.map((x) => x[0]), ['SEM MARCA (revisar)', 'BEIRA RIO', 'DAKOTA']);
  assert.deepEqual(g[1][1].map((i) => i.ref), ['8562.213', '8513.115']);
  assert.deepEqual(core.groupByBrand(its, 'beira 8562').map((x) => x[0]), ['BEIRA RIO']);
  assert.deepEqual(core.groupByBrand(its, 'xyz'), []);
});

test('captionHasRef', () => {
  assert.ok(core.captionHasRef('BEIRA RIO 8513.115', '8513.115'));
  assert.ok(core.captionHasRef('bebece T3533-150', 'BEBECÊ t3533-150'));
  assert.ok(!core.captionHasRef('BEIRA RIO 8513.1155', '8513.115'));
  assert.ok(!core.captionHasRef('qualquer', ''));
});

test('colar demandas: marcadores, repetidas e status', () => {
  assert.deepEqual(core.parseLines('1. BEIRA RIO 8513.115\n- Dakota 777-1\n• BEBECE T3533-150\n\n  beira   rio 8513.115 \n✅ Moleca AB1'),
    ['BEIRA RIO 8513.115', 'Dakota 777-1', 'BEBECE T3533-150', 'Moleca AB1']);
  const r = core.planPaste('BEIRA RIO 8513.115\nDakotta 7\nVizzano 9\nMOLECA AB1', BRANDS, [{ brand: 'BEIRA RIO', ref: '8513.115' }]);
  assert.deepEqual(r.map((x) => x.status), ['repetida', 'revisar', 'sem_marca', 'nova']);
});
