'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const tools = require('../src/main/tools');

const mk = () => fs.mkdtempSync(path.join(os.tmpdir(), 'ferr-'));
const put = (base, id, name) => { fs.mkdirSync(path.join(base, id), { recursive: true }); fs.writeFileSync(path.join(base, id, name), 'x'); };

test('sem ferramentas: tudo aparece como não incluído', () => {
  const r = tools.list(mk());
  assert.equal(r.tools.length, 10);
  assert.ok(r.tools.every((t) => !t.incluido));
  assert.deepEqual(r.pendentes.map((p) => p.nome), ['Grade Fácil', 'Note Deck']);
});

test('acha o programa pelo nome exato ou pelo padrão (instalador/portátil)', () => {
  const base = mk();
  put(base, 'renomeador', 'RenomeadorEmMassa.exe');
  put(base, 'editor-fotos', 'EditorFotos-3.0.0-Portatil.exe');
  put(base, 'suporte-tecnico', 'SuporteInformax-tecnico-instalador.exe');
  put(base, 'suporte-tecnico', 'outro.txt');
  put(base, 'captura-tela', 'LEIA-ME.txt'); // sem o .exe esperado
  const inc = Object.fromEntries(tools.list(base).tools.map((t) => [t.id, t.incluido]));
  assert.equal(inc['renomeador'], true);
  assert.equal(inc['editor-fotos'], true);
  assert.equal(inc['suporte-tecnico'], true);
  assert.equal(inc['captura-tela'], false);
  assert.equal(inc['nomes-calcados'], false);
});

test('a lista não leva regex pela ponte (só dados simples)', () => {
  const r = tools.list(mk());
  JSON.stringify(r); // não pode lançar
  assert.ok(r.tools.every((t) => t.pattern === undefined && t.exe === undefined));
});

test('abrir usa o openPath do sistema e avisa quando não está incluída', async () => {
  const base = mk();
  put(base, 'renomeador', 'RenomeadorEmMassa.exe');
  const abertos = [];
  assert.deepEqual(await tools.open(base, 'renomeador', async (p) => { abertos.push(p); return ''; }), { ok: true });
  assert.equal(path.basename(abertos[0]), 'RenomeadorEmMassa.exe');
  assert.equal((await tools.open(base, 'captura-tela', async () => '')).ok, false);
  assert.equal((await tools.open(base, 'renomeador', async () => 'falhou')).ok, false);
});

test('copiar o instalador do cliente', () => {
  const base = mk(); put(base, 'suporte-cliente', 'SuporteInformax-cliente-instalador.exe');
  const dest = path.join(mk(), 'cliente.exe');
  assert.deepEqual(tools.copyTo(base, 'suporte-cliente', dest), { ok: true });
  assert.ok(fs.existsSync(dest));
  assert.equal(tools.suggestedName(base, 'suporte-cliente'), 'SuporteInformax-cliente-instalador.exe');
});
