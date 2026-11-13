'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('../src/main/core');

test('a pesquisa/agrupamento da interface é igual ao do núcleo', async () => {
  const lists = await import('../src/renderer/lists.js');
  const its = [
    { brand: 'DAKOTA', ref: '777-1', sender: 'Ana' },
    { brand: 'BEIRA RIO', ref: '8513.115', sender: 'Camilo', site: true, atacado: true },
    { brand: 'BEIRA RIO', ref: '8562.213', sender: 'Camilo' },
    { brand: 'BEBECÊ', ref: 'T3533-150', sender: 'Ana' },
    { brand: '', ref: 'Vizzano 9', sender: 'Ana' },
  ];
  for (const q of ['', 'beira', 'beira 8562', 'ana', 'bebece t3533', 'xyz']) {
    assert.deepEqual(lists.groupByBrand(its, q), core.groupByBrand(its, q), `consulta "${q}"`);
    assert.deepEqual(its.map((i) => lists.matches(i, q)), its.map((i) => core.matches(i, q)));
  }
  assert.equal(lists.norm('Maria’s Shoes Ê'), core.norm('Maria’s Shoes Ê'));
});
